#!/usr/bin/env python3
"""A74: N437 optimized full-QPE A44/A64/per-power hybrid benchmark.

Compiles each distinct modular power once to identify per-stage winners, then
compiles the actual semiclassical recycled-QPE circuits at the same optimization
level/seed/backend. This is resource measurement ONLY: no quantum shots,
phase verification, factorization, or hardware execution.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a67_recycled_qpe_ab import build as pure_build
from qrr_a69_hybrid_recycled_qpe import build as hybrid_build
import qrr_a44_generic_modular_multiplier as a44
import qrr_a64_binary_modular_multiplier as a64

def metrics(qc,sim,level,seed):
 start=time.perf_counter()
 compiled=transpile(qc,sim,optimization_level=level,seed_transpiler=seed)
 ops=dict(compiled.count_ops())
 return {"qubits":compiled.num_qubits,"cx":ops.get("cx",0),
         "depth":compiled.depth(),"compiled_counts":ops,
         "compile_seconds":round(time.perf_counter()-start,3)}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=437)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=18)
 p.add_argument("--optimization-level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--objective",choices=("cx","depth"),default="cx")
 p.add_argument("--seed",type=int,default=74)
 p.add_argument("--skip-stage-screen",action="store_true",
   help="Only compile the two pure architectures; no hybrid")
 p.add_argument("--output",default="results/a74_n437_qpe_level1.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base required")
 if a.bits<2 or a.bits>2*a.n.bit_length():p.error("bits must be 2..2*bit_length(n)")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A74_MATCHED_OPT_COMPLETE_RECYCLED_QPE",
    "n":a.n,"base":a.base,"bits":a.bits,"level":a.optimization_level,
    "seed":a.seed,"objective":a.objective,"status":"IN_PROGRESS",
    "stage_costs":[],"full_circuits":[],
    "simulated_shots":0,"paid_hardware_jobs":0,
    "warnings":["Stagewise greedy selection need not optimize the full-circuit objective.",
                "Unrouted Aer compilation is not hardware-specific transpilation."]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  sim=AerSimulator(method="matrix_product_state",max_parallel_threads=2)
  powers=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
  nontrivial=list(dict.fromkeys(x for x in powers if x!=1))
  winners={}
  if not a.skip_stage_screen:
   for power in nontrivial:
    row={"power":power,"architectures":{}}
    for name,builder in (("a44",a44.build),("a64",a64.build)):
     built=builder(a.n,power)
     qc=built[0] if isinstance(built,tuple) else built
     row["architectures"][name]=metrics(qc,sim,a.optimization_level,a.seed)
    aa=row["architectures"]
    winner=min(aa,key=lambda k:(aa[k][a.objective],aa[k]["cx"],aa[k]["depth"]))
    row["winner"]=winner
    winners[power]=winner
    d["stage_costs"].append(row);save()
    print(f"A74 STAGE power={power} A44_CX={aa['a44']['cx']} A64_CX={aa['a64']['cx']} winner={winner}",flush=True)
  architectures=["a44","a64"]+(["hybrid"] if winners else [])
  for name in architectures:
   if name=="hybrid":
    # Hybrid uses the larger A64 scratch space, even for A44-only stages.
    qc,stages=hybrid_build(a.n,a.base,a.bits,winners)
   else:qc,stages=pure_build(a.n,a.base,a.bits,name)
   row={"architecture":name,"source_qubits":qc.num_qubits,
        "source_depth":qc.depth(),"stage_count":len(stages),
        "stage_assignments":{str(k):v for k,v in winners.items()} if name=="hybrid" else None}
   d["full_circuits"].append(row);save()
   row["compiled"]=metrics(qc,sim,a.optimization_level,a.seed);save()
   print(f"A74 FULL {name} qubits={row['compiled']['qubits']} CX={row['compiled']['cx']} depth={row['compiled']['depth']}",flush=True)
  d["best_cx"]=min(d["full_circuits"],key=lambda r:(r["compiled"]["cx"],r["compiled"]["depth"],r["compiled"]["qubits"]))["architecture"]
  d["best_depth"]=min(d["full_circuits"],key=lambda r:(r["compiled"]["depth"],r["compiled"]["cx"],r["compiled"]["qubits"]))["architecture"]
  d["status"]="PASS_OPTIMIZED_FULL_QPE_COST_ONLY";save()
  print("A74 STATUS",d["status"],"BEST_CX",d["best_cx"],"BEST_DEPTH",d["best_depth"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
