#!/usr/bin/env python3
"""A90: resumable N247 A84/A87b matched ideal Aer factoring holdout.

Runs ONLY the next missing architecture per invocation; after both complete,
compares measured phase histograms and factor recovery to exact uniform null.
No known-order oracle enters quantum circuits, but offline order is used for
the post-hoc lattice metric. Native basis u/cx cost is unrouted.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a88_integrated_qpe_ab import qpe
from qrr_a84_fused_carry_multiplier import build as a84
from qrr_a87b_direct_prefix_multiplier import build as a87b
from qrr_a89_aer_phase_holdout import order,recover,lattice_hit,summarize

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=247)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=16)
 p.add_argument("--shots",type=int,default=16)
 p.add_argument("--seed",type=int,default=9001)
 p.add_argument("--level",type=int,choices=(0,1),default=1)
 p.add_argument("--max-memory-mb",type=int,default=8000)
 p.add_argument("--threads",type=int,default=2)
 p.add_argument("--output",default="results/a90_n247_aer_ab.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd coprime n>=9")
 if a.n>247:p.error("n<=247 simulation safety guard")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits 2..2w")
 if not 1<=a.shots<=64:p.error("shots 1..64")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 settings={"n":a.n,"base":a.base,"bits":a.bits,"shots":a.shots,
   "seed":a.seed,"level":a.level}
 if path.exists():
  d=json.loads(path.read_text())
  if d.get("settings")!=settings:raise ValueError("Checkpoint settings differ; use a new --output")
 else:
  d={"experiment":"A90_RESUMABLE_FULL_GATE_AER_QPE_HOLDOUT",
     "settings":settings,"status":"IN_PROGRESS","architectures":{},
     "known_order_source":"OFFLINE_ANALYSIS_ONLY",
     "limitations":["Ideal Aer MPS simulated data; no calibrated physical noise or QPU",
       "Equal seed samples may agree by deterministic coupling; this does not establish exact phase distribution equality",
       "Uniform-frequency null is classical and not physical-noise matched",
       "One invocation evaluates one architecture to avoid expensive duplicated runs"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 r=order(a.base,a.n);total=1<<a.bits
 d["uniform_null"]={"total_frequencies":total,
  "factor_successes":sum(recover(a.n,a.base,a.bits,y,4) is not None for y in range(total)),
  "lattice_hits":sum(lattice_hit(y,a.bits,r) for y in range(total))}
 save()
 try:
  for name,builder in (("a84",a84),("a87b",a87b)):
   if name in d["architectures"] and d["architectures"][name].get("complete"):continue
   t=time.perf_counter()
   circuit,_=qpe(a.n,a.base,a.bits,builder,name)
   native=transpile(circuit,basis_gates=["u","cx"],
          optimization_level=a.level,seed_transpiler=90)
   row={"qubits":native.num_qubits,"cx":int(native.count_ops().get("cx",0)),
       "depth":native.depth(),"compile_seconds":round(time.perf_counter()-t,3),
       "complete":False}
   d["architectures"][name]=row;save()
   print("A90 COMPILED",name,"CX",row["cx"],"depth",row["depth"],flush=True)
   t=time.perf_counter()
   sim=AerSimulator(method="matrix_product_state",
     max_parallel_threads=a.threads,max_memory_mb=a.max_memory_mb)
   result=sim.run(native,shots=a.shots,seed_simulator=a.seed).result()
   if not result.success:raise RuntimeError(str(result.status))
   hist=collections.Counter({int(k.replace(" ",""),2):v for k,v in result.get_counts().items()})
   row["aggregate"]=summarize(hist,a.n,a.base,a.bits,r,4)
   row["aer_seconds"]=round(time.perf_counter()-t,3)
   row["complete"]=True;save()
   print("A90 MEASURED",name,"factors",row["aggregate"]["verified_factor_count"],
     "/",a.shots,"lattice",row["aggregate"]["phase_lattice_hits"],
     "/",a.shots,"seconds",row["aer_seconds"],flush=True)
   break
  if all(d["architectures"].get(x,{}).get("complete") for x in ("a84","a87b")):
   x=d["architectures"]["a84"];y=d["architectures"]["a87b"]
   h1={int(k):v/a.shots for k,v in x["aggregate"]["histogram"].items()}
   h2={int(k):v/a.shots for k,v in y["aggregate"]["histogram"].items()}
   d["comparison"]={"cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
     "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4),
     "empirical_total_variation_distance":round(.5*sum(abs(h1.get(k,0)-h2.get(k,0)) for k in set(h1)|set(h2)),6)}
   d["status"]="PASS_AER_COMPARATIVE_HOLDOUT_WITH_UNIFORM_NULL"
  else:d["status"]="PARTIAL_CHECKPOINT"
  save();print("A90 STATUS",d["status"],d.get("comparison",{}),flush=True)
 except Exception:
  d["status"]="INTERRUPTED_OR_FAIL";d["error"]=traceback.format_exc()[-4000:];save();raise

if __name__=="__main__":main()
