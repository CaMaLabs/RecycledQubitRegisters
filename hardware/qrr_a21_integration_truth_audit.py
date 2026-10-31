#!/usr/bin/env python3
"""A21: truth-in-integration audit of Dark Star, selected arithmetic, recycled
QPE, native placement, and Quaspy. Does NOT claim cross-modulus end-to-end
synergy. No backend API/QPU jobs, no changes to the verified circuit.
"""
import argparse,hashlib,json,re,traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def fingerprint(rel):
    path=ROOT/rel
    return {"exists":path.is_file(),
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None}
def textcheck(rel,needles):
    p=ROOT/rel
    if not p.is_file():return {"file":rel,"present":False,"matches":{}}
    s=p.read_text()
    return {"file":rel,"present":True,"matches":{k:k in s for k in needles}}
def stage(label,status,details):
    return {"component":label,"status":status,"details":details}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="results/qrr_a21_integration_truth_audit.json")
    args=parser.parse_args()
    report={"status":"STARTED","qpu_jobs":0,"purpose":"Audit demonstrated vs actually integrated methods; not an RSA breaking claim",
        "components":[],"gaps":[],"files":{}}
    files=[
        "hardware/dark_star_recycled_scalable_arithmetic_audit.py",
        "hardware/qrr_n35_true_recycled_phase_feedforward.py",
        "hardware/qrr_n35_true_recycled_prune_idle_scratch.py",
        "hardware/qrr_a20_direct_cycle_multiplier.py",
        "integrations/darkstar_hybrid/quaspy_public_postprocess.py",
        "results/indie_diamond_20261030/audit.json.gz",
        "docs/DARK_STAR_RECYCLED_SCALABLE_ARITHMETIC_RESULT.md",
        "docs/QRR_A18_HARDWARE_FEASIBILITY_NO_GO_20261030.md",
        "docs/QRR_A19_NATIVE_POWER_COST_RESULT_20261030.md",
        "docs/QRR_A20_DIRECT_CYCLE_MULTIPLIER_NATIVE_NEGATIVE_20261030.md"
    ]
    report["files"]={p:fingerprint(p) for p in files}
    try:
        checks={
         "darkstar":textcheck("hardware/dark_star_recycled_scalable_arithmetic_audit.py",["recycled","order"]),
         "selected":textcheck("hardware/qrr_n35_true_recycled_phase_feedforward.py",["configure_original_public_arithmetic","emit_public_controlled_power","build_dynamic_source","phase_exact_public_stage_proof"]),
         "pruned":textcheck("hardware/qrr_n35_true_recycled_prune_idle_scratch.py",["reduction_with_exact_instruction_identity","source_dynamic_audit"]),
         "post":textcheck("integrations/darkstar_hybrid/quaspy_public_postprocess.py",["def recover","def load_upstream"]),
        }
        report["source_signatures"]=checks
        # These are different benchmark populations and cannot be combined by simple multiplication.
        report["components"].append(stage("Dark Star public order preconditioning","ARCHIVED_SEPARATE_RESOURCE_MODEL",
           "N209/713/781 staged expected work; not wired to N35 base8 b4 native circuit"))
        report["components"].append(stage("Selected modular adders and phase recycling","SOURCE_WIRED",
           "N35 dynamic source explicitly bootstraps oldsel selected arithmetic and builds one reused phase qubit"))
        report["components"].append(stage("Idle-scratch pruning","SOURCE_WIRED_IN_NATIVE_PATH",
           "N35 32->23 qubit exact instruction replay; hardware compiled for A12-A19"))
        report["components"].append(stage("Physical placement and calibration","POST_COMPILATION_OFFLINE",
           "A12-A18 metadata/routing, no physical fidelity or shot-level optimization"))
        report["components"].append(stage("Quaspy/Ekera public postprocess","SEPARATE_SYNTHETIC_HOLDOUT",
           "A8-A17 ideal and perturbation holdouts, not fed N35 real hardware counts"))
        report["components"].append(stage("A20 direct transpositions","REJECTED_NATIVE_COST",
           "Exact 128 basis per power, but isolated native CZ 21k-32k"))
        report["gaps"]=[
          {"id":"G1","priority":"HIGH","description":"No single matched holdout uses Dark Star public preconditioning, N35-class selected arithmetic, recycled QPE, and Quaspy together with measured or adequately simulated phase output."},
          {"id":"G2","priority":"HIGH","description":"Dark Star resource benchmark uses N209/713/781; A-series native ISA uses N35; Quaspy synthetic benchmark uses other semiprimes. Population transfer invalid."},
          {"id":"G3","priority":"HIGH","description":"No whole-pipeline classical preprocessing accounting and objective denominator (factoring cost per verified recovery) on a common cohort."},
          {"id":"G4","priority":"HIGH","description":"Native N35 CZ/depth 14k+/32k+ fails gate; no QPU budget spend justified."},
          {"id":"G5","priority":"MEDIUM","description":"Original periodic prime-table/pruning methods need separate explicit provenance/ablation verification; no claim those are currently active in emitted N35 circuit."}
        ]
        assert checks["selected"]["present"] and all(checks["selected"]["matches"].values())
        assert checks["pruned"]["present"] and all(checks["pruned"]["matches"].values())
        assert checks["post"]["present"] and all(checks["post"]["matches"].values())
        assert report["files"]["docs/DARK_STAR_RECYCLED_SCALABLE_ARITHMETIC_RESULT.md"]["exists"]
        report["status"]="PASS_WITH_INTEGRATION_GAPS"
    except Exception:
        report["status"]="FAILED_PRECONDITION";report["error"]=traceback.format_exc()
        raise
    finally:
        path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"qpu_jobs":0,
       "integration_gaps":report["gaps"],"components":report["components"]},indent=2))
if __name__=="__main__":main()
