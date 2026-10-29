#!/usr/bin/env python3
"""SECONDARY SAME-COHORT N28 ablation: public router vs identical Brent alone.

Original prospective 16-case PASS preserved unchanged. CPU only, zero IBM.
"""
import hashlib,json,math,statistics,time
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
from integrations.darkstar_hybrid import darkstar_public_cost_router as policy
from simulation.ptp_hybrid import kernel

ROOT=Path("results/dark_star_unified")
MAN=ROOT/"darkstar_public_router_n28_frozen_manifest.json"
OLD=ROOT/"darkstar_public_router_n28_original_16_holdout.json"
OUT=ROOT/"darkstar_n28_posthoc_router_vs_brent_control.json"
SHA="9f8cd1d83b3bcfdfce9c41ceda05621b52c9e9076d7cdc2dec36bc24598b7a51"
ROUNDS=8
METHODS=("router","standalone_same_Brent","wheel210")

def brent_standalone(n):
    begin=time.perf_counter()
    ops=Counter()
    steps=[]
    for p in (2,3,5,7):
        ops["divisibility_tests"]+=1
        if n%p==0:
            f=policy.factors_of(p,n)
            if f:
                steps.append(dict(stage="small_base_prime",prime=p))
                return dict(factors=f,method="small_base_prime",ops=dict(ops),stages=steps,
                    internal_seconds=time.perf_counter()-begin)
    for c,seed,cap in policy.RHO_SQUARING_BUDGETS:
        z=policy.brent_attempt(n,c,seed,cap,policy.RHO_BLOCK)
        steps.append(dict(stage="same_public_Brent",c=c,seed=seed,cap=cap,details=z))
        for k,v in z["ops"].items():
            ops["rho_"+k]+=v
        if z["factors"]:
            return dict(factors=z["factors"],method="same_public_Brent",ops=dict(ops),stages=steps,
                internal_seconds=time.perf_counter()-begin)
    full=kernel.wheel210_factor(n)
    ops["fallback_wheel210_divisions"]+=full.divisibility_tests
    steps.append(dict(stage="complete_wheel210",source=full.to_dict()))
    return dict(factors=list(full.factors) if full.factors else None,
        method="complete_wheel210",ops=dict(ops),stages=steps,
        internal_seconds=time.perf_counter()-begin)

def call(name,n):
    if name=="router":return policy.public_router(n)
    if name=="standalone_same_Brent":return brent_standalone(n)
    if name=="wheel210":return kernel.wheel210_factor(n).to_dict()
    raise AssertionError(name)

def main():
    frozen=json.loads(MAN.read_text())
    original=json.loads(OLD.read_text())
    rs=frozen["selected_public_rows"]
    assert len(rs)==len(original["original_cases"])==16
    assert frozen["row_canonical_sha256"]==original["source_manifest_sha256"]==SHA
    assert original["summary"]["primary_end_to_end_two_baseline_speed_gate_pass"]
    assert frozen["router_source_git_blob_SHA"]==original["policy_source_git_blob"]=="4420a5d5d83869ccc41ab2396cde15d84f98a4c1"
    rows=[]
    for i,fr in enumerate(rs):
        n=fr["N"]
        truth=original["original_cases"][i]["validation_only_synthetic_pq"]
        assert n==original["original_cases"][i]["frozen_public_N"]==math.prod(truth)
        raw={name:[] for name in METHODS}
        originals={}
        ordering=[]
        for repeat in range(ROUNDS):
            ordered=METHODS[repeat%3:]+METHODS[:repeat%3]
            ordering.append(list(ordered))
            for name in ordered:
                t0=time.perf_counter()
                z=call(name,n)
                wall=time.perf_counter()-t0
                assert z["factors"]==truth,(n,name,z["factors"],truth)
                raw[name].append(wall)
                if name not in originals:
                    originals[name]=z
                else:
                    assert originals[name]["factors"]==z["factors"]
                    if name=="router":
                        assert originals[name]["method"]==z["method"]
                    if name=="standalone_same_Brent":
                        assert originals[name]["method"]==z["method"] and originals[name]["ops"]==z["ops"]
        assert all(len(raw[name])==ROUNDS for name in METHODS)
        timings={name:dict(all_original_seconds=raw[name],median_seconds=statistics.median(raw[name]),
            min_seconds=min(raw[name]),max_seconds=max(raw[name])) for name in METHODS}
        faster=timings["router"]["median_seconds"]<timings["standalone_same_Brent"]["median_seconds"]
        standalone_rho=originals["standalone_same_Brent"]["method"]=="same_public_Brent"
        assert originals["standalone_same_Brent"]["ops"].get("rho_modular_squarings",0)<=384
        rows.append(dict(index=i,N=n,original_public_selection=fr,
            original_prereg_report_preserved_unchanged=True,
            original_correct_factors=truth,
            standalone_Brent_factorization=originals["standalone_same_Brent"],
            public_router_factorization=originals["router"],
            complete_wheel210=originals["wheel210"],
            original_method_invocation_orders=ordering,
            all_source_timings=timings,router_faster_than_same_Brent=faster,
            standalone_rho_reached_factor=standalone_rho,
            ratio_router_over_same_Brent=timings["router"]["median_seconds"]/timings["standalone_same_Brent"]["median_seconds"],
            no_private_factors_in_public_method=True))
        print("POSTHOC",i,n,"same Brent",originals["standalone_same_Brent"]["method"],
            "router",originals["router"]["method"],"ratio",rows[-1]["ratio_router_over_same_Brent"],
            "router faster",faster,flush=True)
    nwin=sum(x["router_faster_than_same_Brent"] for x in rows)
    summary=dict(original_case_count=16,
        same_budget_standalone_brent_successful_factors=16,
        original_public_router_successful_factors=16,
        standalone_Brent_found_factor_before_wheel=sum(x["standalone_rho_reached_factor"] for x in rows),
        router_faster_than_standalone_Brent_in_cases=nwin,
        prereg_secondary_required_minimum=9,
        incremental_router_speed_gate_pass=nwin>=9,
        median_router_to_same_Brent_runtime_ratio=statistics.median(x["ratio_router_over_same_Brent"] for x in rows),
        cannot_claim_any_quantum_or_asymptotic_advantage=True)
    result=dict(experiment="N28_post_hoc_same_cohort_router_vs_exact_same_Brent_baseline",
        protocol="docs/DARK_STAR_N28_ROUTER_VS_STANDALONE_BRENT_SECONDARY_PROTOCOL.md",
        original_N28_public_SHA=SHA, original_original_gate_preserved=True,
        separate_post_hoc_mechanism_audit=True,complete=True,
        original_cases=rows,summary=summary,
        zero_QPU=True,paid_runtime_used=False,
        result_caveat="post-hoc same cohort, not fresh independent 16-case holdout; Python timing cannot establish implementation-independent improvement; original primary wheel/LFK PASS remains unaffected",
        timestamp_utc=datetime.now(timezone.utc).isoformat())
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print("SECONDARY COMPLETE",json.dumps(summary),flush=True)

if __name__=="__main__":
    main()
