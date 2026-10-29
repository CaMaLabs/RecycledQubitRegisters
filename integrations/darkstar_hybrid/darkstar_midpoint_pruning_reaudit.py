#!/usr/bin/env python3
"""Exact secondary audit of original Dark Star midpoint pruning across frozen N26.

Compare old per-N table and the new public quadratic-residue sieve, with
identical geometric search limits, verified factors and timed conventional
classical baselines. No quantum hardware. Lead Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
from bisect import bisect_left
from collections import Counter
import hashlib
import json
import math
import statistics
import time
from datetime import datetime,timezone
from pathlib import Path
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from simulation.ptp_hybrid import kernel

ROOT=Path("results/dark_star_unified")
SHA="0c25e448b646a5ade7d919ca78597c8c2883fd8fd450181dd4504c18252fb939"
PROTOCOL="docs/DARK_STAR_N26_RESTORED_MIDPOINT_PRUNING_PROTOCOL.md"
ORIGINAL=ROOT/"unified_n26_public_manifest.json"
DEST=ROOT/"unified_n26_midpoint_pruning_reaudit.json"
WINDOW=4095
REPS=7
WHEELS=(105,15015,255255)


def legacy_exact_window(n,M,cap=WINDOW):
    """v2's actual sorted factor-coupled allowed-residue jump, x budget fixed."""
    t0=time.perf_counter()
    allowed,stats=ds.midpoint_residues(n,M)
    setup=time.perf_counter()-t0
    x0=qr.ceil_sqrt(n)
    limit=x0+cap
    xr=x0%M
    i=bisect_left(allowed,xr)
    if i==len(allowed):
        x=x0+M-xr+allowed[0]
        i=0
    else:
        x=x0+allowed[i]-xr
    tests=0
    last=None
    t1=time.perf_counter()
    f=None
    while x<=limit:
        tests+=1
        v=x*x-n
        y=math.isqrt(v)
        if y*y==v and (x-y)>1:
            p,q=x-y,x+y
            if p*q==n:
                f=[min(p,q),max(p,q)]
                last=x-x0
                break
        j=i+1
        if j<len(allowed):
            x+=allowed[j]-allowed[i]
            i=j
        else:
            x+=M-allowed[i]+allowed[0]
            i=0
    search=time.perf_counter()-t1
    return dict(factors=f,found=f is not None,exact_square_root_tests=tests,
        found_at_offset=last,one_time_public_setup_seconds=setup,
        scan_seconds=search,total_seconds=setup+search,
        midpoint_allowed_count=stats.allowed_count,
        pruning_factor_nominal=stats.pruning_factor)


def time_runs(fn):
    rows=[fn() for _ in range(REPS)]
    base=rows[0]
    assert all(row["factors"]==base["factors"] for row in rows)
    return dict(first_original=base,
        median_total_seconds=statistics.median(row["total_seconds"] for row in rows),
        median_setup_seconds=statistics.median(row.get("one_time_public_mask_setup_seconds",
             row.get("one_time_public_setup_seconds",0.)) for row in rows),
        min_seconds=min(row["total_seconds"] for row in rows),
        max_seconds=max(row["total_seconds"] for row in rows),
        source_repetitions=REPS)


def record(n,truth):
    plain=time_runs(lambda:qr.ordinary_fermat_window(n,WINDOW))
    expected=truth
    assert plain["first_original"]["factors"]==expected
    old={}
    new={}
    exact_agreements=0
    for M in WHEELS:
        ps=qr.WHEELS[M]
        new[str(M)]=time_runs(lambda:qr.fast_public_midpoint_factor(n,ps,WINDOW))
        x=new[str(M)]["first_original"]
        assert x["factors"]==expected
        assert x["found_at_offset"]==plain["first_original"]["found_at_offset"]
        assert x["exact_square_root_tests"]<=plain["first_original"]["exact_square_root_tests"]
        if M in (105,15015):
            old[str(M)]=time_runs(lambda:legacy_exact_window(n,M,WINDOW))
            y=old[str(M)]["first_original"]
            assert y["factors"]==expected
            assert y["found_at_offset"]==x["found_at_offset"]
            assert y["exact_square_root_tests"]==x["exact_square_root_tests"]
            old_allowed,_=ds.midpoint_residues(n,M)
            membership=set(old_allowed)
            masks=[qr.allowed_mask(p,n%p) for p in ps]
            # Every residue modulo full wheel has EXACTLY the same allowed state,
            # not just selected factor points. This proves no candidate loss.
            for xres in range(M):
                fast=all(mask[xres%p] for p,mask in zip(ps,masks))
                assert fast==(xres in membership),(n,M,xres)
                exact_agreements+=1
        print("N",n,"M",M,"new roots",x["exact_square_root_tests"],
              "candidate x",x["scanned_midpoint_positions"],
              "total_time",new[str(M)]["median_total_seconds"],flush=True)
    plain_count=plain["first_original"]["exact_square_root_tests"]
    q=kernel.wheel210_factor(n)
    l=kernel.lfk_factor(n)
    assert list(q.factors)==expected and list(l.factors)==expected
    wheel_time=time_runs(lambda:dict(factors=list(kernel.wheel210_factor(n).factors),
                                     total_seconds=kernel.wheel210_factor(n).elapsed_seconds))
    # The timing above invokes wheel twice per repeat; replace with a single
    # actual call per repeat in the production timing below.
    wheel_time=time_runs(lambda:single_baseline(kernel.wheel210_factor,n))
    lfk_time=time_runs(lambda:single_baseline(kernel.lfk_factor,n))
    assert wheel_time["first_original"]["factors"]==expected
    assert lfk_time["first_original"]["factors"]==expected
    previous_12=qr.fast_public_midpoint_factor(n,qr.WHEELS[15015],WINDOW,max_square_tests=12)
    previously_missed=previous_12["factors"] is None
    return dict(N=n,verified_factors=expected,
        old_12_allowed_square_test_cap_reaches_factor=not previously_missed,
        old_12_allowed_square_test_cap=previous_12,
        full_fermat=plain,
        previous_v2_midpoint_jump=old,
        restored_public_QR_midpoint_sieve=new,
        fair_classical_baselines=dict(conventional_wheel210=wheel_time,
            original_PTP_LFK_kernel=lfk_time,
            conventional_wheel_divisibility_tests=q.divisibility_tests,
            PTP_LFK_integer_search_steps=l.integer_search_steps),
        exact_modular_residue_equivalence_checks=exact_agreements,
        square_test_reduction_over_plain={str(M):plain_count/new[str(M)]["first_original"]["exact_square_root_tests"] for M in WHEELS},
        optimized_255255_faster_than_wheel210_in_runner=(
            new["255255"]["median_total_seconds"]<wheel_time["median_total_seconds"]),
        optimized_255255_faster_than_LFK_in_runner=(
            new["255255"]["median_total_seconds"]<lfk_time["median_total_seconds"]))


def single_baseline(func,n):
    value=func(n)
    return dict(factors=list(value.factors) if value.factors else None,
                total_seconds=value.elapsed_seconds)


def main():
    manifest=json.loads(ORIGINAL.read_text())
    frozen=manifest["selected_public_rows"]
    assert manifest["selected_sha256"]==SHA
    assert len(frozen)==12 and len({x["N"] for x in frozen})==12
    assert manifest["no_prime_factors_or_orders_used_for_selection"]
    rows=[]
    for i,spec in enumerate(frozen):
        original=json.loads((ROOT/f"unified_n26_original_{i:02d}.json").read_text())
        assert original["complete"] and original["frozen_manifest_sha256"]==SHA
        assert original["index"]==i and original["QPU_jobs"]==0
        source=original["rows"][0]
        assert source["frozen_public"]==spec
        truth=source["validation_only_original_synthetic_factors"]
        n=spec["N"]
        assert math.prod(truth)==n
        data=record(n,truth)
        data["original_index"]=i
        data["public_frozen_base"]=spec["base"]
        data["original_classical_first_method"]=source["classical_first_method"]
        data["original_classically_solved_in_12_square_root_gate"]=source["classical_first_solved"]
        rows.append(data)
        print("PASS original",i,n,"pruned M15015 sqrt",
              data["restored_public_QR_midpoint_sieve"]["15015"]["first_original"]["exact_square_root_tests"],
              "full root",data["full_fermat"]["first_original"]["exact_square_root_tests"],flush=True)
    assert len(rows)==12
    special=next(x for x in rows if x["N"]==49273331)
    assert not special["original_classically_solved_in_12_square_root_gate"]
    assert special["verified_factors"]==[4703,10477]
    assert special["full_fermat"]["first_original"]["exact_square_root_tests"]==571
    assert special["restored_public_QR_midpoint_sieve"]["105"]["first_original"]["exact_square_root_tests"]==64
    assert special["restored_public_QR_midpoint_sieve"]["15015"]["first_original"]["exact_square_root_tests"]==14
    assert special["restored_public_QR_midpoint_sieve"]["255255"]["first_original"]["exact_square_root_tests"]==8
    assert not special["old_12_allowed_square_test_cap_reaches_factor"]
    all_agreements=sum(x["exact_modular_residue_equivalence_checks"] for x in rows)
    summary=dict(total_frozen_cases=len(rows),
        all_original_N_factored_by_every_safe_pruning_variant=True,
        no_false_pruning_or_valid_factor_loss=True,
        exhaustively_identical_old_table_vs_new_QR_mask_residues=all_agreements,
        original_12_square_cap_only_classical_survivor_recovered_by_restored_pruning=True,
        classical_real_factor_work_remaining_on_original_12_after_restoring_pruner=0,
        N49273331_ordinary_fermat_exact_square_tests=571,
        N49273331_original_M15015_full_square_tests=14,
        N49273331_new_M255255_full_square_tests=8,
        median_M15015_square_test_reduction=statistics.median(x["square_test_reduction_over_plain"]["15015"] for x in rows),
        median_M255255_square_test_reduction=statistics.median(x["square_test_reduction_over_plain"]["255255"] for x in rows),
        optimized_M255255_end_to_end_faster_than_wheel210_cases=sum(x["optimized_255255_faster_than_wheel210_in_runner"] for x in rows),
        optimized_M255255_end_to_end_faster_than_LFK_cases=sum(x["optimized_255255_faster_than_LFK_in_runner"] for x in rows),
        end_to_end_speed_gate_pass=False)
    summary["end_to_end_speed_gate_pass"]=(summary["optimized_M255255_end_to_end_faster_than_wheel210_cases"]>=7
        and summary["optimized_M255255_end_to_end_faster_than_LFK_cases"]>=7)
    out=dict(experiment="N26_original_PTP_midpoint_pruning_reintegration_exact_reaudit",
        protocol=PROTOCOL,original_frozen_public_manifest_sha256=SHA,
        scope="post_hoc_secondary_classical_evaluation_not_new_holdout",
        complete=True,zero_QPU=True,paid_runtime_used=False,
        finite_shared_midpoint_search_span=WINDOW, repetitions=REPS,
        measured_time_caveat="noisy CPU microbenchmarks; prime-only lookup cache and per-public-N masks reused when warm; setup included per call; compare operations and wall time separately",
        summary=summary,cases=rows,analyzed_utc=datetime.now(timezone.utc).isoformat())
    DEST.write_text(json.dumps(out,indent=2)+"\n")
    print("COMPLETE",json.dumps(summary,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
