#!/usr/bin/env python3
"""K022 independent controlled-adder hybrid exploration; does not touch K020.

Hypothesis: eliminate AND-product scratch / save Toffolis by using kickmix's
conditional arithmetic or controlled-add interfaces, then retain its optimized
carry-adder. Probe API, micro-compile variants, and transplant only those that
build correctly. A full candidate must pass the official unmodified verifier.
Always preserve inverse compute/uncompute and check exact reference baseline.

No candidate is declared correct merely because it compiles or has lower cost.
"""
from __future__ import annotations
import argparse,dataclasses,hashlib,importlib,json,sys,subprocess,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
VERIFIERS=PRIVATE/"official/verifiers"
SAMPLE=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFIER=VERIFIERS/"invsqrt/verify_submission_invsqrt.py"
K016=HERE.parent/"k016/k016_precision_search.json"
RUN=PRIVATE/"runs/k022"
REPORT=HERE/"k022_hybrid_adder.json"
MODES=("conditional","ccx_product","baseline")
def profile(c):
 s=c.operation_statistics()
 return {"qubits":int(c.num_qubits),"bits":int(c.num_bits),
    "toffoli_like":int(s.num_toffoli_like),
    "instructions":int(s.num_instructions),
    "reaction_depth":int(c.reaction_depth()),
    "t_like":int(s.num_t_like)}
def cost(s):return s["qubits"]*s["toffoli_like"]
def digest(p):
 with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def official_verify(path,args):
 total=args.max_x*args.shots_per_x
 batch=min(total,256)
 while total%batch:batch-=1
 cmd=[sys.executable,str(VERIFIER),str(path),"--format","kmb",
      "--max-x",str(args.max_x),"--shots-per-x",str(args.shots_per_x),
      "--batch-size",str(batch),"--max-workers","1","--seed",str(args.seed)]
 try:
  p=subprocess.run(cmd,cwd=str(VERIFIERS),capture_output=True,text=True,
    timeout=args.timeout,check=False)
  try:value=json.loads(p.stdout)
  except json.JSONDecodeError:value={"non_json":p.stdout[-1600:]}
  return {"passed":p.returncode==0 and value.get("status")=="PASS",
    "exit_code":p.returncode,"score":value.get("score"),
    "worst_error_over_tolerance":value.get("worst_error_over_tolerance"),
    "stderr":p.stderr[-1200:],"result":value}
 except subprocess.TimeoutExpired:
  return {"passed":False,"timed_out":True}

def original_add_row(builder,inverse,control,terms,target,scratch,subtract=False):
 import kickmix as km
 sources=km.array([q for q,_ in terms])
 products=km.array([scratch[i] for _,i in terms])
 low=min(i for _,i in terms)
 builder.init_and(control,sources,products)
 if subtract!=inverse:builder.isub(scratch[low:len(target)],target=target[low:])
 else:builder.iadd(scratch[low:len(target)],target=target[low:])
 builder.del_and(control,sources,products)

def custom_add_row(mode):
 import kickmix as km
 def _add_row(builder,inverse,control,terms,target,scratch,subtract=False):
  # The control is a QUANTUM qubit; many conditional APIs only accept a
  # classical bit. A TypeError is a legitimate negative result.
  if mode=="conditional":
   low=min(i for _,i in terms)
   width=len(target)-low
   if width<=0:raise ValueError("empty target slice")
   # Populate just the original per-index (possibly sparse) source positions
   # into a clean temporary register. Avoid potentially incorrect byte-wide
   # quantum classical conditions until kickmix API explicitly accepts them.
   # This branch only works for contiguous coefficient positions; otherwise
   # reject and use unchanged reference implementation.
   positions=[i for _,i in terms]
   if positions!=list(range(low,low+len(positions))):
    return original_add_row(builder,inverse,control,terms,target,scratch,subtract)
   sources=km.array([q for q,_ in terms])
   # Intended: conditional addition of source row directly. The right-hand
   # operand must have width == target slice. If not, keep original.
   if len(sources)!=width:
    return original_add_row(builder,inverse,control,terms,target,scratch,subtract)
   builder.push_condition(control)
   try:
    if subtract!=inverse:builder.isub(sources,target=target[low:])
    else:builder.iadd(sources,target=target[low:])
   finally:
    builder.pop_condition()
   return
  if mode=="ccx_product":
   # QRR-style direct reversible AND into existing scratch (no reset).
   # Unlike measurement-based del_and, CCX uncompute is coherent and
   # can cost more; only promote if actual kickmix costs improve.
   low=min(i for _,i in terms)
   for q,i in terms:builder.ccx(control,q,scratch[i])
   if subtract!=inverse:builder.isub(scratch[low:len(target)],target=target[low:])
   else:builder.iadd(scratch[low:len(target)],target=target[low:])
   for q,i in reversed(terms):builder.ccx(control,q,scratch[i])
   return
  return original_add_row(builder,inverse,control,terms,target,scratch,subtract)
 return _add_row

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--case",type=int,default=21)
 a.add_argument("--max-x",type=int,default=64)
 a.add_argument("--shots-per-x",type=int,default=2)
 a.add_argument("--seed",type=int,default=12345)
 a.add_argument("--timeout",type=int,default=240)
 a.add_argument("--skip-full-build",action="store_true",
   help="Run interface tests only, do not generate full invsqrt")
 args=a.parse_args()
 if min(args.max_x,args.shots_per_x,args.timeout)<1:a.error("invalid arguments")
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 if not K016.is_file() or not VERIFIER.is_file():a.error("Missing K016 or verifier")
 import kickmix as km
 mod=importlib.import_module("invsqrt.nr_reference_circuit")
 data=json.loads(K016.read_text())
 rows=[r for r in data["trials"] if r["case"]==args.case]
 if len(rows)!=1:a.error("Unknown K016 case")
 candidate_row=rows[0]
 if not candidate_row.get("path"):a.error("K016 circuit unavailable")
 path=Path(candidate_row["path"])
 if not path.is_file() or digest(path)!=candidate_row["sha256"]:
  a.error("K016 circuit is absent or SHA mismatch")
 baseline_circuit=km.Circuit.from_file(str(path))
 baseline=profile(baseline_circuit)
 reference_score=cost(baseline)
 prec=dataclasses.replace(mod.Precision(),**candidate_row["changes"])
 orig_fn=mod._add_row
 RUN.mkdir(parents=True,exist_ok=True)
 d={"experiment":"K022_QRR_HYBRID_CONTROLLED_ADDER",
    "case":args.case,"precision_changes":candidate_row["changes"],
    "baseline_stats":baseline,"baseline_sha256":digest(path),
    "k020_touched":False,"full_domain_verified":False,"submitted":False,
    "status":"RUNNING","modes":{},
    "limitations":["Quantum control cannot be assumed compatible with classical condition APIs",
      "Coherent CCX uncompute is not the same cost as measurement-based del_and",
      "Candidates require the official verifier; 64-input smoke tests are insufficient"]}
 def save():
  REPORT.parent.mkdir(parents=True,exist_ok=True)
  REPORT.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  print("K022 BASELINE",baseline,flush=True)
  # Test quantum condition API directly with smallest generated circuit.
  builder=km.CircuitBuilder()
  q=builder.alloc_qubits(5)
  probe={}
  for k in ("push_condition","pop_condition","iadd","init_and","del_and","free"):
   probe[k]=(getattr(km.CircuitBuilder,k).__doc__ or "")[:1300]
  try:
   builder.push_condition(q[0])
   builder.iadd(q[1:3],target=q[3:5])
   builder.pop_condition()
   probe["quantum_condition"]="ACCEPTED"
   probe["quantum_condition_profile"]=profile(builder.finish_circuit())
  except Exception as e:
   probe["quantum_condition"]=f"REJECTED: {type(e).__name__}: {e}"
  d["condition_probe"]=probe
  print("K022 QUANTUM CONDITION",probe["quantum_condition"],flush=True)
  if args.skip_full_build:
   d["status"]="INTERFACE_PROBE_ONLY";save();return
  # Compile baseline from source. This also verifies K016 baseline is
  # genuinely reproducible before any monkeypatch-derived comparisons.
  source=mod.build_nr_circuit(10,prec=prec)
  if profile(source)!=baseline:
   d["status"]="STOP_REFERENCE_REBUILD_MISMATCH"
   d["rebuilt"]=profile(source);save()
   print("K022 STATUS",d["status"],flush=True);return
  # Replacing ONLY _add_row avoids touching the official verifier and
  # preserves the reference's inverse compute/uncompute call schedule.
  for mode in ("conditional","ccx_product"):
   row={"status":"BUILDING"}
   d["modes"][mode]=row;save()
   if mode=="conditional" and probe["quantum_condition"]!="ACCEPTED":
    row["status"]="UNSUPPORTED_QUANTUM_CONDITION";save()
    print("K022",mode,row["status"],flush=True);continue
   try:
    mod._add_row=custom_add_row(mode)
    circuit=mod.build_nr_circuit(10,prec=prec)
    row["resources"]=profile(circuit)
    row["proxy_delta"]=cost(row["resources"])-reference_score
    row["status"]="BUILT"
    print("K022",mode,"RESOURCE_DELTA",row["proxy_delta"],
       row["resources"],flush=True)
    if row["proxy_delta"]<0:
     exported=RUN/(f"case{args.case}_{mode}.kmb")
     circuit.to_file(str(exported),format="kmb")
     row["path"]=str(exported);row["sha256"]=digest(exported)
     row["status"]="PENDING_OFFICIAL_VERIFIER"
    else:
     row["status"]="NO_STATIC_PROXY_WIN"
   except Exception as e:
    row["status"]="BUILD_ERROR"
    row["error"]=f"{type(e).__name__}: {e}"
    row["traceback"]=traceback.format_exc()[-1300:]
    print("K022",mode,row["status"],row["error"],flush=True)
   finally:
    mod._add_row=orig_fn
   save()
  finalists=[(mode,r) for mode,r in d["modes"].items() if
      r["status"]=="PENDING_OFFICIAL_VERIFIER"]
  if finalists:
   d["baseline_verifier"]=official_verify(path,args);save()
   if not d["baseline_verifier"]["passed"]:
    d["status"]="STOP_BASELINE_OFFICIAL_VERIFIER_FAILURE";save()
    print("K022 STATUS",d["status"],flush=True);return
   for mode,row in finalists:
    row["official_verifier"]=official_verify(Path(row["path"]),args)
    result=row["official_verifier"]
    if result["passed"] and isinstance(result["score"],(int,float)):
     row["score_delta"]=result["score"]-d["baseline_verifier"]["score"]
     row["status"]="PRELIMINARY_SCORE_WIN" if row["score_delta"]<0 else "NO_VERIFIED_SCORE_WIN"
    else:row["status"]="REJECTED_BY_OFFICIAL_VERIFIER"
    print("K022 VERIFY",mode,row["status"],
      row.get("score_delta"),flush=True)
    save()
  d["status"]="COMPLETE"
  save()
  print("K022 STATUS",d["status"])
  print("K022 REPORT",REPORT)
 finally:
  mod._add_row=orig_fn
  if d["status"]=="RUNNING":
   d["status"]="ERROR";d["traceback"]=traceback.format_exc()[-1300:]
  save()
if __name__=="__main__":main()
