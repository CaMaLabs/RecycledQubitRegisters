#!/usr/bin/env python3
"""Exact zero-QPU stratified control for public cube preconditioning in adaptive Shor.

Purpose
-------
The PTP-conditioned result applies a -> a^3 mod N when public N mod 3 == 2.
For semiprimes not divisible by 3, that residue class guarantees 3 | lambda(N),
but it does not guarantee 3 | ord_N(a).  A key control is therefore to ask:

    Does N mod 3 == 2 actually select a population where cubing is more useful
    than the non-trigger control class N mod 3 == 1?

This audit applies the *same* public cube transform to both strata and compares
exact order-blind staged-QPE work after the same classical shortcut guardrail.
The default numeric range is disjoint from the first 143..511 PTP3 panel.

No hidden factor/order is used to select N, a, or the transformation.  Factors
and orders are validation labels only.  No IBM service is contacted and no QPU
job is submitted.
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
import dark_star_shor_ptp3_exact_panel_audit as panel

DEFAULT_OUT = Path(
    "results/dark_star_ptp/dark_star_shor_cube_stratified_control_audit.json"
)


def semiprime_pairs(prime_min: int, n_min: int, n_max: int) -> list[tuple[int, int]]:
    primes = [p for p in base.sieve_primes(n_max) if p >= prime_min and p != 3]
    out = []
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


def safe_ratio(num, den):
    if num is None or den in (None, 0):
        return None
    return float(num / den)


def summarize(rows: list[dict]) -> dict:
    factor_capable = [r for r in rows if r["baseline_factor_success_validation_only"]]
    paired = [r for r in factor_capable if r["paired_quantum_guardrail_pass"]]
    reduced = [r for r in paired if r["transformed_order_validation_only"] < r["baseline_order_validation_only"]]
    ratios = [r["unconditional_phase_round_ratio"] for r in paired if r["unconditional_phase_round_ratio"] is not None]
    stop_ratios = [r["conditional_stop_precision_ratio"] for r in paired if r["conditional_stop_precision_ratio"] is not None]
    success_deltas = [r["success_probability_delta"] for r in paired]

    sum_b = sum(
        r["baseline"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in paired
    )
    sum_t = sum(
        r["cube"]["unconditional"]["mean_phase_round_executions_per_attempted_session"]
        for r in paired
    )

    by_n = defaultdict(list)
    for r in paired:
        by_n[r["N"]].append(r)
    per_n = []
    for n, nrows in sorted(by_n.items()):
        rr = [x["unconditional_phase_round_ratio"] for x in nrows if x["unconditional_phase_round_ratio"] is not None]
        per_n.append({
            "N": int(n),
            "rows": len(nrows),
            "mean_phase_round_ratio": mean(rr) if rr else None,
            "fraction_rows_improved": sum(x < 1.0 for x in rr) / len(rr) if rr else None,
        })

    return {
        "semiprimes": len({r["N"] for r in rows}),
        "valid_base_rows": len(rows),
        "factor_capable_validation_rows": len(factor_capable),
        "paired_quantum_guardrail_rows": len(paired),
        "paired_quantum_distinct_N": len(by_n),
        "order_reduced_rows": len(reduced),
        "order_reduced_fraction_of_paired_quantum_rows": len(reduced) / len(paired) if paired else None,
        "mean_order_reduction_factor_on_reduced_rows": (
            mean(r["baseline_order_validation_only"] / r["transformed_order_validation_only"] for r in reduced)
            if reduced else None
        ),
        "mean_row_unconditional_phase_round_ratio": mean(ratios) if ratios else None,
        "median_row_unconditional_phase_round_ratio": median(ratios) if ratios else None,
        "fraction_rows_with_lower_unconditional_phase_work": sum(x < 1.0 for x in ratios) / len(ratios) if ratios else None,
        "aggregate_unconditional_phase_round_ratio_sum_T_over_sum_B": sum_t / sum_b if sum_b else None,
        "aggregate_unconditional_phase_round_reduction_fraction": 1.0 - sum_t / sum_b if sum_b else None,
        "mean_conditional_stop_precision_ratio": mean(stop_ratios) if stop_ratios else None,
        "mean_success_probability_delta_transformed_minus_baseline": mean(success_deltas) if success_deltas else None,
        "fraction_distinct_N_with_mean_phase_ratio_below_1": (
            sum(x["mean_phase_round_ratio"] is not None and x["mean_phase_round_ratio"] < 1.0 for x in per_n) / len(per_n)
            if per_n else None
        ),
        "per_N": per_n,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Exact stratified N mod 3 control for cube-preconditioned adaptive Shor")
    ap.add_argument("--prime-min", type=int, default=11)
    ap.add_argument("--N-min", type=int, default=512)
    ap.add_argument("--N-max", type=int, default=2047)
    ap.add_argument("--bases", nargs="+", type=int, default=[2, 3, 5, 7])
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pairs = semiprime_pairs(args.prime_min, args.N_min, args.N_max)
    if not pairs:
        raise SystemExit("no semiprimes found in requested panel")

    rows = []
    violations = []
    for p, q in pairs:
        n = p * q
        stratum = "trigger_N_mod3_eq_2" if n % 3 == 2 else "control_N_mod3_eq_1"
        lam = base.lcm(p - 1, q - 1)
        stage_bits = staged.stage_schedule(n, args.start_bits, args.step_bits)
        for a in args.bases:
            if math.gcd(a, n) != 1:
                continue
            b = pow(a, 3, n)
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

            baseline = panel.exact_phase_expectation(
                n=n, a=a, r=r0, stage_bits=stage_bits, shots_per_stage=args.shots_per_stage
            )
            cube = panel.exact_phase_expectation(
                n=n, a=b, r=r1, stage_bits=stage_bits, shots_per_stage=args.shots_per_stage
            )
            bc, tc = baseline["conditional_on_success"], cube["conditional_on_success"]
            bu, tu = baseline["unconditional"], cube["unconditional"]

            rows.append({
                "N": n,
                "N_mod_3": n % 3,
                "stratum": stratum,
                "p_validation_only": p,
                "q_validation_only": q,
                "base": a,
                "transformed_base": b,
                "baseline_order_validation_only": r0,
                "transformed_order_validation_only": r1,
                "order_reduction_factor": r0 / r1,
                "baseline_factor_success_validation_only": bool(w0["factor_success"]),
                "paired_quantum_guardrail_pass": bool(guard),
                "baseline_classical_shortcut": shortcut0,
                "transformed_classical_shortcut": shortcut1,
                "baseline": baseline,
                "cube": cube,
                "unconditional_phase_round_ratio": safe_ratio(
                    tu["mean_phase_round_executions_per_attempted_session"],
                    bu["mean_phase_round_executions_per_attempted_session"],
                ),
                "conditional_stop_precision_ratio": safe_ratio(
                    tc["mean_stop_precision_bits_successes"],
                    bc["mean_stop_precision_bits_successes"],
                ),
                "success_probability_delta": float(tc["success_probability_by_cap"] - bc["success_probability_by_cap"]),
            })

    trigger_rows = [r for r in rows if r["N_mod_3"] == 2]
    control_rows = [r for r in rows if r["N_mod_3"] == 1]
    trigger = summarize(trigger_rows)
    control = summarize(control_rows)

    diff = {
        "order_reduced_fraction_trigger_minus_control": (
            trigger["order_reduced_fraction_of_paired_quantum_rows"] - control["order_reduced_fraction_of_paired_quantum_rows"]
            if trigger["order_reduced_fraction_of_paired_quantum_rows"] is not None and control["order_reduced_fraction_of_paired_quantum_rows"] is not None else None
        ),
        "aggregate_phase_reduction_trigger_minus_control": (
            trigger["aggregate_unconditional_phase_round_reduction_fraction"] - control["aggregate_unconditional_phase_round_reduction_fraction"]
            if trigger["aggregate_unconditional_phase_round_reduction_fraction"] is not None and control["aggregate_unconditional_phase_round_reduction_fraction"] is not None else None
        ),
        "mean_success_delta_trigger_minus_control": (
            trigger["mean_success_probability_delta_transformed_minus_baseline"] - control["mean_success_probability_delta_transformed_minus_baseline"]
            if trigger["mean_success_probability_delta_transformed_minus_baseline"] is not None and control["mean_success_probability_delta_transformed_minus_baseline"] is not None else None
        ),
    }

    result = {
        "experiment": "dark_star_shor_cube_stratified_control_audit_v1",
        "zero_qpu": True,
        "monte_carlo_used": False,
        "panel_selection": {
            "prime_min": args.prime_min,
            "N_min": args.N_min,
            "N_max": args.N_max,
            "bases": args.bases,
            "hidden_order_used_for_selection": False,
            "hidden_factor_used_for_policy": False,
            "range_disjoint_from_first_ptp3_panel": bool(args.N_min > 511),
        },
        "public_transform_applied_to_both_strata": "a -> a^3 mod N",
        "trigger_definition": "N mod 3 == 2 (guarantees 3 | lambda(N) for semiprimes not divisible by 3)",
        "control_definition": "N mod 3 == 1 (does not by itself guarantee 3 | lambda(N))",
        "trigger_summary": trigger,
        "control_summary": control,
        "trigger_minus_control": diff,
        "theorem_violations": violations,
        "rows": rows,
        "interpretation_boundary": (
            "Exact conservative ideal staged-QPE comparison after a public classical-shortcut guardrail. "
            "This tests whether the PTP public trigger has incremental predictive value over cubing an N mod 3 == 1 control stratum. "
            "It is not a hardware-runtime/fidelity or asymptotic-complexity result."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== CUBE STRATIFIED CONTROL SUMMARY =====")
    print(json.dumps({"trigger": trigger, "control": control, "trigger_minus_control": diff}, indent=2))
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
