#!/usr/bin/env python3
"""Prospectively frozen N34 Dark Star anytime interleaving original holdout.

24 NEW public N inputs, 7 arms x 9 interleaved full timing reps. Validation
p,q/D recovered only AFTER all public method calls and timing per N.
Uninterrupted and segmented same rho c1 tested separately as strict invariant.
No IBM QPU/Runtime. Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import inspect
import json
import math
import statistics
import time
from pathlib import Path

from integrations.darkstar_hybrid import darkstar_n34_anytime_scheduler as alg
from integrations.darkstar_hybrid import darkstar_n34_anytime_public_manifest as pop
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr

ROOT=Path("results/dark_star_unified")
PUBLIC=ROOT/"darkstar_n34_anytime_public_frozen_manifest.json"
RESULT=ROOT/"darkstar_n34_anytime_original_24_result.json"
GROUPS=("near_0_8","middle_64_640","far_4096_16384")
REPEATS=9
SOURCE_SHA="afdc1e69a94ebfdd7d73fd2b6d5ada6d8c589753"

def frozen():
    m=json.loads(PUBLIC.read_text())
    rows=m["original_public_rows"]
    assert len(rows)==len({r["N"] for r in rows})==24
    assert m["row_SHA256"]==pop.row_sha(rows)
    assert m["selection_salt"]=="DARKSTAR-N34-ANYTIME-20261029"
    assert m["immutable_policy_source_sha"]==SOURCE_SHA
    assert m["hidden_factors_not_in_manifest"]
    assert m["factorization_not_performed_before_manifest_freeze"]
    assert m["group_labels_are_population_metadata_not_factor_algorithm_inputs"]
    assert m["zero_QPU"] and m["IBM_runtime_jobs"]==0 and not m["paid_runtime_used"]
    assert tuple(inspect.signature(alg.factor_public).parameters)==("n","method")
    for i,row in enumerate(rows):
        assert row["group"]==GROUPS[i//8] and row["rank"]==i%8+1
        assert 1<<33<=row["N"]<1<<34 and math.gcd(row["N"],210)==1
    return m

def synthetic_truth_after_timing(n):
    for p in ds.primes_up_to(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q and ds.is_probable_prime(q)
            return [p,q]
    raise AssertionError("synthetic N34 composite failed original construction test")

def resumable_semantics(n):
    results=[]
    for c,seed,budget,stages in ((1,2,1024,alg.BRENT_C1_CHECKPOINTS),
                                 (3,3,512,(96,384,512))):
        uninterrupted=alg.BrentState(n,c,seed,budget)
        uninterrupted.run_until(budget)
        segmented=alg.BrentState(n,c,seed,budget)
        trace=[]
        for cutoff in stages:
            trace.append(segmented.run_until(cutoff))
        assert segmented.factors==uninterrupted.factors
        assert segmented.phase==uninterrupted.phase
        assert segmented.done==uninterrupted.done
        assert dict(segmented.ops)==dict(uninterrupted.ops)
        assert segmented.ops["modular_squarings"]<=budget
        results.append(dict(c=c,seed=seed,budget=budget,
            exact_uninterrupted_vs_paused_factor_equality=True,
            exact_uninterrupted_vs_paused_operation_equality=True,
            cumulative_operations=dict(uninterrupted.ops),
            segmented_checkpoint_receipts=trace))
    return results

def score(i,spec):
    n=spec["N"]
    raw={a:[] for a in alg.METHODS}
    original={}
    invocation_orders=[]
    # Deliberately never pass synthetic construction 'group' to the factoring
    # algorithm or the decisions of when to run QR or Brent.
    for repeat in range(REPEATS):
        rotated=alg.METHODS[repeat%len(alg.METHODS):]+alg.METHODS[:repeat%len(alg.METHODS)]
        invocation_orders.append(list(rotated))
        for arm in rotated:
            start=time.perf_counter()
            z=alg.factor_public(n,arm)
            elapsed=time.perf_counter()-start
            raw[arm].append(elapsed)
            assert z["N"]==n and z["arm"]==arm and z["quantum_jobs"]==0
            assert z["only_public_N_used"] and z["no_factor_or_stratum_or_order_input"]
            if arm not in original:
                original[arm]=z
            else:
                assert z["factors"]==original[arm]["factors"]
                assert z["successful_stage"]==original[arm]["successful_stage"]
                assert z["operation_counts"]==original[arm]["operation_counts"]

    # Reveal only now validation prime factors, never for public selection.
    pq=synthetic_truth_after_timing(n)
    p,q=pq
    displacement=(p+q)//2-qr.ceil_sqrt(n)
    assert pop.group_for(displacement)==spec["group"]
    for method in ("A","B","F","Q","W","L"):
        assert original[method]["complete"]
        assert original[method]["factors"]==pq,(i,n,method,original[method]["factors"],pq)
        ops=original[method]["operation_counts"]
        assert ops.get("Brent_c1_modular_squarings",0)<=1024
        assert ops.get("Brent_c3_modular_squarings",0)<=512
        assert ops.get("QR_exact_square_root_tests",0)<=64
        for part in original[method]["stages"]:
            if part["stage"]=="public_QR_segment" and part["factors"]:
                assert part["found_at_offset"]==displacement
    assert original["M"]["factors"] in (None,pq)
    invariants=resumable_semantics(n)
    times={name:dict(median_seconds=statistics.median(samples),
        original_nine_seconds=samples,
        minimum_seconds=min(samples),maximum_seconds=max(samples),
        factor=original[name]["factors"],
        successful_stage=original[name]["successful_stage"],
        complete=original[name]["complete"]) for name,samples in raw.items()}
    t={a:times[a]["median_seconds"] for a in alg.METHODS}
    wins=dict(A_better_than_B=t["A"]<t["B"],
        A_better_than_Q=t["A"]<t["Q"],
        A_better_than_F=t["A"]<t["F"],
        A_better_than_W=t["A"]<t["W"],
        A_better_than_L=t["A"]<t["L"])
    ratios=dict(A_to_B=t["A"]/t["B"],
        A_to_Q=t["A"]/t["Q"],A_to_F=t["A"]/t["F"])
    summary=dict(index=i,original_public_N=n,
        construction_stratum_for_post_analysis_only=spec["group"],
        synthetic_validation_only_pq=pq,
        synthetic_validation_only_Fermat_midpoint_offset=displacement,
        all_algorithms_received_only_public_N=True,
        complete_original_arm_receipts=original,
        uninterrupted_vs_segmented_rho_proof=invariants,
        original_interleaved_method_orders=invocation_orders,
        original_nine_timing_repeats=times,
        paired_wins=wins,paired_runtime_ratios=ratios,
        no_real_QPU=True)
    print("ORIGINAL",i,spec["group"],n,"D",displacement,
        "stage",original["A"]["successful_stage"],
        "A/B",round(ratios["A_to_B"],3),
        "A/Q",round(ratios["A_to_Q"],3),
        "Brent_sq",original["A"]["operation_counts"].get("Brent_c1_modular_squarings",0),
        "QR_positions",original["A"]["operation_counts"].get("QR_midpoint_positions",0),
        flush=True)
    return summary

def main():
    inputs=frozen()
    out=[score(i,r) for i,r in enumerate(inputs["original_public_rows"])]
    assert len(out)==24
    groups={}
    for group in GROUPS:
        cases=[x for x in out if x["construction_stratum_for_post_analysis_only"]==group]
        assert len(cases)==8
        groups[group]=dict(
            count=8,
            A_faster_than_B=sum(x["paired_wins"]["A_better_than_B"] for x in cases),
            A_faster_than_Q=sum(x["paired_wins"]["A_better_than_Q"] for x in cases),
            A_faster_than_F=sum(x["paired_wins"]["A_better_than_F"] for x in cases),
            A_solved_by_Fermat8=sum(x["complete_original_arm_receipts"]["A"]["successful_stage"]=="early_plain_fermat8" for x in cases),
            A_solved_by_QR=sum(x["complete_original_arm_receipts"]["A"]["successful_stage"]=="anytime_QR_segment" for x in cases),
            A_solved_by_Brent=sum(x["complete_original_arm_receipts"]["A"]["successful_stage"] in ("resumed_Brent_c1","Brent_c3") for x in cases),
            median_casewise_A_to_B=statistics.median(x["paired_runtime_ratios"]["A_to_B"] for x in cases),
            median_casewise_A_to_Q=statistics.median(x["paired_runtime_ratios"]["A_to_Q"] for x in cases),
            median_anytime_QR_midpoint_positions=statistics.median(x["complete_original_arm_receipts"]["A"]["operation_counts"].get("QR_midpoint_positions",0) for x in cases))
    winsB=sum(x["paired_wins"]["A_better_than_B"] for x in out)
    winsQ=sum(x["paired_wins"]["A_better_than_Q"] for x in out)
    winsF=sum(x["paired_wins"]["A_better_than_F"] for x in out)
    far=groups["far_4096_16384"]
    mid=groups["middle_64_640"]
    primary=winsB>=15 and winsQ>=15 and winsF>=13
    secondary=(mid["A_faster_than_B"]>=6 and
        far["A_faster_than_Q"]>=6 and
        far["median_casewise_A_to_B"]<=1.25)
    summary=dict(total_original_34_bit_cases=24,
        all_six_complete_arms_factor_correctly=True,
        exact_24_case_paused_vs_uninterrupted_rho_state_equivalence=True,
        public_only_N_inputs_for_every_factorization=True,
        group_breakdown=groups,
        anytime_win_count_vs_Brent_B=winsB,
        anytime_win_count_vs_full_PTP_Q=winsQ,
        anytime_win_count_vs_Fermat_Brent_F=winsF,
        primary_thresholds=dict(vs_Brent=15,vs_full_QR=15,vs_Fermat_Brent=13),
        original_primary_anytime_gate_PASS=primary,
        secondary_middle_A_faster_than_B=mid["A_faster_than_B"],
        secondary_far_A_faster_than_full_QR=far["A_faster_than_Q"],
        secondary_far_median_A_to_B=far["median_casewise_A_to_B"],
        original_secondary_far_overhead_gate_PASS=secondary,
        original_nine_rotated_repeats_for_each_method=True,
        hardware_QPU_jobs=0,
        full_factorization_speed_or_quantum_advantage_unproven=True)
    result=dict(experiment="DarkStar_N34_anytime_resumable_Brent_QR_interleaving_original",
        prereg="docs/DARK_STAR_N34_ANYTIME_INTERLEAVED_PREREG.md",
        frozen_public_selection_SHA=inputs["row_SHA256"],
        source_frozen_policy_git_blob=SOURCE_SHA,
        complete=True,original_cases=out,
        original_summary=summary,zero_QPU=True,
        paid_runtime_used=False,IBM_runtime_jobs=0,
        limitations="synthetic factor-separation strata are population construction only, not public target information. Small 34-bit Python timing, no crypto scaling or quantum use.",
        completed_utc=datetime.now(timezone.utc).isoformat())
    ROOT.mkdir(exist_ok=True,parents=True)
    RESULT.write_text(json.dumps(result,indent=2)+"\n")
    print("VERIFIED N34 FULL ORIGINAL COHORT",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
