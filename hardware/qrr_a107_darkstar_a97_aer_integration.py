#!/usr/bin/env python3
"""A107: integrated Dark Star public odd-power policy + A97 recycled-QPE Aer.

The quantum measurement source is an actual dynamic QPE circuit using the
optimized A97 controlled modular multipliers (NOT a known-order generator).
Every measured integer is passed to the existing public-only strict continued-
fraction recovery and independently verified by modular exponentiation and gcd.

This is a SMALL textbook semiprime laboratory check, not RSA-2048, not a
production attack, not a quantum-value or physical-device demonstration.
No hidden factors or order enter circuit construction or postprocessing.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a88_integrated_qpe_ab import qpe,verify
from qrr_a97_adaptive_modadd_multiplier import build as a97
from dark_star_shor_staged_stopping_time_audit import recover_strict_verified

def builder_for(level,seed):
 def builder(n,k):
  return a97(n,k,level=level,seed=seed)[0]
 return builder

def run():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--ell",type=int,default=3)
 p.add_argument("--bits",type=int,default=12)
 p.add_argument("--shots",type=int,default=32)
 p.add_argument("--seed",type=int,default=10701)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--output",default="results/a107_darkstar_a97_aer.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or a.n>35:p.error("small-modulus Aer guard: odd 9<=n<=35")
 if math.gcd(a.n,a.base)!=1:p.error("base must be coprime")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits out of range")
 if not 1<=a.ell<=15 or not 1<=a.shots<=1024:p.error("invalid ell/shots")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A107_REAL_AER_A97_DARKSTAR_PUBLIC_ORDER_RECOVERY",
   "status":"IN_PROGRESS","settings":vars(a),"architectures":{},
   "zero_qpu_jobs":True,"limitations":[
     "N<=35 actual gate-level ideal Aer; not a cryptographic-size security test",
     "Odd-power base transform is public and is not necessarily better",
     "Classical preprocessing can already solve tiny N; no quantum advantage",
     "No physical backend noise, crosstalk, logical error correction or realistic RSA resource extrapolation"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  builder=builder_for(a.level,a.seed)
  simulator=AerSimulator(method="matrix_product_state")
  candidates=[("baseline_base",a.base%a.n),("odd_power_base",pow(a.base,a.ell,a.n))]
  for label,base in candidates:
   if math.gcd(base,a.n)!=1:raise AssertionError("transformed base not coprime")
   tic=time.perf_counter()
   q,stages=qpe(a.n,base,a.bits,builder,label)
   checked=sum(verify(a.n,k,builder) for k in stages)
   compiled=transpile(q,basis_gates=["u","cx"],optimization_level=a.level,
                      seed_transpiler=a.seed)
   result=simulator.run(compiled,shots=a.shots,seed_simulator=a.seed).result()
   if not result.success:raise RuntimeError(str(result.status))
   hist=collections.Counter({int(str(key).replace(" ",""),2):int(count)
      for key,count in result.get_counts().items()})
   found=0;verified_pairs=collections.Counter();events=[]
   for y,count in sorted(hist.items()):
    candidate=recover_strict_verified(y,a.bits,base,a.n)
    if candidate:
     factors=list(candidate["factors"])
     if len(factors)!=2 or factors[0]*factors[1]!=a.n:
      raise AssertionError("invalid factors from public verifier")
     found+=count
     verified_pairs[str(factors)]+=count
    events.append({"phase_integer":y,"shots":count,"public_recovery":candidate})
   row={"base":base,"base_exponent":1 if label=="baseline_base" else a.ell,
     "qubits":compiled.num_qubits,"distinct_stage_powers":len(stages),
     "checked_source_basis_states":checked,
     "native_cx":int(compiled.count_ops().get("cx",0)),
     "native_depth":int(compiled.depth()),"shots":a.shots,
     "publicly_verified_factor_shots":found,
     "verified_factor_histogram":dict(verified_pairs),
     "measurement_events":events,
     "elapsed_seconds":round(time.perf_counter()-tic,3)}
   d["architectures"][label]=row;save()
   print("A107",label,"base",base,"CX",row["native_cx"],"depth",row["native_depth"],
     "verified",found,"/",a.shots,"source_cases",checked,flush=True)
  left=d["architectures"]["baseline_base"];right=d["architectures"]["odd_power_base"]
  d["comparison"]={"odd_power_minus_baseline_verified_shots":
    right["publicly_verified_factor_shots"]-left["publicly_verified_factor_shots"],
    "delta_cx":right["native_cx"]-left["native_cx"],
    "delta_depth":right["native_depth"]-left["native_depth"],
    "interpretation":"Base transformation changes order and arithmetic; paired simulator seeds are not a calibrated quantum speedup comparison"}
  d["status"]="PASS_INTEGRATED_GATE_LEVEL_AER_AND_PUBLIC_RECOVERY"
  save();print("A107 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":run()
