#!/usr/bin/env python3
"""Exact zero-QPU cross-semiprime replication of the public PTP-conditioned cube rule.

This is the generalization gate after the N=209 exact expected-cost result.
It intentionally does *not* compile circuits or contact IBM.  Instead it asks
whether the order-blind staged stopping effect survives across a predeclared
panel of small semiprimes.

Public policy
-------------
For every odd semiprime N in the fixed numeric panel with N mod 3 == 2, and for
each fixed public seed base a coprime to N, use

    L = 3
    b = a^3 mod N.

No factor or multiplicative order is used to choose N, a, L, b, the stage
schedule, or the stopping rule.  The known factors in this synthetic panel are
validation labels used only to compute lambda(N), the true orders, and theorem
checks after construction.

Guardrail
---------
The main paired quantum analysis keeps only rows where neither the baseline base
nor the transformed base is already factored by the same public gcd/repeated-
squaring shortcut used in the preceding audits.  It also conditions on rows for
which ordinary Shor half-order factor extraction is validation-successful; odd
powering preserves that witness, and violations are treated as failures.

Stopping model
--------------
At each staged precision, the script analytically sums the conservative
nearest-QPE-bin probability over every eigenphase numerator, uses strict
continued-fraction recovery (the convergent denominator itself must verify),
and computes the exact truncated-geometric stopping distribution.  There is no
Monte Carlo sampling.

Reported phase-round work treats each attempted m-bit staged circuit as cost m.
This is an algorithmic QPE-work replication, not a native-gate, hardware-runtime,
fidelity, or asymptotic-complexity result.  Native compilation should only be
repeated on a fixed representative subset if this panel generalizes.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue
import dark_star_shor_staged_stopping_time_audit as staged
import dark_star_shor_n209_exact_expected_cost as exact

DEFAULT_OUT = Path(
    "results/dark_star_ptp/dark_star_shor_ptp3_exact_panel_audit.json"
)


def exact_phase_expectation(
    *,
    n: int,
    a: int,
    r: int,
    stage_bits: list[int],
    shots_per_stage: int,
) -> dict:
    """Exact conservative staged stopping expectation with phase-round cost only."""
    rows = []
    reach = 1.0
    success_total = 0.0

    prior_full_phase_rounds = 0.0
    prior_full_shots = 0.0
    weighted_stop_bits = 0.0
    weighted_phase_rounds = 0.0
    weighted_shots = 0.0

    for m in stage_bits:
        row = exact.per_shot_stage_success(n, a, r, m)
        p = float(row["per_shot_success_probability"])
        fail_stage = (1.0 - p) ** shots_per_stage
        stage_success = 1.0 - fail_stage
        stop_prob = reach * stage_success
        ek = exact.truncated_geometric_mean_attempts(p, shots_per_stage)

        if stage_success > 0.0 and ek is not None:
            stop_phase_rounds = prior_full_phase_rounds + ek * m
            stop_shots = prior_full_shots + ek
            weighted_stop_bits += stop_prob * m
            weighted_phase_rounds += stop_prob * stop_phase_rounds
            weighted_shots += stop_prob * stop_shots

        rows.append(
            {
                **row,
                "shots_per_stage": int(shots_per_stage),
                "stage_success_probability": float(stage_success),
                "reach_probability": float(reach),
                "stop_probability": float(stop_prob),
                "expected_attempts_in_stop_stage_given_stage_success": ek,
            }
        )

        success_total += stop_prob
        prior_full_phase_rounds += shots_per_stage * m
        prior_full_shots += shots_per_stage
        reach *= fail_stage

    failure_probability = reach
    if success_total > 0.0:
        conditional = {
            "success_probability_by_cap": float(success_total),
            "failure_probability_by_cap": float(failure_probability),
            "mean_stop_precision_bits_successes": float(weighted_stop_bits / success_total),
            "mean_phase_round_executions_successes": float(weighted_phase_rounds / success_total),
            "mean_circuit_shots_successes": float(weighted_shots / success_total),
        }
    else:
        conditional = {
            "success_probability_by_cap": 0.0,
            "failure_probability_by_cap": 1.0,
            "mean_stop_precision_bits_successes": None,
            "mean_phase_round_executions_successes": None,
            "mean_circuit_shots_successes": None,
        }

    unconditional_phase = weighted_phase_rounds + failure_probability * prior_full_phase_rounds
    unconditional_shots = weighted_shots + failure_probability * prior_full_shots
    unconditional = {
        "mean_phase_round_executions_per_attempted_session": float(unconditional_phase),
        "mean_circuit_shots_per_attempted_session": float(unconditional_shots),
    }
    return {
        "stages": rows,
        "conditional_on_success": conditional,
        "unconditional": unconditional,
    }


def panel_pairs(prime_min: int, n_min: int, n_max: int) -> list[tuple[int, int]]:
    primes = [p for p in base.sieve_primes(n_max) if p >= prime_min]
    pairs = []
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            n = p * q
            if n > n_max:
                break
            if n < n_min:
                continue
            # This audit is specifically the public PTP-triggered branch.
            if n % 3 != 2:
                continue
            pairs.append((p, q))
    return sorted(pairs, key=lambda pq: (pq[0] * pq[1], pq[0], pq[1]))


def safe_ratio(num, den):
    if num is None or den in (None, 0):
        return None
    return float(num / den)


def summarize(rows: list[dict], all_pairs: list[tuple[int, int]]) -> dict:
    factor_capable = [r for r in rows if r["baseline_factor_success_validation_only"]]
    paired_quantum = [r for r in factor_capable if r["paired_quantum_guardrail_pass"]]
    reduced = [r for r in paired_quantum if r["transformed_order_validation_only"] < r["baseline_order_validation_only"]]

    ratios = [
        r["comparison"]["unconditional_phase_round_ratio"]
        for r in paired_quantum
        if r["comparison"]["unconditional_phase_round_ratio"] is not None
    ]
    stop_ratios = [
        r["comparison"]["conditional_stop_precision_ratio"]
        for r in paired_quantum
        if r["comparison"]["conditional_stop_precision_ratio"] is not None
    ]
    success_deltas = [
        r["comparison"]["success_probability_delta"] for r in paired_quantum
    ]

    sum_b_phase = sum(
        r["baseline"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in paired_quantum
    )
    sum_t_phase = sum(
        r["ptp3_conditional"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in paired_quantum
    )

    by_n = defaultdict(list)
    for r in paired_quantum:
        by_n[r["N"]].append(r)
    per_n = []
    for n, nrows in sorted(by_n.items()):
        nr = [
            x["comparison"]["unconditional_phase_round_ratio"]
            for x in nrows
            if x["comparison"]["unconditional_phase_round_ratio"] is not None
        ]
        per_n.append(
            {
                "N": int(n),
                "rows": len(nrows),
                "mean_unconditional_phase_round_ratio": mean(nr) if nr else None,
                "fraction_rows_improved": (
                    sum(x < 1.0 for x in nr) / len(nr) if nr else None
                ),
            }
        )

    return {
        "public_trigger_semiprimes": len(all_pairs),
        "distinct_N_with_valid_base_rows": len({r["N"] for r in rows}),
        "valid_base_rows": len(rows),
        "factor_capable_validation_rows": len(factor_capable),
        "paired_quantum_guardrail_rows": len(paired_quantum),
        "paired_quantum_distinct_N": len(by_n),
        "order_reduced_rows": len(reduced),
        "order_reduced_fraction_of_paired_quantum_rows": (
            len(reduced) / len(paired_quantum) if paired_quantum else None
        ),
        "mean_order_reduction_factor_on_reduced_rows": (
            mean(
                r["baseline_order_validation_only"] / r["transformed_order_validation_only"]
                for r in reduced
            )
            if reduced
            else None
        ),
        "mean_row_unconditional_phase_round_ratio": mean(ratios) if ratios else None,
        "median_row_unconditional_phase_round_ratio": median(ratios) if ratios else None,
        "fraction_rows_with_lower_unconditional_phase_work": (
            sum(x < 1.0 for x in ratios) / len(ratios) if ratios else None
        ),
        "aggregate_unconditional_phase_round_ratio_sum_T_over_sum_B": (
            sum_t_phase / sum_b_phase if sum_b_phase else None
        ),
        "aggregate_unconditional_phase_round_reduction_fraction": (
            1.0 - (sum_t_phase / sum_b_phase) if sum_b_phase else None
        ),
        "mean_conditional_stop_precision_ratio": mean(stop_ratios) if stop_ratios else None,
        "mean_success_probability_delta_transformed_minus_baseline": (
            mean(success_deltas) if success_deltas else None
        ),
        "fraction_distinct_N_with_mean_phase_ratio_below_1": (
            sum(
                x["mean_unconditional_phase_round_ratio"] is not None
                and x["mean_unconditional_phase_round_ratio"] < 1.0
                for x in per_n
            )
            / len(per_n)
            if per_n
            else None
        ),
        "per_N": per_n,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Exact zero-QPU cross-semiprime audit of the public PTP cube rule"
    )
    ap.add_argument("--prime-min", type=int, default=11)
    ap.add_argument("--N-min", type=int, default=143)
    ap.add_argument("--N-max", type=int, default=511)
    ap.add_argument("--bases", nargs="+", type=int, default=[2, 3, 5, 7])
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pairs = panel_pairs(args.prime_min, args.N_min, args.N_max)
    if not pairs:
        raise SystemExit("no public-trigger semiprimes found in requested panel")

    rows = []
    theorem_violations = []
    for p, q in pairs:
        n = p * q
        lam = base.lcm(p - 1, q - 1)
        stage_bits = staged.stage_schedule(n, args.start_bits, args.step_bits)
        for a in args.bases:
            if math.gcd(a, n) != 1:
                continue

            L = 3  # public trigger already enforced by N mod 3 == 2
            b = pow(a, L, n)
            r0 = base.multiplicative_order_from_lambda(a, n, lam)
            r1 = base.multiplicative_order_from_lambda(b, n, lam)
            expected_r1 = r0 // math.gcd(r0, L)
            if r1 != expected_r1:
                theorem_violations.append(
                    {"N": n, "base": a, "type": "order_identity", "got": r1, "expected": expected_r1}
                )

            w0 = pre.factor_witness(a, r0, n)
            w1 = pre.factor_witness(b, r1, n)
            same_pair = pre.compact_factor_pair(w0, n) == pre.compact_factor_pair(w1, n)
            same_half = (not w0["order_even"]) or w0["half_power"] == w1["half_power"]
            if not same_pair or not same_half:
                theorem_violations.append(
                    {"N": n, "base": a, "type": "witness_preservation"}
                )

            shortcut0 = qvalue.power2_chain_shortcut(a, n)
            shortcut1 = qvalue.power2_chain_shortcut(b, n)
            paired_guardrail = not shortcut0["factor_found"] and not shortcut1["factor_found"]

            baseline = exact_phase_expectation(
                n=n,
                a=a,
                r=r0,
                stage_bits=stage_bits,
                shots_per_stage=args.shots_per_stage,
            )
            transformed = exact_phase_expectation(
                n=n,
                a=b,
                r=r1,
                stage_bits=stage_bits,
                shots_per_stage=args.shots_per_stage,
            )

            bc = baseline["conditional_on_success"]
            tc = transformed["conditional_on_success"]
            bu = baseline["unconditional"]
            tu = transformed["unconditional"]
            comparison = {
                "unconditional_phase_round_ratio": safe_ratio(
                    tu["mean_phase_round_executions_per_attempted_session"],
                    bu["mean_phase_round_executions_per_attempted_session"],
                ),
                "conditional_stop_precision_ratio": safe_ratio(
                    tc["mean_stop_precision_bits_successes"],
                    bc["mean_stop_precision_bits_successes"],
                ),
                "conditional_phase_round_ratio": safe_ratio(
                    tc["mean_phase_round_executions_successes"],
                    bc["mean_phase_round_executions_successes"],
                ),
                "success_probability_delta": float(
                    tc["success_probability_by_cap"] - bc["success_probability_by_cap"]
                ),
            }

            rows.append(
                {
                    "N": n,
                    "N_bits": n.bit_length(),
                    "p_validation_only": p,
                    "q_validation_only": q,
                    "base": a,
                    "public_exponent": L,
                    "transformed_base": b,
                    "lambda_validation_only": lam,
                    "baseline_order_validation_only": r0,
                    "transformed_order_validation_only": r1,
                    "order_reduction_factor": r0 / r1,
                    "baseline_factor_success_validation_only": bool(w0["factor_success"]),
                    "transformed_factor_success_validation_only": bool(w1["factor_success"]),
                    "baseline_classical_shortcut": shortcut0,
                    "transformed_classical_shortcut": shortcut1,
                    "paired_quantum_guardrail_pass": bool(paired_guardrail),
                    "stage_bits": stage_bits,
                    "baseline": baseline,
                    "ptp3_conditional": transformed,
                    "comparison": comparison,
                }
            )

    summary = summarize(rows, pairs)
    result = {
        "experiment": "dark_star_shor_ptp3_exact_panel_audit_v1",
        "zero_qpu": True,
        "monte_carlo_used": False,
        "public_policy": "For N mod 3 == 2, transform a -> a^3 mod N",
        "panel_selection": {
            "prime_min": args.prime_min,
            "N_min": args.N_min,
            "N_max": args.N_max,
            "bases": args.bases,
            "public_trigger": "N mod 3 == 2",
            "hidden_order_used_for_selection": False,
            "hidden_factor_used_for_policy": False,
        },
        "stopping_model": {
            "start_bits": args.start_bits,
            "step_bits": args.step_bits,
            "shots_per_stage": args.shots_per_stage,
            "nearest_bin_only": True,
            "strict_verified_cf_denominator": True,
            "textbook_cap": "2*bit_length(N)",
        },
        "summary": summary,
        "theorem_violations": theorem_violations,
        "rows": rows,
        "interpretation_boundary": (
            "Exact idealized staged-QPE phase-work replication across a fixed small-semiprime panel. "
            "Factors/orders are validation labels only. This is not native-gate cost, measured QPU runtime/fidelity, "
            "or an asymptotic Shor complexity improvement."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== PTP3 EXACT PANEL SUMMARY =====")
    compact = {k: v for k, v in summary.items() if k != "per_N"}
    print(json.dumps(compact, indent=2))
    print("\n===== PTP3 EXACT PANEL PER-N =====")
    print(json.dumps(summary["per_N"], indent=2))
    print("\n===== OVERALL =====")
    print(
        json.dumps(
            {
                "pass": not theorem_violations,
                "zero_qpu": True,
                "monte_carlo_used": False,
                "theorem_violations": theorem_violations,
                "saved": str(args.out.resolve()),
            },
            indent=2,
        )
    )
    return 0 if not theorem_violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
