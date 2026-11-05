#!/usr/bin/env python3
"""A97: adaptive reversible modular-add synthesis, A87b vs A96.

Select between exact gate-level adder candidates per modular constant based
on locally transpiled CX/depth cost, then construct the SAME A87b multiplier
with the selected adders. The selection is amortized over a repeated adder
within each multiplier and does NOT change the arithmetic function.

IMPORTANT: Per-adder costs are a selection heuristic, not evidence of full
multiplier improvement. Both candidate and A87b full multipliers are
independently compiled with the same settings and validated exhaustively.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a61_binary_modular_adder import ge
from qrr_a87b_direct_prefix_multiplier import add as a87b_add,build as a87b_build,verify_multiplier
from qrr_a96_interval_prefix_multiplier import add as a96_add

def candidate_cost(qc,level,seed):
 native=transpile(qc,basis_gates=["u","cx"],optimization_level=level,seed_transpiler=seed)
 return {"cx":int(native.count_ops().get("cx",0)),"depth":int(native.depth())}

def build(n,a,level=1,seed=97,objective="cx",choices=None):
 if n<3 or n%2!=1 or math.gcd(n,a)!=1:
  raise ValueError("odd modulus, coprime multiplier")
 w=n.bit_length();a%=n;inverse=pow(a,-1,n)
 q=QuantumCircuit(2*w+6)
 c=q.qubits[0];x=list(q.qubits[1:1+w]);y=list(q.qubits[1+w:1+2*w])
 active,enable,lv,lw,lp=q.qubits[1+2*w:]
 cache={}
 ledger={} if choices is None else choices
 def toggle():
  q.cx(c,active);ge(q,x+[c],active,(1<<w)+n)
 toggle()
 def accumulate(source,target,coef):
  for j,s in enumerate(source):
   k=(coef*(1<<j))%n
   if not k:continue
   if k not in cache:
    if k not in ledger:
     left=a87b_add(n,k);right=a96_add(n,k)
     lc=candidate_cost(left,level,seed)
     rc=candidate_cost(right,level,seed)
     sel="a96" if (rc[objective],rc["depth" if objective=="cx" else "cx"]) < (lc[objective],lc["depth" if objective=="cx" else "cx"]) else "a87b"
     ledger[k]={"selected":sel,"a87b":lc,"a96":rc}
    cache[k]=(a96_add(n,k) if ledger[k]["selected"]=="a96" else a87b_add(n,k))
   q.ccx(active,s,enable)
   q.compose(cache[k],qubits=[enable]+target+[lv,lw,lp],inplace=True)
   q.ccx(active,s,enable)
 accumulate(x,y,a)
 for xi,yi in zip(x,y):q.cswap(active,xi,yi)
 accumulate(x,y,-inverse)
 toggle()
 return q,ledger

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--objective",choices=("cx","depth"),default="cx")
 p.add_argument("--seed",type=int,default=97)
 p.add_argument("--output",default="results/a97_adaptive_adder.json")
 args=p.parse_args()
 if args.n<9 or args.n%2!=1 or math.gcd(args.n,args.a)!=1:p.error("odd N >=9 and coprime a required")
 path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A97_ADAPTIVE_A87B_A96_MODADD_SELECTOR",
   "settings":{"n":args.n,"a":args.a,"level":args.level,"seed":args.seed,"objective":args.objective},
   "status":"IN_PROGRESS","rows":[],
   "limitations":["Per-constant native CX/depth is a heuristic for candidate selection",
     "Full multiplier native compilation and exact reversible semantics determine success",
     "No QPE Aer simulation, hardware routing, QPU job or noise simulation"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  t=time.perf_counter()
  mixed,ledger=build(args.n,args.a,args.level,args.seed,args.objective)
  d["adders"]={str(k):v for k,v in sorted(ledger.items())}
  d["adder_selection_counts"]={name:sum(v["selected"]==name for v in ledger.values()) for name in ("a87b","a96")}
  save()
  for name,qc in (("a87b",a87b_build(args.n,args.a)),("a97",mixed)):
   cases=verify_multiplier(args.n,args.a,(lambda n,a,qq=qc:qq))
   native=candidate_cost(qc,args.level,args.seed)
   row={"architecture":name,"qubits":qc.num_qubits,"basis_cases":cases,
        **native,"seconds_since_start":round(time.perf_counter()-t,3)}
   d["rows"].append(row);save()
   print("A97 COST",name,row,flush=True)
  x,y=d["rows"]
  d["comparison"]={"delta_cx":y["cx"]-x["cx"],
    "delta_depth":y["depth"]-x["depth"],
    "cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
    "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4)}
  d["status"]="PASS_EXHAUSTIVE_SOURCE_AND_NATIVE_COST"
  save();print("A97 SELECTED",d["adder_selection_counts"],flush=True)
  print("A97 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:];save();raise

if __name__=="__main__":main()
