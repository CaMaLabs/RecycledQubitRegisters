#!/usr/bin/env python3
"""A88: matched full dynamic QPE cost comparison for A84 and A87B.

N<=247: compile complete circuits to u/cx. Larger: boxed source only.
Stage basis tests cover all control/input values, including scratch cleanup.
No Aer/QPU shots, device routing or error correction in this experiment.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,transpile
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from qrr_a84_fused_carry_multiplier import build as a84
from qrr_a87b_direct_prefix_multiplier import build as a87b
from qrr_a65_reversible_basis_exhaustive import evaluate,instruction_stream

def qpe(n,base,bits,builder,name):
 w=n.bit_length()
 ph=QuantumRegister(1,"phase");x=QuantumRegister(w,"work")
 anc=QuantumRegister(w+5,"scratch");cl=ClassicalRegister(bits,"readout")
 q=QuantumCircuit(ph,x,anc,cl,name=name);q.x(x[0]);cache={}
 for j in range(bits-1,-1,-1):
  k=pow(base,1<<j,n);q.h(ph[0])
  if k!=1:
   if k not in cache:
    stage=builder(n,k)
    assert stage.num_qubits==q.num_qubits,(name,k,"width")
    cache[k]=stage.to_gate(label=name+"_"+str(k))
   q.append(cache[k],[ph[0],*x,*anc])
  for t in range(bits-1,j,-1):
   with q.if_test((cl[bits-1-t],1)):
    q.p(-2*math.pi/(1<<(t-j+1)),ph[0])
  q.h(ph[0]);q.measure(ph[0],cl[bits-1-j])
  if j:q.reset(ph[0])
 assert int(q.count_ops().get("if_else",0))==bits*(bits-1)//2
 assert int(q.count_ops().get("measure",0))==bits
 assert int(q.count_ops().get("reset",0))==bits-1
 return q,cache

def verify(n,k,builder):
 q=builder(n,k);stream=instruction_stream(q);w=n.bit_length()
 for c in (0,1):
  for x in range(1<<w):
   actual=evaluate(stream,c|(x<<1))
   dest=(k*x%n) if c and x<n else x
   assert actual==c|(dest<<1),(n,k,c,x,actual,dest)
 return 2*(1<<w)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=247)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=16)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--source-only",action="store_true")
 p.add_argument("--skip-stage-check",action="store_true")
 p.add_argument("--output",default="results/a88_n247_qpe.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n >=9 and coprime base required")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits out of range")
 if a.n>247 and not a.source_only:p.error("N>247 requires --source-only (RAM guard)")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A88_A84_A87B_FULL_DYNAMIC_QPE_AB","settings":vars(a),
    "status":"IN_PROGRESS","architectures":{},
    "caveats":["Source basis tests alone do not prove coherent phase equivalence",
      "No Aer sampling, device routing, physical noise, QPU, or fault tolerance",
      "For source-only runs these are not full native QPE costs"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for label,builder in (("a84",a84),("a87b",a87b)):
   start=time.perf_counter();q,cache=qpe(a.n,a.base,a.bits,builder,label)
   row={"qubits":q.num_qubits,"classical_bits":q.num_clbits,
        "top_level_operations":len(q.data),"distinct_powers":len(cache),
        "boxed_definition_operations":sum(len(g.definition.data) for g in cache.values()),
        "build_seconds":round(time.perf_counter()-start,3)}
   d["architectures"][label]=row;save()
   if not a.skip_stage_check:
    start=time.perf_counter()
    row["verified_basis_cases"]=sum(verify(a.n,k,builder) for k in sorted(cache))
    row["stage_check_seconds"]=round(time.perf_counter()-start,3);save()
   if not a.source_only:
    start=time.perf_counter()
    native=transpile(q,basis_gates=["u","cx"],optimization_level=a.level,seed_transpiler=88)
    row["native"]={"cx":int(native.count_ops().get("cx",0)),
      "depth":native.depth(),"qubits":native.num_qubits,
      "compile_seconds":round(time.perf_counter()-start,3)}
    save()
   print("A88",label.upper(),row,flush=True)
  if a.source_only:d["status"]="PASS_BOXED_SOURCE_ONLY_WITH_STAGE_CHECK" if not a.skip_stage_check else "PASS_BOXED_SOURCE_ONLY"
  else:
   left=d["architectures"]["a84"]["native"];right=d["architectures"]["a87b"]["native"]
   d["comparison"]={"delta_cx":right["cx"]-left["cx"],
      "delta_depth":right["depth"]-left["depth"],
      "cx_reduction_pct":round(100*(left["cx"]-right["cx"])/left["cx"],4),
      "depth_reduction_pct":round(100*(left["depth"]-right["depth"])/left["depth"],4)}
   d["status"]="PASS_FULL_DYNAMIC_QPE_COST_AND_STAGE_BASIS" if not a.skip_stage_check else "PASS_FULL_DYNAMIC_QPE_COST_ONLY"
  save();print("A88 STATUS",d["status"],d.get("comparison",{}),flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:];save();raise
if __name__=="__main__":main()
