#!/usr/bin/env python3
"""A96: dyadic interval-prefix synthesis for wrap flags in modular arithmetic.

A87b computes [N-k <= x < N] as ge(x,N-k) XOR ge(x,N).
A96 synthesizes this *interval directly* into disjoint aligned binary
prefix blocks. It removes redundant comparator work and can share logic
between the initial wrap computation and the control-off cleanup.

The interval cover is exact for every w-bit x; out-of-range x>=N remains
unchanged. No new ancillas. Correctness must pass exhaustive computational
basis tests of the real reversible circuit before promoting any improvement.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a61_binary_modular_adder import ge,add_constant,flip_pattern
from qrr_a87b_direct_prefix_multiplier import (
 build as baseline_build,add as baseline_add,conditioned_ge,
 verify_adder,verify_multiplier
)

def interval_blocks(lo,hi,width):
 """Minimal aligned dyadic partition of [lo,hi); (prefix_bits,pattern)."""
 bound=1<<width
 if not 0<=lo<=hi<=bound:raise ValueError("invalid interval")
 result=[]
 x=lo
 while x<hi:
  # Largest aligned block starting at x and fitting remaining interval.
  aligned=(x & -x).bit_length()-1 if x else width
  size_power=min(aligned,(hi-x).bit_length()-1)
  result.append((width-size_power,x>>size_power))
  x+=1<<size_power
 return result

def interval_xor(q,work,target,lo,hi,condition=None):
 """XOR [lo<=work<hi] (and condition if supplied) into target."""
 width=len(work)
 for prefix_bits,pattern in interval_blocks(lo,hi,width):
  # The high prefix bits are the only work controls needed.
  first=width-prefix_bits
  controls=[work[i] for i in range(first,width)]
  if condition is not None:
   controls=[condition]+controls
   pattern=(pattern<<1)|1
  flip_pattern(q,controls,target,pattern)

def add(n,k):
 if n<3 or n%2!=1:raise ValueError("odd n")
 w=n.bit_length();k%=n
 q=QuantumCircuit(w+4)
 c=q.qubits[0];work=list(q.qubits[1:1+w])
 valid,wrap,pred=q.qubits[w+1:w+4]
 if not k:return q
 q.x(valid);ge(q,work,valid,n)
 # Directly synthesize [N-k <= x < N] rather than two GE predicates.
 interval_xor(q,work,wrap,n-k,n)
 for value,flag in ((k,valid),(-n,wrap)):
  q.ccx(c,flag,pred)
  add_constant(q,work,value,pred)
  q.ccx(c,flag,pred)
 # Control off: reverse the original wrap flag with a single interval.
 q.x(c)
 interval_xor(q,work,wrap,n-k,n,condition=c)
 q.x(c)
 # Control on: wrap correction flag clears via output < k.
 q.cx(c,wrap)
 conditioned_ge(q,work,wrap,k,c)
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
   if k==0:continue
   q.ccx(active,s,enable)
   if k not in cache:cache[k]=add(n,k)
   q.compose(cache[k],qubits=[enable]+target+[lv,lw,lp],inplace=True)
   q.ccx(active,s,enable)
 accumulate(x,y,a)
 for xi,yi in zip(x,y):q.cswap(active,xi,yi)
 accumulate(x,y,-inv)
 toggle()
 return q

def check_interval(width):
 from qrr_a65_reversible_basis_exhaustive import evaluate,instruction_stream
 for lo in range(1<<width):
  for hi in range(lo,(1<<width)+1):
   # Check unconditioned and conditioned covers for small widths only.
   q=QuantumCircuit(width+2);work=list(q.qubits[:width])
   interval_xor(q,work,q.qubits[width],lo,hi,condition=q.qubits[width+1])
   stream=instruction_stream(q)
   for x in range(1<<width):
    for condition in (0,1):
     initial=x|(condition<<(width+1))
     got=evaluate(stream,initial)
     expected=initial|((int(condition and lo<=x<hi))<<width)
     if got!=expected:raise AssertionError((width,lo,hi,x,condition,got,expected))
 return True

def run():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--k",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--output",default="results/a96_interval_prefix.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.k)!=1:p.error("odd n>=9, coprime k required")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A96_DYADIC_INTERVAL_PREFIX_WRAP_SYNTHESIS",
   "status":"IN_PROGRESS","n":a.n,"k":a.k,"level":a.level,
   "rows":[],"limitations":["Unrouted standalone multiplier u/cx compilation",
    "Computational-basis exhaustive tests, not coherent phase or noise validation",
    "No performance benefit assumed until measured against A87b at same settings"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  # Exhaustive interval truth-table for small w.
  for w in (2,3):
   check_interval(w)
  print("A96 INTERVAL TRUTH TABLE PASS",flush=True)
  for mod in dict.fromkeys((15,35,a.n)):
   for k in dict.fromkeys((1,mod//2,mod-1,a.k%mod)):
    if k==0:continue
    cases=verify_adder(mod,k,add)
    print("A96 ADDER",mod,k,"PASS",cases,flush=True)
  for label,builder in (("a87b",baseline_build),("a96",build)):
   start=time.perf_counter()
   cases=verify_multiplier(a.n,a.k,builder)
   circuit=builder(a.n,a.k)
   native=transpile(circuit,basis_gates=["u","cx"],
      optimization_level=a.level,seed_transpiler=96)
   row={"architecture":label,"qubits":native.num_qubits,
     "cx":int(native.count_ops().get("cx",0)),
     "depth":int(native.depth()),
     "basis_cases":cases,
     "compile_seconds":round(time.perf_counter()-start,3)}
   d["rows"].append(row);save()
   print("A96 COST",label,row,flush=True)
  old,new=d["rows"]
  d["comparison"]={"delta_cx":new["cx"]-old["cx"],
     "delta_depth":new["depth"]-old["depth"],
     "cx_reduction_pct":round(100*(old["cx"]-new["cx"])/old["cx"],4),
     "depth_reduction_pct":round(100*(old["depth"]-new["depth"])/old["depth"],4)}
  d["status"]="PASS_EXHAUSTIVE_BASIS_AND_NATIVE_COST"
  save();print("A96 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:];save();raise

if __name__=="__main__":run()
