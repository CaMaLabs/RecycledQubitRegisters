#!/usr/bin/env python3
"""K017: independent staged official-verifier stress tests of K016 precision wins.

The Kaggle invsqrt verifier checks contiguous x=1..max_x. This script
increases max_x and varies seeds while holding verifier settings matched
between baseline and candidates. It records every pass/fail and stops
promoting candidates after a failed stage.

Passing an abbreviated max_x is NOT proof of full-domain correctness and
NOT an official Kaggle submission.
"""
import argparse, hashlib, json, subprocess, sys, time, traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
REFERENCE=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFIER=PRIVATE/"official/verifiers/invsqrt/verify_submission_invsqrt.py"
K016=HERE.parent/"k016/k016_precision_search.json"
REPORT=HERE/"k017_staged_verifier.json"

def digest(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def run(path, max_x, shots, seed, timeout):
 total=max_x*shots
 # A small fixed batch keeps memory and process-count bounded; require
 # exact divisibility, as the official verifier mandates.
 batch=min(256,total)
 while total%batch:batch-=1
 cmd=[sys.executable,str(VERIFIER),str(path),"--format","kmb",
  "--shots-per-x",str(shots),"--max-x",str(max_x),
  "--batch-size",str(batch),"--max-workers","1","--seed",str(seed)]
 started=time.monotonic()
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,
    cwd=str(VERIFIER.parent),check=False)
  try: output=json.loads(p.stdout)
  except json.JSONDecodeError:output={"error":"Non-JSON verifier output","stdout_tail":p.stdout[-1500:]}
  return {"passed":p.returncode==0 and output.get("status")=="PASS",
    "returncode":p.returncode,"seconds":round(time.monotonic()-started,2),
    "output":output,"stderr_tail":p.stderr[-1200:],
    "total_shots":total,"batch_size":batch}
 except subprocess.TimeoutExpired as exc:
  return {"passed":False,"timeout":True,
    "seconds":round(time.monotonic()-started,2),
    "total_shots":total,"batch_size":batch,
    "stdout_tail":str(exc.stdout)[-1000:]}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--cases",default="5,21,22")
 p.add_argument("--max-x-levels",default="32,128,512")
 p.add_argument("--seeds",default="12345,23456")
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--timeout-per-run",type=int,default=180)
 p.add_argument("--report",type=Path,default=REPORT)
 args=p.parse_args()
 cases=[int(s.strip()) for s in args.cases.split(",") if s.strip()]
 levels=[int(s.strip()) for s in args.max_x_levels.split(",") if s.strip()]
 seeds=[int(s.strip()) for s in args.seeds.split(",") if s.strip()]
 if (not cases or not levels or not seeds or args.shots_per_x<1 or args.timeout_per_run<1
     or any(x<1 for x in levels) or sorted(set(levels))!=levels
     or len(cases)>15 or len(levels)>10 or len(seeds)>10):
  p.error("Invalid cases/levels/seeds or budgets")
 if not K016.is_file() or not REFERENCE.is_file() or not VERIFIER.is_file():
  p.error("K016 report or official files missing")
 k016=json.loads(K016.read_text())
 trials={t["case"]:t for t in k016["trials"]}
 for c in cases:
  if c not in trials or "path" not in trials[c]:
   p.error(f"K016 case {c} has no generated candidate path")
 candidates={str(c):Path(trials[c]["path"]) for c in cases}
 for c,path in candidates.items():
  if not path.is_file():p.error(f"Missing case {c}: {path}")
  if digest(path)!=trials[int(c)]["sha256"]:
   p.error(f"K016 candidate case {c} SHA256 mismatch")
 data={"experiment":"K017_INVSQRT_PRECISION_STAGED_OFFICIAL_VERIFICATION",
  "status":"RUNNING","reference_sha256":digest(REFERENCE),
  "cases":{c:{"case":int(c),"changes":trials[int(c)]["changes"],
      "sha256":digest(path),"stages":[],"eligible":True}
      for c,path in candidates.items()},
  "stages":[],"settings":{"levels":levels,"seeds":seeds,
  "shots_per_x":args.shots_per_x,"timeout_per_run":args.timeout_per_run},
  "official_full_domain_verified":False,"kaggle_submitted":False,
  "limitations":["--max-x N covers only contiguous x=1..N, not the full verifier benchmark domain",
   "Changed circuit SHA can alter stochastic measurement trace even with a shared explicit seed",
   "Any FAIL disqualifies the candidate from promotion under this protocol",
   "PASS at tested levels is not a guarantee for untested inputs or seeds",
   "Test reduced precision at full domain or establish sound analytic error bounds before submission"]}
 def save():
  args.report.parent.mkdir(parents=True,exist_ok=True)
  args.report.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  for level in levels:
   for seed in seeds:
    if not any(row["eligible"] for row in data["cases"].values()):break
    print(f"K017 STAGE max_x={level} seed={seed} shots_per_x={args.shots_per_x}",flush=True)
    baseline=run(REFERENCE,level,args.shots_per_x,seed,args.timeout_per_run)
    stage={"max_x":level,"seed":seed,
     "reference":{"passed":baseline["passed"],"result":baseline["output"] if "output" in baseline else {},
                  "seconds":baseline["seconds"]},
     "candidates":[]}
    data["stages"].append(stage);save()
    if not baseline["passed"]:
     data["status"]="STOP_BASELINE_FAILURE_OR_TIMEOUT"
     print("K017 STOP baseline did not pass",baseline,flush=True)
     save();return
    for name,row in data["cases"].items():
     if not row["eligible"]:continue
     result=run(candidates[name],level,args.shots_per_x,seed,args.timeout_per_run)
     v=result.get("output",{})
     score_delta=(v.get("score")-baseline["output"]["score"]
          if result["passed"] and isinstance(v.get("score"),(int,float)) else None)
     entry={"max_x":level,"seed":seed,"passed":result["passed"],
            "score_delta":score_delta,"score":v.get("score"),
            "status":v.get("status"),"error":v.get("error"),
            "worst_error_over_tolerance":v.get("worst_error_over_tolerance"),
            "seconds":result["seconds"],"timed_out":result.get("timeout",False),
            "stderr_tail":result.get("stderr_tail","")}
     row["stages"].append(entry)
     stage["candidates"].append({"case":int(name),**entry})
     if not result["passed"] or score_delta is None or score_delta>=0:
      row["eligible"]=False
      row["disqualification"]="VERIFIER_FAILURE_OR_NO_SCORE_WIN"
     print("K017 CASE",name,"max_x",level,"seed",seed,
       "PASS",entry["passed"],"SCORE_DELTA",score_delta,
       "ERROR_RATIO",entry["worst_error_over_tolerance"],flush=True)
     save()
   else:continue
   break
  qualified=[name for name,row in data["cases"].items() if row["eligible"]]
  data["qualified_at_tested_levels"]=qualified
  data["status"]="PASS_STAGED_TESTED_LEVELS" if qualified else "NO_CANDIDATE_SURVIVED_STAGED_TESTS"
  save()
  print("K017 STATUS",data["status"])
  print("K017 SURVIVORS",qualified)
  print("K017 REPORT",args.report)
 except Exception:
  data["status"]="ERROR";data["traceback"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":main()
