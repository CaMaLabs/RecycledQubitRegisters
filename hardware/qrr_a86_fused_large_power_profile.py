#!/usr/bin/env python3
"""A86: resumable A76/A84 isolated modular-power comparison at larger N.

This is NOT full dynamic recycled QPE transpilation. The result is a
multiplicity-weighted sum of individually compiled arithmetic stages.
No simulator shots, QPU runs, known factors, or known order.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a76_reduced_active_flag import build as a76
from qrr_a84_fused_carry_multiplier import build as a84

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--max-new-powers",type=int,default=6)
 p.add_argument("--output",default="results/a86_n2491_fused_power_profile.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("N odd >=9, base coprime")
 if not 1<=a.bits<=2*a.n.bit_length():p.error("bits 1..2w")
 if a.max_new_powers<1:p.error("max new powers must be positive")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 powers=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
 counts=collections.Counter(p for p in powers if p!=1)
 unique=list(dict.fromkeys(p for p in powers if p!=1))
 settings={"n":a.n,"base":a.base,"bits":a.bits,"level":a.level}
 if path.exists():
  d=json.loads(path.read_text())
  if d.get("settings")!=settings:raise ValueError("Checkpoint settings mismatch; change output path")
 else:
  d={"experiment":"A86_ISOLATED_A76_A84_POWER_PROFILE","settings":settings,
     "status":"IN_PROGRESS","rows":{},
     "limitations":["Independent stage compilation sums are not complete QPE resources",
       "No Aer shots, QPU execution, hardware noise, or native topology routing",
       "No factor/order oracle used; no classical factors passed to builders"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save();new=0
 try:
  for power in unique:
   key=str(power)
   row=d["rows"].setdefault(key,{"power":power,"multiplicity":counts[power],"architectures":{}})
   if all(name in row["architectures"] for name in ("a76","a84")):continue
   for name,builder in (("a76",a76),("a84",a84)):
    if name in row["architectures"]:continue
    t=time.perf_counter()
    native=transpile(builder(a.n,power),basis_gates=["u","cx"],
         optimization_level=a.level,seed_transpiler=86)
    row["architectures"][name]={"qubits":native.num_qubits,
      "cx":int(native.count_ops().get("cx",0)),"depth":native.depth(),
      "compile_seconds":round(time.perf_counter()-t,3)}
    save()
    print("A86 POWER",power,"repeat",counts[power],name,
      "CX",row["architectures"][name]["cx"],
      "depth",row["architectures"][name]["depth"],flush=True)
   new+=1
   if new>=a.max_new_powers:break
  completed=sum(len(d["rows"].get(str(p),{}).get("architectures",{}))==2 for p in unique)
  d["completed_powers"]=completed;d["distinct_powers"]=len(unique)
  if completed==len(unique):
   for name in ("a76","a84"):
    d[name+"_isolated_sum"]={"cx":sum(counts[p]*d["rows"][str(p)]["architectures"][name]["cx"] for p in unique),
      "depth":sum(counts[p]*d["rows"][str(p)]["architectures"][name]["depth"] for p in unique),
      "max_qubits":max(d["rows"][str(p)]["architectures"][name]["qubits"] for p in unique)}
   x=d["a76_isolated_sum"];y=d["a84_isolated_sum"]
   d["comparison"]={"cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
     "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4),
     "delta_cx":y["cx"]-x["cx"],"delta_depth":y["depth"]-x["depth"]}
   d["status"]="PASS_ISOLATED_POWER_COST_ONLY"
  else:d["status"]="PARTIAL_CHECKPOINT"
  save()
  print("A86 STATUS",d["status"],"completed",completed,"/",len(unique),flush=True)
  if "comparison" in d:print("A86 COMPARISON",d["comparison"],flush=True)
 except Exception:
  d["status"]="ERROR";d["error"]=traceback.format_exc()[-5000:];save();raise

if __name__=="__main__":main()
