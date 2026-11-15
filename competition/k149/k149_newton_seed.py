#!/usr/bin/env python3
"""K149: full-domain exact-integer fixed-point Newton invsqrt feasibility.
Numerical surrogate ONLY; no reversible implementation, score, or KMX rewrite.
x=2^(2*k)*m with 1<=m<4. Uniform seed LUT separately on [1,2),[2,4).
y <- y*(3-m*y*y)/2 with nearest rounding after each Q multiplication.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
N=3133452
EPS=2**-24
def table(q,bins):
 a=np.arange(bins,dtype=np.float64)
 m1=1+(a+.5)/bins
 m2=2+2*(a+.5)/bins
 return np.rint(np.concatenate((1/np.sqrt(m1),1/np.sqrt(m2)))*(1<<q)).astype(np.int64)
def trial(xs,q,bins,iters=2,block=100000):
 if not(12<=q<=30) or bins<1 or bins&(bins-1):raise ValueError("invalid q or bins")
 scale=np.int64(1<<q);lut=table(q,bins)
 worst=[(0.,0)]*(iters+1);fails=[0]*(iters+1)
 for start in range(0,len(xs),block):
  x=xs[start:start+block].astype(np.int64)
  exponent=np.frexp(x.astype(np.float64))[1]-1
  k=exponent//2
  m=(x<<q)//np.left_shift(np.int64(1),2*k)
  hi=m>=2*scale
  index=np.where(hi,bins+(m-2*scale)*bins//(2*scale),(m-scale)*bins//scale)
  if np.any((index<0)|(index>=2*bins)):raise AssertionError("bad seed index")
  y=lut[index]
  ref=1/np.sqrt(x.astype(np.float64))
  for step in range(iters+1):
   v=(y.astype(np.float64)/scale)/np.left_shift(np.int64(1),k)
   error=np.abs(v-ref)/ref
   j=int(np.argmax(error));maximum=float(error[j])
   if maximum>worst[step][0]:worst[step]=(maximum,int(x[j]))
   fails[step]+=int(np.count_nonzero(error>=EPS))
   if step==iters:break
   if np.any((y<0)|(y>scale)):raise AssertionError("y bound")
   yy=(y*y+scale//2)//scale
   myy=(m*yy+scale//2)//scale
   factor=3*scale-myy
   if np.any((factor<0)|(factor>3*scale)):raise AssertionError("factor bound")
   y=(y*factor+scale)//(2*scale)
 return [{"iteration":i,"worst_relative_error":z,
  "tolerance_fraction":z/EPS,"worst_x":x,"violations":fails[i]}
  for i,(z,x) in enumerate(worst)]
def resource(q,iters):
 pp=q*(q+1)//2
 return {"variable_multiplications":3*iters,
 "schoolbook_truncated_partial_products_each":pp,
 "schoolbook_partial_product_proxy_total":pp*3*iters,
 "estimated_live_input_seed_and_product_bits":22+2*q,
 "baseline_qubits":62,
 "warning":"Proxy is NOT a universal lower bound; omits carries, cleanup, lookup and output phase."}
def selftest():
 r=trial(np.arange(1,1001,dtype=np.int64),28,32,2,100)
 assert r[0]["worst_relative_error"]>r[1]["worst_relative_error"]>r[2]["worst_relative_error"]
 assert trial(np.array([1,2,3,4,2**20,2**21,N]),30,64,2)[-1]["violations"]==0
 print("K149_SELFTEST PASS integer Newton, LUT addressing and numerical convergence",flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k149/results/newton_seed_report.json"))
 p.add_argument("--max-x",type=int,default=N)
 p.add_argument("--q",default="24,26,28,30")
 p.add_argument("--bins",default="32,64,128")
 p.add_argument("--iterations",type=int,default=2)
 p.add_argument("--block",type=int,default=100000)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args();selftest()
 if a.selftest:return
 if not(1<=a.max_x<=N and 1<=a.iterations<=4 and a.block>=100):p.error("bad bounds")
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 xs=np.arange(1,a.max_x+1,dtype=np.int64)
 rows=[]
 for q in sorted(set(int(v) for v in a.q.split(","))):
  for bins in sorted(set(int(v) for v in a.bins.split(","))):
   results=trial(xs,q,bins,a.iterations,a.block)
   row={"q":q,"bins_per_octave":bins,"lut_entries":2*bins,
    "steps":results,"resources":resource(q,a.iterations)}
   rows.append(row)
   print("K149_CASE",json.dumps({"q":q,"bins":bins,
    "final":results[-1],"resources":row["resources"]}),flush=True)
 good=sorted([r for r in rows if r["steps"][-1]["violations"]==0],
   key=lambda r:(r["lut_entries"],r["q"]))
 d={"status":"NUMERICAL_PASS_ONLY_NO_KICKMIX_CANDIDATE","source_sha256":sha,
  "tested_x":a.max_x,"nominal_relative_tolerance":EPS,
  "arithmetic":"exact integer Q fixed point; nearest rounded multiplication",
  "seed":"separate midpoint-LUT seeds over normalized [1,2),[2,4)",
  "rows":rows,"smallest_lut_pass":good[0] if good else None,
  "caveats":["Floating double oracle reference; fixed-point iterations use signed 64-bit integers",
   "Nominal tolerance is numerical surrogate, NOT an official Helios phase certificate",
   "No quantum lookup, reversible multiply, scratch clean, qubit feasibility or official score",
   "schoolbook product proxy is not a theoretical lower bound"]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(d,indent=2)+"\n")
 print("K149_RESULT",json.dumps({"configs":len(rows),"passing":len(good),
  "smallest_lut_pass":{"q":good[0]["q"],"bins":good[0]["bins_per_octave"],
    "worst_fraction":good[0]["steps"][-1]["tolerance_fraction"]} if good else None,
  "out":str(a.out)}),flush=True)
if __name__=="__main__":main()
