#!/usr/bin/env python3
"""A98: checkpointed N2491 A87b-vs-A97 adaptive multiplier screening.

The per-constant selector compiles both adder candidates at the same u/cx
basis, objective CX. Full multiplier compilations are independently measured
with the SAME optimization level/seed. Source computational-basis semantics
and scratch cleanup are checked on identical seeded probes for both.

This is single-stage ideal arithmetic cost, not whole QPE or device fidelity.
No hardware jobs.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qrr_a87b_direct_prefix_multiplier import build as baseline
from qrr_a97_adaptive_modadd_multiplier import build as adaptive
from qrr_a92_boxed_qpe_topology_audit import audit

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--powers",nargs="+",type=int,default=[8,64,2448,2217,1051])
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=9801)
 p.add_argument("--probes",type=int,default=16)
 p.add_argument("--max-new-powers",type=int,default=1)
 p.add_argument("--output",default="results/a98_n2491_adaptive_power_profile.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd N>=9 coprime base")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits outside allowed range")
 if a.probes<0 or a.max_new_powers<1:p.error("nonnegative probes and positive max-new-powers required")
 schedule=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
 powers=list(dict.fromkeys(a.powers))
 if not powers or any(k==1 or k not in schedule for k in powers):
  p.error("All --powers must be nonidentity QPE stage powers")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 settings={"n":a.n,"base":a.base,"bits":a.bits,"powers":powers,
           "level":a.level,"seed":a.seed,"probes":a.probes}
 if out.exists():
  d=json.loads(out.read_text())
  if d.get("settings")!=settings:raise ValueError("Checkpoint setting mismatch; change output path")
 else:
  d={"experiment":"A98_A97_ADAPTIVE_LARGE_MODULUS_POWER_SCREEN","settings":settings,
     "status":"IN_PROGRESS","stages":{},"qpu_jobs":0,
     "limitations":["Single-stage separately transpiled ideal u/cx gate counts, not whole QPE",
       "Selected on standalone adders; full multiplier native cost is authoritative",
       "Source sampled basis checks are not coherent phase equality or physical noise",
       "No IBM-target routing, noise simulation or device job"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  new=0
  for power in powers:
   row=d["stages"].setdefault(str(power),{"power":power,"architectures":{}})
   if all(n in row["architectures"] for n in ("a87b","a97")):continue
   for name in ("a87b","a97"):
    if name in row["architectures"]:continue
    t=time.perf_counter()
    if name=="a87b":circuit=baseline(a.n,power);ledger=None
    else:circuit,ledger=adaptive(a.n,power,level=a.level,seed=a.seed,objective="cx")
    # Independent semantics check uses this already-built circuit; source
    # function signature agrees with the verifier and does not reselect.
    cases=audit(a.n,power,(lambda n,k,circ=circuit:circ),a.probes,a.seed)
    native=transpile(circuit,basis_gates=["u","cx"],
       optimization_level=a.level,seed_transpiler=a.seed)
    result={"qubits":native.num_qubits,"cx":int(native.count_ops().get("cx",0)),
      "depth":native.depth(),"verified_basis_cases":cases,
      "seconds":round(time.perf_counter()-t,3)}
    if ledger is not None:
     result["selected_adders"]={
        key:sum(v["selected"]==key for v in ledger.values()) for key in ("a87b","a96")}
     result["unique_adder_constants"]=len(ledger)
    row["architectures"][name]=result;save()
    print("A98",power,name,"CX",result["cx"],"depth",result["depth"],
      "basis",cases,"selection",result.get("selected_adders"),flush=True)
   old=row["architectures"]["a87b"];newrow=row["architectures"]["a97"]
   row["comparison"]={"delta_cx":newrow["cx"]-old["cx"],
     "delta_depth":newrow["depth"]-old["depth"],
     "cx_reduction_pct":round(100*(old["cx"]-newrow["cx"])/old["cx"],4),
     "depth_reduction_pct":round(100*(old["depth"]-newrow["depth"])/old["depth"],4)}
   save();print("A98 POWER RESULT",power,row["comparison"],flush=True)
   new+=1
   if new>=a.max_new_powers:break
  complete=[k for k in powers if all(n in d["stages"].get(str(k),{}).get("architectures",{}) for n in ("a87b","a97"))]
  d["completed_powers"]=len(complete);d["requested_powers"]=len(powers)
  if len(complete)==len(powers):
   sums={name:{"cx":sum(d["stages"][str(k)]["architectures"][name]["cx"] for k in powers),
     "depth":sum(d["stages"][str(k)]["architectures"][name]["depth"] for k in powers)}
     for name in ("a87b","a97")}
   x=sums["a87b"];y=sums["a97"]
   d["isolated_stage_sums_only"]=sums
   d["comparison"]={"cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
     "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4),
     "cx_stage_wins":sum(d["stages"][str(k)]["comparison"]["delta_cx"]<0 for k in powers),
     "depth_stage_wins":sum(d["stages"][str(k)]["comparison"]["delta_depth"]<0 for k in powers)}
   d["status"]="PASS_ISOLATED_STAGE_COMPARATIVE_SCREEN"
  else:d["status"]="PARTIAL_CHECKPOINT"
  save();print("A98 STATUS",d["status"],len(complete),"/",len(powers),
    d.get("comparison",{}),flush=True)
 except Exception:
  d["status"]="ERROR_OR_INTERRUPTED";d["error"]=traceback.format_exc()[-6000:];save();raise

if __name__=="__main__":main()
