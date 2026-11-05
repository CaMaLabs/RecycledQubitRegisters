#!/usr/bin/env python3
"""A109: whole-multiplier coordinate descent over A97's reversible adder choices.

A97's per-constant choice minimizes an isolated add circuit's native CX
cost. A109 measures the FULL composed controlled modular multiplier after
transpilation and greedily flips choices only when the complete circuit
improves. Source behavior is unchanged because both adders implement the
same exact reversible map, but this is independently verified exhaustively
on the chosen modulus with clean workspace.

A positive result is not assumed. Full compile counts are valid only for
the given Qiskit optimizer, basis and seed, and may not survive IBM routing.
"""
import argparse,copy,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a97_adaptive_modadd_multiplier import build as a97_build
from qrr_a87b_direct_prefix_multiplier import verify_multiplier

def native_cost(q,level,seed):
 routed=transpile(q,basis_gates=["u","cx"],
    optimization_level=level,seed_transpiler=seed)
 return {"cx":int(routed.count_ops().get("cx",0)),
   "depth":int(routed.depth()),"qubits":routed.num_qubits}

def metric(row,objective):
 if objective=="depth":return row["depth"],row["cx"]
 return row["cx"],row["depth"]

def circuit_with_choices(n,a,level,seed,assign):
 choices={int(k):{"selected":v} for k,v in assign.items()}
 q,ledger=a97_build(n,a,level=level,seed=seed,objective="cx",choices=choices)
 if {int(k):v["selected"] for k,v in ledger.items()}!={int(k):v for k,v in assign.items()}:
  raise AssertionError("A97 used a different selector assignment")
 return q

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=10901)
 p.add_argument("--objective",choices=("cx","depth"),default="cx")
 p.add_argument("--max-passes",type=int,default=3)
 p.add_argument("--max-tests",type=int,default=128)
 p.add_argument("--output",default="results/a109_n35_full_multiplier_choice_search.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.a)!=1:p.error("odd N >=9, coprime multiplier required")
 if a.max_passes<1 or a.max_tests<1:p.error("max-passes and max-tests must be >=1")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 settings={"n":a.n,"a":a.a,"level":a.level,"seed":a.seed,
    "objective":a.objective,"max_passes":a.max_passes,"max_tests":a.max_tests}
 if path.exists():
  d=json.loads(path.read_text())
  if d.get("settings")!=settings:
   raise ValueError("Checkpoint parameters differ; use a fresh output path")
 else:
  d={"experiment":"A109_FULL_MULTIPLIER_ADDER_SELECTION_COORDINATE_DESCENT",
    "settings":settings,"status":"IN_PROGRESS",
    "tested_candidates":[],"accepted_moves":[],"qpu_jobs_submitted":0,
    "limitations":["Full native u/cx compilation is authoritative for this experiment only",
      "No physical routing, Aer phase study or cryptographic-strength factoring",
      "Correctness tests cover initialized-zero ancillary workspace, not arbitrary scratch states",
      "The greedy finite search is not a global optimizer and may find no better choices"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  q_initial,ledger=a97_build(a.n,a.a,level=a.level,seed=a.seed,objective="cx")
  init_assign={str(k):v["selected"] for k,v in sorted(ledger.items())}
  init_cost=native_cost(q_initial,a.level,a.seed)
  d["frozen_a97"]={"native":init_cost,"choices":init_assign}
  if "best" not in d:
   d["best"]={"native":init_cost,"choices":init_assign}
   d["passes_completed"]=0
  elif d["best"]["choices"]!=init_assign:
   # A prior accepted checkpoint is valid; rebuild and independently confirm.
   check=native_cost(circuit_with_choices(a.n,a.a,a.level,a.seed,d["best"]["choices"]),a.level,a.seed)
   if check!=d["best"]["native"]:raise AssertionError("Existing best checkpoint native costs changed")
  save()
  print("A109 FROZEN",init_cost,"constants",len(init_assign),flush=True)
  tests=0
  for attempt in range(d.get("passes_completed",0),a.max_passes):
   selected=d["best"]["choices"]
   best_cost=d["best"]["native"]
   winner=None
   for k in sorted(selected,key=int):
    if tests>=a.max_tests:break
    alt=copy.copy(selected)
    alt[k]="a96" if selected[k]=="a87b" else "a87b"
    candidate=circuit_with_choices(a.n,a.a,a.level,a.seed,alt)
    measured=native_cost(candidate,a.level,a.seed)
    tests+=1
    row={"pass":attempt+1,"constant":int(k),"from":selected[k],
      "to":alt[k],**measured}
    d["tested_candidates"].append(row)
    if metric(measured,a.objective)<metric(best_cost,a.objective):
     best_cost=measured;winner={"constant":k,"choices":alt,"native":measured,
       "previous":selected[k],"pass":attempt+1}
    save()
   if winner:
    d["best"]={"native":winner["native"],"choices":winner["choices"]}
    d["accepted_moves"].append({"pass":winner["pass"],
      "constant":int(winner["constant"]),"from":winner["previous"],
      "to":winner["choices"][winner["constant"]],**winner["native"]})
    print("A109 ACCEPT",d["accepted_moves"][-1],flush=True)
   d["passes_completed"]=attempt+1
   save()
   if not winner or tests>=a.max_tests:break
  q_final=circuit_with_choices(a.n,a.a,a.level,a.seed,d["best"]["choices"])
  measured=native_cost(q_final,a.level,a.seed)
  if measured!=d["best"]["native"]:raise AssertionError("Final compiled costs changed")
  if measured["qubits"]!=init_cost["qubits"]:
   raise AssertionError("Candidate increased logical qubit count")
  cases_initial=verify_multiplier(a.n,a.a,lambda n,k:q_initial)
  cases_final=verify_multiplier(a.n,a.a,lambda n,k:q_final)
  x=init_cost;y=measured
  d["verification"]={"baseline_cases":cases_initial,"candidate_cases":cases_final,
    "clean_ancillas":True,"qubit_count_unchanged":True}
  d["comparison"]={"delta_cx":y["cx"]-x["cx"],
    "cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
    "delta_depth":y["depth"]-x["depth"],
    "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4)}
  d["status"]="PASS_EXACT_MULTIPLIER_GREEDY_SEARCH" if metric(y,a.objective)<metric(x,a.objective) else "PASS_NO_WHOLE_MULTIPLIER_IMPROVEMENT"
  save()
  print("A109 SELECTED",d["best"]["choices"],flush=True)
  print("A109 STATUS",d["status"],d["comparison"],"tests",tests,flush=True)
 except Exception:
  d["status"]="ERROR_OR_INTERRUPTED";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
