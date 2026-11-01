#!/usr/bin/env python3
"""A54: independent controlled-power stage validation before larger semiprimes.

Tests every UNIQUE nonidentity controlled multiplication power used by A50's
18-bit N437 order finder, on deterministic basis probes with Aer. Also checks
control-off and scratch cleanup, and verifies each stage's inverse mapping at
the classical level. Uses no factor-recovery oracle or QPU.
"""
import argparse,json,math,random,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a53_gate_semantics_feedback_audit import stage_aer,feedback_audit
from qrr_a44_generic_modular_multiplier import independent_permutation_validation

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=437)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=18)
 p.add_argument("--threads",type=int,default=4)
 p.add_argument("--probes",type=int,default=3)
 p.add_argument("--seed",type=int,default=20261104)
 p.add_argument("--output",default="results/a54_controlled_powers_validation.json")
 a=p.parse_args()
 if not 1<=a.probes<=16:p.error("probes must be 1..16")
 if math.gcd(a.base,a.n)!=1:p.error("base must be coprime")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A54_ALL_UNIQUE_A50_CONTROLLED_POWERS","status":"IN_PROGRESS",
    "n":a.n,"base":a.base,"bits":a.bits,"qpu_jobs":0,"stages":[]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  rng=random.Random(a.seed)
  powers=sorted(set(pow(a.base,1<<j,a.n) for j in range(a.bits) if pow(a.base,1<<j,a.n)!=1))
  for power in powers:
   checked=independent_permutation_validation(a.n,power)
   inv=pow(power,-1,a.n)
   assert all((inv*(power*y%a.n))%a.n==y for y in range(a.n))
   ys=[0,1,a.n-1,(1<<a.n.bit_length())-1]
   ys+=rng.sample(range(1<<a.n.bit_length()),a.probes)
   inputs=[(1,y) for y in dict.fromkeys(ys)]+[(0,1),(0,a.n-1)]
   t=time.perf_counter()
   row=stage_aer(a.n,power,inputs,a.threads)
   row["classical_permutation_states"]=checked
   row["time_s"]=round(time.perf_counter()-t,3)
   d["stages"].append(row);save()
   print("A54 N",a.n,"power",power,"cases",len(inputs),"PASS",row["time_s"],"s",flush=True)
  d["feedback"]=feedback_audit(a.n,a.base,a.bits)
  d["status"]="PASS_SAMPLED_ALL_UNIQUE_POWERS_AND_STRUCTURAL_FEEDBACK"
  save()
 except Exception:
  d["status"]="FAIL_VALIDATION";d["error"]=traceback.format_exc()[-4000:]
  save();raise
 print("A54 STATUS",d["status"],"UNIQUE POWERS",len(powers),"SAVED",out,flush=True)
if __name__=="__main__":main()
