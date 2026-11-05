#!/usr/bin/env python3
"""A58: independently seeded ideal-orbit QPE vs matched uniform-frequency null.

Classically enumerates order-orbit; not gate-level and not quantum advantage.
Writes checkpoint after every arm. Integer timeout required by pinned Quaspy.
"""
import argparse,json,math,random,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
from qrr_a57_exact_orbit_qpe import orbit,sample
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--moduli",nargs="+",type=int,default=[899,1147,1763,2491])
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--shots",type=int,default=128)
 p.add_argument("--seeds",nargs="+",type=int,default=[20261109,20261110])
 p.add_argument("--budget",type=int,default=1000)
 p.add_argument("--timeout",type=int,default=2)
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--output",default="results/a58_ideal_scaling_null.json")
 a=p.parse_args()
 if not 1<=a.shots<=1000:p.error("shots outside 1..1000")
 if a.timeout<1 or a.budget<1:p.error("timeout and budget must be positive")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"A58_IDEAL_ORBIT_VS_UNIFORM_NULL","status":"IN_PROGRESS",
       "provenance":"classically enumerated modular orbit; ideal quantum-state simulation, not gate-level or QPU",
       "shots_per_arm":a.shots,"seeds":a.seeds,"rows":[]}
 def save():out.write_text(json.dumps(data,indent=2)+"\n")
 save();post.load_upstream(a.upstream)
 for n in a.moduli:
  if n%2==0 or math.gcd(n,a.base)!=1:p.error(f"invalid odd modulus/base N={n}")
  bits=2*n.bit_length()
  orb=orbit(n,a.base)
  for seed in a.seeds:
   rng=np.random.default_rng(seed^(n<<8))
   null_rng=random.Random(seed^(n<<9)^0xA58)
   arms={"ideal_orbit":[sample(n,a.base,bits,rng,orb) for _ in range(a.shots)],
         "uniform_random":[null_rng.randrange(1<<bits) for _ in range(a.shots)]}
   for arm,freqs in arms.items():
    row={"n":n,"base":a.base,"bits":bits,"orbit_length_classical_reference":len(orb),
         "seed":seed,"cohort":arm,"cases":[],"status":"IN_PROGRESS"}
    data["rows"].append(row);save()
    t=time.perf_counter()
    for f in freqs:
     result=post.recover(n,a.base,bits,f,method="ekera",budget=a.budget,timeout=a.timeout)
     if result["status"]=="ERROR":raise RuntimeError(f"Quaspy ERROR N={n} {arm}")
     factors=result.get("factors")
     if factors is not None:assert math.prod(factors)==n
     row["cases"].append({"frequency":f,"status":result["status"],"factors":factors,
                          "candidate_exponent":result.get("candidate_exponent")})
     save()
    row["successes"]=sum(x["factors"] is not None for x in row["cases"])
    row["seconds"]=round(time.perf_counter()-t,4)
    row["status"]="COMPLETE";save()
    print("A58",n,"bits",bits,"seed",seed,arm,row["successes"],"/",a.shots,"s",row["seconds"],flush=True)
 data["status"]="PASS_IDEAL_ORBIT_NULL_CONTROL_SWEEP_NOT_GATE_LEVEL"
 save();print("A58 STATUS",data["status"],"SAVED",out,flush=True)
if __name__=="__main__":main()
