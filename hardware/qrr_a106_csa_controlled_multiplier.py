#!/usr/bin/env python3
"""A106: first exact clean carry-save controlled modular multiplier.

Reversible gate-level construction for odd N, coprime A:
 |control,x,zero,scratch=0> -> |control,(A*x mod N if enabled),zero,scratch=0>
with invalid x>=N unchanged, same external contract as A97. A102's
fully clean modulo-N three-input carry-save XOR operation serves as
a reusable reduction kernel. A ternary partial-product tree accumulates
the constant-weighted bits of x. Every temporary tree node is uncomputed,
and A97-style compute/swap/inverse-compute cleans the product register.

A106 is a FIRST architectural integration, NOT an optimized carry-save
multiplier. The extra width and duplicated reversible modular reduction
can overwhelm all arithmetic wins. Never treat an individual modular
sum gain as evidence that the complete multiplier wins.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a102_clean_modular_csa_three_sum import build as mod3
from qrr_a97_adaptive_modadd_multiplier import build as baseline
from qrr_a87b_direct_prefix_multiplier import verify_multiplier
from qrr_a61_binary_modular_adder import ge

def tree_structure(w):
 """Make node indexes and topological steps from w weighted leaf bits."""
 nodes=[];level=[("leaf",j) for j in range(w)]
 while len(level)>1:
  nxt=[]
  for start in range(0,len(level),3):
   group=level[start:start+3]
   if len(group)==1:
    nxt.append(group[0]);continue
   index=len(nodes)
   nodes.append({"index":index,"inputs":group})
   nxt.append(("node",index))
  level=nxt
 return nodes,level[0]

def build(n,a,architecture="carry_save",max_qubits=512):
 if n<3 or n%2!=1 or math.gcd(n,a)!=1:
  raise ValueError("odd N>=3 and coprime A required")
 w=n.bit_length();a%=n;inverse=pow(a,-1,n)
 kernel,km=mod3(n,architecture)
 W=km["sum_guard_bits"];res_offset=km["output_register_offset"]
 nodes,root=tree_structure(w)
 # 2w+2: control, x, y, active (same functional contract as A97);
 # +one w-bit output per tree node, and one reusable A102 kernel register.
 total=2*w+2+len(nodes)*w+kernel.num_qubits
 if total>max_qubits:
  raise ValueError(f"A106_{architecture} requires {total} logical qubits at N={n} (max_qubits={max_qubits}); no circuit allocated")
 q=QuantumCircuit(total)
 ctrl=q.qubits[0];x=list(q.qubits[1:1+w]);y=list(q.qubits[1+w:1+2*w])
 active=q.qubits[2*w+1]
 off=2*w+2
 node_regs=[list(q.qubits[off+j*w:off+(j+1)*w]) for j in range(len(nodes))]
 scratch=list(q.qubits[off+len(nodes)*w:])
 inv_kernel=kernel.inverse()
 def toggle_active():
  q.cx(ctrl,active)
  ge(q,x+[ctrl],active,(1<<w)+n)
 def compute_node(node,coef):
  # Kernel three operand registers start clean, and are restored to
  # their exact original input values by the kernel/uncompute sequence.
  inputs=node["inputs"]
  for slot,src in enumerate(inputs):
   input_offset=slot*W
   if src[0]=="leaf":
    const=(coef*(1<<src[1]))%n
    if const:
     for bit in range(w):
      if const>>bit&1:q.ccx(active,x[src[1]],scratch[input_offset+bit])
   else:
    for bit in range(w):
     q.cx(node_regs[src[1]][bit],scratch[input_offset+bit])
  q.compose(kernel,qubits=scratch,inplace=True)
  for bit in range(w):
   q.cx(scratch[res_offset+bit],node_regs[node["index"]][bit])
  q.compose(inv_kernel,qubits=scratch,inplace=True)
  for slot,src in reversed(list(enumerate(inputs))):
   input_offset=slot*W
   if src[0]=="leaf":
    const=(coef*(1<<src[1]))%n
    if const:
     for bit in range(w):
      if const>>bit&1:q.ccx(active,x[src[1]],scratch[input_offset+bit])
   else:
    for bit in range(w):
     q.cx(node_regs[src[1]][bit],scratch[input_offset+bit])
 def accumulate(coef):
  for node in nodes:compute_node(node,coef)
  if root[0]=="node":
   register=node_regs[root[1]]
   for bit in range(w):q.cx(register[bit],y[bit])
  else:
   # Only possible with a 1-bit word; disallowed by N>=3.
   raise AssertionError("unexpected leaf root")
  for node in reversed(nodes):compute_node(node,coef)
 toggle_active()
 accumulate(a)
 for xi,yi in zip(x,y):q.cswap(active,xi,yi)
 accumulate(-inverse)
 toggle_active()
 return q,{"n":n,"a":a,"architecture":architecture,"qubits":total,
   "scratch_qubits":kernel.num_qubits,"tree_node_count":len(nodes),
   "tree_node_qubits":len(nodes)*w,"w":w,
   "source_ops":len(q.data),"active_qubit":2*w+1}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15)
 p.add_argument("--a",type=int,default=2)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=10601)
 p.add_argument("--max-qubits",type=int,default=512)
 p.add_argument("--max-candidate-source-ops",type=int,default=500000)
 p.add_argument("--skip-native",action="store_true")
 p.add_argument("--output",default="results/a106_csa_controlled_multiplier.json")
 a=p.parse_args()
 if a.n<3 or a.n%2!=1 or math.gcd(a.n,a.a)!=1:p.error("N must be odd >=3, multiplier coprime to N")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A106_FIRST_CLEAN_CSA_CONTROLLED_MODULAR_MULTIPLIER",
    "settings":{"n":a.n,"a":a.a,"level":a.level,"seed":a.seed,
      "max_qubits":a.max_qubits,"skip_native":a.skip_native},
    "status":"IN_PROGRESS","candidate":{},"baseline":{},
    "limits":["First reversible ternary partial-product tree construction; may be much wider and more costly than A97",
      "Complete multiplier source basis tests exact at specified modulus and initial zero workspace",
      "No proof of quantum phase equivalence from computational basis alone",
      "Local u/cx transpilation only, not IBM routing or QPU jobs",
      "IBM Fez has 156 physical qubits: logical widths above this cannot fit"],
    "qpu_jobs_submitted":0}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  start=time.perf_counter()
  q,meta=build(a.n,a.a,"carry_save",a.max_qubits)
  d["candidate"]["structure"]=meta;save()
  print("A106 STRUCTURE",meta,flush=True)
  if len(q.data)>a.max_candidate_source_ops:
   raise RuntimeError("Candidate source circuit exceeds --max-candidate-source-ops; resource screen stopped before verification")
  cases=verify_multiplier(a.n,a.a,lambda n,k:q)
  d["candidate"]["basis_cases"]=cases
  d["candidate"]["basis_clean_ancillas"]=True
  d["candidate"]["elapsed_seconds"]=round(time.perf_counter()-start,3)
  save()
  print("A106 MULTIPLIER PASS",a.n,a.a,"basis",cases,flush=True)
  if a.skip_native:
   d["status"]="PASS_EXACT_SOURCE_MULTIPLIER_ONLY"
   save();print("A106 STATUS",d["status"],flush=True);return
  # Local full-multiplier comparisons, not isolated adder comparisons.
  for name,circuit in (("a97",baseline(a.n,a.a,level=a.level,seed=a.seed)[0]),
                        ("a106_carry_save",q)):
   tic=time.perf_counter()
   native=transpile(circuit,basis_gates=["u","cx"],
       optimization_level=a.level,seed_transpiler=a.seed)
   row={"qubits":circuit.num_qubits,"cx":int(native.count_ops().get("cx",0)),
        "depth":int(native.depth()),"elapsed_seconds":round(time.perf_counter()-tic,3)}
   d["baseline" if name=="a97" else "candidate"]["native"]=row
   save();print("A106 NATIVE",name,row,flush=True)
  base=d["baseline"]["native"];cand=d["candidate"]["native"]
  d["comparison"]={"delta_cx":cand["cx"]-base["cx"],
     "cx_reduction_pct":round(100*(base["cx"]-cand["cx"])/base["cx"],4),
     "delta_depth":cand["depth"]-base["depth"],
     "depth_reduction_pct":round(100*(base["depth"]-cand["depth"])/base["depth"],4),
     "extra_logical_qubits":cand["qubits"]-base["qubits"]}
  d["status"]="PASS_EXACT_MULTIPLIER_AND_COMPARATIVE_COST"
  save();print("A106 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL_OR_RESOURCE_LIMIT";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
