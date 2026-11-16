#!/usr/bin/env python3
"""K152 exact reversible bounded-domain Newton-delta lookup.
Demonstrates actual X/CX/CCX gates, cleanup, and exact basis-state outputs.
NOT a full-domain 22-bit Helios candidate or reversible Newton multiplier.
"""
import argparse,collections,hashlib,json,math,random
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
Q1=14;Q2=26;B=32
T=[round((1<<Q1)/math.sqrt(1+(j+.5)/B)) for j in range(B)]
T += [round((1<<Q1)/math.sqrt(2+2*(j+.5)/B)) for j in range(B)]
def step(y,m,q):
 s=1<<q
 v=(y*y+s//2)//s
 w=(m*v+s//2)//s
 return (y*(3*s-w)+s)//(2*s)
def delta(x):
 if x==0:return 0
 k=(x.bit_length()-1)//2
 m=(x<<14)//(1<<(2*k));s=1<<14
 a=(B+(m-2*s)*B//(2*s)) if m>=2*s else ((m-s)*B//s)
 assert 0<=a<64
 y=step(T[a],m,14)
 v=y<<12
 z=step(v,(x<<26)//(1<<(2*k)),26)-v
 assert -(1<<13)<=z<(1<<13)
 return z
def anf(n):
 truth=[delta(x)&16383 for x in range(1<<n)]
 t=truth[:]
 for b in range(n):
  for i in range(1<<n):
   if i&(1<<b):t[i]^=t[i^(1<<b)]
 return [(i,w) for i,w in enumerate(t) if w],truth
def synth(n):
 assert 1<=n<=14
 terms,truth=anf(n);ops=[]
 def op(g,*a):ops.append((g,*a))
 for mask,word in terms:
  c=[i for i in range(n) if (mask>>i)&1]
  outputs=[36+j for j in range(14) if (word>>j)&1]
  if len(c)==0:
   for o in outputs:op("X",o)
  elif len(c)==1:
   for o in outputs:op("CX",c[0],o)
  elif len(c)==2:
   for o in outputs:op("CCX",c[0],c[1],o)
  else:
   # q50..q61 are 12 clean ancillas; len(c)-2 <= 12.
   chain=[("CCX",c[0],c[1],50)]
   for j in range(2,len(c)-1):
    chain.append(("CCX",50+j-2,c[j],50+j-1))
   ops.extend(chain)
   for o in outputs:op("CCX",50+len(c)-3,c[-1],o)
   ops.extend(reversed(chain))
 return ops,terms,truth
def run(v,ops):
 for g,*w in ops:
  if g=="X":v^=1<<w[0]
  elif g=="CX":v^=((v>>w[0])&1)<<w[1]
  elif g=="CCX":v^=(((v>>w[0])&1)&((v>>w[1])&1))<<w[2]
  else:raise AssertionError(g)
 return v
def verify(n,ops,truth,checks):
 rng=random.Random(29+n)
 sample=list(range(1<<n)) if (1<<n)<=checks else sorted(set(
  [0,1,(1<<n)-1]+[rng.randrange(1<<n) for _ in range(checks-3)]))
 for x in sample:
  y=rng.randrange(1<<14)
  d=rng.randrange(1<<14)
  before=x|(y<<22)|(d<<36)
  after=run(before,ops)
  expected=x|(y<<22)|((d^truth[x])<<36)
  assert after==expected,(n,x,hex(after^expected))
  assert run(after,ops)==before,(n,x,"not involution")
 return len(sample)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--widths",default="6,8,10")
 p.add_argument("--checks",type=int,default=96)
 p.add_argument("--emit-width",type=int,default=0)
 p.add_argument("--out",type=Path,default=Path("competition/k152/results/gate_audit.json"))
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 for n in (2,3,4):
  ops,terms,truth=synth(n)
  assert verify(n,ops,truth,1<<n)==1<<n
 print("K152_SELFTEST PASS reversible oracle, exact output, clean scratch",flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 widths=sorted(set(int(i) for i in a.widths.split(",")))
 if not widths or any(n<1 or n>14 for n in widths) or a.checks<3:
  p.error("1<=width<=14, checks>=3")
 rows=[]
 for n in widths:
  ops,terms,truth=synth(n)
  checked=verify(n,ops,truth,a.checks)
  counts=collections.Counter(g for g,*_ in ops)
  row={"input_bits":n,"inputs_covered":1<<n,"full_domain_covered":False,
       "toffoli_ccx_count":counts["CCX"],"cx":counts["CX"],
       "x":counts["X"],"total_gates":len(ops),
       "nonzero_anf_terms":len(terms),"tested_basis_cases":checked,
       "declared_qubits":62,"used_scratch":max(0,n-2),
       "status":"EXACT_BOUNDED_ORACLE_ONLY"}
  if n==a.emit_width:
   path=a.out.parent/f"k152_{n}bit_BOUNDED_NOT_HELIOS.kmx"
   path.parent.mkdir(parents=True,exist_ok=True)
   with path.open("w") as f:
    f.write("# BOUNDED INPUT ONLY: x < 2**%d. NOT A VALID FULL HELIOS SUBMISSION\n"%n)
    for g,*w in ops:f.write(g+" "+" ".join("q"+str(z) for z in w)+"\n")
   row["bounded_sample_kmx"]=str(path)
  rows.append(row)
  print("K152_CASE",json.dumps(row),flush=True)
 report={"status":"EXACT_GATE_COUNTS_ON_BOUNDED_DOMAINS_ONLY","pinned_sha256":sha,
         "layout":{"x_qubits":22,"y14_qubits":14,"delta_qubits":14,
                   "scratch_qubits":12,"total":62},
         "rows":rows,"full_helios_candidate":False,
         "limitations":["No full 22-input synthesis: ANF ladder needs up to 20 clean scratch.",
           "Oracle computes delta(x) by truth table, NOT the arithmetic Newton step.",
           "No official phase precision/score test or full-domain equivalent circuit."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K152_RESULT",json.dumps({"widths":widths,"candidate":False,"out":str(a.out)}),flush=True)
if __name__=="__main__":main()
