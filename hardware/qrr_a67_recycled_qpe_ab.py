#!/usr/bin/env python3
"""A67: small-modulus recycled one-phase-qubit QPE A44/A64 AB integration.

Constructs real semiclassical QPE from either actual reversible modular
multiplier. No simulated/oracle phases. --run-aer is opt-in.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,transpile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
import qrr_a44_generic_modular_multiplier as a44
import qrr_a64_binary_modular_multiplier as a64

def build(n,base,bits,architecture):
 w=n.bit_length()
 phase=QuantumRegister(1,"phase")
 work=QuantumRegister(w,"work")
 scratch=QuantumRegister(w-2 if architecture=="a44" else w+6,"scratch")
 readout=ClassicalRegister(bits,"readout")
 qc=QuantumCircuit(phase,work,scratch,readout)
 qc.x(work[0])
 stages=[]
 for j in range(bits-1,-1,-1):
  power=pow(base,1<<j,n)
  qc.h(phase[0])
  if power!=1:
   stage=a44.build(n,power)[0] if architecture=="a44" else a64.build(n,power)
   assert stage.num_qubits==1+w+len(scratch),(stage.num_qubits,1+w+len(scratch))
   qc.compose(stage,qubits=list(phase)+list(work)+list(scratch),inplace=True)
  for t in range(bits-1,j,-1):
   with qc.if_test((readout[bits-1-t],1)):
    qc.p(-2*math.pi/(1<<(t-j+1)),phase[0])
  qc.h(phase[0])
  qc.measure(phase[0],readout[bits-1-j])
  if j>0:qc.reset(phase[0])
  stages.append({"j":j,"power":power})
 return qc,stages

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15)
 p.add_argument("--base",type=int,default=2)
 p.add_argument("--bits",type=int,default=8)
 p.add_argument("--architectures",nargs="+",choices=["a44","a64"],default=["a44","a64"])
 p.add_argument("--compile",action="store_true")
 p.add_argument("--run-aer",action="store_true")
 p.add_argument("--shots",type=int,default=2)
 p.add_argument("--threads",type=int,default=2)
 p.add_argument("--method",choices=["statevector","matrix_product_state"],default="matrix_product_state")
 p.add_argument("--max-memory-mb",type=int,default=12000)
 p.add_argument("--output",default="results/a67_recycled_qpe_ab.json")
 a=p.parse_args()
 if not (a.n>=9 and a.n%2 and math.gcd(a.base,a.n)==1):p.error("odd n>=9 and coprime base required")
 if a.bits<2 or a.bits>2*a.n.bit_length():p.error("bits must be 2..2*bit_length(n)")
 if a.run_aer and not a.compile:p.error("--run-aer requires --compile")
 if a.n>35 and a.run_aer:p.error("Aer runs limited to n<=35 in this early integration")
 if a.shots<1 or a.shots>8:p.error("1..8 shots")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A67_RECYCLED_QPE_A44_A64_AB","status":"IN_PROGRESS",
  "n":a.n,"base":a.base,"bits":a.bits,"oracle_used":False,"rows":[]}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 try:
  for architecture in a.architectures:
   start=time.perf_counter()
   qc,stages=build(a.n,a.base,a.bits,architecture)
   row={"architecture":architecture,"qubits":qc.num_qubits,"source_counts":dict(qc.count_ops()),
        "source_depth":qc.depth(),"stages":stages,"measured":False,
        "build_seconds":round(time.perf_counter()-start,3)}
   report["rows"].append(row);save()
   print("A67 SOURCE",architecture,"qubits",qc.num_qubits,"ops",sum(qc.count_ops().values()),"depth",qc.depth(),flush=True)
   if a.compile:
    from qiskit_aer import AerSimulator
    sim=AerSimulator(method=a.method,max_parallel_threads=a.threads,max_memory_mb=a.max_memory_mb)
    compiled=transpile(qc,sim,optimization_level=0,seed_transpiler=67)
    row["compiled"]={"qubits":compiled.num_qubits,"counts":dict(compiled.count_ops()),"depth":compiled.depth()}
    save()
    print("A67 COMPILED",architecture,"cx",compiled.count_ops().get("cx",0),"depth",compiled.depth(),flush=True)
    if a.run_aer:
     result=sim.run(compiled,shots=a.shots,memory=True,seed_simulator=67).result()
     if not result.success:raise RuntimeError(result.status)
     row["measured"]=True;row["readouts"]=[int(str(v).replace(" ",""),2) for v in result.get_memory(compiled)]
     save();print("A67 MEASURED",architecture,row["readouts"],flush=True)
  report["status"]="PASS_AER_READOUTS" if a.run_aer else ("PASS_COMPILED_NOT_SIMULATED" if a.compile else "PASS_SOURCE_BUILD_ONLY")
  save();print("A67 STATUS",report["status"],"SAVED",out,flush=True)
 except Exception:
  report["status"]="FAIL";report["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
