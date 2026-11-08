#!/usr/bin/env python3
"""K026: multi-method overnight Kaggle invsqrt research campaign.

Implements applicable pieces of QRR/Dark-Star/LWE work rather than claiming
unrelated cryptanalytic methods are quantum arithmetic optimizations:
* precision mutation/crossover and active-qubit resource minimization;
* independent K015 source-level modular arithmetic row schedule transforms;
* QRR-inspired grouped versus scalar measurement-uncomputed AND cells;
* bounded/stratified numerical-error pruning and full-range error checks;
* staged OFFICIAL unmodified kickmix verifier over independent seeds;
* persistent SQLite candidate ledger, resume, file-hash verification and lock.

No QPU use, paid service, Kaggle submission or interference with K025.
A finite-domain verifier pass is NOT proof of full benchmark correctness.
"""
from __future__ import annotations
import argparse,ast,dataclasses,fcntl,hashlib,importlib,json,math,os,random
import signal,sqlite3,subprocess,sys,time,traceback,types
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
VERIFIERS=PRIVATE/"official/verifiers"
SOURCE=VERIFIERS/"invsqrt/nr_reference_circuit.py"
VERIFY=VERIFIERS/"invsqrt/verify_submission_invsqrt.py"
SAMPLE=PRIVATE/"official/sample_submission/invsqrt.kmb"
K024=PRIVATE/"runs/k024/search.sqlite3"
K023=HERE.parent/"k023/k023_precision_frontier.json"
RUN=PRIVATE/"runs/k026"
DB=RUN/"campaign.sqlite3"
REPORT=HERE/"k026_status.json"
PARAMS=("delta_bits","coef_bits","square_bits","product_bits","result_bits")
SCHEDULES={
 "horner_delta":("_horner","for control, m in delta:","for control, m in reversed(delta):"),
 "square_outer":("_square","for k in range(1, wc + 1):","for k in reversed(range(1, wc + 1)):"),
 "multiply_m_outer":("_multiply_m","for i in range(width):","for i in reversed(range(width)):"),
 "multiply_y0_outer":("_multiply_y0","for k in range(1, wc + 1):","for k in reversed(range(1, wc + 1)):"),
}
METHODS={
 "QRR_ARITHMETIC_PRECISION":"mutate five working-register widths with exact kickmix cost accounting",
 "QRR_REGISTER_RECYCLING":"test width-reduced live register allocation; K018 plain wire remapping was negative",
 "QRR_SCRATCH_UNCOMPUTE":"test independent scalar measurement-AND variants with official correctness gate",
 "QRR_ADDER_SUBSTITUTION":"K021 ripple and K022 CCX substitutions lost; preserve native iadd for now",
 "QRR_PHASE_LINEAGE":"official verifier must validate measurement/phase behavior",
 "QRR_PHYSICAL_PLACEMENT":"IBM Fez coupling-map site pinning is not a kickmix cost optimization",
 "DARK_STAR_PRUNING":"bounded evolutionary mutation, crossover, strict error/resource constraints",
 "LWE_NOISE_CONSTRAINT":"stratified numerical-error stress inputs and bounded-search heuristics",
 "LWE_FOURIER_NTT":"not used: no proven equivalent transform for this function",
 "LWE_LLL_BKZ":"not used: lattice basis reduction not a relevant adder replacement",
 "K015_ROW_SCHEDULE":"source-level independent partial-product accumulation ordering",
}
def js(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)
def ident(spec):return hashlib.sha256(js(spec).encode()).hexdigest()[:20]
def checksum(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def stats(c):
 s=c.operation_statistics()
 return {"qubits":int(c.num_qubits),"toffoli":int(s.num_toffoli_like),
         "instructions":int(s.num_instructions),"depth":int(c.reaction_depth()),
         "t_like":int(s.num_t_like),"bits":int(c.num_bits)}
def proxy(s):return s["qubits"]*s["toffoli"]
def change_source(text,schedules):
 if not schedules:return text
 tree=ast.parse(text); lines=text.splitlines(keepends=True)
 for name in schedules:
  function,old,new=SCHEDULES[name]
  funcs=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==function]
  if len(funcs)!=1:raise RuntimeError("Missing source function "+function)
  node=funcs[0]
  indices=[i for i in range(node.lineno-1,node.end_lineno)
           if lines[i].lstrip().startswith(old)]
  if len(indices)!=1:raise RuntimeError("Missing source loop "+name)
  i=indices[0]
  lines[i]=lines[i].replace(old,new,1)
 result="".join(lines);ast.parse(result)
 return result

def build(source,spec,export=None):
 """Source mutated in memory. Official verifier and local files untouched."""
 import kickmix as km
 patch=change_source(source,spec["schedule"])
 tag=ident({"schedule":spec["schedule"],"and_mode":spec["and_mode"]})
 name="invsqrt._k026_"+tag
 module=types.ModuleType(name)
 module.__file__=str(SOURCE);module.__package__="invsqrt"
 sys.modules[name]=module  # Python 3.14 dataclasses require this.
 try:
  exec(compile(patch,str(SOURCE),"exec"),module.__dict__)
  if spec["and_mode"]!="grouped":
   def partial_row(builder,inverse,control,terms,target,scratch,subtract=False):
    low=min(i for _,i in terms)
    pairs=list(terms)
    if spec["and_mode"]=="scalar_reverse":pairs.reverse()
    # Independent single-bit AND cells. Reference uses a grouped
    # init_and/del_and, so resource/phase equivalence is NOT assumed.
    for source_q,i in pairs:
     builder.init_and(control,source_q,scratch[i])
    if subtract!=inverse:
     builder.isub(scratch[low:len(target)],target=target[low:])
    else:
     builder.iadd(scratch[low:len(target)],target=target[low:])
    for source_q,i in reversed(pairs):
     builder.del_and(control,source_q,scratch[i])
   module._add_row=partial_row
  p=dataclasses.replace(module.Precision(),**spec["params"])
  circuit=module.build_nr_circuit(10,prec=p)
  result=stats(circuit)
  if export is not None:
   circuit.to_file(str(export),format="kmb")
  return result
 finally:
  sys.modules.pop(name,None)

def screen(model,prec,inputs,bound):
 v=np.asarray(model(10,prec,inputs))
 if v.shape!=inputs.shape or v.dtype.kind not in "fi":
  raise ValueError("Unexpected official model output shape/dtype")
 if not np.all(np.isfinite(v)):raise ValueError("Non-finite numerical model result")
 i=int(np.argmax(np.abs(v)))
 return float(abs(v[i])),int(inputs[i])

def model_screen(model,prec,limit,max_x,batch,adversarial):
 # LWE-inspired constraint pruning: test known hard spots, dyadic regions,
 # and stratified samples FIRST; no assertion of ML-KEM cryptanalysis.
 err=0.0;worst=0;checked=0
 probes=np.asarray(sorted(set(x for x in adversarial if 1<=x<=max_x)),dtype=np.int64)
 for offset in range(0,len(probes),batch):
  sample=probes[offset:offset+batch]
  value,where=screen(model,prec,sample,limit)
  if value>err:err,worst=value,where
  checked+=len(sample)
  if err>limit:return {"pass":False,"max_error":err,"worst_x":worst,
                        "checked":checked,"phase":"adversarial"}
 for first in range(1,max_x+1,batch):
  last=min(max_x,first+batch-1)
  xs=np.arange(first,last+1,dtype=np.int64)
  value,where=screen(model,prec,xs,limit)
  if value>err:err,worst=value,where
  checked+=len(xs)
  if err>limit:return {"pass":False,"max_error":err,"worst_x":worst,
                        "checked":checked,"phase":"full-prefix"}
 return {"pass":True,"max_error":err,"worst_x":worst,"checked":checked,
         "full_prefix_max_x":max_x,"phase":"full-prefix"}

def verify(path,level,seed,shots,timeout):
 total=level*shots;batch=min(256,total)
 while total%batch:batch-=1
 cmd=[sys.executable,str(VERIFY),str(path),"--format","kmb",
      "--max-x",str(level),"--shots-per-x",str(shots),
      "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 began=time.monotonic()
 try:
  p=subprocess.run(cmd,cwd=str(VERIFIERS),capture_output=True,text=True,
        check=False,timeout=timeout)
  try:d=json.loads(p.stdout)
  except json.JSONDecodeError:d={"status":"NON_JSON","stdout_tail":p.stdout[-600:]}
  return {"passed":p.returncode==0 and d.get("status")=="PASS",
    "score":d.get("score"),"error_ratio":d.get("worst_error_over_tolerance"),
    "code":p.returncode,"elapsed":round(time.monotonic()-began,2),
    "stderr_tail":p.stderr[-900:],"status":d.get("status")}
 except subprocess.TimeoutExpired:
  return {"passed":False,"timeout":True,"elapsed":round(time.monotonic()-began,2)}

def db_open():
 db=sqlite3.connect(DB,timeout=30)
 db.execute("PRAGMA journal_mode=WAL")
 db.execute("PRAGMA busy_timeout=30000")
 db.execute("""CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY,v TEXT)""")
 db.execute("""CREATE TABLE IF NOT EXISTS candidates (
 id TEXT PRIMARY KEY, spec TEXT, status TEXT, generation INTEGER,
 model_error REAL, model_worst_x INTEGER, model_done INTEGER,
 resource_json TEXT, resource_proxy INTEGER, circuit TEXT, circuit_sha TEXT,
 reason TEXT, last_update REAL)""")
 db.execute("""CREATE TABLE IF NOT EXISTS tests (
 candidate TEXT,level INTEGER,seed INTEGER,verifier_pass INTEGER,
 score REAL,error_ratio REAL,details TEXT,
 PRIMARY KEY(candidate,level,seed))""")
 db.execute("""CREATE TABLE IF NOT EXISTS reference (
 level INTEGER,seed INTEGER,verifier_pass INTEGER,score REAL,details TEXT,
 PRIMARY KEY(level,seed))""")
 db.commit()
 return db
def update(db,id,**values):
 values["last_update"]=time.time()
 fields=list(values)
 db.execute("UPDATE candidates SET "+", ".join(x+"=?" for x in fields)+
            " WHERE id=?",(*[values[x] for x in fields],id));db.commit()

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--hours",type=float,default=9)
 ap.add_argument("--max-candidates",type=int,default=4000)
 ap.add_argument("--model-max-x",type=int,default=3133452)
 ap.add_argument("--model-batch",type=int,default=8192)
 ap.add_argument("--numerical-headroom",type=float,default=2.5)
 ap.add_argument("--population",type=int,default=24)
 ap.add_argument("--verify-per-generation",type=int,default=4)
 ap.add_argument("--levels",default="64,512,4096,16384,65536")
 ap.add_argument("--seeds",default="12345,23456")
 ap.add_argument("--shots-per-x",type=int,default=2)
 ap.add_argument("--timeout",type=int,default=420)
 ap.add_argument("--random-seed",type=int,default=2601107)
 ap.add_argument("--idle-sleep",type=float,default=10,
   help="Only used if candidate space becomes temporarily exhausted")
 ap.add_argument("--max-errors",type=int,default=30)
 a=ap.parse_args()
 levels=[int(x) for x in a.levels.split(",") if x]
 seeds=[int(x) for x in a.seeds.split(",") if x]
 if not (0<a.hours<=72 and 1<=a.max_candidates<=200000
  and 64<=a.model_max_x<=100000000 and 64<=a.model_batch<=200000
  and 1<=a.numerical_headroom<=100 and 2<=a.population<=128
  and 1<=a.verify_per_generation<=32 and levels==sorted(set(levels))
  and bool(levels) and len(levels)<=10 and bool(seeds) and len(seeds)<=8
  and all(v>0 for v in levels) and all(s>=0 for s in seeds)
  and 1<=a.shots_per_x<=32 and 30<=a.timeout<=3600 and a.idle_sleep>=0
  and a.max_errors>=1):
  ap.error("Invalid search budgets")
 if not all(p.is_file() for p in (SOURCE,VERIFY,SAMPLE)):
  ap.error("Missing K001 official verifier assets")
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 import kickmix as km
 ref=importlib.import_module("invsqrt.nr_reference_circuit")
 default=ref.Precision()
 base={k:int(getattr(default,k)) for k in PARAMS}
 reference_resources=stats(km.Circuit.from_file(str(SAMPLE)))
 ref_cost=proxy(reference_resources)
 RUN.mkdir(parents=True,exist_ok=True)
 lockfile=(RUN/"k026.lock").open("w")
 try:fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise SystemExit("Another K026 run is active")
 db=db_open()
 config={"model_max_x":a.model_max_x,"model_batch":a.model_batch,
   "headroom":a.numerical_headroom,"levels":levels,
   "seeds":seeds,"shots":a.shots_per_x,"reference_sha":checksum(SAMPLE),
   "reference_source_sha":checksum(SOURCE)}
 current=db.execute("SELECT v FROM meta WHERE k='settings'").fetchone()
 if current and json.loads(current[0])!=config:
  ap.error("Existing K026 DB uses different verifier/model settings; preserve old results and use same settings")
 db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)",("settings",js(config)));db.commit()
 source=SOURCE.read_text()
 # Reference full-range error from existing K023 data only when complete and
 # identical parameterization; otherwise compute via official numerical model.
 base_error=None;known_hard=[1,2,3,8192,16384]
 if K023.is_file():
  try:
   history=json.loads(K023.read_text())
   if history.get("criteria",{}).get("max_x_inclusive")==a.model_max_x:
    for row in history.get("candidates",[]):
     if row.get("params")==base and row.get("status")=="DONE":
      base_error=row.get("max_abs_relative_error")
     if row.get("status")=="DONE" and isinstance(row.get("worst_x"),int):
      known_hard.append(row["worst_x"])
  except Exception as e:print("K026 K023 HISTORY ERROR",repr(e),flush=True)
 if base_error is None:
  measured=model_screen(ref.relative_error,default,float("inf"),
                        a.model_max_x,a.model_batch,known_hard)
  base_error=measured["max_error"]
 if not isinstance(base_error,(float,int)) or not 0<base_error<float("inf"):
  raise RuntimeError("No reliable numerical baseline")
 threshold=base_error*a.numerical_headroom
 rng=random.Random(a.random_seed)
 # Deterministic seeded generation across restarts using generation number.
 stopped=False
 def terminate(*_):
  nonlocal stopped
  stopped=True
 signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
 deadline=time.monotonic()+3600*a.hours
 baseline_seeds=[
  (14,17,28,28,29),(14,17,28,27,29),(14,16,28,27,29),
  (13,17,28,28,29),(14,17,27,28,29),(14,17,28,28,28)]
 parent_pool=[tuple(base[x] for x in PARAMS)]
 for row in baseline_seeds:
  if len(row)==len(PARAMS):parent_pool.append(row)
 if K024.is_file():
  try:
   old=sqlite3.connect(f"file:{K024}?mode=ro",uri=True,timeout=5)
   for raw, in old.execute("""SELECT params FROM candidates
      WHERE state='VERIFIED_PARTIAL' ORDER BY cost ASC LIMIT 20"""):
    d=json.loads(raw)
    parent_pool.append(tuple(int(d[k]) for k in PARAMS))
   old.close()
  except Exception as e:print("K026 K024 INTAKE WARNING",repr(e),flush=True)
 # Iterative Pareto-guided mutation and source architecture permutations.
 generation=db.execute("SELECT COALESCE(MAX(generation),-1)+1 FROM candidates").fetchone()[0]
 processed=db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
 error_count=0
 def report(status):
  states=dict(db.execute("SELECT status,COUNT(*) FROM candidates GROUP BY status").fetchall())
  rows=db.execute("""SELECT c.id,c.spec,c.status,c.resource_proxy,c.model_error,
        c.model_worst_x,c.resource_json,
        MAX(CASE WHEN t.verifier_pass=1 THEN t.level ELSE 0 END) AS reach,
        SUM(CASE WHEN t.verifier_pass=0 THEN 1 ELSE 0 END) AS failures
      FROM candidates c LEFT JOIN tests t ON c.id=t.candidate
      GROUP BY c.id ORDER BY reach DESC,failures ASC,c.resource_proxy ASC LIMIT 25""").fetchall()
  summary={"experiment":"K026_OVERNIGHT_MULTIMETHOD_RESEARCH",
    "status":status,"generation":generation,"candidates_seen":processed,
    "states":states,"reference_stats":reference_resources,
    "baseline_model_error":base_error,"numerical_heuristic_limit":threshold,
    "method_registry":METHODS,"leaders":[
      {"id":x[0],"spec":json.loads(x[1]),"status":x[2],"cost":x[3],
      "model_error":x[4],"worst_input":x[5],
      "resources":json.loads(x[6]) if x[6] else None,
      "furthest_verified_prefix":x[7],"failed_tests":x[8] or 0} for x in rows],
    "database":str(DB),"kaggle_submitted":False,"full_domain_verified":False,
    "limitations":["Heuristic model relative-error limit is not official verifier tolerance",
      "No claim that ALL cross-repo algorithms have mathematically applicable transplants",
      "Finite input prefixes and finite seeds do not certify full-domain accuracy"]}
  tmp=REPORT.with_suffix(".tmp");tmp.write_text(json.dumps(summary,indent=2)+"\n")
  tmp.replace(REPORT)
 def candidates_from_generation(g):
  local=random.Random(a.random_seed+g*1000003)
  survivors=db.execute("""SELECT c.spec, MAX(t.level) AS reach
      FROM candidates c JOIN tests t ON c.id=t.candidate
      WHERE t.verifier_pass=1 GROUP BY c.id
      ORDER BY reach DESC,c.resource_proxy ASC LIMIT 35""").fetchall()
  pool=parent_pool[:]
  for raw,reach in survivors:
   sp=json.loads(raw);pool.extend(
       [tuple(sp["params"][k] for k in PARAMS)]*
       max(1,min(5,int(reach)//512)))
  pool=list(dict.fromkeys(pool))
  result=[]
  for i in range(a.population*5):
   if g==0 and i<len(pool):
    params=list(pool[i])
   elif local.random()<0.20:
    params=[base[k] for k in PARAMS]
   else:
    params=list(local.choice(pool))
    if len(pool)>1 and local.random()<0.45:
     other=local.choice(pool)
     params=[local.choice((x,y)) for x,y in zip(params,other)]
   for _ in range(local.choice((1,1,1,2,3))):
    j=local.randrange(len(PARAMS))
    lo=max(3,base[PARAMS[j]]-local.choice((2,3,4,5,7)))
    params[j]=max(lo,min(base[PARAMS[j]],
              params[j]+local.choice((-3,-2,-1,1,2))))
   if g==0 and i<len(pool):
    mode="grouped";schedule=[]
   else:
    mode=local.choices(("grouped","scalar","scalar_reverse"),(75,15,10))[0]
    schedule=sorted(x for x in SCHEDULES if local.random()<0.25)
   spec={"params":dict(zip(PARAMS,params)),
         "and_mode":mode,"schedule":schedule}
   yield spec
 def baseline_verification(level,seed):
  row=db.execute("SELECT verifier_pass,score FROM reference WHERE level=? AND seed=?",
                 (level,seed)).fetchone()
  if row is not None:return row
  result=verify(SAMPLE,level,seed,a.shots_per_x,a.timeout)
  score=result.get("score")
  db.execute("INSERT OR REPLACE INTO reference VALUES (?,?,?,?,?)",
      (level,seed,int(result["passed"]),score,js(result)));db.commit()
  return (int(result["passed"]),score)
 try:
  print("K026 START baseline",reference_resources,"model_error",base_error,
    "limit",threshold,"campaign_hours",a.hours,flush=True)
  report("RUNNING")
  while not stopped and time.monotonic()<deadline and processed<a.max_candidates:
   queued=[]
   for spec in candidates_from_generation(generation):
    id=id_for(spec)
    if db.execute("SELECT 1 FROM candidates WHERE id=?",(id,)).fetchone():continue
    db.execute("""INSERT INTO candidates (id,spec,status,generation,last_update)
               VALUES (?,?,?,?,?)""",
               (id,js(spec),"PENDING",generation,time.time()))
    queued.append((id,spec))
    processed+=1
    if len(queued)>=a.population or processed>=a.max_candidates:break
   db.commit()
   print("K026 GENERATION",generation,"NEW",len(queued),
        "TOTAL",processed,flush=True)
   if not queued:
    generation+=1
    time.sleep(a.idle_sleep)
    continue
   eligible=[]
   for index,(id,spec) in enumerate(queued):
    if stopped or time.monotonic()>=deadline:break
    try:
     precision=dataclasses.replace(default,**spec["params"])
     numerics=model_screen(ref.relative_error,precision,threshold,
                            a.model_max_x,a.model_batch,known_hard)
     if not numerics["pass"]:
      update(db,id,status="MODEL_REJECT",model_error=numerics["max_error"],
        model_worst_x=numerics["worst_x"],model_done=0,
        reason=numerics["phase"]);continue
     st=build(source,spec)
     candidate_cost=proxy(st)
     update(db,id,status="STATIC_WIN" if candidate_cost<ref_cost else "STATIC_REJECT",
        model_error=numerics["max_error"],model_worst_x=numerics["worst_x"],
        model_done=a.model_max_x,resource_json=js(st),
        resource_proxy=candidate_cost)
     if candidate_cost<ref_cost:eligible.append((id,spec,st,candidate_cost,numerics))
    except Exception as e:
     error_count+=1
     update(db,id,status="BUILD_OR_MODEL_ERROR",
       reason=f"{type(e).__name__}: {str(e)[:250]}")
     print("K026 ERROR",id,type(e).__name__,str(e)[:180],flush=True)
    if index%6==0:report("RUNNING")
   # Diversified promotion: best resource cost and best numerical accuracy.
   by_cost=sorted(eligible,key=lambda x:x[3])
   by_error=sorted(eligible,key=lambda x:x[4]["max_error"])
   chosen=[];added=set()
   for i in range(max(len(by_cost),len(by_error))):
    for ranked in (by_cost,by_error):
     if i<len(ranked) and ranked[i][0] not in added:
      x=ranked[i];added.add(x[0]);chosen.append(x)
     if len(chosen)>=a.verify_per_generation:break
    if len(chosen)>=a.verify_per_generation:break
   for id,spec,st,c,numerics in chosen:
    if stopped or time.monotonic()>=deadline:break
    file=RUN/(id+".kmb")
    try:
     rebuilt=build(source,spec,export=file)
     if rebuilt!=st:raise AssertionError("nondeterministic cost profile")
     update(db,id,status="VERIFYING",circuit=str(file),
       circuit_sha=checksum(file))
     survives=True
     for level in levels:
      if not survives or stopped or time.monotonic()>=deadline:break
      for seed in seeds:
       if stopped or time.monotonic()>=deadline:break
       past=db.execute("""SELECT verifier_pass FROM tests
           WHERE candidate=? AND level=? AND seed=?""",(id,level,seed)).fetchone()
       if past is not None:
        survives=bool(past[0]);continue
       ref_status,ref_score=baseline_verification(level,seed)
       if not ref_status or not isinstance(ref_score,(float,int)):
        print("K026 STOP baseline verifier failed",level,seed,flush=True)
        stopped=True;break
       result=verify(file,level,seed,a.shots_per_x,a.timeout)
       score=result.get("score")
       wins=(result["passed"] and isinstance(score,(float,int))
             and score<ref_score)
       db.execute("INSERT OR REPLACE INTO tests VALUES (?,?,?,?,?,?,?)",
         (id,level,seed,int(wins),score,
          result.get("error_ratio"),js(result)));db.commit()
       print("K026 VERIFY",id,"X",level,"SEED",seed,
         "PASS",result["passed"],"SCORE_DELTA",
         (score-ref_score if isinstance(score,(int,float)) else None),
         "ERROR_RATIO",result.get("error_ratio"),flush=True)
       if not wins:
        survives=False;break
     if survives and not stopped:
      update(db,id,status="PARTIAL_VERIFIER_PASS")
     elif db.execute("SELECT 1 FROM tests WHERE candidate=? AND verifier_pass=0",
                     (id,)).fetchone():
      update(db,id,status="OFFICIAL_REJECT")
      # Rejected variants need not consume persistent storage.
      if file.exists():file.unlink()
     else:update(db,id,status="PAUSED_VERIFICATION")
    except Exception as e:
     error_count+=1;update(db,id,status="EXPORT_OR_VERIFY_ERROR",
       reason=f"{type(e).__name__}: {str(e)[:300]}")
     print("K026 EXPORT/VERIFY ERROR",id,repr(e),flush=True)
    report("RUNNING")
   generation+=1
   report("RUNNING")
   if error_count>=a.max_errors:
    print("K026 STOP too many repeated errors",error_count,flush=True)
    break
  reason=("STOP_SIGNAL" if stopped else
          "STOP_ERROR_THRESHOLD" if error_count>=a.max_errors else
          "STOP_CANDIDATE_BUDGET" if processed>=a.max_candidates else
          "FINISHED_HOURS")
  report(reason)
  print("K026 STATUS",reason,"TOTAL",processed,
       "GENERATIONS",generation,flush=True)
  print("K026 REPORT",REPORT,"K026 SQLITE",DB,flush=True)
 finally:
  db.close()
  fcntl.flock(lockfile,fcntl.LOCK_UN)
  lockfile.close()
if __name__=="__main__":main()
