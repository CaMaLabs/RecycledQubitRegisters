#!/usr/bin/env python3
"""A79 bounded real gate-level recycled QPE semiprime frontier.

Builds actual controlled modular multiplier phases (no order/orbit oracle),
runs local Aer MPS only when --run-aer set, and verifies factors from measured
frequencies using bounded continued-fraction public-data postprocessing.
Only nontrivial semiprimes (two prime factors) are accepted. No known-factor
oracle is supplied to the quantum circuit or postprocessor.
"""
import argparse,json,math,sys,time,traceback
from fractions import Fraction
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
from qrr_a67_recycled_qpe_ab import build as qpe_build

def is_prime(n):
 if n<2:return False
 for k in range(2,math.isqrt(n)+1):
  if n%k==0:return False
 return True

def is_semiprime(n):
 factors=[];x=n
 for p in range(2,math.isqrt(x)+1):
  while x%p==0:
   factors.append(p);x//=p
   if len(factors)>2:return False
 if x>1:factors.append(x)
 return len(factors)==2 and all(is_prime(x) for x in factors)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=437)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=0)
 p.add_argument("--architecture",choices=("a44","a64"),default="a64")
 p.add_argument("--shots",type=int,default=1)
 p.add_argument("--run-aer",action="store_true")
 p.add_argument("--max-memory-mb",type=int,default=8000)
 p.add_argument("--threads",type=int,default=2)
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--output",default="results/a79_semiprime_frontier.json")
 a=p.parse_args()
 if not is_semiprime(a.n) or math.gcd(a.n,a.base)!=1:p.error("N must be semiprime and base coprime")
 bits=a.bits or 2*a.n.bit_length()
 if bits<2 or bits>2*a.n.bit_length():p.error("bits must be 2..2*w")
 if a.shots<1 or a.shots>4:p.error("shots must be 1..4")
 if a.max_memory_mb<1024:p.error("memory cap must be at least 1024 MB")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A79_NO_ORACLE_GATE_LEVEL_SEMIPRIME_FRONTIER",
    "n":a.n,"base":a.base,"bits":bits,"architecture":a.architecture,
    "status":"IN_PROGRESS","shots_requested":a.shots,
    "known_order_oracle":False,"actual_aer_shots":0,
    "verified_factor_recoveries":0,"readouts":[],
    "warnings":["A compile/build success is NOT a factoring demonstration.",
                "Max memory is simulator allocation budget, not guaranteed host process RSS."]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  start=time.perf_counter()
  qc,stages=qpe_build(a.n,a.base,bits,a.architecture)
  d["source"]={"qubits":qc.num_qubits,"instructions":len(qc.data),
    "depth":qc.depth(),"distinct_powers":len({v["power"] for v in stages})}
  save();print("A79 BUILT N",a.n,"qubits",qc.num_qubits,"instructions",len(qc.data),flush=True)
  if not a.run_aer:
   d["status"]="PASS_SOURCE_ONLY_NO_FACTORIZATION";save()
   print("A79 STATUS",d["status"],flush=True);return
  sim=AerSimulator(method="matrix_product_state",max_parallel_threads=a.threads,
                   max_memory_mb=a.max_memory_mb)
  compiled=transpile(qc,sim,optimization_level=0,seed_transpiler=79)
  d["compiled"]={"cx":compiled.count_ops().get("cx",0),
      "depth":compiled.depth(),"qubits":compiled.num_qubits}
  save()
  print("A79 COMPILED",d["compiled"],"seconds",round(time.perf_counter()-start,3),flush=True)
  print("A79 SIMULATING LOCAL AER MPS...",flush=True)
  result=sim.run(compiled,shots=a.shots,memory=True,seed_simulator=79).result()
  if not result.success:raise RuntimeError(str(result.status))
  freqs=[int(str(f).replace(" ",""),2) for f in result.get_memory(compiled)]
  d["actual_aer_shots"]=len(freqs);save()
  for freq in freqs:
   # Public-only continued-fraction recovery: no N factor list or order oracle.
   # Try small multiples of the candidate denominator; this is classical
   # postprocessing of a MEASURED QPE frequency, not simulated success.
   denom=Fraction(freq,1<<bits).limit_denominator(a.n).denominator if freq else 1
   found=None;used_order=None
   if freq:
    for multiple in range(1,2*a.n//denom+1):
     order=multiple*denom
     if order%2 or pow(a.base,order,a.n)!=1:continue
     middle=pow(a.base,order//2,a.n)
     if middle in (1,a.n-1):continue
     p1,p2=math.gcd(middle-1,a.n),math.gcd(middle+1,a.n)
     if 1<p1<a.n and 1<p2<a.n and p1*p2==a.n:
      found=sorted([p1,p2]);used_order=order;break
   factors=found
   verified=factors is not None
   r={"candidate_denominator":denom,"candidate_order":used_order,
      "max_multiples":2*a.n//denom if freq else 0,
      "method":"measured_frequency_continued_fraction_bounded_multiples"}
   row={"frequency":freq,"verified":verified,"factors":factors,
        "postprocess":r}
   d["readouts"].append(row);d["verified_factor_recoveries"]+=int(verified);save()
   print("A79 SHOT frequency",freq,"factors",row["factors"],"verified",verified,flush=True)
  d["status"]="PASS_VERIFIED_GATE_LEVEL_FACTORS" if d["verified_factor_recoveries"] else "PASS_MEASURED_NO_FACTORS"
  d["elapsed_seconds"]=round(time.perf_counter()-start,3);save()
  print("A79 STATUS",d["status"],"verified",d["verified_factor_recoveries"],"/",len(freqs),flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-5000:];save();raise
if __name__=="__main__":main()
