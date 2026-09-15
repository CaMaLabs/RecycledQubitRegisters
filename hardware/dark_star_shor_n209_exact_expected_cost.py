#!/usr/bin/env python3
"""Exact zero-QPU expectation audit for the N=209 staged Dark-Star/Shor result.

This removes Monte Carlo noise from the staged-stopping/native-cost experiment.
It reads the existing N=209 compiler receipt and computes the exact idealized
stage-by-stage stopping probabilities under the same conservative model used by
`dark_star_shor_staged_stopping_time_audit.py`:

- public policy chooses only N and a;
- the true order is used only to generate/score the ideal QPE distribution;
- only the nearest QPE bin is credited;
- continued-fraction recovery is strict: the denominator itself must verify;
- stages are independent reruns;
- each stage gets a fixed number of shots;
- native CZ/depth costs come from the already-compiled receipt.

No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import dark_star_shor_staged_stopping_time_audit as staged

DEFAULT_RECEIPT = Path(
    "results/dark_star_ptp/ibm_shor209_public_cube_staged_cost_preflight.json"
)
DEFAULT_OUT = Path(
    "results/dark_star_ptp/dark_star_shor_n209_exact_expected_cost.json"
)


def per_shot_stage_success(n: int, a: int, r: int, phase_bits: int) -> dict:
    """Exact success probability of one conservative ideal shot at one stage."""
    total = 0.0
    recovering_numerators = 0
    nearest_weight_sum = 0.0
    for s in range(r):
        y, p_near = staged.nearest_bin_and_probability(s, r, phase_bits)
        nearest_weight_sum += p_near / r
        rec = staged.recover_strict_verified(y, phase_bits, a, n)
        if rec is not None:
            total += p_near / r
            recovering_numerators += 1
    return {
        "phase_bits": int(phase_bits),
        "per_shot_success_probability": float(total),
        "recovering_eigenphase_numerators": int(recovering_numerators),
        "order": int(r),
        "mean_nearest_bin_probability": float(nearest_weight_sum),
    }


def truncated_geometric_mean_attempts(p: float, shots: int) -> float | None:
    """E[K | >=1 success in at most shots Bernoulli(p) attempts]."""
    if shots <= 0 or p <= 0.0:
        return None
    q = 1.0 - (1.0 - p) ** shots
    if q <= 0.0:
        return None
    num = 0.0
    for k in range(1, shots + 1):
        num += k * ((1.0 - p) ** (k - 1)) * p
    return num / q


def exact_policy_expectation(
    *,
    n: int,
    a: int,
    r: int,
    stage_bits: list[int],
    stage_table: dict,
    shots_per_stage: int,
) -> dict:
    rows = []
    reach = 1.0
    success_total = 0.0

    prior_full_phase_rounds = 0.0
    prior_full_cz = 0.0
    prior_full_depth = 0.0
    prior_full_shots = 0.0

    weighted_stop_bits = 0.0
    weighted_phase_rounds = 0.0
    weighted_cz = 0.0
    weighted_depth = 0.0
    weighted_shots = 0.0

    for m in stage_bits:
        row = per_shot_stage_success(n, a, r, m)
        p = float(row["per_shot_success_probability"])
        fail_stage = (1.0 - p) ** shots_per_stage
        stage_success = 1.0 - fail_stage
        stop_prob = reach * stage_success
        ek = truncated_geometric_mean_attempts(p, shots_per_stage)

        best = stage_table[str(m)]["best"]
        cz = int(best["cz"])
        depth = int(best["compiled_depth"])

        if stage_success > 0.0 and ek is not None:
            stop_phase_rounds = prior_full_phase_rounds + ek * m
            stop_cz = prior_full_cz + ek * cz
            stop_depth = prior_full_depth + ek * depth
            stop_shots = prior_full_shots + ek

            weighted_stop_bits += stop_prob * m
            weighted_phase_rounds += stop_prob * stop_phase_rounds
            weighted_cz += stop_prob * stop_cz
            weighted_depth += stop_prob * stop_depth
            weighted_shots += stop_prob * stop_shots

        rows.append(
            {
                **row,
                "shots_per_stage": int(shots_per_stage),
                "stage_success_probability": float(stage_success),
                "reach_probability": float(reach),
                "stop_probability": float(stop_prob),
                "expected_attempts_in_stop_stage_given_stage_success": ek,
                "compiled_cz_per_shot": cz,
                "compiled_depth_per_shot": depth,
            }
        )

        success_total += stop_prob
        prior_full_phase_rounds += shots_per_stage * m
        prior_full_cz += shots_per_stage * cz
        prior_full_depth += shots_per_stage * depth
        prior_full_shots += shots_per_stage
        reach *= fail_stage

    failure_probability = reach
    if success_total <= 0.0:
        raise RuntimeError("no successful stopping probability under staged model")

    # Conditional on eventual success by the textbook cap, matching the prior
    # Monte Carlo summaries that report successful sessions.
    conditional = {
        "success_probability_by_cap": float(success_total),
        "failure_probability_by_cap": float(failure_probability),
        "mean_stop_precision_bits_successes": float(weighted_stop_bits / success_total),
        "mean_cumulative_phase_round_executions_successes": float(
            weighted_phase_rounds / success_total
        ),
        "mean_native_cz_executions_successes": float(weighted_cz / success_total),
        "mean_compiled_depth_executions_successes": float(weighted_depth / success_total),
        "mean_circuit_shots_executed_successes": float(weighted_shots / success_total),
    }

    # Unconditional expected work is useful operationally because failed sessions
    # consume the full schedule.  This is separate from the prior success-only
    # summaries.
    unconditional_phase = weighted_phase_rounds + failure_probability * prior_full_phase_rounds
    unconditional_cz = weighted_cz + failure_probability * prior_full_cz
    unconditional_depth = weighted_depth + failure_probability * prior_full_depth
    unconditional_shots = weighted_shots + failure_probability * prior_full_shots
    unconditional = {
        "mean_phase_round_executions_per_attempted_session": float(unconditional_phase),
        "mean_native_cz_executions_per_attempted_session": float(unconditional_cz),
        "mean_compiled_depth_executions_per_attempted_session": float(unconditional_depth),
        "mean_circuit_shots_per_attempted_session": float(unconditional_shots),
    }

    return {"stages": rows, "conditional_on_success": conditional, "unconditional": unconditional}


def ratio_block(b: dict, t: dict, section: str) -> dict:
    bb = b[section]
    tt = t[section]
    keys = sorted(set(bb) & set(tt))
    ratios = {}
    for key in keys:
        bv = bb[key]
        tv = tt[key]
        if isinstance(bv, (int, float)) and isinstance(tv, (int, float)) and bv != 0:
            ratios[key] = {
                "baseline": float(bv),
                "transformed": float(tv),
                "ratio_transformed_over_baseline": float(tv / bv),
                "reduction_fraction": float(1.0 - tv / bv),
            }
    return ratios


def main() -> int:
    ap = argparse.ArgumentParser(description="Exact expectation audit for N209 staged native cost")
    ap.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.receipt.exists():
        raise SystemExit(f"missing compiler receipt: {args.receipt}")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))

    n = int(receipt["N"])
    seed_base = int(receipt["seed_base"])
    transformed_base = int(receipt["transformed_base"])
    r0 = int(receipt["baseline_order_validation_only"])
    r1 = int(receipt["transformed_order_validation_only"])
    stage_bits = [int(x) for x in receipt["stage_bits"]]
    shots_per_stage = int(receipt["shots_per_stage"])
    tables = receipt["compile_tables"]

    baseline = exact_policy_expectation(
        n=n,
        a=seed_base,
        r=r0,
        stage_bits=stage_bits,
        stage_table=tables["baseline"],
        shots_per_stage=shots_per_stage,
    )
    transformed = exact_policy_expectation(
        n=n,
        a=transformed_base,
        r=r1,
        stage_bits=stage_bits,
        stage_table=tables["ptp3_conditional"],
        shots_per_stage=shots_per_stage,
    )

    comparison = {
        "conditional_on_success": ratio_block(baseline, transformed, "conditional_on_success"),
        "unconditional": ratio_block(baseline, transformed, "unconditional"),
    }

    result = {
        "experiment": "dark_star_shor_n209_exact_expected_cost_v1",
        "zero_qpu": True,
        "monte_carlo_used": False,
        "receipt": str(args.receipt),
        "N": n,
        "seed_base": seed_base,
        "public_rule": receipt.get("public_rule"),
        "transformed_base": transformed_base,
        "baseline_order_validation_only": r0,
        "transformed_order_validation_only": r1,
        "stage_bits": stage_bits,
        "shots_per_stage": shots_per_stage,
        "baseline": baseline,
        "ptp3_conditional": transformed,
        "comparison": comparison,
        "interpretation_boundary": (
            "Exact expectation under the same conservative ideal nearest-bin-only staged model, "
            "weighted by compiled native CZ/depth costs from the prior Fez preflight. This is not "
            "hardware runtime/fidelity and not an asymptotic-complexity claim."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== EXACT N209 STAGE SUCCESS TABLE =====")
    print(json.dumps({
        "baseline": baseline["stages"],
        "ptp3_conditional": transformed["stages"],
    }, indent=2))
    print("\n===== EXACT N209 EXPECTED-COST SUMMARY =====")
    print(json.dumps({
        "baseline": {
            **baseline["conditional_on_success"],
            **baseline["unconditional"],
        },
        "ptp3_conditional": {
            **transformed["conditional_on_success"],
            **transformed["unconditional"],
        },
    }, indent=2))
    print("\n===== EXACT N209 COST RATIO =====")
    print(json.dumps(comparison, indent=2))
    print("\n===== OVERALL =====")
    print(json.dumps({
        "pass": True,
        "zero_qpu": True,
        "monte_carlo_used": False,
        "saved": str(args.out.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
