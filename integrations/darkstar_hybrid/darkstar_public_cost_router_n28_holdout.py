#!/usr/bin/env python3
"""Post-freeze N28 original public-only classical router holdout.

Scientific result uses 16 *PRE-FROZEN* N28; does not train policy or choose
candidate methods from observed hidden factors/timings. No QPU.
Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import hashlib
import json
import math
import statistics
import time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

from integrations.darkstar_hybrid import darkstar_public_cost_router as router
from integrations.darkstar_hybrid import darkstar_unified as original
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import darkstar_public_router_n28_manifest as selection
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from simulation.ptp_hybrid import kernel

ROOT=Path("results/dark_star_unified")
MANIFEST=ROOT/"darkstar_public_router_n28_frozen_manifest.json"
DEST=ROOT/"darkstar_public_router_n28_original_16_holdout.json"
SHA="9f8cd1d83b3bcfdfce9c41ceda05621b52c9e9076d7cdc2dec36bc24598b7a51"
METHODS=("public_router","wheel210","PTP_LFK","old_fixed_pipeline","fermat_4096_bounded")
REPEATS=8

def frozen():
    manifest=json.loads(MANIFEST.read_text())
    rows=manifest["selected_public_rows"]
    assert len(rows)==16 and len({x["N"] for x in rows})==16
    assert manifest["row_canonical_sha256"]==SHA==selection.digest(rows)
    assert manifest["no_hidden_prime_factor_or_order_used_to_rank"]
    assert manifest["no_classical_or_quantum_outcomes_inspected_before_freeze"]
    assert manifest["router_revision"]==router.POLICY_ID
    assert manifest["router_source_git_blob_SHA"]=="4420a5d5d83869ccc41ab2396cde15d84f98a4c1"
    assert manifest["zero_QPU"] and manifest["IBM_runtime_jobs"]==0
    for i,x in enumerate(rows):
        assert 1<<27<=x["N"]<1<<28 and math.gcd(x["N"],210)==1
        assert x["rank"]==1+i%8
        assert x["group"]==("G1_mod3_1" if i<8 else "G2_mod3_2")
    return rows

def public_method(name,n):
    if name=="public_router":
        return router.public_router(n)
    if name=="wheel210":
        return kernel.wheel210_factor(n).to_dict()
    if name=="PTP_LFK":
        return kernel.lfk_factor(n).to_dict()
    if name=="old_fixed_pipeline":
        # Original complete preflight frozen in prior N27 study.
        # It includes old 12-root M105 and M15015, B31/rho64/trial97
        # and restored M255255; do NOT use hidden p/q.
        return original.public_classical_preflight(n,17,fermat_tests=12,
            restored_prune_max_offset=4095,restored_prune_square_tests=12)
    if name=="fermat_4096_bounded":
        return qr.ordinary_fermat_window(n,4095)
    raise AssertionError(name)

def truth_after_public_timing(n):
    for p in ds.primes_up_to(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q and ds.is_probable_prime(q)
            return [p,q]
    raise AssertionError("synthetic construction invalid")

def factor_of(result):
    if result["factors"]:
        return list(result["factors"])
    return None

def audit_router(n,a):
    assert a["policy"]==router.POLICY_ID and a["N"]==n
    assert a["order_or_factors_used_for_routing"] is False and not a["uses_quantum_hardware"]
    ops=a["operation_totals"]
    assert ops.get("rho_modular_squarings",0)<=384
    st=a["stages"]
    for x in st:
        if x["stage"]=="brent_public_rho":
            assert x["ops"].get("modular_squarings",0)<=x["max_modular_squarings"]
        if x["stage"]=="restored_QR_255255_bounded":
            assert x["scanned_midpoint_positions"]<=128
            assert x["exact_square_root_tests"]<=8
            assert x["no_private_prime_factors_or_order_used"]
        if x["stage"]=="public_QR_route_decision":
            assert x["selected"]==(4*x["initial_square_gap"]<=qr.ceil_sqrt(n))
    if a["method"]=="complete_wheel210_fallback":
        assert any(x["stage"]=="complete_wheel210_fallback" for x in st)
    return dict(successful_method=a["method"],stages=st,operation_totals=ops)

def evaluate(n,index):
    # Rotate the independent run order. ALL timing/computation comes from
    # public N and is collected BEFORE recovering validation-only true p/q.
    raw={method:[] for method in METHODS}
    source={}
    invocation_order=[]
    for repetition in range(REPEATS):
        ordered=METHODS[repetition%len(METHODS):]+METHODS[:repetition%len(METHODS)]
        invocation_order.append(list(ordered))
        for name in ordered:
            start=time.perf_counter()
            result=public_method(name,n)
            elapsed=time.perf_counter()-start
            raw[name].append(elapsed)
            if name not in source:
                source[name]=result
            else:
                assert factor_of(source[name])==factor_of(result),(n,name)
                if name=="public_router":
                    assert source[name]["method"]==result["method"]
                    assert source[name]["operation_totals"]==result["operation_totals"]
    truth=truth_after_public_timing(n)
    assert all(factor_of(source[name])==truth for name in ("public_router","wheel210","PTP_LFK"))
    for name in ("old_fixed_pipeline","fermat_4096_bounded"):
        assert factor_of(source[name]) in (None,truth)
    a=source["public_router"]
    branch=audit_router(n,a)
    summaries={}
    for method in METHODS:
        durations=raw[method]
        assert len(durations)==REPEATS
        summaries[method]=dict(median_seconds=statistics.median(durations),
            min_seconds=min(durations),max_seconds=max(durations),
            all_original_elapsed_seconds=durations,
            outcome_factor=source[method]["factors"],
            method_name=(source[method].get("method",method)),
            complete=method in ("public_router","wheel210","PTP_LFK"))
    r=summaries["public_router"]["median_seconds"]
    wheel=summaries["wheel210"]["median_seconds"]
    lfk=summaries["PTP_LFK"]["median_seconds"]
    fixed=summaries["old_fixed_pipeline"]["median_seconds"]
    record=dict(index=index,frozen_public_N=n,
        validation_only_synthetic_pq=truth,
        public_routing_receipt=a,
        router_audit=branch,
        original_classical_method_full_receipts=source,
        original_all_eight_interleaved_method_orders=invocation_order,
        per_method_timing=summaries,
        router_faster_than_complete_wheel210=r<wheel,
        router_faster_than_complete_PTP_LFK=r<lfk,
        router_faster_than_prior_fixed_pipeline=r<fixed,
        router_over_wheel210_median_runtime_ratio=r/wheel,
        router_over_PTP_LFK_median_runtime_ratio=r/lfk,
        true_factor_secrecy_guardrail="all timed public algorithms executed before validation-only p/q extraction",
        real_QPU_jobs=0)
    print("CASE",index,n,"router",a["method"],"sqrt",a["operation_totals"].get("exact_square_root_tests",0),
          "rho squares",a["operation_totals"].get("rho_modular_squarings",0),
          "wheel fallback divisions",a["operation_totals"].get("wheel210_fallback_divisibility_tests",0),
          "router us",round(r*1e6,1),"wheel us",round(wheel*1e6,1),"LFK us",round(lfk*1e6,1),
          flush=True)
    return record

def main():
    rows=frozen()
    out=[]
    for i,row in enumerate(rows):
        out.append(evaluate(row["N"],i))
    wins_wheel=sum(x["router_faster_than_complete_wheel210"] for x in out)
    wins_lfk=sum(x["router_faster_than_complete_PTP_LFK"] for x in out)
    wins_old=sum(x["router_faster_than_prior_fixed_pipeline"] for x in out)
    total_methods=dict(Counter(x["public_routing_receipt"]["method"] for x in out))
    ratios_wheel=[x["router_over_wheel210_median_runtime_ratio"] for x in out]
    ratios_lfk=[x["router_over_PTP_LFK_median_runtime_ratio"] for x in out]
    require=9
    passed=wins_wheel>=require and wins_lfk>=require
    summary=dict(total_new_frozen_28_bit_cases=16,
        all_correct_factors_verified=True,
        router_successful_factors=16,
        independent_complete_wheel210_success=16,
        independent_PTP_LFK_success=16,
        public_router_branch_outcomes=total_methods,
        router_faster_than_wheel210_in_cases=wins_wheel,
        router_faster_than_PTP_LFK_in_cases=wins_lfk,
        router_faster_than_previous_full_fixed_preflight_in_cases=wins_old,
        median_casewise_router_to_wheel210_runtime_ratio=statistics.median(ratios_wheel),
        median_casewise_router_to_PTP_LFK_runtime_ratio=statistics.median(ratios_lfk),
        original_primary_win_threshold_each=9,
        primary_end_to_end_two_baseline_speed_gate_pass=passed,
        all_methods_timed_interleaved_eight_times=True,
        no_hidden_factors_used_for_routing=True,
        real_QPU_jobs=0,paid_runtime=False,
        no_quantum_advantage_or_asymptotic_claim=True)
    output=dict(experiment="DarkStar_fresh_N28_public_cost_router_full_16_original_holdout",
        source_manifest_sha256=SHA,
        policy=router.POLICY_ID,
        protocol="docs/DARK_STAR_PUBLIC_COST_ROUTER_N28_PREREG.md",
        policy_source_git_blob="4420a5d5d83869ccc41ab2396cde15d84f98a4c1",
        original_case_count=16,original_repeats_per_method=REPEATS,
        complete=True,original_cases=out,summary=summary,
        limitations="small synthetic semiprimes, each classical baseline factors all N; Python microsecond timings noisy; heuristic is not a theorem for factor proximity; no QPU, no cryptographic-scale complexity benefit",
        zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False,
        analyzed_utc=datetime.now(timezone.utc).isoformat())
    ROOT.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(output,indent=2)+"\n")
    print("FULL SIXTEEN ORIGINAL PUBLIC HOLDOUT COMPLETE",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
