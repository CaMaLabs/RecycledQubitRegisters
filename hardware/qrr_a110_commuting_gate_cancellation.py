#!/usr/bin/env python3
"""A110: phase-exact commutation-aware cancellation on frozen A97 multiplier.

Applies a conservative reversible gate rewrite to the ACTUAL source A97
circuit: G ... G -> identity only if G commutes with every intermediate
gate. X/CX/CCX/open-control MCX are XOR-target maps; two commute when
neither writes a control read by the other, including shared controls and
shared XOR target. CSWAP gates commute ONLY across disjoint support.

All affected source gates are classical permutation gates, hence the
rewrite is phase-exact on arbitrary superpositions, not merely basis
equivalent (subject to correct gate semantics). Exhaustive basis checks
and an independent full native u/cx compile are still required.

Benchmark objective: native full-multiplier CX and depth, same qubits.
A negative result is a valid screening result. No QPU jobs.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a97_adaptive_modadd_multiplier import build as frozen_build
from qrr_a87b_direct_prefix_multiplier import verify_multiplier

def shape(q,inst):
 op=inst.operation
 bits=tuple(q.find_bit(x).index for x in inst.qubits)
 name=op.name
 if name=="x":
  return {"key":(name,bits,None),"controls":frozenset(),
   "writes":frozenset(bits),"support":frozenset(bits),"xor":True}
 if name in ("cx","ccx") or name.startswith(("mcx","ccx_o","cx_o")):
  state=getattr(op,"ctrl_state",None)
  if state is None:state=(1<<(len(bits)-1))-1
  return {"key":(name,bits,state),"controls":frozenset(bits[:-1]),
   "writes":frozenset((bits[-1],)),"support":frozenset(bits),"xor":True}
 if name=="cswap":
  return {"key":(name,bits,None),"controls":frozenset((bits[0],)),
   "writes":frozenset(bits[1:]),"support":frozenset(bits),"xor":False}
 raise ValueError(f"Unsupported gate for safe involution rewrite: {name}")

def commute(a,b):
 if a["xor"] and b["xor"]:
  return not (a["writes"] & b["controls"]) and not (b["writes"] & a["controls"])
 return not (a["support"] & b["support"])

def simplify(q,max_window):
 source=[(inst,shape(q,inst)) for inst in q.data]
 active=[];removed=[];passes=0
 # Rescan to a stable fixed point. Every cancellation removes two ops.
 while True:
  passes+=1;stack=[];changes=0
  for original,desc in active if passes>1 else source:
   hit=None
   steps=0
   for i in range(len(stack)-1,-1,-1):
    previous=stack[i][1]
    if previous["key"]==desc["key"]:
     hit=i;break
    if not commute(previous,desc):
     break
    steps+=1
    if steps>=max_window:break
   if hit is None:stack.append((original,desc))
   else:
    prior=stack.pop(hit)
    removed.append({"gate":desc["key"][0],"distance":len(stack)-hit,
       "qubits":list(desc["key"][1])})
    changes+=1
  active=stack
  if not changes:break
  if passes>len(source)//2+1:raise RuntimeError("Unexpected cancellation nontermination")
 result=QuantumCircuit(q.num_qubits)
 for original,desc in active:
  result.append(original.operation,
    [result.qubits[q.find_bit(qbit).index] for qbit in original.qubits],[])
 if len(q.data)-len(result.data)!=2*len(removed):
  raise AssertionError("Rewrite did not conserve gate removal accounting")
 return result,{"initial_source_ops":len(q.data),
    "final_source_ops":len(result.data),
    "cancelled_pairs":len(removed),"removed_source_ops":2*len(removed),
    "rewrite_passes":passes,
    "removed_gates_by_type":dict(collections.Counter(x["gate"] for x in removed)),
    "examples":removed[:20]}

def native(q,level,seed):
 compiled=transpile(q,basis_gates=["u","cx"],
    optimization_level=level,seed_transpiler=seed)
 return {"cx":int(compiled.count_ops().get("cx",0)),
    "depth":int(compiled.depth()),"logical_qubits":q.num_qubits}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=11001)
 p.add_argument("--max-window",type=int,default=200)
 p.add_argument("--output",default="results/a110_n35_commuting_cancellation.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.a)!=1:p.error("odd modulus >=9, coprime multiplier")
 if a.max_window<1:p.error("max-window must be positive")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A110_PHASE_EXACT_A97_COMMUTATION_CANCELLATION",
   "settings":vars(a),"status":"IN_PROGRESS","qpu_jobs_submitted":0,
   "limitations":["Conservative source gate cancellation; other Boolean resyntheses are untested",
     "Full native u/cx local compilation; not backend-routed or physically noisy",
     "No other research methods, ML-KEM, or factoring breakthrough implied",
     "Result may be negative if Qiskit already cancels equivalent gates"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  start=time.perf_counter()
  frozen,selected=frozen_build(a.n,a.a,level=a.level,seed=a.seed,objective="cx")
  revised,report=simplify(frozen,a.max_window)
  d["rewrite"]=report
  d["architecture_choices"]={str(k):v["selected"] for k,v in sorted(selected.items())}
  save()
  print("A110 REWRITE",report,flush=True)
  for label,source in (("a97_frozen",frozen),("a110_candidate",revised)):
   tic=time.perf_counter()
   count=verify_multiplier(a.n,a.a,lambda n,m,qq=source:qq)
   cost=native(source,a.level,a.seed)
   cost["basis_cases"]=count
   cost["elapsed_seconds"]=round(time.perf_counter()-tic,3)
   d[label]=cost;save()
   print("A110 NATIVE",label,cost,flush=True)
  left=d["a97_frozen"];right=d["a110_candidate"]
  d["comparison"]={"delta_cx":right["cx"]-left["cx"],
    "delta_depth":right["depth"]-left["depth"],
    "cx_reduction_pct":round(100*(left["cx"]-right["cx"])/left["cx"],4),
    "depth_reduction_pct":round(100*(left["depth"]-right["depth"])/left["depth"],4),
    "extra_qubits":right["logical_qubits"]-left["logical_qubits"]}
  d["status"]="PASS_EXACT_NATIVE_IMPROVEMENT" if (
    right["cx"]<left["cx"] and right["depth"]<left["depth"]) else "PASS_EXACT_REWRITE_NO_DUAL_NATIVE_WIN"
  save()
  print("A110 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
