#!/usr/bin/env python3
"""Held-out residue-prime panel for odd-power Shor preconditioning.

This experiment follows the public N mod 3 -> a^3 result and asks whether the
*selector mechanism* generalizes to other odd primes without pretending that
mod 5 or mod 7 has the same deterministic guarantee as mod 3.

For each ell in {3, 5, 7}, squarefree semiprimes N=pq with p,q != ell are split
using public information only:

    control: N mod ell == 1
    trigger: N mod ell != 0,1

A deterministic public base a is selected from a fixed pool, and the identical
odd-power transform is used in both groups:

    b = a^ell mod N.

Why this selector is principled
--------------------------------
Condition on N mod ell = rho for prime ell and assume the hidden prime residues
are sampled uniformly from F_ell^*. For rho != 1 there are ell-1 ordered
factor-residue pairs (x,y) with xy=rho, and exactly two of them contain a 1:
(1,rho) and (rho,1). For rho=1 only (1,1) contains a 1. Therefore the public
residue model predicts

    P(ell | lambda(N) | N mod ell != 1) ~= 2/(ell-1)
    P(ell | lambda(N) | N mod ell == 1) ~= 1/(ell-1).

For ell=3, the trigger probability is 1, reproducing the exact guarantee. For
ell>=5 no residue class can guarantee ell | lambda(N): choose any nonzero x not
in {1,rho}; then y=rho/x is also not 1, so the same public product residue can
come from two hidden factors neither congruent to 1 mod ell.

Primary endpoint
----------------
At the independent-N level, compare the fraction of deterministic public bases
whose validation-only order is divisible by ell in trigger vs control. Fisher
exact p-values are reported and Holm-corrected across ell={3,5,7}.

Secondary endpoints
-------------------
- validation-only ell | lambda(N), to verify the residue mechanism;
- the same classical-shortcut / Shor-factor-capable quantum-value population
  used by the preceding audits;
- exact conservative staged-QPE work on a deterministic SHA-256-ranked subset
  of eligible rows in each group.

The staged scorer below is mathematically equivalent to the existing strict
continued-fraction verifier on factor-capable rows, but faster. A convergent
denominator d verifies a^d=1 iff ord_N(a) divides d. Since the row is already
conditioned on successful standard Shor factor extraction, minimizing any such
verified d returns the same factor-producing order. The fast scorer therefore
checks divisibility by the validation order only as an exact simulation/scoring
optimization; it is not an operational stopping rule and does not change the
public algorithm.

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
import dark_star_shor_n209_exact_expected_cost as exact
import dark_star_shor_ptp3_independent_holdout_audit as fixed_holdout

DEFAULT_OUT = Path("results/dark_star_ptp/dark_star_shor_residue_prime_panel_audit.json")
ELLS = (3, 5, 7)
BASE_POOL = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)
SELECTION_SALT = "QRR-residue-ell-panel-v1"


def hash_int(*parts) -> int:
    msg = "|".join(str(x) for x in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(msg).digest(), "big")


def semiprime_pairs(prime_min: int, n_min: int, n_max: int) -> list[tuple[int, int]]:
    primes = [p for p in base.sieve_primes(n_max) if p >= prime_min]
    out = []
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            n = p * q
            if n > n_max:
                break
            if n >= n_min:
                out.append((p, q))
    return out


def choose_public_base(n: int, ell: int) -> int:
    start = hash_int(SELECTION_SALT, "base", ell, n) % len(BASE_POOL)
    for offset in range(len(BASE_POOL)):
        a = BASE_POOL[(start + offset) % len(BASE_POOL)]
        if math.gcd(a, n) == 1:
            return int(a)
    raise AssertionError(f"no coprime public base found for N={n}")


def select_balanced_pairs(pairs, ell: int, per_group: int):
    groups = {"trigger": [], "control": []}
    for p, q in pairs:
        n = p * q
        if n % ell == 0:
            continue
        group = "control" if n % ell == 1 else "trigger"
        groups[group].append((p, q))
    selected = []
    for group in ("trigger", "control"):
        ranked = sorted(
            groups[group],
            key=lambda pq: (
                hash_int(SELECTION_SALT, "N", ell, group, pq[0] * pq[1]),
                pq[0] * pq[1],
            ),
        )
        if per_group > 0:
            ranked = ranked[:per_group]
        selected.extend((group, p, q) for p, q in ranked)
    return selected


def selector_theory(ell: int) -> dict:
    return {
        "ell": ell,
        "unit_residue_count": ell - 1,
        "control_N_mod_ell_eq_1_lambda_divisibility_prior": 1.0 / (ell - 1),
        "trigger_N_mod_ell_not_0_or_1_lambda_divisibility_prior": 2.0 / (ell - 1),
        "prior_risk_ratio_trigger_over_control": 2.0,
        "trigger_is_deterministic_lambda_guarantee": ell == 3,
        "guarantee_note": (
            "For ell=3 the only nonzero residues are 1 and 2, so product 2 forces a hidden residue 1. "
            "For ell>=5, every public nonzero product residue admits a factor-residue pair with neither residue 1."
        ),
    }


def safe_ratio(num, den):
    if num is None or den in (None, 0):
        return None
    return float(num / den)


def fast_recover_from_validation_order(y: int, phase_bits: int, r_validation_only: int, n: int) -> bool:
    """Exact scoring equivalent of strict verification on factor-capable rows."""
    if y == 0:
        return False
    q = 1 << phase_bits
    seen = set()
    for d in staged.convergent_denominators(y, q):
        d = int(d)
        if d <= 1 or d > n or d in seen:
            continue
        seen.add(d)
        if d % r_validation_only == 0:
            return True
    return False


def fast_per_shot_stage_success(n: int, r_validation_only: int, phase_bits: int) -> float:
    if (1 << phase_bits) < r_validation_only:
        return 0.0
    total = 0.0
    recovery_cache = {}
    for s in range(r_validation_only):
        y, p_near = staged.nearest_bin_and_probability(s, r_validation_only, phase_bits)
        if y not in recovery_cache:
            recovery_cache[y] = fast_recover_from_validation_order(y, phase_bits, r_validation_only, n)
        if recovery_cache[y]:
            total += p_near / r_validation_only
    return float(total)


def fast_exact_phase_expectation(*, n: int, r_validation_only: int, stage_bits: list[int], shots_per_stage: int) -> dict:
    rows = []
    reach = 1.0
    success_total = 0.0
    prior_full_phase_rounds = 0.0
    prior_full_shots = 0.0
    weighted_stop_bits = 0.0
    weighted_phase_rounds = 0.0
    weighted_shots = 0.0
    for m in stage_bits:
        p = fast_per_shot_stage_success(n, r_validation_only, m)
        fail_stage = (1.0 - p) ** shots_per_stage
        stage_success = 1.0 - fail_stage
        stop_prob = reach * stage_success
        ek = exact.truncated_geometric_mean_attempts(p, shots_per_stage)
        if stage_success > 0.0 and ek is not None:
            weighted_stop_bits += stop_prob * m
            weighted_phase_rounds += stop_prob * (prior_full_phase_rounds + ek * m)
            weighted_shots += stop_prob * (prior_full_shots + ek)
        rows.append({
            "phase_bits": int(m),
            "per_shot_success_probability": float(p),
            "shots_per_stage": int(shots_per_stage),
            "stage_success_probability": float(stage_success),
            "reach_probability": float(reach),
            "stop_probability": float(stop_prob),
            "expected_attempts_in_stop_stage_given_stage_success": ek,
        })
        success_total += stop_prob
        prior_full_phase_rounds += shots_per_stage * m
        prior_full_shots += shots_per_stage
        reach *= fail_stage
    conditional = {
        "success_probability_by_cap": float(success_total),
        "failure_probability_by_cap": float(reach),
        "mean_stop_precision_bits_successes": float(weighted_stop_bits / success_total) if success_total else None,
        "mean_phase_round_executions_successes": float(weighted_phase_rounds / success_total) if success_total else None,
        "mean_circuit_shots_successes": float(weighted_shots / success_total) if success_total else None,
    }
    unconditional = {
        "mean_phase_round_executions_per_attempted_session": float(weighted_phase_rounds + reach * prior_full_phase_rounds),
        "mean_circuit_shots_per_attempted_session": float(weighted_shots + reach * prior_full_shots),
    }
    return {"stages": rows, "conditional_on_success": conditional, "unconditional": unconditional}


def reference_equivalence_check(limit: int = 100000) -> dict:
    checks = 0
    mismatches = []
    primes = [p for p in base.sieve_primes(1024) if p >= 11]
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            n = p * q
            if n < 143:
                continue
            if n > 1024:
                break
            lam = base.lcm(p - 1, q - 1)
            for a in (2, 3, 5, 7, 11):
                if math.gcd(a, n) != 1:
                    continue
                r = base.multiplicative_order_from_lambda(a, n, lam)
                if not pre.factor_witness(a, r, n)["factor_success"]:
                    continue
                for m in staged.stage_schedule(n, 4, 2):
                    ys = {staged.nearest_bin_and_probability(s, r, m)[0] for s in range(r)}
                    for y in ys:
                        ref = staged.recover_strict_verified(y, m, a, n) is not None
                        fast = fast_recover_from_validation_order(y, m, r, n)
                        checks += 1
                        if ref != fast:
                            mismatches.append({"N": n, "base": a, "order": r, "phase_bits": m, "y": y, "reference": ref, "fast": fast})
                            return {"checks": checks, "mismatches": mismatches}
                        if checks >= limit:
                            return {"checks": checks, "mismatches": mismatches}
    return {"checks": checks, "mismatches": mismatches}


def summarize_group(rows, ell: int) -> dict:
    factor_capable = [r for r in rows if r["baseline_factor_success_validation_only"]]
    eligible = [r for r in factor_capable if r["paired_quantum_guardrail_pass"]]
    reduced = [r for r in eligible if r["order_reduced"]]
    return {
        "selected_semiprimes": len(rows),
        "lambda_div_ell_rows": sum(r["lambda_div_ell_validation_only"] for r in rows),
        "lambda_div_ell_fraction": sum(r["lambda_div_ell_validation_only"] for r in rows) / len(rows) if rows else None,
        "order_div_ell_rows": sum(r["order_div_ell_validation_only"] for r in rows),
        "order_div_ell_fraction": sum(r["order_div_ell_validation_only"] for r in rows) / len(rows) if rows else None,
        "factor_capable_validation_rows": len(factor_capable),
        "factor_capable_fraction": len(factor_capable) / len(rows) if rows else None,
        "transformed_classical_shortcut_fraction": sum(r["transformed_classical_shortcut"]["factor_found"] for r in rows) / len(rows) if rows else None,
        "paired_quantum_guardrail_rows": len(eligible),
        "guardrail_retention_of_factor_capable": len(eligible) / len(factor_capable) if factor_capable else None,
        "eligible_order_div_ell_rows": sum(r["order_div_ell_validation_only"] for r in eligible),
        "eligible_order_div_ell_fraction": sum(r["order_div_ell_validation_only"] for r in eligible) / len(eligible) if eligible else None,
        "eligible_order_reduced_rows": len(reduced),
        "eligible_order_reduced_fraction": len(reduced) / len(eligible) if eligible else None,
        "eligible_order_reduced_fraction_wilson95": fixed_holdout.wilson(len(reduced), len(eligible)),
        "mean_order_reduction_factor_on_reduced_rows": mean(r["order_reduction_factor"] for r in reduced) if reduced else None,
    }


def fisher_for_boolean(rows, key: str) -> dict:
    tr = [r for r in rows if r["group"] == "trigger"]
    cr = [r for r in rows if r["group"] == "control"]
    a = sum(bool(r[key]) for r in tr); b = len(tr) - a
    c = sum(bool(r[key]) for r in cr); d = len(cr) - c
    return {
        "table": [[a, b], [c, d]],
        "trigger_fraction": a / len(tr) if tr else None,
        "control_fraction": c / len(cr) if cr else None,
        "absolute_rate_difference": a / len(tr) - c / len(cr) if tr and cr else None,
        "risk_ratio": (a / len(tr)) / (c / len(cr)) if tr and cr and c else None,
        "fisher_exact_two_sided_p_independent_N": fixed_holdout.fisher_two_sided(a, b, c, d),
    }


def fisher_eligible_reduction(rows) -> dict:
    vals = {}
    for group in ("trigger", "control"):
        rr = [r for r in rows if r["group"] == group and r["eligible_quantum_row"]]
        k = sum(r["order_reduced"] for r in rr)
        vals[group] = (k, len(rr) - k, len(rr))
    a, b, nt = vals["trigger"]; c, d, nc = vals["control"]
    return {
        "table": [[a, b], [c, d]],
        "trigger_fraction": a / nt if nt else None,
        "control_fraction": c / nc if nc else None,
        "absolute_rate_difference": a / nt - c / nc if nt and nc else None,
        "risk_ratio": (a / nt) / (c / nc) if nt and nc and c else None,
        "fisher_exact_two_sided_p_independent_N": fixed_holdout.fisher_two_sided(a, b, c, d),
    }


def holm_adjust(pairs) -> dict[str, float]:
    ordered = sorted(pairs, key=lambda x: x[1])
    m = len(ordered); out = {}; previous = 0.0
    for idx, (ell, p) in enumerate(ordered):
        adjusted = max(previous, min(1.0, (m - idx) * p))
        out[str(ell)] = float(adjusted); previous = adjusted
    return out


def phase_subset_summary(rows) -> dict:
    if not rows:
        return {"rows": 0, "mean_unconditional_phase_round_ratio": None, "median_unconditional_phase_round_ratio": None, "aggregate_unconditional_phase_round_ratio_sum_T_over_sum_B": None, "aggregate_unconditional_phase_round_reduction_fraction": None, "fraction_rows_with_lower_phase_work": None, "order_reduced_rows": 0}
    ratios = [r["phase_comparison"]["unconditional_phase_round_ratio"] for r in rows]
    sum_b = sum(r["phase_baseline"]["unconditional"]["mean_phase_round_executions_per_attempted_session"] for r in rows)
    sum_t = sum(r["phase_transformed"]["unconditional"]["mean_phase_round_executions_per_attempted_session"] for r in rows)
    agg = sum_t / sum_b if sum_b else None
    return {
        "rows": len(rows),
        "mean_unconditional_phase_round_ratio": mean(ratios),
        "median_unconditional_phase_round_ratio": median(ratios),
        "aggregate_unconditional_phase_round_ratio_sum_T_over_sum_B": agg,
        "aggregate_unconditional_phase_round_reduction_fraction": 1.0 - agg if agg is not None else None,
        "fraction_rows_with_lower_phase_work": sum(x < 1.0 - 1e-12 for x in ratios) / len(ratios),
        "order_reduced_rows": sum(r["order_reduced"] for r in rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Held-out ell={3,5,7} public residue selector panel for adaptive Shor")
    ap.add_argument("--prime-min", type=int, default=11)
    ap.add_argument("--N-min", type=int, default=16384)
    ap.add_argument("--N-max", type=int, default=32767)
    ap.add_argument("--per-group", type=int, default=160)
    ap.add_argument("--phase-per-group", type=int, default=12)
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--verify-fast-equivalence", action="store_true")
    ap.add_argument("--equivalence-check-limit", type=int, default=100000)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    equivalence = None
    if args.verify_fast_equivalence:
        equivalence = reference_equivalence_check(args.equivalence_check_limit)
        if equivalence["mismatches"]:
            raise RuntimeError(f"fast scorer equivalence failed: {equivalence['mismatches'][0]}")
        print(f"fast scorer equivalence: {equivalence['checks']} checks, 0 mismatches")

    all_pairs = semiprime_pairs(args.prime_min, args.N_min, args.N_max)
    if not all_pairs:
        raise SystemExit("no semiprimes in requested held-out range")
    panels = {}; primary_pvals = []; all_violations = []

    for ell in ELLS:
        selected = select_balanced_pairs(all_pairs, ell, args.per_group)
        rows = []; violations = []
        for idx, (group, p, q) in enumerate(selected, start=1):
            n = p * q; a = choose_public_base(n, ell); b = pow(a, ell, n)
            lam = base.lcm(p - 1, q - 1)
            r0 = base.multiplicative_order_from_lambda(a, n, lam)
            r1 = base.multiplicative_order_from_lambda(b, n, lam)
            expected = r0 // math.gcd(r0, ell)
            if r1 != expected:
                violations.append({"N": n, "ell": ell, "type": "order_identity", "got": r1, "expected": expected})
            w0 = pre.factor_witness(a, r0, n); w1 = pre.factor_witness(b, r1, n)
            witness_preserved = ((not w0["order_even"] or w0["half_power"] == w1["half_power"]) and pre.compact_factor_pair(w0, n) == pre.compact_factor_pair(w1, n))
            if not witness_preserved:
                violations.append({"N": n, "ell": ell, "type": "witness_preservation"})
            shortcut0 = qvalue.power2_chain_shortcut(a, n); shortcut1 = qvalue.power2_chain_shortcut(b, n)
            guard = not shortcut0["factor_found"] and not shortcut1["factor_found"]
            factor_capable = bool(w0["factor_success"]); eligible = factor_capable and guard
            rows.append({
                "N": n, "ell": ell, "N_mod_ell": n % ell, "group": group,
                "selection_rank_hash": hex(hash_int(SELECTION_SALT, "N", ell, group, n))[2:18],
                "p_validation_only": p, "q_validation_only": q, "base": a, "transformed_base": b,
                "lambda_validation_only": lam, "lambda_div_ell_validation_only": lam % ell == 0,
                "baseline_order_validation_only": r0, "transformed_order_validation_only": r1,
                "order_div_ell_validation_only": r0 % ell == 0, "order_reduced": r1 < r0,
                "order_reduction_factor": r0 / r1,
                "baseline_factor_success_validation_only": factor_capable,
                "half_order_witness_preserved": witness_preserved,
                "baseline_classical_shortcut": shortcut0, "transformed_classical_shortcut": shortcut1,
                "paired_quantum_guardrail_pass": bool(guard), "eligible_quantum_row": bool(eligible),
                "phase_baseline": None, "phase_transformed": None, "phase_comparison": None,
            })
            if idx % 80 == 0:
                print(f"ell={ell}: processed {idx}/{len(selected)} independent N rows")

        trigger_rows = [r for r in rows if r["group"] == "trigger"]
        control_rows = [r for r in rows if r["group"] == "control"]
        lambda_test = fisher_for_boolean(rows, "lambda_div_ell_validation_only")
        order_test = fisher_for_boolean(rows, "order_div_ell_validation_only")
        eligible_test = fisher_eligible_reduction(rows)
        primary_pvals.append((ell, order_test["fisher_exact_two_sided_p_independent_N"]))

        phase_rows_by_group = {}
        for group in ("trigger", "control"):
            eligible_rows = [r for r in rows if r["group"] == group and r["eligible_quantum_row"]]
            ranked = sorted(eligible_rows, key=lambda r: (hash_int(SELECTION_SALT, "phase", ell, group, r["N"]), r["N"]))
            if args.phase_per_group > 0:
                ranked = ranked[: args.phase_per_group]
            for pos, row in enumerate(ranked, start=1):
                stage_bits = staged.stage_schedule(row["N"], args.start_bits, args.step_bits)
                bres = fast_exact_phase_expectation(n=row["N"], r_validation_only=row["baseline_order_validation_only"], stage_bits=stage_bits, shots_per_stage=args.shots_per_stage)
                tres = fast_exact_phase_expectation(n=row["N"], r_validation_only=row["transformed_order_validation_only"], stage_bits=stage_bits, shots_per_stage=args.shots_per_stage)
                br = bres["unconditional"]["mean_phase_round_executions_per_attempted_session"]
                tr = tres["unconditional"]["mean_phase_round_executions_per_attempted_session"]
                row["phase_baseline"] = bres; row["phase_transformed"] = tres
                row["phase_comparison"] = {
                    "unconditional_phase_round_ratio": safe_ratio(tr, br),
                    "conditional_stop_precision_ratio": safe_ratio(tres["conditional_on_success"]["mean_stop_precision_bits_successes"], bres["conditional_on_success"]["mean_stop_precision_bits_successes"]),
                    "success_probability_delta": tres["conditional_on_success"]["success_probability_by_cap"] - bres["conditional_on_success"]["success_probability_by_cap"],
                }
                if not row["order_reduced"] and abs(row["phase_comparison"]["unconditional_phase_round_ratio"] - 1.0) > 1e-12:
                    violations.append({"N": row["N"], "ell": ell, "type": "unchanged_order_but_phase_work_changed", "ratio": row["phase_comparison"]["unconditional_phase_round_ratio"]})
                if pos % 4 == 0:
                    print(f"ell={ell} {group}: staged-QPE {pos}/{len(ranked)}")
            phase_rows_by_group[group] = ranked

        panels[str(ell)] = {
            "selector_theory": selector_theory(ell),
            "trigger_definition": f"N mod {ell} not in {{0,1}}",
            "control_definition": f"N mod {ell} == 1",
            "transform": f"b = a^{ell} mod N in both groups",
            "trigger_summary": summarize_group(trigger_rows, ell),
            "control_summary": summarize_group(control_rows, ell),
            "lambda_divisibility_test_all_selected_N": lambda_test,
            "primary_order_divisibility_test_all_selected_N": order_test,
            "eligible_quantum_order_reduction_test": eligible_test,
            "phase_subset": {
                "selection": "SHA256-ranked by public N within the already-defined eligible quantum population",
                "per_group_requested": args.phase_per_group,
                "trigger": phase_subset_summary(phase_rows_by_group["trigger"]),
                "control": phase_subset_summary(phase_rows_by_group["control"]),
            },
            "violations": violations,
            "rows": rows,
        }
        all_violations.extend(violations)

    holm = holm_adjust(primary_pvals)
    for ell in ELLS:
        panels[str(ell)]["primary_order_divisibility_test_all_selected_N"]["holm_adjusted_p_across_3_5_7"] = holm[str(ell)]

    result = {
        "experiment": "dark_star_shor_residue_prime_panel_audit_v1",
        "zero_qpu": True, "monte_carlo_used": False,
        "selection": {
            "prime_min": args.prime_min, "N_min": args.N_min, "N_max": args.N_max,
            "per_group": args.per_group, "phase_per_group": args.phase_per_group,
            "ells": list(ELLS), "base_pool": list(BASE_POOL), "selection_salt": SELECTION_SALT,
            "one_deterministic_public_base_per_N_per_ell": True,
            "hidden_factor_or_order_used_for_public_selection": False,
        },
        "staged_qpe": {
            "start_bits": args.start_bits, "step_bits": args.step_bits, "shots_per_stage": args.shots_per_stage,
            "model": "exact nearest-bin-only conservative staged QPE; fast acceptance scorer is theorem-equivalent to strict public denominator verification on factor-capable rows",
            "fast_reference_equivalence_check": equivalence,
        },
        "primary_family_holm_adjusted_p": holm,
        "panels": panels,
        "violation_count": len(all_violations), "violations": all_violations,
        "interpretation_boundary": {
            "ell3": "deterministic public lambda-divisibility guarantee plus empirical order enrichment",
            "ell5_ell7": "probabilistic public residue enrichment only; no deterministic hidden-factor guarantee",
            "not_claimed": ["asymptotic improvement to Shor", "measured QPU speedup", "hardware-fidelity advantage", "novelty of the elementary order identity"],
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("\n===== RESIDUE-PRIME SELECTOR PANEL =====")
    for ell in ELLS:
        p = panels[str(ell)]; tr = p["trigger_summary"]; cr = p["control_summary"]
        ot = p["primary_order_divisibility_test_all_selected_N"]; ps = p["phase_subset"]
        print(f"ell={ell}: lambda-div trigger/control {tr['lambda_div_ell_fraction']:.4f}/{cr['lambda_div_ell_fraction']:.4f}; order-div {tr['order_div_ell_fraction']:.4f}/{cr['order_div_ell_fraction']:.4f}; p={ot['fisher_exact_two_sided_p_independent_N']:.6g}; Holm={ot['holm_adjusted_p_across_3_5_7']:.6g}")
        print(f"       eligible reduced {tr['eligible_order_reduced_fraction']:.4f}/{cr['eligible_order_reduced_fraction']:.4f}; phase aggregate ratio trigger/control {ps['trigger']['aggregate_unconditional_phase_round_ratio_sum_T_over_sum_B']:.4f}/{ps['control']['aggregate_unconditional_phase_round_ratio_sum_T_over_sum_B']:.4f}")
    print(f"violations={len(all_violations)}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
