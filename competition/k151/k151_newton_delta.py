#!/usr/bin/env python3
"""K151: exhaustive Q14->Q26 Newton delta feasibility, not a Kickmix gate circuit."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
N=3133452
TOL=2.0**-24
def seed_lut(q,b):
 a=np.arange(b,dtype=float)
 m=np.r_[1+(a+.5)/b,2+2*(a+.5)/b]
 return np.rint((1<<q)/np.sqrt(m)).astype(np.int64)
def newton(y,m,q):
 s=np.int64(1<<q)
 sq=(y*y+s//2)//s
 p=(m*sq+s//2)//s
 return (y*(3*s-p)+s)//(2*s)
def batch(lo,hi,q1,q2,b,lut):
 x=np.arange(lo,hi,dtype=np.int64)
 e=np.frexp(x.astype(float))[1]-1
 k=e//2
 div=np.left_shift(np.int64(1),2*k)
 s1=np.int64(1<<q1)
 m1=(x<<q1)//div
 idx=np.where(m1>=2*s1,b+((m1-2*s1)*b)//(2*s1),((m1-s1)*b)//s1)
 assert np.all((idx>=0)&(idx<2*b))
 y1=newton(lut[idx],m1,q1)
 base=y1<<(q2-q1)
 m2=(x<<q2)//div
 y2=newton(base,m2,q2)
 delta=y2-base
 assert np.array_equal(base+delta,y2)
 actual=(y2.astype(float)/(1<<q2))/np.left_shift(np.int64(1),k)
 ref=1/np.sqrt(x.astype(float))
 return x,y1,y2,delta,np.abs(actual-ref)/ref
def analyze(n,q1,q2,b,chunk):
 lut=seed_lut(q1,b)
 low=0;high=0;max1=0;max2=0;worst=0.;at=0;fails=0
 counts={"negative":0,"positive":0,"zero":0}
 for start in range(1,n+1,chunk):
  x,y1,y2,d,err=batch(start,min(n+1,start+chunk),q1,q2,b,lut)
  low=min(low,int(d.min()));high=max(high,int(d.max()))
  max1=max(max1,int(y1.max()));max2=max(max2,int(y2.max()))
  counts["negative"]+=int(np.count_nonzero(d<0))
  counts["positive"]+=int(np.count_nonzero(d>0))
  counts["zero"]+=int(np.count_nonzero(d==0))
  fails+=int(np.count_nonzero(err>=TOL))
  j=int(np.argmax(err))
  if float(err[j])>worst:worst=float(err[j]);at=int(x[j])
 width=max(1,high.bit_length()+1,(~low).bit_length()+1)
 bits1=max1.bit_length();bits2=max2.bit_length()
 return {"domain":[1,n],"first_q":q1,"last_q":q2,"lookup_entries":2*b,
  "numerical_violations":fails,"worst_relative_error":worst,
  "worst_fraction_of_tolerance":worst/TOL,"worst_x":at,
  "signed_delta_min":low,"signed_delta_max":high,"signed_delta_bits":width,
  "first_estimate_bits":bits1,"second_estimate_bits":bits2,
  "baseline_naive_register_bits":22+bits1+bits2,
  "delta_register_bits":22+bits1+width,
  "nominal_remaining_qubits":62-(22+bits1+width),
  "sign_counts":counts,
  "reversible_map":"(x,y1,out)->(x,y1,out XOR delta(x,y1))",
  "limitations":["Statistical ranges established only on actual seeded input domain, not arbitrary y1 states",
  "No reversible gate-level implementation of delta and clean scratch",
  "XOR oracle bijective only if input remains and temp work is clean",
  "No evidence remaining qubits suffice for arithmetic",
  "No official verifier, KMX candidate, phase tolerance or score improvement"]}
def selftest():
 lut=seed_lut(14,32)
 for a,z in ((1,300),(300,1000),(100000,100100)):
  x,y1,y2,d,e=batch(a,z,14,26,32,lut)
  assert np.array_equal((y1<<12)+d,y2)
 for delta in (-12,0,128):
  mask=(1<<27)-1
  for out in (0,1,1234):
   assert (out^(delta&mask)^(delta&mask))==out
 print("K151_SELFTEST PASS delta recovery and XOR involution",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k151/results/delta_feasibility.json"))
 p.add_argument("--max-x",type=int,default=N)
 p.add_argument("--first-q",type=int,default=14)
 p.add_argument("--last-q",type=int,default=26)
 p.add_argument("--bins",type=int,default=32)
 p.add_argument("--chunk",type=int,default=100000)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args();selftest()
 if a.selftest:return
 if not(1<=a.max_x<=N and 10<=a.first_q<=a.last_q<=30 and a.bins>0 and not(a.bins&(a.bins-1)) and a.chunk>=100):p.error("invalid bounds")
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 report=analyze(a.max_x,a.first_q,a.last_q,a.bins,a.chunk)
 report["status"]="CORRECTION_WIDTH_ONLY_NO_QUANTUM_REWRITE";report["pinned_sha256"]=sha
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K151_RESULT",json.dumps({k:report[k] for k in ("numerical_violations","worst_fraction_of_tolerance","signed_delta_min","signed_delta_max","signed_delta_bits","delta_register_bits","nominal_remaining_qubits")}),flush=True)
 print("K151_REPORT",str(a.out),flush=True)
if __name__=="__main__":main()
