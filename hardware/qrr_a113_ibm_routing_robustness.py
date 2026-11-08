#!/usr/bin/env python3
"""A113: robust target-only A97/A110 resource holdout, multiple seeds and layouts.

Locally transpiles each controlled modular-power stage against read-only IBM
backend target metadata. Every A97/A110 trial uses the exact same target,
physical layout, transpiler seed, and optimization level. Trials checkpoint
one power/layout/seed pairing at a time. No hardware jobs or paid runtime.
"""
import argparse,collections,json,math,sys,time,traceback
from collections import deque
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a97_adaptive_modadd_multiplier import build as a97
from qrr_a110_commuting_gate_cancellation import simplify
from qrr_a92_boxed_qpe_topology_audit import audit

def layouts_for_backend(backend,width,count):
 cmap=backend.coupling_map
 if cmap is None:raise RuntimeError("No backend coupling graph")
 adj={i:set() for i in range(backend.num_qubits)}
 for u,v in cmap.get_edges():
  adj[u].add(v);adj[v].add(u)
 options=[];used=set()
 # Spread roots across the entire device to test spatial sensitivity.
 roots=list(range(0,backend.num_qubits,max(1,backend.num_qubits//(count*3))))
 roots+=list(range(backend.num_qubits))
 for root in roots:
  queue=deque([root]);seen={root};order=[]
  while queue and len(order)<width:
   v=queue.popleft();order.append(v)
   for neighbor in sorted(adj[v]):
    if neighbor not in seen:seen.add(neighbor);queue.append(neighbor)
  if len(order)==width:
   physical=frozenset(order)
   if physical not in used:
    options.append({"root":root,"qubits":order})
    used.add(physical)
    if len(options)>=count:break
 if len(options)<count:raise RuntimeError("Insufficient distinct connected physical subsets")
 return options

def two_qubit_ledger(q):
 c=collections.Counter()
 for item in q.data:
  if len(item.qubits)==2:c[item.operation.name]+=1
 return dict(sorted(c.items()))

def compile_stage(q,backend,layout,seed,level):
 t=transpile(q,backend=backend,initial_layout=layout,
   layout_method="trivial",routing_method="sabre",
   seed_transpiler=seed,optimization_level=level)
 ledger=two_qubit_ledger(t)
 return {"two_qubit_gates":sum(ledger.values()),"two_qubit_by_name":ledger,
   "depth":int(t.depth()),"qubits_in_transpiled_circuit":t.num_qubits}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--backend-name",default="ibm_fez")
 p.add_argument("--instance",default=None)
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--powers",type=int,nargs="+",default=[8,64,2448,2217,1051])
 p.add_argument("--seeds",type=int,nargs="+",default=[9401,9402,9403])
 p.add_argument("--layout-count",type=int,default=2)
 p.add_argument("--level",type=int,choices=(0,1,2,3),default=1)
 p.add_argument("--probes",type=int,default=8)
 p.add_argument("--max-window",type=int,default=200)
 p.add_argument("--max-new-trials",type=int,default=1)
 p.add_argument("--output",default="results/a113_ibm_fez_routing_robustness.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("Odd modulus and coprime base required")
 if a.bits<2 or a.bits>2*a.n.bit_length():p.error("Invalid bits")
 if a.probes<0 or a.layout_count<2 or a.max_window<1 or a.max_new_trials<1:p.error("Invalid work controls")
 if len(set(a.seeds))!=len(a.seeds) or len(a.seeds)<2:p.error("Use at least two distinct transpiler seeds")
 schedule={pow(a.base,1<<j,a.n) for j in range(a.bits)}
 powers=list(dict.fromkeys(a.powers))
 if not powers or any(k==1 or k not in schedule for k in powers):p.error("Power not in phase-estimation schedule")
 from qiskit_ibm_runtime import QiskitRuntimeService
 service=QiskitRuntimeService(instance=a.instance) if a.instance else QiskitRuntimeService()
 backend=service.backend(a.backend_name)
 width=2*a.n.bit_length()+6
 if backend.num_qubits<width:raise RuntimeError("Backend has insufficient qubits")
 options=layouts_for_backend(backend,width,a.layout_count)
 settings={"n":a.n,"base":a.base,"bits":a.bits,"powers":powers,
   "seeds":a.seeds,"backend":backend.name,"level":a.level,"probes":a.probes,
   "max_window":a.max_window,"layouts":options}
 output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
 if output.exists():
  d=json.loads(output.read_text())
  if d.get("settings")!=settings:
   raise ValueError("Checkpoint settings/layouts differ; preserve prior output and use another path")
 else:
  d={"experiment":"A113_IBM_FEZ_MULTISEED_MULTILAYOUT_ROUTING_HOLDOUT",
    "settings":settings,"status":"IN_PROGRESS","trials":{},
    "qpu_jobs_submitted":0,
    "limitations":["Target metadata and local compiler only, no real QPU execution",
      "Isolated multiplier stages; stage sums are NOT full QPE costs",
      "Routing heuristic and physical subset layout selection may bias results",
      "Finite sampled basis verification and limited transpiler seeds",
      "Native 2Q and depth counts alone do not establish fault-tolerant cost or quantum advantage"]}
 def save():output.write_text(json.dumps(d,indent=2)+"\n")
 save()
 print("A113 DEVICE",backend.name,"physical",backend.num_qubits,
   "logical",width,"layouts",[(x["root"],x["qubits"]) for x in options],flush=True)
 new=0
 try:
  # Cache circuit within one invocation, while preserving identical source per pair.
  for power in powers:
   for idx,location in enumerate(options):
    for seed in a.seeds:
     key=f"p{power}_l{idx}_s{seed}"
     row=d["trials"].setdefault(key,{"power":power,"layout_index":idx,
       "layout_root":location["root"],"seed":seed,"architectures":{}})
     if "comparison" in row:continue
     raw=a97(a.n,power,level=a.level,seed=seed)[0]
     optimized,report=simplify(raw,a.max_window)
     for name,qc in (("a97",raw),("a110",optimized)):
      if name in row["architectures"]:continue
      tick=time.perf_counter()
      checked=audit(a.n,power,lambda n,k,circ=qc:circ,a.probes,seed)
      cost=compile_stage(qc,backend,location["qubits"],seed,a.level)
      cost["basis_checks"]=checked
      cost["elapsed_seconds"]=round(time.perf_counter()-tick,3)
      if name=="a110":cost["cancelled_pairs"]=report["cancelled_pairs"]
      row["architectures"][name]=cost;save()
      print("A113 ROUTED",key,name,"2Q",cost["two_qubit_gates"],
        "depth",cost["depth"],"basis",checked,flush=True)
     x=row["architectures"]["a97"];y=row["architectures"]["a110"]
     row["comparison"]={"delta_two_qubit":y["two_qubit_gates"]-x["two_qubit_gates"],
       "delta_depth":y["depth"]-x["depth"],
       "two_qubit_reduction_pct":round(100*(x["two_qubit_gates"]-y["two_qubit_gates"])/x["two_qubit_gates"],4),
       "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4)}
     new+=1;save()
     print("A113 TRIAL",key,row["comparison"],flush=True)
     if new>=a.max_new_trials:break
    if new>=a.max_new_trials:break
   if new>=a.max_new_trials:break
  wanted=len(powers)*len(options)*len(a.seeds)
  completed=[v for v in d["trials"].values() if "comparison" in v]
  d["completed_trials"]=len(completed);d["total_trials"]=wanted
  if len(completed)==wanted:
   wins=sum(v["comparison"]["delta_two_qubit"]<0 for v in completed)
   depth_wins=sum(v["comparison"]["delta_depth"]<0 for v in completed)
   x2=sum(v["architectures"]["a97"]["two_qubit_gates"] for v in completed)
   y2=sum(v["architectures"]["a110"]["two_qubit_gates"] for v in completed)
   xd=sum(v["architectures"]["a97"]["depth"] for v in completed)
   yd=sum(v["architectures"]["a110"]["depth"] for v in completed)
   reductions=[v["comparison"]["two_qubit_reduction_pct"] for v in completed]
   d["aggregate"]={"two_qubit_trial_wins":wins,"depth_trial_wins":depth_wins,
     "two_qubit_weighted_reduction_pct":round(100*(x2-y2)/x2,4),
     "depth_weighted_reduction_pct":round(100*(xd-yd)/xd,4),
     "min_two_qubit_reduction_pct":min(reductions),
     "max_two_qubit_reduction_pct":max(reductions),
     "trial_count":len(completed)}
   d["status"]="PASS_ROUTING_ROBUSTNESS" if wins==wanted and depth_wins==wanted else "COMPLETE_MIXED_ROUTING_RESULTS"
  else:d["status"]="PARTIAL_CHECKPOINT"
  save()
  print("A113 STATUS",d["status"],len(completed),"/",wanted,
    d.get("aggregate",{}),flush=True)
 except Exception:
  d["status"]="ERROR_OR_INTERRUPTED";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
