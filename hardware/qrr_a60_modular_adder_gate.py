#!/usr/bin/env python3
"""A60: real controlled modular-addition gate synthesis and semantic audit.

A reversible building block for a future shift-add modular multiplier.
This first implementation compiles the *addition permutation* with Gray swaps;
it is NOT yet an optimized ripple-carry adder or a full multiplier. Track
honest gate cost and clean ancilla proof by sampled Aer basis execution.
"""
import argparse,json,math,random,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
from qiskit.circuit.library import MCXVChain
from qiskit_aer import AerSimulator
import qrr_a44_generic_modular_multiplier as a44

def addition_mapping(n,k):
 w=n.bit_length();k%=n
 return [(y+k)%n if y<n else y for y in range(1<<w)]

def build(n,k):
 w=n.bit_length()
 if n<9 or n%2==0:raise ValueError("odd n>=9 required")
 values=addition_mapping(n,k)
 qc=QuantumCircuit(1+w+(w-2))
 work=list(range(1,w+1));anc=list(range(w+1,qc.num_qubits))
 frame=0;count=0
 for left,right in a44.exchanges(values):
  path=[left]
  for j in range(w):
   if (left^right)>>j&1:path.append(path[-1]^(1<<j))
  for i in list(range(len(path)-1))+list(range(len(path)-3,-1,-1)):
   u,v=path[i],path[i+1]; bit=(u^v).bit_length()-1
   need=sum(1<<j for j in range(w) if j!=bit and not (u>>j)&1)
   for j in range(w):
    if (frame^need)>>j&1:qc.x(work[j])
   frame=need
   qc.append(MCXVChain(w,dirty_ancillas=False,relative_phase=False,action_only=False),
     [0]+[work[j] for j in range(w) if j!=bit]+[work[bit]]+anc)
   count+=1
 for j in range(w):
  if frame>>j&1:qc.x(work[j])
 return qc,count

def audit(n,k,probes,threads):
 w=n.bit_length();expected=addition_mapping(n,k)
 assert sorted(expected)==list(range(1<<w))
 for y in range(1<<w):
  z=y
  for l,r in a44.exchanges(expected):
   if z==l:z=r
   elif z==r:z=l
  assert z==expected[y],(y,z,expected[y])
 qc,mcx=build(n,k)
 rng=random.Random(60+n+k)
 sample=[0,1,n-1,n,(1<<w)-1]+[rng.randrange(1<<w) for _ in range(probes)]
 sample=list(dict.fromkeys(sample))
 sim=AerSimulator(method="matrix_product_state",max_parallel_threads=threads)
 compiled=transpile(qc,sim,optimization_level=0,seed_transpiler=60)
 observations=[]
 for ctrl in (0,1):
  for y in sample:
   run=QuantumCircuit(qc.num_qubits,qc.num_qubits)
   if ctrl:run.x(0)
   for j in range(w):
    if y>>j&1:run.x(j+1)
   run.compose(compiled,inplace=True)
   run.measure(range(qc.num_qubits),range(qc.num_qubits))
   got=int(next(iter(sim.run(run,shots=1,seed_simulator=60).result().get_counts())),2)
   target=(expected[y] if ctrl else y)
   want=ctrl|(target<<1)
   if got!=want:raise AssertionError(f"gate mismatch ctrl={ctrl} y={y} got={got} expected={want}")
   observations.append({"control":ctrl,"input":y,"output":target,"scratch_zero":True})
 return {"n":n,"constant":k,"permutation_states":1<<w,"gate_cases":len(observations),
   "controlled_gate_verified":True,"clean_ancillas_in_tested_cases":True,
   "logical_qubits":qc.num_qubits,"source_mcx":mcx,"source_depth":qc.depth(),
   "source_counts":dict(qc.count_ops()),"compiled_counts":dict(compiled.count_ops()),
   "compiled_depth":compiled.depth()}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--constants",type=int,nargs="+",default=[8])
 p.add_argument("--probes",type=int,default=3)
 p.add_argument("--threads",type=int,default=2)
 p.add_argument("--no-aer",action="store_true")
 p.add_argument("--output",default="results/a60_modular_adder_gate.json")
 a=p.parse_args()
 if not 0<=a.probes<=20:p.error("probes 0..20")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A60_ACTUAL_CONTROLLED_MODULAR_ADDER","status":"IN_PROGRESS",
 "full_modular_multiplier_synthesized":False,
 "architecture":"Gray-path add-permutation building block, not polynomial-size ripple adder",
 "rows":[]}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 try:
  for k in a.constants:
   t=time.perf_counter()
   if a.no_aer:
    values=addition_mapping(a.n,k)
    assert sorted(values)==list(range(len(values)))
    qc,mcx=build(a.n,k)
    row={"n":a.n,"constant":k,"permutation_states":len(values),
     "source_mcx":mcx,"source_depth":qc.depth(),
     "logical_qubits":qc.num_qubits,
     "source_counts":dict(qc.count_ops()),"actual_gate_semantics_verified":False}
   else:row=audit(a.n,k,a.probes,a.threads)
   row["elapsed_s"]=round(time.perf_counter()-t,3)
   report["rows"].append(row);save()
   print("A60 N",a.n,"k",k,"MCX",row["source_mcx"],
      "depth",row["source_depth"],"gate_verified",not a.no_aer,flush=True)
  report["status"]="PASS_ADDER_GATE_AUDIT" if not a.no_aer else "PASS_SOURCE_ONLY"
  save()
 except Exception:
  report["status"]="FAIL";report["error"]=traceback.format_exc()[-4000:];save();raise
 print("A60 STATUS",report["status"],"SAVED",out,flush=True)

if __name__=="__main__":main()
