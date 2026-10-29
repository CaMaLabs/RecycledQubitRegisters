#!/usr/bin/env python3
"""Fresh N27, SHA-frozen BEFORE score: restored classical-first and matched
wheel/PTP benchmark, plus 3 precommitted seeds plain/cube QPE counterfactual.
No QPU or IBM Runtime. Research lead Chase Lunsford / CaMaLabs.
"""
import hashlib
import json
import math
import statistics
import time
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone

from integrations.darkstar_hybrid import darkstar_unified as u
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import darkstar_unified_n27_public_manifest as population
from simulation.ptp_hybrid import kernel
from hardware import dark_star_recycled_scalable_arithmetic_audit as gates

ROOT=Path("results/dark_star_unified")
MAN=ROOT/"unified_n27_restored_public_manifest.json"
SHA="12f169a7edabe5d548dba4c8bd07d348a2bd174378ad2faf934dcfe8b5828b10"
SEEDS=(20261028,20262037,20263046)
TRIALS=5

def verify_public():
    z=json.loads(MAN.read_text())
    rows=z["selected_public_rows"]
    assert len(rows)==len(set(v["N"] for v in rows))==12
    assert z["selected_sha256"]==population.row_digest(rows)==SHA
    assert z["no_private_pq_or_order_in_ranking_or_base_selection"]
    assert z["no_classical_filter_or_quantum_outcome_used_to_select"]
    assert z["zero_QPU"] and z["IBM_runtime_jobs"]==0
    for i,r in enumerate(rows):
        assert 1<<26<=r["N"]<1<<27 and r["rank"]==1+i%6
        assert population.base_for(r["N"],r["group"])==r["base"]
        assert r["public_cube"]==pow(r["base"],3,r["N"])
    return rows

def time_public(fn):
    times=[]
    result=None
    for i in range(TRIALS):
        t0=time.perf_counter()
        x=fn()
        times.append(time.perf_counter()-t0)
        if result is None:
            result=x
        else:
            assert result.get("factors")==x.get("factors")
    return result,dict(repeats=TRIALS,median_wall_seconds=statistics.median(times),
                       min_wall_seconds=min(times),max_wall_seconds=max(times))

def post_selection_synthetic_factors(n):
    for p in ds.primes_up_to(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q and ds.is_probable_prime(q)
            return [p,q]
    raise AssertionError("invalid synthetic frame")

def analyze_row(i,r):
    n,a=r["N"],r["base"]
    # ALL publicly chosen methods run BEFORE any true p/q/order validation.
    public,public_time=time_public(lambda:u.public_classical_preflight(n,a,fermat_tests=12,
        restored_prune_max_offset=4095,restored_prune_square_tests=12))
    baselines={}
    for key,f in (("trial",kernel.trial_division_factor),
                  ("wheel210",kernel.wheel210_factor),
                  ("PTP_LFK",kernel.lfk_factor)):
        result,timing=time_public(lambda:f(n).to_dict())
        baselines[key]=dict(observations=result,timing=timing)
    # Synthetic factors ONLY NOW revealed, for ideal eigenphases and validation.
    p,q=post_selection_synthetic_factors(n)
    assert public["factors"] in ([p,q],None)
    assert all(v["observations"]["factors"]==[p,q] for v in baselines.values())
    model={}
    cache={}
    for exponent in (1,3):
        label=f"L{exponent}"
        receipts=[]
        for seed in SEEDS:
            z=u.run_quantum_counterfactual(n,p,q,a,exponent,seed,gate_cache=cache)
            assert z["base"]==pow(a,exponent,n)
            if z["classically_shortcut"]:
                assert z["shortcut_factors"]==[p,q]
            else:
                assert not z["factors"] or z["factors"]==[p,q]
            delta=Counter()
            if z["model_attempted"]:
                for stage in z["stage_receipts"]:
                    bits=stage["m"]
                    old=gates.stage_arithmetic_count(n,z["base"],bits,cache)
                    optimized=gates.stage_arithmetic_count_public_identity_pruned(n,z["base"],bits,cache)
                    assert old["ccx"]==stage["source_CCX_per_shot"]
                    for key in ("ccx","cx","cswap"):
                        assert old[key]>=optimized[key]
                        delta[key]+=stage["shots_attempted"]*(old[key]-optimized[key])
                assert delta["ccx"]<=z["counterfactual_source_counts"]["source_CCX"]
            receipts.append(dict(seed=seed,source_original_arm=z,
                                 exact_public_identity_source_gate_savings=dict(delta)))
        executed=[z for z in receipts if z["source_original_arm"]["model_attempted"]]
        succ=sum(z["source_original_arm"]["success"] for z in executed)
        original_ccx=sum(z["source_original_arm"]["counterfactual_source_counts"]["source_CCX"] for z in executed)
        pruned_ccx=original_ccx-sum(z["exact_public_identity_source_gate_savings"].get("ccx",0) for z in executed)
        model[label]=dict(base=pow(a,exponent,n),seeds=list(SEEDS),
            receipts=receipts,model_attempts=len(executed),model_factor_successes=succ,
            public_classical_shortcuts=len(receipts)-len(executed),
            original_source_CCX=original_ccx,public_identity_pruned_source_CCX=pruned_ccx,
            source_cost_per_model_factor_success=original_ccx/succ if succ else None,
            ratio_defined=bool(succ),
            no_QPU=True)
    selected="L3" if n%3==2 else "L1"
    out=dict(index=i,frozen_public_row=r,source_public_SHA=SHA,
        actual_classical_first_receipt=public,actual_classical_first_timing=public_time,
        actual_classically_solved=bool(public["factors"]),
        actual_classical_method=public["method"],
        independent_classical_baselines=baselines,
        synthetic_validation_only_pq=[p,q],
        quantum_needed_under_fixed_prereg_public_gate=not bool(public["factors"]),
        public_conditional_odd_power_model_choice=selected,
        ideal_model_even_if_classically_solved=True,
        all_three_seed_ideal_QPE_model_arms=model,
        zero_QPU=True,paid_runtime_used=False)
    pth=ROOT/f"unified_n27_restored_original_{i:02d}.json"
    pth.write_text(json.dumps(out,indent=2)+"\n")
    print("ORIGINAL",i,n,"public",public["method"],"classically solved",bool(public["factors"]),
          "wheel",baselines["wheel210"]["observations"]["divisibility_tests"],
          "PTP LFK",baselines["PTP_LFK"]["observations"]["integer_search_steps"],
          "ideal plain",model["L1"]["model_factor_successes"],
          "cube",model["L3"]["model_factor_successes"],"zero QPU",flush=True)
    return out

def main():
    rr=verify_public()
    ROOT.mkdir(exist_ok=True,parents=True)
    rows=[]
    for i,r in enumerate(rr):
        rows.append(analyze_row(i,r))
    assert len(rows)==12 and len({r["frozen_public_row"]["N"] for r in rows})==12
    assert all(r["source_public_SHA"]==SHA and r["zero_QPU"] for r in rows)
    actual=sum(r["actual_classically_solved"] for r in rows)
    bymethod=dict(Counter(r["actual_classical_method"] for r in rows))
    model={}
    for label in ("L1","L3"):
        arm=[r["all_three_seed_ideal_QPE_model_arms"][label] for r in rows]
        successes=sum(z["model_factor_successes"] for z in arm)
        original=sum(z["original_source_CCX"] for z in arm)
        optimized=sum(z["public_identity_pruned_source_CCX"] for z in arm)
        model[label]=dict(model_sessions=sum(z["model_attempts"] for z in arm),
            ideal_factor_successes=successes,public_classical_shortcuts=sum(z["public_classical_shortcuts"] for z in arm),
            original_total_source_CCX=original,public_identity_pruned_total_source_CCX=optimized,
            exact_identity_CCX_saved=original-optimized,
            model_cost_per_factor_success=original/successes if successes else None,
            model_pruned_cost_per_factor_success=optimized/successes if successes else None)
    summary=dict(frozen_public_rows=12,sha=SHA,
        restored_classically_solved=actual,
        public_budget_remaining=12-actual,public_classical_methods=bymethod,
        all_conventional_wheel210_factorable=12,
        all_original_PTP_LFK_factorable=12,
        original_plain_model=model["L1"],
        original_cube_model=model["L3"],
        practical_factor_speedup_or_quantum_advantage_demonstrated=False)
    receipt=dict(experiment="DarkStar_fresh_N27_restored_public_classical_and_ideal_QPE",
        protocol="docs/DARK_STAR_N27_RESTORED_PLUS_IDENTITY_PRUNING_PREREG.md",
        source_public_SHA=SHA,complete=True,
        original_rows_archived=12,
        original_source_receipt_filenames=[f"unified_n27_restored_original_{i:02d}.json" for i in range(12)],
        summary=summary,zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False,
        limitations="tiny synthetically generated semiprimes; wheel and PTP LFK solve all; ideal head-limited QPE sampled on secret factor-generated orders only for evaluation; CCX source-level not native device, 3 seeds descriptive only; latency and comparable classical overhead not exchanged with QPU CCX.",
        analyzed_utc=datetime.now(timezone.utc).isoformat())
    (ROOT/"unified_n27_restored_all_12_summary.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("ALL 12 ORIGINAL FRESH N27 COMPLETE",json.dumps(summary),"NO QPU",flush=True)

if __name__=="__main__":
    main()
