#!/usr/bin/env python3
"""K004: official inverse-square-root verifier smoke baseline and gate API reconnaissance.

Runs the *unmodified* official sample through Google's own verifier (with
small explicit shot count), records exit status/output, and emits safe
kickmix format / API metadata. Smoke testing is NOT official scoring.
No candidate edits, no submission, no large DQI circuit loading.
"""
import argparse,hashlib,inspect,json,os,re,subprocess,sys,time,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
OFFICIAL=(HERE/"../k001/private/official").resolve()
SAMPLE=OFFICIAL/"sample_submission/invsqrt.kmb"
VERIFIER=OFFICIAL/"verifiers/invsqrt/verify_submission_invsqrt.py"
REPORT=HERE/"k004_invsqrt_baseline.json"

def invoke(argv,limit):
 start=time.monotonic()
 try:
  run=subprocess.run(argv,timeout=limit,check=False,capture_output=True,text=True,
   cwd=str(OFFICIAL),env={**os.environ,"PYTHONUNBUFFERED":"1"})
  return {"command_argv":argv,"return_code":run.returncode,"elapsed_seconds":round(time.monotonic()-start,3),
   "stdout_tail":run.stdout[-9000:],"stderr_tail":run.stderr[-9000:],
   "timed_out":False}
 except subprocess.TimeoutExpired as e:
  def dec(s):
   if isinstance(s,bytes):return s.decode(errors="replace")[-9000:]
   return (s or "")[-9000:]
  return {"command_argv":argv,"timed_out":True,"elapsed_seconds":round(time.monotonic()-start,3),
   "stdout_tail":dec(e.stdout),"stderr_tail":dec(e.stderr)}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--timeout",type=int,default=180)
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--max-x",type=int,default=8)
 p.add_argument("--full-baseline",action="store_true",help="Run verifier defaults instead of smoke parameters")
 p.add_argument("--output",default=str(REPORT))
 a=p.parse_args()
 if a.timeout<10 or a.shots_per_x<1 or a.max_x<1:p.error("invalid smoke limits")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"K004_KICKMIX_OFFICIAL_INVSQRT_BASELINE_SMOKE","status":"IN_PROGRESS",
    "sample_mutated":False,"is_official_score":False,"competition_submitted":False,
    "official_verifier":str(VERIFIER.relative_to(OFFICIAL)),
    "sample":str(SAMPLE.relative_to(OFFICIAL))}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 if not SAMPLE.exists() or not VERIFIER.exists():raise SystemExit("Missing K001 downloaded assets")
 try:
  with SAMPLE.open("rb") as f:d["reference_sha256_before"]=hashlib.file_digest(f,"sha256").hexdigest()
  import kickmix as km
  d["kickmix_location"]=str(getattr(km,"__file__",None))
  d["public_symbols"]=[x for x in dir(km) if not x.startswith("_")]
  d["circuit_methods"]=[x for x in dir(km.Circuit) if not x.startswith("_")]
  d["builder_methods"]=[x for x in dir(km.CircuitBuilder) if not x.startswith("_")]
  d["builder_signature"]=(str(inspect.signature(km.CircuitBuilder)) if hasattr(km.CircuitBuilder,"__signature__") else "native extension: unavailable")
  d["file_signatures"]={}
  for name in ("from_file","to_file","text_diagram","operation_statistics","reaction_depth"):
   obj=getattr(km.Circuit,name,None)
   if obj is None:continue
   try:sig=str(inspect.signature(obj))
   except Exception:sig="native extension: unavailable"
   d["file_signatures"][name]={"signature":sig,"doc":(inspect.getdoc(obj) or "")[:2000]}
  print("K004 REFERENCE SHA256",d["reference_sha256_before"],flush=True)
  help_cmd=[sys.executable,str(VERIFIER),"--help"]
  d["verifier_help"]=invoke(help_cmd,min(a.timeout,40))
  print("K004 HELP EXIT",d["verifier_help"].get("return_code"),
   "TIMEOUT",d["verifier_help"]["timed_out"],flush=True)
  print("K004 HELP TAIL",d["verifier_help"]["stdout_tail"][-3000:],
   d["verifier_help"]["stderr_tail"][-1000:],flush=True)
  cmd=[sys.executable,str(VERIFIER),str(SAMPLE),"--format","kmb"]
  if not a.full_baseline:
   # Official verifier requires total shots divisible by batch_size.
   total=a.shots_per_x*a.max_x
   batch=min(256,total)
   while total%batch:batch-=1
   cmd+=["--shots-per-x",str(a.shots_per_x),"--max-x",str(a.max_x),
     "--batch-size",str(batch),"--max-workers","1"]
   d["smoke_batch_size"]=batch
   d["smoke_total_shots"]=total
  d["verification_mode"]="FULL_VERIFIER_DEFAULTS" if a.full_baseline else "REDUCED_SHOTS_SMOKE"
  d["verification"]=invoke(cmd,a.timeout)
  result=d["verification"]
  print("K004 VERIFIER",d["verification_mode"],"EXIT",result.get("return_code"),
    "TIMEOUT",result["timed_out"],flush=True)
  print("K004 OUTPUT",result["stdout_tail"][-3500:],flush=True)
  print("K004 STDERR",result["stderr_tail"][-2000:],flush=True)
  with SAMPLE.open("rb") as f:d["reference_sha256_after"]=hashlib.file_digest(f,"sha256").hexdigest()
  if d["reference_sha256_before"]!=d["reference_sha256_after"]:
   raise AssertionError("Official reference was unexpectedly modified")
  if result["timed_out"]:d["status"]="BASELINE_VERIFIER_TIMEOUT"
  elif result.get("return_code")==0:d["status"]="PASS_OFFICIAL_REFERENCE_VERIFIER_SMOKE" if not a.full_baseline else "PASS_OFFICIAL_REFERENCE_VERIFIER_DEFAULTS"
  else:d["status"]="BASELINE_VERIFIER_ERROR"
  save();print("K004 STATUS",d["status"],"REPORT",out,flush=True)
 except Exception:
  d["status"]="K004_ERROR";d["error"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":main()
