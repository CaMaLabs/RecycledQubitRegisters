#!/usr/bin/env python3
"""K020: resumable overnight mutagenic precision optimization for Kaggle invsqrt.

Search combines QRR-style resource accounting with evolutionary mutations,
crossover and LWE-inspired bounded candidate selection. All arithmetic is
generated with Google's original local reference builder and the official
Precision dataclass. Every promoted circuit goes through the UNMODIFIED
official verifier. No cryptanalytic algorithm is claimed to prove circuit
equivalence. No Kaggle submissions, API calls, QPU jobs, or costs.

IMPORTANT: partial-domain verifier PASS != full benchmark correctness.
The winner ledger records tested max_x and seeds, never claims universal PASS.
"""
from __future__ import annotations
import argparse, concurrent.futures, dataclasses, hashlib, importlib, json, math
import os, random, shutil, signal, sqlite3, subprocess, sys, time, traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
ROOT=HERE.parents[1]
VERIFIERS=PRIVATE/"official/verifiers"
SAMPLE=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFY=VERIFIERS/"invsqrt/verify_submission_invsqrt.py"
RUN=PRIVATE/"runs/k020"
DB=RUN/"search.sqlite3"
REPORT=HERE/"k020_status.json"
PARAMS=("delta_bits","coef_bits","square_bits","product_bits","result_bits")
CANDIDATE_SEEDS=[
 (14,17,28,28,29), # official
 (14,16,28,27,29), # K016 case21; smoke survived 8192
 (14,17,28,27,29), # K016 case10; smoke survived 8192
 (14,17,27,28,29), # K016 case7
 (14,17,28,28,28), # K016 case13
 (14,16,28,28,29), # failed by 4096, keep as negative control
 (14,15,28,28,29), # failed by 128, keep as negative control
]

def js(v):return json.dumps(v,sort_keys=True,separators=(",",":"))
def config_id(cfg):return hashlib.sha256(js(cfg).encode()).hexdigest()[:20]
def profile(c):
 s=c.operation_statistics()
 return {"qubits":int(c.num_qubits),"bits":int(c.num_bits),
         "toffoli_like":int(s.num_toffoli_like),
         "t_like":int(s.num_t_like),
         "instructions":int(s.num_instructions),
         "reaction_depth":int(c.reaction_depth())}
def sha(path):
 with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()

def build_job(job):
 """Runs in a separate worker; never writes to SQLite or reports."""
 cfg, dest, mode, model_x=job
 row={"config":cfg,"id":config_id(cfg)}
 try:
  if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
  import kickmix as km
  mod=importlib.import_module("invsqrt.nr_reference_circuit")
  defaults=mod.Precision()
  precision=dataclasses.replace(defaults,**cfg)
  circuit=mod.build_nr_circuit(10,prec=precision)
  row["resources"]=profile(circuit)
  row["proxy"]=row["resources"]["qubits"]*row["resources"]["toffoli_like"]
  row["status"]="BUILT"
  # Optional numeric reference probe ranks candidates; it is not a correctness
  # gate. A model's return shape or units must not be assumed.
  if mode and model_x:
   try:
    import numpy as np
    values=np.asarray(mod.relative_error(10,precision,np.asarray(model_x,dtype=np.int64)))
    if values.size and values.dtype.kind in "fi" and np.all(np.isfinite(values)):
     row["model_abs_max"]=float(np.max(np.abs(values)))
     row["model_abs_p95"]=float(np.percentile(np.abs(values),95))
   except Exception as error:
    row["model_note"]=f"{type(error).__name__}: {str(error)[:180]}"
  if dest:
   target=Path(dest)
   target.parent.mkdir(parents=True,exist_ok=True)
   circuit.to_file(str(target),format="kmb")
   row["path"]=str(target)
   row["sha256"]=sha(target)
 except Exception as error:
  row["status"]="BUILD_ERROR"
  row["error"]=f"{type(error).__name__}: {str(error)[:350]}"
 return row

def run_verifier(path,max_x,seed,shots,timeout):
 total=max_x*shots
 batch=min(256,total)
 while total%batch:batch-=1
 cmd=[sys.executable,str(VERIFY),str(path),"--format","kmb",
      "--max-x",str(max_x),"--shots-per-x",str(shots),
      "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 started=time.monotonic()
 try:
  cp=subprocess.run(cmd,cwd=str(VERIFIERS),capture_output=True,text=True,
      timeout=timeout,check=False)
  try:result=json.loads(cp.stdout)
  except json.JSONDecodeError:
   result={"status":"ERROR","message":"non-JSON stdout","tail":cp.stdout[-350:]}
  return {"passed":cp.returncode==0 and result.get("status")=="PASS",
          "exit_code":cp.returncode,"result":result,
          "stderr":cp.stderr[-550:],"seconds":round(time.monotonic()-started,2),
          "max_x":max_x,"seed":seed,"shots_per_x":shots}
 except subprocess.TimeoutExpired:
  return {"passed":False,"timed_out":True,"max_x":max_x,
          "seed":seed,"seconds":round(time.monotonic()-started,2)}

def open_db(path):
 db=sqlite3.connect(path,timeout=40)
 db.execute("PRAGMA journal_mode=WAL")
 db.execute("PRAGMA busy_timeout=40000")
 db.execute("""CREATE TABLE IF NOT EXISTS candidates (
 id TEXT PRIMARY KEY, config TEXT NOT NULL, generation INTEGER NOT NULL,
 resources TEXT, proxy REAL, model_abs_max REAL, status TEXT NOT NULL,
 path TEXT, sha256 TEXT, last_updated REAL NOT NULL)""")
 db.execute("""CREATE TABLE IF NOT EXISTS tests (
 id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL,
 max_x INTEGER NOT NULL, seed INTEGER NOT NULL,
 passed INTEGER NOT NULL, score REAL, error_ratio REAL,
 result_json TEXT, UNIQUE(candidate_id,max_x,seed))""")
 db.execute("""CREATE TABLE IF NOT EXISTS reference_tests (
 max_x INTEGER NOT NULL, seed INTEGER NOT NULL,
 passed INTEGER NOT NULL, score REAL, result_json TEXT,
 PRIMARY KEY(max_x,seed))""")
 db.execute("""CREATE TABLE IF NOT EXISTS metadata (
 key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
 db.commit()
 return db

def mutate(rng,parents,default,bounds):
 if not parents or rng.random()<0.20:
  cfg=list(default)
 else:
  a=list(rng.choice(parents))
  if len(parents)>1 and rng.random()<0.45:
   b=rng.choice(parents)
   cfg=[rng.choice((a[i],b[i])) for i in range(5)]
  else:cfg=a
 for _ in range(1 if rng.random()<0.75 else rng.choice((2,3))):
  i=rng.randrange(5)
  lo,hi=bounds[i]
  if rng.random()<0.15:cfg[i]=rng.randint(lo,hi)
  else:cfg[i]=max(lo,min(hi,cfg[i]+rng.choice((-2,-1,1,2))))
 return tuple(cfg)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--hours",type=float,default=8)
 p.add_argument("--workers",type=int,default=2)
 p.add_argument("--generation-size",type=int,default=24)
 p.add_argument("--promote-per-generation",type=int,default=4)
 p.add_argument("--levels",default="64,512,4096,8192")
 p.add_argument("--seeds",default="12345,23456")
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--verifier-timeout",type=int,default=240)
 p.add_argument("--max-candidates",type=int,default=2500)
 p.add_argument("--max-verifications",type=int,default=300)
 p.add_argument("--rng-seed",type=int,default=20261107)
 p.add_argument("--model-probe",action="store_true",
                help="Rank using the official deterministic model; never use it as sole proof")
 p.add_argument("--report",type=Path,default=REPORT)
 args=p.parse_args()
 levels=[int(x) for x in args.levels.split(",")]
 seeds=[int(x) for x in args.seeds.split(",")]
 if not (0<args.hours<=48 and 1<=args.workers<=8 and
         2<=args.generation_size<=256 and 1<=args.promote_per_generation<=32 and
         1<=args.max_candidates<=100000 and 0<=args.max_verifications<=100000 and
         1<=args.shots_per_x<=64 and 10<=args.verifier_timeout<=3600 and
         1<=len(levels)<=10 and 1<=len(seeds)<=10 and
         levels==sorted(set(levels)) and all(x>0 for x in levels)):
  p.error("invalid budgets or verification stages")
 if not SAMPLE.is_file() or not VERIFY.is_file():
  p.error("K001 bootstrap assets are missing")
 RUN.mkdir(parents=True,exist_ok=True)
 db=open_db(DB)
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 mod=importlib.import_module("invsqrt.nr_reference_circuit")
 defaults=mod.Precision()
 baseline=tuple(int(getattr(defaults,x)) for x in PARAMS)
 bounds=tuple((max(3,x-7),x) for x in baseline)
 # coef_bits below 15 produced build errors in K016, but keep discovery
 # possible; candidate failures are logged without crashing overnight run.
 import kickmix as km
 ref=km.Circuit.from_file(str(SAMPLE))
 base_stats=profile(ref);base_proxy=base_stats["qubits"]*base_stats["toffoli_like"]
 run_config={"levels":levels,"seeds":seeds,"shots_per_x":args.shots_per_x,
     "default_precision":dict(zip(PARAMS,baseline)),"source_hash":sha(SAMPLE)}
 existing=db.execute("SELECT value FROM metadata WHERE key='run_config'").fetchone()
 if existing and json.loads(existing[0])!=run_config:
  p.error("Database belongs to different verifier settings; use same options or archive private/runs/k020")
 db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)",
     ("run_config",js(run_config)))
 db.commit()
 rng=random.Random(args.rng_seed)
 signal_stop=[False]
 def stop(*_):signal_stop[0]=True
 signal.signal(signal.SIGTERM,stop)
 signal.signal(signal.SIGINT,stop)
 deadline=time.monotonic()+args.hours*3600
 model_x=[]
 if args.model_probe:
  bound=3*(2**10-2)**2
  model_x=sorted(set([1,bound,*[min(bound,int(2**(i/8))) for i in range(8*22)]]
      +[rng.randint(1,bound) for _ in range(64)]))
 verified_count=db.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
 generation=db.execute("SELECT COALESCE(MAX(generation),-1)+1 FROM candidates").fetchone()[0]
 baseline_cache={}
 for max_x,seed,passed,score,result in db.execute(
     "SELECT max_x,seed,passed,score,result_json FROM reference_tests"):
  baseline_cache[(max_x,seed)]={"passed":bool(passed),"score":score}
 report={"status":"RUNNING","experiment":"K020_OVERNIGHT_MUTAGENIC_PRECISION_SEARCH",
   "db":str(DB),"baseline":base_stats,"default_precision":dict(zip(PARAMS,baseline)),
   "hours_budget":args.hours,"workers":args.workers,"generation_size":args.generation_size,
   "levels":levels,"seeds":seeds,"full_domain_verified":False,
   "kaggle_submitted":False,
   "warnings":["Model probe is advisory only",
     "No automated full-domain proof or Kaggle submission",
     "Verifier cost and accuracy are assessed only over the named input range and seeds",
     "Correctness for quantum superpositions/measurement feedback requires official verifier"],
   "generation":generation,"tested_candidates":0,"verifier_tests":verified_count}
 def save():
  report["generation"]=generation
  report["verifier_tests"]=verified_count
  report["tested_candidates"]=db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
  report["survivors"]=db.execute(
   "SELECT candidate_id,MAX(max_x) FROM tests WHERE passed=1 GROUP BY candidate_id "
   "ORDER BY MAX(max_x) DESC LIMIT 12").fetchall()
  args.report.parent.mkdir(parents=True,exist_ok=True)
  args.report.write_text(json.dumps(report,indent=2)+"\n")
 def cfgdict(v):return dict(zip(PARAMS,v))
 def parents():
  # Base parents plus the best previously verified candidates, weighted by
  # maximum passed stage and their static cost. No unverified claims.
  rows=db.execute("""SELECT c.config,MAX(t.max_x) AS reach,MIN(t.score) AS score
   FROM candidates c JOIN tests t ON t.candidate_id=c.id
   WHERE t.passed=1 AND t.score IS NOT NULL
   GROUP BY c.id ORDER BY reach DESC,score ASC LIMIT 24""").fetchall()
  values=list(CANDIDATE_SEEDS)
  for raw,reach,score in rows:
   d=json.loads(raw)
   values.extend([tuple(d[x] for x in PARAMS)]*max(1,min(5,reach//64)))
  return values
 def reference_test(max_x,seed):
  key=(max_x,seed)
  if key in baseline_cache:return baseline_cache[key]
  result=run_verifier(SAMPLE,max_x,seed,args.shots_per_x,args.verifier_timeout)
  score=result.get("result",{}).get("score")
  db.execute("INSERT OR REPLACE INTO reference_tests VALUES (?,?,?,?,?)",
    (max_x,seed,int(result["passed"]),score,js(result)))
  db.commit()
  baseline_cache[key]={"passed":result["passed"],"score":score}
  return baseline_cache[key]
 try:
  with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
   while not signal_stop[0] and time.monotonic()<deadline:
    done=db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    if done>=args.max_candidates or verified_count>=args.max_verifications:break
    members=parents();proposed=[]
    # Explicitly test defaults/known K016 cases once; then mutate.
    if done==0:
     proposed.extend(CANDIDATE_SEEDS)
    tries=0
    while len(proposed)<args.generation_size and tries<args.generation_size*80:
     proposed.append(mutate(rng,members,baseline,bounds));tries+=1
    unique=[]
    existing_ids={row[0] for row in db.execute("SELECT id FROM candidates")}
    seen=set()
    for v in proposed:
     cfg=cfgdict(v);cid=config_id(cfg)
     if cid not in seen and cid not in existing_ids:
      seen.add(cid);unique.append((cid,cfg))
     if len(unique)>=min(args.generation_size,args.max_candidates-done):break
    if not unique:
     print("K020 STOP: mutation space yielded no novel candidates",flush=True);break
    print(f"K020 GENERATION={generation} NEW={len(unique)} "
          f"DB={done} VERIFIED_TESTS={verified_count}",flush=True)
    future_map={
     pool.submit(build_job,(cfg,None,args.model_probe,model_x)): (cid,cfg)
     for cid,cfg in unique
    }
    built=[]
    for future in concurrent.futures.as_completed(future_map):
     cid,cfg=future_map[future]
     try:row=future.result()
     except Exception as error:
      row={"status":"WORKER_ERROR","error":str(error)[:400]}
     resource=row.get("resources")
     proxy=row.get("proxy")
     status=row["status"]
     if status=="BUILT":
      status="STATIC_WIN" if proxy<base_proxy else "STATIC_PRUNED"
      if all(cfg[key]==baseline[i] for i,key in enumerate(PARAMS)):
       status="REFERENCE"
     db.execute("""INSERT OR IGNORE INTO candidates
      (id,config,generation,resources,proxy,model_abs_max,status,path,sha256,last_updated)
      VALUES (?,?,?,?,?,?,?,?,?,?)""",
      (cid,js(cfg),generation,js(resource) if resource else None,
       proxy,row.get("model_abs_max"),status,None,None,time.time()))
     if status=="STATIC_WIN":built.append((cid,cfg,row))
    db.commit()
    # The exploration frontier includes candidates that minimize actual
    # qubit*Toffoli proxy, with a modest model heuristic if available.
    built.sort(key=lambda a:(a[2]["proxy"],
                  a[2].get("model_abs_max",0.0)))
    selected=built[:args.promote_per_generation]
    print(f"K020 GENERATION={generation} STATIC_WINS={len(built)} "
          f"PROMOTED={len(selected)}",flush=True)
    for cid,cfg,preview in selected:
     if signal_stop[0] or time.monotonic()>deadline or verified_count>=args.max_verifications:break
     target=RUN/"candidates"/(cid+".kmb")
     row=build_job((cfg,str(target),False,[]))
     if row.get("status")!="BUILT":
      db.execute("UPDATE candidates SET status=? WHERE id=?",("EXPORT_FAILED",cid));db.commit()
      continue
     db.execute("UPDATE candidates SET status=?,path=?,sha256=? WHERE id=?",
       ("VERIFYING",str(target),row["sha256"],cid))
     db.commit()
     furthest=0;passes=0;failed=False
     try:
      for max_x in levels:
       if failed or signal_stop[0] or time.monotonic()>deadline:break
       for seed in seeds:
        if signal_stop[0] or time.monotonic()>deadline or verified_count>=args.max_verifications:
         break
        baseline_test=reference_test(max_x,seed)
        if not baseline_test["passed"]:
         print("K020 BASELINE FAILED/TIMED OUT",max_x,seed,flush=True)
         failed=True;break
        result=run_verifier(target,max_x,seed,args.shots_per_x,args.verifier_timeout)
        verified_count+=1
        output=result.get("result",{})
        score=output.get("score")
        winning=(result["passed"] and isinstance(score,(int,float))
                and score<baseline_test["score"])
        db.execute("""INSERT OR REPLACE INTO tests
         (candidate_id,max_x,seed,passed,score,error_ratio,result_json)
         VALUES (?,?,?,?,?,?,?)""",
         (cid,max_x,seed,int(winning),score,
           output.get("worst_error_over_tolerance"),js(result)))
        db.commit()
        print(f"K020 CANDIDATE={cid} INPUTS={max_x} SEED={seed} "
          f"PASS={result['passed']} SCORE={score} IMPROVES={winning} "
          f"ERROR={output.get('worst_error_over_tolerance')}",flush=True)
        if not winning:
         failed=True;break
        passes+=1;furthest=max_x
       if failed:break
     finally:
      # Keep only fully staged survivors as useful submission *candidates*;
      # failing options can be reconstructed reproducibly from the JSON config.
      completed=(passes==len(levels)*len(seeds))
      if not completed and target.exists():target.unlink()
      status=("STAGED_SMOKE_PASS_NOT_FULL_DOMAIN" if completed else
         "REJECTED_OR_INCOMPLETE")
      db.execute("UPDATE candidates SET status=?,path=?,sha256=? WHERE id=?",
         (status,str(target) if completed else None,
          row["sha256"] if completed else None,cid))
      db.commit()
     report["most_recent_candidate"]={"id":cid,"changes":cfg,"furthest_max_x":furthest,
        "completed_all_stages":completed,"resources":preview.get("resources")}
     save()
    generation+=1
    save()
  report["status"]="STOPPED" if signal_stop[0] else "FINISHED_BUDGET"
 except Exception:
  report["status"]="ERROR"
  report["traceback"]=traceback.format_exc()[-6000:]
  raise
 finally:
  save()
  print("K020 STATUS",report["status"],flush=True)
  print("K020 DATABASE",DB,flush=True)
  print("K020 REPORT",args.report,flush=True)
  db.close()

if __name__=="__main__":main()
