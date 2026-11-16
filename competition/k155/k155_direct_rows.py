#!/usr/bin/env python3
"""K155: in-place controlled partial row increments, exact signed 4-bit check.
Bounded demonstration; NOT a full Helios quantum arithmetic candidate.
"""
import argparse,collections,hashlib,json,random
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
def mcx(c,t,s):
 n=len(c)
 if n==0:return [("X",t)]
 if n==1:return [("CX",c[0],t)]
 if n==2:return [("CCX",c[0],c[1],t)]
 assert n-2<=len(s)
 chain=[("CCX",c[0],c[1],s[0])]
 for j in range(2,n-1):chain.append(("CCX",s[j-2],c[j],s[j-1]))
 return chain+[("CCX",s[n-3],c[-1],t)]+list(reversed(chain))
def conditional_power(controls,p,k,negative,scratch):
 gates=[]
 for t in reversed(range(k,len(p))):
  low=p[k:t]
  if negative:gates.extend(("X",z) for z in low)
  gates.extend(mcx(controls+low,p[t],scratch))
  if negative:gates.extend(("X",z) for z in reversed(low))
 return gates
def circuit(n):
 r=list(range(n));y=list(range(n,2*n));out=list(range(2*n,3*n))
 prod=list(range(3*n,5*n));scratch=list(range(5*n,7*n-1))
 forward=[]
 for i in range(n):
  for j in range(n):
   forward+=conditional_power([y[i],r[j]],prod,i+j,j==n-1,scratch)
 rounding=conditional_power([],prod,n,False,scratch)
 extract=[("CX",prod[min(2*n-1,n+1+j)],out[j]) for j in range(n)]
 return forward+rounding+extract+list(reversed(rounding))+list(reversed(forward)),{
  "data_bits":3*n,"product_bits":2*n,"carry_chain_scratch":len(scratch),
  "total_scratch":2*n+len(scratch),"total_wires":5*n+len(scratch)}
def execute(v,ops):
 for gate,*a in ops:
  if gate=="X":v^=1<<a[0]
  elif gate=="CX":v^=((v>>a[0])&1)<<a[1]
  elif gate=="CCX":v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
  else:raise ValueError(gate)
 return v
def check(n,ops):
 rng=random.Random(155+n);tested=0;mask=(1<<n)-1
 for r in range(1<<n):
  signed=r-(1<<n) if r&(1<<(n-1)) else r
  for y in range(1<<n):
   result=((signed*y+(1<<n))//(1<<(n+1)))&mask
   for d in (0,mask,rng.randrange(1<<n)):
    v=r|(y<<n)|(d<<(2*n))
    expected=r|(y<<n)|((d^result)<<(2*n))
    after=execute(v,ops)
    assert after==expected,(n,r,y,d,result,hex(after^expected))
    assert execute(after,ops)==v
    tested+=1
 return tested
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k155/results/direct_rows.json"))
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 summaries=[]
 for n in (2,3,4):
  ops,resources=circuit(n)
  cases=check(n,ops);counts=collections.Counter(op for op,*_ in ops)
  summaries.append({"width":n,"cases":cases,**dict(counts),**resources})
 assert summaries[-1]["cases"]==768 and summaries[-1]["CCX"]==888
 print("K155_SELFTEST PASS exact signed streaming, arbitrary XOR outputs, scratch cleanup, involution",flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 report={"status":"BOUNDED_DIRECT_ROW_ARITHMETIC_NOT_HELIOS","pinned_sha256":sha,
  "bounded_cases":summaries,
  "comparison":{"K154_CCX":240,"K154_scratch":17,
                "K155_CCX":888,"K155_scratch":15},
  "limits":["4-bit test only, no full 22-bit Helios candidate",
    "Saved 2 scratch but increased CCX 648 vs K154",
    "Not an optimum, nor a no-go theorem for low-workspace multiplication",
    "Measurement-based erasure needs correct X-basis phase feedback; naive Z measurement on live product decoheres"]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K155_RESULT",json.dumps({"CCX":888,"CX":6,"X":82,"scratch":15,
   "tested_basis_cases":768,"delta_CCX_vs_K154":648,
   "scratch_saved_vs_K154":2,"full_helios_candidate":False,
   "out":str(a.out)}),flush=True)
if __name__=="__main__":main()
