#!/usr/bin/env python3
"""A103: matched IBM Fez native routing holdout for full A102 modular-N sum.

Compare A102 complete clean reversible 3-input reduction mod N at baseline
and carry-save architectures. Candidate uses 98 logical qubits at N=2491
vs 71 baseline. Nested layouts chosen from one connected 98-qubit BFS
subgraph; this is not an equal-width resource comparison.
No QPU execution, payment, or quantum phase/noise simulation.
"""
import argparse,collections,json,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a102_clean_modular_csa_three_sum import build,check,triples
from qrr_a94_ibm_target_local_routing import connected_layout

def ledger(circuit):
 counts=collections.Counter()
 for item in circuit.data:
  if len(item.qubits)==2:counts[item.operation.name]+=1
 return dict(sorted(counts.items()))

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--backend-name",default="ibm_fez")
 p.add_argument("--instance",default="open-instance")
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--seed",type=int,default=10101)
 p.add_argument("--probes",type=int,default=128)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--max-new-architectures",type=int,default=1)
 p.add_argument("--output",default="results/a103_ibm_fez_modular_csa.json")
 a=p.parse_args()
 if a.n<3 or a.n%2!=1 or a.n.bit_length()>14:p.error("odd modulus up to 14 bits only")
 if a.probes<0 or a.max_new_architectures<1:p.error("nonnegative probes and positive max-new-architectures required")
 from qiskit_ibm_runtime import QiskitRuntimeService
 service=QiskitRuntimeService(instance=a.instance) if a.instance else QiskitRuntimeService()
 backend=service.backend(a.backend_name)
 baseline_circ,baseline_meta=build(a.n,"baseline")
 candidate_circ,candidate_meta=build(a.n,"carry_save")
 max_qubits=candidate_circ.num_qubits
 if backend.num_qubits<max_qubits:
  raise RuntimeError(f"Backend only {backend.num_qubits} qubits; candidate requires {max_qubits}")
 common_layout=connected_layout(backend,max_qubits)
 # A100's baseline uses the first 4w physical positions. Same logical
 # register positions are therefore initialized on the SAME physical qubits.
 physical_layouts={"baseline":common_layout[:baseline_circ.num_qubits],"carry_save":common_layout}
 settings={"backend":backend.name,"n":a.n,"seed":a.seed,"probes":a.probes,
   "level":a.level,"layouts":physical_layouts}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():
  d=json.loads(out.read_text())
  if d["settings"]!=settings:raise ValueError("Saved checkpoint has different settings or layout")
 else:
  d={"experiment":"A103_READ_ONLY_IBM_TARGET_CLEAN_MODULAR_CSA_ROUTING",
     "status":"IN_PROGRESS","settings":settings,"architectures":{},"qpu_jobs":0,
     "limitations":["Full clean modular-N three-input sum, NOT modular multiplication or full QPE",
       "A102 baseline/carry-save widths differ, and +27 logical qubits for N2491 are a real hardware cost",
       "Source computational-basis checks not hardware execution or phase/noise verification",
       "Layout prefixes of one connected region, but routing path lengths and optimization may differ",
       "Device calibration changes over time; routing results are snapshot dependent"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 checks=list(triples(a.n.bit_length(),a.probes,a.seed,4))
 print("A103 DEVICE",backend.name,"max_width",max_qubits,
   "layout",common_layout,flush=True)
 new=0
 try:
  for name,circ,meta in (("baseline",baseline_circ,baseline_meta),("carry_save",candidate_circ,candidate_meta)):
   if name in d["architectures"]:continue
   tick=time.perf_counter()
   tested=check(circ,meta,checks)
   native=transpile(circ,backend=backend,optimization_level=a.level,
     seed_transpiler=a.seed,initial_layout=physical_layouts[name],
     layout_method="trivial",routing_method="sabre")
   counts=ledger(native)
   row={"logical_qubits":circ.num_qubits,
     "physical_qubits_in_transpiled_circuit":native.num_qubits,
     "two_qubit_gates":sum(counts.values()),"two_qubit_by_name":counts,
     "depth":int(native.depth()),"basis_cases":tested,
     "elapsed_seconds":round(time.perf_counter()-tick,3)}
   d["architectures"][name]=row;save()
   print("A103 ROUTED",name,row,flush=True)
   new+=1
   if new>=a.max_new_architectures:break
  if len(d["architectures"])==2:
   left=d["architectures"]["baseline"];right=d["architectures"]["carry_save"]
   d["comparison"]={"delta_two_qubit":right["two_qubit_gates"]-left["two_qubit_gates"],
     "two_qubit_reduction_pct":round(100*(left["two_qubit_gates"]-right["two_qubit_gates"])/left["two_qubit_gates"],4),
     "delta_depth":right["depth"]-left["depth"],
     "depth_reduction_pct":round(100*(left["depth"]-right["depth"])/left["depth"],4),
     "extra_logical_qubits":right["logical_qubits"]-left["logical_qubits"]}
   d["status"]="PASS_READ_ONLY_TARGET_ROUTED_COMPARISON"
  else:d["status"]="PARTIAL_CHECKPOINT"
  save()
  print("A103 STATUS",d["status"],d.get("comparison",{}),flush=True)
 except Exception:
  d["status"]="ERROR_OR_INTERRUPTED";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
