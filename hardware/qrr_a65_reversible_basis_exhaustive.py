#!/usr/bin/env python3
"""A65 exhaustive computational-basis semantics of the actual A64 source gate circuit.

This interprets X/CX/CCX/MCX(open controls)/CSWAP reversibly without Aer.
It is a gate-level classical basis test, NOT a quantum superposition/phase test.
"""
import argparse,json,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a64_binary_modular_multiplier import build

def instruction_stream(qc):
 stream=[]
 for item in qc.data:
  op=item.operation
  indices=tuple(qc.find_bit(q).index for q in item.qubits)
  name=op.name
  if name=="x":stream.append((0,0,1<<indices[0],0));continue
  if name in ("cx","ccx") or name.startswith("mcx"):
   n=len(indices)-1
   ctrl_mask=sum(1<<j for j in indices[:-1])
   # Qiskit ctrl_state little-endian in ordered control qubits.
   state=getattr(op,"ctrl_state",None)
   if state is None:state=(1<<n)-1
   ones=sum((1<<indices[j]) for j in range(n) if (state>>j)&1)
   stream.append((1,ctrl_mask,1<<indices[-1],ones))
   continue
  if name=="cswap":
   stream.append((2,1<<indices[0],1<<indices[1],1<<indices[2]));continue
  if name=="barrier":continue
  raise ValueError(f"Unsupported source operation {name} on {indices}")
 return stream

def evaluate(stream,state):
 for op,c,t,p in stream:
  if op==0:state^=t
  elif op==1:
   if state&c==p:state^=t
  else:
   if (state&c) and bool(state&t)!=bool(state&p):state^=t|p
 return state

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=35)
 p.add_argument("--a",type=int,default=8)
 p.add_argument("--output",default="results/a65_reversible_basis_exhaustive.json")
 args=p.parse_args()
 path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
 data={"experiment":"A65_A64_SOURCE_GATE_EXHAUSTIVE_CLASSICAL_BASIS",
       "status":"IN_PROGRESS","n":args.n,"a":args.a,
       "limits":"Checks exact source reversible gate basis action and scratch cleanup, NOT quantum phases or hardware-native decompositions."}
 def save():path.write_text(json.dumps(data,indent=2)+"\n")
 save()
 try:
  start=time.perf_counter();qc=build(args.n,args.a);stream=instruction_stream(qc)
  w=args.n.bit_length();failed=[];total=0
  for ctrl in (0,1):
   for x in range(1<<w):
    initial=ctrl|(x<<1)
    got=evaluate(stream,initial)
    z=(args.a*x)%args.n if ctrl and x<args.n else x
    expected=ctrl|(z<<1)
    total+=1
    if got!=expected:
     failed.append({"control":ctrl,"input":x,"got":got,"expected":expected})
     if len(failed)>=10:break
   if failed:break
  data.update({"gate_cases":total,"qubits":qc.num_qubits,"source_operations":len(stream),
       "failures":failed,"elapsed_seconds":round(time.perf_counter()-start,3),
       "status":"PASS_EXHAUSTIVE_BASIS_WITH_CLEAN_ANCILLAS" if not failed else "FAIL_SOURCE_GATE_BASIS"})
  save()
  print("A65",data["status"],"N",args.n,"a",args.a,"cases",total,"qubits",qc.num_qubits,
        "source_gates",len(stream),"seconds",data["elapsed_seconds"],flush=True)
  if failed:
   print("FIRST FAILURES",json.dumps(failed),flush=True);sys.exit(1)
 except Exception:
  data["status"]="ERROR";data["error"]=traceback.format_exc()[-4000:];save();raise
if __name__=="__main__":main()
