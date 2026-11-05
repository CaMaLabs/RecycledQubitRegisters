#!/usr/bin/env python3
"""A73: fair level-1 A44 vs A64 modular-multiplier native CX/depth comparison.

Same n, base, u/cx basis, transpiler seed, optimization level and gate
semantics. A64 has 8 more qubits; resource evidence only, not full QPE.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a44_generic_modular_multiplier as a44
import qrr_a64_binary_modular_multiplier as a64

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,required=True)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--output",required=True)
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base required")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A73_MATCHED_OPT_MULTIPLIER_NATIVE_COST","status":"IN_PROGRESS",
    "n":a.n,"base":a.base,"optimization_level":a.level,"basis":["u","cx"],
    "seed_transpiler":73,"quantum_executed":False,"rows":[]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for name,builder in (("a44",a44.build),("a64",a64.build)):
   start=time.perf_counter()
   built=builder(a.n,a.base)
   qc=built[0] if isinstance(built,tuple) else built
   native=transpile(qc,basis_gates=["u","cx"],optimization_level=a.level,seed_transpiler=73)
   counts=dict(native.count_ops())
   row={"architecture":name,"qubits":native.num_qubits,"cx":counts.get("cx",0),
     "depth":native.depth(),"u":counts.get("u",0),"source_depth":qc.depth(),
     "compile_seconds":round(time.perf_counter()-start,3)}
   d["rows"].append(row);save()
   print(f"A73 N={a.n} LEVEL={a.level} {name.upper()} qubits={row['qubits']} CX={row['cx']} depth={row['depth']} seconds={row['compile_seconds']}",flush=True)
  a44row,a64row=d["rows"]
  d["a64_vs_a44"]={"cx_reduction_pct":round(100*(1-a64row["cx"]/a44row["cx"]),3),
   "depth_reduction_pct":round(100*(1-a64row["depth"]/a44row["depth"]),3),
   "additional_qubits":a64row["qubits"]-a44row["qubits"]}
  d["status"]="PASS_MATCHED_NATIVE_COST_NOT_QPE";save()
  print("A73 STATUS",d["status"],"A64_vs_A44",d["a64_vs_a44"],flush=True)
 except Exception:
  d["status"]="ERROR";d["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
