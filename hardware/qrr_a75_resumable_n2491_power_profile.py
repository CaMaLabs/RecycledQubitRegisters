#!/usr/bin/env python3
"""A75: resumable per-power N2491 QPE arithmetic cost profiler.

Profiles separately compiled A44 and A64 modular multiplier stages rather
than allocating an enormous dynamic-QPE circuit. Predicts only the SUM of
isolated stage CX/depth, not the fully compiled/recycled QPE resources.
No quantum shots, paid runtime or hardware jobs.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a44_generic_modular_multiplier as a44
import qrr_a64_binary_modular_multiplier as a64

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=12)
 p.add_argument("--level",type=int,choices=(0,1),default=1)
 p.add_argument("--max-new-powers",type=int,default=3)
 p.add_argument("--output",default="results/a75_n2491_stage_profile.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base")
 if a.bits<1 or a.bits>2*a.n.bit_length():p.error("bits range")
 if a.max_new_powers<1:p.error("--max-new-powers must be >=1")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 powers=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
 counts=collections.Counter(power for power in powers if power!=1)
 unique=list(dict.fromkeys(power for power in powers if power!=1))
 settings={"n":a.n,"base":a.base,"bits":a.bits,"level":a.level}
 if path.exists():
  data=json.loads(path.read_text())
  if data.get("settings")!=settings:raise ValueError("Saved checkpoint settings mismatch; change --output")
 else:
  data={"experiment":"A75_ISOLATED_MODULAR_POWERS","settings":settings,
        "status":"IN_PROGRESS","rows":{},"notes":[
        "Per-stage native u/cx gate compilation, not full dynamic QPE compilation.",
        "Sums exclude phase, feedback, measurement, reset and cross-stage transpiler optimization.",
        "Arithmetic depth sum is sequential stage depth only; not complete QPE depth.",
        "No Aer shots or real hardware runtime."]}
 def save():path.write_text(json.dumps(data,indent=2)+"\n")
 save();new=0
 try:
  for power in unique:
   key=str(power)
   row=data["rows"].setdefault(key,{"power":power,"multiplicity":counts[power],"architectures":{}})
   # Fully completed powers must not consume the per-run budget.
   if all(name in row["architectures"] for name in ("a44","a64")):
    continue
   for name,builder in (("a44",a44.build),("a64",a64.build)):
    if name in row["architectures"]:continue
    start=time.perf_counter();obj=builder(a.n,power)
    qc=obj[0] if isinstance(obj,tuple) else obj
    native=transpile(qc,basis_gates=["u","cx"],optimization_level=a.level,seed_transpiler=75)
    row["architectures"][name]={"cx":int(native.count_ops().get("cx",0)),
      "depth":int(native.depth()),"qubits":qc.num_qubits,
      "compile_seconds":round(time.perf_counter()-start,3)}
    save()
    print(f"A75 STAGE power={power} repeats={counts[power]} {name} CX={row['architectures'][name]['cx']} depth={row['architectures'][name]['depth']}",flush=True)
   new+=1
   if new>=a.max_new_powers:break
  complete=all(len(data["rows"].get(str(x),{}).get("architectures",{}))==2 for x in unique)
  for name in ("a44","a64"):
   valid=[(x,data["rows"].get(str(x),{}).get("architectures",{}).get(name)) for x in unique]
   if all(v is not None for _,v in valid):
    data[name+"_isolated_stage_sum"]={"cx":sum(counts[x]*v["cx"] for x,v in valid),
       "depth":sum(counts[x]*v["depth"] for x,v in valid),
       "max_qubits":max(v["qubits"] for _,v in valid)}
  data["distinct_powers"]=len(unique)
  data["completed_powers"]=sum(len(data["rows"].get(str(x),{}).get("architectures",{}))==2 for x in unique)
  data["status"]="PASS_ISOLATED_STAGE_SUM_ESTIMATE_NOT_FULL_QPE" if complete else "PARTIAL_CHECKPOINT"
  save()
  print(f"A75 STATUS {data['status']} completed={data['completed_powers']}/{len(unique)}",flush=True)
  if complete:
   for name in ("a44","a64"):print("A75 ISOLATED_STAGE_SUM",name,data[name+"_isolated_stage_sum"],flush=True)
 except Exception:
  data["status"]="ERROR";data["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
