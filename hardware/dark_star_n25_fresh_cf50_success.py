#!/usr/bin/env python3
"""Fresh SHA-frozen four N25 public classical survivors: ideal QPE m50 success.

Research lead Chase Lunsford / CaMaLabs. Pure CPU, zero IBM QPU/Runtime.
Post-manifest exact validation orders are used ONLY to generate simulated
QPE outcomes. The public ON-DEMAND CF/GCD factor verifier knows only
(measured_y,Q,base,N), and operation counts are metered separately.
All four previously unseen rows stay in the outputs; no postselection.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from fractions import Fraction
from pathlib import Path
import hashlib
import json
import math
import time
import traceback

import dark_star_n25_online_qpe_arithmetic as old
import dark_star_n25_online_public_manifest as earlier
import dark_star_recycled_scalable_arithmetic_audit as gates

REV="dark-star-n25-fresh-frozen-online-cf50-v1-20261028"
PROTOCOL="docs/DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_PROTOCOL.md"
MANIFEST=Path("results/dark_star_ptp/dark_star_n25_fresh_cf50_manifest.json")
FROZEN_SHA="a136789dcdcbb32730f293973805f8edacf5d684d8350c2e51c665db0099d629"
ORIGINAL_SHA="66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
SAMPLE_COUNT=16384
M=50
Q=1<<M
ALPHA=.01
FAMILY=8 # exactly four cases x two public bases at one fixed width
EPS=math.sqrt(math.log(2*FAMILY/ALPHA)/(2*SAMPLE_COUNT))
TAIL_WORST=1/63
COUPLED_SALT="QRR-N25-CF50-FRESH-PHASE-20261028"
OUTPUT_PREFIX="n25_fresh_cf50_index"

def read_locked_public():
    j=json.loads(MANIFEST.read_text())
    rows=j["selected_public_rows"]
    calculated=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    assert j["selected_sha256"]==FROZEN_SHA==calculated
    assert j["original_eight_selected_sha256"]==ORIGINAL_SHA
    assert j["revision"]=="dark-star-n25-fresh-public-b47-rho64-survivors-v1-20261028"
    assert j["preregistration"]==PROTOCOL
    assert j["secret_factor_or_validation_order_not_used_in_public_selection"]
    assert j["no_QPE_or_factor_witness_scored_during_selection"]
    assert j["public_only_B31_and_B47_rho64_trial97_screening"]
    assert j["zero_QPU"] and j["qpu_jobs_submitted"]==0
    assert len(rows)==4 and len({r["N"] for r in rows})==4
    assert not set(j["original_eight_N_excluded"]).intersection(r["N"] for r in rows)
    for row in rows:
        n=row["N"];a=row["base"]
        assert row["unsolved_by_fixed_public_B31_B47_rho64_trial97"]
        assert row["cube"]==pow(a,3,n) and math.gcd(a,n)==1
        checked=next(v for v in j["public_screenings"][row["group"]] if v["N"]==n)
        assert not checked["B31_factored"] and not checked["additional_B47_rho64_trial97"]["classically_solved"]
    return j


def ratio(value:Fraction):
    return dict(numerator=value.numerator,denominator=value.denominator,
                decimal=float(value))


def arm(n,base,order,uniforms,cache):
    # Reuse original verified 65-bin centered ideal phase sampler / public
    # online CF/GCD validation, but with NEW 16384 count and NEW public salt.
    s=old.stage(n,base,order,M,uniforms)
    assert s["m"]==M and s["sample_count"]==SAMPLE_COUNT
    assert s["online_CF_denominators_checked"]>=0
    assert s["online_modpow_calls"]>=0 and s["online_gcd_calls"]>=0
    assert s["tail_mass_mean"]<=TAIL_WORST+1e-6
    accepted=s["head_accepted_count"]
    assert 0<=accepted<=SAMPLE_COUNT
    h=accepted/SAMPLE_COUNT
    lower=max(0.,h-EPS)
    upper=min(1.,h+EPS+TAIL_WORST)
    assert 0<=lower<=upper<=1
    source=gates.stage_arithmetic_count(n,base,M,cache)
    ccx=int(source["ccx"]);cx=int(source["cx"]);swaps=int(source["cswap"])
    assert ccx>0 and cx>=0 and swaps>=0
    return dict(base=base,
        head_sample_count=SAMPLE_COUNT,
        head_factor_success_count=int(accepted),
        head_success_probability_empirical=h,
        overall_ideal_success_interval_with_omitted_tail=[lower,upper],
        nominal_simultaneous_hoeffding_eps=EPS,
        omitted_tail_conservative_upper_bound=TAIL_WORST,
        observed_mean_omitted_mass=s["tail_mass_mean"],
        observed_sampler_tail_events=int(s["tail_events"]),
        on_demand_public_verifier_ops=dict(
            denominator_checks=int(s["online_CF_denominators_checked"]),
            modular_exponentiation_calls=int(s["online_modpow_calls"]),
            gcd_calls=int(s["online_gcd_calls"])),
        source_arithmetic=dict(ccx=ccx,cx=cx,controlled_swaps=swaps),
        true_order_used_only_by_ideal_phase_sampler=True,
        no_precomputed_denominator_producing_table=True)


def compare(plain,cube,capable):
    cp=int(plain["source_arithmetic"]["ccx"])
    cc=int(cube["source_arithmetic"]["ccx"])
    cr=Fraction(cc,cp)
    pl,ph=plain["overall_ideal_success_interval_with_omitted_tail"]
    cl,ch=cube["overall_ideal_success_interval_with_omitted_tail"]
    hp=plain["head_success_probability_empirical"]
    hc=cube["head_success_probability_empirical"]
    ratio_est=(hc/hp if hp>0 else None)
    ratio_lo=cl/ph if ph>0 else None
    ratio_hi=ch/pl if pl>0 else None
    if not capable:
        status="factor_incapable_undefined"
    elif ratio_lo is not None and ratio_lo>float(cr):
        status="bounded_cube_win"
    elif ratio_hi is not None and ratio_hi<float(cr):
        status="bounded_cube_loss"
    else:
        status="inconclusive"
    expected_cost_lo_plain=cp/ph if ph>0 else None
    expected_cost_hi_plain=cp/pl if pl>0 else None
    expected_cost_lo_cube=cc/ch if ch>0 else None
    expected_cost_hi_cube=cc/cl if cl>0 else None
    return dict(status=status,
        source_ccx_cube_over_plain_break_even_ratio=ratio(cr),
        direct_fixed_width_head_success_ratio_cube_over_plain=ratio_est,
        conservative_ideal_success_ratio_interval_cube_over_plain=[ratio_lo,ratio_hi],
        expected_source_CCX_per_success_intervals=dict(
           plain=[expected_cost_lo_plain,expected_cost_hi_plain],
           cube=[expected_cost_lo_cube,expected_cost_hi_cube]),
        source_ccx_delta_cube_minus_plain=cc-cp,
        factor_capable_validated_after_public_freeze=bool(capable),
        realized_probabilities_not_claimed_to_be_actual_quantum_hardware=True,
        fixed_width_only_no_adaptive_cost_claim=True)


def score(index):
    manifest=read_locked_public()
    spec=manifest["selected_public_rows"][index]
    n,a,b=int(spec["N"]),int(spec["base"]),int(spec["cube"])
    old.SAMPLES=SAMPLE_COUNT
    old.SEED=COUPLED_SALT
    # Explicit original selftest includes all short measured y and their
    # original public on-demand CF proper-factor behavior equivalence.
    started=time.process_time()
    tests=old.selftest()
    assert tests["online_CF_matches_legacy_direct_public_factor_extractor"]==1680
    # Post-manifest-only independent classical validation factors/orders.
    p,q=old.validation_factors(n)
    assert p*q==n and p!=q
    lam=math.lcm(p-1,q-1)
    r=gates.multiplicative_order_from_lambda(a,n,lam)
    rb=gates.multiplicative_order_from_lambda(b,n,lam)
    assert rb==r//math.gcd(r,3)
    witness_a=gates.factor_witness(a,r,n)
    witness_b=gates.factor_witness(b,rb,n)
    assert witness_a["factor_success"]==witness_b["factor_success"]
    assert witness_a["factors"]==witness_b["factors"]
    common=old.common_uniforms(n,M)
    assert len(common[0])==len(common[1])==SAMPLE_COUNT
    cache={}
    plain=arm(n,a,r,common,cache)
    cube=arm(n,b,rb,common,cache)
    result=compare(plain,cube,bool(witness_a["factor_success"]))
    assert result["source_ccx_cube_over_plain_break_even_ratio"]["numerator"]>0
    row=dict(selected_index=index,**spec,
        original_manifest_sha256=FROZEN_SHA,
        frozen_public_classical_budget_ledger=next(
           z for z in manifest["public_screenings"][spec["group"]] if z["N"]==n),
        validation_only=dict(prime_factors=[p,q],
            order_plain=r,order_cube=rb,
            order_cube_div3_identity=True,
            witness_plain=witness_a,
            witness_cube=witness_b,
            half_power_witness_invariant=True),
        plain=plain,cube_arm=cube,comparison=result,
        cpu_process_seconds=round(time.process_time()-started,5),
        quantum_runtime_used=False,paid_runtime_used=False)
    print("FRESH CF50 N25 RESULT",index,n,a,
        "orders only after freeze",r,"->",rb,
        "factor-capable",witness_a["factor_success"],
        "HEAD counts",plain["head_factor_success_count"],cube["head_factor_success_count"],
        "CCX cost",plain["source_arithmetic"]["ccx"],cube["source_arithmetic"]["ccx"],
        "status",result["status"],"CPU seconds",row["cpu_process_seconds"],
        "NO QPU",flush=True)
    return row,tests


def main(index):
    p=Path(f"{OUTPUT_PREFIX}{index:02d}.json")
    result=dict(revision=REV,
      research_lead="Chase Lunsford / CaMaLabs",
      preregistration=PROTOCOL,manifest_sha256=FROZEN_SHA,
      selected_index=index,
      fixed_public_n25_cohort=True,
      fixed_phase_bits=M,head_samples_per_base=SAMPLE_COUNT,
      sampling_salt=COUPLED_SALT,
      simultaneous_nominal_alpha=ALPHA,family_size=FAMILY,
      minimum_model_tail_worst_bound=TAIL_WORST,
      phase_sampler_uses_validation_only_order=True,
      measured_outcome_verifier_is_public_only=True,
      source_CCX_not_native_CZ=True,
      qpu_jobs_submitted=0,zero_QPU=True,paid_runtime_used=False,
      result_complete=False,status="STARTED")
    def save():p.write_text(json.dumps(result,indent=2)+"\n")
    save()
    try:
        row,tests=score(index)
        result.update(result_complete=True,status="SUCCESS",
                      selftests=tests,row=row,
                      completed_utc=datetime.now(timezone.utc).isoformat())
        save()
        return 0
    except Exception as exc:
        result.update(result_complete=False,status="FAIL",
                      failure_class=type(exc).__name__,
                      failure_message=str(exc)[:1800],
                      failure_traceback=traceback.format_exc()[-3000:])
        save()
        print("FRESH N25 CF50 FAILURE",index,type(exc).__name__,
              str(exc),traceback.format_exc()[-1100:],"NO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--index",type=int,required=True,choices=range(4))
    raise SystemExit(main(parser.parse_args().index))
