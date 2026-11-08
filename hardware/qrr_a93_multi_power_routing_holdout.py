#!/usr/bin/env python3
"""A93: resumable routing holdout for A84 vs A87b modular power stages.

Default: five selected N2491 powers on a *synthetic* bidirectional line.
Optional --backend-name: fetch actual IBM backend TARGET for *local transpilation*.
NEVER submit jobs. Charges and QPU availability are not tested.

Report one selected, independently transpiled multiplier at a time. These
routed stage sums are NOT the native cost of a complete dynamic QPE circuit.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit.transpiler import CouplingMap
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a84_fused_carry_multiplier import build as a84
from qrr_a87b_direct_prefix_multiplier import build as a87b
from qrr_a92_boxed_qpe_topology_audit import audit

ARCHITECTURES=(("a84",a84),("a87b",a87b))
TWO_QUBIT={"cx","cz","ecr","iswap","rxx","ryy","rzz","rzx","swap","dcx","xx_plus_yy"}

def two_qubit_count(qc):
 counts=collections.Counter()
 for item in qc.data:
  if len(item.qubits)==2:
   counts[item.operation.name]+=1
 return dict(counts)

def run():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--powers",nargs="+",type=int,default=[8,64,2448,2217,1051])
 p.add_argument("--backend-name",default=None,
     help="Optional IBM backend name; reads backend.target metadata for LOCAL transpilation only")
 p.add_argument("--instance",default=None,
     help="Optional IBM instance for service selection, if needed")
 p.add_argument("--level",type=int,choices=(0,1,2,3),default=1)
 p.add_argument("--probes",type=int,default=8)
 p.add_argument("--seed",type=int,default=9301)
 p.add_argument("--max-new-powers",type=int,default=1)
 p.add_argument("--output",default="results/a93_n2491_routed_holdout.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits must fit QPE precision")
 if a.probes<0 or a.max_new_powers<1:p.error("probes >=0 and max-new-powers >=1")
 schedule=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
 powers=list(dict.fromkeys(a.powers))
 if not powers or any(k==1 or k not in schedule for k in powers):
  p.error("Every requested power must be a nonidentity power in the schedule")
 topology=("ibm_target:"+a.backend_name) if a.backend_name else "synthetic_bidirectional_line"
 # Read backends only when explicitly requested. No runtime job APIs.
 backend=None
 if a.backend_name:
  from qiskit_ibm_runtime import QiskitRuntimeService
  service=QiskitRuntimeService(instance=a.instance) if a.instance else QiskitRuntimeService()
  backend=service.backend(a.backend_name)
  if backend.num_qubits < 2*a.n.bit_length()+6:
   p.error(f"Backend {a.backend_name} has insufficient qubits")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 settings={"n":a.n,"base":a.base,"bits":a.bits,"powers":powers,
           "level":a.level,"probes":a.probes,"seed":a.seed,
           "topology":topology,"backend_instance":a.instance}
 if out.exists():
  d=json.loads(out.read_text())
  if d.get("settings")!=settings:raise ValueError("Checkpoint settings changed; use a new output path")
 else:
  d={"experiment":"A93_MULTI_POWER_ROUTED_A84_A87B_AB",
     "settings":settings,"status":"IN_PROGRESS","stages":{},
     "hardware_jobs":0,"cost_incurred":False,
     "limitations":["Local transpilation only, no actual QPU execution or validated noise fidelity",
       "Synthetic nearest-neighbor line is not a specific IBM topology unless --backend-name is used",
       "Independently routed stage counts are not whole-QPE compilation",
       "Native two-qubit operations vary across device gate sets; CX-only comparisons are not universal"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  started=0
  for power in powers:
   key=str(power)
   row=d["stages"].setdefault(key,{"power":power,"architectures":{}})
   if all(x in row["architectures"] for x,_ in ARCHITECTURES):continue
   for name,builder in ARCHITECTURES:
    if name in row["architectures"]:continue
    start=time.perf_counter()
    qc=builder(a.n,power)
    verified=audit(a.n,power,builder,a.probes,a.seed)
    if backend:
     # No backend.run. Backend target, coupling map and operation errors
     # are sourced from metadata; no claim about execution.
     routed=transpile(qc,backend=backend,
         optimization_level=a.level,seed_transpiler=a.seed,
         routing_method="sabre")
    else:
     edges=[(i,i+1) for i in range(qc.num_qubits-1)]
     coupling=CouplingMap(edges);coupling.make_symmetric()
     routed=transpile(qc,coupling_map=coupling,
         basis_gates=["rz","sx","x","cx"],
         initial_layout=list(range(qc.num_qubits)),
         layout_method="trivial",routing_method="sabre",
         optimization_level=a.level,seed_transpiler=a.seed)
    q2=two_qubit_count(routed)
    result={"qubits":routed.num_qubits,
      "cx":int(routed.count_ops().get("cx",0)),
      "two_qubit_total":sum(q2.values()),
      "two_qubit_operations":q2,
      "depth":int(routed.depth()),
      "basis_cases":verified,
      "compile_seconds":round(time.perf_counter()-start,3)}
    row["architectures"][name]=result;save()
    print("A93 ROUTED",power,name,"2Q",result["two_qubit_total"],
          "CX",result["cx"],"depth",result["depth"],"basis",verified,flush=True)
   left=row["architectures"]["a84"];right=row["architectures"]["a87b"]
   row["comparison"]={
     "two_qubit_reduction_pct":round(100*(left["two_qubit_total"]-right["two_qubit_total"])/left["two_qubit_total"],4),
     "depth_reduction_pct":round(100*(left["depth"]-right["depth"])/left["depth"],4),
     "delta_two_qubit":right["two_qubit_total"]-left["two_qubit_total"],
     "delta_depth":right["depth"]-left["depth"]}
   save()
   print("A93 POWER RESULT",power,row["comparison"],flush=True)
   started+=1
   if started>=a.max_new_powers:break
  complete=[k for k in powers if all(x in d["stages"].get(str(k),{}).get("architectures",{}) for x,_ in ARCHITECTURES)]
  d["completed_powers"]=len(complete)
  d["requested_powers"]=len(powers)
  if len(complete)==len(powers):
   summary={}
   for name,_ in ARCHITECTURES:
    rows=[d["stages"][str(k)]["architectures"][name] for k in powers]
    summary[name]={"total_two_qubit":sum(x["two_qubit_total"] for x in rows),
                   "total_cx":sum(x["cx"] for x in rows),
                   "total_stage_depth":sum(x["depth"] for x in rows),
                   "max_qubits":max(x["qubits"] for x in rows)}
   l=summary["a84"];r=summary["a87b"]
   d["routed_stage_sum_only"]=summary
   d["comparison"]={"two_qubit_reduction_pct":round(
       100*(l["total_two_qubit"]-r["total_two_qubit"])/l["total_two_qubit"],4),
      "depth_reduction_pct":round(
       100*(l["total_stage_depth"]-r["total_stage_depth"])/l["total_stage_depth"],4),
      "stage_wins_two_qubit":sum(d["stages"][str(k)]["comparison"]["delta_two_qubit"]<0 for k in powers),
      "stage_wins_depth":sum(d["stages"][str(k)]["comparison"]["delta_depth"]<0 for k in powers)}
   d["status"]="PASS_ROUTED_MULTI_POWER_COST_HOLDOUT"
  else:d["status"]="PARTIAL_CHECKPOINT"
  save()
  print("A93 STATUS",d["status"],"completed",len(complete),"/",len(powers),
        d.get("comparison",{}),flush=True)
 except Exception:
  d["status"]="ERROR_OR_INTERRUPTED"
  d["error"]=traceback.format_exc()[-6000:];save()
  raise

if __name__=="__main__":run()
