#!/usr/bin/env python3
"""A64 experimental compute-swap-uncompute modular multiplier from A61.
Input |c,x,0,0...> -> |c,a*x mod N,0,0...> for x<N; x>=N fixed.
Proof MUST be established by execution; no multiplier advantage asserted.
"""
import argparse,json,math,random,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a61_binary_modular_adder import build as add_build,ge

def build(n,a):
 if n<3 or not n%2 or math.gcd(n,a)!=1:raise ValueError("odd N and gcd(a,N)=1 required")
 w=n.bit_length();a%=n;inverse=pow(a,-1,n)
 # c, X[w], Y[w], global_valid, active, bit_enable, local_valid, local_wrap, local_pred
 q=QuantumCircuit(2*w+7)
 c=q.qubits[0];x=list(q.qubits[1:1+w]);y=list(q.qubits[1+w:1+2*w])
 global_valid,active,bit_enable,lv,lw,lp=q.qubits[1+2*w:]
 q.x(global_valid);ge(q,x,global_valid,n)
 q.ccx(c,global_valid,active)
 def accumulation(source,target,coefficient):
  for j,s in enumerate(source):
   k=coefficient*(1<<j)%n
   if k==0:continue
   q.ccx(active,s,bit_enable)
   adder=add_build(n,k)
   q.compose(adder,qubits=[bit_enable]+target+[lv,lw,lp],inplace=True)
   q.ccx(active,s,bit_enable)
 accumulation(x,y,a)
 # Controlled register swap; active stays invariant through the swap.
 for xi,yi in zip(x,y):q.cswap(active,xi,yi)
 # x now holds a*x, y holds original x; subtract (a^-1)*x from y.
 accumulation(x,y,-inverse)
 q.ccx(c,global_valid,active)
 q.x(global_valid);ge(q,x,global_valid,n)
 return q

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15);p.add_argument("--a",type=int,default=2)
 p.add_argument("--probes",type=int,default=8)
 p.add_argument("--exhaustive",action="store_true")
 p.add_argument("--no-aer",action="store_true")
 p.add_argument("--native-cost",action="store_true")
 p.add_argument("--output",default="results/a64_multiplier.json")
 args=p.parse_args();out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A64_A61_COMPUTE_SWAP_UNCOMPUTE_MULTIPLIER","status":"IN_PROGRESS",
    "n":args.n,"a":args.a,"rows":[],"quantum_speedup_claimed":False}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  start=time.perf_counter();qc=build(args.n,args.a);w=args.n.bit_length()
  d["source"]={"qubits":qc.num_qubits,"counts":dict(qc.count_ops()),"depth":qc.depth()}
  if args.native_cost:
   native=transpile(qc,basis_gates=["u","cx"],optimization_level=0,seed_transpiler=64)
   d["native"]={"cx":native.count_ops().get("cx",0),"depth":native.depth(),"counts":dict(native.count_ops())}
  save()
  if not args.no_aer:
   ys=list(range(1<<w)) if args.exhaustive else list(dict.fromkeys([0,1,args.n-1,args.n,(1<<w)-1]+random.Random(64).sample(range(1<<w),min(args.probes,1<<w))))
   for c in (0,1):
    for x in ys:
     test=QuantumCircuit(qc.num_qubits,qc.num_qubits)
     if c:test.x(0)
     for j in range(w):
      if x>>j&1:test.x(j+1)
     test.compose(qc,inplace=True)
     test.measure(range(test.num_qubits),range(test.num_qubits))
     prepared=transpile(test,basis_gates=["u","cx","measure"],optimization_level=0,seed_transpiler=64)
     sim=AerSimulator(method="statevector",max_parallel_threads=1)
     result=sim.run(prepared,shots=1,seed_simulator=64).result()
     if not result.success:raise RuntimeError(result.status)
     got=int(next(iter(result.get_counts())),2)
     z=(args.a*x)%args.n if c and x<args.n else x
     expected=c|(z<<1)
     if got!=expected:raise AssertionError(f"ctrl={c} x={x} got={got} expected={expected}")
     d["rows"].append({"control":c,"x":x,"verified":True})
     if len(d["rows"])%8==0:save()
  d["elapsed_seconds"]=round(time.perf_counter()-start,3)
  d["status"]="PASS_GATE_AUDIT" if not args.no_aer else "SOURCE_ONLY_NOT_VALIDATED";save()
  print("A64",d["status"],"N",args.n,"a",args.a,"qubits",qc.num_qubits,"cases",len(d["rows"]),"source_depth",qc.depth(),"native",d.get("native"),flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
