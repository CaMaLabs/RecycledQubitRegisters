#!/usr/bin/env python3
"""A87b: direct controlled-prefix encoding for carry-wrap predicate cleanup.

A84 implements controlled_ge by computing a threshold into an ancilla,
using CCX, and uncomputing the threshold. This candidate expands the
threshold's disjoint prefix indicators into condition-controlled MCX gates.
It performs exactly the same XOR predicate without temporary computation.

This is not radix-16; it is comparator predicate/Boolean encoding synthesis.
All gates are real reversible source instructions; test clean ancilla and
exact truth table before interpreting native resource results.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a61_binary_modular_adder import ge,add_constant,flip_pattern
from qrr_a65_reversible_basis_exhaustive import instruction_stream,evaluate
from qrr_a84_fused_carry_multiplier import build as a84_build,fused_add as a84_add

def conditioned_ge(q,work,target,threshold,condition):
 w=len(work);limit=1<<w
 if threshold<=0:q.cx(condition,target);return
 if threshold>=limit:return
 for j in range(w-1,-1,-1):
  if (threshold>>j)&1:continue
  positions=[j]+list(range(j+1,w))
  pattern=1
  for t,bit in enumerate(positions[1:],1):
   pattern|=((threshold>>bit)&1)<<t
  flip_pattern(q,[condition]+[work[b] for b in positions],target,1|(pattern<<1))
 flip_pattern(q,[condition]+work,target,1|(threshold<<1))

def add(n,k,direct=True):
 if n<3 or n%2!=1:raise ValueError("odd n")
 w=n.bit_length();k%=n
 q=QuantumCircuit(w+4)
 c=q.qubits[0];work=list(q.qubits[1:1+w])
 valid,wrap,pred=q.qubits[w+1:w+4]
 if not k:return q
 q.x(valid);ge(q,work,valid,n)
 ge(q,work,wrap,n-k);ge(q,work,wrap,n)
 for value,flag in ((k,valid),(-n,wrap)):
  q.ccx(c,flag,pred)
  add_constant(q,work,value,pred)
  q.ccx(c,flag,pred)
 def controlled(threshold,target,condition):
  if direct:conditioned_ge(q,work,target,threshold,condition)
  else:
   ge(q,work,pred,threshold);q.ccx(condition,pred,target)
   ge(q,work,pred,threshold)
 q.x(c)
 controlled(n-k,wrap,c);controlled(n,wrap,c)
 q.x(c)
 q.cx(c,wrap);controlled(k,wrap,c)
 q.x(valid);ge(q,work,valid,n)
 return q

def build(n,a):
 if n<3 or n%2!=1 or math.gcd(n,a)!=1:raise ValueError("odd n and coprime a")
 w=n.bit_length();a%=n;inv=pow(a,-1,n)
 q=QuantumCircuit(2*w+6)
 c=q.qubits[0];x=list(q.qubits[1:1+w]);y=list(q.qubits[1+w:1+2*w])
 active,enable,lv,lw,lp=q.qubits[1+2*w:]
 def toggle():
  q.cx(c,active);ge(q,x+[c],active,(1<<w)+n)
 toggle()
 cache={}
 def accumulate(source,target,coef):
  for j,s in enumerate(source):
   k=(coef*(1<<j))%n
   if not k:continue
   q.ccx(active,s,enable)
   if k not in cache:cache[k]=add(n,k)
   q.compose(cache[k],qubits=[enable]+target+[lv,lw,lp],inplace=True)
   q.ccx(active,s,enable)
 accumulate(x,y,a)
 for xi,yi in zip(x,y):q.cswap(active,xi,yi)
 accumulate(x,y,-inv)
 toggle()
 return q

def verify_adder(n,k,builder):
 qc=builder(n,k);stream=instruction_stream(qc);w=n.bit_length()
 for c in (0,1):
  for y in range(1<<w):
   actual=evaluate(stream,c|(y<<1))
   dest=(y+k)%n if c and y<n else y
   expected=c|(dest<<1)
   if actual!=expected:raise AssertionError(f"adder N={n} k={k} c={c} y={y} actual={actual} expected={expected}")
 return 2*(1<<w)

def verify_multiplier(n,k,builder):
 qc=builder(n,k);stream=instruction_stream(qc);w=n.bit_length()
 for c in (0,1):
  for x in range(1<<w):
   actual=evaluate(stream,c|(x<<1))
   dest=k*x%n if c and x<n else x
   expected=c|(dest<<1)
   if actual!=expected:raise AssertionError(f"mult N={n} k={k} c={c} x={x} actual={actual} expected={expected}")
 return 2*(1<<w)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--k",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--output",default="results/a87b_direct_prefix.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.k)!=1:p.error("odd n >=9 and coprime k")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A87B_DIRECT_CONTROLLED_PREFIX_CARRY_CLEANUP",
    "status":"IN_PROGRESS","n":a.n,"k":a.k,"level":a.level,"rows":[],
    "claim_limit":"Direct predicate resynthesis; not radix-16, full QPE or noise validation"}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for n in list(dict.fromkeys((15,a.n))):
   constants=list(dict.fromkeys((1,n//2,n-1)))
   for k in constants:
    check=verify_adder(n,k,add)
    print("A87B ADDER PASS",n,k,check,flush=True)
  for name,builder in (("a84",a84_build),("a87b",build)):
   t=time.perf_counter()
   cases=verify_multiplier(a.n,a.k,builder)
   circuit=builder(a.n,a.k)
   native=transpile(circuit,basis_gates=["u","cx"],
       optimization_level=a.level,seed_transpiler=87)
   row={"architecture":name,"qubits":native.num_qubits,
     "cx":int(native.count_ops().get("cx",0)),"depth":native.depth(),
     "exhaustive_basis_cases":cases,"seconds":round(time.perf_counter()-t,3)}
   d["rows"].append(row);save()
   print("A87B COST",name,row,flush=True)
  a0,a1=d["rows"]
  d["comparison"]={"delta_cx":a1["cx"]-a0["cx"],
    "delta_depth":a1["depth"]-a0["depth"],
    "cx_reduction_pct":round(100*(a0["cx"]-a1["cx"])/a0["cx"],4),
    "depth_reduction_pct":round(100*(a0["depth"]-a1["depth"])/a0["depth"],4)}
  d["status"]="PASS_EXHAUSTIVE_SOURCE_AND_NATIVE_COST"
  save()
  print("A87B STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:];save();raise
if __name__=="__main__":main()
