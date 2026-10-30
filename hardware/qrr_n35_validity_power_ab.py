#!/usr/bin/env python3
"""Actual N35 public controlled-power validity-only comparator A/B. No QPU."""
import argparse,json,traceback,statistics
from pathlib import Path
from datetime import datetime,timezone
import qrr_n35_true_recycled_phase_feedforward as source
import qrr_n35_validity_comparator_transplant as new
primitive=source.oldsel.primitive
POWERS=(2,4,8,11,16,29)
SEEDS=(509,1223,4093,8776)
OUT=Path("results/qrr_n35_validity_power_ab")
def predicate_factory(original,stats):
 def substitute(qc,x,threshold,flag,carry,chain,controls=(),geq=True):
  if len(x)==6 and int(threshold)==35:
   stats["replaced"]+=1
   return new.emit(qc,x,flag,carry,chain,controls=controls,geq=geq)
  stats["unchanged"]+=1
  return original(qc,x,threshold,flag,carry,chain,controls=controls,geq=geq)
 return substitute
def circuit_for(power,candidate):
 qc,r,_=source.source_registers()
 original=primitive.predicate
 stats={"replaced":0,"unchanged":0}
 try:
  if candidate: primitive.predicate=predicate_factory(original,stats)
  original(qc,r["work"],35,r["valid"][0],r["carry"],r["scratch"],geq=False) if not candidate else primitive.predicate(qc,r["work"],35,r["valid"][0],r["carry"],r["scratch"],geq=False)
  source.emit_public_controlled_power(qc,r,power)
  primitive.predicate(qc,r["work"],35,r["valid"][0],r["carry"],r["scratch"],geq=False)
 finally:primitive.predicate=original
 return qc,r,stats
def audit(circuit,regs,power):
 # Existing independent exact complex-amplitude +1 exhaustive source gate interpreter.
 check=source.previous.exhaustive_full_multiplier_phases(circuit,regs,power)
 assert check["pass_all"] and check["full_residue_control_basis_cases"]==128
 assert check["exact_complex_output_phase_plus_one"]
 assert check["all_25_auxiliaries_clean"] and check["disabled_invalid_states_identity"]
 return {"cases":128,"pass":True,"phase_plus_one":True,
         "counts":dict(circuit.count_ops()),"qubits":circuit.num_qubits}
def run(native=False):
 OUT.mkdir(parents=True,exist_ok=True)
 receipt={"utc":datetime.now(timezone.utc).isoformat(),"lead":"Chase Lunsford / CaMaLabs",
          "public_powers":list(POWERS),"native_requested":native,"native_compiles":0,
          "qpu_jobs":0,"pairs":[],"status":"STARTED"}
 dest=OUT/"controlled_powers_ab.json"
 def save():dest.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
 save()
 try:
  source.configure_original_public_arithmetic()
  for power in POWERS:
   row={"power":power}
   for label,variant in (("baseline",False),("candidate",True)):
    qc,r,stats=circuit_for(power,variant)
    row[label]={"proof":audit(qc,r,power),"predicate_calls":stats}
    assert stats["replaced"]>=2 if variant else stats["replaced"]==0
   receipt["pairs"].append(row);save()
   print("POWER EXACT",power,"baseline/candidate both 128/128; phase +1; auxiliaries clean",flush=True)
  receipt["status"]="SOURCE_EXACT_PASS";save()
  if native:
   from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
   from qiskit_ibm_runtime import QiskitRuntimeService
   service=QiskitRuntimeService()
   backend=service.backend("ibm_fez")
   for row in receipt["pairs"]:
    for seed in SEEDS:
     pair={"seed":seed}
     for label,variant in (("baseline",False),("candidate",True)):
      qc,_,_=circuit_for(row["power"],variant)
      manager=generate_preset_pass_manager(optimization_level=1,backend=backend,seed_transpiler=seed)
      isa=manager.run(qc)
      pair[label]={"cz":int(isa.count_ops().get("cz",0)),"depth":isa.depth(),
                   "source_qubits":qc.num_qubits}
      receipt["native_compiles"]+=1
     pair["wins_both"]=(pair["candidate"]["cz"]<pair["baseline"]["cz"] and
                        pair["candidate"]["depth"]<pair["baseline"]["depth"])
     row.setdefault("native",[]).append(pair)
     save()
    row["robust_native_win"]=sum(x["wins_both"] for x in row["native"])>=3
   receipt["status"]="NATIVE_DONE";save()
  receipt["success"]=True;save()
  print(json.dumps({"status":receipt["status"],"powers_verified":len(receipt["pairs"]),
                    "native_compiles":receipt["native_compiles"],"qpu_jobs":0},indent=2))
  return 0
 except Exception as e:
  receipt.update(status="FAIL",success=False,error=repr(e),traceback=traceback.format_exc()[-4000:])
  save();print(traceback.format_exc(),flush=True);return 1
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--native",action="store_true",
 help="after all source proofs, read-only Fez backend CPU compiles; never QPU")
 a=p.parse_args();raise SystemExit(run(a.native))
