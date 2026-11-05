#!/usr/bin/env python3
"""A84: carry-control fusion inside A76 modular arithmetic.

A61 applies each constant's carry cascade with two explicit control flags.
A84 instead computes their AND in A61's existing clean predicate_scratch,
performs the SAME controlled binary addition with one enable, then uncomputes
the AND. This is arithmetic resynthesis, not a register-basis wrapper.

Temporary reuse is legal: predicate_scratch is used by A61's threshold
cleanup only AFTER both additions have finished. All scratch bits must clean.

No prime factors, order, or quantum oracle are supplied. Compare compiled
native CX/depth at identical optimization levels and exhaustive source gates.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a61_binary_modular_adder import ge,add_constant
from qrr_a65_reversible_basis_exhaustive import instruction_stream,evaluate

def fused_add(n,k):
 if n<3 or n%2!=1:raise ValueError("odd modulus >=3 required")
 w=n.bit_length();k%=n
 qc=QuantumCircuit(w+4)
 control=qc.qubits[0];work=list(qc.qubits[1:w+1])
 valid,wrap,pred=qc.qubits[w+1:w+4]
 if k==0:return qc
 qc.x(valid);ge(qc,work,valid,n)
 ge(qc,work,wrap,n-k);ge(qc,work,wrap,n)
 def add_two_controls(value,flag1,flag2):
  # Compute enabled carry once. Do not use pred for other work in this span.
  qc.ccx(flag1,flag2,pred)
  add_constant(qc,work,value,pred)
  qc.ccx(flag1,flag2,pred)
 add_two_controls(k,control,valid)
 add_two_controls(-n,control,wrap)
 def controlled_ge(target,threshold,condition):
  ge(qc,work,pred,threshold)
  qc.ccx(condition,pred,target)
  ge(qc,work,pred,threshold)
 qc.x(control)
 controlled_ge(wrap,n-k,control);controlled_ge(wrap,n,control)
 qc.x(control)
 qc.cx(control,wrap);controlled_ge(wrap,k,control)
 qc.x(valid);ge(qc,work,valid,n)
 return qc

def build(n,a):
 if n<3 or n%2!=1 or math.gcd(n,a)!=1:raise ValueError("odd n, coprime a")
 w=n.bit_length();a%=n;inv=pow(a,-1,n)
 q=QuantumCircuit(2*w+6)
 c=q.qubits[0];x=list(q.qubits[1:1+w]);y=list(q.qubits[1+w:1+2*w])
 active,enable,lv,lw,lp=q.qubits[1+2*w:]
 def active_toggle():
  q.cx(c,active);ge(q,x+[c],active,(1<<w)+n)
 active_toggle()
 cache={}
 def accumulate(source,target,coefficient):
  for j,s in enumerate(source):
   k=coefficient*(1<<j)%n
   if k==0:continue
   q.ccx(active,s,enable)
   if k not in cache:cache[k]=fused_add(n,k)
   q.compose(cache[k],qubits=[enable]+target+[lv,lw,lp],inplace=True)
   q.ccx(active,s,enable)
 accumulate(x,y,a)
 for xi,yi in zip(x,y):q.cswap(active,xi,yi)
 accumulate(x,y,-inv)
 active_toggle()
 return q

def check(qc,n,k):
 w=n.bit_length();stream=instruction_stream(qc)
 for ctrl in (0,1):
  for x in range(1<<w):
   got=evaluate(stream,ctrl|(x<<1))
   expected=ctrl|(((k*x%n) if ctrl and x<n else x)<<1)
   if got!=expected:
    raise AssertionError(f"n={n} k={k} c={ctrl} x={x} got={got} expected={expected}")
 return 2*(1<<w)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=247)
 p.add_argument("--k",type=int,default=8)
 p.add_argument("--optimization-level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--output",default="results/a84_carry_fusion.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.k)!=1:p.error("odd N >=9 and coprime k")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A84_A76_FUSED_CARRY_CONTROLS","status":"IN_PROGRESS",
         "n":a.n,"k":a.k,"optimization_level":a.optimization_level,
         "architecture":"A76 modular multiplier with internally resynthesized A61 adder",
         "rows":[],"hardware_routing_verified":False,"quantum_aer_verified":False}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 try:
  from qrr_a76_reduced_active_flag import build as old_build
  from qrr_a61_binary_modular_adder import build as old_add
  # Exhaustive arithmetic audit for small modulus and the requested modulus.
  # Test the inner addition separately, including all flags cleaned.
  for adder_n in dict.fromkeys([15,a.n]):
   w=adder_n.bit_length()
   for constant in (1,adder_n//2,adder_n-1):
    add=fused_add(adder_n,constant)
    stream=instruction_stream(add)
    for ctrl in (0,1):
     for x in range(1<<w):
      got=evaluate(stream,ctrl|(x<<1))
      expect=ctrl|((((x+constant)%adder_n) if ctrl and x<adder_n else x)<<1)
      if got!=expect:
       raise AssertionError(f"adder n={adder_n} k={constant} ctrl={ctrl} x={x}")
  print("A84 ADDER EXHAUSTIVE PASS",flush=True)
  for name,builder in (("a76",old_build),("a84",build)):
   start=time.perf_counter()
   qc=builder(a.n,a.k)
   cases=check(qc,a.n,a.k)
   print("A84 BASIS",name,"PASS",cases,"qubits",qc.num_qubits,flush=True)
   native=transpile(qc,basis_gates=["u","cx"],
          optimization_level=a.optimization_level,seed_transpiler=84)
   row={"architecture":name,"qubits":native.num_qubits,
        "cx":int(native.count_ops().get("cx",0)),"depth":native.depth(),
        "basis_cases":cases,"seconds":round(time.perf_counter()-start,3)}
   report["rows"].append(row);save()
   print("A84 COST",name,row,flush=True)
  old,new=report["rows"]
  report["comparison"]={"delta_cx":new["cx"]-old["cx"],
      "delta_depth":new["depth"]-old["depth"],
      "cx_reduction_pct":round(100*(old["cx"]-new["cx"])/old["cx"],4),
      "depth_reduction_pct":round(100*(old["depth"]-new["depth"])/old["depth"],4)}
  report["status"]="PASS_EXHAUSTIVE_BASIS_AND_NATIVE_COST";save()
  print("A84 STATUS",report["status"],report["comparison"],flush=True)
 except Exception:
  report["status"]="FAIL";report["error"]=traceback.format_exc()[-5000:];save();raise

if __name__=="__main__":main()
