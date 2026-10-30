#!/usr/bin/env python3
"""Frozen N32 PTP vs Brent separation benchmark. No quantum hardware.

Only PUBLIC N enters the search methods; synthetic p,q and separation
labels enter solely AFTER all benchmark methods finish on each N.
Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
from collections import Counter
import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from integrations.darkstar_hybrid import darkstar_public_cost_router as old
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from integrations.darkstar_hybrid import darkstar_v2 as ds
from simulation.ptp_hybrid import kernel
from integrations.darkstar_hybrid import darkstar_n32_separation_manifest as population

ROOT=Path("results/dark_star_unified")
MAN=ROOT/"darkstar_n32_separation_frozen_manifest.json"
DEST=ROOT/"darkstar_n32_separation_vs_brent_original_24_results.json"
METHODS=("B","F","Q","FQ","wheel210","PTP_LFK","fermat2048")
STRATA=("near_0_8","middle_64_640","far_4096_16384")
REPEATS=9
RHO_BUDGETS=((1,2,1024),(3,3,512))
QR_OFFSET=2047
QR_SQUARES=96
EARLY_SQUARES=8

def factor_public(n,method):
    """No private factor/order/stratum can enter this function."""
    if method=="wheel210":
        z=kernel.wheel210_factor(n)
        return dict(factors=list(z.factors) if z.factors else None,
                    method="wheel210",operations=dict(divisibility_tests=z.divisibility_tests),
                    stages=[dict(stage="wheel210",**z.to_dict())],
                    complete=True)
    if method=="PTP_LFK":
        z=kernel.lfk_factor(n)
        return dict(factors=list(z.factors) if z.factors else None,
                    method="PTP_LFK",operations=dict(divisibility_tests=z.divisibility_tests,
                    integer_search_steps=z.integer_search_steps,pair_checks=z.pair_checks),
                    stages=[dict(stage="PTP_LFK",**z.to_dict())],complete=True)
    if method=="fermat2048":
        z=qr.ordinary_fermat_window(n,QR_OFFSET)
        return dict(factors=z["factors"],method="fermat2048",operations=dict(
                square_root_tests=z["exact_square_root_tests"],
                midpoint_positions=z["scanned_midpoint_positions"]),
                stages=[dict(stage="fermat2048",**z)],complete=False)
    if method not in ("B","F","Q","FQ"):
        raise ValueError(method)
    stages=[]
    totals=Counter()
    for p in (2,3,5,7):
        totals["divisibility_tests"]+=1
        if n%p==0:
            found=old.factors_of(p,n)
            stages.append(dict(stage="base_prime",factor=p,factors=found))
            if found:
                return dict(factors=found,method=method,successful_stage="base_prime",
                    operations=dict(totals),stages=stages,complete=True)
    if method in ("F","FQ"):
        z=old.early_fermat(n,EARLY_SQUARES)
        totals["plain_fermat_square_roots"]+=z["exact_square_tests"]
        stages.append(dict(stage="plain_fermat8",**z))
        if z["factors"]:
            return dict(factors=z["factors"],method=method,successful_stage="plain_fermat8",
                operations=dict(totals),stages=stages,complete=True)
    if method in ("Q","FQ"):
        # Clear per-N masks BEFORE recording this invocation's elapsed time
        # so per-modulus setup is NOT accidentally free from prior repetitions.
        qr.allowed_mask.cache_clear()
        z=qr.fast_public_midpoint_factor(n,qr.WHEELS[255255],
            max_offset=QR_OFFSET,max_square_tests=QR_SQUARES)
        totals["QR_modular_membership_checks"]+=z["modular_membership_checks"]
        totals["QR_sqrt_tests"]+=z["exact_square_root_tests"]
        totals["QR_positions_scanned"]+=z["scanned_midpoint_positions"]
        stages.append(dict(stage="QR_255255",**z))
        assert z["no_private_prime_factors_or_order_used"]
        assert z["scanned_midpoint_positions"]<=QR_OFFSET+1
        assert z["exact_square_root_tests"]<=QR_SQUARES
        if z["factors"]:
            return dict(factors=z["factors"],method=method,successful_stage="QR_255255",
                operations=dict(totals),stages=stages,complete=True)
    for c,seed,budget in RHO_BUDGETS:
        z=old.brent_attempt(n,c,seed,budget)
        stages.append(dict(stage="public_Brent",c=c,seed=seed,budget=budget,**z))
        assert z["ops"].get("modular_squarings",0)<=budget
        for key,val in z["ops"].items():
            totals["rho_"+key]+=val
        if z["factors"]:
            return dict(factors=z["factors"],method=method,successful_stage="public_Brent",
                operations=dict(totals),stages=stages,complete=True)
    wheel=kernel.wheel210_factor(n)
    totals["fallback_wheel_divisibility_tests"]+=wheel.divisibility_tests
    stages.append(dict(stage="complete_wheel_fallback",**wheel.to_dict()))
    return dict(factors=list(wheel.factors) if wheel.factors else None,
        method=method,successful_stage="complete_wheel_fallback",
        operations=dict(totals),stages=stages,complete=True)

def synthetic_truth_after_all_timing(n):
    # This is NOT available to the functions above.
    for p in ds.primes_up_to(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q and ds.is_probable_prime(q)
            return [p,q]
    raise AssertionError("synthetic semiprime construction invalid")

def audited_manifest():
    m=json.loads(MAN.read_text())
    rows=m["selected_public_rows"]
    assert m["sha256_canonical_rows"]==population.digest(rows)
    assert len(rows)==24 and len({x["N"] for x in rows})==24
    assert m["no_factors_or_order_in_public_manifest"]
    assert m["no_routing_algorithm_receives_construction_stratum"]
    assert m["zero_QPU"]
    for i,r in enumerate(rows):
        assert r["stratum"]==STRATA[i//8]
        assert r["rank"]==i%8+1 and (1<<31)<=r["N"]<(1<<32)
    return m

def single_case(i,row):
    n=row["N"]
    timings={k:[] for k in METHODS}
    receipts={}
    order=[]
    # Fully interleave methods, shifting order deterministically each repeat.
    # The factor construction stratum is deliberately NEVER passed here.
    for rep in range(REPEATS):
        methods=METHODS[rep%len(METHODS):]+METHODS[:rep%len(METHODS)]
        order.append(list(methods))
        for method in methods:
            start=time.perf_counter()
            z=factor_public(n,method)
            elapsed=time.perf_counter()-start
            timings[method].append(elapsed)
            if method not in receipts:
                receipts[method]=z
            else:
                assert receipts[method]["factors"]==z["factors"],(i,n,method)
                if method in ("B","F","Q","FQ"):
                    assert receipts[method]["successful_stage"]==z["successful_stage"]
                    assert receipts[method]["operations"]==z["operations"]
    # Only after all public-only benchmark runs: generate synthetic truth.
    truth=synthetic_truth_after_all_timing(n)
    p,q=truth
    D=(p+q)//2 - qr.ceil_sqrt(n)
    assert population.stratum_for(D)==row["stratum"],(i,n,D,row["stratum"])
    for method in ("B","F","Q","FQ","wheel210","PTP_LFK"):
        assert receipts[method]["factors"]==truth,(i,method,receipts[method]["factors"],truth)
    assert receipts["fermat2048"]["factors"] in (None,truth)
    assert receipts["B"]["operations"].get("rho_modular_squarings",0)<=1536
    for method in ("Q","FQ"):
        for z in receipts[method]["stages"]:
            if z["stage"]=="QR_255255":
                assert z["exact_square_root_tests"]<=96
                assert z["scanned_midpoint_positions"]<=2048
                if z["factors"]:
                    assert z["found_at_offset"]==D
    summary={name:dict(
        complete=receipts[name]["complete"],
        median_elapsed_seconds=statistics.median(timings[name]),
        raw_nine_elapsed_seconds=timings[name],
        min_elapsed_seconds=min(timings[name]),
        max_elapsed_seconds=max(timings[name]),
        factors=receipts[name]["factors"],
        successful_stage=receipts[name].get("successful_stage"),
        operations=receipts[name]["operations"]) for name in METHODS}
    B=summary["B"]["median_elapsed_seconds"]
    F=summary["F"]["median_elapsed_seconds"]
    Q=summary["Q"]["median_elapsed_seconds"]
    FQ=summary["FQ"]["median_elapsed_seconds"]
    counts={k:dict(benefit=summary[k]["median_elapsed_seconds"]<B,
                   ratio_to_B=summary[k]["median_elapsed_seconds"]/B)
            for k in ("F","Q","FQ")}
    counts["Q"]["faster_than_F"]=Q<F
    result=dict(index=i,public_N=n,construction_stratum_post_validation=row["stratum"],
        validation_only_prime_factors=truth,validation_only_true_Fermat_midpoint_offset=D,
        public_methods_called_with_only_N=True,
        complete_method_receipts=receipts,full_timing_by_method=summary,
        invocation_orders=order,
        paired_vs_strong_B=counts,
        actual_QPU_jobs=0)
    print("RESULT",i,row["stratum"],"N",n,"offset",D,
          "route B",receipts["B"].get("successful_stage"),
          "QR",receipts["Q"].get("successful_stage"),
          "B_us",round(B*1e6,2),"Q/B",round(Q/B,3),
          "F/B",round(F/B,3),"FQ/B",round(FQ/B,3),flush=True)
    return result

def main():
    manifest=audited_manifest()
    rows=manifest["selected_public_rows"]
    cases=[single_case(i,r) for i,r in enumerate(rows)]
    assert len(cases)==24
    per={}
    for stratum in STRATA:
        subset=[x for x in cases if x["construction_stratum_post_validation"]==stratum]
        assert len(subset)==8
        per[stratum]=dict(
            N_count=8,
            Q_faster_than_B=sum(x["paired_vs_strong_B"]["Q"]["benefit"] for x in subset),
            Q_faster_than_F=sum(x["paired_vs_strong_B"]["Q"]["faster_than_F"] for x in subset),
            F_faster_than_B=sum(x["paired_vs_strong_B"]["F"]["benefit"] for x in subset),
            FQ_faster_than_B=sum(x["paired_vs_strong_B"]["FQ"]["benefit"] for x in subset),
            median_Q_to_B=statistics.median(x["paired_vs_strong_B"]["Q"]["ratio_to_B"] for x in subset),
            median_F_to_B=statistics.median(x["paired_vs_strong_B"]["F"]["ratio_to_B"] for x in subset))
    middle=per["middle_64_640"]
    total_fq=sum(x["paired_vs_strong_B"]["FQ"]["benefit"] for x in cases)
    first=middle["Q_faster_than_B"]>=6 and middle["Q_faster_than_F"]>=6
    second=total_fq>=13
    summary=dict(
        total_original_frozen_N32_cases=24,
        all_six_complete_methods_verify_exact_factors=True,
        algorithm_calls_only_public_N=True,
        strata=per,
        primary_Q_middle_vs_B_wins=middle["Q_faster_than_B"],
        primary_Q_middle_vs_F_wins=middle["Q_faster_than_F"],
        primary_minimum_both=6,
        prereg_PTP_specific_middle_win=first,
        secondary_FQ_wins_vs_B_all_strata=total_fq,
        secondary_required_minimum=13,
        prereg_broad_FQ_router_win=second,
        max_rho_square_count=1536,
        public_PT_P_only_square_work_with_setup_included=True,
        eight_or_more_raw_repeats_per_method=True,
        no_quantum_or_crypto_complexity_claim=True,
        zero_QPU=True)
    result=dict(experiment="DarkStar_fresh_N32_prematched_factor_separation_PTP_vs_strong_Brent",
        protocol="docs/DARK_STAR_N32_SEPARATION_VS_BRENT_PREREG.md",
        public_manifest_row_SHA256=manifest["sha256_canonical_rows"],
        complete=True,
        original_cases=cases,
        summary=summary,
        limitations="training population originally configured by hidden synthetic factor separations but factoring algorithms see only N. Timed 32-bit Python methods not state-of-the-art factoring and not asymptotic or quantum speedup.",
        real_QPU_jobs=0,paid_runtime_used=False,
        timestamp_utc=datetime.now(timezone.utc).isoformat())
    ROOT.mkdir(exist_ok=True,parents=True)
    (ROOT/"darkstar_n32_separation_vs_brent_original_24_results.json").write_text(json.dumps(result,indent=2)+"\n")
    print("ORIGINAL COHORT COMPLETE",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
