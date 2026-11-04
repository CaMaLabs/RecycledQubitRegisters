#!/usr/bin/env python3
"""A77: compact, stage-cached 24-bit recycled-QPE assembly.

Construct each distinct modular-power circuit once as a reusable boxed gate;
append its definition without flattening into the dynamic QPE circuit.
QPY export is optional. No full native transpilation or Aer execution.
Resource totals, if supplied, are ISOLATED stage estimates, not full-QPE costs.
"""
import argparse,collections,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,qpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a64_binary_modular_multiplier as a64
import qrr_a76_reduced_active_flag as a76

def build(n,base,bits,architecture):
 w=n.bit_length()
 phase=QuantumRegister(1,"phase")
 work=QuantumRegister(w,"work")
 scratch=QuantumRegister(w+6 if architecture=="a64" else w+5,"scratch")
 classical=ClassicalRegister(bits,"readout")
 qc=QuantumCircuit(phase,work,scratch,classical,name="recycled_qpe_boxed")
 qc.x(work[0]);cache={};rows=[]
 for j in range(bits-1,-1,-1):
  power=pow(base,1<<j,n)
  qc.h(phase[0])
  if power!=1:
   if power not in cache:
    source=a64.build(n,power) if architecture=="a64" else a76.build(n,power)
    if source.num_qubits!=qc.num_qubits:raise AssertionError("Gate width mismatch")
    cache[power]=source.to_gate(label=f"{architecture}_pow_{power}")
   qc.append(cache[power],list(phase)+list(work)+list(scratch))
  for t in range(bits-1,j,-1):
   with qc.if_test((classical[bits-1-t],1)):
    qc.p(-2*math.pi/(1<<(t-j+1)),phase[0])
  qc.h(phase[0]);qc.measure(phase[0],classical[bits-1-j])
  if j>0:qc.reset(phase[0])
  rows.append({"j":j,"power":power,"identity":power==1})
 return qc,cache,rows

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--architecture",choices=("a64","a76"),default="a76")
 p.add_argument("--stage-profile",default="results/a75_n2491_24bit_profile.json")
 p.add_argument("--output",default="results/a77_n2491_boxed_source.json")
 p.add_argument("--qpy",default=None,help="Optional local QPY circuit export (not native compiled)")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base")
 if a.bits<2 or a.bits>2*a.n.bit_length():p.error("bits outside requested precision range")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A77_COMPACT_BOXED_RECYCLED_QPE","n":a.n,"base":a.base,"bits":a.bits,
    "architecture":a.architecture,"status":"IN_PROGRESS","quantum_shots":0,
    "full_native_compilation":False,"hardware_jobs":0}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  start=time.perf_counter();qc,cache,rows=build(a.n,a.base,a.bits,a.architecture)
  d["source"]={"qubits":qc.num_qubits,"classical_bits":qc.num_clbits,
     "top_level_instructions":len(qc.data),"source_depth":qc.depth(),
     "unique_boxed_multiplier_definitions":len(cache),
     "boxed_definition_operations":sum(len(g.definition.data) for g in cache.values()),
     "dynamic_if_else":qc.count_ops().get("if_else",0),
     "measurements":qc.count_ops().get("measure",0),
     "resets":qc.count_ops().get("reset",0)}
  d["stage_schedule"]=rows
  expected_feedback=a.bits*(a.bits-1)//2
  assert d["source"]["dynamic_if_else"]==expected_feedback
  assert d["source"]["measurements"]==a.bits
  assert d["source"]["resets"]==a.bits-1
  d["build_seconds"]=round(time.perf_counter()-start,3)
  save()
  profile=Path(a.stage_profile)
  if profile.is_file():
   s=json.loads(profile.read_text())
   if s.get("settings")=={"n":a.n,"base":a.base,"bits":a.bits,"level":1} and s.get("status")=="PASS_ISOLATED_STAGE_SUM_ESTIMATE_NOT_FULL_QPE":
    if a.architecture=="a64":
     d["isolated_stage_cost_only"]=s["a64_isolated_stage_sum"]
    else:
     d["isolated_stage_cost_only"]={"status":"NOT_MEASURED_FOR_A76",
       "note":"A75 A64 stage cost cannot be reused for new A76 circuit"}
  if a.qpy:
   dest=Path(a.qpy);dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open("wb") as handle:qpy.dump(qc,handle)
   d["qpy_path"]=str(dest)
  d["status"]="PASS_COMPACT_DYNAMIC_SOURCE_NOT_NATIVE_COMPILED";save()
  print("A77 STATUS",d["status"],"qubits",qc.num_qubits,
        "boxed_stages",len(cache),"top_level_ops",len(qc.data),
        "boxed_definition_ops",d["source"]["boxed_definition_operations"],
        "seconds",d["build_seconds"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-4000:];save();raise

if __name__=="__main__":main()
