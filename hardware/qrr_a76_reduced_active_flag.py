#!/usr/bin/env python3
"""A76: remove one redundant A64 validity flag without changing arithmetic.

The active flag is c AND [x<N]. Compute as:
    active ^= c
    active ^= [c*2**w + x >= 2**w + N]
using the EXISTING reversible ge primitive on work+[control].
This replaces A64's separate global_valid flag and ccx.
Gate-basis validation is required before promotion.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a61_binary_modular_adder import build as add_build,ge
from qrr_a65_reversible_basis_exhaustive import instruction_stream,evaluate

def build(n,a):
 if n<3 or n%2!=1 or math.gcd(n,a)!=1:raise ValueError("odd N and coprime a")
 w=n.bit_length();a%=n;inverse=pow(a,-1,n)
 # c, X[w], Y[w], active, bit_enable, local_valid, local_wrap, local_pred
 q=QuantumCircuit(2*w+6)
 c=q.qubits[0];x=list(q.qubits[1:1+w]);y=list(q.qubits[1+w:1+2*w])
 active,bit_enable,lv,lw,lp=q.qubits[1+2*w:]
 def active_toggle():
  q.cx(c,active)
  ge(q,x+[c],active,(1<<w)+n)
 active_toggle()
 def accumulation(source,target,coefficient):
  for j,s in enumerate(source):
   k=coefficient*(1<<j)%n
   if k==0:continue
   q.ccx(active,s,bit_enable)
   adder=add_build(n,k)
   q.compose(adder,qubits=[bit_enable]+target+[lv,lw,lp],inplace=True)
   q.ccx(active,s,bit_enable)
 accumulation(x,y,a)
 for xi,yi in zip(x,y):q.cswap(active,xi,yi)
 accumulation(x,y,-inverse)
 active_toggle()
 return q

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--native-cost",action="store_true")
 p.add_argument("--output",default="results/a76_reduced_scratch.json")
 a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A76_ONE_LESS_ANCILLA_EXHAUSTIVE_BASIS","n":a.n,
    "a":a.a,"status":"IN_PROGRESS","quantum_aer_verified":False}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  t=time.perf_counter();qc=build(a.n,a.a)
  stream=instruction_stream(qc);w=a.n.bit_length()
  d["source"]={"qubits":qc.num_qubits,"ops":len(stream),"depth":qc.depth()}
  save()
  total=0
  for ctrl in (0,1):
   for x in range(1<<w):
    got=evaluate(stream,ctrl|(x<<1))
    z=(a.a*x)%a.n if ctrl and x<a.n else x
    want=ctrl|(z<<1)
    if got!=want:
     raise AssertionError(f"N={a.n} a={a.a} ctrl={ctrl} x={x} got={got} want={want}")
    total+=1
  d["source_basis_cases_verified"]=total
  d["all_scratch_clean_for_tested_inputs"]=True
  d["status"]="PASS_EXHAUSTIVE_SOURCE_BASIS"
  save()
  print("A76 BASIS PASS",a.n,a.a,"cases",total,"qubits",qc.num_qubits,"seconds",round(time.perf_counter()-t,3),flush=True)
  if a.native_cost:
   from qrr_a64_binary_modular_multiplier import build as old_build
   for name,builder in (("A64",old_build),("A76",build)):
    started=time.perf_counter();native=transpile(builder(a.n,a.a),basis_gates=["u","cx"],
     optimization_level=1,seed_transpiler=76)
    d[name+"_native"]={"cx":native.count_ops().get("cx",0),
     "depth":native.depth(),"qubits":native.num_qubits,
     "compile_seconds":round(time.perf_counter()-started,3)}
    save()
    print("A76 COST",name,d[name+"_native"],flush=True)
  print("A76 STATUS",d["status"],"SAVED",out,flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-4000:];save();raise

if __name__=="__main__":main()
