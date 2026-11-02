#!/usr/bin/env python3
"""A59: N2491 gate-cost baseline and reversible-arithmetic design screen.

Actual Qiskit gate construction/cost for the existing A44 Gray-path stage.
Separately tests polynomial-size shift-add modular multiplication *as a
classical reversible-register specification*, NOT as a quantum gate circuit.
Cost bounds for the proposed architecture are analytical and explicitly
labeled uncompiled. No claim of proven gate savings.
"""
import argparse,json,math,time,sys
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a44_generic_modular_multiplier as a44

def shift_add(a,x,n):
 out=0;v=a%n
 for j in range(n.bit_length()):
  if x>>j&1:out=(out+v)%n
  v=(v*2)%n
 return out

def validate(n,a):
 width=n.bit_length();mask=(1<<width)-1
 assert math.gcd(a,n)==1
 # Classical reversible embedding (x,0)->(x,f(x)), with explicit
 # inverse multiplication for subsequent input uncompute.
 inv=pow(a,-1,n)
 seen=set()
 for x in range(1<<width):
  y=shift_add(a,x,n) if x<n else x
  assert y == (a*x%n if x<n else x)
  assert (inv*y%n if y<n else y)==x
  assert y not in seen
  seen.add(y)
 return {"checked_basis_inputs":1<<width,"inverse_checked":True,
          "out_of_range_fixed":True,"functional_embedding_only":True}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--max-stages",type=int,default=2)
 p.add_argument("--output",default="results/a59_n2491_arithmetic_screen.json")
 a=p.parse_args()
 if a.n%2==0 or math.gcd(a.n,a.base)!=1:p.error("odd modulus and coprime base needed")
 if not 1<=a.max_stages<=a.bits:p.error("invalid stage count")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A59_N2491_POLYNOMIAL_ARITHMETIC_SCREEN",
 "status":"IN_PROGRESS","n":a.n,"base":a.base,"bits":a.bits,
 "stage_results":[],"candidate_is_compiled_quantum_circuit":False,
 "caveat":"Shift-add is a reversible-function specification, NOT a reversible quantum circuit or proven gate-cost improvement."}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 powers=list(dict.fromkeys(pow(a.base,1<<j,a.n) for j in range(a.bits) if pow(a.base,1<<j,a.n)!=1))
 for power in powers[:a.max_stages]:
  t=time.perf_counter()
  proof=validate(a.n,power)
  qc,mcx=a44.build(a.n,power)
  row={"power":power,"functional_candidate":proof,"a44_actual_source_mcx":mcx,
       "a44_actual_source_gates":dict(qc.count_ops()),
       "a44_actual_source_depth":qc.depth(),
       "a44_actual_qubits":qc.num_qubits,
       "construction_seconds":round(time.perf_counter()-t,3),
       "candidate_nominal_shift_add_steps":a.n.bit_length(),
       "candidate_implementation_status":"NOT_SYNTHESIZED_NO_GATE_COMPARISON_YET"}
  report["stage_results"].append(row);save()
  print("A59 stage",power,"A44 MCX",mcx,"depth",qc.depth(),
        "candidate functional cases",proof["checked_basis_inputs"],flush=True)
 report["distinct_nontrivial_powers"]=len(powers)
 report["candidate_architecture"]={
  "proposed":"controlled reversible modular shift/add with conditional reduction, Bennett uncompute, input permutation cleanup",
  "required_next_proof":"Synthesize Qiskit gates; test control=0/1, all inputs, ancilla return; report transpiled cx/ccx/depth",
  "resource_comparison":"NOT_YET_AVAILABLE"}
 report["status"]="PASS_BASELINE_AND_FUNCTIONAL_SPEC_ONLY"
 save();print("A59 STATUS",report["status"],"stages",len(report["stage_results"]),"SAVED",out,flush=True)
if __name__=="__main__":main()
