#!/usr/bin/env python3
"""A7: public-power-29-only k23 substitution in real N35 dynamic phase recycling.
CPU proof and read-only Fez compiler only. NEVER submits a QPU job.
"""
import argparse,json,statistics,traceback
from datetime import datetime,timezone
from pathlib import Path
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import qrr_n35_true_recycled_phase_feedforward as src
import qrr_n35_complement_constant_source_selector as conj
import qrr_n35_true_recycled_prune_idle_scratch as pruning

BASES=(2,8); BITS=(4,6,8); SEEDS=(509,1223,4093,8776)
OUT=Path("results/qrr_n35_a7_power29_dynamic_ab/results.json")

def build(base,bits,candidate):
    original_emit=src.emit_public_controlled_power
    primitive=src.oldsel.primitive
    original_modadd=primitive.modadd
    original_inner=conj.old.one_bit_bypass_constant_add
    audit={"power29_stages":0,"k23_replacements":0}
    def emit(qc,reg,power):
        if not candidate or int(power)%35!=29:
            return original_emit(qc,reg,power)
        audit["power29_stages"]+=1
        def selected(qc,t,k,n,controls,flag,carry,chain):
            if int(k)%int(n)!=23:
                return original_modadd(qc,t,k,n,controls,flag,carry,chain)
            audit["k23_replacements"]+=1
            conj.old.one_bit_bypass_constant_add=conj.conjugated_constant_add
            try: return original_modadd(qc,t,k,n,controls,flag,carry,chain)
            finally: conj.old.one_bit_bypass_constant_add=original_inner
        primitive.modadd=selected
        try:return original_emit(qc,reg,power)
        finally:primitive.modadd=original_modadd
    try:
        if candidate:src.emit_public_controlled_power=emit
        qc,r,c,schedule,feedback=src.build_dynamic_source(base,bits)
    finally:
        src.emit_public_controlled_power=original_emit
        primitive.modadd=original_modadd
        conj.old.one_bit_bypass_constant_add=original_inner
    checks=src.inspect_dynamic_source(qc,r,c,base,bits,schedule,feedback)
    return qc,audit,checks

def verify_powers():
    # Reuse original authoritative exhaustive emitted source gate interpreter.
    # Validates candidate power29 and unchanged other five distinct multipliers.
    import qrr_n35_a6_selective_k23_power_ab as a6
    proof=[]
    for power in (2,4,8,11,16,29):
        qc,r,counts=a6.make(power,power==29)
        p=a6.prove(qc,r,power)
        proof.append({"power":power,"cases":p["cases"],"phase_plus_one":p["phase_plus_one"],
                      "aux_clean":p["aux_clean"],"k23_replacements":counts["k23_replaced"]})
    assert sum(x["k23_replacements"] for x in proof)==1
    return proof

def main(native):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    d={"lead":"Chase Lunsford / CaMaLabs","utc":datetime.now(timezone.utc).isoformat(),
       "A7":"public power29 k23 only, dynamic phase recycling",
       "baseline":"original 23-wire pruned identical arithmetic source",
       "phase_widths":list(BITS),"bases":list(BASES),"seeds":list(SEEDS),
       "qpu_jobs":0,"native_compiles":0,"status":"STARTED","rows":[]}
    def save():OUT.write_text(json.dumps(d,indent=2,default=str)+"\n")
    save()
    try:
        src.configure_original_public_arithmetic()
        d["power_exact_proofs"]=verify_powers();save()
        circuits={}
        for base in BASES:
            for bits in BITS:
                row={"base":base,"bits":bits,"source":{}}
                for label,flag in (("baseline",False),("candidate",True)):
                    full,audit,checks=build(base,bits,flag)
                    lean,prune_proof=pruning.reduction_with_exact_instruction_identity(full,bits)
                    circuits[base,bits,label]=lean
                    row["source"][label]={"audit":audit,
                        "source_qubits":lean.num_qubits,"measure":checks["actual_midcircuit_measure_count"],
                        "reset":checks["actual_midcircuit_reset_count"],
                        "if_else":checks["actual_classical_if_else_feedback_count"],
                        "counts":dict(lean.count_ops()),"scratch_pruned_exact":True}
                b=row["source"]["baseline"];c=row["source"]["candidate"]
                assert b["measure"]==c["measure"]==bits
                assert b["reset"]==c["reset"]==bits-1
                assert b["if_else"]==c["if_else"]==bits*(bits-1)//2
                assert c["audit"]["k23_replacements"]==sum(x["public_multiplier"]==29 for x in src.build_dynamic_source(base,bits)[3])
                assert b["audit"]["k23_replacements"]==0
                d["rows"].append(row);save()
                print("A7 SOURCE",base,bits,"k23 swaps",c["audit"]["k23_replacements"],flush=True)
        assert sum(x["source"]["candidate"]["audit"]["k23_replacements"] for x in d["rows"])>0
        d["status"]="SOURCE_PASS";save()
        if native:
            from qiskit_ibm_runtime import QiskitRuntimeService
            backend=QiskitRuntimeService().backend("ibm_fez")
            for row in d["rows"]:
                base,bits=row["base"],row["bits"];row["native"]=[]
                for seed in SEEDS:
                    pair={"seed":seed}
                    for label in ("baseline","candidate"):
                        pm=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed)
                        isa=pm.run(circuits[base,bits,label])
                        pair[label]={"cz":int(isa.count_ops().get("cz",0)),"depth":isa.depth()}
                        d["native_compiles"]+=1
                    pair["win_both"]=all(pair["candidate"][key]<pair["baseline"][key] for key in ("cz","depth"))
                    row["native"].append(pair);save()
                row["wins"]=sum(x["win_both"] for x in row["native"])
                row["median_delta_cz"]=statistics.median(x["candidate"]["cz"]-x["baseline"]["cz"] for x in row["native"])
                row["median_delta_depth"]=statistics.median(x["candidate"]["depth"]-x["baseline"]["depth"] for x in row["native"])
                row["robust_win"]=row["wins"]>=3
            d["status"]="NATIVE_DONE";save()
        d["success"]=True;save()
        print(json.dumps({"status":d["status"],"native_compiles":d["native_compiles"],
           "qpu_jobs":0,"summary":[{k:r.get(k) for k in ("base","bits","wins","median_delta_cz","median_delta_depth","robust_win")} for r in d["rows"]]},indent=2))
    except Exception:
        d.update(status="FAIL",success=False,traceback=traceback.format_exc()[-5000:]);save()
        print(traceback.format_exc());raise

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--native",action="store_true",
       help="CPU-only Fez target transpilation, never submit hardware jobs")
    main(p.parse_args().native)
