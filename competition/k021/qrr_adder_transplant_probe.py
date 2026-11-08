#!/usr/bin/env python3
"""K021: independently validate QRR Cuccaro adder vs Google native iadd.

No interaction with K020: output under competition/k021 and
competition/k001/private/runs/k021 only.

First prove exact classical truth-table equivalence of an in-place ripple
adder and its inverse for widths 1..8 (256*256 pairs at n=8).
Then inspect kickmix CircuitBuilder interfaces and attempt genuine micro
circuit compilation and native resource comparisons for widths 3,5,8,12.

A cost win is not a full inverse-square-root transplant. Such a transplant
requires a CLEAN carry ancilla and verified interaction with _add_row's
measurement-based uncomputation and phase semantics.
"""
from __future__ import annotations
import importlib,inspect,json,re,sys,traceback
from pathlib import Path

HERE=Path(__file__).resolve().parent
VERIFIERS=(HERE/"../k001/private/official/verifiers").resolve()
REPORT=HERE/"k021_qrr_adder_comparison.json"

def gates(n, inverse=False):
 # Cuccaro MAJ/UMA without a final carry-out. One clean carry-in ancilla,
 # a_i and b_i arrays. Each MAJ uses CX,CX,CCX; UMA CCX,CX,CX.
 # Wires are (cin=0, a=[1..n], b=[n+1..2n]).
 ops=[];carry=0;stages=[]
 for i in range(n):
  a=1+i;b=1+n+i
  stage=(carry,b,a)
  stages.append(stage)
  carry=a
 def maj(c,b,a):
  return [("cx",a,b),("cx",a,c),("ccx",c,b,a)]
 def uma(c,b,a):
  return [("ccx",c,b,a),("cx",a,c),("cx",c,b)]
 for stage in stages:ops.extend(maj(*stage))
 for stage in reversed(stages):ops.extend(uma(*stage))
 return [(op,tuple(q)) for op,*q in (reversed(ops) if inverse else ops)]

def apply(state,gate):
 op,q=gate
 if op=="cx":state[q[1]]^=state[q[0]]
 elif op=="ccx":state[q[2]]^=(state[q[0]]&state[q[1]])
 else:raise ValueError(op)

def exact_test(n):
 forward=gates(n)
 inv=gates(n,True)
 combinations=0
 for av in range(1<<n):
  a=[(av>>i)&1 for i in range(n)]
  for bv in range(1<<n):
   b=[(bv>>i)&1 for i in range(n)]
   x=[0]+a+b
   before=x[:]
   for gate in forward:apply(x,gate)
   result=sum(x[n+i+1]<<i for i in range(n))
   if result!=((av+bv)&((1<<n)-1)) or x[:n+1]!=before[:n+1]:
    raise AssertionError(f"forward n={n} a={av} b={bv} result={result} wires={x}")
   for gate in inv:apply(x,gate)
   if x!=before:raise AssertionError(f"inverse n={n} a={av} b={bv}")
   combinations+=1
 return {"width":n,"tested_pairs":combinations,"passed":True,
         "cx":sum(op=="cx" for op,_ in forward),
         "ccx":sum(op=="ccx" for op,_ in forward),
         "logical_qubits":2*n+1}

def signature(obj):
 try:return str(inspect.signature(obj))
 except Exception as e:return f"unknown: {e}"

def main():
 d={"experiment":"K021_QRR_CUCCARO_VS_GOOGLE_NATIVE_ADD",
    "status":"STARTED","full_invsqrt_transplant_verified":False,
    "k020_touched":False,"exact_tests":[],
    "kickmix_api":{},"microbenchmarks":[],
    "limitations":["Gate-count comparisons alone cannot establish full invsqrt score improvements",
                   "Ripple addition uses an extra CLEAN carry ancilla",
                   "Any full transplant must preserve measurement-based uncomputation and phase semantics"]}
 def save():
  REPORT.parent.mkdir(parents=True,exist_ok=True)
  REPORT.write_text(json.dumps(d,indent=2)+"\n")
 try:
  for n in range(1,9):
   row=exact_test(n)
   d["exact_tests"].append(row)
   print("K021 EXACT RIPPLE",n,"pairs",row["tested_pairs"],
         "CX",row["cx"],"CCX",row["ccx"],"PASS",flush=True)
  import kickmix as km
  Builder=km.CircuitBuilder
  methods=[n for n in dir(Builder) if not n.startswith("_")]
  d["kickmix_api"]={"builder_methods":methods,
      "builder_init":signature(Builder),
      "alloc_qubits":signature(getattr(Builder,"alloc_qubits",None)),
      "iadd":signature(getattr(Builder,"iadd",None)),
      "cx":signature(getattr(Builder,"cx",None)),
      "ccx":signature(getattr(Builder,"ccx",None))}
  print("K021 BUILDER API",d["kickmix_api"],flush=True)
  if VERIFIERS.exists() and str(VERIFIERS) not in sys.path:
   sys.path.insert(0,str(VERIFIERS))
  try:
   ref=importlib.import_module("invsqrt.nr_reference_circuit")
   d["source_interface"]={
     "_add_row":signature(ref._add_row),
     "build_nr_circuit":signature(ref.build_nr_circuit),
     "precision":repr(ref.Precision()),
     "source_excerpt":[line.strip() for line in
       inspect.getsource(ref._add_row).splitlines() if
       any(key in line for key in ("iadd(","isub(","init_and","del_and","scratch","target"))]}
   print("K021 SOURCE",d["source_interface"],flush=True)
  except Exception as e:
   d["source_error"]=f"{type(e).__name__}: {e}"
  # Perform native microbench if kickmix's callable interface permits it.
  # These are independent circuits and do NOT substitute for official verifier.
  for n in (3,5,8,12):
   row={"width":n,"ripple_gate_counts":exact_test(n) if n<=8 else
      {"cx":4*n,"ccx":2*n,"logical_qubits":2*n+1}}
   try:
    builder=Builder()
    q=builder.alloc_qubits(2*n+1)
    for op,indices in gates(n):
     getattr(builder,op)(*[q[j] for j in indices])
    row["ripple_build"]="GATES_EMITTED"
    row["builder_type"]=type(builder).__name__
    row["export_candidates"]=[v for v in methods if any(k in v for k in
                                     ("circuit","build","final","export"))]
    # probe natural API patterns without assuming availability
    for attr in ("build","to_circuit","circuit","get_circuit"):
     target=getattr(builder,attr,None)
     if target is None:continue
     try:
      circuit=target() if callable(target) else target
      if hasattr(circuit,"operation_statistics"):
       s=circuit.operation_statistics()
       row["ripple_native"]={
         "num_qubits":int(circuit.num_qubits),
         "toffoli_like":int(s.num_toffoli_like),
         "instructions":int(s.num_instructions),
         "reaction_depth":int(circuit.reaction_depth())}
       break
     except Exception as e:
      row[attr+"_error"]=f"{type(e).__name__}: {e}"
   except Exception as e:
    row["ripple_build_error"]=f"{type(e).__name__}: {e}"
    row["ripple_build_traceback"]=traceback.format_exc()[-500:]
   try:
    builder=Builder()
    q=builder.alloc_qubits(2*n+1)
    builder.iadd(q[1:n+1],target=q[n+1:2*n+1])
    row["native_iadd_build"]="GATES_EMITTED"
    for attr in ("build","to_circuit","circuit","get_circuit"):
     target=getattr(builder,attr,None)
     if target is None:continue
     try:
      circuit=target() if callable(target) else target
      if hasattr(circuit,"operation_statistics"):
       s=circuit.operation_statistics()
       row["native_iadd_stats"]={
         "num_qubits":int(circuit.num_qubits),
         "toffoli_like":int(s.num_toffoli_like),
         "instructions":int(s.num_instructions),
         "reaction_depth":int(circuit.reaction_depth())}
       break
     except Exception as e:
      row["iadd_"+attr+"_error"]=f"{type(e).__name__}: {e}"
   except Exception as e:
    row["native_iadd_error"]=f"{type(e).__name__}: {e}"
   d["microbenchmarks"].append(row)
   print("K021 COMPARE width",n,
         "ripple",row.get("ripple_native",row.get("ripple_build_error")),
         "native",row.get("native_iadd_stats",row.get("native_iadd_error")),
         flush=True)
  d["status"]="PASS_EXACT_RIPPLE_AND_INTERFACE_PROBE"
  save()
  print("K021 STATUS",d["status"],flush=True)
  print("K021 REPORT",REPORT,flush=True)
 except Exception:
  d["status"]="FAIL";d["traceback"]=traceback.format_exc()[-4500:]
  save();raise
if __name__=="__main__":main()
