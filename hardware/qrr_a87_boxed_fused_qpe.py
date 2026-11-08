#!/usr/bin/env python3
"""A87: compact full 24-bit recycled QPE using A84 fused-carry arithmetic.

This is SOURCE assembly, NOT whole-circuit native transpilation or quantum
simulation. Every modular power is cached as a boxed reversible subcircuit.
Can optionally cross-check completed A86 independent stage-cost checkpoint.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,qpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a84_fused_carry_multiplier import build as fused_build

def build(n,base,bits):
 w=n.bit_length()
 phase=QuantumRegister(1,"phase")
 work=QuantumRegister(w,"work")
 scratch=QuantumRegister(w+5,"scratch")
 classical=ClassicalRegister(bits,"readout")
 qc=QuantumCircuit(phase,work,scratch,classical,name="a87_recycled_qpe_boxed")
 qc.x(work[0]);cache={};schedule=[]
 for j in range(bits-1,-1,-1):
  power=pow(base,1<<j,n)
  qc.h(phase[0])
  if power!=1:
   if power not in cache:
    source=fused_build(n,power)
    if source.num_qubits!=qc.num_qubits:raise AssertionError("Width mismatch")
    cache[power]=source.to_gate(label="a84_"+str(power))
   qc.append(cache[power],list(phase)+list(work)+list(scratch))
  for t in range(bits-1,j,-1):
   with qc.if_test((classical[bits-1-t],1)):
    qc.p(-2*math.pi/(1<<(t-j+1)),phase[0])
  qc.h(phase[0]);qc.measure(phase[0],classical[bits-1-j])
  if j>0:qc.reset(phase[0])
  schedule.append({"j":j,"power":power,"boxed":power!=1})
 return qc,cache,schedule

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=2491)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=24)
 p.add_argument("--profile",default="results/a86_n2491_fused_power_profile.json")
 p.add_argument("--qpy",default=None)
 p.add_argument("--output",default="results/a87_n2491_a84_boxed.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits 2..2w")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A87_A84_BOXED_24BIT_RECYCLED_QPE","status":"IN_PROGRESS",
    "n":a.n,"base":a.base,"bits":a.bits,"architecture":"a84",
    "native_full_compilation":False,"aer_shots":0,"hardware_shots":0,
    "limitations":["Boxing saves source representation and avoids immediate circuit flattening; it does not reduce logical arithmetic gate count",
                   "A86 sums are isolated arithmetic stages, not complete QPE transpilation"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  start=time.perf_counter();qc,cache,stages=build(a.n,a.base,a.bits)
  ops=qc.count_ops()
  d["source"]={"qubits":qc.num_qubits,"classical_bits":qc.num_clbits,
   "top_level_instructions":len(qc.data),"source_depth":qc.depth(),
   "unique_boxed_powers":len(cache),
   "boxed_definition_operations":sum(len(g.definition.data) for g in cache.values()),
   "dynamic_if_else":int(ops.get("if_else",0)),
   "measurements":int(ops.get("measure",0)),"resets":int(ops.get("reset",0))}
  d["stage_schedule"]=stages
  assert d["source"]["dynamic_if_else"]==a.bits*(a.bits-1)//2
  assert d["source"]["measurements"]==a.bits
  assert d["source"]["resets"]==a.bits-1
  assert qc.num_qubits==2*a.n.bit_length()+6
  profile=Path(a.profile)
  if profile.is_file():
   s=json.loads(profile.read_text())
   if s.get("settings")=={"n":a.n,"base":a.base,"bits":a.bits,"level":1} and s.get("status")=="PASS_ISOLATED_POWER_COST_ONLY":
    d["isolated_stage_cost_only"]={"a76":s["a76_isolated_sum"],
                                    "a84":s["a84_isolated_sum"],
                                    "comparison":s["comparison"]}
   else:d["profile_warning"]="Checkpoint not complete or does not match parameters"
  else:d["profile_warning"]="No A86 checkpoint available"
  if a.qpy:
   destination=Path(a.qpy);destination.parent.mkdir(parents=True,exist_ok=True)
   with destination.open("wb") as f:qpy.dump(qc,f)
   d["qpy_path"]=str(destination)
  d["build_seconds"]=round(time.perf_counter()-start,3)
  d["status"]="PASS_BOXED_DYNAMIC_SOURCE_ONLY";save()
  print("A87 STATUS",d["status"],"qubits",qc.num_qubits,
        "unique_powers",len(cache),"top_level_ops",len(qc.data),
        "definition_ops",d["source"]["boxed_definition_operations"],
        "build_seconds",d["build_seconds"],flush=True)
  if "isolated_stage_cost_only" in d:
   print("A87 ISOLATED_ONLY",d["isolated_stage_cost_only"]["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:];save();raise

if __name__=="__main__":main()
