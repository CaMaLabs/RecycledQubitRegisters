#!/usr/bin/env python3
"""A57 orbit-state exact ideal modular permutation QPE.

NOT gate-level, NOT a QPU: cyclic orbit a^k mod N is calculated classically
and used as a compact Hilbert basis. Simulates exactly ideal controlled
multiplication, phase feedback, H, projective measurement, and reset.
Compare its order peaks against A51/A52 before extrapolating.
"""
import argparse,json,math,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def orbit(n,a):
 out=[]; seen=set();x=1
 while x not in seen:
  seen.add(x);out.append(x);x=x*a%n
 if x!=1:raise AssertionError("cycle did not return to 1")
 return out

def sample(n,a,bits,rng,orb):
 r=len(orb)
 # state after each phase-qubit measure/reset: normalized work ket
 work=np.zeros(r,dtype=np.complex128);work[0]=1
 measured=[0]*bits
 for j in range(bits-1,-1,-1):
  # |+> control followed by controlled multiplication by a^(2^j)
  c0=work/math.sqrt(2)
  c1=np.roll(work, (1<<j)%r)/math.sqrt(2)
  angle=sum(-2*math.pi/(1<<(t-j+1)) for t in range(bits-1,j,-1)
            if measured[bits-1-t])
  c1=c1*np.exp(1j*angle)
  zero=(c0+c1)/math.sqrt(2)
  one=(c0-c1)/math.sqrt(2)
  p1=float(np.vdot(one,one).real)
  p1=min(1.,max(0.,p1))
  bit=int(rng.random()<p1)
  chosen=one if bit else zero
  prob=p1 if bit else 1-p1
  if prob<=0:raise AssertionError("impossible measurement sampled")
  work=chosen/math.sqrt(prob)
  measured[bits-1-j]=bit
 frequency=sum(b<<i for i,b in enumerate(measured))
 return frequency

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=437)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=18)
 p.add_argument("--shots",type=int,default=64)
 p.add_argument("--seed",type=int,default=20261107)
 p.add_argument("--with-quaspy",action="store_true")
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--output",default="results/a57_orbit_qpe.json")
 a=p.parse_args()
 if math.gcd(a.n,a.base)!=1 or a.n%2!=1:p.error("base must be coprime to odd n")
 if a.shots<1 or a.shots>10000:p.error("shots must be 1..10000")
 if a.bits<=a.n.bit_length():p.error("phase bits must exceed modulus bitlength")
 t=time.perf_counter();orb=orbit(a.n,a.base);r=len(orb)
 rng=np.random.default_rng(a.seed)
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A57_EXACT_IDEAL_ORBIT_QPE","status":"IN_PROGRESS",
    "n":a.n,"base":a.base,"bits":a.bits,"seed":a.seed,"orbit_size":r,
    "provenance":"Classical exact quantum-state simulation using classically enumerated orbit, NOT gate-level, NOT QPU",
    "readouts":[]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 if a.with_quaspy:post.load_upstream(a.upstream)
 for i in range(a.shots):
  f=sample(a.n,a.base,a.bits,rng,orb)
  row={"frequency":f,"bitstring":format(f,f"0{a.bits}b")}
  if a.with_quaspy:
   q=post.recover(a.n,a.base,a.bits,f,method="ekera",budget=1000,timeout=2)
   if q.get("factors") is not None:assert math.prod(q["factors"])==a.n
   row["recovery_status"]=q["status"];row["factors"]=q.get("factors")
  d["readouts"].append(row)
  if (i+1)%8==0 or i+1==a.shots:
   save();print("A57",a.n,"shots",i+1,"/",a.shots,flush=True)
 d["status"]="PASS_IDEAL_ORBIT_SIMULATION_NOT_GATE_LEVEL"
 d["elapsed_seconds"]=round(time.perf_counter()-t,3)
 if a.with_quaspy:
  d["factor_successes"]=sum(x["factors"] is not None for x in d["readouts"])
 save()
 print("A57 STATUS",d["status"],"N",a.n,"orbit",r,"seconds",d["elapsed_seconds"],
       "factor_successes",d.get("factor_successes","not_run"),"SAVED",out,flush=True)
if __name__=="__main__":main()
