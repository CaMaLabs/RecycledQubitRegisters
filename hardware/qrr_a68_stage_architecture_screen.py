#!/usr/bin/env python3
"""A68: measure each DISTINCT controlled modular power in recycled QPE.

Do not claim that mixed stage counts equal optimized full-circuit counts.
A64 use requires its 8-qubit overhead for the entire circuit.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a44_generic_modular_multiplier as a44
import qrr_a64_binary_modular_multiplier as a64
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=221);p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=16)
 p.add_argument("--output",default="results/a68_n221_stage_costs.json")
 a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"A68_PER_POWER_ARCHITECTURE_SELECTION","n":a.n,"base":a.base,"bits":a.bits,
       "status":"IN_PROGRESS","native_basis":["u","cx"],"rows":[]}
 def save():out.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  powers=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
  costs={}
  for power in dict.fromkeys(powers):
   if power==1:continue
   row={"power":power,"counts":{}}
   for name,builder in (("a44",a44.build),("a64",a64.build)):
    started=time.perf_counter();obj=builder(a.n,power)
    qc=obj[0] if isinstance(obj,tuple) else obj
    native=transpile(qc,basis_gates=["u","cx"],optimization_level=0,seed_transpiler=68)
    row["counts"][name]={"cx":native.count_ops().get("cx",0),"depth":native.depth(),
                        "qubits":qc.num_qubits,"seconds":round(time.perf_counter()-started,3)}
   row["lower_cx"]="a44" if row["counts"]["a44"]["cx"]<=row["counts"]["a64"]["cx"] else "a64"
   row["lower_depth"]="a44" if row["counts"]["a44"]["depth"]<=row["counts"]["a64"]["depth"] else "a64"
   costs[power]=row;data["rows"].append(row);save()
   print("A68 POWER",power,"A44_CX",row["counts"]["a44"]["cx"],"A64_CX",row["counts"]["a64"]["cx"],"CHEAPER",row["lower_cx"],flush=True)
  data["stages"]=[{"j":j,"power":power,"cx_winner":costs[power]["lower_cx"] if power!=1 else "identity",
    "depth_winner":costs[power]["lower_depth"] if power!=1 else "identity"} for j,power in enumerate(powers)]
  data["status"]="PASS_PER_STAGE_NATIVE_COSTS_NOT_FULL_HYBRID_COMPILED";save()
  print("A68 STATUS",data["status"],"DISTINCT_POWERS",len(costs),flush=True)
 except Exception:
  data["status"]="ERROR";data["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
