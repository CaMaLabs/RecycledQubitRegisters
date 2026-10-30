#!/usr/bin/env python3
"""N35 34-constant modular-add screening: frozen selected vs ripple/XOR increment.
Real emitted Qiskit X/CX/CCX/relative-phase gates; no QPU or private inputs.
This is NOT an implementation of Gidney's 2025 constant-workspace adder.
"""
import argparse,json,traceback,statistics
from pathlib import Path
from datetime import datetime,timezone
from qiskit import QuantumCircuit,QuantumRegister
import qrr_n35_true_recycled_phase_feedforward as source
import qrr_n35_single_modmul_ripple_toffoli as primitive
from qrr_n35_static_gate_cost_sign_selector import source_gate_cost
# Capture original ripple implementation BEFORE configure_original_public_arithmetic mutates primitive.modadd.
ORIGINAL_RIPPLE_MODADD = primitive.modadd
OUT=Path("results/qrr_n35_modadd_ripple_screen")
SEEDS=(509,1223,4093,8776)
def build(k,variant):
 en=QuantumRegister(1,"enable");t=QuantumRegister(6,"target")
 flag=QuantumRegister(1,"wrap");carry=QuantumRegister(6,"carry")
 scratch=QuantumRegister(9,"scratch")
 qc=QuantumCircuit(en,t,flag,carry,scratch)
 if variant=="selected":
  source.oldsel.structural_selected_modadd(qc,t,k,35,[en[0]],flag[0],carry,scratch)
 else:
  ORIGINAL_RIPPLE_MODADD(qc,t,k,35,[en[0]],flag[0],carry,scratch)
 return qc,dict(enable=list(en),target=list(t),wrap=list(flag),carry=list(carry),scratch=list(scratch))
def verify(qc,r,k):
 # Actual emitted gates, exact complex amplitudes (+1), not only truth-table integers.
 old=source.previous
 idx,instructions,counts=old.actual_complex_instructions(qc)
 ep=idx[r["enable"][0]];positions=[idx[z] for z in r["target"]]
 aux=[idx[z] for name in ("wrap","carry","scratch") for z in r[name]]
 cases=0
 for enabled in (0,1):
  for x in range(35 if enabled else 64):
   initial=(enabled<<ep)|sum(((x>>j)&1)<<pos for j,pos in enumerate(positions))
   end,amplitude=old.evolve_basis(instructions,initial)
   got=sum(((end>>pos)&1)<<j for j,pos in enumerate(positions))
   assert got==((x+k)%35 if enabled else x),(k,x,enabled,got)
   assert ((end>>ep)&1)==enabled
   assert all(not ((end>>pos)&1) for pos in aux),(k,x,enabled,"dirty")
   old.check_exact_phase(amplitude,f"modadd k={k} x={x} enabled={enabled}")
   cases+=1
 return dict(cases=cases,phase_plus_one=True,aux_clean=True,
             gates=dict(qc.count_ops()),source_proxy=source_gate_cost(qc.count_ops()))
def main():
 p=argparse.ArgumentParser();p.add_argument("--native",action="store_true",
 help="CPU transpile read-only ibm_fez metadata AFTER exact proof; no QPU");p.add_argument("--limit",type=int,default=34)
 a=p.parse_args();assert 1<=a.limit<=34
 OUT.mkdir(parents=True,exist_ok=True);path=OUT/"screen.json"
 result=dict(lead="Chase Lunsford / CaMaLabs",utc=datetime.now(timezone.utc).isoformat(),
  compare="frozen selected modadd vs original ripple modadd",not_gidney_adder=True,
  tested_enabled_valid_35_and_disabled_all_64=True, qpu_jobs=0, native_compiles=0,
  native_requested=a.native,rows=[],status="STARTED")
 def save():path.write_text(json.dumps(result,indent=2,default=str)+"\n")
 save()
 try:
  source.configure_original_public_arithmetic()
  cache={}
  for k in range(1,a.limit+1):
   row=dict(k=k)
   for variant in ("selected","ripple"):
    qc,r=build(k,variant)
    row[variant]=verify(qc,r,k);cache[(k,variant)]=qc
   row["source_proxy_delta_ripple_minus_selected"]=(row["ripple"]["source_proxy"]-row["selected"]["source_proxy"])
   result["rows"].append(row);save()
   print(f"K={k} EXACT 198/198 selected/ripple; PROXY DELTA {row['source_proxy_delta_ripple_minus_selected']}",flush=True)
  # Prevent accidental self-comparison due to module-level function rebinding.
  assert any(r["selected"]["gates"] != r["ripple"]["gates"] for r in result["rows"]), "Identical source histograms across every k: inspect comparison wiring"
  result["status"]="SOURCE_EXACT_PASS";save()
  if a.native:
   from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
   from qiskit_ibm_runtime import QiskitRuntimeService
   backend=QiskitRuntimeService().backend("ibm_fez")
   for row in result["rows"]:
    pairs=[]
    for seed in SEEDS:
     one=dict(seed=seed)
     for variant in ("selected","ripple"):
      pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed)
      isa=pm.run(cache[(row["k"],variant)])
      one[variant]=dict(cz=int(isa.count_ops().get("cz",0)),depth=isa.depth())
      result["native_compiles"]+=1
     one["ripple_wins_both"]=(one["ripple"]["cz"]<one["selected"]["cz"] and one["ripple"]["depth"]<one["selected"]["depth"])
     pairs.append(one);row["native"]=pairs;save()
    row["ripple_robust_win"]=sum(z["ripple_wins_both"] for z in pairs)>=3
   result["status"]="NATIVE_DONE";save()
  result["success"]=True;save()
  print(json.dumps(dict(status=result["status"],constants=len(result["rows"]),
   native_compiles=result["native_compiles"],qpu_jobs=0),indent=2))
  return 0
 except Exception as e:
  result.update(status="FAIL",success=False,error=repr(e),traceback=traceback.format_exc()[-4500:]);save()
  print(traceback.format_exc());return 1
if __name__=="__main__":raise SystemExit(main())
