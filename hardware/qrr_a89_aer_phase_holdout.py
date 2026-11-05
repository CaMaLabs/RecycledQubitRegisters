#!/usr/bin/env python3
"""A89: real Aer gate-level dynamic QPE A84/A87B comparison with exact uniform null.

Controlled modular stages are the A88 implementations. This samples genuine
dynamic semiclassical phase readouts, not synthetic known-order frequencies.
Known order is computed only for post-hoc diagnostic phase lattice analysis.
"""
import argparse,collections,json,math,sys,time,traceback
from fractions import Fraction
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qrr_a88_integrated_qpe_ab import qpe
from qrr_a84_fused_carry_multiplier import build as a84
from qrr_a87b_direct_prefix_multiplier import build as a87b

def order(a,n):
 x=a%n
 for r in range(1,n+1):
  if x==1:return r
  x=x*a%n
 raise AssertionError("order not found")

def recover(n,a,bits,frequency,max_multiple):
 fraction=Fraction(frequency,1<<bits).limit_denominator(n)
 for mult in range(1,max_multiple+1):
  r=fraction.denominator*mult
  if r%2 or pow(a,r,n)!=1:continue
  z=pow(a,r//2,n)
  if z in (1,n-1):continue
  p=math.gcd(z-1,n);q=math.gcd(z+1,n)
  if 1<p<n and n%p==0:return sorted((p,n//p))
  if 1<q<n and n%q==0:return sorted((q,n//q))
 return None

def lattice_hit(freq,bits,r):
 # Circular distance from freq/2**bits to a lattice point j/r <= one bin.
 denominator=1<<bits
 return min(abs(freq*r-j*denominator) for j in range(r+1))<=r

def summarize(hist,n,base,bits,r,multiples):
 return {"shots":sum(hist.values()),
  "distinct_frequencies":len(hist),
  "verified_factor_count":sum(v for y,v in hist.items() if recover(n,base,bits,y,multiples)),
  "phase_lattice_hits":sum(v for y,v in hist.items() if lattice_hit(y,bits,r)),
  "histogram":dict(sorted((str(k),v) for k,v in hist.items()))}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15)
 p.add_argument("--base",type=int,default=2)
 p.add_argument("--bits",type=int,default=8)
 p.add_argument("--shots-per-seed",type=int,default=64)
 p.add_argument("--seeds",type=int,default=4)
 p.add_argument("--seed-start",type=int,default=8901)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--max-multiple",type=int,default=4)
 p.add_argument("--output",default="results/a89_n15_aer_holdout.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("coprime odd n>=9 required")
 if a.n>35:p.error("Aer guard: n<=35 only")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits out of range")
 if a.seeds<2 or a.shots_per_seed<1 or not 1<=a.max_multiple<=8:p.error("invalid seeds/shots/multiples")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 r=order(a.base,a.n)
 exact=collections.Counter({y:1 for y in range(1<<a.bits)})
 d={"experiment":"A89_GATE_LEVEL_DYNAMIC_QPE_INDEPENDENT_SEED_HOLDOUT",
  "status":"IN_PROGRESS","settings":vars(a),"offline_order_for_diagnostic_only":r,
  "architectures":{},"null":{"type":"EXACT_UNIFORM_ALL_FREQUENCIES",
   "factor_success_count":summarize(exact,a.n,a.base,a.bits,r,a.max_multiple)["verified_factor_count"],
   "lattice_hit_count":summarize(exact,a.n,a.base,a.bits,r,a.max_multiple)["phase_lattice_hits"],
   "total_frequencies":1<<a.bits},
  "limitations":["Ideal Aer MPS only, no noise or hardware claims",
   "The exact uniform null is not a matched physical-noise model",
   "Same simulator seeds are not independent hardware trials",
   "Order is computed offline only; it never enters the QPE circuit or factor postprocessor"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  simulator=AerSimulator(method="matrix_product_state")
  for label,builder in (("a84",a84),("a87b",a87b)):
   tic=time.perf_counter();q,cache=qpe(a.n,a.base,a.bits,builder,label)
   native=transpile(q,basis_gates=["u","cx"],optimization_level=a.level,seed_transpiler=89)
   row={"qubits":native.num_qubits,"cx":int(native.count_ops().get("cx",0)),
    "depth":native.depth(),"compile_seconds":round(time.perf_counter()-tic,3),
    "seed_cohorts":[]}
   d["architectures"][label]=row;save()
   aggregate=collections.Counter()
   for i in range(a.seeds):
    seed=a.seed_start+i;start=time.perf_counter()
    result=simulator.run(native,shots=a.shots_per_seed,seed_simulator=seed).result()
    counts=result.get_counts()
    hist=collections.Counter()
    for key,num in counts.items():hist[int(key.replace(" ",""),2)]+=num
    aggregate.update(hist)
    cohort={"seed":seed,**summarize(hist,a.n,a.base,a.bits,r,a.max_multiple),
            "seconds":round(time.perf_counter()-start,3)}
    row["seed_cohorts"].append(cohort);save()
    print("A89",label,"seed",seed,"factors",cohort["verified_factor_count"],
          "lattice",cohort["phase_lattice_hits"],flush=True)
   row["aggregate"]=summarize(aggregate,a.n,a.base,a.bits,r,a.max_multiple)
   save()
  l=d["architectures"]["a84"]["aggregate"];rr=d["architectures"]["a87b"]["aggregate"]
  left={int(k):v/l["shots"] for k,v in l["histogram"].items()}
  right={int(k):v/rr["shots"] for k,v in rr["histogram"].items()}
  d["comparison"]={"empirical_total_variation_distance":round(
    .5*sum(abs(left.get(y,0)-right.get(y,0)) for y in set(left)|set(right)),6),
    "delta_factor_success_count":rr["verified_factor_count"]-l["verified_factor_count"],
    "delta_lattice_hits":rr["phase_lattice_hits"]-l["phase_lattice_hits"],
    "cx_reduction_pct":round(100*(d["architectures"]["a84"]["cx"]-d["architectures"]["a87b"]["cx"])/d["architectures"]["a84"]["cx"],4)}
  d["status"]="PASS_AER_HOLDOUT_WITH_UNIFORM_NULL"
  save();print("A89 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:];save();raise
if __name__=="__main__":main()
