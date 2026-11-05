#!/usr/bin/env python3
"""A102: clean reversible 3-input modular-N sum with carry-save A/B.

|a,b,c,0,clean> -> |a,b,c,(a+b+c) mod N,clean>, for all w-bit
a,b,c and w=N.bit_length(). All input high guard bits start zero.

Both implementations form the exact integer sum in a w+2-bit scratch
accumulator, reversibly subtract powers-of-two multiples of N while
remembering quotient flags, COPY the reduced value into a separate
output register, REVERSE modular reduction and then UNCOMPUTE the
original sum circuit. All temporary guards, quotient flags, compressor
bits and accumulator bits must return to zero.

Baseline uses 3 variable ripple adds; candidate uses a clean 3:2
carry-save compressor + 2 ripple adds. Every operation including
modular reduction and cleanup is included in native cost comparison.

Not a modular multiplier, phase estimation or physical hardware run.
"""
import argparse,json,math,random,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a100_carry_save_reversible_screen import baseline as ripple_sum,candidate as csa_sum
from qrr_a61_binary_modular_adder import ge,add_constant
from qrr_a65_reversible_basis_exhaustive import instruction_stream,evaluate

def factors_for(n,w):
 qmax=(3*((1<<w)-1))//n
 if qmax==0:return []
 return [1<<k for k in range(qmax.bit_length()-1,-1,-1)]

def build(n,method="carry_save"):
 if n<3 or n%2!=1:raise ValueError("odd modulus >=3 required")
 w=n.bit_length()
 W=w+2
 if method not in ("baseline","carry_save"):raise ValueError("unknown method")
 source=ripple_sum(W) if method=="baseline" else csa_sum(W)
 factors=factors_for(n,w)
 nsource=source.num_qubits
 qc=QuantumCircuit(nsource+w+len(factors))
 qc.compose(source,qubits=range(nsource),inplace=True)
 accumulator=list(qc.qubits[3*W:4*W])
 output=list(qc.qubits[nsource:nsource+w])
 flags=list(qc.qubits[nsource+w:])
 # Coherent binary quotient extraction, subtract all eligible 2^j*N.
 # For x in [0,3*(2^w-1)], this computes x mod N.
 for factor,flag in zip(factors,flags):
  ge(qc,accumulator,flag,factor*n)
  add_constant(qc,accumulator,-factor*n,flag)
 # Copy residue into output; not measurement, remains reversible.
 for src,dst in zip(accumulator[:w],output):
  qc.cx(src,dst)
 # Restore original accumulator AND clean all quotient flags. Each flag
 # is recomputed against the restored pre-subtraction value of its stage.
 for factor,flag in reversed(list(zip(factors,flags))):
  add_constant(qc,accumulator,factor*n,flag)
  ge(qc,accumulator,flag,factor*n)
 qc.compose(source.inverse(),qubits=range(nsource),inplace=True)
 return qc,{"modulus":n,"input_bits":w,"sum_guard_bits":W,
   "quotient_factors":factors,"logical_qubits":qc.num_qubits,
   "output_register_offset":nsource,
   "baseline_qubit_count":4*W+w+len(factors),
   "extra_candidate_qubits":(2*W-1)}

def triples(w,probes,seed,exhaustive_up_to):
 maxv=1<<w
 if w<=exhaustive_up_to:
  for x in range(maxv):
   for y in range(maxv):
    for z in range(maxv):yield x,y,z
  return
 points=[0,1,2,maxv//2-1,maxv//2,maxv-2,maxv-1]
 points=[x for x in dict.fromkeys(points) if 0<=x<maxv]
 used=set()
 for x in points:
  for y in points:
   for z in points:
    row=(x,y,z)
    if row not in used:used.add(row);yield row
 rng=random.Random(seed+w)
 for _ in range(probes):
  row=(rng.randrange(maxv),rng.randrange(maxv),rng.randrange(maxv))
  if row not in used:used.add(row);yield row

def check(qc,meta,values):
 w=meta["input_bits"];W=meta["sum_guard_bits"]
 offset=meta["output_register_offset"]
 stream=instruction_stream(qc)
 count=0
 for x,y,z in values:
  # Input high guard bits and all other scratch start zero.
  inp=x|(y<<W)|(z<<(2*W))
  got=evaluate(stream,inp)
  expected=inp|(((x+y+z)%meta["modulus"])<<offset)
  if got!=expected:
   raise AssertionError(f"N={meta['modulus']} x={x} y={y} z={z} got={got} expected={expected} XOR={got^expected}")
  count+=1
 return count

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--probes",type=int,default=128)
 p.add_argument("--exhaustive-up-to",type=int,default=4)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=10201)
 p.add_argument("--output",default="results/a102_clean_modular_three_sum.json")
 a=p.parse_args()
 if a.n<3 or a.n%2!=1 or a.n.bit_length()>14:p.error("odd modulus with up to 14 bits required")
 if not 0<=a.probes<=100000 or not 0<=a.exhaustive_up_to<=4:p.error("invalid audit counts")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 d={"experiment":"A102_CLEAN_REVERSIBLE_MODULAR_N_THREE_OPERAND_SUM",
   "status":"IN_PROGRESS","settings":{"n":a.n,"level":a.level,
    "seed":a.seed,"probes":a.probes,"exhaustive_up_to":a.exhaustive_up_to},
   "architectures":{},"qpu_jobs_submitted":0,
   "limitations":["3-input sum modulo N is NOT modular multiplication nor full QPE",
    "High input guard bits must initialize to zero; tests cover all w-bit operands",
    "This construction copies residue and recomputes the original sum to uncompute scratch, which may dominate costs",
    "Ideal native u/cx cost only, no physical routing or phase/noise validation",
    "Large-modulus checks sampled rather than exhaustive"]}
 def save():out.write_text(json.dumps(d,indent=2)+"\n")
 save()
 try:
  w=a.n.bit_length()
  points=list(triples(w,a.probes,a.seed,a.exhaustive_up_to))
  for name in ("baseline","carry_save"):
   t=time.perf_counter()
   qc,meta=build(a.n,name)
   count=check(qc,meta,points)
   native=transpile(qc,basis_gates=["u","cx"],
       optimization_level=a.level,seed_transpiler=a.seed)
   row={"qubits":qc.num_qubits,"basis_cases":count,
     "cx":int(native.count_ops().get("cx",0)),
     "depth":int(native.depth()),"source_ops":len(qc.data),
     "seconds":round(time.perf_counter()-t,3)}
   d["architectures"][name]=row
   d["structural_parameters"]=meta
   save();print("A102",name,row,flush=True)
  l=d["architectures"]["baseline"];r=d["architectures"]["carry_save"]
  d["comparison"]={"delta_cx":r["cx"]-l["cx"],
    "cx_reduction_pct":round(100*(l["cx"]-r["cx"])/l["cx"],4),
    "delta_depth":r["depth"]-l["depth"],
    "depth_reduction_pct":round(100*(l["depth"]-r["depth"])/l["depth"],4),
    "additional_qubits":r["qubits"]-l["qubits"]}
  d["status"]="PASS_EXACT_MODULAR_SOURCE_AND_NATIVE_COST"
  save();print("A102 STATUS",d["status"],d["comparison"],flush=True)
 except Exception:
  d["status"]="FAIL";d["error"]=traceback.format_exc()[-6000:]
  save();raise

if __name__=="__main__":main()
