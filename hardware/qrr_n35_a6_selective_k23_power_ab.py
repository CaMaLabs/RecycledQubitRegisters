#!/usr/bin/env python3
"""A6 selective k=23 complement in REAL N35 public controlled multipliers.
Phase-exact full-residue proofs before any Fez CPU compilation. Zero QPU.
"""
import argparse,json,traceback,statistics
from datetime import datetime,timezone
from pathlib import Path
import qrr_n35_true_recycled_phase_feedforward as source
import qrr_n35_complement_constant_source_selector as complement
POWERS=(2,4,8,11,16,29);SEEDS=(509,1223,4093,8776)
OUT=Path("results/qrr_n35_a6_k23_full_power_ab/results.json")
def make(power,variant):
    qc,r,_=source.source_registers()
    old=source.oldsel
    original=old.structural_selected_modadd
    original_inner=complement.old.one_bit_bypass_constant_add
    counts={"k23_replaced":0,"other_k_unchanged":0}
    def selective(qc,target,k,modulus,controls,flag,carry,chain):
        if int(k)%int(modulus)==23:
            counts["k23_replaced"]+=1
            complement.old.one_bit_bypass_constant_add=complement.conjugated_constant_add
            try:return original(qc,target,k,modulus,controls,flag,carry,chain)
            finally:complement.old.one_bit_bypass_constant_add=original_inner
        counts["other_k_unchanged"]+=1
        return original(qc,target,k,modulus,controls,flag,carry,chain)
    primitive=old.primitive
    original_hook=primitive.modadd
    try:
        if variant: primitive.modadd=selective
        primitive.predicate(qc,r["work"],35,r["valid"][0],r["carry"],r["scratch"],geq=False)
        source.emit_public_controlled_power(qc,r,power)
        primitive.predicate(qc,r["work"],35,r["valid"][0],r["carry"],r["scratch"],geq=False)
    finally:
        primitive.modadd=original_hook
        complement.old.one_bit_bypass_constant_add=original_inner
    assert counts["k23_replaced"]==0 if not variant else True
    return qc,r,counts
def prove(qc,r,power):
    proof=source.previous.exhaustive_full_multiplier_phases(qc,r,power)
    assert proof["pass_all"] and proof["full_residue_control_basis_cases"]==128
    assert proof["exact_complex_output_phase_plus_one"] and proof["all_25_auxiliaries_clean"]
    assert proof["disabled_invalid_states_identity"]
    return {"cases":128,"phase_plus_one":True,"aux_clean":True,"ops":dict(qc.count_ops())}
def run(native):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    d={"research_lead":"Chase Lunsford / CaMaLabs","created_utc":datetime.now(timezone.utc).isoformat(),
       "experiment":"A6: selective k23 in original public controlled powers",
       "seeds":list(SEEDS),"status":"STARTED","qpu_jobs":0,"native_compiles":0,"rows":[]}
    def save():OUT.write_text(json.dumps(d,indent=2)+"\n")
    save()
    try:
        source.configure_original_public_arithmetic()
        compiled={}
        substitutions=0
        for power in POWERS:
            row={"power":power}
            for label,variant in (("baseline",False),("candidate",True)):
                qc,r,counts=make(power,variant)
                row[label]={"proof":prove(qc,r,power),"counts":counts}
                compiled[power,label]=qc
                if variant:substitutions+=counts["k23_replaced"]
            d["rows"].append(row);save()
            print("A6 EXACT POWER",power,"candidate substitutions",row["candidate"]["counts"]["k23_replaced"],flush=True)
        if substitutions==0:raise AssertionError("No k23 calls were replaced; reject inert A/B")
        if not any(row["baseline"]["proof"]["ops"]!=row["candidate"]["proof"]["ops"] for row in d["rows"]):
            raise AssertionError("Candidate source histograms all equal: reject self-comparison")
        d["source_proof_pass"]=True;d["status"]="SOURCE_PASS";save()
        if native:
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
            from qiskit_ibm_runtime import QiskitRuntimeService
            backend=QiskitRuntimeService().backend("ibm_fez")
            for row in d["rows"]:
                row["native"]=[]
                for seed in SEEDS:
                    pair={"seed":seed}
                    for label in ("baseline","candidate"):
                        pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed)
                        isa=pm.run(compiled[row["power"],label])
                        pair[label]={"cz":int(isa.count_ops().get("cz",0)),"depth":isa.depth()}
                        d["native_compiles"]+=1
                    pair["win_both"]=all(pair["candidate"][metric]<pair["baseline"][metric] for metric in ("cz","depth"))
                    row["native"].append(pair);save()
                row["wins"]=sum(x["win_both"] for x in row["native"])
                row["robust_win"]=row["wins"]>=3
                row["median_delta_cz"]=statistics.median(x["candidate"]["cz"]-x["baseline"]["cz"] for x in row["native"])
                row["median_delta_depth"]=statistics.median(x["candidate"]["depth"]-x["baseline"]["depth"] for x in row["native"])
            d["status"]="NATIVE_DONE";save()
        d["success"]=True;save()
        print(json.dumps({"status":d["status"],"public_powers":len(d["rows"]),"substitutions":substitutions,
          "native_compiles":d["native_compiles"],"qpu_jobs":0,
          "summary":[{k:row.get(k) for k in ("power","wins","median_delta_cz","median_delta_depth","robust_win")} for row in d["rows"]]},indent=2))
        return 0
    except Exception:
        d.update(status="FAIL",success=False,traceback=traceback.format_exc()[-4500:]);save();print(traceback.format_exc());return 1
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--native",action="store_true",
       help="Read-only IBM Fez target CPU transpilation; no QPU job")
    raise SystemExit(run(parser.parse_args().native))
