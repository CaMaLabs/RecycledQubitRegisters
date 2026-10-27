#!/usr/bin/env python3
"""Frozen post-hoc source CCX break-even thresholds for all eight N25 cases.
Lead: Chase Lunsford / CaMaLabs. ZERO IBM QPU, ZERO paid/free runtime.
This does not simulate QPE or claim a probability advantage.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from fractions import Fraction
from pathlib import Path
import json,math

ROOT=Path("results/dark_star_ptp")
ORIGINAL=ROOT/"dark_star_n25_online_model_all_8.json"
EXACT=ROOT/"dark_star_n25_exact_order_dominance.json"
PREFIX=ROOT/"dark_star_n25_prefix_dominance.json"
OUTPUT=ROOT/"dark_star_n25_changed_order_break_even.json"
PROTOCOL="docs/DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_PROTOCOL.md"
SHA="66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
WIDTHS=tuple(range(4,51,2))
SHOTS_PER_WIDTH=4
FACTOR_CAPABLE_REDUCED={(20508127,3),(24467873,3),(28064303,13)}
FACTOR_INCAPABLE_REDUCED={(29256449,5)}


def exact_ratio(x:Fraction)->dict:
    return dict(numerator=x.numerator,denominator=x.denominator,decimal=float(x))


def evaluate_case(i,source,exact,previous):
    n=int(source["N"]);a=int(source["base"]);b=int(source["cube"])
    assert a>1 and n>2 and math.gcd(a,n)==1
    assert b==pow(a,3,n)
    assert exact["index"]==previous["index"]==i
    assert exact["N"]==previous["N"]==n
    assert exact["base"]==previous["base"]==a
    r=int(source["validation_only"]["order_plain"])
    rc=int(source["validation_only"]["order_cube"])
    assert rc==r//math.gcd(3,r)
    assert exact["exact_orders"]==dict(plain=r,cube=rc,equal=(r==rc))
    assert previous["order_plain"]==r and previous["order_cube"]==rc
    assert exact["original_model_status"]==previous["original_n25_status"]==source["cube_vs_plain"]["status"]
    assert source["zero_QPU"] is True
    capable=source["validation_only"]["factor_capable"]
    assert exact["factor_incapable_for_both_exact"] is (not capable)
    assert previous["factor_capable"] is capable
    pair=(n,a)
    if r!=rc and capable:
        assert pair in FACTOR_CAPABLE_REDUCED
        category="changed_order_factor_capable_break_even_only"
    elif r!=rc:
        assert pair in FACTOR_INCAPABLE_REDUCED
        category="changed_order_factor_incapable_undefined"
    else:
        category="same_order_control_only"
        assert pair not in FACTOR_CAPABLE_REDUCED|FACTOR_INCAPABLE_REDUCED
    p=source["model_plain"]["structural_modular_arithmetic_per_stage"]
    c=source["model_cube"]["structural_modular_arithmetic_per_stage"]
    assert len(p)==len(c)==len(WIDTHS)==24
    stages=[]
    flat_plain=[];flat_cube=[]
    for m,pp,cc in zip(WIDTHS,p,c):
        assert pp["m"]==cc["m"]==m
        v=int(pp["ccx"]);w=int(cc["ccx"])
        assert type(pp["ccx"]) is type(cc["ccx"]) is int
        assert v>0 and w>=0
        stage_ratio=Fraction(w,v)
        stages.append(dict(phase_bits=m,ccx_plain_per_shot=v,
           ccx_cube_per_shot=w,delta_ccx_cube_minus_plain=w-v,
           fixed_width_per_shot_cube_over_plain=exact_ratio(stage_ratio),
           hypothetical_per_trial_success_ratio_must_exceed=(
               exact_ratio(stage_ratio) if capable else None),
           strict_cube_cheaper_source_ccx=(w<v),
           note="This threshold compares independent fixed-width repeated trials only; verifier CPU work excluded. It is not observed success probability."))
        flat_plain.extend([v]*SHOTS_PER_WIDTH)
        flat_cube.extend([w]*SHOTS_PER_WIDTH)
    assert len(flat_plain)==len(flat_cube)==96

    # Independent cross-check: O(96) shot expansion versus stage weighted
    # prefix sum (complete stages + j/4 shots of the current stage).
    cumulative_plain=cumulative_cube=0
    prefixes=[]
    for k,(vp,vc) in enumerate(zip(flat_plain,flat_cube),1):
        cumulative_plain+=vp;cumulative_cube+=vc
        widthindex=(k-1)//SHOTS_PER_WIDTH
        completed=k//SHOTS_PER_WIDTH
        partial=k%SHOTS_PER_WIDTH
        expected_p=sum(SHOTS_PER_WIDTH*z["ccx_plain_per_shot"] for z in stages[:completed])
        expected_c=sum(SHOTS_PER_WIDTH*z["ccx_cube_per_shot"] for z in stages[:completed])
        if partial:
            expected_p+=partial*stages[completed]["ccx_plain_per_shot"]
            expected_c+=partial*stages[completed]["ccx_cube_per_shot"]
        assert cumulative_plain==expected_p and cumulative_cube==expected_c,(n,a,k)
        z=Fraction(cumulative_cube,cumulative_plain)
        prefixes.append(dict(fixed_workload_shots=k,
           width=WIDTHS[widthindex],shot_within_width=(k-1)%4+1,
           cumulative_plain_CCX=cumulative_plain,
           cumulative_cube_CCX=cumulative_cube,
           cumulative_cube_minus_plain_CCX=cumulative_cube-cumulative_plain,
           fixed_prefix_cost_ratio=exact_ratio(z),
           IMPORTANT_not_early_stopping_per_success_ratio=True))
    ratios=[Fraction(z["fixed_prefix_cost_ratio"]["numerator"],z["fixed_prefix_cost_ratio"]["denominator"]) for z in prefixes]
    minratio=min(ratios);maxratio=max(ratios)
    cheaper=sum(z["strict_cube_cheaper_source_ccx"] for z in stages)
    prefix_less=sum(z["cumulative_cube_minus_plain_CCX"]<0 for z in prefixes)
    prefix_equal=sum(z["cumulative_cube_minus_plain_CCX"]==0 for z in prefixes)
    if r==rc:
        assert previous["shot_prefixes_evaluated"]==96
        assert previous["min_ratio"] is not None
        if previous["every_prefix_cube_more_expensive"]:
            assert minratio>1 and prefix_less==prefix_equal==0
        f=previous["exact_min_ratio_fraction"]
        assert Fraction(f[0],f[1])==minratio
    else:
        assert previous["verdict"]=="not_applicable_order_reduced"
        assert previous["shot_prefixes_evaluated"]==0
    return dict(index=i,N=n,base=a,cube=b,validation_only_order_plain=r,
         validation_only_order_cube=rc,order_reduces=(r!=rc),
         validation_only_factor_capable=capable,
         analysis_category=category,original_primary_status=source["cube_vs_plain"]["status"],
         original_same_order_prefix_verdict=previous["verdict"],
         stage_width_count=len(stages),fixed_prefix_shots=len(prefixes),
         cube_strictly_cheaper_at_stage_count=cheaper,
         cube_strictly_dearer_at_stage_count=sum(z["delta_ccx_cube_minus_plain"]>0 for z in stages),
         fixed_prefix_cheaper_count=prefix_less,
         fixed_prefix_equal_count=prefix_equal,
         fixed_prefix_dearer_count=96-prefix_less-prefix_equal,
         minimum_fixed_prefix_cost_ratio=exact_ratio(minratio),
         minimum_ratio_shot=ratios.index(minratio)+1,
         maximum_fixed_prefix_cost_ratio=exact_ratio(maxratio),
         maximum_ratio_shot=ratios.index(maxratio)+1,
         final_96_shot_cost_ratio=prefixes[-1]["fixed_prefix_cost_ratio"],
         factor_success_cost_ratio_defined_for_this_base_pair=bool(capable),
         observed_success_probability_ratio=None,
         inferred_cube_factor_success_win=None,
         fixed_width_independent_shot_break_even_thresholds=stages,
         fixed_workload_stopping_prefixes=prefixes,
         caveat="Post-hoc source CCX-only cost ratio; unequal orders prevent common stopping-time coupling. Fixed-workload prefix ratio is not an adaptive QPE per-factor ratio.")


def main():
    orig=json.loads(ORIGINAL.read_text())
    audit=json.loads(EXACT.read_text())
    previous=json.loads(PREFIX.read_text())
    assert orig["source_manifest_sha256"]==audit["original_manifest_sha256"]==previous["manifest_sha256"]==SHA
    assert orig["complete"] and orig["summary"]["total"]==audit["result_count"]==previous["summary"]["total"]==8
    assert orig["summary"]["bounded_win"]==orig["summary"]["bounded_loss"]==0
    assert orig["summary"]["model_statuses"]==dict(inconclusive=6,factor_incapable_or_uncertified=2)
    assert orig["zero_QPU"] and audit["zero_QPU"] and previous["zero_QPU"]
    assert orig["qpu_jobs_submitted"]==audit["qpu_jobs_submitted"]==previous["qpu_jobs_submitted"]==0
    assert not orig["paid_runtime_used"] and not audit["paid_runtime_used"] and not previous["paid_runtime_used"]
    assert len(orig["rows"])==len(audit["cases"])==len(previous["cases"])==8
    rows=[evaluate_case(i,x,y,z) for i,(x,y,z) in
          enumerate(zip(orig["rows"],audit["cases"],previous["cases"]))]
    categories=Counter(x["analysis_category"] for x in rows)
    assert categories==Counter(dict(
      changed_order_factor_capable_break_even_only=3,
      changed_order_factor_incapable_undefined=1,
      same_order_control_only=4))
    assert { (x["N"],x["base"]) for x in rows if x["analysis_category"]=="changed_order_factor_capable_break_even_only"}==FACTOR_CAPABLE_REDUCED
    assert all(x["inferred_cube_factor_success_win"] is None for x in rows)
    result=dict(experiment="dark_star_n25_fixed_cost_break_even_secondary",
       research_lead="Chase Lunsford / CaMaLabs",
       utc=datetime.now(timezone.utc).isoformat(),
       preregistration=PROTOCOL,source_manifest_sha256=SHA,
       original_primary_status=dict(orig["summary"]),
       original_scientific_receipts_unchanged=True,
       analysis_scope="post_hoc_same_N25_cohort_eight_cases",
       independent_cohort_replication=False,
       native_IBM_transpilation=False,quantum_hardware_executed=False,
       source_level_CCX_only=True,
       summary=dict(total=8,categories=dict(categories),
          order_reducing_factor_capable=3,
          extra_positive_success_claims=0,
          crosscheck_exact_96_prefix_per_case=True,
          old_preregistered_results_unchanged=True,
          no_QPU=True),
       all_cases=rows,
       warning="For order-changing cases neither QPE outcome probabilities nor adaptive stopping time distributions coincide. Break-even fixed-width thresholds are CONDITIONAL, not observed success. The 96-shot fixed workload ratio must not be labeled per-factor cost advantage.",
       zero_QPU=True,qpu_jobs_submitted=0,paid_runtime_used=False)
    OUTPUT.write_text(json.dumps(result,indent=2)+"\n")
    for x in rows:
        print("ROW",x["index"],x["N"],x["base"],
              x["analysis_category"],"cube cheaper stages",x["cube_strictly_cheaper_at_stage_count"],
              "96-shot fixed ratio",x["final_96_shot_cost_ratio"]["decimal"],flush=True)
    print("SUCCESS: all eight original N25 rows audited; conditional targets not wins; zero QPU",flush=True)


if __name__=="__main__":
    main()
