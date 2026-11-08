#!/usr/bin/env python3
"""A69 real hybrid recycled QPE compiled resource cost; no simulated shots."""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,transpile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a44_generic_modular_multiplier as a44
import qrr_a64_binary_modular_multiplier as a64

def build(n,base,bits,winners):
 w=n.bit_length()
 phase=QuantumRegister(1,"phase")
 work=QuantumRegister(w,"work")
 scratch=QuantumRegister(w+6,"scratch")
 readout=ClassicalRegister(bits,"readout")
 qc=QuantumCircuit(phase,work,scratch,readout)
 qc.x(work[0]);stages=[]
 for j in range(bits-1,-1,-1):
  power=pow(base,1<<j,n)
  qc.h(phase[0])
  arch="identity" if power==1 else winners.get(power)
  if arch=="a44":
   sub=a44.build(n,power)[0]
   qc.compose(sub,qubits=list(phase)+list(work)+list(scratch[:w-2]),inplace=True)
  elif arch=="a64":
   sub=a64.build(n,power)
   qc.compose(sub,qubits=list(phase)+list(work)+list(scratch),inplace=True)
  elif arch!="identity":raise ValueError(f"No stage selection for power={power}")
  for t in range(bits-1,j,-1):
   with qc.if_test((readout[bits-1-t],1)):
    qc.p(-2*math.pi/(1<<(t-j+1)),phase[0])
  qc.h(phase[0]);qc.measure(phase[0],readout[bits-1-j])
  if j>0:qc.reset(phase[0])
  stages.append({"j":j,"power":power,"architecture":arch})
 return qc,stages

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=221);p.add_argument("--base",type=int,default=8);p.add_argument("--bits",type=int,default=16)
 p.add_argument("--screen",default="results/a68_n221_stage_costs.json")
 p.add_argument("--objective",choices=["lower_cx","lower_depth"],default="lower_cx")
 p.add_argument("--output",default="results/a69_n221_hybrid_compilation.json")
 a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A69_REAL_HYBRID_RECYCLED_QPE","status":"IN_PROGRESS","n":a.n,"base":a.base,"bits":a.bits,
 "not_a_quantum_simulation":True}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  s=json.loads(Path(a.screen).read_text())
  if (s.get("n"),s.get("base"),s.get("bits"),s.get("status")) != (a.n,a.base,a.bits,"PASS_PER_STAGE_NATIVE_COSTS_NOT_FULL_HYBRID_COMPILED"):
   raise ValueError("Stage screen does not match run inputs or was not validated")
  winners={int(row["power"]):row[a.objective] for row in s["rows"]}
  start=time.perf_counter();qc,stages=build(a.n,a.base,a.bits,winners)
  d["stages"]=stages;d["source"]={"qubits":qc.num_qubits,"depth":qc.depth(),"counts":dict(qc.count_ops())};save()
  print("A69 SOURCE",qc.num_qubits,"qubits",sum(qc.count_ops().values()),"ops",flush=True)
  from qiskit_aer import AerSimulator
  sim=AerSimulator(method="matrix_product_state")
  compiled=transpile(qc,sim,optimization_level=0,seed_transpiler=69)
  d["compiled"]={"qubits":compiled.num_qubits,"cx":compiled.count_ops().get("cx",0),
     "depth":compiled.depth(),"counts":dict(compiled.count_ops()),
     "seconds":round(time.perf_counter()-start,3)}
  d["status"]="PASS_HYBRID_COMPILED_NOT_SIMULATED";save()
  print("A69",d["status"],"CX",d["compiled"]["cx"],"depth",d["compiled"]["depth"],"qubits",compiled.num_qubits,flush=True)
 except Exception:
  d["status"]="ERROR";d["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
