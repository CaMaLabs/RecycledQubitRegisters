#!/usr/bin/env python3
"""A72 complete N221 hybrid stage sweep at transpiler optimization level 1.

Full 2^3 assignments, including a separate minimum-qubit pure A44 baseline.
Reports compilation resources only, no Aer execution or factoring.
"""
import argparse,itertools,json,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a69_hybrid_recycled_qpe import build as hybrid_build
from qrr_a67_recycled_qpe_ab import build as pure_build

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=221)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=16)
 p.add_argument("--screen",default="results/a68_n221_stage_costs.json")
 p.add_argument("--optimization-level",type=int,choices=[0,1,2],default=1)
 p.add_argument("--output",default="results/a72_n221_full_level1.json")
 a=p.parse_args()
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A72_EXHAUSTIVE_HYBRID_COMPILATION_OPT_SWEEP","status":"IN_PROGRESS",
    "n":a.n,"base":a.base,"bits":a.bits,"optimization_level":a.optimization_level,
    "quantum_simulated":False,"rows":[]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  s=json.loads(Path(a.screen).read_text())
  assert (s.get("n"),s.get("base"),s.get("bits"),s.get("status")) == (
   a.n,a.base,a.bits,"PASS_PER_STAGE_NATIVE_COSTS_NOT_FULL_HYBRID_COMPILED")
  powers=sorted({pow(a.base,1<<j,a.n) for j in range(a.bits)}-{1})
  if len(powers)>6:raise ValueError("Cannot sweep >6 distinct powers")
  sim=AerSimulator(method="matrix_product_state")
  for choices in itertools.product(("a44","a64"),repeat=len(powers)):
   winners=dict(zip(powers,choices))
   label="/".join(choices);start=time.perf_counter()
   if all(x=="a44" for x in choices):
    qc,_=pure_build(a.n,a.base,a.bits,"a44")
   elif all(x=="a64" for x in choices):
    qc,_=pure_build(a.n,a.base,a.bits,"a64")
   else:qc,_=hybrid_build(a.n,a.base,a.bits,winners)
   compiled=transpile(qc,sim,optimization_level=a.optimization_level,seed_transpiler=71)
   row={"assignment":{str(k):v for k,v in winners.items()},
        "label":label,"qubits":compiled.num_qubits,
        "cx":compiled.count_ops().get("cx",0),"depth":compiled.depth(),
        "seconds":round(time.perf_counter()-start,3)}
   d["rows"].append(row);save()
   print("A72",label,"CX",row["cx"],"depth",row["depth"],"qubits",row["qubits"],flush=True)
  d["best_cx"]=min(d["rows"],key=lambda r:(r["cx"],r["depth"],r["qubits"]))
  d["best_depth"]=min(d["rows"],key=lambda r:(r["depth"],r["cx"],r["qubits"]))
  d["status"]="PASS_FULL_COMPILED_ASSIGNMENT_SWEEP"
  save()
  print("A72 BEST_CX",d["best_cx"]["label"],d["best_cx"]["cx"],"BEST_DEPTH",
        d["best_depth"]["label"],d["best_depth"]["depth"],flush=True)
 except Exception:
  d["status"]="ERROR";d["error"]=traceback.format_exc()[-4000:];save();raise

if __name__=="__main__":main()
