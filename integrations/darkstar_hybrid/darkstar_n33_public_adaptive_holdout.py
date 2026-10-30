#!/usr/bin/env python3
"""Full prospective N33 24-case public-only adaptive QR selector holdout.

Only N and fixed method label enter live algorithm. Prime-factor truth and
synthetic strata used AFTER all complete per-case timings, solely to audit
scientific outcomes. No QPU, no training on this cohort.
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

from integrations.darkstar_hybrid import darkstar_n33_public_adaptive_qr as policy
from integrations.darkstar_hybrid import darkstar_n33_public_manifest as selection
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr

ROOT=Path("results/dark_star_unified")
MAN=ROOT/"darkstar_n33_adaptive_qr_public_frozen_manifest.json"
OUT=ROOT/"darkstar_n33_adaptive_qr_original_24_result.json"
STAGES=("near_0_8","middle_64_640","far_4096_16384")
REPEATS=9

def get_frozen():
    m=json.loads(MAN.read_text())
    rr=m["original_public_rows"]
    assert len(rr)==len({r["N"] for r in rr})==24
    assert m["row_SHA256"]==selection.row_sha(rr)
    assert m["hidden_factors_not_in_manifest"]
    assert m["factorization_not_performed_before_manifest_freeze"]
    assert m["group_labels_are_population_metadata_not_factor_algorithm_inputs"]
    assert m["immutable_policy_source_sha"]=="431d1e8d8e3120c78415dcae226cb521be652732"
    assert m["zero_QPU"] and m["IBM_runtime_jobs"]==0
    assert tuple(inspect.signature(policy.public_factor).parameters)==("n","method")
    assert policy.METHODS==("A","B","F","Q","W","L","M")
    for i,r in enumerate(rr):
        assert r["group"]==STAGES[i//8] and r["rank"]==i%8+1
        assert 1<<32<=r["N"]<1<<33 and math.gcd(r["N"],210)==1
        assert all(x not in r for x in ("p","q","D","true_midpoint_offset"))
    return m

def post_timing_truth(n):
    for p in ds.primes_up_to(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q and ds.is_probable_prime(q)
            return [p,q]
    raise AssertionError("Invalid original synthetic semiprime")

def single(i,spec):
    n=spec["N"]
    raw={key:[] for key in policy.METHODS}
    orig={}
    schedule=[]
    for rep in range(REPEATS):
        arms=policy.METHODS[rep%len(policy.METHODS):]+policy.METHODS[:rep%len(policy.METHODS)]
        schedule.append(list(arms))
        for arm in arms:
            start=time.perf_counter()
            z=policy.public_factor(n,arm)
            elapsed=time.perf_counter()-start
            raw[arm].append(elapsed)
            assert z["N"]==n and z["arm"]==arm
            assert z["public_N_only"] and not z["has_private_factor_or_stratum_input"]
            assert z["QPU_jobs"]==0
            if arm not in orig:
                orig[arm]=z
            else:
                assert orig[arm]["factors"]==z["factors"],(i,arm)
                assert orig[arm]["successful_stage"]==z["successful_stage"],(i,arm)
                assert orig[arm]["operations"]==z["operations"],(i,arm)
    truth=post_timing_truth(n)
    p,q=truth
    D=(p+q)//2 - qr.ceil_sqrt(n)
    assert selection.group_for(D)==spec["group"],(i,n,D,spec["group"])
    for arm in ("A","B","F","Q","W","L"):
        assert orig[arm]["complete"]
        assert orig[arm]["factors"]==truth,(i,arm,orig[arm]["factors"],truth)
    assert orig["M"]["factors"] in (None,truth)
    for arm in ("A","B","F","Q"):
        assert orig[arm]["operations"].get("rho_modular_squarings",0)<=1536
        for z in orig[arm]["stages"]:
            if z["stage"] in ("public_QR_64_position_pilot","extended_QR_midpoint_scan"):
                if z["factors"]:
                    assert z["found_at_offset"]==D
                assert z["exact_square_root_tests"]<=64
    for arm in ("A","Q"):
        steps=orig[arm]["stages"]
        if any(x["stage"]=="QR_public_mask_setup" for x in steps):
            assert any(x["stage"]=="public_QR_64_position_pilot" for x in steps)
            assert sum(x["exact_square_root_tests"] for x in steps
                       if x["stage"] in ("public_QR_64_position_pilot","extended_QR_midpoint_scan"))<=64
            if arm=="A":
                decision=next((x for x in steps if x["stage"]=="public_eligibility_decision"),None)
                if decision:
                    assert decision["extend"]==(decision["qualifying_pilot_positions"]<=2
                        and not next(x for x in steps if x["stage"]=="public_QR_64_position_pilot")["root_cap_hit"])
    stats={arm:dict(
        median_wall_seconds=statistics.median(raw[arm]),
        all_nine_original_times_seconds=raw[arm],
        min_wall_seconds=min(raw[arm]),max_wall_seconds=max(raw[arm]),
        factor_verified=orig[arm]["factors"]==truth,
        method=orig[arm]["successful_stage"],
        complete=orig[arm]["complete"],
        public_operations=orig[arm]["operations"]) for arm in policy.METHODS}
    med={arm:stats[arm]["median_wall_seconds"] for arm in policy.METHODS}
    pilot=next((x for x in orig["A"]["stages"] if x["stage"]=="public_QR_64_position_pilot"),None)
    dec=next((x for x in orig["A"]["stages"] if x["stage"]=="public_eligibility_decision"),None)
    decision=dict(reached_QR_pilot=pilot is not None,
        pilot_qualified_midpoints=(pilot["qualifying_positions"] if pilot else None),
        pilot_found_factor=(bool(pilot["factors"]) if pilot else False),
        extended_QR_selected=bool(dec and dec["extend"]),
        factor_from_A_QR=orig["A"]["successful_stage"] in
            ("public_QR_64_position_pilot","extended_QR_midpoint_scan"),
        predictor_only_public_data=True)
    row=dict(index=i,public_frozen_N=n,
        original_synthetic_stratum_post_validation=spec["group"],
        validation_only_prime_factors=truth,validation_only_actual_midpoint_D=D,
        model_is_CPU_only=True,raw_interleaved_arm_orders=schedule,
        original_method_receipts=orig,full_comparison_timing=stats,
        adaptive_online_decision=decision,
        paired_wins=dict(A_faster_than_B=med["A"]<med["B"],
                         A_faster_than_Q=med["A"]<med["Q"],
                         A_faster_than_F=med["A"]<med["F"],
                         A_faster_than_W=med["A"]<med["W"],
                         A_faster_than_L=med["A"]<med["L"]),
        ratios=dict(A_over_B=med["A"]/med["B"],
                    A_over_Q=med["A"]/med["Q"],
                    A_over_F=med["A"]/med["F"]))
    print("CASE",i,spec["group"],n,"D",D,"A",orig["A"]["successful_stage"],
          "pilot_hits",decision["pilot_qualified_midpoints"],
          "extend",decision["extended_QR_selected"],
          "A/B",round(row["ratios"]["A_over_B"],3),
          "A/Q",round(row["ratios"]["A_over_Q"],3),flush=True)
    return row

def main():
    cohort=get_frozen()
    originals=[single(i,spec) for i,spec in enumerate(cohort["original_public_rows"])]
    assert len(originals)==24
    groups={}
    for group in STAGES:
        rr=[r for r in originals if r["original_synthetic_stratum_post_validation"]==group]
        assert len(rr)==8
        groups[group]=dict(
            cases=len(rr),
            A_beats_B=sum(r["paired_wins"]["A_faster_than_B"] for r in rr),
            A_beats_Q=sum(r["paired_wins"]["A_faster_than_Q"] for r in rr),
            A_beats_F=sum(r["paired_wins"]["A_faster_than_F"] for r in rr),
            Q_pilot_reached=sum(r["adaptive_online_decision"]["reached_QR_pilot"] for r in rr),
            extended_QR_selected=sum(r["adaptive_online_decision"]["extended_QR_selected"] for r in rr),
            actual_A_QR_factor_recovery=sum(r["adaptive_online_decision"]["factor_from_A_QR"] for r in rr),
            median_casewise_A_to_B=statistics.median(r["ratios"]["A_over_B"] for r in rr),
            median_casewise_A_to_Q=statistics.median(r["ratios"]["A_over_Q"] for r in rr))
    all_b=sum(r["paired_wins"]["A_faster_than_B"] for r in originals)
    all_q=sum(r["paired_wins"]["A_faster_than_Q"] for r in originals)
    p1=all_b>=15 and all_q>=15
    gmid=groups["middle_64_640"]
    gfar=groups["far_4096_16384"]
    p2=gmid["A_beats_B"]>=6 and gmid["extended_QR_selected"]>=4 and
        (8-gfar["extended_QR_selected"]>=6)
    summary=dict(
        total_original_cases=24,all_six_complete_algorithms_correct=True,
        public_only_policy_inputs_verified=True,
        original_N33_public_manifest_SHA=cohort["row_SHA256"],
        strata=groups,
        adaptive_beats_B_total=all_b,
        adaptive_beats_nonadaptive_Q_total=all_q,
        primary_threshold_each=15,
        prereg_primary_adaptive_policy_gate_pass=p1,
        secondary_middle_A_beats_B=gmid["A_beats_B"],
        secondary_middle_extended_QR_selected=gmid["extended_QR_selected"],
        secondary_far_extended_QR_skipped=8-gfar["extended_QR_selected"],
        prereg_secondary_middle_and_far_selectivity_gate_pass=p2,
        nine_interleaved_timings_each_method=True,
        qpu_jobs=0,uses_no_hidden_factors_to_route=True,
        no_asymptotic_or_quantum_advantage_claim=True)
    full=dict(experiment="DarkStar_N33_ORIGINAL_public_only_QR_selectivity_adaptive_vs_Brent",
        prereg="docs/DARK_STAR_N33_PUBLIC_ADAPTIVE_QR_PREREG.md",
        frozen_public_manifest_SHA=cohort["row_SHA256"],
        frozen_policy_source_git_blob=cohort["immutable_policy_source_sha"],
        complete=True,original_cases=originals,summary=summary,
        zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False,
        interpretation="selected separation strata use synthetic factors for construction only; policy never has access; 33-bit classical CPU results not a quantum or cryptographic advantage",
        completed_utc=datetime.now(timezone.utc).isoformat())
    ROOT.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(full,indent=2)+"\n")
    print("ORIGINAL 24 ALL SIX FACTORED N33",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
