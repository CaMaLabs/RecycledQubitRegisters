#!/usr/bin/env python3
"""K015: cross-repo-inspired arithmetic row scheduling at source level.

Uses local official invsqrt reference source in memory; modifies ONLY loop
iteration order in four accumulator sections. Each row writes a target
accumulator via (+/-) addition while its control/data sources are distinct
registers and each row's scratch is independently cleaned. Commutativity of
modular accumulation suggests exact equivalence, but kickmix's measurement
feedback and conditional semantics must be checked by its OFFICIAL verifier.

Runs a bounded beam of source-generated candidates, measures actual kickmix
Toffoli cost / Q, verifies candidates with a positive static score proxy.
No official source copied into git, no Kaggle submission or paid compute.
"""
import argparse,ast,hashlib,json,os,re,subprocess,sys,time,traceback,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIVATE=(HERE/"../k001/private").resolve()
REFERENCE_SOURCE=PRIVATE/"official/verifiers/invsqrt/nr_reference_circuit.py"
VERIFIERS=REFERENCE_SOURCE.parent.parent
SAMPLE=PRIVATE/"official/sample_submission/invsqrt.kmb"
VERIFY=REFERENCE_SOURCE.parent/"verify_submission_invsqrt.py"
RUN_DIR=PRIVATE/"runs/k015"
REPORT=HERE/"k015_row_schedule_results.json"
# Exact per-function loop expressions drawn from the official reference.
TRANSFORMS={
 "horner_delta":("_horner","for control, m in delta:","for control, m in reversed(delta):"),
 "square_outer":("_square","for k in range(1, wc + 1):","for k in reversed(range(1, wc + 1)):"),
 "multiply_m_outer":("_multiply_m","for i in range(width):","for i in reversed(range(width)):"),
 "multiply_y0_outer":("_multiply_y0","for k in range(1, wc + 1):","for k in reversed(range(1, wc + 1)):"),
}
def mutate(original,names):
 if not names:return original
 tree=ast.parse(original)
 lines=original.splitlines(keepends=True)
 changes=[]
 for name in names:
  function,old,new=TRANSFORMS[name]
  nodes=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==function]
  if len(nodes)!=1:raise RuntimeError(f"Missing or ambiguous function {function}")
  n=nodes[0]
  found=[i for i in range(n.lineno-1,n.end_lineno)
    if old in lines[i] and lines[i].lstrip().startswith(old)]
  if len(found)!=1:raise RuntimeError(f"Expected exactly one {old!r} in {function}, got {found}")
  i=found[0]
  changes.append((i,lines[i].replace(old,new,1)))
 for i,modified in changes:lines[i]=modified
 result="".join(lines)
 ast.parse(result)
 return result
def build(code,label,n_p):
 import kickmix as km
 # The reference module uses its local import context. Keep imports within
 # the official verifier directory without writing patched source to disk.
 if str(VERIFIERS) not in sys.path:sys.path.insert(0,str(VERIFIERS))
 mod=types.ModuleType("invsqrt._k015_"+label)
 mod.__file__=str(REFERENCE_SOURCE)
 mod.__package__="invsqrt"
 # Python 3.14 dataclasses resolve annotation types through sys.modules.
 # The temporary module must be registered before executing its classes.
 sys.modules[mod.__name__]=mod
 try:
  exec(compile(code,str(REFERENCE_SOURCE),"exec"),mod.__dict__)
  circuit=mod.build_nr_circuit(n_p)
 finally:
  sys.modules.pop(mod.__name__,None)
 o=circuit.operation_statistics()
 stats={"instructions":int(o.num_instructions),"toffoli_like":int(o.num_toffoli_like),
   "t_like":int(o.num_t_like),"qubits":int(circuit.num_qubits),
   "bits":int(circuit.num_bits),"reaction_depth":int(circuit.reaction_depth())}
 return circuit,stats
def file_sha(path):
 with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def verify(path,args):
 cmd=[sys.executable,str(VERIFY),str(path),"--format","kmb",
      "--shots-per-x",str(args.shots_per_x),"--max-x",str(args.max_x),
      "--batch-size",str(args.batch_size),"--max-workers","1",
      "--seed",str(args.seed)]
 try:
  p=subprocess.run(cmd,check=False,timeout=args.timeout,capture_output=True,text=True,
    cwd=str(VERIFIERS))
  try:d=json.loads(p.stdout)
  except json.JSONDecodeError:d={"error":"non-JSON verifier output","stdout_tail":p.stdout[-1700:]}
  return {"exit_code":p.returncode,"result":d,"stderr_tail":p.stderr[-1700:],
     "passed":p.returncode==0 and d.get("status")=="PASS"}
 except subprocess.TimeoutExpired:
  return {"passed":False,"timeout":True}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n-p",type=int,default=10)
 p.add_argument("--shots-per-x",type=int,default=2)
 p.add_argument("--max-x",type=int,default=8)
 p.add_argument("--batch-size",type=int,default=16)
 p.add_argument("--seed",type=int,default=12345)
 p.add_argument("--timeout",type=int,default=180)
 p.add_argument("--max-candidates",type=int,default=15)
 p.add_argument("--max-verifications",type=int,default=3)
 p.add_argument("--report",default=str(REPORT))
 args=p.parse_args()
 if min(args.n_p,args.shots_per_x,args.max_x,args.batch_size,args.timeout)<1:
  p.error("invalid sizes")
 if (args.shots_per_x*args.max_x)%args.batch_size:
  p.error("num shots must be divisible by batch size")
 if args.max_candidates<1 or args.max_candidates>15 or args.max_verifications<0 or args.max_verifications>15:
  p.error("candidate budgets invalid")
 if not REFERENCE_SOURCE.exists() or not SAMPLE.exists() or not VERIFY.exists():
  p.error("Missing K001 official sources")
 if args.n_p!=10:p.error("Current official sample and verifier A/B are bound to n_p=10")
 RUN_DIR.mkdir(parents=True,exist_ok=True)
 import kickmix as km
 original_source=REFERENCE_SOURCE.read_text(encoding="utf-8")
 # Validate all four source edits are structurally located before compiling any.
 for name in TRANSFORMS:mutate(original_source,[name])
 reference_sha=file_sha(SAMPLE)
 reference=km.Circuit.from_file(str(SAMPLE))
 base_o=reference.operation_statistics()
 baseline={"qubits":int(reference.num_qubits),"toffoli_like":int(base_o.num_toffoli_like),
           "instructions":int(base_o.num_instructions)}
 baseline["cost_proxy"]=baseline["qubits"]*baseline["toffoli_like"]
 names=list(TRANSFORMS)
 cases=[(i,tuple(k for bit,k in enumerate(names) if i&(1<<bit))) for i in range(1,16)]
 cases=cases[:args.max_candidates]
 d={"experiment":"K015_ROW_ACCUMULATION_SCHEDULING",
    "status":"IN_PROGRESS","source_sha256":hashlib.sha256(original_source.encode()).hexdigest(),
    "sample_sha256":reference_sha,"reference":baseline,
    "cross_repo_inspiration":["QRR arithmetic partial-product scheduling",
       "LWE branch pruning via static cost bounds"],
    "limitations":["Every potential win must pass the official functional and phase verifier",
      "Static gate counts do not predict rotation cost or full benchmark score",
      "Changing gate order changes stochastic simulator trace and seed behavior",
      "No direct LWE cryptanalytic transform is claimed to be a kickmix circuit identity"],
    "trials":[],"kaggle_submitted":False}
 out=Path(args.report);out.parent.mkdir(parents=True,exist_ok=True)
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  baseline_built, built_stats=build(original_source,"baseline",args.n_p)
  d["rebuilt_reference"]=built_stats
  d["rebuilt_reference_matched_official_stats"]=all(
   built_stats[k]==baseline[k] for k in ("qubits","toffoli_like","instructions"))
  print("K015 REBUILT BASELINE",built_stats,
    "MATCH",d["rebuilt_reference_matched_official_stats"],flush=True)
  if not d["rebuilt_reference_matched_official_stats"]:
   d["status"]="FAIL_REFERENCE_REBUILD_MISMATCH";save();return
  for n,selected in cases:
   print("K015 BUILD",n,",".join(selected),flush=True)
   code=mutate(original_source,selected)
   row={"case":n,"transforms":list(selected),"status":"BUILDING"}
   d["trials"].append(row);save()
   try:
    circuit,s=build(code,str(n),args.n_p)
    row["stats"]=s
    row["static_cost_proxy"]=s["qubits"]*s["toffoli_like"]
    row["static_proxy_delta"]=row["static_cost_proxy"]-baseline["cost_proxy"]
    if row["static_proxy_delta"]>=0:
     row["status"]="PRUNED_NONIMPROVING_STATIC_COST"
    else:
     path=RUN_DIR/f"candidate_{n:02d}.kmb"
     circuit.to_file(str(path),format="kmb")
     row["path"]=str(path);row["sha256"]=file_sha(path)
     row["status"]="STATIC_COST_WIN_PENDING_OFFICIAL_VERIFIER"
   except Exception as exc:
    row["status"]="BUILD_ERROR";row["error"]=f"{type(exc).__name__}: {str(exc)[:1000]}"
   print("K015 CASE",n,"STATUS",row["status"],
     "PROXY_DELTA",row.get("static_proxy_delta"),flush=True)
   save()
  finalists=sorted((x for x in d["trials"] if x["status"]=="STATIC_COST_WIN_PENDING_OFFICIAL_VERIFIER"),
    key=lambda r:r["static_proxy_delta"])[:args.max_verifications]
  if finalists:
   print("K015 OFFICIAL VERIFIER BASELINE...",flush=True)
   d["official_baseline"]=verify(SAMPLE,args);save()
   if not d["official_baseline"]["passed"]:
    d["status"]="FAIL_BASELINE_VERIFIER";save()
    print("K015 STATUS",d["status"],d["official_baseline"],flush=True);return
   for row in finalists:
    print("K015 VERIFY CASE",row["case"],flush=True)
    row["official"]=verify(Path(row["path"]),args)
    if row["official"]["passed"]:
     row["score_delta"]=row["official"]["result"]["score"]-d["official_baseline"]["result"]["score"]
     row["status"]="OFFICIAL_SMOKE_SCORE_WIN" if row["score_delta"]<0 else "OFFICIAL_SMOKE_NO_SCORE_WIN"
    else:row["status"]="OFFICIAL_SMOKE_FAILED"
    print("K015 VERIFY RESULT",row["case"],row["status"],
       row.get("score_delta"),flush=True)
    save()
  wins=[x for x in d["trials"] if x["status"]=="OFFICIAL_SMOKE_SCORE_WIN"]
  d["status"]="PASS_VERIFIED_SMOKE_WIN" if wins else "PASS_SEARCH_NO_VERIFIED_SCORE_WIN"
  save()
  print("K015 STATUS",d["status"])
  print("K015 BUILT",len(d["trials"]),"STATIC_WINS",
    sum(x["static_proxy_delta"]<0 for x in d["trials"] if "static_proxy_delta" in x),
    "VERIFIED_WINS",len(wins))
  print("K015 REPORT",out)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":main()
