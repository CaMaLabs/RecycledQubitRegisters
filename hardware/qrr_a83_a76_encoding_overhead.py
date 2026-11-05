#!/usr/bin/env python3
"""A83: A76 architecture-transfer encoding audit (honest negative control).

A82 demonstrated a *resynthesized* binary-linear permutation advantage for
A44. A83 tests whether placing reversible GF(2) register-basis transforms
around the existing A76 arithmetic kernel yields any native-gate benefit.

This is a conjugation / conversion-overhead screen, NOT a new A76
encoded-arithmetic synthesis. A wrapper around an unchanged arithmetic
algorithm is not expected to reproduce A82's saving.

Every candidate's gate-level semantics is checked exhaustively on small
moduli by interpreting its real reversible source gates (A65). Native CX
and depth are measured using the same transpilation settings. No factors,
secret orders, or oracle stages are used.
"""
import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path
from qiskit import QuantumCircuit, transpile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a76_reduced_active_flag import build as a76_build
from qrr_a65_reversible_basis_exhaustive import instruction_stream,evaluate

def transform_edges(w,variant):
 if variant=="identity":return []
 if variant=="chain":return [(j,j+1) for j in range(w-1)]
 if variant=="reverse_chain":return [(j,j-1) for j in range(w-1,0,-1)]
 if variant=="star_low":return [(0,j) for j in range(1,w)]
 if variant=="star_high":return [(w-1,j) for j in range(w-1)]
 if variant=="pair":return [(j,j+1) for j in range(0,w-1,2)]
 if variant.startswith("shift"):
  shift=int(variant[5:])
  if not (1<=shift<w):raise ValueError(variant)
  return [(j,j+shift) for j in range(w-shift)]
 raise ValueError(variant)

def build(n,k,variant):
 base=a76_build(n,k);w=n.bit_length()
 if variant=="identity":return base
 edges=transform_edges(w,variant)
 out=QuantumCircuit(base.num_qubits)
 # Outward register semantics must be IDENTICAL to baseline.
 # E^-1 before A76, E after A76. Since A76 is not resynthesized in E,
 # this is an overhead audit rather than a proof of encoding gain.
 for src,dst in reversed(edges):out.cx(1+src,1+dst)
 out.compose(base,inplace=True)
 for src,dst in edges:out.cx(1+src,1+dst)
 return out

def check_transformed_basis(qc,n,k):
 w=n.bit_length();stream=instruction_stream(qc)
 failures=[]
 for ctrl in (0,1):
  for x in range(1<<w):
   got=evaluate(stream,ctrl|(x<<1))
   expected=ctrl|((((k*x)%n if ctrl and x<n else x))<<1)
   if got!=expected:
    failures.append({"c":ctrl,"x":x,"got":got,"expected":expected})
    return False,failures
 return True,failures

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--k",type=int,default=8)
 p.add_argument("--optimization-level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--variants",nargs="+",default=["identity","chain","reverse_chain","star_low","star_high","pair","shift2"])
 p.add_argument("--check-basis",action="store_true")
 p.add_argument("--output",default="results/a83_a76_encoding_overhead.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.k)!=1:p.error("N odd >=9, k coprime")
 if a.n.bit_length()<4:p.error("N requires at least 4-bit register")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A83_A76_GF2_ENCODING_CONVERSION_OVERHEAD",
    "status":"IN_PROGRESS","n":a.n,"k":a.k,"level":a.optimization_level,
    "variants":[],"note":"Transforms use unchanged A76 arithmetic kernel; wrapper is NOT a resynthesized encoded multiplier. No benefit should be assumed.",
    "quantum_phase_validation":"NOT_RUN",
    "full_qpe_validation":"NOT_RUN"}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for name in a.variants:
   t=time.perf_counter();qc=build(a.n,a.k,name)
   row={"variant":name,"qubits":qc.num_qubits,
        "encoding_cx_overhead":2*len(transform_edges(a.n.bit_length(),name))}
   if a.check_basis:
    valid,failures=check_transformed_basis(qc,a.n,a.k)
    row["source_basis_check"]="PASS" if valid else "FAIL"
    row["failures"]=failures
    if not valid:
     d["variants"].append(row);d["status"]="FAIL_BASIS";save()
     raise AssertionError(f"{name} changes arithmetic semantics, not a harmless wrapper")
   native=transpile(qc,basis_gates=["u","cx"],
                    optimization_level=a.optimization_level,seed_transpiler=83)
   row["cx"]=int(native.count_ops().get("cx",0))
   row["depth"]=native.depth()
   row["compile_seconds"]=round(time.perf_counter()-t,3)
   d["variants"].append(row);save()
   print("A83",name,"qubits",row["qubits"],"CX",row["cx"],
         "depth",row["depth"],"basis",row.get("source_basis_check","NOT_TESTED"),flush=True)
  baseline=next(x for x in d["variants"] if x["variant"]=="identity")
  for row in d["variants"]:
   row["delta_cx"]=row["cx"]-baseline["cx"]
   row["delta_depth"]=row["depth"]-baseline["depth"]
  d["status"]="PASS_COMPILED_OVERHEAD_SCREEN" if not a.check_basis else "PASS_EXHAUSTIVE_BASIS_AND_COMPILED"
  save()
  print("A83 STATUS",d["status"],"baseline_CX",baseline["cx"],
        "best_CX",min(r["cx"] for r in d["variants"]),"SAVED",out,flush=True)
 except Exception:
  if d["status"]=="IN_PROGRESS":d["status"]="ERROR"
  d["error"]=traceback.format_exc()[-5000:];save();raise
if __name__=="__main__":main()
