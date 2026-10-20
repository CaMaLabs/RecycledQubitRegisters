#!/usr/bin/env python3
"""Independent FRESH eight-seed holdout for frozen N35 source cost sign selector.

Chase Lunsford / CaMaLabs.
Read-only Fez CPU compiler, NO device jobs/runtime. Reuse EXACT prior source
selector code and verify 34 Qiskit source gate score rows against immutable
original CI archived receipts BEFORE backend access. Verify every ACTUAL
emitted complex Qiskit gate phase on original and selected full sources.
8 new preregistered seeds + historical 8776 anchor kept OUTSIDE holdout score.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_static_gate_cost_sign_selector as original

N=35
BASES=(2,8)
ANCHOR=8776
FRESH_SEEDS=(1729,3137,5003,7919,10103,13007,20011,31799)
ALL_SEEDS=(ANCHOR,)+FRESH_SEEDS
REV="qrr-n35-static-sign-selector-fresh-seed-holdout-v1-20261019"
ROOT=Path("results/ibm_shor35_static_sign_selector_fresh_holdout")
OLD_ROOT=Path("results/ibm_shor35_static_gate_sign_selector")


def original_json(base):
    path=OLD_ROOT/f"qrr_n35_static_sign_selector_base{base}.json"
    if not path.exists():
        raise AssertionError(f"Missing original independently audited source receipt: {path}")
    z=json.loads(path.read_text())
    assert z["status"]=="COMPILE_SUCCESS" and z["success"]
    assert z["summary"]["robust_gate_per_base_pass"]
    return z


def source_proof_and_exact_previous_immutability(base,archived):
    """Re-run full phase gate oracle and compare source vectors and map EXACTLY."""
    original.bootstrap_original_best()
    arithmetic=original.standalone_public_arithmetic_identity()
    inverse=original.dm.boolean_and_inverse_operator_proof()
    cmp=original.dm.exhaustive_demorgan_comparator_phase_proof()
    assert arithmetic["cases"]==3366 and arithmetic["pass_all"]
    assert cmp["pass_all"] and cmp["actual_emitted_gate_cases"]==42672
    assert cmp["final_complex_phase_plus_one_every_case"]

    mapping,rows,positive,signed=original.prebackend_static_source_selector()
    assert rows==archived["prebackend_public_k_source_score_table"],(
        "Frozen public source score table changed before backend access")
    assert {str(k):mapping[k] for k in sorted(mapping)}==archived["public_k_sign_selection"],(
        "Frozen public public-k sign decision map changed before backend access")
    assert len(rows)==34
    assert all(mapping[k]==("signed" if k%2 else "positive")
               for k in range(1,N))

    per_k=original.quantum_phase_per_k_adds(positive,signed)
    assert per_k["pass_all"] and per_k["total_quantum_operator_basis_cases"]==6732
    assert per_k["exact_complex_phase_plus_one"] and per_k["all_aux_clean"]

    old_qc,new_qc,whole=original.prove_whole_source_variants(base,mapping)
    prev=archived["prebackend_exact_quantum_gate_proofs"]["whole_full_multiplier"]
    assert whole["actual_signed_weighted_additions"]==prev["actual_signed_weighted_additions"]
    assert whole["actual_positive_weighted_additions"]==prev["actual_positive_weighted_additions"]
    assert whole["selection_for_each_weight"]==prev["selection_for_each_weight"]
    for version in ("original_full","candidate_full"):
        p=whole[version]
        ref=prev[version]
        assert p["pass_all"] and p["full_residue_control_basis_cases"]==128
        assert p["all_25_auxiliaries_clean"] and p["exact_complex_output_phase_plus_one"]
        assert p["quantum_source_gate_counts"]==ref["quantum_source_gate_counts"]
    assert old_qc.num_qubits==new_qc.num_qubits==32
    print("FROZEN ORIGINAL SOURCE AND EXACT QUANTUM GATE PHASES VERIFIED",base,
          "3366 identity +42672 comparator +6732 per-k both signs +128 original +128 selected",
          "34 archived public decision/proxy vectors UNCHANGED",
          "signed weighted",whole["actual_signed_weighted_additions"],"NO QPU",
          flush=True)
    return old_qc,new_qc,dict(
        public_arithmetic_identity=arithmetic,
        inverse_operator=inverse,
        comparator_complex_phase_proof=cmp,
        all_34_both_implementations_phase_proof=per_k,
        full_multipliers_complex_phase_proof=whole,
        original_all_34_source_score_rows_exact_match=True,
        public_sign_choice_map_exact_match=True,
        full_source_gate_distribution_exact_match=True,
        every_amplitude_exactly_plus_one=True,
        all_25_aux_clean=True,
        application_logical_qubits=32)


def summarize_fresh(fresh,anchor_pair,archived):
    assert len(fresh)==8
    delta_cz=[z["candidate_minus_original"]["cz"] for z in fresh]
    delta_depth=[z["candidate_minus_original"]["depth"] for z in fresh]
    wins=sum(a<0 and b<0 for a,b in zip(delta_cz,delta_depth))
    anchor_archived=next(z for z in archived["matched_seed_pairs"] if z["seed"]==8776)
    anchor_ok=all(anchor_pair[v]["cz"]==anchor_archived[v]["cz"] and
                  anchor_pair[v]["depth"]==anchor_archived[v]["depth"]
                  for v in ("original","candidate"))
    medc=statistics.median(delta_cz)
    medd=statistics.median(delta_depth)
    return dict(
        fresh_pairs=8,
        anchor_8776_is_separate_and_not_counted=True,
        anchor_original_and_selected_both_exact_historical=anchor_ok,
        historical_anchor_drift=not anchor_ok,
        fresh_joint_cz_and_depth_improvement_seeds=wins,
        fresh_cz_improvement_seeds=sum(x<0 for x in delta_cz),
        fresh_depth_improvement_seeds=sum(x<0 for x in delta_depth),
        fresh_median_paired_cz_delta=medc,
        fresh_median_paired_depth_delta=medd,
        fresh_min_paired_cz_delta=min(delta_cz),
        fresh_max_paired_cz_delta=max(delta_cz),
        fresh_min_paired_depth_delta=min(delta_depth),
        fresh_max_paired_depth_delta=max(delta_depth),
        frozen_rule_at_least_six_of_eight_joint=(wins>=6),
        both_fresh_paired_medians_strictly_negative=(medc<0 and medd<0),
        fresh_holdout_per_base_pass=bool(
            anchor_ok and wins>=6 and medc<0 and medd<0),
        every_fresh_and_anchor_result_preserved=True,
        all_fresh_and_anchor_compiles_fail_device_gate=all(
            not z["candidate_hardware_feasible"] and
            not z["original_hardware_feasible"]
            for z in [anchor_pair]+fresh)
    )


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    output=ROOT/f"qrr_n35_static_sign_fresh_holdout_base{base}.json"
    rec=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        utc=datetime.now(timezone.utc).isoformat(),
        preregistration="docs/QRR_N35_STATIC_GATE_SIGN_FRESH_SEED_HOLDOUT_PREREG.md",
        old_verified_result_document="docs/QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md",
        N=N,base=base,fresh_seeds=list(FRESH_SEEDS),historical_anchor_seed=ANCHOR,
        all_pair_seeds_in_compile_order=list(ALL_SEEDS),
        original_source_score_formula="cx+6*ccx+3*rccx; x excluded; ties choose positive",
        original_k_selection_map_immutable=True,
        read_only_ibm_target="ibm_fez",optimizer_level=1,
        device_cz_limit=800,device_depth_limit=2000,
        full_six_bit_public_residue=True,true_order_not_used=True,
        prime_factors_not_used=True,precomputed_modular_orbit_not_used=True,
        qpu_jobs_submitted=0,paid_runtime_used=False,quantum_runtime_used=False,
        original_anchor_pair=None,fresh_seed_pairs=[],
        status="STARTED",success=False)
    def save():output.write_text(json.dumps(rec,indent=2,default=str)+"\n")
    save()
    try:
        prior=original_json(base)
        qc_old,qc_new,proof=source_proof_and_exact_previous_immutability(base,prior)
        rec["before_backend_source_quantum_proof"]=proof
        rec["frozen_old_8776_native_anchor"]={
            v:{m:next(z for z in prior["matched_seed_pairs"] if z["seed"]==ANCHOR)[v][m]
               for m in ("cz","depth")} for v in ("original","candidate")}
        rec["status"]="FROZEN_SOURCE_PHASE_PROOFS_PASS"
        save()

        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Invalid IBM Fez backend TARGET")
        rec["fez_target_num_qubits"]=int(backend.num_qubits)
        rec["status"]="NATIVE_CPU_FRESH_HOLDOUT_COMPILATION"
        save()

        for seed in ALL_SEEDS:
            pm=generate_preset_pass_manager(backend=backend,
                optimization_level=1,seed_transpiler=seed)
            old=original.native_compile(pm,qc_old)
            new=original.native_compile(pm,qc_new)
            delta=dict(cz=new["cz"]-old["cz"],depth=new["depth"]-old["depth"])
            row=dict(seed=seed,original=old,candidate=new,
                candidate_minus_original=delta,
                both_native_resources_improved=(delta["cz"]<0 and delta["depth"]<0),
                original_hardware_feasible=(old["cz"]<=800 and old["depth"]<=2000),
                candidate_hardware_feasible=(new["cz"]<=800 and new["depth"]<=2000))
            if seed==ANCHOR:
                rec["original_anchor_pair"]=row
            else:
                rec["fresh_seed_pairs"].append(row)
            save()
            print("FRESH N35 STATIC SIGN SOURCE FEZ CPU",base,seed,
                "ANCHOR" if seed==ANCHOR else "HOLDOUT",
                "ORIGINAL",old["cz"],old["depth"],
                "NEW",new["cz"],new["depth"],
                "DELTA",delta["cz"],delta["depth"],
                "JOINT",row["both_native_resources_improved"],
                "DEVICE",row["candidate_hardware_feasible"],
                "NO QPU",flush=True)

        summ=summarize_fresh(rec["fresh_seed_pairs"],rec["original_anchor_pair"],prior)
        rec.update(status="COMPILE_SUCCESS",success=True,
            fresh_holdout_summary=summ,
            all_eighteen_native_compilations_complete=True)
        save()
        print("FRESH HOLDOUT N35 SUMMARY",base,json.dumps(summ,sort_keys=True),
              "NO QPU",flush=True)
        return 0
    except Exception as exc:
        rec.update(status="FAIL",success=False,
            failure_class=type(exc).__name__,
            failure_message=str(exc)[:1800],
            failure_traceback=traceback.format_exc()[-3200:],
            qpu_jobs_submitted=0,paid_runtime_used=False,quantum_runtime_used=False)
        save()
        print("FRESH N35 PUBLIC SIGN HOLDOUT FAILED",base,type(exc).__name__,
            str(exc)[:700],traceback.format_exc()[-1200:],
            "ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(ap.parse_args().base))
