#!/usr/bin/env python3
"""A85: full recycled semiclassical QPE A76 vs A84.

Same phase register, feedforward, modular powers and seeds for both
architectures. Native CX and depth at common optimization level.
Optional Aer shots allowed for small moduli; large N compiled only.
No factor/order oracle used. Keep hardware claims separate from Aer.
"""
import argparse,json,math,sys,time,traceback
from fractions import Fraction
from pathlib import Path
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a76_reduced_active_flag import build as a76
from qrr_a84_fused_carry_multiplier import build as a84

def build(n,base,bits,architecture):
 w=n.bit_length()
 phase=QuantumRegister(1,"phase")
 work=QuantumRegister(w,"work")
 scratch=QuantumRegister(w+5,"scratch")
 readout=ClassicalRegister(bits,"readout")
 qc=QuantumCircuit(phase,work,scratch,readout)
 qc.x(work[0])
 powers=[]
 builder=a76 if architecture=="a76" else a84
 cache={}
 for j in range(bits-1,-1,-1):
  power=pow(base,1<<j,n);powers.append(power)
  qc.h(phase[0])
  if power!=1:
   if power not in cache:cache[power]=builder(n,power)
   qc.compose(cache[power],qubits=list(phase)+list(work)+list(scratch),inplace=True)
  for t in range(bits-1,j,-1):
   with qc.if_test((readout[bits-1-t],1)):
    qc.p(-2*math.pi/(1<<(t-j+1)),phase[0])
  qc.h(phase[0]);qc.measure(phase[0],readout[bits-1-j])
  if j>0:qc.reset(phase[0])
 return qc,powers

def recover(n,base,bits,freq):
 if not freq:return None
 denom=Fraction(freq,1<<bits).limit_denominator(n).denominator
 for multiple in range(1,5):
  order=denom*multiple
  if order%2 or pow(base,order,n)!=1:continue
  z=pow(base,order//2,n)
  if z in (1,n-1):continue
  x,y=math.gcd(z-1,n),math.gcd(z+1,n)
  if 1<x<n and 1<y<n and x*y==n:return sorted((x,y))
 return None

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15)
 p.add_argument("--base",type=int,default=2)
 p.add_argument("--bits",type=int,default=8)
 p.add_argument("--architectures",nargs="+",choices=["a76","a84"],default=["a76","a84"])
 p.add_argument("--optimization-level",type=int,choices=(0,1),default=1)
 p.add_argument("--shots",type=int,default=0,help="0 for native compilation only")
 p.add_argument("--seed",type=int,default=8501)
 p.add_argument("--threads",type=int,default=2)
 p.add_argument("--max-memory-mb",type=int,default=8000)
 p.add_argument("--output",default="results/a85_full_qpe_ab.json")
 a=p.parse_args()
 if a.n<9 or a.n%2!=1 or math.gcd(a.n,a.base)!=1:p.error("odd n>=9 and coprime base required")
 if not 2<=a.bits<=2*a.n.bit_length():p.error("bits out of range")
 if not 0<=a.shots<=64:p.error("shots out of range")
 if a.shots and a.n>35:p.error("gate-level Aer sampling is restricted to n<=35")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A85_FULL_QPE_A76_A84_ARITHMETIC_AB","status":"IN_PROGRESS",
    "n":a.n,"base":a.base,"bits":a.bits,"seed":a.seed,"shots_per_architecture":a.shots,
    "optimization_level":a.optimization_level,"rows":[],
    "limitations":["Native CX and depth are ideal un-routed basis-gate costs",
                   "No QPU jobs, no fault tolerance, no physical noise",
                   "Matched seeds alone do not prove equal phase probability distributions"]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  for architecture in a.architectures:
   t=time.perf_counter();qc,powers=build(a.n,a.base,a.bits,architecture)
   sim=AerSimulator(method="matrix_product_state",max_parallel_threads=a.threads,
                    max_memory_mb=a.max_memory_mb)
   compiled=transpile(qc,sim,optimization_level=a.optimization_level,seed_transpiler=a.seed)
   row={"architecture":architecture,"qubits":compiled.num_qubits,
        "cx":int(compiled.count_ops().get("cx",0)),"depth":compiled.depth(),
        "distinct_nonidentity_powers":len(set(powers)-{1}),
        "compiled_seconds":round(time.perf_counter()-t,3),
        "shots":0,"factor_successes":None}
   d["rows"].append(row);save()
   print("A85 COMPILED",architecture,"qubits",row["qubits"],
         "CX",row["cx"],"depth",row["depth"],flush=True)
   if a.shots:
    t=time.perf_counter()
    result=sim.run(compiled,shots=a.shots,memory=True,seed_simulator=a.seed).result()
    if not result.success:raise RuntimeError(str(result.status))
    freqs=[int(str(v).replace(" ",""),2) for v in result.get_memory(compiled)]
    recovered=[recover(a.n,a.base,a.bits,f) for f in freqs]
    row["frequencies"]=freqs
    row["factor_successes"]=sum(v is not None for v in recovered)
    row["shots"]=len(freqs);row["aer_seconds"]=round(time.perf_counter()-t,3)
    save()
    print("A85 SAMPLED",architecture,"factor_recovery",row["factor_successes"],
          "/",len(freqs),"frequencies",freqs,flush=True)
  if len(d["rows"])==2 and {v["architecture"] for v in d["rows"]}=={"a76","a84"}:
   baseline=next(v for v in d["rows"] if v["architecture"]=="a76")
   candidate=next(v for v in d["rows"] if v["architecture"]=="a84")
   d["comparison"]={"cx_reduction_pct":round(100*(baseline["cx"]-candidate["cx"])/baseline["cx"],4),
                    "depth_reduction_pct":round(100*(baseline["depth"]-candidate["depth"])/baseline["depth"],4),
                    "delta_cx":candidate["cx"]-baseline["cx"],
                    "delta_depth":candidate["depth"]-baseline["depth"]}
   print("A85 COMPARISON",d["comparison"],flush=True)
  d["status"]="PASS_COMPILED_AND_AER_SAMPLED" if a.shots else "PASS_COMPILED_NOT_SIMULATED"
  save();print("A85 STATUS",d["status"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:];save();raise
if __name__=="__main__":main()
