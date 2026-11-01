#!/usr/bin/env python3
"""A50: N437, 18-bit true recycled phase circuit with A44 modular gate source.

Build and record a real Qiskit circuit (one reused phase qubit, nine work,
seven clean ancillas), optionally compile and optionally execute Aer
measured shots. A budget guard defaults to build-only; no oracle frequencies.
Postprocessing is the pinned Quaspy adapter used by A49.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,transpile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
import qrr_a44_generic_modular_multiplier as modular
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def build(n,base,bits):
 width=n.bit_length()
 phase=QuantumRegister(1,"recycled_phase")
 work=QuantumRegister(width,"work")
 scratch=QuantumRegister(width-2,"clean_ancillas")
 classical=ClassicalRegister(bits,"readout")
 qc=QuantumCircuit(phase,work,scratch,classical)
 qc.x(work[0])
 stages=[]
 for j in range(bits-1,-1,-1):
  power=pow(base,1<<j,n)
  qc.h(phase[0])
  if power!=1:
   # This is A44's actual reversible gate source, not an order/orbit oracle.
   stage,_=modular.build(n,power)
   assert stage.num_qubits==qc.num_qubits
   qc.compose(stage,qubits=list(phase)+list(work)+list(scratch),inplace=True)
  for t in range(bits-1,j,-1):
   with qc.if_test((classical[bits-1-t],1)):
    qc.p(-2*math.pi/(1<<(t-j+1)),phase[0])
  qc.h(phase[0])
  qc.measure(phase[0],classical[bits-1-j])
  if j>0:qc.reset(phase[0])
  stages.append({"stage_j":j,"public_power":power})
 return qc,stages

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=437)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=18)
 p.add_argument("--compile",action="store_true")
 p.add_argument("--run-aer",action="store_true")
 p.add_argument("--shots",type=int,default=1)
 p.add_argument("--threads",type=int,default=4)
 p.add_argument("--seed",type=int,default=20261031)
 p.add_argument("--aer-method",choices=["matrix_product_state","statevector"],default="matrix_product_state")
 p.add_argument("--max-memory-mb",type=int,default=0)
 p.add_argument("--max-source-operations",type=int,default=300000)
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--output",default="results/a50_n437_recycled_handoff.json")
 a=p.parse_args()
 if a.n<9 or a.n%2==0 or math.gcd(a.n,a.base)!=1:p.error("odd n and coprime base required")
 if not a.n.bit_length()<a.bits<=2*a.n.bit_length():p.error("Quaspy phase bits must be m+1..2m")
 if not 1<=a.shots<=16:p.error("shots must be 1..16")
 if a.run_aer and not a.compile:p.error("--run-aer requires --compile")
 if a.max_memory_mb<0:p.error("memory limit must be nonnegative")
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A50_N437_ACTUAL_RECYCLED_SOURCE_TO_QUASPY","status":"IN_PROGRESS",
 "n":a.n,"base":a.base,"bits":a.bits,"qpu_jobs":0,
 "actual_Aer_measured_readouts":False,"known_order_oracle_used":False,"seed":a.seed,"aer_method":a.aer_method,"max_memory_mb":a.max_memory_mb,"threads":a.threads,"readouts":[]}
 def save():dest.write_text(json.dumps(report,indent=2)+"\n")
 save();t0=time.perf_counter()
 try:
  circuit,stages=build(a.n,a.base,a.bits)
  counts=dict(circuit.count_ops())
  source_ops=sum(counts.values())
  report["source"]={"qubits":circuit.num_qubits,"classical_bits":circuit.num_clbits,
   "counts":counts,"source_depth":circuit.depth(),"source_operations":source_ops,
   "stages":stages,"construction_seconds":round(time.perf_counter()-t0,3)}
  assert counts.get("measure",0)==a.bits and counts.get("reset",0)==a.bits-1
  assert counts.get("if_else",0)==a.bits*(a.bits-1)//2
  report["status"]="PASS_ACTUAL_DYNAMIC_SOURCE_BUILD_NOT_SIMULATED"
  save()
  print("A50 SOURCE",json.dumps({k:v for k,v in report["source"].items() if k!="stages"}),flush=True)
  if source_ops>a.max_source_operations:
   report["status"]="RESOURCE_GATE_STOP_SOURCE_TOO_LARGE"
   save();print("A50 RESOURCE GATE STOP",source_ops,">",a.max_source_operations,flush=True)
   return
  if a.compile:
   from qiskit_aer import AerSimulator
   sim=AerSimulator(method=a.aer_method,max_parallel_threads=a.threads,**({"max_memory_mb":a.max_memory_mb} if a.max_memory_mb else {}))
   start=time.perf_counter()
   print("A50 COMPILING actual dynamic source...",flush=True)
   compiled=transpile(circuit,sim,optimization_level=0,seed_transpiler=a.seed)
   report["compiled"]={"counts":dict(compiled.count_ops()),"depth":compiled.depth(),
    "seconds":round(time.perf_counter()-start,3)}
   report["status"]="PASS_COMPILED_NOT_MEASURED"
   save();print("A50 COMPILED",json.dumps(report["compiled"]),flush=True)
   if a.run_aer:
    start=time.perf_counter()
    print("A50 AER gate-level simulation starting",flush=True)
    result=sim.run(compiled,shots=a.shots,seed_simulator=a.seed,memory=True).result()
    if not result.success:raise RuntimeError(str(result.status))
    memory=result.get_memory(compiled)
    assert len(memory)==a.shots
    report["actual_Aer_measured_readouts"]=True
    report["simulation_seconds"]=round(time.perf_counter()-start,3)
    post.load_upstream(a.upstream)
    for word in memory:
     frequency=int(str(word).replace(" ",""),2)
     recovered=post.recover(a.n,a.base,a.bits,frequency,method="ekera",budget=1000,timeout=2)
     factors=recovered["factors"]
     if factors is not None:assert math.prod(factors)==a.n
     entry={"measured_bitstring":str(word),"frequency":frequency,"ekera":recovered}
     report["readouts"].append(entry);save()
     print("A50 MEASURED",json.dumps(entry),flush=True)
    report["status"]="PASS_ACTUAL_AER_MEASUREMENTS_POSTPROCESSED"
    save()
 except Exception as e:
  report["status"]="FAIL_NOT_VALIDATED";report["error"]=repr(e)
  report["traceback"]=traceback.format_exc()[-3000:];save();raise
 print("A50 STATUS",report["status"],"SAVED",dest,flush=True)

if __name__=="__main__":main()
