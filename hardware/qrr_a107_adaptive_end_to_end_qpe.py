#!/usr/bin/env python3
"""A107: end-to-end recycled-QPE + adaptive A97 + order/factor recovery.

Build actual dynamic semiclassical QPE from exact gate-level A87b or A97
controlled modular multipliers. Use independently seeded ideal Aer MPS
shots and the same classical continued-fraction recovery for each.
Includes exhaustive source-basis checks for every distinct modular power
and resource comparison of fully transpiled QPE circuits.

This does NOT integrate Dark Star periodic-prime pruning or ML-KEM/LWE
research; neither is claimed by this experiment. Does not use A106:
A106 has a much larger register and is not verified / cost-promoted yet.
No QPU run, no cryptographic-strength factoring claim.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a88_integrated_qpe_ab import qpe,verify
from qrr_a87b_direct_prefix_multiplier import build as a87b
from qrr_a97_adaptive_modadd_multiplier import build as adaptive
from qrr_a89_aer_phase_holdout import order,recover,lattice_hit

def summarize(hist,n,base,bits,r,multiples):
 return {"shots":sum(hist.values()),
   "distinct_frequencies":len(hist),
   "verified_factor_count":sum(count for f,count in hist.items()
     if recover(n,base,bits,f,multiples) is not None),
   "phase_lattice_hits":sum(count for f,count in hist.items()
     if lattice_hit(f,bits,r)),
   "frequencies":dict(sorted((str(f),count) for f,count in hist.items()))}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15)
 p.add_argument("--base",type=int,default=2)
 p.add_argument("--bits",type=int,default=8)
 p.add_argument("--shots-per-seed",type=int,default=32)
 p.add_argument("--seeds",type=int,default=3)
 p.add_argument("--seed-start",type=int,default=10701)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--max-multiple",type=int,default=4)
 p.add_argument("--source-only",action="store_true")
 p.add_argument("--output",default="results/a107_adaptive_end_to_end_qpe.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base required")
 if a.n>35 and not a.source_only:p.error("Use --source-only for N>35 (Aer memory guard)")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits out of range")
 if a.shots_per_seed<1 or a.seeds<2 or not 1<=a.max_multiple<=8:p.error("invalid sample settings")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"A107_A97_ADAPTIVE_FULL_DYNAMIC_RECYCLED_QPE_ORDER_RECOVERY",
   "settings":vars(a),"status":"IN_PROGRESS",
   "stage_powers":sorted(set(pow(a.base,1<<j,a.n) for j in range(a.bits))-{1}),
   "architectures":{},"qpu_jobs_submitted":0,
   "integration_scope":{"included":["A87b full modular multiplier baseline","A97 per-constant adaptive adder selection","Actual dynamic QPE with recycled phase qubit","Classical continued-fraction order and factor recovery","Exact-uniform-frequency null","Matched local u/cx compilation","Seeded ideal MPS measurement"],
     "not_included":["Dark Star periodic-prime preprocessing","Historical recursive pruning approaches",
       "LWE / ML-KEM attacks","A106 carry-save multiplier (awaits validation)","Quantum error correction",
       "Physical QPU execution","Cryptographic-strength RSA attack"]},
   "limitations":["Ideal MPS; no hardware noise, calibration, fault tolerance, or physical factoring claim",
     "Same random seeds do not imply independent hardware sampling",
     "Source-basis tests alone do not prove phase equivalence",
     "N<=35 for full native QPE and sampled Aer; larger N source-only"]}
 def save():path.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  r=order(a.base,a.n)
  data["reference_order_for_diagnostics_only"]=r
  null=collections.Counter({i:1 for i in range(1<<a.bits)})
  data["exact_uniform_null"]=summarize(null,a.n,a.base,a.bits,r,a.max_multiple)
  builders={
   "a87b":a87b,
   "a97":lambda n,k:adaptive(n,k,level=a.level,seed=a.seed_start,objective="cx")[0]}
  for name,builder in builders.items():
   tick=time.perf_counter()
   q,cache=qpe(a.n,a.base,a.bits,builder,name)
   row={"qubits":q.num_qubits,"clbits":q.num_clbits,
     "distinct_nonidentity_stages":len(cache),
     "top_level_ops":len(q.data),
     "verified_stage_basis_cases":0,
     "seed_cohorts":[]}
   data["architectures"][name]=row;save()
   for k in sorted(cache):
    cases=verify(a.n,k,builder)
    row["verified_stage_basis_cases"]+=cases
    print("A107 VERIFY",name,"power",k,"cases",cases,flush=True)
   if a.source_only:
    row["build_seconds"]=round(time.perf_counter()-tick,3)
    save();print("A107 SOURCE",name,row["qubits"],"qubits",flush=True)
    continue
   native=transpile(q,basis_gates=["u","cx"],
     optimization_level=a.level,seed_transpiler=a.seed_start)
   row["native"]={"cx":int(native.count_ops().get("cx",0)),
     "depth":int(native.depth()),"qubits":native.num_qubits}
   row["build_seconds"]=round(time.perf_counter()-tick,3);save()
   print("A107 NATIVE",name,row["native"],flush=True)
   aggregate=collections.Counter()
   for i in range(a.seeds):
    seed=a.seed_start+i
    sim=AerSimulator(method="matrix_product_state")
    result=sim.run(native,shots=a.shots_per_seed,seed_simulator=seed).result()
    if not result.success:raise RuntimeError(result.status)
    hist=collections.Counter({int(key.replace(" ",""),2):v for key,v in result.get_counts().items()})
    aggregate.update(hist)
    cohort={"seed":seed,**summarize(hist,a.n,a.base,a.bits,r,a.max_multiple)}
    row["seed_cohorts"].append(cohort);save()
    print("A107 SHOTS",name,seed,"factor",cohort["verified_factor_count"],
       "lattice",cohort["phase_lattice_hits"],flush=True)
   row["aggregate"]=summarize(aggregate,a.n,a.base,a.bits,r,a.max_multiple)
   save()
  if a.source_only:
   data["status"]="PASS_BOXED_SOURCE_QPE_AND_STAGE_BASIS"
  else:
   l=data["architectures"]["a87b"];v=data["architectures"]["a97"]
   hist_l={int(k):val/l["aggregate"]["shots"] for k,val in l["aggregate"]["frequencies"].items()}
   hist_v={int(k):val/v["aggregate"]["shots"] for k,val in v["aggregate"]["frequencies"].items()}
   data["comparison"]={
     "cx_reduction_pct":round(100*(l["native"]["cx"]-v["native"]["cx"])/l["native"]["cx"],4),
     "depth_reduction_pct":round(100*(l["native"]["depth"]-v["native"]["depth"])/l["native"]["depth"],4),
     "factor_success_difference":v["aggregate"]["verified_factor_count"]-l["aggregate"]["verified_factor_count"],
     "phase_lattice_hit_difference":v["aggregate"]["phase_lattice_hits"]-l["aggregate"]["phase_lattice_hits"],
     "empirical_total_variation_distance":round(
       .5*sum(abs(hist_l.get(k,0)-hist_v.get(k,0)) for k in set(hist_l)|set(hist_v)),6)}
   data["status"]="PASS_FULL_QPE_AND_IDEAL_AER_PHASE_HOLDOUT"
  save();print("A107 STATUS",data["status"],data.get("comparison",{}),flush=True)
 except Exception:
  data["status"]="FAIL";data["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
