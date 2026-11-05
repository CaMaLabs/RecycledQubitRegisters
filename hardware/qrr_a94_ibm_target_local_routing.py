#!/usr/bin/env python3
"""A94: real IBM backend TARGET, zero-job, routed controlled-multiplier A/B.

Fetches metadata using QiskitRuntimeService, never calls backend.run, Sampler,
Estimator, session, or job submission. Compiles A84/A87b locally against the
SAME hardware target and the SAME connected physical-qubit initial layout.
One modular power per invocation, checkpoint after each architecture.

Resource result: routed individual arithmetic stages, NOT full dynamic QPE.
Hardware calibration is a metadata snapshot, NOT a fidelity prediction.
"""
import argparse,collections,json,math,sys,time,traceback
from collections import deque
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a84_fused_carry_multiplier import build as a84
from qrr_a87b_direct_prefix_multiplier import build as a87b
from qrr_a92_boxed_qpe_topology_audit import audit

def connected_layout(backend,width):
 cmap=backend.coupling_map
 if cmap is None:raise RuntimeError("Backend has no coupling map; cannot validate physical connectivity")
 edges=list(cmap.get_edges())
 adj={i:set() for i in range(backend.num_qubits)}
 for u,v in edges:
  adj[u].add(v);adj[v].add(u)
 # Deterministic BFS, choosing a connected, physically available subset.
 # Use a connected physical subgraph. Device-specific disabled edges are
 # handled by the compiler target during transpilation.
 candidates=[]
 for root in range(backend.num_qubits):
  seen={root};q=deque([root]);order=[]
  while q and len(order)<width:
   v=q.popleft()
   order.append(v)
   for neighbor in sorted(adj[v]):
    if neighbor not in seen:
     seen.add(neighbor);q.append(neighbor)
  if len(order)>=width:
   candidates.append(order)
   break
 if not candidates:raise RuntimeError(f"No connected subset of {width} qubits in backend coupling map")
 return candidates[0]

def gate_ledger(qc):
 by_name=collections.Counter()
 for item in qc.data:
  if len(item.qubits)==2:by_name[item.operation.name]+=1
 return dict(sorted(by_name.items()))

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--backend-name",default=None,
    help="Explicit IBM backend name; if absent select first accessible real backend with enough qubits")
 p.add_argument("--instance",default=None,
    help="Optional QiskitRuntimeService instance selector")
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--powers",nargs="+",type=int,default=[8,64,2448,2217,1051])
 p.add_argument("--level",type=int,choices=(0,1,2,3),default=1)
 p.add_argument("--seed",type=int,default=9401)
 p.add_argument("--probes",type=int,default=8)
 p.add_argument("--max-new-powers",type=int,default=1)
 p.add_argument("--output",default="results/a94_ibm_target_routing.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n >=9 coprime base required")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("invalid bit count")
 if a.max_new_powers<1 or a.probes<0:p.error("invalid probes or max new powers")
 schedule=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
 powers=list(dict.fromkeys(a.powers))
 if not powers or any(x==1 or x not in schedule for x in powers):p.error("powers must appear in QPE schedule")
 width=2*a.n.bit_length()+6

 from qiskit_ibm_runtime import QiskitRuntimeService
 service=QiskitRuntimeService(instance=a.instance) if a.instance else QiskitRuntimeService()
 if a.backend_name:
  backend=service.backend(a.backend_name)
 else:
  available=service.backends(simulator=False,operational=True,min_num_qubits=width)
  if not available:raise RuntimeError("No accessible operational hardware backend with enough qubits")
  backend=sorted(available,key=lambda x:x.name)[0]
 if backend.num_qubits<width:raise RuntimeError(f"Backend {backend.name} has fewer than {width} qubits")
 layout=connected_layout(backend,width)
 snapshot={"backend":backend.name,"backend_qubits":backend.num_qubits,
   "logical_qubits":width,"initial_layout":layout,
   "target_instructions":sorted(backend.target.operation_names),
   "coupling_edges":len(backend.coupling_map.get_edges()),
   "dt_seconds":getattr(backend.target,"dt",None)}
 print("A94 DEVICE",snapshot["backend"],"physical",snapshot["backend_qubits"],
       "logical",width,"layout",layout,flush=True)
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 settings={"n":a.n,"base":a.base,"bits":a.bits,"powers":powers,
    "backend":backend.name,"level":a.level,"seed":a.seed,"probes":a.probes,
    "initial_layout":layout}
 if path.exists():
  d=json.loads(path.read_text())
  if d.get("settings")!=settings:
   raise ValueError("Existing checkpoint settings differ (backend/target/layout); use a fresh output")
 else:
  d={"experiment":"A94_REAL_IBM_TARGET_LOCAL_ROUTING_A84_A87B",
     "settings":settings,"device_snapshot":snapshot,"status":"IN_PROGRESS",
     "stages":{},"qpu_jobs_submitted":0,
     "limitations":["Read-only backend metadata and local transpilation; no QPU execution or paid runtime",
       "Device target may change with calibration; no error-adjusted fidelity claim",
       "One compiled modular-power stage at a time, not full 24-bit QPE",
       "Same fixed initial layout and transpiler seed; routing is heuristic"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save();new=0
 try:
  for k in powers:
   row=d["stages"].setdefault(str(k),{"power":k,"architectures":{}})
   if all(name in row["architectures"] for name in ("a84","a87b")):continue
   for name,builder in (("a84",a84),("a87b",a87b)):
    if name in row["architectures"]:continue
    start=time.perf_counter()
    checked=audit(a.n,k,builder,a.probes,a.seed)
    circuit=builder(a.n,k)
    native=transpile(circuit,backend=backend,optimization_level=a.level,
       seed_transpiler=a.seed,initial_layout=layout,
       layout_method="trivial",routing_method="sabre")
    ledger=gate_ledger(native)
    entry={"basis_cases":checked,"qubits_in_transpiled_circuit":native.num_qubits,
       "two_qubit_gates":sum(ledger.values()),"two_qubit_by_name":ledger,
       "cx":int(native.count_ops().get("cx",0)),
       "depth":int(native.depth()),
       "compile_seconds":round(time.perf_counter()-start,3)}
    row["architectures"][name]=entry;save()
    print("A94 ROUTED",k,name,"2Q",entry["two_qubit_gates"],
       "CX",entry["cx"],"depth",entry["depth"],"basis",checked,flush=True)
   x=row["architectures"]["a84"];y=row["architectures"]["a87b"]
   row["comparison"]={
    "two_qubit_reduction_pct":round(100*(x["two_qubit_gates"]-y["two_qubit_gates"])/x["two_qubit_gates"],4),
    "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4)}
   save();print("A94 POWER RESULT",k,row["comparison"],flush=True)
   new+=1
   if new>=a.max_new_powers:break
  done=[k for k in powers if all(name in d["stages"].get(str(k),{}).get("architectures",{}) for name in ("a84","a87b"))]
  d["completed_powers"]=len(done);d["total_powers"]=len(powers)
  if len(done)==len(powers):
   totals={}
   for name in ("a84","a87b"):
    rows=[d["stages"][str(k)]["architectures"][name] for k in powers]
    totals[name]={"sum_two_qubit_gates":sum(x["two_qubit_gates"] for x in rows),
      "sum_depth":sum(x["depth"] for x in rows)}
   x=totals["a84"];y=totals["a87b"]
   d["stage_sums_not_full_qpe"]=totals
   d["comparison"]={"two_qubit_reduction_pct":round(
    100*(x["sum_two_qubit_gates"]-y["sum_two_qubit_gates"])/x["sum_two_qubit_gates"],4),
    "depth_reduction_pct":round(100*(x["sum_depth"]-y["sum_depth"])/x["sum_depth"],4),
    "two_qubit_stage_wins":sum(d["stages"][str(k)]["comparison"]["two_qubit_reduction_pct"]>0 for k in powers)}
   d["status"]="PASS_IBM_TARGET_LOCAL_ROUTED_HOLDOUT"
  else:d["status"]="PARTIAL_CHECKPOINT"
  save()
  print("A94 STATUS",d["status"],"completed",len(done),"/",len(powers),
      d.get("comparison",{}),flush=True)
 except Exception:
  d["status"]="ERROR_OR_INTERRUPTED";d["error"]=traceback.format_exc()[-5000:];save();raise

if __name__=="__main__":main()
