#!/usr/bin/env python3
"""A53 independent semantic checks for A44/A50 (no QPU, no factor oracle).

Run real Qiskit/Aer multiplier circuit on basis states and inspect all output
bits incl clean ancillas. Audit A50 feedback control-flow guards/angles.
This is a sampled gate-semantic audit, not a mathematical proof for every input.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a44_generic_modular_multiplier as mult
import qrr_a50_n437_recycled_aer_quaspy as a50

def stage_aer(n,base,inputs,threads):
 src,mcx=mult.build(n,base)
 w=n.bit_length()
 sim=AerSimulator(method="matrix_product_state",max_parallel_threads=threads)
 tq=transpile(src,sim,optimization_level=0,seed_transpiler=53)
 results=[]
 for ctl,y in inputs:
  qc=QuantumCircuit(src.num_qubits,src.num_qubits)
  if ctl:qc.x(0)
  for j in range(w):
   if y>>j&1:qc.x(1+j)
  qc.compose(tq,inplace=True)
  qc.measure(range(src.num_qubits),range(src.num_qubits))
  outcome=sim.run(qc,shots=1,seed_simulator=53).result().get_counts()
  if len(outcome)!=1:raise AssertionError("non-deterministic basis result")
  got=int(next(iter(outcome)),2)
  expected_y=(base*y%n if ctl and y<n else y)
  expected=ctl|(expected_y<<1)
  ok=got==expected
  results.append({"control":ctl,"input":y,"expected_output":expected_y,
                  "actual_output":(got>>1)&((1<<w)-1),
                  "scratch":got>>(w+1),"control_out":got&1,"pass":ok})
  if not ok:raise AssertionError(f"MULTIPLIER FAIL n={n} base={base} ctl={ctl} y={y} got={got} expected={expected}")
 return {"n":n,"base":base,"logical_qubits":src.num_qubits,
         "mcx_instances":mcx,"basis_cases":results,"status":"PASS_SAMPLED_GATE_SEMANTICS"}

def feedback_audit(n,base,bits):
 circuit,stages=a50.build(n,base,bits)
 readout=circuit.cregs[0]
 seen={}
 for instruction in circuit.data:
  if instruction.operation.name!="if_else":continue
  op=instruction.operation
  condition=op.condition
  if condition is None or condition[1]!=1:
   raise AssertionError("incorrect conditional predicate")
  # The IfElseOp condition is attached to the ClassicalRegister or Clbit.
  if condition[0] not in readout:
   raise AssertionError("feedback references foreign bit")
  bit=readout.index(condition[0])
  body=op.blocks[0]
  if len(body.data)!=1 or body.data[0].operation.name!="p":
   raise AssertionError("feedback block does not contain exactly one phase")
  angle=float(body.data[0].operation.params[0])
  seen.setdefault(bit,[]).append(angle)
 expected={}
 for j in range(bits-1,-1,-1):
  for t in range(bits-1,j,-1):
   bit=bits-1-t
   expected.setdefault(bit,[]).append(-2*math.pi/(1<<(t-j+1)))
 if sum(map(len,seen.values()))!=bits*(bits-1)//2:
  raise AssertionError("missing feedback edges")
 for bit,angles in expected.items():
  left=sorted(seen.get(bit,[]));right=sorted(angles)
  if len(left)!=len(right) or any(abs(x-y)>1e-12 for x,y in zip(left,right)):
   raise AssertionError(f"feedback angle mismatch bit {bit}")
 if circuit.count_ops().get("measure")!=bits or circuit.count_ops().get("reset")!=bits-1:
  raise AssertionError("incorrect measure/reset counts")
 return {"n":n,"base":base,"bits":bits,"feedback_conditions":sum(map(len,seen.values())),
         "measurements":bits,"resets":bits-1,
         "status":"PASS_STRUCTURAL_FEEDBACK_SIGNS_AND_BIT_MAPPING",
         "limitation":"Structural audit; not a full independent dynamic quantum semantics proof"}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--threads",type=int,default=4)
 p.add_argument("--n437-cases",type=int,default=4)
 p.add_argument("--output",default="results/a53_gate_semantics_feedback.json")
 args=p.parse_args()
 out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A53_ACTUAL_GATE_SEMANTICS_AND_FEEDBACK_AUDIT",
         "status":"IN_PROGRESS","qpu_jobs":0,"rows":[]}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 try:
  # N35 provides small independently inspectable gate semantics including
  # bypass (control=0), multiplication (control=1), and out-of-range y.
  for n,base,inputs in [
   (35,2,[(0,0),(0,34),(1,0),(1,1),(1,7),(1,34),(1,35),(1,63)]),
   (437,8,[(0,1),(1,1),(1,436),(1,511)][:args.n437_cases])
  ]:
   t=time.perf_counter()
   row=stage_aer(n,base,inputs,args.threads)
   row["wall_seconds"]=round(time.perf_counter()-t,3)
   report["rows"].append(row);save()
   print("A53 GATE",n,base,len(inputs),"PASS seconds",row["wall_seconds"],flush=True)
  row=feedback_audit(437,8,18)
  report["rows"].append(row);save()
  print("A53 FEEDBACK",row["status"],row["feedback_conditions"],flush=True)
  report["status"]="PASS_SAMPLED_GATE_AND_STRUCTURAL_FEEDBACK_CHECKS"
  save()
 except Exception:
  report["status"]="FAIL_VALIDATION";report["error"]=traceback.format_exc()[-4000:]
  save();raise
 print("A53 STATUS",report["status"],"SAVED",out,flush=True)
if __name__=="__main__":main()
