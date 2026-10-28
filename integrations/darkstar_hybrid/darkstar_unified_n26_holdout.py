#!/usr/bin/env python3
"""Frozen N26 unified end-to-end PTP/classical/odd-power/ideal-QPE holdout.

Public case/base committed to main BEFORE this scoring module. Twelve shards;
eight fixed seeds per seven arms. Absolutely ZERO IBM hardware/Runtime.
"""
from __future__ import annotations
import argparse, hashlib, json, math, statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import darkstar_unified as u
from integrations.darkstar_hybrid import darkstar_unified_n26_public_manifest as pop

ROOT=Path("results/dark_star_unified")
MANIFEST=ROOT/"unified_n26_public_manifest.json"
SHA="0c25e448b646a5ade7d919ca78597c8c2883fd8fd450181dd4504c18252fb939"
PREREG="docs/DARK_STAR_UNIFIED_N26_FRESH_POPULATION_PREREG.md"
SEEDS=tuple(20261028+1009*j for j in range(8))
NROWS=12
ARMS=("L1","L3","L5","L7","L105","L1155","L15015")


def get_frozen():
    m=json.loads(MANIFEST.read_text())
    rr=m["selected_public_rows"]
    assert len(rr)==len({r["N"] for r in rr})==NROWS
    assert m["selected_sha256"]==SHA==pop.rows_hash(rr)
    assert m["no_prime_factors_or_orders_used_for_selection"]
    assert m["no_prime_factors_published_in_manifest"] and m["no_classical_budget_or_model_score_used_for_selection"]
    assert m["no_QPU"] and m["IBM_runtime_jobs"]==0
    for i,x in enumerate(rr):
        n,a=x["N"],x["base"]
        assert 1<<25<=n<1<<26
        assert x["group"]==("G1_mod3_1" if n%3==1 else "G2_mod3_2")
        assert a==pop.base_for(n,x["group"])
        assert x["public_cube"]==pow(a,3,n)
        assert x["rank"]==1+(i%6)
    return m


def simulator_only_factors(n):
    """Only used for IDEAL QPE eigenphases and synthetic truth, not public control."""
    for p in ds.primes_up_to(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q and ds.is_probable_prime(q)
            return p,q
    raise AssertionError("Frozen construction not a two-distinct-prime semiprime")


def per_arm_aggregate(replicates, label):
    all_z=[r["arms"][label] for r in replicates]
    assert len(all_z)==len(SEEDS)
    base=all_z[0]["base"]
    assert all(a["base"]==base and a["exponent"]==all_z[0]["exponent"] for a in all_z)
    shortcuts=[a for a in all_z if a["classically_shortcut"]]
    if shortcuts:
        assert len(shortcuts)==len(SEEDS) and all(a["shortcut_factors"]==shortcuts[0]["shortcut_factors"] for a in shortcuts)
        return dict(base=base, exponent=shortcuts[0]["exponent"],public_classical_shortcut=True,
            public_shortcut_factors=shortcuts[0]["shortcut_factors"],
            simulator_runs=0,simulator_factors=0,
            modeled_CCX_per_factor_success=None,mean_CCX_per_attempt=None,
            quantum_cost_not_charged=True)
    assert all(a["model_attempted"] for a in all_z)
    nsuccess=sum(a["success"] for a in all_z)
    ccx=sum(a["counterfactual_source_counts"]["source_CCX"] for a in all_z)
    shots=sum(a["shots"] for a in all_z)
    return dict(base=base,exponent=all_z[0]["exponent"],public_classical_shortcut=False,
        simulator_runs=len(SEEDS),simulator_factors=nsuccess,
        empirical_factor_success_frequency=nsuccess/len(SEEDS),
        total_source_CCX_for_all_sessions=ccx,
        modeled_CCX_per_factor_success=ccx/nsuccess if nsuccess else None,
        mean_CCX_per_attempt=ccx/len(SEEDS),
        mean_shots=shots/len(SEEDS),
        total_shots=shots,
        quantum_cost_not_charged=False,
        logical_wide_peak_max=max(a["logical_architectures"]["wide_peak_logical"] for a in all_z),
        logical_recycled_peak_max=max(a["logical_architectures"]["recycled_peak_logical"] for a in all_z),
        total_online_CF_modpow=sum(a["counterfactual_source_counts"].get("public_CF_modular_pow_calls",0) for a in all_z),
        total_online_CF_gcd=sum(a["counterfactual_source_counts"].get("public_CF_gcd_calls",0) for a in all_z),
        total_unmodeled_tail_events=sum(a["counterfactual_source_counts"].get("unmodeled_tail_events",0) for a in all_z))


def score(index):
    manifest=get_frozen()
    frozen=manifest["selected_public_rows"][index]
    n,a=frozen["N"],frozen["base"]
    print("FROZEN MANIFEST",SHA,"index",index,"N",n,"public base",a,flush=True)
    # Validation-only synthetic factors recovered AFTER immutable public SHA freeze.
    p,q=simulator_only_factors(n)
    print("Validation ONLY factors OK; never used for public selection",flush=True)
    first=u.run_synthetic_case(p,q,base=a,seed=SEEDS[0],fermat_tests=12)
    assert first["N"]==n and first["public_base"]==a
    assert first["safety"]["uses_QPU"] is False and first["safety"]["IBM_runtime_jobs"]==0
    assert first["actual_classical_first_outcome"]["factors"] in ([p,q],None)
    assert first["public_conditional_odd_exponent"]==(3 if n%3==2 else 1)
    assert set(first["all_fixed_exponent_ablation_arms"])==set(ARMS)
    reps=[dict(seed=SEEDS[0],arms=first["all_fixed_exponent_ablation_arms"])]
    shared_gate_cache={}
    # Reuse public modular arithmetic source construction across ALL 7 arms and seeds.
    for seed in SEEDS[1:]:
        arms={}
        for exponent in u.ODD_EXPONENTS:
            z=u.run_quantum_counterfactual(n,p,q,a,exponent,seed,gate_cache=shared_gate_cache)
            assert z["label"]=="L"+str(exponent)
            assert z["base"]==pow(a,exponent,n)
            if z.get("factors"):
                assert z["factors"]==[p,q]
            if z["classically_shortcut"]:
                assert z["shortcut_factors"]==[p,q]
            arms[z["label"]]=z
        reps.append(dict(seed=seed,arms=arms))
    assert [r["seed"] for r in reps]==list(SEEDS)
    aggregated={label:per_arm_aggregate(reps,label) for label in ARMS}
    assert set(aggregated)==set(ARMS)
    chosen="L3" if n%3==2 else "L1"
    assert first["actual_classical_first_outcome"]["publicly_fixed_odd_power_fallback_priority"][0]==int(chosen[1:])
    if first["actual_classical_first_outcome"]["success"]:
        assert first["actual_classical_first_outcome"]["factors"]==[p,q]
    valid_baselines=first["classical_full_reference_baselines"]
    assert all(valid_baselines[k]["factors"]==[p,q] for k in ("trial","conventional_wheel210","ptp_LFK_kernel"))
    classical=first["public_classical_preflight"]
    wheel_tests=valid_baselines["conventional_wheel210"]["divisibility_tests"]
    kernel_work=valid_baselines["ptp_LFK_kernel"]["integer_search_steps"]
    # Source-CCX counts and divisions are NOT interchangeable physical currency.
    end_to_end_practical_advantage_demonstrated=False
    row=dict(index=index,frozen_public=frozen,
        validation_only_original_synthetic_factors=[p,q],
        classical_first_solved=bool(classical["factors"]),
        classical_first_method=classical["method"],
        conventional_wheel210_divisibility_tests=wheel_tests,
        PTP_LFK_integer_steps=kernel_work,
        fixed_public_selector_arm=chosen,
        fixed_8_seed_empirical_comparisons=aggregated,
        primary_end_to_end_practical_advantage_demonstrated=end_to_end_practical_advantage_demonstrated,
        first_complete_unified_pipeline_receipt=first,
        all_eight_original_seed_receipts=reps,
        correct_ptp_factors=first["validated_PTProot_pair_after_real_factors"],
        QPU_jobs=0,paid_runtime=False)
    out=dict(experiment="dark_star_unified_fresh_n26_12_shard_cpu_only",
        preregistration=PREREG, frozen_manifest_sha256=SHA,
        index=index,complete=True,rows=[row],seeds=list(SEEDS),
        source_cost_model="reversible_clean_MCX_abstract_CCX_not_native_CZ",
        quantum_simulator="ideal_65_centered_QPE_bins_with_unmodeled_tail_as_failure",
        classical_reference_not_quantum_advantage=True,
        no_blind_retraining_or_replacement=True,
        QPU_jobs=0, paid_runtime_used=False,
        completed_utc=datetime.now(timezone.utc).isoformat())
    target=Path(f"unified_n26_row_{index:02d}.json")
    target.write_text(json.dumps(out,indent=2)+"\n")
    print("COMPLETE",index,n,"classical",classical["method"],
          "wheel_divisions",wheel_tests,"kernel_steps",kernel_work,
          "plain",aggregated["L1"].get("simulator_factors"),
          "cube",aggregated["L3"].get("simulator_factors"),
          "fixed public policy",chosen,"NO QPU",flush=True)


def merge(source):
    frozen=get_frozen()["selected_public_rows"]
    rows=[]
    for i,fr in enumerate(frozen):
        path=source/f"n26-row-{i}"/f"unified_n26_row_{i:02d}.json"
        doc=json.loads(path.read_text())
        assert doc["complete"] and doc["index"]==i and doc["frozen_manifest_sha256"]==SHA
        assert doc["QPU_jobs"]==0 and not doc["paid_runtime_used"] and doc["no_blind_retraining_or_replacement"]
        assert doc["seeds"]==list(SEEDS) and len(doc["rows"])==1
        r=doc["rows"][0]
        assert r["frozen_public"]==fr and r["index"]==i and r["QPU_jobs"]==0
        assert len(r["all_eight_original_seed_receipts"])==len(SEEDS)
        assert [x["seed"] for x in r["all_eight_original_seed_receipts"]]==list(SEEDS)
        assert set(r["fixed_8_seed_empirical_comparisons"])==set(ARMS)
        assert r["correct_ptp_factors"]
        assert r["first_complete_unified_pipeline_receipt"]["N"]==fr["N"]
        assert r["first_complete_unified_pipeline_receipt"]["public_base"]==fr["base"]
        assert r["first_complete_unified_pipeline_receipt"]["public_conditional_odd_exponent"]==(3 if fr["N"]%3==2 else 1)
        assert all((not z["model_attempted"] or len(z["stage_receipts"])<=25)
                   for session in r["all_eight_original_seed_receipts"]
                   for z in session["arms"].values())
        assert all(not z["quantum_cost_not_charged"] or z["public_classical_shortcut"]
                   for z in r["fixed_8_seed_empirical_comparisons"].values())
        assert not r["primary_end_to_end_practical_advantage_demonstrated"]
        rows.append(r)
        print("AUDIT",i,fr["N"],"classical",r["classical_first_method"],flush=True)
    solved=sum(r["classical_first_solved"] for r in rows)
    synth_summary={}
    for arm in ARMS:
        a=[r["fixed_8_seed_empirical_comparisons"][arm] for r in rows]
        synth_summary[arm]=dict(
            publicly_classically_factored_rows=sum(z["public_classical_shortcut"] for z in a),
            simulator_rows=sum(not z["public_classical_shortcut"] for z in a),
            simulator_attempts=sum(z["simulator_runs"] for z in a),
            simulator_successes=sum(z["simulator_factors"] for z in a),
            aggregate_source_CCX=sum(z.get("total_source_CCX_for_all_sessions",0) for z in a),
            empirical_source_CCX_per_success=(
                sum(z.get("total_source_CCX_for_all_sessions",0) for z in a)/
                sum(z["simulator_factors"] for z in a)
                if sum(z["simulator_factors"] for z in a)>0 else None))
    extra=dict(total_frozen_rows=12,semiprime_bitlength=26,
        classically_solved_by_unified_preflight=solved,
        not_solved_by_unified_preflight=12-solved,
        standalone_conventional_wheel_solved=sum(bool(r["first_complete_unified_pipeline_receipt"]
                                                      ["classical_full_reference_baselines"]["conventional_wheel210"]["factors"]) for r in rows),
        standalone_PTP_LFK_solved=sum(bool(r["first_complete_unified_pipeline_receipt"]
                                         ["classical_full_reference_baselines"]["ptp_LFK_kernel"]["factors"]) for r in rows),
        primary_practical_end_to_end_advantage_demonstrated=False,
        simulated_fixed_policy_ell3_for_mod3_2=6,
        simulated_fixed_policy_ell1_for_mod3_1=6,
        per_arm=synth_summary)
    # Summary deliberately omits raw seed series; all original per-case receipts remain separate.
    summary=dict(experiment="dark_star_unified_fresh_n26_original_12_verified",
        source_preregistration=PREREG,frozen_public_sha256=SHA,
        complete=True,zero_QPU=True,paid_runtime_used=False,
        original_science_shards_preserved=12,
        actual_claim="12 synthetic 26-bit semiprimes, 8 model seeds x 7 fixed arms, actual classical-first or explicit ideal-model counterfactual",
        limitations="No physical quantum advantage, no native ISA, unknown keys not attacked, small classical factoring is easy. CCX and integer divisions are incomparable resource currencies.",
        summary=extra,
        original_case_keys=[dict(index=i,N=z["N"],base=z["base"],group=z["group"]) for i,z in enumerate(frozen)])
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/"unified_n26_all_12_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    for i in range(12):
        path=source/f"n26-row-{i}"/f"unified_n26_row_{i:02d}.json"
        (ROOT/f"unified_n26_original_{i:02d}.json").write_bytes(path.read_bytes())
    print("ALL ORIGINAL 12 SCIENCE SHARDS PRESERVED, NO QPU",json.dumps(extra),flush=True)


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--index",type=int,choices=range(NROWS))
    mode.add_argument("--merge",action="store_true")
    parser.add_argument("--shards",type=Path,default=Path("n26-shards"))
    a=parser.parse_args()
    if a.merge:
        merge(a.shards)
    else:
        score(a.index)


if __name__=="__main__":
    main()
