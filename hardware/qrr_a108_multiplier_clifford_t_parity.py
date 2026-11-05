#!/usr/bin/env python3
"""A108: fair complete-multiplier feasibility and Clifford+T benchmark.

Compare fully clean A97 and experimental A106 on identical N,A,
source-basis gate semantics and local compilation settings. Resource-plan
A106 at N2491 WITHOUT constructing the huge complete multiplier.
The optional Clifford+T decomposition gives T-count/T-depth after
Qiskit synthesis, not logical fault-tolerant space-time volume.

This does NOT implement Gossett, Wang et al., or Barrett paper circuits:
published results are incomparable until independently reconstructed.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a106_csa_controlled_multiplier import build as csa,tree_structure
from qrr_a97_adaptive_modadd_multiplier import build as adaptive
from qrr_a87b_direct_prefix_multiplier import verify_multiplier
from qrr_a102_clean_modular_csa_three_sum import build as kernel

def preflight(n):
 w=n.bit_length()
 nodes,_=tree_structure(w)
 _,meta=kernel(n,"carry_save")
 W=meta["sum_guard_bits"]
 count=2*w+2+w*len(nodes)+meta["logical_qubits"]
 return {"w":w,"ternary_tree_nodes":len(nodes),
  "kernel_guard_width":W,"shared_kernel_qubits":meta["logical_qubits"],
  "tree_register_qubits":w*len(nodes),"predicted_csa_multiplier_qubits":count,
  "ibm_fez_156_qubit_fit":count<=156}

def native_metrics(qc,basis,level,seed):
 compiled=transpile(qc,basis_gates=basis,optimization_level=level,seed_transpiler=seed)
 ops=compiled.count_ops()
 return {"basis":basis,"cx":int(ops.get("cx",0)),
   "depth":int(compiled.depth()),
   "t_count":int(ops.get("t",0)+ops.get("tdg",0)) if "t" in basis else None,
   "t_depth":int(compiled.depth(lambda inst:inst.operation.name in ("t","tdg")))
     if "t" in basis else None,
   "qubits":compiled.num_qubits}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--n",type=int,default=15)
 ap.add_argument("--a",type=int,default=2)
 ap.add_argument("--max-qubits",type=int,default=156)
 ap.add_argument("--level",type=int,choices=(0,1,2),default=1)
 ap.add_argument("--seed",type=int,default=10801)
 ap.add_argument("--clifford-t",action="store_true")
 ap.add_argument("--preflight-only",action="store_true")
 ap.add_argument("--output",default="results/a108_multiplier_parity.json")
 a=ap.parse_args()
 if a.n<3 or a.n%2!=1 or math.gcd(a.n,a.a)!=1:ap.error("odd N>=3, coprime multiplier required")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A108_FULL_MULTIPLIER_COST_AND_EXTERNAL_COMPARABILITY_GATE",
  "settings":vars(a),"status":"IN_PROGRESS","preflight":preflight(a.n),
  "architectures":{},"qpu_jobs":0,
  "limitations":["Source basis validation proves permutation on specified clean subspace, not physical noise resilience",
    "Clifford+T is post-transpilation accounting, not a logical error-corrected cost model",
    "No independent published Gossett/compressor/Barrett circuit is implemented in this comparison",
    "A106's large workspace may be unsuitable for Fez even if its gate count improves"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  print("A108 PREFLIGHT",d["preflight"],flush=True)
  if a.preflight_only:
   d["status"]="PASS_WIDTH_PREFLIGHT_ONLY";save()
   print("A108 STATUS",d["status"],flush=True);return
  if d["preflight"]["predicted_csa_multiplier_qubits"]>a.max_qubits:
   d["status"]="NOT_COMPARABLE_WIDTH_EXCEEDS_LIMIT";save()
   print("A108 STATUS",d["status"],flush=True);return
  for name in ("a97","a106"):
   tick=time.perf_counter()
   qc=(adaptive(a.n,a.a,level=a.level,seed=a.seed)[0]
       if name=="a97" else csa(a.n,a.a,"carry_save",max_qubits=a.max_qubits)[0])
   cases=verify_multiplier(a.n,a.a,lambda n,k,q=qc:q)
   row={"source_basis_cases":cases,"logical_qubits":qc.num_qubits,
     "source_ops":len(qc.data),
     "u_cx":native_metrics(qc,["u","cx"],a.level,a.seed)}
   if a.clifford_t:
    row["clifford_t"]=native_metrics(qc,
      ["h","s","sdg","t","tdg","cx","x"],a.level,a.seed)
   row["elapsed_seconds"]=round(time.perf_counter()-tick,3)
   d["architectures"][name]=row;save()
   print("A108",name,"basis",cases,"qubits",row["logical_qubits"],
     "cx",row["u_cx"]["cx"],"depth",row["u_cx"]["depth"],
     "T",row.get("clifford_t",{}).get("t_count"),flush=True)
  x=d["architectures"]["a97"]["u_cx"];y=d["architectures"]["a106"]["u_cx"]
  d["comparison"]={"delta_cx":y["cx"]-x["cx"],
   "cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
   "delta_depth":y["depth"]-x["depth"],
   "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4),
   "delta_qubits":y["qubits"]-x["qubits"]}
  if a.clifford_t:
   p=d["architectures"]["a97"]["clifford_t"];q=d["architectures"]["a106"]["clifford_t"]
   d["comparison"]["delta_t_count"]=q["t_count"]-p["t_count"]
   d["comparison"]["delta_t_depth"]=q["t_depth"]-p["t_depth"]
  d["status"]="PASS_FULL_MULTIPLIER_SOURCE_AND_COST_AB"
  save();print("A108 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":main()
