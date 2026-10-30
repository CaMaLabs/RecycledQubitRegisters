#!/usr/bin/env python3
"""A5: hotspot-specific modular-add exact proof and native A/B.
Challenger uses existing complement-conjugate inner adder, not a new Gidney design.
No QPU submission; only read-only Fez target metadata on --native.
"""
import argparse,json,traceback
from pathlib import Path
from datetime import datetime,timezone
from qiskit import QuantumCircuit,QuantumRegister
import qrr_n35_true_recycled_phase_feedforward as source
import qrr_n35_complement_constant_source_selector as complement
HOTSPOTS=(11,13,17,23,29);SEEDS=(509,1223,4093,8776)
OUT=Path("results/qrr_n35_a5_hotspot_complement_ab/results.json")
def construct(k,arm):
 en=QuantumRegister(1,"enable");t=QuantumRegister(6,"target")
 wrap=QuantumRegister(1,"wrap");carry=QuantumRegister(6,"carry");scratch=QuantumRegister(9,"scratch")
 qc=QuantumCircuit(en,t,wrap,carry,scratch)
 original=complement.old.one_bit_bypass_constant_add
 try:
  if arm=="complement":
   complement.old.one_bit_bypass_constant_add=complement.conjugated_constant_add
  source.oldsel.structural_selected_modadd(qc,t,k,35,[en[0]],wrap[0],carry,scratch)
 finally: complement.old.one_bit_bypass_constant_add=original
 return qc,{"enable":list(en),"target":list(t),"wrap":list(wrap),"carry":list(carry),"scratch":list(scratch)}
def prove(qc,r,k):
 verifier=source.previous
 ix,inst,ops=verifier.actual_complex_instructions(qc)
 ep=ix[r["enable"][0]]
 bits=[ix[b] for b in r["target"]]
 aux=[ix[b] for name in ("wrap","carry","scratch") for b in r[name]]
 for enabled in (0,1):
  for y in range(35 if enabled else 64):
   before=(enabled<<ep)|sum(((y>>j)&1)<<b for j,b in enumerate(bits))
   after,phase=verifier.evolve_basis(inst,before)
   z=sum(((after>>b)&1)<<j for j,b in enumerate(bits))
   assert z==((y+k)%35 if enabled else y),(k,enabled,y,z)
   assert ((after>>ep)&1)==enabled
   assert all(not ((after>>b)&1) for b in aux),(k,enabled,y,"dirty")
   verifier.check_exact_phase(phase,f"A5 k={k},enable={enabled},y={y}")
 return {"cases":99,"exact_phase_plus_one":True,"all_ancillas_clean":True,
         "gates":dict(qc.count_ops())}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--native",action="store_true");args=ap.parse_args()
 OUT.parent.mkdir(parents=True,exist_ok=True)
 result={"research_lead":"Chase Lunsford / CaMaLabs",
  "date":datetime.now(timezone.utc).isoformat(),
  "challenge":"existing conjugate inner add vs original selected N35 modadd",
  "not_new_gidney_or_shared_xor_design":True,"hotspots":list(HOTSPOTS),
  "native_compiles":0,"qpu_jobs":0,"status":"STARTED","rows":[]}
 def save():OUT.write_text(json.dumps(result,indent=2,default=str)+"\n")
 save()
 try:
  source.configure_original_public_arithmetic()
  circuits={}
  for k in HOTSPOTS:
   row={"k":k,"source":{}}
   for arm in ("selected","complement"):
    qc,r=construct(k,arm)
    row["source"][arm]=prove(qc,r,k)
    circuits[(k,arm)]=qc
   result["rows"].append(row);save()
   print("A5 EXACT",k,"198/198, exact +1, all aux clean; gates",row["source"],flush=True)
  # If the selected code path does not actually invoke the patched routine,
  # do not spend time compiling a meaningless self-comparison.
  assert any(row["source"]["selected"]["gates"]!=row["source"]["complement"]["gates"] for row in result["rows"]), "No source differences: candidate hook ineffective"
  result["status"]="SOURCE_PASS";save()
  if args.native:
   from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
   from qiskit_ibm_runtime import QiskitRuntimeService
   backend=QiskitRuntimeService().backend("ibm_fez")
   for row in result["rows"]:
    row["native"]=[]
    for seed in SEEDS:
     pair={"seed":seed}
     for arm in ("selected","complement"):
      pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed)
      isa=pm.run(circuits[(row["k"],arm)])
      pair[arm]={"cz":int(isa.count_ops().get("cz",0)),"depth":isa.depth()}
      result["native_compiles"]+=1
     pair["candidate_win_both"]=all(pair["complement"][key]<pair["selected"][key] for key in ("cz","depth"))
     row["native"].append(pair);save()
    row["robust_win"]=sum(x["candidate_win_both"] for x in row["native"])>=3
   result["status"]="NATIVE_DONE";save()
  result["success"]=True;save()
  print(json.dumps({"status":result["status"],"rows":len(result["rows"]),"native_compiles":result["native_compiles"],"qpu_jobs":0},indent=2))
 except Exception as e:
  result.update(status="FAIL",success=False,error=str(e),traceback=traceback.format_exc()[-3000:]);save()
  print(traceback.format_exc());raise
if __name__=="__main__":main()
