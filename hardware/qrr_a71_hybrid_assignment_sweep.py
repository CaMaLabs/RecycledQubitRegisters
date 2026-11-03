#!/usr/bin/env python3
"""A71: bounded exact enumeration of mixed A44/A64 recycled QPE assignments.

Uses the actual A69 circuit builder and the A68 native per-power screen.
Compares ALL nonidentity power assignments at level 0, and optionally
refines the top candidates at level 1. No Aer execution or factoring claim.
"""
import argparse,itertools,json,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a69_hybrid_recycled_qpe import build

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=221)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=16)
 p.add_argument("--screen",default="results/a68_n221_stage_costs.json")
 p.add_argument("--refine-top",type=int,default=2)
 p.add_argument("--output",default="results/a71_n221_assignment_sweep.json")
 a=p.parse_args()
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"A71_EXACT_HYBRID_STAGE_ASSIGNMENT_SWEEP",
       "status":"IN_PROGRESS","n":a.n,"base":a.base,"bits":a.bits,
       "quantum_simulated":False,"basis":["u","cx"],"rows":[]}
 def save():out.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  screen=json.loads(Path(a.screen).read_text())
  if (screen.get("n"),screen.get("base"),screen.get("bits"),screen.get("status"))!=(
      a.n,a.base,a.bits,"PASS_PER_STAGE_NATIVE_COSTS_NOT_FULL_HYBRID_COMPILED"):
   raise ValueError("A68 screen must match n/base/bits and have passing status")
  powers=sorted({pow(a.base,1<<j,a.n) for j in range(a.bits)}-{1})
  if len(powers)>6:raise ValueError("Too many distinct powers (>6); restrict sweep")
  if set(powers)!={int(r["power"]) for r in screen["rows"]}:
   raise ValueError("Screen power list does not match phase circuit")
  if a.refine_top<0 or a.refine_top>8:p.error("--refine-top 0..8")
  for choices in itertools.product(("a44","a64"),repeat=len(powers)):
   assign=dict(zip(powers,choices))
   started=time.perf_counter()
   qc,stages=build(a.n,a.base,a.bits,assign)
   native=transpile(qc,basis_gates=["u","cx","measure","reset","if_else"],
                    optimization_level=0,seed_transpiler=71)
   ops=dict(native.count_ops())
   row={"assignments":{str(k):v for k,v in assign.items()},
        "qubits":native.num_qubits,"cx":ops.get("cx",0),"depth":native.depth(),
        "native_ops":ops,"compile_seconds":round(time.perf_counter()-started,3),
        "optimization_level":0}
   data["rows"].append(row);save()
   print("A71 LEVEL0",row["assignments"],"CX",row["cx"],"depth",row["depth"],
         "qubits",row["qubits"],flush=True)
  ranked=sorted(data["rows"],key=lambda r:(r["cx"],r["depth"],r["qubits"]))
  data["best_level0"]=ranked[0]
  data["refined"]=[]
  for row in ranked[:a.refine_top]:
   started=time.perf_counter()
   qc,_=build(a.n,a.base,a.bits,{int(k):v for k,v in row["assignments"].items()})
   native=transpile(qc,optimization_level=1,seed_transpiler=71,
      basis_gates=["u","cx","measure","reset","if_else"])
   r={"assignments":row["assignments"],"qubits":native.num_qubits,
      "cx":native.count_ops().get("cx",0),"depth":native.depth(),
      "optimization_level":1,"compile_seconds":round(time.perf_counter()-started,3)}
   data["refined"].append(r);save()
   print("A71 LEVEL1",r["assignments"],"CX",r["cx"],"depth",r["depth"],flush=True)
  data["status"]="PASS_COMPLETE_ASSIGNMENT_COMPILE_SWEEP"
  save()
  print("A71 STATUS",data["status"],"BEST_LEVEL0",data["best_level0"]["assignments"],
        "CX",data["best_level0"]["cx"],"DEPTH",data["best_level0"]["depth"],flush=True)
 except Exception:
  data["status"]="FAIL";data["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
