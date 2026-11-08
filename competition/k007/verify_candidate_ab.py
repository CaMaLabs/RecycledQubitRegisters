#!/usr/bin/env python3
"""K007: matched-seed official Kaggle invsqrt verifier A/B comparison.

Runs both unmodified reference and K006 candidate through the official
verifier with identical arguments. Records output in a local experiment
report; does not submit to Kaggle or change reference assets.

Smoke verification is not equivalent to the full 200M-shot benchmark.
"""
import argparse,hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
REFERENCE=PRIVATE/"official/sample_submission/invsqrt.kmb"
CANDIDATE=PRIVATE/"runs/k006/candidate.kmb"
VERIFIER=PRIVATE/"official/verifiers/invsqrt/verify_submission_invsqrt.py"
DEFAULT_REPORT=HERE/"k007_ab_report.json"

def digest(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def invoke(name,path,args):
 cmd=[sys.executable,str(VERIFIER),str(path),"--format","kmb",
      "--shots-per-x",str(args.shots_per_x),"--max-x",str(args.max_x),
      "--batch-size",str(args.batch_size),"--max-workers","1",
      "--seed",str(args.seed)]
 started=time.monotonic()
 try:
  cp=subprocess.run(cmd,text=True,capture_output=True,
    timeout=args.timeout,check=False,cwd=str(VERIFIER.parent))
  row={"name":name,"returncode":cp.returncode,"timeout":False,
       "seconds":round(time.monotonic()-started,3),
       "stdout_tail":cp.stdout[-12000:],"stderr_tail":cp.stderr[-6000:],
       "sha256":digest(path)}
  try:row["verifier"]=json.loads(cp.stdout)
  except json.JSONDecodeError:row["parse_error"]="verifier stdout is not standalone JSON"
 except subprocess.TimeoutExpired as exc:
  row={"name":name,"returncode":None,"timeout":True,
       "seconds":round(time.monotonic()-started,3),
       "stdout_tail":(exc.stdout or b"").decode(errors="replace")[-12000:] if isinstance(exc.stdout,bytes) else (exc.stdout or "")[-12000:],
       "stderr_tail":(exc.stderr or b"").decode(errors="replace")[-6000:] if isinstance(exc.stderr,bytes) else (exc.stderr or "")[-6000:],
       "sha256":digest(path)}
 return row

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--max-x",type=int,default=8)
 p.add_argument("--batch-size",type=int,default=16)
 p.add_argument("--seed",type=int,default=12345)
 p.add_argument("--timeout",type=int,default=180)
 p.add_argument("--report",default=str(DEFAULT_REPORT))
 args=p.parse_args()
 if min(args.shots_per_x,args.max_x,args.batch_size,args.timeout)<1:
  p.error("shots, max-x, batch-size and timeout must be positive")
 total=args.shots_per_x*args.max_x
 if total%args.batch_size:p.error(f"total shots {total} not divisible by batch-size {args.batch_size}")
 for path in (REFERENCE,CANDIDATE,VERIFIER):
  if not path.is_file():p.error(f"missing local file: {path}")
 report=Path(args.report);report.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"K007_OFFICIAL_VERIFIER_MATCHED_SEED_AB",
       "status":"IN_PROGRESS","submitted_to_kaggle":False,
       "full_official_score":False,
       "settings":{"seed":args.seed,"shots_per_x":args.shots_per_x,
         "max_x":args.max_x,"batch_size":args.batch_size,
         "total_shots":total,"max_workers":1},
       "limitations":["Small-shot functional smoke test, not exhaustive equivalence",
         "Seed equality alone does not force identical internal shot trajectories when circuit hashes differ",
         "Positive local verifier result is not a Kaggle acceptance receipt"]}
 def save():report.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  for label,path in (("baseline",REFERENCE),("candidate",CANDIDATE)):
   print(f"K007 RUN {label.upper()} ...",flush=True)
   row=invoke(label,path,args)
   data[label]=row
   v=row.get("verifier",{})
   print(f"K007 {label.upper()} exit={row['returncode']} timeout={row['timeout']} "
         f"status={v.get('status')} score={v.get('score')} "
         f"toffoli={v.get('toffoli_count')} Q={v.get('num_qubits')}",flush=True)
   if row["returncode"]!=0 or v.get("status")!="PASS":
    print("K007 VERIFIER OUTPUT",row.get("stdout_tail","")[-2500:],flush=True)
    print("K007 VERIFIER ERROR",row.get("stderr_tail","")[-1500:],flush=True)
   save()
   if row["returncode"]!=0 or v.get("status")!="PASS":
    data["status"]="FAIL_"+label.upper()+"_VERIFIER"
    save()
    print("K007 STATUS",data["status"],"REPORT",report,flush=True)
    return 1
  base=data["baseline"]["verifier"]
  cand=data["candidate"]["verifier"]
  data["comparison"]={}
  for key in ("score","toffoli_equivalent","toffoli_count","t_count",
              "rotation_count","num_qubits","reaction_depth","num_ops",
              "worst_error_over_tolerance"):
   if isinstance(base.get(key),(int,float)) and isinstance(cand.get(key),(int,float)):
    data["comparison"][key]={"reference":base[key],"candidate":cand[key],
      "delta":cand[key]-base[key]}
  sb=base.get("score");sc=cand.get("score")
  if sb is None or sc is None:
   data["status"]="PASS_BOTH_WITHOUT_SCORE"
  elif sc<sb:
   data["status"]="PASS_BOTH_SCORE_IMPROVED"
  elif sc==sb:
   data["status"]="PASS_BOTH_SCORE_UNCHANGED"
  else:
   data["status"]="PASS_BOTH_SCORE_REGRESSED"
  save()
  print("K007 SCORE DELTA",data["comparison"].get("score"),flush=True)
  print("K007 STATUS",data["status"],"REPORT",report,flush=True)
  return 0
 except Exception:
  data["status"]="ERROR"
  data["error"]=traceback.format_exc()[-7000:]
  save();raise

if __name__=="__main__":sys.exit(main())
