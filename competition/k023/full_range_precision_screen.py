#!/usr/bin/env python3
"""K023: checkpointed deterministic full-range precision screening.

Calls the OFFICIAL local invsqrt.nr_reference_circuit.relative_error model for
many x at once, independently for each immutable Precision configuration.

This is a screening experiment, NOT the official circuit verifier. A model
PASS is never a Kaggle acceptance or quantum-phase equivalence claim.
The input bound is caller-selected; do not mistake a chosen bound for the
official entire domain without verifying the actual verifier specification.

Read-only K016 and K020 intake; distinct K023 SQLite database and reports.
Resume safely after a disconnect/restart. No internet, payments, QPU or
Kaggle submissions. Intended to be run concurrently with K020 under a modest
CPU/IO budget.
"""
from __future__ import annotations
import argparse,dataclasses,hashlib,importlib,json,math,sqlite3,sys,time,traceback
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
VERIFIERS=PRIVATE/"official/verifiers"
K016=HERE.parent/"k016/k016_precision_search.json"
K020_DB=PRIVATE/"runs/k020/search.sqlite3"
WORK=PRIVATE/"runs/k023"
DBFILE=WORK/"model_sweep.sqlite3"
REPORT=HERE/"k023_precision_frontier.json"
PARAMS=("delta_bits","coef_bits","square_bits","product_bits","result_bits")

def encoding(o):return json.dumps(o,sort_keys=True,separators=(",",":"))
def key_for(d):return hashlib.sha256(encoding(d).encode()).hexdigest()[:20]

def open_database(path):
 db=sqlite3.connect(path,timeout=20)
 db.execute("PRAGMA journal_mode=WAL")
 db.execute("PRAGMA busy_timeout=20000")
 db.execute("""CREATE TABLE IF NOT EXISTS jobs(
 id TEXT PRIMARY KEY, params TEXT NOT NULL, sources TEXT,
 x_end INTEGER NOT NULL DEFAULT 0, n_evaluated INTEGER NOT NULL DEFAULT 0,
 max_abs_relative_error REAL, x_at_max INTEGER, rms_sum REAL NOT NULL DEFAULT 0,
 n_nonfinite INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL DEFAULT 'PENDING', error TEXT, updated REAL)""")
 db.execute("""CREATE TABLE IF NOT EXISTS metadata(
 key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
 db.commit()
 return db

def intake(defaults, from_k016, from_k020, k020_limit):
 configs={}
 def add(config,source):
  try:values={k:int(config[k]) for k in PARAMS}
  except (KeyError,TypeError,ValueError):return
  if any(v<2 for v in values.values()):return
  cid=key_for(values)
  if cid not in configs:configs[cid]={"params":values,"sources":[]}
  if source not in configs[cid]["sources"]:configs[cid]["sources"].append(source)
 add(defaults,"reference")
 if from_k016 and K016.is_file():
  d=json.loads(K016.read_text())
  for row in d.get("trials",[]):
   if row.get("resources") is not None:
    values={**defaults,**row["changes"]}
    add(values,f"k016_case_{row['case']}")
 if from_k020 and K020_DB.is_file():
  # A read-only connection prevents blocking or writing to the live
  # overnight mutation database.
  try:
   db=sqlite3.connect(f"file:{K020_DB}?mode=ro",uri=True,timeout=3)
   rows=db.execute("""SELECT config,id,status FROM candidates
      WHERE status NOT IN ('BUILD_ERROR','WORKER_ERROR','EXPORT_FAILED')
      ORDER BY CASE WHEN status='STAGED_SMOKE_PASS_NOT_FULL_DOMAIN'
               THEN 0 WHEN status='STATIC_WIN' THEN 1 ELSE 2 END,
               proxy ASC LIMIT ?""",(k020_limit,)).fetchall()
   for raw,cid,status in rows:
    try:add(json.loads(raw),f"k020_{cid}_{status}")
    except json.JSONDecodeError:pass
   db.close()
  except sqlite3.Error as e:
   print("K023 NOTE: K020 intake unavailable:",e,flush=True)
 return configs

def update_row(db,cid,**updates):
 names=list(updates)
 db.execute("UPDATE jobs SET "+", ".join(f"{k}=?" for k in names)+
            " WHERE id=?",(*[updates[k] for k in names],cid))
 db.commit()

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--max-x",type=int,default=3_133_452,
   help="Inclusive deterministic input bound, NOT asserted official full-domain size")
 ap.add_argument("--batch-size",type=int,default=8192,
   help="Numerical samples per vectorized call; lower for memory/CPU constraints")
 ap.add_argument("--max-configs",type=int,default=60)
 ap.add_argument("--k020-limit",type=int,default=80)
 ap.add_argument("--hours",type=float,default=6)
 ap.add_argument("--relative-tolerance",type=float,
   help="Optional explicit relative-error threshold; leave unset for observational results")
 ap.add_argument("--skip-k016",action="store_true")
 ap.add_argument("--skip-k020",action="store_true")
 ap.add_argument("--report",type=Path,default=REPORT)
 a=ap.parse_args()
 if not (1<=a.max_x<=100_000_000 and 64<=a.batch_size<=1_000_000
         and 1<=a.max_configs<=1000 and 0<=a.k020_limit<=10000
         and 0<a.hours<=72):
  ap.error("Invalid search limits")
 if a.relative_tolerance is not None and (not math.isfinite(a.relative_tolerance) or a.relative_tolerance<=0):
  ap.error("Relative tolerance must be positive and finite")
 if not VERIFIERS.is_dir():ap.error("K001 local official verifier directory missing")
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 module=importlib.import_module("invsqrt.nr_reference_circuit")
 default=module.Precision()
 defaults={k:int(getattr(default,k)) for k in PARAMS}
 if not dataclasses.is_dataclass(default):ap.error("Official Precision is not a dataclass")
 WORK.mkdir(parents=True,exist_ok=True)
 db=open_database(DBFILE)
 criteria={"max_x_inclusive":a.max_x,"model":"invsqrt.nr_reference_circuit.relative_error",
           "n_p":10,"batch_size":a.batch_size,
           "relative_tolerance":a.relative_tolerance}
 old=db.execute("SELECT value FROM metadata WHERE key='criteria'").fetchone()
 if old and json.loads(old[0])!=criteria:
  ap.error("Existing K023 database uses different max-x/batch/tolerance; archive private/runs/k023 first")
 db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)",("criteria",encoding(criteria)))
 configs=intake(defaults,not a.skip_k016,not a.skip_k020,a.k020_limit)
 # Baseline first, then known validated partial-domain candidates, then
 # all available configurations. No claim model means verifier-correct.
 def priority(item):
  config=item[1]["params"]
  changes=sum(config[k]!=defaults[k] for k in PARAMS)
  source=item[1]["sources"]
  seeds=0 if "reference" in source else (1 if any(x in source for x in ("k016_case_10","k016_case_21","k016_case_7","k016_case_13")) else 2)
  return (seeds,changes,sum(defaults[k]-config[k] for k in PARAMS))
 ordered=sorted(configs.items(),key=priority)[:a.max_configs]
 for cid,item in ordered:
  db.execute("""INSERT OR IGNORE INTO jobs
    (id,params,sources,status,updated) VALUES (?,?,?,?,?)""",
    (cid,encoding(item["params"]),encoding(item["sources"]),"PENDING",time.time()))
 db.commit()
 deadline=time.monotonic()+a.hours*3600
 print("K023 INPUT BOUND",a.max_x,"CONFIGS",len(ordered),"BATCH",a.batch_size,flush=True)
 print("K023 NOTE this is model screening, not full official circuit verification",flush=True)
 def write_report(status):
  rows=db.execute("""SELECT id,params,sources,x_end,n_evaluated,
   max_abs_relative_error,x_at_max,rms_sum,n_nonfinite,status,error
   FROM jobs ORDER BY CASE WHEN status='DONE' THEN 0 ELSE 1 END,
   max_abs_relative_error ASC""").fetchall()
  values=[]
  for cid,params,sources,end,count,maxerr,where,rms,nonfinite,s,e in rows:
   item={"id":cid,"params":json.loads(params),
       "sources":json.loads(sources or "[]"),
       "tested_through_x":end,"samples":count,
       "max_abs_relative_error":maxerr,"worst_x":where,
       "rms_relative_error":math.sqrt(rms/count) if count else None,
       "nonfinite_samples":nonfinite,"status":s,"error":e}
   if a.relative_tolerance is not None and s=="DONE":
    item["within_user_supplied_relative_tolerance_on_tested_domain"]=(
      nonfinite==0 and maxerr is not None and maxerr<=a.relative_tolerance)
   values.append(item)
  output={"experiment":"K023_DETERMINISTIC_PRECISION_FRONTIER","status":status,
       "criteria":criteria,"default_precision":defaults,
       "total_configurations":len(rows),
       "finished":sum(x["status"]=="DONE" for x in values),
       "full_domain_verified":False,"kaggle_submitted":False,
       "disclaimer":"Chosen x bound and deterministic relative_error model do NOT establish official full-domain phase/circuit correctness.",
       "candidates":values}
  a.report.parent.mkdir(parents=True,exist_ok=True)
  tmp=a.report.with_suffix(".tmp")
  tmp.write_text(json.dumps(output,indent=2)+"\n")
  tmp.replace(a.report)
  return output
 try:
  write_report("RUNNING")
  for cid,_ in ordered:
   if time.monotonic()>=deadline:break
   row=db.execute("SELECT params,x_end,n_evaluated,max_abs_relative_error,x_at_max,rms_sum,n_nonfinite,status FROM jobs WHERE id=?",(cid,)).fetchone()
   raw,start,count,max_error,max_x_seen,sumsq,nonfinite,status=row
   if status=="DONE":continue
   prec=dataclasses.replace(default,**json.loads(raw))
   if status=="ERROR":
    print("K023 SKIP failed",cid,flush=True);continue
   print("K023 START",cid,json.loads(raw),"RESUME",start,flush=True)
   try:
    for offset in range(start+1,a.max_x+1,a.batch_size):
     if time.monotonic()>=deadline:break
     end=min(a.max_x,offset+a.batch_size-1)
     xs=np.arange(offset,end+1,dtype=np.int64)
     values=np.asarray(module.relative_error(10,prec,xs))
     if values.shape!=xs.shape:
      raise RuntimeError(f"Model returned shape {values.shape}, expected {xs.shape}")
     if values.dtype.kind not in "fi":
      raise RuntimeError(f"Model returned unexpected dtype {values.dtype}")
     valid=np.isfinite(values)
     n_invalid=int((~valid).sum())
     nonfinite+=n_invalid
     if valid.any():
      abs_error=np.abs(values[valid].astype(np.float64))
      arg=int(np.argmax(abs_error))
      highest=float(abs_error[arg])
      if max_error is None or highest>max_error:
       max_error=highest
       max_x_seen=int(xs[valid][arg])
      sumsq+=float(np.dot(abs_error,abs_error))
     count+=len(xs)
     start=end
     update_row(db,cid,x_end=start,n_evaluated=count,
       max_abs_relative_error=max_error,x_at_max=max_x_seen,rms_sum=sumsq,
       n_nonfinite=nonfinite,status="RUNNING",updated=time.time())
     if end==a.max_x or end%max(a.batch_size*32,1)==0:
      print("K023 PROGRESS",cid,"x",end,"max_error",max_error,
          "worst_x",max_x_seen,"nonfinite",nonfinite,flush=True)
    if start==a.max_x:
     update_row(db,cid,status="DONE",updated=time.time())
     print("K023 DONE",cid,"max_error",max_error,
           "worst_x",max_x_seen,flush=True)
    write_report("RUNNING")
   except Exception as e:
    update_row(db,cid,status="ERROR",
      error=f"{type(e).__name__}: {str(e)[:750]}",updated=time.time())
    print("K023 ERROR",cid,repr(e),flush=True)
    write_report("RUNNING")
  out=write_report("COMPLETE" if all(x[0]=="DONE" for x in
       db.execute("SELECT status FROM jobs").fetchall()) else "PAUSED_BUDGET_OR_PARTIAL")
  print("K023 STATUS",out["status"],"FINISHED",out["finished"],flush=True)
  print("K023 REPORT",a.report,flush=True)
  print("K023 DATABASE",DBFILE,flush=True)
 finally:
  db.close()
if __name__=="__main__":main()
