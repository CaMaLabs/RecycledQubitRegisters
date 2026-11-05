#!/usr/bin/env python3
"""A78 synthetic-noise recycled-QPE A44/A64/A76 comparison.

Entire circuit contains actual modular gates, dynamic measurement/reset and
semiclassical feedforward. This is a *synthetic* noise study, not device-calibrated
or fault tolerant. Factor recoveries use only measured frequencies.
"""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from fractions import Fraction
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel,depolarizing_error,thermal_relaxation_error
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a67_recycled_qpe_ab import build as build_baseline
from qrr_a76_reduced_active_flag import build as build_a76

def build(n,base,bits,arch):
 if arch!="a76":return build_baseline(n,base,bits,arch)[0]
 width=n.bit_length()
 phase=QuantumRegister(1,"phase");work=QuantumRegister(width,"work")
 scratch=QuantumRegister(width+5,"scratch");readout=ClassicalRegister(bits,"readout")
 qc=QuantumCircuit(phase,work,scratch,readout)
 qc.x(work[0])
 for j in range(bits-1,-1,-1):
  power=pow(base,1<<j,n);qc.h(phase[0])
  if power!=1:
   gate=build_a76(n,power)
   qc.compose(gate,qubits=list(phase)+list(work)+list(scratch),inplace=True)
  for t in range(bits-1,j,-1):
   with qc.if_test((readout[bits-1-t],1)):
    qc.p(-2*math.pi/(1<<(t-j+1)),phase[0])
  qc.h(phase[0]);qc.measure(phase[0],readout[bits-1-j])
  if j>0:qc.reset(phase[0])
 return qc

def factors(n,base,bits,frequency):
 if frequency==0:return None
 r=Fraction(frequency,1<<bits).limit_denominator(n).denominator
 if r%2 or pow(base,r,n)!=1:return None
 x=pow(base,r//2,n)
 if x in (1,n-1):return None
 p,q=math.gcd(x-1,n),math.gcd(x+1,n)
 return sorted((p,q)) if p>1 and q>1 and p*q==n else None

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15);p.add_argument("--base",type=int,default=2)
 p.add_argument("--bits",type=int,default=8);p.add_argument("--shots",type=int,default=32)
 p.add_argument("--gate-errors",type=float,nargs="+",default=[0,0.0001,0.001])
 p.add_argument("--architectures",nargs="+",choices=["a44","a64","a76"],default=["a44","a64","a76"])
 p.add_argument("--max-memory-mb",type=int,default=10000)
 p.add_argument("--output",default="results/a78_noise_ab.json")
 a=p.parse_args()
 if a.n<9 or a.n>35 or not a.n%2 or math.gcd(a.base,a.n)!=1:p.error("odd N 9..35 and coprime base required")
 if a.bits<2 or a.bits>2*a.n.bit_length():p.error("phase bits 2..2w")
 if a.shots<1 or a.shots>1000:p.error("shots 1..1000")
 if any(x<0 or x>=0.1 for x in a.gate_errors):p.error("depolarizing probability must be in [0,0.1)")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A78_SYNTHETIC_GATE_NOISE_RECYCLED_QPE","status":"IN_PROGRESS",
    "n":a.n,"base":a.base,"bits":a.bits,"shots":a.shots,"rows":[],
    "noise_assumptions":"Independent 1q depolarizing with p1=p2/10, 2q depolarizing p2, ideal measurement/reset; no idle decoherence or crosstalk; NOT device calibrated.",
    "ancilla_syndrome_check":"NOT_MEASURED: temporary arithmetic ancillas are uncomputed but not read out as syndromes",
    "physical_noise_advantage":"NOT_ESTABLISHED"}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for arch in a.architectures:
   circuit=build(a.n,a.base,a.bits,arch)
   ideal=AerSimulator(method="matrix_product_state",max_parallel_threads=2,
                      max_memory_mb=a.max_memory_mb)
   compiled=transpile(circuit,ideal,optimization_level=1,seed_transpiler=78)
   row={"architecture":arch,"qubits":compiled.num_qubits,
    "cx":compiled.count_ops().get("cx",0),"depth":compiled.depth(),"runs":[]}
   d["rows"].append(row);save()
   print("A78 COMPILED",arch,"qubits",row["qubits"],"cx",row["cx"],"depth",row["depth"],flush=True)
   for prob in a.gate_errors:
    noise=None
    if prob:
     noise=NoiseModel()
     noise.add_all_qubit_quantum_error(depolarizing_error(prob,2),["cx"])
     one=depolarizing_error(prob/10,1)
     for name in ("u","u1","u2","u3","h","x","sx","rz","p"):
      noise.add_all_qubit_quantum_error(one,[name])
    sim=AerSimulator(method="matrix_product_state",noise_model=noise,
                     max_parallel_threads=2,max_memory_mb=a.max_memory_mb)
    started=time.perf_counter()
    result=sim.run(compiled,shots=a.shots,memory=True,seed_simulator=78).result()
    if not result.success:raise RuntimeError(result.status)
    frequencies=[int(str(z).replace(" ",""),2) for z in result.get_memory(compiled)]
    successes=[factors(a.n,a.base,a.bits,f) for f in frequencies]
    r={"p2":prob,"p1":prob/10,"shots":a.shots,
       "factor_successes":sum(x is not None for x in successes),
       "factor_success_fraction":sum(x is not None for x in successes)/a.shots,
       "frequency_histogram":{str(v):frequencies.count(v) for v in sorted(set(frequencies))},
       "seconds":round(time.perf_counter()-started,3)}
    row["runs"].append(r);save()
    print("A78",arch,"p2",prob,"verified",r["factor_successes"],"/",a.shots,
          "seconds",r["seconds"],flush=True)
  d["status"]="PASS_SYNTHETIC_NOISE_BENCHMARK";save()
  print("A78 STATUS",d["status"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:];save();raise
if __name__=="__main__":main()
