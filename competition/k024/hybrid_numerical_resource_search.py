#!/usr/bin/env python3
"""K024: restartable, independent hybrid search over invsqrt precision.

Stage 1: deterministic model screens on 1..min(max-x,8192).
Stage 2: full-range numerical screen for survivors, with overflow rejection.
Stage 3: build kickmix circuit, rank by actual resource proxy.
Stage 4: UNMODIFIED official verifier at progressively larger x ranges.
Each decision is checkpointed in a separate SQLite file. No K020/K023 writes.

A numerical model result is not a quantum verification certificate.
No Kaggle submission is performed.
"""
from __future__ import annotations
import argparse,dataclasses,hashlib,importlib,itertools,json,math,os,sqlite3,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
VERIFIERS=PRIVATE/"official/verifiers"
SAMPLE=PRIVATE/"official/sample_submission/invsqrt.kmb"
OFFICIAL=VERIFIERS/"invsqrt/verify_submission_invsqrt.py"
RUN=PRIVATE/"runs/k024"
DB=RUN/"search.sqlite3"
SUMMARY=HERE/"k024_status.json"
K023=HERE.parent/"k023/k023_precision_frontier.json"
PARAMS=("delta_bits","coef_bits","square_bits","product_bits","result_bits")

def compact(obj):return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)
def cid(params):return hashlib.sha256(compact(params).encode()).hexdigest()[:16]
def hash_file(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def resources(c):
 s=c.operation_statistics()
 return {"qubits":int(c.num_qubits),"toffoli":int(s.num_toffoli_like),
         "instructions":int(s.num_instructions),"depth":int(c.reaction_depth()),
         "t_like":int(s.num_t_like)}
def proxy(s):return s["qubits"]*s["toffoli"]
def open_db():
 RUN.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(DB,timeout=30)
 db.execute("PRAGMA journal_mode=WAL")
 db.execute("PRAGMA busy_timeout=30000")
 db.execute("""CREATE TABLE IF NOT EXISTS metadata(k TEXT PRIMARY KEY, v TEXT)""")
 db.execute("""CREATE TABLE IF NOT EXISTS candidates(
  id TEXT PRIMARY KEY, params TEXT NOT NULL, state TEXT NOT NULL,
  model_err REAL, model_worst_x INTEGER, model_checked_x INTEGER DEFAULT 0,
  resources TEXT, cost INTEGER, file TEXT, file_sha TEXT,
  fail_reason TEXT, updated REAL)""")
 db.execute("""CREATE TABLE IF NOT EXISTS verifications(
  id TEXT, max_x INTEGER, seed INTEGER, passed INTEGER, score REAL,
  error_ratio REAL, details TEXT, PRIMARY KEY(id,max_x,seed))""")
 db.execute("""CREATE TABLE IF NOT EXISTS reference_checks(
  max_x INTEGER, seed INTEGER, passed INTEGER, score REAL, details TEXT,
  PRIMARY KEY(max_x,seed))""")
 db.commit()
 return db
def put(db,ident,**fields):
 fields["updated"]=time.time()
 keys=list(fields)
 db.execute("UPDATE candidates SET "+",".join(k+"=?" for k in keys)+
            " WHERE id=?",(*[fields[k] for k in keys],ident))
 db.commit()
def run_verifier(file,max_x,seed,shots,timeout):
 n=max_x*shots;batch=min(256,n)
 while n%batch:batch-=1
 args=[sys.executable,str(OFFICIAL),str(file),"--format","kmb",
       "--max-x",str(max_x),"--shots-per-x",str(shots),
       "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 started=time.monotonic()
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,
                   cwd=str(VERIFIERS),check=False)
  try:result=json.loads(p.stdout)
  except json.JSONDecodeError:result={"status":"NON_JSON","stdout_tail":p.stdout[-900:]}
  return {"passed":p.returncode==0 and result.get("status")=="PASS",
          "score":result.get("score"),"worst_error_over_tolerance":result.get("worst_error_over_tolerance"),
          "returncode":p.returncode,"elapsed":round(time.monotonic()-started,1),
          "result":result,"stderr":p.stderr[-1000:]}
 except subprocess.TimeoutExpired:
  return {"passed":False,"timed_out":True,"elapsed":round(time.monotonic()-started,1)}
def screen(model,precision,max_x,batch,limit):
 maxerr=0.0;worst=0
 for start in range(1,max_x+1,batch):
  end=min(start+batch-1,max_x)
  xs=np.arange(start,end+1,dtype=np.int64)
  values=np.asarray(model(10,precision,xs))
  if values.shape!=xs.shape or values.dtype.kind not in "fi":
   raise ValueError("Unexpected deterministic-model result")
  if not np.all(np.isfinite(values)):raise ValueError("Non-finite model outputs")
  pos=int(np.argmax(np.abs(values)))
  err=float(abs(values[pos]))
  if err>maxerr:maxerr=err;worst=int(xs[pos])
  if limit is not None and maxerr>limit:
   return maxerr,worst,end,False
 return maxerr,worst,max_x,True
def emit(db,status,baseline,settings):
 states=dict(db.execute("SELECT state,COUNT(*) FROM candidates GROUP BY state").fetchall())
 rows=db.execute("""SELECT c.id,c.params,c.state,c.model_err,c.model_worst_x,
  c.model_checked_x,c.cost,c.resources,c.file,
  MAX(CASE WHEN v.passed=1 THEN v.max_x ELSE 0 END),
  SUM(CASE WHEN v.passed=0 THEN 1 ELSE 0 END)
 FROM candidates c LEFT JOIN verifications v ON v.id=c.id
 GROUP BY c.id
 ORDER BY COALESCE(MAX(CASE WHEN v.passed=1 THEN v.max_x ELSE 0 END),0) DESC,
 COALESCE(SUM(CASE WHEN v.passed=0 THEN 1 ELSE 0 END),0) ASC,
 c.cost ASC LIMIT 20""").fetchall()
 leaders=[{"id":x[0],"params":json.loads(x[1]),"state":x[2],
   "max_relative_error":x[3],"worst_x":x[4],"screened_through":x[5],
   "cost_proxy":x[6],"resources":json.loads(x[7]) if x[7] else None,
   "file":x[8],"furthest_official_pass":x[9],
   "verifier_failures":x[10] or 0} for x in rows]
 record={"experiment":"K024_HYBRID_MUTAGENIC_NUMERICAL_RESOURCE_VERIFIER",
  "status":status,"state_counts":states,"baseline":baseline,
  "settings":settings,"leaders":leaders,
  "k020_modified":False,"k023_modified":False,
  "full_official_domain_verified":False,"kaggle_submitted":False,
  "limitations":["Only the official verifier validates circuit behavior on tested inputs",
   "Deterministic model screening is necessary exploration, not sufficient verification",
   "A limited verifier input range is never a full-domain guarantee"]}
 tmp=SUMMARY.with_suffix(".tmp")
 tmp.write_text(json.dumps(record,indent=2)+"\n");tmp.replace(SUMMARY)
 return record

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--hours",type=float,default=8)
 p.add_argument("--max-x",type=int,default=3133452)
 p.add_argument("--batch-size",type=int,default=8192)
 p.add_argument("--numerical-headroom",type=float,default=2.25,
   help="Relative to official deterministic reference; heuristic ranking screen, NOT official tolerance")
 p.add_argument("--max-candidates",type=int,default=150)
 p.add_argument("--max-builds",type=int,default=35)
 p.add_argument("--max-official-candidates",type=int,default=12)
 p.add_argument("--levels",default="64,512,4096,16384")
 p.add_argument("--seeds",default="12345")
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--verifier-timeout",type=int,default=360)
 args=p.parse_args()
 levels=[int(v) for v in args.levels.split(",") if v]
 seeds=[int(v) for v in args.seeds.split(",") if v]
 if not (0<args.hours<=72 and 1<=args.max_x<=100000000 and
         256<=args.batch_size<=200000 and 1<=args.max_candidates<=1000 and
         1<=args.max_builds<=200 and 1<=args.max_official_candidates<=100 and
         1<=args.shots_per_x<=32 and 30<=args.verifier_timeout<=3600 and
         1<=args.numerical_headroom<=100 and levels==sorted(set(levels))
         and bool(levels) and bool(seeds) and all(x>0 for x in levels+seeds)):
  p.error("Invalid parameters")
 if not SAMPLE.is_file() or not OFFICIAL.is_file():
  p.error("K001 competition files missing")
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 import kickmix as km
 mod=importlib.import_module("invsqrt.nr_reference_circuit")
 default=mod.Precision()
 original={k:int(getattr(default,k)) for k in PARAMS}
 baseline=resources(km.Circuit.from_file(str(SAMPLE)))
 # Fix the same precision grid across resumptions.
 settings={"original":original,"max_x":args.max_x,"batch_size":args.batch_size,
     "headroom_multiplier":args.numerical_headroom,
     "levels":levels,"seeds":seeds,"shots_per_x":args.shots_per_x,
     "sample_sha256":hash_file(SAMPLE)}
 db=open_db()
 old=db.execute("SELECT v FROM metadata WHERE k='settings'").fetchone()
 if old and json.loads(old[0])!=settings:
  p.error("Different parameters from existing K024 database; keep settings or archive K024 run directory")
 db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)",("settings",compact(settings)))
 db.commit()
 start=time.monotonic();deadline=start+args.hours*3600
 # Baseline measured on full numerical range, checkpointed as one job.
 base_id=cid(original)
 db.execute("INSERT OR IGNORE INTO candidates(id,params,state,updated) VALUES (?,?,?,?)",
            (base_id,compact(original),"NEW",time.time()))
 db.commit()
 row=db.execute("SELECT state,model_err,model_checked_x FROM candidates WHERE id=?",(base_id,)).fetchone()
 if row[0] in ("FULL_MODEL_PASS","BUILT","VERIFIED_PARTIAL") and row[2]==args.max_x:
  base_error=row[1]
 else:
  print("K024 baseline model sweep",args.max_x,flush=True)
  base_error,worst,checked,_=screen(mod.relative_error,default,
                                   args.max_x,args.batch_size,None)
  put(db,base_id,state="FULL_MODEL_PASS",model_err=base_error,
      model_worst_x=worst,model_checked_x=checked,
      resources=compact(baseline),cost=proxy(baseline))
 if base_error<=0:raise RuntimeError("Reference numerical error unexpectedly zero")
 threshold=base_error*args.numerical_headroom
 print("K024 REFERENCE ERROR",base_error,"HEURISTIC SCREEN LIMIT",threshold,flush=True)
 # Seed targeted from verified K016, then 0..2 bit reductions. Values are
 # deterministic so a stopped search can resume with the same candidate set.
 combos=list(itertools.product((0,1,2),repeat=5))
 def rank(ds):
  d,c,s,p,r=ds
  # First prioritize modest reductions with prior K016 evidence.
  known={(0,0,0,1,0),(0,0,1,0,0),(0,0,0,0,1),
         (0,1,0,1,0),(1,0,0,0,0)}
  if ds==(0,0,0,0,0):return (-2,0,ds)
  if ds in known:return (-1,sum(ds),ds)
  return (0,sum(ds),ds)
 combos.sort(key=rank)
 combos=combos[:args.max_candidates]
 config_list=[]
 for offsets in combos:
  params={k:original[k]-offsets[i] for i,k in enumerate(PARAMS)}
  if min(params.values())<3:continue
  ident=cid(params)
  config_list.append((ident,params))
  db.execute("INSERT OR IGNORE INTO candidates(id,params,state,updated) VALUES (?,?,?,?)",
             (ident,compact(params),"NEW",time.time()))
 db.commit()
 # K023 results are valid full-range deterministic scans for exactly the
 # same model and bound only. Reuse them if input bound matches.
 reused=0
 if K023.is_file():
  try:
   k023=json.loads(K023.read_text())
   if k023.get("criteria",{}).get("max_x_inclusive")==args.max_x:
    for record in k023.get("candidates",[]):
     if record.get("status")!="DONE" or record.get("tested_through_x")!=args.max_x:continue
     config=record.get("params",{})
     ident=cid(config)
     state_row=db.execute("SELECT state FROM candidates WHERE id=?",(ident,)).fetchone()
     if state_row and state_row[0]=="NEW":
      error=record.get("max_abs_relative_error")
      if isinstance(error,(int,float)) and math.isfinite(error):
       state="FULL_MODEL_PASS" if error<=threshold else "MODEL_REJECT"
       put(db,ident,state=state,model_err=error,
           model_worst_x=record.get("worst_x"),model_checked_x=args.max_x,
           fail_reason=None if state=="FULL_MODEL_PASS" else "ABOVE_HEURISTIC_NUMERICAL_LIMIT")
       reused+=1
  except Exception as ex:
   print("K024 WARNING K023 import",str(ex)[:300],flush=True)
 print("K024 K023 COMPLETE SCANS REUSED",reused,flush=True)
 emit(db,"RUNNING",baseline,settings)
 # First phase: numerically test entire domain; reject early if max error
 # already exceeds a conservative threshold. Overflow is recorded.
 for i,(ident,params) in enumerate(config_list):
  if time.monotonic()>=deadline:break
  row=db.execute("SELECT state FROM candidates WHERE id=?",(ident,)).fetchone()
  if row[0]!="NEW":continue
  print("K024 MODEL",i+1,"/",len(config_list),params,flush=True)
  try:
   prec=dataclasses.replace(default,**params)
   sample_max=min(args.max_x,8192)
   err,worst,checked,ok=screen(mod.relative_error,prec,sample_max,
                               args.batch_size,threshold)
   if ok and checked<args.max_x:
    err,worst,checked,ok=screen(mod.relative_error,prec,args.max_x,
                               args.batch_size,threshold)
   state="FULL_MODEL_PASS" if ok and checked==args.max_x else "MODEL_REJECT"
   put(db,ident,state=state,model_err=err,model_worst_x=worst,
       model_checked_x=checked,fail_reason=None if state=="FULL_MODEL_PASS" else "HEURISTIC_ERROR_LIMIT")
   print("K024 MODEL RESULT",ident,state,"ERR",err,"WORST_X",worst,flush=True)
  except Exception as ex:
   put(db,ident,state="OVERFLOW_OR_MODEL_ERROR",
       fail_reason=f"{type(ex).__name__}: {str(ex)[:250]}")
   print("K024 MODEL ERROR",ident,type(ex).__name__,str(ex)[:160],flush=True)
  if i%5==0:emit(db,"RUNNING",baseline,settings)
 # Second phase: build the most accurate numerical survivors first, plus
 # configurations with larger width reductions. Ranking is heuristic.
 rows=db.execute("""SELECT id,params,model_err FROM candidates
   WHERE state='FULL_MODEL_PASS' AND id!=?
   ORDER BY model_err ASC""",(base_id,)).fetchall()
 ranked=[]
 for ident,raw,err in rows:
  params=json.loads(raw)
  potential=sum(original[k]-params[k] for k in PARAMS)
  ranked.append((ident,params,err,potential))
 ranked.sort(key=lambda x:(-x[3],x[2]))
 # Preserve exploration: interleave accuracy and reduction frontiers.
 by_accuracy=sorted(ranked,key=lambda x:x[2])
 chosen=[];used=set()
 for i in range(max(len(ranked),len(by_accuracy))):
  for seq in (ranked,by_accuracy):
   if i<len(seq) and seq[i][0] not in used:
    used.add(seq[i][0]);chosen.append(seq[i])
  if len(chosen)>=args.max_builds:break
 chosen=chosen[:args.max_builds]
 for ident,params,error,red in chosen:
  if time.monotonic()>=deadline:break
  state=db.execute("SELECT state FROM candidates WHERE id=?",(ident,)).fetchone()[0]
  if state!="FULL_MODEL_PASS":continue
  try:
   circuit=mod.build_nr_circuit(10,prec=dataclasses.replace(default,**params))
   s=resources(circuit)
   c=proxy(s)
   if c>=proxy(baseline):
    put(db,ident,state="NO_RESOURCE_WIN",resources=compact(s),cost=c)
    continue
   file=RUN/(ident+".kmb")
   circuit.to_file(str(file),format="kmb")
   put(db,ident,state="BUILT",resources=compact(s),cost=c,
       file=str(file),file_sha=hash_file(file))
   print("K024 BUILD WIN",ident,"COST",c,"VS",proxy(baseline),flush=True)
  except Exception as e:
   put(db,ident,state="BUILD_ERROR",fail_reason=f"{type(e).__name__}: {str(e)[:300]}")
   print("K024 BUILD ERROR",ident,str(e)[:250],flush=True)
  emit(db,"RUNNING",baseline,settings)
 # Third phase: official verifier on best build wins.
 winners=db.execute("""SELECT id,params,file,cost,file_sha FROM candidates
   WHERE state IN ('BUILT','VERIFYING','VERIFIED_PARTIAL')
   ORDER BY cost ASC LIMIT ?""",(args.max_official_candidates,)).fetchall()
 for ident,raw,file,c,original_hash in winners:
  if time.monotonic()>=deadline:break
  f=Path(file)
  if not f.is_file() or hash_file(f)!=original_hash:
   put(db,ident,state="MISSING_OR_MUTATED_CIRCUIT");continue
  if db.execute("SELECT state FROM candidates WHERE id=?",(ident,)).fetchone()[0]=="VERIFIED_PARTIAL":
   continue
  put(db,ident,state="VERIFYING")
  survived=True
  for level in levels:
   if not survived or time.monotonic()>=deadline:break
   for seed in seeds:
    if time.monotonic()>=deadline:break
    previous=db.execute("""SELECT passed FROM verifications
                           WHERE id=? AND max_x=? AND seed=?""",(ident,level,seed)).fetchone()
    if previous:
     survived=bool(previous[0]);continue
    ref=db.execute("""SELECT passed,score FROM reference_checks WHERE max_x=? AND seed=?""",
                   (level,seed)).fetchone()
    if not ref:
     print("K024 REFERENCE OFFICIAL",level,seed,flush=True)
     vr=run_verifier(SAMPLE,level,seed,args.shots_per_x,args.verifier_timeout)
     score=vr.get("score")
     db.execute("INSERT OR REPLACE INTO reference_checks VALUES (?,?,?,?,?)",
        (level,seed,int(vr["passed"]),score,compact(vr)));db.commit()
     ref=(int(vr["passed"]),score)
    if not ref[0] or not isinstance(ref[1],(float,int)):
     put(db,ident,state="PAUSED_REFERENCE_VERIFIER_ERROR")
     survived=False;break
    print("K024 OFFICIAL",ident,level,seed,flush=True)
    result=run_verifier(f,level,seed,args.shots_per_x,args.verifier_timeout)
    score=result.get("score")
    passed=(result["passed"] and isinstance(score,(float,int)) and score<ref[1])
    db.execute("INSERT OR REPLACE INTO verifications VALUES (?,?,?,?,?,?,?)",
        (ident,level,seed,int(passed),score,
         result.get("worst_error_over_tolerance"),compact(result)))
    db.commit()
    print("K024 OFFICIAL RESULT",ident,level,"PASS",result["passed"],
          "SCORE_DELTA",score-ref[1] if isinstance(score,(int,float)) else None,
          "ERROR_RATIO",result.get("worst_error_over_tolerance"),flush=True)
    if not passed:survived=False;break
   emit(db,"RUNNING",baseline,settings)
  if survived and time.monotonic()<deadline:
   put(db,ident,state="VERIFIED_PARTIAL")
  else:
   state="OFFICIAL_REJECT" if any(row[0]==0 for row in db.execute(
       "SELECT passed FROM verifications WHERE id=?",(ident,))) else "VERIFYING"
   put(db,ident,state=state)
 final=emit(db,"STOPPED_TIME_BUDGET" if time.monotonic()>=deadline else "FINISHED",
            baseline,settings)
 print("K024 STATUS",final["status"],"COUNTS",final["state_counts"],flush=True)
 print("K024 REPORT",SUMMARY,"K024 SQLITE",DB,flush=True)
 db.close()
if __name__=="__main__":main()
