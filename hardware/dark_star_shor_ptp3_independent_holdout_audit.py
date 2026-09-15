#!/usr/bin/env python3
"""Exact zero-QPU independent-N holdout for the public PTP-conditioned cube rule.

Purpose
-------
The earlier stratified control used multiple public seed bases per semiprime, so
base rows within a fixed N are not statistically independent.  This holdout uses
exactly one public base (a=2) per odd squarefree semiprime in a disjoint numeric
range.  That makes each analyzed row correspond to a distinct N.

Public transform
----------------
For every semiprime N not divisible by 3, apply the same transform

    b = 2^3 mod N = 8

and compare two public strata:

    trigger: N mod 3 == 2
    control: N mod 3 == 1

No factor or multiplicative order is used to choose N, the base, the transform,
the stage schedule, or the stopping rule.  Factors and orders are validation
labels only.

Main analysis
-------------
The quantum-relevant analysis keeps rows where ordinary Shor factor extraction
is validation-successful and where neither the baseline nor transformed base is
already solved by the public gcd/repeated-squaring shortcut guardrail.

For eligible rows, the script computes the exact conservative staged-QPE
expectation used in the previous audits.  There is no Monte Carlo sampling and
no IBM/QPU access.

The primary binary endpoint is whether cubing reduces the order.  Because there
is one row per distinct N, the trigger/control Fisher exact test no longer has
the shared-N clustering caveat of the multi-base panel.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue
import dark_star_shor_staged_stopping_time_audit as staged
import dark_star_shor_ptp3_exact_panel_audit as panel

DEFAULT_OUT = Path(
    "results/dark_star_ptp/dark_star_shor_ptp3_independent_holdout_audit.json"
)


def semiprime_pairs(prime_min: int, n_min: int, n_max: int) -> list[tuple[int, int]]:
    primes = [p for p in base.sieve_primes(n_max) if p >= prime_min and p != 3]
    out: list[tuple[int, int]] = []
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            n = p * q
            if n > n_max:
                break
            if n < n_min:
                continue
            if n % 3 not in (1, 2):
                continue
            out.append((p, q))
    return sorted(out, key=lambda pq: (pq[0] * pq[1], pq[0], pq[1]))


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    z2 = z * z
    den = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / den
    half = z * math.sqrt((p * (1.0 - p) / total) + z2 / (4.0 * total * total)) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p-value for [[a,b],[c,d]], stdlib only."""
    r1 = a + b
    r2 = c + d
    c1 = a + c
    n = r1 + r2
    if n == 0:
        return 1.0

    def prob(x: int) -> float:
        if x < 0 or x > r1 or x > c1 or c1 - x > r2:
            return 0.0
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)

    lo = max(0, r1 - (n - c1))
    hi = min(r1, c1)
    p_obs = prob(a)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs + 1e-18))


def safe_ratio(num, den):
    if num is None or den in (None, 0):
        return None
    return float(num / den)


def summarize(rows: list[dict]) -> dict:
    factor_capable = [r for r in rows if r["baseline_factor_success_validation_only"]]
    eligible = [r for r in factor_capable if r["paired_quantum_guardrail_pass"]]
    reduced = [r for r in eligible if r["transformed_order_validation_only"] < r["baseline_order_validation_only"]]
    ratios = [r["unconditional_phase_round_ratio"] for r in eligible if r["unconditional_phase_round_ratio"] is not None]
    stop_ratios = [r["conditional_stop_precision_ratio"] for r in eligible if r["conditional_stop_precision_ratio"] is not None]
    success_deltas = [r["success_probability_delta"] for r in eligible if r["success_probability_delta"] is not None]

    sum_b = sum(
        r["baseline"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in eligible
    )
    sum_t = sum(
        r["cube"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in eligible
    )

    return {
        "semiprimes": len(rows),
        "factor_capable_validation_rows": len(factor_capable),
        "paired_quantum_guardrail_rows": len(eligible),
        "lambda_div_3_fraction": (
            sum(r["lambda_validation_only"] % 3 == 0 for r in eligible) / len(eligible)
            if eligible else None
        ),
        "r_div_3_fraction": (
            sum(r["baseline_order_validation_only"] % 3 == 0 for r in eligible) / len(eligible)
            if eligible else None
        ),
        "order_reduced_rows": len(reduced),
        "order_reduced_fraction": len(reduced) / len(eligible) if eligible else None,
        "order_reduced_fraction_wilson95": wilson(len(reduced), len(eligible)),
        "mean_order_reduction_factor_on_reduced_rows": (
            mean(r["baseline_order_validation_only"] / r["transformed_order_validation_only"] for r in reduced)
            if reduced else None
        ),
        "mean_unconditional_phase_round_ratio": mean(ratios) if ratios else None,
        "median_unconditional_phase_round_ratio": median(ratios) if ratios else None,
        "fraction_rows_with_lower_phase_work": (
            sum(x < 1.0 for x in ratios) / len(ratios) if ratios else None
        ),
        "aggregate_unconditional_phase_round_ratio_sum_T_over_sum_B": (
            sum_t / sum_b if sum_b else None
        ),
        "aggregate_unconditional_phase_round_reduction_fraction": (
            1.0 - sum_t / sum_b if sum_b else None
        ),
        "mean_conditional_stop_precision_ratio": mean(stop_ratios) if stop_ratios else None,
        "mean_success_probability_delta_transformed_minus_baseline": (
            mean(success_deltas) if success_deltas else None
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Exact independent-N holdout for public PTP cube preconditioning")
    ap.add_argument("--prime-min", type=int, default=11)
    ap.add_argument("--N-min", type=int, default=2048)
    ap.add_argument("--N-max", type=int, default=8191)
    ap.add_argument("--base", type=int, default=2)
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.base != 2:
        raise SystemExit("this preregistered holdout fixes the public base at a=2")

    pairs = semiprime_pairs(args.prime_min, args.N_min, args.N_max)
    if not pairs:
        raise SystemExit("no semiprimes found in requested holdout range")

    rows = []
    violations = []
    for p, q in pairs:
        n = p * q
        a = 2
        b = pow(a, 3, n)
        lam = base.lcm(p - 1, q - 1)
        r0 = base.multiplicative_order_from_lambda(a, n, lam)
        r1 = base.multiplicative_order_from_lambda(b, n, lam)
        expected = r0 // math.gcd(r0, 3)
        if r1 != expected:
            violations.append({"N": n, "type": "order_identity", "got": r1, "expected": expected})

        w0 = pre.factor_witness(a, r0, n)
        w1 = pre.factor_witness(b, r1, n)
        same_pair = pre.compact_factor_pair(w0, n) == pre.compact_factor_pair(w1, n)
        same_half = (not w0["order_even"]) or w0["half_power"] == w1["half_power"]
        if not same_pair or not same_half:
            violations.append({"N": n, "type": "witness_preservation"})

        shortcut0 = qvalue.power2_chain_shortcut(a, n)
        shortcut1 = qvalue.power2_chain_shortcut(b, n)
        guard = not shortcut0["factor_found"] and not shortcut1["factor_found"]
        factor_capable = bool(w0["factor_success"])
        eligible = factor_capable and guard

        baseline = None
        cube = None
        phase_ratio = None
        stop_ratio = None
        success_delta = None
        if eligible:
            stage_bits = staged.stage_schedule(n, args.start_bits, args.step_bits)
            baseline = panel.exact_phase_expectation(
                n=n, a=a, r=r0, stage_bits=stage_bits, shots_per_stage=args.shots_per_stage
            )
            cube = panel.exact_phase_expectation(
                n=n, a=b, r=r1, stage_bits=stage_bits, shots_per_stage=args.shots_per_stage
            )
            bc, tc = baseline["conditional_on_success"], cube["conditional_on_success"]
            bu, tu = baseline["unconditional"], cube["unconditional"]
            phase_ratio = safe_ratio(
                tu["mean_phase_round_executions_per_attempted_session"],
                bu["mean_phase_round_executions_per_attempted_session"],
            )
            stop_ratio = safe_ratio(
                tc["mean_stop_precision_bits_successes"],
                bc["mean_stop_precision_bits_successes"],
            )
            success_delta = float(tc["success_probability_by_cap"] - bc["success_probability_by_cap"])

            if r0 % 3 != 0 and abs(phase_ratio - 1.0) > 1e-12:
                violations.append({"N": n, "type": "no_3_in_order_but_phase_ratio_changed", "ratio": phase_ratio})
            if r0 % 3 == 0 and not (phase_ratio < 1.0):
                violations.append({"N": n, "type": "3_in_order_but_phase_work_not_improved", "ratio": phase_ratio})

        rows.append({
            "N": n,
            "N_mod_3": n % 3,
            "stratum": "trigger_N_mod3_eq_2" if n % 3 == 2 else "control_N_mod3_eq_1",
            "p_validation_only": p,
            "q_validation_only": q,
            "base": a,
            "transformed_base": b,
            "lambda_validation_only": lam,
            "baseline_order_validation_only": r0,
            "transformed_order_validation_only": r1,
            "order_reduction_factor": r0 / r1,
            "baseline_factor_success_validation_only": factor_capable,
            "baseline_classical_shortcut": shortcut0,
            "transformed_classical_shortcut": shortcut1,
            "paired_quantum_guardrail_pass": bool(guard),
            "eligible_quantum_row": bool(eligible),
            "baseline": baseline,
            "cube": cube,
            "unconditional_phase_round_ratio": phase_ratio,
            "conditional_stop_precision_ratio": stop_ratio,
            "success_probability_delta": success_delta,
        })

    trigger_rows = [r for r in rows if r["N_mod_3"] == 2]
    control_rows = [r for r in rows if r["N_mod_3"] == 1]
    trigger = summarize(trigger_rows)
    control = summarize(control_rows)

    a = int(trigger["order_reduced_rows"])
    b = int(trigger["paired_quantum_guardrail_rows"] - a)
    c = int(control["order_reduced_rows"])
    d = int(control["paired_quantum_guardrail_rows"] - c)
    trigger_rate = trigger["order_reduced_fraction"]
    control_rate = control["order_reduced_fraction"]

    comparison = {
        "independent_N_contingency_table": [[a, b], [c, d]],
        "trigger_order_reduction_rate": trigger_rate,
        "control_order_reduction_rate": control_rate,
        "absolute_rate_difference": (
            trigger_rate - control_rate if trigger_rate is not None and control_rate is not None else None
        ),
        "risk_ratio": (
            trigger_rate / control_rate if trigger_rate is not None and control_rate not in (None, 0) else None
        ),
        "fisher_exact_two_sided_p_independent_N": fisher_two_sided(a, b, c, d),
        "aggregate_phase_reduction_trigger_minus_control": (
            trigger["aggregate_unconditional_phase_round_reduction_fraction"]
            - control["aggregate_unconditional_phase_round_reduction_fraction"]
            if trigger["aggregate_unconditional_phase_round_reduction_fraction"] is not None
            and control["aggregate_unconditional_phase_round_reduction_fraction"] is not None
            else None
        ),
    }

    result = {
        "experiment": "dark_star_shor_ptp3_independent_holdout_audit_v1",
        "zero_qpu": True,
        "monte_carlo_used": False,
        "holdout_selection": {
            "prime_min": args.prime_min,
            "N_min": args.N_min,
            "N_max": args.N_max,
            "one_public_base_per_N": True,
            "base": 2,
            "range_disjoint_from_prior_512_2047_control": bool(args.N_min > 2047),
            "hidden_order_used_for_selection": False,
            "hidden_factor_used_for_policy": False,
        },
        "public_transform": "a=2 -> a^3 mod N",
        "trigger_definition": "N mod 3 == 2",
        "control_definition": "N mod 3 == 1",
        "trigger_summary": trigger,
        "control_summary": control,
        "comparison": comparison,
        "theorem_violations": violations,
        "rows": rows,
        "interpretation_boundary": (
            "Exact ideal staged-QPE resource comparison with one independent semiprime N per row and fixed public base a=2. "
            "Factors/orders are validation labels only. This is not hardware runtime/fidelity and not an asymptotic Shor complexity claim."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== PTP3 INDEPENDENT-N HOLDOUT SUMMARY =====")
    print(json.dumps({"trigger": trigger, "control": control, "comparison": comparison}, indent=2))
    print("\n===== OVERALL =====")
    print(json.dumps({
        "pass": not violations,
        "zero_qpu": True,
        "monte_carlo_used": False,
        "theorem_violations": violations,
        "saved": str(args.out.resolve()),
    }, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
