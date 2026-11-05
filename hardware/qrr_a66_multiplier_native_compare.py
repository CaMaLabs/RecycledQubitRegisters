#!/usr/bin/env python3
"""A66 controlled modular-multiplier A44/A64 native gate benchmark.

Defaults to small N=35 for affordable native comparison. For large N, source
counts only by default. Native compilation at large N requires --force-native.
All results are resource counts, not full quantum algorithm demonstrations.
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
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--native",action="store_true")
 p.add_argument("--force-native",action="store_true")
 p.add_argument("--output",default="results/a66_multiplier_compare.json")
 args=p.parse_args()
 if args.n>127 and args.native and not args.force_native:
  p.error("Native A44 for N>127 may be very expensive; rerun with --force-native only if resources permit")
 if math.gcd(args.n,args.a)!=1 or args.n<9 or args.n%2==0:p.error("odd N>=9 and coprime a needed")
 path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A66_A44_VS_A64_FULL_MULTIPLIER","status":"IN_PROGRESS",
    "n":args.n,"a":args.a,"comparison_basis":["u","cx"],
    "native_requested":args.native,"correctness_test":False,"rows":[]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for name,build in (("A44_GRAY_PATH",a44.build),("A64_BINARY",a64.build)):
   start=time.perf_counter()
   result=build(args.n,args.a);qc=result[0] if isinstance(result,tuple) else result
   row={"architecture":name,"logical_qubits":qc.num_qubits,
        "source_depth":qc.depth(),"source_counts":dict(qc.count_ops()),
        "source_seconds":round(time.perf_counter()-start,3)}
   if name=="A44_GRAY_PATH":row["mcx_vchain_instances"]=result[1]
   d["rows"].append(row);save()
   print("A66 SOURCE",name,"qubits",qc.num_qubits,"depth",qc.depth(),
         "counts",dict(qc.count_ops()),flush=True)
   if args.native:
    compiled=transpile(qc,basis_gates=["u","cx"],optimization_level=0,seed_transpiler=66)
    row["native_cx"]=compiled.count_ops().get("cx",0)
    row["native_depth"]=compiled.depth()
    row["native_ops"]=dict(compiled.count_ops())
    row["total_seconds"]=round(time.perf_counter()-start,3)
    save()
    print("A66 NATIVE",name,"CX",row["native_cx"],"depth",row["native_depth"],
          "seconds",row["total_seconds"],flush=True)
  if args.native:
   x,y=d["rows"]
   d["cx_ratio_A44_over_A64"]=round(x["native_cx"]/y["native_cx"],6) if y["native_cx"] else None
   d["depth_ratio_A44_over_A64"]=round(x["native_depth"]/y["native_depth"],6) if y["native_depth"] else None
  d["status"]="PASS_COST_COMPARISON" if args.native else "PASS_SOURCE_COST_ONLY"
  save();print("A66 STATUS",d["status"],"SAVED",path,flush=True)
 except Exception:
  d["status"]="ERROR";d["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
