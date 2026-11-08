#!/usr/bin/env python3
"""K025 independent checkpointed finalist verifier for K024 circuits.

Only scores circuits built in K024 and recorded with SHA256. Runs the
UNMODIFIED official Google inverse-square-root verifier on additional
input ranges and independent seeds. Read-only access to the K024 DB.
New results persisted only in private/runs/k025 and competition/k025.
This is a finite prefix-domain check, NOT proof of full benchmark acceptance.
"""
from __future__ import annotations
import argparse,hashlib,json,sqlite3,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
K024=PRIVATE/"runs/k024/search.sqlite3"
SAMPLE=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFIER=PRIVATE/"official/verifiers/invsqrt/verify_submission_invsqrt.py"
RUN=PRIVATE/"runs/k025"
DB=RUN/"verification.sqlite3"
REPORT=HERE/"k025_validation.json"

def sha(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def j(x):return json.dumps(x,sort_keys=True,separators=(",",":"))
def run(path,max_x,seed,shots,timeout):
 total=max_x*shots
 batch=min(total,256)
 while total%batch:batch-=1
 cmd=[sys.executable,str(VERIFIER),str(path),"--format","kmb",
      "--max-x",str(max_x),"--shots-per-x",str(shots),
      "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 started=time.monotonic()
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,check=False,
    timeout=timeout,cwd=str(VERIFIER.parent))
  try:data=json.loads(p.stdout)
  except json.JSONDecodeError:data={"status":"NON_JSON","tail":p.stdout[-1500:]}
  return {"pass":p.returncode==0 and data.get("status")=="PASS",
    "score":data.get("score"),"error_ratio":data.get("worst_error_over_tolerance"),
    "status":data.get("status"),"result":data,
    "elapsed_s":round(time.monotonic()-started,2),
    "exit_code":p.returncode,"stderr":p.stderr[-1500:]}
 except subprocess.TimeoutExpired:
  return {"pass":False,"timeout":True,"status":"TIMEOUT",
    "elapsed_s":round(time.monotonic()-started,2)}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--top",type=int,default=5)
 ap.add_argument("--levels",default="32768,65536")
 ap.add_argument("--seeds",default="12345,23456")
 ap.add_argument("--shots-per-x",type=int,default=2)
 ap.add_argument("--timeout-per-run",type=int,default=600)
 ap.add_argument("--hours",type=float,default=8)
 a=ap.parse_args()
 levels=[int(s) for s in a.levels.split(",") if s]
 seeds=[int(s) for s in a.seeds.split(",") if s]
 if not (1<=a.top<=30 and 1<=len(levels)<=8 and levels==sorted(set(levels)) and
    all(x>0 for x in levels) and 1<=len(seeds)<=8 and
    all(s>=0 for s in seeds) and 1<=a.shots_per_x<=16 and
    30<=a.timeout_per_run<=3600 and 0<a.hours<=72):
  ap.error("Invalid input budgets")
 if not K024.is_file() or not SAMPLE.is_file() or not VERIFIER.is_file():
  ap.error("Missing K024 run database or official verifier")
 original=sqlite3.connect(f"file:{K024}?mode=ro",uri=True,timeout=10)
 rows=original.execute("""SELECT id,params,file,file_sha,resources,cost,state
  FROM candidates WHERE state='VERIFIED_PARTIAL' ORDER BY cost ASC LIMIT ?""",
  (a.top,)).fetchall()
 original.close()
 if not rows:ap.error("No saved K024 VERIFIED_PARTIAL candidates")
 candidates={}
 for ident,params,path,expected,resources,cost,state in rows:
  file=Path(path)
  if not file.is_file():ap.error(f"Missing candidate file: {file}")
  if sha(file)!=expected:ap.error(f"SHA mismatch for candidate {ident}")
  candidates[ident]={"id":ident,"params":json.loads(params),
    "file":str(file),"sha256":expected,"resources":json.loads(resources),
    "cost_proxy":cost}
 RUN.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(DB,timeout=30)
 db.execute("PRAGMA journal_mode=WAL")
 db.execute("""CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT)""")
 db.execute("""CREATE TABLE IF NOT EXISTS tests(
  candidate TEXT,max_x INTEGER,seed INTEGER,pass INTEGER,score REAL,
  error_ratio REAL,result_json TEXT,
  PRIMARY KEY(candidate,max_x,seed))""")
 settings={"levels":levels,"seeds":seeds,"shots_per_x":a.shots_per_x,
           "reference_sha":sha(SAMPLE),"candidates":{k:v["sha256"] for k,v in candidates.items()}}
 existing=db.execute("SELECT value FROM metadata WHERE key='settings'").fetchone()
 if existing and json.loads(existing[0])!=settings:
  ap.error("K025 database uses different settings; archive private/runs/k025 to start a new independent protocol")
 db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)",("settings",j(settings)))
 db.commit()
 deadline=time.monotonic()+3600*a.hours
 def save(status):
  items=[]
  for ident,c in candidates.items():
   records=db.execute("""SELECT max_x,seed,pass,score,error_ratio,result_json
                  FROM tests WHERE candidate=? ORDER BY max_x,seed""",(ident,)).fetchall()
   tests=[{"max_x":x,"seed":seed,"pass":bool(ok),
     "score":score,"error_ratio":err,
     "details":json.loads(raw)} for x,seed,ok,score,err,raw in records]
   items.append({**c,"tests":tests,
       "highest_tested_pass":max([x["max_x"] for x in tests if x["pass"]],default=0),
       "failures":sum(not x["pass"] for x in tests),
       "complete":len(tests)==len(levels)*len(seeds)})
  doc={"experiment":"K025_K024_FINALISTS_INDEPENDENT_SEEDS",
       "status":status,"settings":settings,"candidates":items,
       "k024_modified":False,"full_domain_verified":False,"kaggle_submitted":False,
       "limitations":["A finite tested prefix is not the entire domain",
         "The official verifier's per-input accuracy and phase semantics govern actual pass",
         "Incomplete or timeout results are not proof of rejection",
         "A numerical model scan does not substitute for quantum circuit verification"]}
  REPORT.parent.mkdir(parents=True,exist_ok=True)
  temp=REPORT.with_suffix(".tmp");temp.write_text(json.dumps(doc,indent=2)+"\n")
  temp.replace(REPORT)
  return doc
 save("RUNNING")
 # Include reference for each stage/seed, caching it in this same DB.
 jobs=[(level,seed) for level in levels for seed in seeds]
 for level,seed in jobs:
  if time.monotonic()>=deadline:break
  refkey="__official_reference__"
  prior=db.execute("SELECT pass,score FROM tests WHERE candidate=? AND max_x=? AND seed=?",
                   (refkey,level,seed)).fetchone()
  if prior is None:
   print("K025 BASELINE",level,seed,flush=True)
   result=run(SAMPLE,level,seed,a.shots_per_x,a.timeout_per_run)
   prior=(int(result["pass"]),result.get("score"))
   db.execute("INSERT OR REPLACE INTO tests VALUES (?,?,?,?,?,?,?)",
     (refkey,level,seed,prior[0],prior[1],result.get("error_ratio"),j(result)))
   db.commit()
  if not prior[0] or not isinstance(prior[1],(float,int)):
   print("K025 STOP: baseline failed or timed out",level,seed,flush=True)
   break
  for ident,c in candidates.items():
   if time.monotonic()>=deadline:break
   if db.execute("""SELECT 1 FROM tests WHERE candidate=? AND pass=0""",(ident,)).fetchone():
    continue
   tested=db.execute("SELECT pass FROM tests WHERE candidate=? AND max_x=? AND seed=?",
      (ident,level,seed)).fetchone()
   if tested is not None:continue
   print("K025 CANDIDATE",ident,"X",level,"SEED",seed,flush=True)
   result=run(Path(c["file"]),level,seed,a.shots_per_x,a.timeout_per_run)
   score=result.get("score")
   accepted=bool(result["pass"] and isinstance(score,(int,float)) and score<prior[1])
   db.execute("INSERT OR REPLACE INTO tests VALUES (?,?,?,?,?,?,?)",
      (ident,level,seed,int(accepted),score,result.get("error_ratio"),j(result)))
   db.commit()
   print("K025 RESULT",ident,"X",level,"SEED",seed,
      "VERIFIER_PASS",result["pass"],"SCORE_DELTA",
      (score-prior[1] if isinstance(score,(int,float)) else None),
      "ERROR_RATIO",result.get("error_ratio"),flush=True)
   save("RUNNING")
 doc=save("BUDGET_REACHED" if time.monotonic()>=deadline else "COMPLETE")
 print("K025 STATUS",doc["status"])
 print("K025 REPORT",REPORT)
 db.close()

if __name__=="__main__":main()
