#!/usr/bin/env python3
"""A63: native-basis cost of A61 modular constant ADDER (not multiplier)."""
import argparse,json,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a61_binary_modular_adder import build
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--constants",type=int,nargs="+",default=[8,64])
 p.add_argument("--output",default="results/a63_adder_native_cost.json")
 a=p.parse_args();path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"A63_BINARY_MODULAR_ADDER_NATIVE_COST","status":"IN_PROGRESS",
       "correctness_at_n_verified":False,"full_multiplier":False,"rows":[]}
 def save():path.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  for k in a.constants:
   start=time.perf_counter();qc=build(a.n,k)
   native=transpile(qc,basis_gates=["u","cx"],optimization_level=0,seed_transpiler=63)
   ops=dict(native.count_ops())
   row={"n":a.n,"k":k,"qubits":qc.num_qubits,
        "source_ops":dict(qc.count_ops()),"source_depth":qc.depth(),
        "native_ops":ops,"native_cx":ops.get("cx",0),"native_depth":native.depth(),
        "compile_seconds":round(time.perf_counter()-start,3),
        "native_basis":["u","cx"],"note":"addition stage only; no quantum semantic audit at this modulus"}
   data["rows"].append(row);save()
   print("A63", "N",a.n,"k",k,"qubits",qc.num_qubits,"CX",row["native_cx"],"depth",row["native_depth"],"seconds",row["compile_seconds"],flush=True)
  data["status"]="PASS_COST_COMPILATION_NOT_GATE_VALIDATION";save()
 except Exception:
  data["status"]="ERROR";data["error"]=traceback.format_exc()[-4000:];save();raise
 print("A63 STATUS",data["status"],"SAVED",path,flush=True)
if __name__=="__main__":main()
