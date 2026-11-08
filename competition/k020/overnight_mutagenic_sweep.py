#!/usr/bin/env python3
"""K020 overnight mutagenic quantum compiler sweep (local, resumable, no spend).

Constructs combinations of the 5 precision widths from Google's *local*
official builder. Uses SQLite checkpoints, randomized deterministic ordering,
static Q*Toffoli pruning, an accuracy-margin promotion gate, escalating
OFFICIAL verifier tests and a retained Pareto/frontier of generated binaries.

No verifier source modification. No Kaggle submission. PASS on partial x
domains is NOT proof of full-domain behavior. Run unattended with nohup.
"""
import argparse,dataclasses,hashlib,importlib,itertools,json,os,random,sqlite3,subprocess,sys,time,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
VERIFIERS=PRIVATE/"official/verifiers"
OFFICIAL=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFY=VERIFIERS/"invsqrt/verify_submission_invsqrt.py"
OUT=PRIVATE/"runs/k020"
FIELDS=("delta_bits","coef_bits","square_bits","product_bits","result_bits")
def key(d):
 return ",".join(str(d[k]) for k in FIELDS)
def filehash(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def measure(c):
 s=c.operation_statistics()
 return {"qubits":int(c.num_qubits),"toffoli":int(s.num_toffoli_like),
 "instructions":int(s.num_instructions),"depth":int(c.reaction_depth()),
 "t_like":int(s.num_t_like)}
def verify(path,x,shots,seed,timeout):
 total=x*shots
 batch=min(256,total)
 while total%batch:batch-=1
 cmd=[sys.executable,str(VERIFY),str(path),"--format","kmb",
      "--shots-per-x",str(shots),"--max-x",str(x),
      "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 started=time.monotonic()
 try:
  p=subprocess.run(cmd,check=False,text=True,capture_output=True,
      cwd=str(VERIFIERS),timeout=timeout)
  try:j=json.loads(p.stdout)
  except Exception:j={"error":"invalid_json","stdout_tail":p.stdout[-1000:]}
  return {"ok":p.returncode==0 and j.get("status")=="PASS",
   "status":j.get("status"),"error":j.get("error"),"score":j.get("score"),
   "margin_ratio":j.get("worst_error_over_tolerance"),"seconds":round(time.monotonic()-started,2),
   "returncode":p.returncode,"stderr":p.stderr[-700:]}
 except subprocess.TimeoutExpired:
  return {"ok":False,"error":"TIMEOUT","seconds":round(time.monotonic()-started,2)}
def setup(db):
 db.executescript("""
 CREATE TABLE IF NOT EXISTS candidates(
  id TEXT PRIMARY KEY, knobs TEXT NOT NULL, status TEXT NOT NULL,
  qubits INT,toffoli INT,instructions INT,depth INT,
  proxy_delta REAL,artifact TEXT,sha256 TEXT,error TEXT,updated REAL
 );
 CREATE TABLE IF NOT EXISTS tests(
  candidate TEXT NOT NULL, level INT NOT NULL, seed INT NOT NULL,
  outcome TEXT NOT NULL, result TEXT NOT NULL,
  PRIMARY KEY(candidate,level,seed)
 );
 CREATE TABLE IF NOT EXISTS baselines(
  level INT NOT NULL, seed INT NOT NULL, result TEXT NOT NULL,
  PRIMARY KEY(level,seed)
 );
 """)
 db.commit()
def queryone(db,sql,args=()):
 return db.execute(sql,args).fetchone()
def save_candidate(db,ident,knobs,status,stats=None,proxy=None,path=None,sha=None,error=None):
 s=stats or {}
 db.execute("""INSERT OR REPLACE INTO candidates
 (id,knobs,status,qubits,toffoli,instructions,depth,proxy_delta,artifact,sha256,error,updated)
 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
 (ident,json.dumps(knobs,sort_keys=True),status,s.get("qubits"),s.get("toffoli"),
 s.get("instructions"),s.get("depth"),proxy,str(path) if path else None,sha,error,time.time()))
 db.commit()
def output_status(db,deadline,base_score=None):
 rows=db.execute("SELECT status,count(*) FROM candidates GROUP BY status").fetchall()
 best=db.execute("""SELECT id,proxy_delta,qubits,toffoli FROM candidates
 WHERE status IN ('STATIC_WIN','STAGE_PASS','SURVIVOR') ORDER BY proxy_delta ASC LIMIT 6""").fetchall()
 promoted=db.execute("SELECT candidate,level,outcome FROM tests ORDER BY level DESC LIMIT 8").fetchall()
 return {"utc_time":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
  "time_left_seconds":int(max(0,deadline-time.monotonic())),
  "candidate_counts":dict(rows),"best_static":best,
  "recent_stage_results":promoted,"reference_smoke_score":base_score,
  "full_domain_validated":False,"kaggle_submitted":False}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--hours",type=float,default=8)
 p.add_argument("--max-builds",type=int,default=650)
 p.add_argument("--max-reduction",type=int,default=3)
 p.add_argument("--max-stage-candidates",type=int,default=48)
 p.add_argument("--levels",default="32,256,2048,8192")
 p.add_argument("--seeds",default="12345,23456")
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--margin-limit",type=float,default=0.90)
 p.add_argument("--timeout-per-test",type=int,default=240)
 p.add_argument("--random-seed",type=int,default=20020)
 a=p.parse_args()
 if not 0<a.hours<=72 or not 1<=a.max_builds<=5000 or not 1<=a.max_reduction<=8:
  p.error("Invalid runtime or mutation budget")
 if not 1<=a.max_stage_candidates<=500 or not 0<a.margin_limit<=1:
  p.error("Invalid promotion budget")
 levels=[int(x) for x in a.levels.split(",")];seeds=[int(x) for x in a.seeds.split(",")]
 if any(x<=0 for x in levels+seeds) or sorted(set(levels))!=levels or not levels or not seeds:
  p.error("Levels must be ascending distinct positive integers; seeds positive")
 if a.shots_per_x<1 or a.timeout_per_test<1:p.error("Invalid shots/timeout")
 for path in (OFFICIAL,VERIFY):
  if not path.is_file():p.error(f"Missing official file {path}")
 OUT.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(str(OUT/"sweep.sqlite3"),timeout=30)
 db.execute("PRAGMA journal_mode=WAL")
 setup(db)
 # Lock the experiment parameters so reruns don't accidentally mix
 # two incompatible protocols into one checkpoint.
 protocol={"reference_sha":filehash(OFFICIAL),"levels":levels,"seeds":seeds,
 "shots":a.shots_per_x,"margin_limit":a.margin_limit,
 "max_reduction":a.max_reduction,"random_seed":a.random_seed}
 protocolfile=OUT/"protocol.json"
 if protocolfile.exists():
  if json.loads(protocolfile.read_text())!=protocol:
   p.error("Existing checkpoint uses a different protocol. Move private/runs/k020 aside before changing levels/seeds.")
 else:protocolfile.write_text(json.dumps(protocol,indent=2)+"\n")
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 module=importlib.import_module("invsqrt.nr_reference_circuit")
 base=module.Precision()
 initial={k:getattr(base,k) for k in FIELDS}
 from kickmix import Circuit
 baseline=measure(Circuit.from_file(str(OFFICIAL)))
 proxy0=baseline["qubits"]*baseline["toffoli"]
 deadline=time.monotonic()+a.hours*3600
 print("K020 START","hours",a.hours,"baseline",baseline,"parameters",initial,flush=True)
 rng=random.Random(a.random_seed)
 mutants=[]
 for offsets in itertools.product(range(a.max_reduction+1),repeat=len(FIELDS)):
  if all(v==0 for v in offsets):continue
  knobs={k:initial[k]-delta for k,delta in zip(FIELDS,offsets)}
  if any(v<2 for v in knobs.values()):continue
  mutants.append(knobs)
 rng.shuffle(mutants)
 # First inspect one-bit and two-bit changes, then explore deeper mutations.
 # Favors broad, safe search before aggressive precision collapse.
 mutants.sort(key=lambda d:(sum(initial[k]-d[k] for k in FIELDS),
                             sum((initial[k]-d[k])**2 for k in FIELDS)))
 built=0
 for knobs in mutants:
  if time.monotonic()>deadline or built>=a.max_builds:break
  ident=key(knobs)
  if queryone(db,"SELECT 1 FROM candidates WHERE id=?",(ident,)):continue
  built+=1
  try:
   obj=module.build_nr_circuit(10,prec=dataclasses.replace(base,**knobs))
   s=measure(obj)
   delta=s["qubits"]*s["toffoli"]-proxy0
   # Keep only actual resource wins; postpone expensive serialization until
   # the candidate enters the small verification beam.
   status="STATIC_WIN" if delta<0 and s["qubits"]<=baseline["qubits"] else "PRUNED_COST"
   save_candidate(db,ident,knobs,status,s,delta)
  except Exception as exc:
   save_candidate(db,ident,knobs,"BUILD_ERROR",error=f"{type(exc).__name__}: {exc}"[:500])
  if built%25==0:
   print("K020 BUILT",built,"OF",min(len(mutants),a.max_builds),
     "TIME_LEFT_MIN",round((deadline-time.monotonic())/60,1),flush=True)
 # Beam policy: rank by static resource savings, but include low-change
 # candidates so aggressive precision errors don't monopolize verification.
 rows=db.execute("""SELECT id,knobs,proxy_delta FROM candidates WHERE status
 IN ('STATIC_WIN','STAGE_PASS','SURVIVOR') ORDER BY proxy_delta ASC""").fetchall()
 picked=[];seen=set()
 diverse=sorted(rows,key=lambda r:(sum(initial[k]-json.loads(r[1])[k] for k in FIELDS),r[2]))
 for group in (rows[:a.max_stage_candidates//2],diverse,rows):
  for row in group:
   if len(picked)>=a.max_stage_candidates:break
   if row[0] not in seen:picked.append(row);seen.add(row[0])
  if len(picked)>=a.max_stage_candidates:break
 print("K020 STATIC SEARCH","new_builds",built,"static_wins",len(rows),
   "verification_beam",len(picked),flush=True)
 for ident,knob_json,delta in picked:
  if time.monotonic()>=deadline:break
  knobs=json.loads(knob_json)
  if queryone(db,"SELECT status FROM candidates WHERE id=?",(ident,))[0]=="SURVIVOR":continue
  path=OUT/("candidate_"+ident.replace(",","_")+".kmb")
  # Never trust pre-existing artefacts without checkpoint digest comparison.
  old=queryone(db,"SELECT artifact,sha256 FROM candidates WHERE id=?",(ident,))
  if not path.is_file() or not old or not old[1] or filehash(path)!=old[1]:
   try:
    obj=module.build_nr_circuit(10,prec=dataclasses.replace(base,**knobs))
    obj.to_file(str(path),format="kmb")
    s=measure(obj)
    save_candidate(db,ident,knobs,"STATIC_WIN",s,delta,path,filehash(path))
   except Exception as exc:
    save_candidate(db,ident,knobs,"BUILD_ERROR",error=f"{type(exc).__name__}: {exc}"[:500]);continue
  survived=True
  for level in levels:
   if not survived or time.monotonic()>=deadline:break
   for seed in seeds:
    if time.monotonic()>=deadline:break
    existing=queryone(db,"SELECT outcome,result FROM tests WHERE candidate=? AND level=? AND seed=?",
        (ident,level,seed))
    if existing:
     if existing[0]!="PASS":survived=False;break
     continue
    b=queryone(db,"SELECT result FROM baselines WHERE level=? AND seed=?",(level,seed))
    if b is None:
     baseline_result=verify(OFFICIAL,level,a.shots_per_x,seed,a.timeout_per_test)
     db.execute("INSERT INTO baselines VALUES(?,?,?)",(level,seed,json.dumps(baseline_result)));db.commit()
    else:baseline_result=json.loads(b[0])
    if not baseline_result["ok"]:
     print("K020 STOP: official baseline failure/timeout",level,seed,baseline_result,flush=True)
     survived=False
     break
    ans=verify(path,level,a.shots_per_x,seed,a.timeout_per_test)
    if ans["ok"] and isinstance(ans.get("score"),(int,float)):
     ans["delta"]=ans["score"]-baseline_result["score"]
    ok=(ans["ok"] and ans.get("delta",0)<0
       and isinstance(ans.get("margin_ratio"),(int,float))
       and ans["margin_ratio"]<=a.margin_limit)
    state="PASS" if ok else "FAIL"
    db.execute("INSERT INTO tests VALUES(?,?,?,?,?)",(ident,level,seed,state,json.dumps(ans)));db.commit()
    print("K020 TEST",ident,"max_x",level,"seed",seed,"status",state,
      "delta",ans.get("delta"),"error_ratio",ans.get("margin_ratio"),flush=True)
    if not ok:survived=False;break
   if not survived:break
  current=queryone(db,"SELECT qubits,toffoli,instructions,depth,artifact,sha256 FROM candidates WHERE id=?",(ident,))
  if current:
   s={"qubits":current[0],"toffoli":current[1],"instructions":current[2],"depth":current[3]}
   save_candidate(db,ident,knobs,"SURVIVOR" if survived and time.monotonic()<deadline
      else "STAGE_PASS" if survived else "REJECTED_STAGE",s,delta,Path(current[4]) if current[4] else None,current[5])
 # Keep summary and all candidates in SQLite; no private binaries in Git.
 status=output_status(db,deadline)
 status["protocol"]=protocol
 status["status"]="OVERNIGHT_BUDGET_REACHED" if time.monotonic()>=deadline else "SEARCH_PASS_COMPLETE"
 (OUT/"status.json").write_text(json.dumps(status,indent=2)+"\n")
 print("K020 STATUS",status["status"],flush=True)
 print("K020 CANDIDATES",status["candidate_counts"],flush=True)
 print("K020 BEST",status["best_static"],flush=True)
 print("K020 DATABASE",OUT/"sweep.sqlite3",flush=True)
 print("K020 SUMMARY",OUT/"status.json",flush=True)
if __name__=="__main__":main()
