#!/usr/bin/env python3
"""A101: read-only real-IBM-target routing holdout for A100 clean carry-save sum.

Compare A100's 3-input reversible ripple accumulator (4w qubits) with its
clean 3:2 carry-save implementation (6w-1 qubits), compiling both to the
same IBM target, seed, routing policy, optimization level. The candidate
has a wider physical footprint. Layouts are nested prefixes of one
connected BFS layout of max(widths) physical qubits.

Arithmetic is mod 2**w, not modular multiplication mod N. No QPU jobs.
Do NOT claim full-QPE improvement based on this prototype.
"""
import argparse,collections,json,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a100_carry_save_reversible_screen import (
 baseline,candidate,audit,sample_triples
)
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
 p.add_argument("--width",type=int,default=12)
 p.add_argument("--seed",type=int,default=10101)
 p.add_argument("--probes",type=int,default=128)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--max-new-architectures",type=int,default=1)
 p.add_argument("--output",default="results/a101_ibm_fez_carry_save.json")
 a=p.parse_args()
 if not 2<=a.width<=20:p.error("width 2..20 only")
 if a.probes<0 or a.max_new_architectures<1:p.error("nonnegative probes and positive max-new-architectures required")
 from qiskit_ibm_runtime import QiskitRuntimeService
 service=QiskitRuntimeService(instance=a.instance) if a.instance else QiskitRuntimeService()
 backend=service.backend(a.backend_name)
 max_qubits=6*a.width-1
 if backend.num_qubits<max_qubits:
  raise RuntimeError(f"Backend only {backend.num_qubits} qubits; candidate requires {max_qubits}")
 common_layout=connected_layout(backend,max_qubits)
 # A100's baseline uses the first 4w physical positions. Same logical
 # register positions are therefore initialized on the SAME physical qubits.
 physical_layouts={"baseline":common_layout[:4*a.width],"carry_save":common_layout}
 settings={"backend":backend.name,"width":a.width,"seed":a.seed,"probes":a.probes,
   "level":a.level,"layouts":physical_layouts}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():
  d=json.loads(out.read_text())
  if d["settings"]!=settings:raise ValueError("Saved checkpoint has different settings or layout")
 else:
  d={"experiment":"A101_READ_ONLY_IBM_TARGET_CARRY_SAVE_ROUTING",
     "status":"IN_PROGRESS","settings":settings,"architectures":{},"qpu_jobs":0,
     "limitations":["Clean sum mod 2^w only; not modular multiplication or full QPE",
       "A100 baseline/carry-save widths differ, and additional logical qubits are a real hardware cost",
       "Source computational-basis checks not hardware execution or phase/noise verification",
       "Layout prefixes of one connected region, but routing path lengths and optimization may differ",
       "Device calibration changes over time; routing results are snapshot dependent"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 checks=list(sample_triples(a.width,a.probes,a.seed,4))
 print("A101 DEVICE",backend.name,"max_width",max_qubits,
   "layout",common_layout,flush=True)
 new=0
 try:
  for name,builder in (("baseline",baseline),("carry_save",candidate)):
   if name in d["architectures"]:continue
   tick=time.perf_counter()
   circ=builder(a.width)
   tested=audit(circ,a.width,checks)
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
   print("A101 ROUTED",name,row,flush=True)
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
  print("A101 STATUS",d["status"],d.get("comparison",{}),flush=True)
 except Exception:
  d["status"]="ERROR_OR_INTERRUPTED";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
