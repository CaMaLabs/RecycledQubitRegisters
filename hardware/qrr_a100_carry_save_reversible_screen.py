#!/usr/bin/env python3
"""A100: exact clean reversible 3:2 carry-save accumulation prototype.

Compare two COMPLETE reversible functions that map
 |a,b,c,0,clean> -> |a,b,c,(a+b+c) mod 2**w,clean>.
Baseline: three sequential in-place controlled ripple additions into output.
Candidate: bitwise 3:2 compression, TWO ripple additions (sum and shifted
carry), and full compressor uncomputation. Input registers are preserved.

This is deliberately NOT modular multiplication mod N and NOT a Shor QPE
operation. Extra clean ancillas are counted. No speedup is claimed unless
the fully cleaned implementation wins on native gate metrics.

The reversible circuits use X, CX, CCX and MCX with no measurements.
Source-basis exhaustive/random tests inspect the whole output state,
including scratch cleanup; compilation uses matched Qiskit settings.
"""
import argparse,json,random,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a61_binary_modular_adder import flip_pattern
from qrr_a65_reversible_basis_exhaustive import instruction_stream,evaluate

def add_shifted(q,source,target,shift=0):
 """Reversible target += (source << shift) mod 2**w, source unchanged.
 Increment by each control bit, high-to-low target updates per bit.
 """
 w=len(target)
 for j,s in enumerate(source):
  pos=j+shift
  if pos>=w:break
  for i in range(w-1,pos,-1):
   controls=[s]+target[pos:i]
   flip_pattern(q,controls,target[i],(1<<len(controls))-1)
  q.cx(s,target[pos])

def regs(q,w):
 a=list(q.qubits[:w]);b=list(q.qubits[w:2*w])
 c=list(q.qubits[2*w:3*w]);out=list(q.qubits[3*w:4*w])
 return a,b,c,out

def baseline(width):
 q=QuantumCircuit(4*width,name="a100_three_ripple")
 a,b,c,out=regs(q,width)
 for inp in (a,b,c):add_shifted(q,inp,out)
 return q

def candidate(width):
 # Extra w clean sum bits, w-1 carry bits: 6w-1 total.
 q=QuantumCircuit(6*width-1,name="a100_csa_clean")
 a,b,c,out=regs(q,width)
 sums=list(q.qubits[4*width:5*width])
 carries=list(q.qubits[5*width:])
 for j in range(width):
  q.cx(a[j],sums[j])
  q.cx(b[j],sums[j]) # t=a XOR b
  if j<width-1:
   q.ccx(a[j],b[j],carries[j])
   q.ccx(c[j],sums[j],carries[j])
  q.cx(c[j],sums[j]) # sum=a XOR b XOR c
 add_shifted(q,sums,out)
 add_shifted(q,carries,out,shift=1)
 # Uncompute all compressor outputs with inputs untouched.
 for j in range(width-1,-1,-1):
  q.cx(c[j],sums[j])
  if j<width-1:
   q.ccx(c[j],sums[j],carries[j])
   q.ccx(a[j],b[j],carries[j])
  q.cx(b[j],sums[j])
  q.cx(a[j],sums[j])
 return q

def sample_triples(width,probes,seed,exhaustive_width):
 limit=1<<width
 if width<=exhaustive_width:
  for a in range(limit):
   for b in range(limit):
    for c in range(limit):yield a,b,c
  return
 values=[0,1,limit-1,limit//2,(limit//2)-1]
 unique=[x for x in dict.fromkeys(values) if 0<=x<limit]
 seen=set()
 for a in unique:
  for b in unique:
   for c in unique:
    tup=(a,b,c)
    if tup not in seen:
     seen.add(tup);yield tup
 rng=random.Random(seed+width)
 for _ in range(probes):
  tup=(rng.randrange(limit),rng.randrange(limit),rng.randrange(limit))
  if tup not in seen:
   seen.add(tup);yield tup

def audit(q,width,triples):
 stream=instruction_stream(q)
 count=0
 for a,b,c in triples:
  inp=a|(b<<width)|(c<<(2*width))
  got=evaluate(stream,inp)
  want=inp|(((a+b+c)% (1<<width))<<(3*width))
  if got!=want:
   raise AssertionError(f"width={width} a={a} b={b} c={c} got={got} want={want}")
  count+=1
 return count

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--width",type=int,default=4)
 p.add_argument("--probes",type=int,default=128)
 p.add_argument("--exhaustive-up-to",type=int,default=4)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=10001)
 p.add_argument("--output",default="results/a100_carry_save_prototype.json")
 a=p.parse_args()
 if not 2<=a.width<=24:p.error("2<=width<=24")
 if not 0<=a.probes<=100000:p.error("0<=probes<=100000")
 if not 0<=a.exhaustive_up_to<=5:p.error("0<=exhaustive-up-to<=5")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A100_CLEAN_REVERSIBLE_3_TO_2_CARRY_SAVE_SCREEN",
    "status":"IN_PROGRESS","width":a.width,"seed":a.seed,
    "optimization_level":a.level,"architectures":{},
    "limitations":["This computes sum mod 2^w, NOT multiplication or modular reduction mod N",
     "Carry-save candidate uses 2w-1 MORE qubits; full cleanup included",
     "Source-gate correctness checks computational-basis mappings; does not quantify hardware phase noise",
     "Native unrestricted u/cx costs cannot be taken as real backend costs"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  samples=list(sample_triples(a.width,a.probes,a.seed,a.exhaustive_up_to))
  for name,builder in (("baseline",baseline),("carry_save",candidate)):
   t=time.perf_counter()
   qc=builder(a.width)
   checked=audit(qc,a.width,samples)
   native=transpile(qc,basis_gates=["u","cx"],
       optimization_level=a.level,seed_transpiler=a.seed)
   row={"qubits":qc.num_qubits,
     "extra_qubits_over_baseline":qc.num_qubits-4*a.width,
     "source_ops":len(qc.data),
     "cx":int(native.count_ops().get("cx",0)),
     "depth":int(native.depth()),"basis_cases":checked,
     "seconds":round(time.perf_counter()-t,3)}
   d["architectures"][name]=row;save()
   print("A100",name,row,flush=True)
  x=d["architectures"]["baseline"];y=d["architectures"]["carry_save"]
  d["comparison"]={"delta_cx":y["cx"]-x["cx"],
    "delta_depth":y["depth"]-x["depth"],
    "delta_qubits":y["qubits"]-x["qubits"],
    "cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
    "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4)}
  d["status"]="PASS_CLEAN_REVERSIBLE_BASIS_AND_NATIVE_SCREEN"
  save();print("A100 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
