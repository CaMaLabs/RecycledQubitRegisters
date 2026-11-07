#!/usr/bin/env python3
"""A114: explicit exact Clifford+T resource accounting for A97 versus A110.

Each controlled-X with k>=2 controls is expanded into a clean-ancilla
Toffoli ladder (2*k-3 Toffolis), using k-2 *additional clean scratch*
qubits. CSWAP is decomposed into CX, Toffoli, CX. Every Toffoli is expanded
by Qiskit's built-in CCXGate.definition, checked to use only Clifford+T
primitives. Count T/Tdg, CX, and an explicit conservative T-layer schedule.

This is a *specific exact synthesis construction*, NOT minimum T count,
a physical surface-code resource estimate, or an actual hardware run.
No IBM connectivity assumptions or QPU jobs.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit.circuit.library import CCXGate
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a97_adaptive_modadd_multiplier import build as a97
from qrr_a110_commuting_gate_cancellation import simplify
from qrr_a87b_direct_prefix_multiplier import verify_multiplier

ALLOWED={"h","s","sdg","t","tdg","cx","x","z","id","sx","sxdg"}
# sx/sxdg are Clifford, but the CCX definition should not require them.

def toffoli_recipe():
 q=CCXGate().definition
 recipe=[]
 for inst in q.data:
  name=inst.operation.name
  if name not in ALLOWED:
   raise ValueError(f"CCX definition contains gate not in Clifford+T: {name}")
  bits=[q.find_bit(bit).index for bit in inst.qubits]
  recipe.append((name,bits))
 if sum(name in ("t","tdg") for name,_ in recipe)!=7:
  raise AssertionError("Expected exact 7-T Qiskit CCX; version changed")
 if sum(name=="cx" for name,_ in recipe)!=6:
  raise AssertionError("Expected 6-CX Qiskit CCX; version changed")
 return recipe

class Ledger:
 def __init__(self,total_qubits,recipe):
  self.time=[0]*total_qubits
  self.counts=collections.Counter()
  self.recipe=recipe
  self.toffolis=0
  self.multi_control_hist=collections.Counter()
  self.max_t_depth=0
 def gate(self,name,qs):
  self.counts[name]+=1
  if name in ("t","tdg"):
   self.time[qs[0]]+=1
   self.max_t_depth=max(self.max_t_depth,self.time[qs[0]])
  elif len(qs)>1:
   sync=max(self.time[i] for i in qs)
   for i in qs:self.time[i]=sync
 def ccx(self,a,b,t):
  self.toffolis+=1
  q=(a,b,t)
  for name,bits in self.recipe:
   self.gate(name,[q[i] for i in bits])
 def mcx(self,controls,target,control_state,ancillas):
  k=len(controls);self.multi_control_hist[k]+=1
  if control_state<0 or control_state>=(1<<k):
   raise ValueError("Bad MCX control state")
  inverted=[controls[i] for i in range(k) if not control_state & (1<<i)]
  for i in inverted:self.gate("x",[i])
  if k==0:self.gate("x",[target])
  elif k==1:self.gate("cx",[controls[0],target])
  elif k==2:self.ccx(controls[0],controls[1],target)
  else:
   if len(ancillas)<k-2:raise AssertionError("Insufficient clean ancillas")
   self.ccx(controls[0],controls[1],ancillas[0])
   for j in range(2,k-1):
    self.ccx(ancillas[j-2],controls[j],ancillas[j-1])
   self.ccx(ancillas[k-3],controls[-1],target)
   for j in range(k-2,1,-1):
    self.ccx(ancillas[j-2],controls[j],ancillas[j-1])
   self.ccx(controls[0],controls[1],ancillas[0])
  for i in reversed(inverted):self.gate("x",[i])
 def feed(self,q,inst,extra):
  op=inst.operation;name=op.name
  bits=[q.find_bit(v).index for v in inst.qubits]
  if name=="x":self.gate("x",bits);return
  if name=="cx":self.gate("cx",bits);return
  if name=="cswap":
   c,a,b=bits
   self.gate("cx",[b,a]);self.ccx(c,a,b);self.gate("cx",[b,a])
   return
  if name=="ccx" or name.startswith(("mcx","ccx_o","cx_o")):
   controls=bits[:-1]
   state=getattr(op,"ctrl_state",None)
   if state is None:state=(1<<len(controls))-1
   self.mcx(controls,bits[-1],state,extra)
   return
  raise ValueError(f"Unsupported source gate: {name}")
 def report(self):
  return {"clifford_t_gate_counts":dict(sorted(self.counts.items())),
    "t_count":self.counts["t"]+self.counts["tdg"],
    "t_depth_fixed_construction_upper_bound":self.max_t_depth,
    "cx_count_explicit_construction":self.counts["cx"],
    "exact_ccx_instances":self.toffolis,
    "source_mcx_control_hist":dict(sorted((str(k),v) for k,v in self.multi_control_hist.items()))}

def evaluate(q,recipe):
 max_controls=max((len(inst.qubits)-1 for inst in q.data
    if inst.operation.name=="ccx" or inst.operation.name.startswith(("mcx","ccx_o","cx_o"))),default=0)
 extra=max(0,max_controls-2)
 ledger=Ledger(q.num_qubits+extra,recipe)
 scratch=list(range(q.num_qubits,q.num_qubits+extra))
 for inst in q.data:ledger.feed(q,inst,scratch)
 out=ledger.report()
 out["input_logical_qubits"]=q.num_qubits
 out["additional_clean_ancillas"]=extra
 out["constructed_logical_qubits"]=q.num_qubits+extra
 out["source_operations"]=len(q.data)
 return out

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=11401)
 p.add_argument("--max-window",type=int,default=200)
 p.add_argument("--skip-basis",action="store_true",
   help="Use only for large moduli; smaller n<=35 checked exhaustively by default")
 p.add_argument("--output",default="results/a114_n35_clifford_t_resource_audit.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.a)!=1:p.error("Odd N>=9 and coprime multiplier required")
 if a.max_window<1:p.error("Invalid max-window")
 output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A114_EXACT_CLIFFORD_T_CONSTRUCTION_RESOURCE_AUDIT",
   "settings":vars(a),"status":"IN_PROGRESS","qpu_jobs_submitted":0,
   "synthesis_model":{"controlled_x":"k-control X with k-2 clean ancillas, 2k-3 CCX for k>=2",
     "controlled_swap":"CX-CCX-CX","toffoli":"Qiskit CCXGate exact 7T 6CX standard definition",
     "t_depth":"Conservative constructive T-layer scheduling; preserve CX dependencies; not optimized minimum",
     "logical_qubits":"Original circuit qubits plus additional reusable clean MCX decomposition ancillas"},
   "limitations":["Exact constructive Clifford+T resource model, NOT optimal fault-tolerant synthesis",
     "Additional clean ancilla qubits MUST be counted in comparisons",
     "No surface code distance, distillation, physical qubits, magic state factories, or real QPU runtime",
     "Single source circuit per modulus and constant; stage totals do not form complete QPE",
     "Algebraic rewrite phase preservation is argued using commutation of permutation gates"]}
 def save():output.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  recipe=toffoli_recipe()
  d["ccx_recipe"]=[{"name":name,"local_qubits":bits} for name,bits in recipe]
  raw,choices=a97(a.n,a.a,level=a.level,seed=a.seed,objective="cx")
  opt,rewrite=simplify(raw,a.max_window)
  d["source_rewrite"]=rewrite
  d["adder_selections"]={str(k):v["selected"] for k,v in choices.items()}
  for name,q in (("a97",raw),("a110",opt)):
   start=time.perf_counter()
   if not a.skip_basis and a.n<=35:
    cases=verify_multiplier(a.n,a.a,lambda n,k,c=q:c)
   else:cases=None
   row=evaluate(q,recipe)
   row["verified_basis_cases"]=cases
   row["elapsed_seconds"]=round(time.perf_counter()-start,3)
   d[name]=row
   save()
   print("A114 RESOURCE",name,{k:row[k] for k in ("t_count",
     "t_depth_fixed_construction_upper_bound","cx_count_explicit_construction",
     "constructed_logical_qubits","exact_ccx_instances","verified_basis_cases")},flush=True)
  x=d["a97"];y=d["a110"]
  d["comparison"]={
    "t_count_saved":x["t_count"]-y["t_count"],
    "t_count_reduction_pct":round(100*(x["t_count"]-y["t_count"])/x["t_count"],4) if x["t_count"] else 0,
    "t_depth_bound_saved":x["t_depth_fixed_construction_upper_bound"]-y["t_depth_fixed_construction_upper_bound"],
    "t_depth_bound_reduction_pct":round(100*(x["t_depth_fixed_construction_upper_bound"]-y["t_depth_fixed_construction_upper_bound"])/x["t_depth_fixed_construction_upper_bound"],4) if x["t_depth_fixed_construction_upper_bound"] else 0,
    "constructed_qubit_delta":y["constructed_logical_qubits"]-x["constructed_logical_qubits"],
    "cx_reduction_pct":round(100*(x["cx_count_explicit_construction"]-y["cx_count_explicit_construction"])/x["cx_count_explicit_construction"],4) if x["cx_count_explicit_construction"] else 0}
  d["status"]="PASS_CONSTRUCTIVE_FT_RESOURCE_AUDIT" if d["comparison"]["constructed_qubit_delta"]==0 else "PASS_DIFFERENT_ANCILLA_BUDGETS"
  save()
  print("A114 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
