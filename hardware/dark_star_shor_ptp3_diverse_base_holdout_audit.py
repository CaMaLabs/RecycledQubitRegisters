#!/usr/bin/env python3
"""Exact zero-QPU diverse-base independent-N holdout for PTP-conditioned cubing.

This is a preregistered-style robustness check after the fixed-base a=2 holdout.
It keeps one statistically independent row per semiprime N, but removes the
possibility that the previous separation was peculiar to base 2.

Public design
-------------
- Holdout range is disjoint from earlier panels by default: 8192..16383.
- Candidate semiprimes are ranked by SHA-256 of public N with a fixed salt.
- Up to the same number of N values is taken from each residue stratum.
- Exactly one public base is chosen per N by SHA-256 from a fixed small-prime
  pool, cycling publicly until gcd(a,N)=1.
- The same transform b = a^3 mod N is applied in both strata.
- Hidden factors/orders are validation labels only and are never used to select
  N, choose a, choose the transform, or set the stopping rule.

Primary endpoint
----------------
Among ordinary-Shor-factor-capable rows that survive the same public classical
shortcut guardrail on both a and b, compare the fraction with reduced order in:

    trigger: N mod 3 == 2
    control: N mod 3 == 1

Because there is one row per N, the Fisher exact test is at the independent-N
level. Wilson intervals are reported for each stratum.

Secondary endpoint
------------------
For eligible rows, compute the exact conservative staged-QPE expectation used in
previous audits (no Monte Carlo) and compare unconditional phase-round work.

No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue
import dark_star_shor_staged_stopping_time_audit as staged
import dark_star_shor_ptp3_exact_panel_audit as panel
import dark_star_shor_ptp3_independent_holdout_audit as fixed_holdout

DEFAULT_OUT = Path(
    "results/dark_star_ptp/dark_star_shor_ptp3_diverse_base_holdout_audit.json"
)
BASE_POOL = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
SELECTION_SALT = "QRR-PTP3-diverse-base-holdout-v1"


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
    return out


def hash_int(*parts) -> int:
    msg = "|".join(str(x) for x in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(msg).digest(), "big")


def choose_public_base(n: int) -> int:
    start = hash_int(SELECTION_SALT, "base", n) % len(BASE_POOL)
    for offset in range(len(BASE_POOL)):
        a = BASE_POOL[(start + offset) % len(BASE_POOL)]
        if math.gcd(a, n) == 1:
            return int(a)
    raise AssertionError(f"no coprime base found for N={n}")


def select_balanced_pairs(
    pairs: list[tuple[int, int]], per_stratum: int
) -> list[tuple[int, int]]:
    strata = {1: [], 2: []}
    for p, q in pairs:
        n = p * q
        strata[n % 3].append((p, q))
    selected = []
    for residue in (1, 2):
        ranked = sorted(
            strata[residue],
            key=lambda pq: (
                hash_int(SELECTION_SALT, "N", pq[0] * pq[1]),
                pq[0] * pq[1],
            ),
        )
        if per_stratum > 0:
            ranked = ranked[:per_stratum]
        selected.extend(ranked)
    return sorted(selected, key=lambda pq: pq[0] * pq[1])


def safe_ratio(num, den):
    if num is None or den in (None, 0):
        return None
    return float(num / den)


def summarize(rows: list[dict]) -> dict:
    factor_capable = [r for r in rows if r["baseline_factor_success_validation_only"]]
    eligible = [r for r in factor_capable if r["paired_quantum_guardrail_pass"]]
    reduced = [
        r for r in eligible
        if r["transformed_order_validation_only"] < r["baseline_order_validation_only"]
    ]
    ratios = [
        r["unconditional_phase_round_ratio"]
        for r in eligible
        if r["unconditional_phase_round_ratio"] is not None
    ]
    stop_ratios = [
        r["conditional_stop_precision_ratio"]
        for r in eligible
        if r["conditional_stop_precision_ratio"] is not None
    ]
    success_deltas = [
        r["success_probability_delta"]
        for r in eligible
        if r["success_probability_delta"] is not None
    ]
    sum_b = sum(
        r["baseline"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in eligible
    )
    sum_t = sum(
        r["cube"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in eligible
    )
    base_counts = {}
    for r in rows:
        key = str(r["base"])
        base_counts[key] = base_counts.get(key, 0) + 1

    return {
        "selected_semiprimes": len(rows),
        "base_counts": base_counts,
        "factor_capable_validation_rows": len(factor_capable),
        "factor_capable_fraction": len(factor_capable) / len(rows) if rows else None,
        "paired_quantum_guardrail_rows": len(eligible),
        "guardrail_retention_of_factor_capable": (
            len(eligible) / len(factor_capable) if factor_capable else None
        ),
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
        "order_reduced_fraction_wilson95": fixed_holdout.wilson(len(reduced), len(eligible)),
        "mean_order_reduction_factor_on_reduced_rows": (
            mean(
                r["baseline_order_validation_only"] / r["transformed_order_validation_only"]
                for r in reduced
            ) if reduced else None
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
    ap = argparse.ArgumentParser(
        description="Exact independent-N diverse-base holdout for public PTP cube preconditioning"
    )
    ap.add_argument("--prime-min", type=int, default=11)
    ap.add_argument("--N-min", type=int, default=8192)
    ap.add_argument("--N-max", type=int, default=16383)
    ap.add_argument("--per-stratum", type=int, default=200)
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    all_pairs = semiprime_pairs(args.prime_min, args.N_min, args.N_max)
    selected = select_balanced_pairs(all_pairs, args.per_stratum)
    if not selected:
        raise SystemExit("no semiprimes found in diverse-base holdout range")

    rows = []
    violations = []
    for idx, (p, q) in enumerate(selected, start=1):
        n = p * q
        a = choose_public_base(n)
        b = pow(a, 3, n)
        lam = base.lcm(p - 1, q - 1)
        r0 = base.multiplicative_order_from_lambda(a, n, lam)
        r1 = base.multiplicative_order_from_lambda(b, n, lam)
        expected = r0 // math.gcd(r0, 3)
        if r1 != expected:
            violations.append({"N": n, "base": a, "type": "order_identity", "got": r1, "expected": expected})

        w0 = pre.factor_witness(a, r0, n)
        w1 = pre.factor_witness(b, r1, n)
        same_pair = pre.compact_factor_pair(w0, n) == pre.compact_factor_pair(w1, n)
        same_half = (not w0["order_even"]) or w0["half_power"] == w1["half_power"]
        if not same_pair or not same_half:
            violations.append({"N": n, "base": a, "type": "witness_preservation"})

        shortcut0 = qvalue.power2_chain_shortcut(a, n)
        shortcut1 = qvalue.power2_chain_shortcut(b, n)
        guard = not shortcut0["factor_found"] and not shortcut1["factor_found"]
        factor_capable = bool(w0["factor_success"])
        eligible = factor_capable and guard

        baseline = cube = None
        phase_ratio = stop_ratio = success_delta = None
        if eligible:
            stage_bits = staged.stage_schedule(n, args.start_bits, args.step_bits)
            baseline = panel.exact_phase_expectation(
                n=n, a=a, r=r0, stage_bits=stage_bits,
                shots_per_stage=args.shots_per_stage,
            )
            cube = panel.exact_phase_expectation(
                n=n, a=b, r=r1, stage_bits=stage_bits,
                shots_per_stage=args.shots_per_stage,
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
            success_delta = float(
                tc["success_probability_by_cap"] - bc["success_probability_by_cap"]
            )

            if r0 % 3 != 0 and abs(phase_ratio - 1.0) > 1e-12:
                violations.append({"N": n, "base": a, "type": "no_3_in_order_but_phase_ratio_changed", "ratio": phase_ratio})
            if r0 % 3 == 0 and not (phase_ratio < 1.0):
                violations.append({"N": n, "base": a, "type": "3_in_order_but_phase_work_not_improved", "ratio": phase_ratio})

        rows.append({
            "N": n,
            "N_mod_3": n % 3,
            "stratum": "trigger_N_mod3_eq_2" if n % 3 == 2 else "control_N_mod3_eq_1",
            "selection_rank_hash": hex(hash_int(SELECTION_SALT, "N", n))[2:18],
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
        if idx % 50 == 0:
            print(f"processed {idx}/{len(selected)} independent N values")

    trigger_rows = [r for r in rows if r["N_mod_3"] == 2]
    control_rows = [r for r in rows if r["N_mod_3"] == 1]
    trigger = summarize(trigger_rows)
    control = summarize(control_rows)

    aa = int(trigger["order_reduced_rows"])
    bb = int(trigger["paired_quantum_guardrail_rows"] - aa)
    cc = int(control["order_reduced_rows"])
    dd = int(control["paired_quantum_guardrail_rows"] - cc)
    tr = trigger["order_reduced_fraction"]
    cr = control["order_reduced_fraction"]

    comparison = {
        "independent_N_contingency_table": [[aa, bb], [cc, dd]],
        "trigger_order_reduction_rate": tr,
        "control_order_reduction_rate": cr,
        "absolute_rate_difference": tr - cr if tr is not None and cr is not None else None,
        "risk_ratio": tr / cr if tr is not None and cr not in (None, 0) else None,
        "fisher_exact_two_sided_p_independent_N": fixed_holdout.fisher_two_sided(aa, bb, cc, dd),
        "aggregate_phase_reduction_trigger_minus_control": (
            trigger["aggregate_unconditional_phase_round_reduction_fraction"]
            - control["aggregate_unconditional_phase_round_reduction_fraction"]
            if trigger["aggregate_unconditional_phase_round_reduction_fraction"] is not None
            and control["aggregate_unconditional_phase_round_reduction_fraction"] is not None
            else None
        ),
        "factor_capable_fraction_difference_trigger_minus_control": (
            trigger["factor_capable_fraction"] - control["factor_capable_fraction"]
        ),
        "guardrail_retention_difference_trigger_minus_control": (
            trigger["guardrail_retention_of_factor_capable"]
            - control["guardrail_retention_of_factor_capable"]
        ),
    }

    result = {
        "experiment": "dark_star_shor_ptp3_diverse_base_holdout_audit_v1",
        "zero_qpu": True,
        "monte_carlo_used": False,
        "selection": {
            "prime_min": args.prime_min,
            "N_min": args.N_min,
            "N_max": args.N_max,
            "per_stratum": args.per_stratum,
            "one_public_base_per_N": True,
            "base_pool": list(BASE_POOL),
            "selection_salt": SELECTION_SALT,
            "N_selection": "SHA256-ranked within each public N mod 3 stratum",
            "base_selection": "SHA256(N)-indexed fixed base pool, cycle until gcd(a,N)=1",
            "range_disjoint_from_fixed_base_holdout": bool(args.N_min > 8191),
            "hidden_order_used_for_selection": False,
            "hidden_factor_used_for_policy": False,
        },
        "public_transform": "a -> a^3 mod N",
        "trigger_definition": "N mod 3 == 2",
        "control_definition": "N mod 3 == 1",
        "trigger_summary": trigger,
        "control_summary": control,
        "comparison": comparison,
        "theorem_violations": violations,
        "rows": rows,
        "interpretation_boundary": (
            "Exact ideal staged-QPE resource comparison with one independent N and one deterministic public base per row. "
            "This tests base-2 specificity and reports attrition balance. Factors/orders are validation labels only. "
            "It is not a hardware runtime/fidelity or asymptotic-complexity result."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== PTP3 DIVERSE-BASE INDEPENDENT HOLDOUT SUMMARY =====")
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
