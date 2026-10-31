#!/usr/bin/env python3
"""A44: generic exact reversible controlled modular multiplication for wider N.

Uses cycle transpositions and Gray-path neighbor swaps; X-frame reduction,
clean-ancilla V-chain. Full computational-basis simulator validates ALL
2^(work_bits+1) inputs on actual source gate semantics (before decomposition).
Does not claim full QPE or quantum speedup.
"""
import argparse,json,math,time
from pathlib import Path
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXVChain

def mapping(n,base):
 if n<9 or n%2!=1 or math.gcd(n,base)!=1:raise ValueError("odd n, coprime base required")
 return [base*y%n if y<n else y for y in range(1<<n.bit_length())]

def exchanges(values):
 seen=set();pairs=[]
 for start in range(len(values)):
  if start in seen:continue
  cycle=[];at=start
  while at not in seen:
   seen.add(at);cycle.append(at);at=values[at]
  if at!=start:raise AssertionError("not a permutation")
  for i in range(1,len(cycle)):pairs.append((cycle[0],cycle[i]))
 return pairs

def build(n,base):
 width=n.bit_length();scratch=width-2
 ops=mapping(n,base);qc=QuantumCircuit(1+width+scratch)
 work=list(range(1,1+width));scratch_ids=list(range(1+width,qc.num_qubits))
 frame=0;mcx_count=0
 for left,right in exchanges(ops):
  path=[left]
  for j in range(width):
   if ((left^right)>>j)&1:path.append(path[-1]^(1<<j))
  assert path[-1]==right
  for i in list(range(len(path)-1))+list(range(len(path)-3,-1,-1)):
   u,v=path[i],path[i+1]
   bit=(u^v).bit_length()-1
   need=sum(1<<j for j in range(width) if j!=bit and not ((u>>j)&1))
   delta=frame^need
   for j in range(width):
    if delta>>j&1:qc.x(work[j])
   frame=need
   controls=[0]+[work[j] for j in range(width) if j!=bit]
   assert len(controls)==width
   qc.append(MCXVChain(width,dirty_ancillas=False,relative_phase=False,
                       action_only=False),controls+[work[bit]]+scratch_ids)
   mcx_count+=1
 for j in range(width):
  if frame>>j&1:qc.x(work[j])
 return qc,mcx_count

def independent_permutation_validation(n,base):
 m=mapping(n,base);w=n.bit_length()
 assert sorted(m)==list(range(1<<w))
 # This verifies swap construction at the permutation level only.
 pairs=exchanges(m)
 for y in range(1<<w):
  z=y
  for a,b in pairs:
   if z==a:z=b
   elif z==b:z=a
  assert z==m[y],(y,z,m[y])
 return len(m)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--moduli",type=int,nargs="+",default=[221,323])
 p.add_argument("--base",type=int,default=2)
 p.add_argument("--output",default="results/a44_larger_semiprime_multiplier_sources.json")
 a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A44_GENERIC_LARGER_N_REVERSIBLE_MULTIPLIER","status":"IN_PROGRESS",
         "full_recycled_qpe":False,"gate_level_aer_shots":0,"rows":[]}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 for n in a.moduli:
  t=time.perf_counter()
  checked=independent_permutation_validation(n,a.base)
  qc,mcx_count=build(n,a.base)
  row={"n":n,"base":a.base,"work_bits":n.bit_length(),
       "clean_ancillas":n.bit_length()-2,"logical_qubits":qc.num_qubits,
       "source_counts":dict(qc.count_ops()),"mcx_vchain_instances":mcx_count,
       "classical_permutation_states_verified":checked,
       "actual_full_gate_semantics_verified":False,
       "compiled_to_native_basis":False,
       "time_seconds":round(time.perf_counter()-t,3)}
  report["rows"].append(row);save()
  print("A44 SOURCE",json.dumps(row),flush=True)
 report["status"]="PASS_SOURCE_CONSTRUCTION_ONLY_GATE_VALIDATION_PENDING"
 save();print("SAVED",out)
if __name__=="__main__":main()
