#!/usr/bin/env python3
"""K016: accuracy-constrained precision-width search for official invsqrt.

Load the actual official reference builder, discover its Precision dataclass
parameters, construct narrower candidate arithmetic circuits, then
independently verify any static-cost wins with Google's own phase/function
verifier. All source and generated candidate binaries remain in private/.

The 16-shot smoke test is NOT the full competition benchmark. Do not submit
smoke-only candidates or call them fully verified.
"""
import argparse,dataclasses,hashlib,importlib,json,subprocess,sys,traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PRIVATE=(ROOT/"../k001/private").resolve()
VERIFIERS=PRIVATE/"official/verifiers"
OFFICIAL=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFY=VERIFIERS/"invsqrt/verify_submission_invsqrt.py"
RUN=PRIVATE/"runs/k016"
REPORT=ROOT/"k016_precision_search.json"

def sha256(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def resource(c):
 s=c.operation_statistics()
 return {"qubits":int(c.num_qubits),"bits":int(c.num_bits),
    "toffoli_like":int(s.num_toffoli_like),"t_like":int(s.num_t_like),
    "instructions":int(s.num_instructions),
    "reaction_depth":int(c.reaction_depth())}
def verify(p,args):
 cmd=[sys.executable,str(VERIFY),str(p),"--format","kmb",
      "--shots-per-x",str(args.shots_per_x),"--max-x",str(args.max_x),
      "--batch-size",str(args.batch_size),"--max-workers","1",
      "--seed",str(args.seed)]
 try:
  run=subprocess.run(cmd,check=False,capture_output=True,text=True,timeout=args.timeout,cwd=str(VERIFIERS))
  try:value=json.loads(run.stdout)
  except json.JSONDecodeError:value={"parse_error":run.stdout[-2000:]}
  return {"pass":run.returncode==0 and value.get("status")=="PASS",
    "exit_code":run.returncode,"result":value,"stderr_tail":run.stderr[-1600:]}
 except subprocess.TimeoutExpired:
  return {"pass":False,"timed_out":True}
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--max-candidates",type=int,default=25)
 a.add_argument("--max-verifications",type=int,default=6)
 a.add_argument("--max-reduction",type=int,default=3)
 a.add_argument("--shots-per-x",type=int,default=2)
 a.add_argument("--max-x",type=int,default=8)
 a.add_argument("--batch-size",type=int,default=16)
 a.add_argument("--seed",type=int,default=12345)
 a.add_argument("--timeout",type=int,default=180)
 a.add_argument("--report",type=Path,default=REPORT)
 args=a.parse_args()
 if not 1<=args.max_candidates<=100 or not 0<=args.max_verifications<=20 or not 1<=args.max_reduction<=8:
  a.error("Candidate budget out of range")
 if min(args.shots_per_x,args.max_x,args.batch_size,args.timeout)<1 or (args.shots_per_x*args.max_x)%args.batch_size:
  a.error("Invalid shot or batch settings")
 if not OFFICIAL.is_file() or not VERIFY.is_file():a.error("K001 official files not found")
 RUN.mkdir(parents=True,exist_ok=True)
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 module=importlib.import_module("invsqrt.nr_reference_circuit")
 Precision=module.Precision
 if not dataclasses.is_dataclass(Precision):a.error("Official Precision is not a dataclass")
 base=Precision()
 fields={f.name:getattr(base,f.name) for f in dataclasses.fields(base) if f.init}
 from kickmix import Circuit
 ref=Circuit.from_file(str(OFFICIAL))
 baseline=resource(ref)
 score_proxy=lambda s:s["qubits"]*s["toffoli_like"]
 reference_sha=sha256(OFFICIAL)
 data={"experiment":"K016_REFERENCE_PRECISION_PARAMETER_SEARCH",
  "status":"RUNNING","submitted":False,"full_official_verification":False,
  "reference":{"resources":baseline,"sha256":reference_sha},
  "precision_defaults":{k:(v if isinstance(v,(str,float,int,bool,type(None))) else str(v)) for k,v in fields.items()},
  "hypothesis":"Narrower precision/working widths may reduce qubits or Toffoli count",
  "search_policy":"one parameter at a time, descending reductions, then paired reductions with separate verifier",
  "trials":[],"verification_settings":{"shots_per_x":args.shots_per_x,"max_x":args.max_x,
   "batch_size":args.batch_size,"seed":args.seed},
  "limitations":["Do not assume reduced precision preserves the required error tolerance",
   "Only the official verifier determines whether a candidate is accepted on tested shots",
   "Smoke pass does not imply full-domain validity, so do not submit a smoke-only result",
   "Avoid changing the verifier or its specified acceptance parameters"]}
 def save():
  args.report.parent.mkdir(parents=True,exist_ok=True)
  args.report.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  built=module.build_nr_circuit(10,prec=base)
  data["rebuilt_reference"]=resource(built)
  if data["rebuilt_reference"]!=baseline:
   data["status"]="FAIL_REFERENCE_BUILD_MISMATCH";save()
   print("K016 STATUS",data["status"],data["rebuilt_reference"],baseline,flush=True)
   return
  print("K016 REFERENCE",baseline,flush=True)
  print("K016 PRECISION FIELDS",data["precision_defaults"],flush=True)
  target_names=["coef_bits","square_bits","product_bits","result_bits","delta_bits","precision_bits","n_bits","guard_bits","output_bits"]
  # Actual names are authoritative. Other integer dataclass fields which look
  # like widths may be considered, but never alter physical target n_p.
  candidates=[k for k,v in fields.items() if k in target_names and isinstance(v,int)
             and not isinstance(v,bool) and v>4]
  candidates+= [k for k,v in fields.items() if k not in candidates and
      ("bits" in k or "prec" in k) and isinstance(v,int) and not isinstance(v,bool) and v>4]
  cases=[]
  for key in candidates:
   for reduction in range(1,args.max_reduction+1):
    if fields[key]-reduction<2:continue
    cases.append({key:fields[key]-reduction})
  # Explore paired reductions only after singles, within the bound.
  for i,k1 in enumerate(candidates):
   for k2 in candidates[i+1:]:
    cases.append({k1:fields[k1]-1,k2:fields[k2]-1})
  for i,changes in enumerate(cases[:args.max_candidates],1):
   row={"case":i,"changes":changes,"status":"BUILDING"}
   data["trials"].append(row);save()
   try:
    newprec=dataclasses.replace(base,**changes)
    candidate=module.build_nr_circuit(10,prec=newprec)
    s=resource(candidate)
    row["resources"]=s
    row["static_proxy_delta"]=score_proxy(s)-score_proxy(baseline)
    # The proxy ignores rotations and measurements; prioritize it only to
    # avoid an expensive verifier call for strictly non-improving resources.
    if row["static_proxy_delta"]<0 and s["qubits"]<=baseline["qubits"]:
     path=RUN/f"candidate_{i:02d}.kmb"
     candidate.to_file(str(path),format="kmb")
     row["path"]=str(path);row["sha256"]=sha256(path)
     row["status"]="PENDING_VERIFIER"
    else:row["status"]="PRUNED_NO_STATIC_COST_WIN"
   except Exception as e:
    row["status"]="BUILD_ERROR";row["error"]=f"{type(e).__name__}: {str(e)[:1000]}"
   print("K016 CASE",i,changes,row["status"],
      "DELTA",row.get("static_proxy_delta"),flush=True)
   save()
  finalists=sorted((x for x in data["trials"] if x["status"]=="PENDING_VERIFIER"),
                   key=lambda x:x["static_proxy_delta"])[:args.max_verifications]
  if finalists:
   print("K016 OFFICIAL REFERENCE VERIFIER...",flush=True)
   data["baseline_verifier"]=verify(OFFICIAL,args);save()
   if not data["baseline_verifier"]["pass"]:
    data["status"]="FAIL_BASELINE_VERIFIER";save()
    print("K016 STATUS",data["status"],flush=True);return
   for row in finalists:
    print("K016 OFFICIAL VERIFY CASE",row["case"],flush=True)
    v=verify(Path(row["path"]),args);row["official_verifier"]=v
    if v["pass"]:
     row["score_delta"]=v["result"]["score"]-data["baseline_verifier"]["result"]["score"]
     row["status"]="OFFICIAL_SMOKE_WIN" if row["score_delta"]<0 else "OFFICIAL_SMOKE_NO_WIN"
    else:row["status"]="OFFICIAL_SMOKE_REJECTED"
    print("K016 VERIFIER",row["case"],row["status"],row.get("score_delta"),flush=True)
    save()
  winners=[x for x in data["trials"] if x["status"]=="OFFICIAL_SMOKE_WIN"]
  data["status"]="PASS_PRELIMINARY_SCORE_WIN" if winners else "PASS_NO_VERIFIED_SCORE_WIN"
  data["static_wins"]=sum(x.get("static_proxy_delta",0)<0 for x in data["trials"])
  data["verified_smoke_wins"]=len(winners)
  if sha256(OFFICIAL)!=reference_sha:raise AssertionError("Reference sample was modified")
  save()
  print("K016 STATUS",data["status"])
  print("K016 STATIC_WINS",data["static_wins"],"SMOKE_WINS",len(winners))
  print("K016 REPORT",args.report)
 except Exception:
  data["status"]="FAIL";data["traceback"]=traceback.format_exc()[-6500:]
  save();raise
if __name__=="__main__":main()
