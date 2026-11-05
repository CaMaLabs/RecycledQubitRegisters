#!/usr/bin/env python3
"""A104: externally controlled clean reversible modular-3-sum XOR primitive.

Map |control,a,b,c,dst=any,workspace=0> to
|control,a,b,c,dst XOR (control * ((a+b+c) mod N)),workspace=0>.
The A102 computation is run, result is copied via CCX to destination,
and the full A102 computation is uncomputed. This tests control and
workspace cleanup with a FAIR ripple vs CSA comparison.

This does NOT implement modular multiplication, in-place modular
addition, or an entire recycled QPE. Additional qubits are explicit.
"""
import argparse,json,random,sys,time,traceback
from pathlib import Path
from qiskit import QuantumCircuit,transpile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from qrr_a102_clean_modular_csa_three_sum import build as modular_sum
from qrr_a65_reversible_basis_exhaustive import instruction_stream,evaluate

def build(n,architecture):
 work,meta=modular_sum(n,architecture)
 w=meta["input_bits"];W=meta["sum_guard_bits"]
 # Prefix all original workspace with control register, add destination at end.
 qc=QuantumCircuit(work.num_qubits+1+w)
 control=qc.qubits[0]
 src=list(qc.qubits[1:1+work.num_qubits])
 dst=list(qc.qubits[1+work.num_qubits:])
 qc.compose(work,qubits=src,inplace=True)
 residue_offset=meta["output_register_offset"]
 for j in range(w):
  qc.ccx(control,src[residue_offset+j],dst[j])
 qc.compose(work.inverse(),qubits=src,inplace=True)
 return qc,{"n":n,"w":w,"W":W,"work_qubits":work.num_qubits,
  "control_index":0,"dst_offset":1+work.num_qubits,
  "architecture":architecture,"qubits":qc.num_qubits}

def cases(w,probes,seed,exhaustive_limit):
 limit=1<<w
 if w<=exhaustive_limit:
  for control in (0,1):
   for x in range(limit):
    for y in range(limit):
     for z in range(limit):
      for dest in (0,limit-1):
       yield control,x,y,z,dest
  return
 edge=[0,1,2,limit//2,limit-1]
 edge=list(dict.fromkeys(x for x in edge if 0<=x<limit))
 for control in (0,1):
  for x in edge:
   for y in edge:
    for z in edge:
     for dest in (0,limit-1):
      yield control,x,y,z,dest
 rng=random.Random(seed+w)
 for _ in range(probes):
  yield rng.randrange(2),rng.randrange(limit),rng.randrange(limit),rng.randrange(limit),rng.randrange(limit)

def validate(qc,meta,all_cases):
 stream=instruction_stream(qc)
 w=meta["w"];W=meta["W"];offset=meta["dst_offset"];n=meta["n"]
 count=0
 for control,x,y,z,dest in all_cases:
  initial=control|(x<<1)|(y<<(1+W))|(z<<(1+2*W))|(dest<<offset)
  expected=control|(x<<1)|(y<<(1+W))|(z<<(1+2*W))|(
   (dest^( ((x+y+z)%n) if control else 0))<<offset)
  observed=evaluate(stream,initial)
  if observed!=expected:
   raise AssertionError(f"N={n} arch={meta['architecture']} control={control} operands={x,y,z} dest={dest} xor={observed^expected}")
  count+=1
 return count

def run():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=15)
 p.add_argument("--level",type=int,choices=(0,1,2),default=1)
 p.add_argument("--seed",type=int,default=10401)
 p.add_argument("--probes",type=int,default=128)
 p.add_argument("--exhaustive-up-to",type=int,default=4)
 p.add_argument("--output",default="results/a104_controlled_modular_csa.json")
 a=p.parse_args()
 if a.n<3 or a.n%2!=1 or a.n.bit_length()>14:p.error("odd modulus with at most 14 bits")
 if not 0<=a.exhaustive_up_to<=4 or not 0<=a.probes<=100000:p.error("invalid audit probe counts")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"A104_CONTROLLED_MODULAR_3_SUM_XOR",
  "status":"IN_PROGRESS","settings":{"n":a.n,"level":a.level,
   "seed":a.seed,"probes":a.probes,"exhaustive_up_to":a.exhaustive_up_to},
  "architectures":{},"qpu_jobs_submitted":0,
  "limitations":["Controlled 3-input modular XOR, NOT modular multiplication or in-place modular addition",
   "Full A102 compute and uncompute retained; output is a fresh independent destination register",
   "Qubit width exceeds A97 modular-power width, so gate savings are not directly transferable",
   "Source-gate computational basis tests only, no phase-noise or real-QPU proof"]}
 def save():out.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  vals=list(cases(a.n.bit_length(),a.probes,a.seed,a.exhaustive_up_to))
  for arch in ("baseline","carry_save"):
   tick=time.perf_counter()
   qc,meta=build(a.n,arch)
   tested=validate(qc,meta,vals)
   native=transpile(qc,basis_gates=["u","cx"],optimization_level=a.level,seed_transpiler=a.seed)
   data["architectures"][arch]={
    "logical_qubits":qc.num_qubits,"cx":int(native.count_ops().get("cx",0)),
    "depth":int(native.depth()),"basis_cases":tested,
    "source_ops":len(qc.data),"seconds":round(time.perf_counter()-tick,3)}
   save()
   print("A104",arch,data["architectures"][arch],flush=True)
  x=data["architectures"]["baseline"];y=data["architectures"]["carry_save"]
  data["comparison"]={"delta_cx":y["cx"]-x["cx"],
    "cx_reduction_pct":round(100*(x["cx"]-y["cx"])/x["cx"],4),
    "delta_depth":y["depth"]-x["depth"],
    "depth_reduction_pct":round(100*(x["depth"]-y["depth"])/x["depth"],4),
    "extra_qubits":y["logical_qubits"]-x["logical_qubits"]}
  data["status"]="PASS_CONTROLLED_REVERSIBLE_BASIS_AND_NATIVE_COST"
  save()
  print("A104 STATUS",data["status"],data["comparison"],flush=True)
 except Exception:
  data["status"]="FAIL";data["error"]=traceback.format_exc()[-6000:]
  save();raise
if __name__=="__main__":run()
