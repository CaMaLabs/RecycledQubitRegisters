#!/usr/bin/env python3
"""A70: actual small-N hybrid recycled-QPE Aer and classical factor verification.
Mixed powers are explicitly selected; no oracle frequencies or claimed speedup.
"""
import argparse,json,math,sys,time,traceback
from fractions import Fraction
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a69_hybrid_recycled_qpe import build as hybrid_build
from qrr_a67_recycled_qpe_ab import build as baseline_build

def factors_from_frequency(n,a,bits,freq):
 if not freq:return None
 # Exact continued fraction denominator; multiple-of-order recovery remains limited.
 r=Fraction(freq,1<<bits).limit_denominator(n).denominator
 if r%2 or pow(a,r,n)!=1:return None
 t=pow(a,r//2,n)
 if t in (1,n-1):return None
 p,q=math.gcd(t-1,n),math.gcd(t+1,n)
 return sorted((p,q)) if p>1 and q>1 and p*q==n else None

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15);p.add_argument("--base",type=int,default=2)
 p.add_argument("--bits",type=int,default=8);p.add_argument("--shots",type=int,default=8)
 p.add_argument("--threads",type=int,default=2);p.add_argument("--max-memory-mb",type=int,default=12000)
 p.add_argument("--output",default="results/a70_n15_hybrid_aer_ab.json")
 a=p.parse_args()
 if a.n>35 or a.n<9 or a.n%2==0 or math.gcd(a.n,a.base)!=1:p.error("odd 9<=n<=35, coprime base")
 if not 2<=a.bits<=2*a.n.bit_length() or not 1<=a.shots<=16:p.error("bits/shots limits")
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A70_ACTUAL_HYBRID_RECYCLED_QPE_AER","status":"IN_PROGRESS","n":a.n,"base":a.base,"bits":a.bits,"shots":a.shots,
    "known_order_oracle":False,"architectures":[]}
 def save():path.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  distinct=[pow(a.base,1<<j,a.n) for j in range(a.bits)]
  nontrivial=list(dict.fromkeys(x for x in distinct if x!=1))
  if len(nontrivial)<2:p.error("Need >=2 distinct nonidentity modular powers for genuine mixed architecture")
  # Force A64 for the first unique power, A44 for the rest.
  winners={v:("a64" if i==0 else "a44") for i,v in enumerate(nontrivial)}
  for name in ("a44","a64","hybrid"):
   start=time.perf_counter()
   qc,stages=(hybrid_build(a.n,a.base,a.bits,winners) if name=="hybrid"
              else baseline_build(a.n,a.base,a.bits,name))
   sim=AerSimulator(method="matrix_product_state",max_parallel_threads=a.threads,max_memory_mb=a.max_memory_mb)
   compiled=transpile(qc,sim,optimization_level=0,seed_transpiler=70)
   row={"architecture":name,"qubits":qc.num_qubits,"cx":compiled.count_ops().get("cx",0),
        "depth":compiled.depth(),"powers":[{"power":v,"selected":winners[v]} for v in nontrivial] if name=="hybrid" else None}
   d["architectures"].append(row);save()
   print("A70 COMPILED",name,"qubits",row["qubits"],"cx",row["cx"],"depth",row["depth"],flush=True)
   res=sim.run(compiled,shots=a.shots,memory=True,seed_simulator=70).result()
   if not res.success:raise RuntimeError(str(res.status))
   row["frequencies"]=[int(str(v).replace(" ",""),2) for v in res.get_memory(compiled)]
   row["verified_factors"]=[factors_from_frequency(a.n,a.base,a.bits,v) for v in row["frequencies"]]
   row["verified_factor_count"]=sum(x is not None for x in row["verified_factors"])
   row["seconds"]=round(time.perf_counter()-start,3);save()
   print("A70 MEASURED",name,row["frequencies"],"FACTOR_RECOVERY",row["verified_factor_count"],"/",a.shots,flush=True)
  d["status"]="PASS_ACTUAL_HYBRID_AER_POSTPROCESSED";save();print("A70 STATUS",d["status"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
