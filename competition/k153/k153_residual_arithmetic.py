#!/usr/bin/env python3
"""K153 exact Q14/Q26 Newton residual and gate-level reversible 14-bit adder.
K153 is NOT a full 22-bit Newton multiplier circuit or Helios candidate.
"""
import argparse,collections,hashlib,json,random
from pathlib import Path
import numpy as np
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
N=3133452;S14=1<<14;S26=1<<26;TOL=2**-24
def lut():
 j=np.arange(32,dtype=float)
 return np.rint(S14/np.sqrt(np.r_[1+(j+.5)/32,2+2*(j+.5)/32])).astype(np.int64)
def batch(lo,hi,t):
 x=np.arange(lo,hi,dtype=np.int64)
 k=(np.frexp(x.astype(float))[1]-1)//2
 div=np.left_shift(np.int64(1),2*k)
 m14=(x<<14)//div
 idx=np.where(m14>=2*S14,32+((m14-2*S14)*32)//(2*S14),(m14-S14)*32//S14)
 assert np.all((idx>=0)&(idx<64))
 y=t[idx];sq=(y*y+S14//2)//S14
 p=(m14*sq+S14//2)//S14
 y14=(y*(3*S14-p)+S14)//(2*S14)
 # Exact identity: rounded (y14<<12)^2 / 2^26 = (y14^2+2)//4.
 sq26=(y14*y14+2)//4
 m26=(x<<26)//div
 product=(m26*sq26+S26//2)//S26
 residual=S26-product
 correction=(y14*residual+(1<<14))//(1<<15)
 full=((y14<<12)*(3*S26-product)+S26)//(2*S26)
 assert np.array_equal(full,(y14<<12)+correction)
 actual=(full.astype(float)/S26)/np.left_shift(np.int64(1),k)
 err=np.abs(actual-1/np.sqrt(x.astype(float)))/(1/np.sqrt(x.astype(float)))
 return x,y14,residual,correction,err
def mcx(controls,target,scratch,ops):
 n=len(controls)
 if n==1:ops.append(("CX",controls[0],target));return
 if n==2:ops.append(("CCX",controls[0],controls[1],target));return
 if n-2>len(scratch):raise ValueError("not enough ancilla")
 chain=[("CCX",controls[0],controls[1],scratch[0])]
 for i in range(2,n-1):
  chain.append(("CCX",scratch[i-2],controls[i],scratch[i-1]))
 ops.extend(chain)
 ops.append(("CCX",scratch[n-3],controls[-1],target))
 ops.extend(reversed(chain))
def add_gates(n):
 if not 1<=n<=14:raise ValueError("width 1..14")
 a=list(range(36,36+n));b=list(range(22,22+n));scratch=list(range(50,62));ops=[]
 # High target first ensures lower carry controls read OLD b bits.
 for j in range(n):
  for bit in range(n-1,j-1,-1):
   mcx([a[j]]+b[j:bit],b[bit],scratch,ops)
 return ops
def execute(state,ops):
 for g,*q in ops:
  if g=="X":state^=1<<q[0]
  elif g=="CX":state^=((state>>q[0])&1)<<q[1]
  elif g=="CCX":state^=(((state>>q[0])&1)&((state>>q[1])&1))<<q[2]
  else:raise ValueError(g)
 return state
def verify(n,ops,count):
 rng=random.Random(153+n)
 cases=[(a,b) for a in range(1<<n) for b in range(1<<n)] if n<=4 else [(rng.randrange(1<<n),rng.randrange(1<<n)) for _ in range(count)]
 for a,b in cases:
  x=rng.randrange(1<<22)
  init=x|(b<<22)|(a<<36)
  result=execute(init,ops)
  expected=x|((((a+b)&((1<<n)-1))<<22))|(a<<36)
  assert result==expected,(n,a,b)
  assert execute(result,reversed(ops))==init
 return len(cases)
def selftest():
 for n in (2,3,4):
  gates=add_gates(n)
  assert verify(n,gates,30)==1<<(2*n)
 t=lut()
 for a,b in ((1,300),(100000,100200),(3120000,3120200)):
  *_,err=batch(a,b,t);assert not np.count_nonzero(err>=TOL)
 print("K153_SELFTEST PASS rounded residual identity and reversible modular-adder exhaustive small widths",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k153/results/residual_arithmetic.json"))
 p.add_argument("--max-x",type=int,default=N)
 p.add_argument("--chunk",type=int,default=100000)
 p.add_argument("--adder-width",type=int,default=14)
 p.add_argument("--adder-checks",type=int,default=256)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args();selftest()
 if a.selftest:return
 if not 1<=a.max_x<=N or not 1<=a.adder_width<=14 or a.chunk<100 or a.adder_checks<1:p.error("invalid bounds")
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 tab=lut();minr=maxr=mind=maxd=bad=0;worst=0.;at=0
 for lo in range(1,a.max_x+1,a.chunk):
  x,y,r,d,e=batch(lo,min(a.max_x+1,lo+a.chunk),tab)
  minr=min(minr,int(r.min()));maxr=max(maxr,int(r.max()))
  mind=min(mind,int(d.min()));maxd=max(maxd,int(d.max()))
  bad+=int(np.count_nonzero(e>=TOL))
  j=int(np.argmax(e))
  if float(e[j])>worst:worst=float(e[j]);at=int(x[j])
 gates=add_gates(a.adder_width);checked=verify(a.adder_width,gates,a.adder_checks)
 counts=collections.Counter(g for g,*_ in gates)
 rb=max(maxr.bit_length()+1,(~minr).bit_length()+1)
 db=max(maxd.bit_length()+1,(~mind).bit_length()+1)
 report={"status":"EXACT_INTEGER_RESIDUAL_AND_REVERSIBLE_ADDER_ONLY",
  "source_sha256":sha,"inputs_tested":a.max_x,"numerical_violations":bad,
  "worst_error_fraction":worst/TOL,"worst_x":at,
  "residual_min":minr,"residual_max":maxr,"residual_signed_bits":rb,
  "delta_min":mind,"delta_max":maxd,"delta_signed_bits":db,
  "identities":["squared_q26=(y14*y14+2)//4",
   "product_q26=(m26*squared_q26+2^25)//2^26",
   "residual_q26=2^26-product_q26",
   "delta=(y14*residual_q26+2^14)//2^15",
   "y26=(y14<<12)+delta"],
  "adder":{"width":a.adder_width,"CCX":counts["CCX"],"CX":counts["CX"],
   "basis_cases":checked,"max_scratch":max(0,a.adder_width-2),"allocated_total":62,
   "primitive":"(a,b,0)->(a,(b+a) mod 2^n,0)"},
  "warnings":["No gate-level reversible multiplier, residual computation, phase application or cleanup for Newton",
   "The 16-bit residual cannot be stored simultaneously with 50 data bits using only 62 qubits",
   "The adder is a separately verified primitive, not a complete correction circuit",
   "No Kickmix candidate or official score verification"]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K153_RESULT",json.dumps({"numerical_violations":bad,"residual_range":[minr,maxr],
  "residual_bits":rb,"delta_range":[mind,maxd],"delta_bits":db,
  "adder_ccx":counts["CCX"],"adder_cx":counts["CX"],
  "adder_scratch":max(0,a.adder_width-2),"status":report["status"]}),flush=True)
 print("K153_REPORT",str(a.out),flush=True)
if __name__=="__main__":main()
