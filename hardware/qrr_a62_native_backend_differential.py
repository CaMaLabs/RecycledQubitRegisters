#!/usr/bin/env python3
"""A62: identical native-basis stream differential Aer statevector vs MPS."""
import argparse,json,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a61_binary_modular_adder import build
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35);p.add_argument("--k",type=int,default=1)
 p.add_argument("--output",default="results/a62_native_backend_differential.json")
 a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A62_IDENTICAL_NATIVE_CIRCUIT_BACKEND_DIFFERENTIAL","status":"IN_PROGRESS","cases":[]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  source=build(a.n,a.k);w=a.n.bit_length()
  # Basis list shared by BOTH engines. No backend-specific transpilation.
  for control in (0,1):
   for y in range(1<<w):
    qc=QuantumCircuit(source.num_qubits,source.num_qubits)
    if control:qc.x(0)
    for i in range(w):
     if (y>>i)&1:qc.x(i+1)
    qc.compose(source,inplace=True)
    qc.measure(range(qc.num_qubits),range(qc.num_qubits))
    native=transpile(qc,basis_gates=["u","cx","measure"],optimization_level=0,seed_transpiler=62)
    if control==0 and y==0:d["common_native_counts"]=dict(native.count_ops());save()
    results={}
    for method in ("statevector","matrix_product_state"):
     sim=AerSimulator(method=method,max_parallel_threads=1)
     res=sim.run(native,shots=1,seed_simulator=62).result()
     if not res.success:raise RuntimeError(f"{method}: {res.status}")
     counts=res.get_counts()
     if len(counts)!=1:raise RuntimeError(f"{method} non-deterministic output")
     results[method]=int(next(iter(counts)),2)
    expected_y=(y+a.k)%a.n if control and y<a.n else y
    expected=control|(expected_y<<1)
    if any(x!=expected for x in results.values()):
     row={"control":control,"y":y,"expected":expected,"results":results}
     d["cases"].append(row);d["status"]="FAIL_BACKEND_DISCREPANCY" if len(set(results.values()))>1 else "FAIL_BOTH_BACKENDS"
     save();print("A62 FIRST FAILURE",json.dumps(row),flush=True);return
  d["status"]="PASS_IDENTICAL_NATIVE_BASIS_ALL_INPUTS";save()
  print("A62 STATUS",d["status"],"CASES",2*(1<<w),flush=True)
 except Exception:
  d["status"]="ERROR";d["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
