#!/usr/bin/env python3
"""Zero-QPU staged stopping-time audit for Dark-Star/Shor preconditioning.

This follows dark_star_shor_adaptive_precision_bound_audit.py and replaces the
validation-only precision proxy with a conservative idealized stopping-time
simulation.

Public workflow:
1. choose odd-power policy from N only;
2. build b = a^L mod N;
3. run staged phase estimation at increasing precision;
4. continued-fraction postprocess each measured phase;
5. accept only a denominator that itself verifies b^d = 1 (no hidden order and
   no searched denominator multiples);
6. minimize that verified candidate with public modular exponentiation, then
   apply the normal Shor gcd factor extraction;
7. stop at the first verified factor; otherwise increase precision.

Simulation boundary:
- The hidden true order is used only to generate ideal QPE samples and to score
  the run after the fact.
- To stay conservative and cheap, each ideal QPE shot only credits the nearest
  phase bin. Its exact nearest-bin probability is used; all non-nearest outcomes
  are treated as failures even though some would also recover the order.
- Every stage is an independent rerun. cumulative_phase_round_executions counts
  the sum of m over all attempted shots, deliberately more conservative than an
  implementation that can reuse earlier phase work.
- Classical GCD/repeated-squaring shortcuts are applied first; rows they solve
  are excluded from quantum-value statistics.

No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue


def convergent_denominators(num: int, den: int):
    coeffs = []
    n, d = int(num), int(den)
    while d:
        q, rem = divmod(n, d)
        coeffs.append(q)
        n, d = d, rem

    p_nm2, p_nm1 = 0, 1
    q_nm2, q_nm1 = 1, 0
    for coeff in coeffs:
        p = coeff * p_nm1 + p_nm2
        q = coeff * q_nm1 + q_nm2
        if q:
            yield q
        p_nm2, p_nm1 = p_nm1, p
        q_nm2, q_nm1 = q_nm1, q


def minimize_verified_order(a: int, n: int, candidate: int) -> int:
    r = int(candidate)
    for p in sorted(base.factor_int(r)):
        while r % p == 0 and pow(a, r // p, n) == 1:
            r //= p
    return r


def recover_strict_verified(y: int, phase_bits: int, a: int, n: int) -> dict | None:
    """Strict CF recovery: a convergent denominator itself must verify."""
    if y == 0:
        return None
    q = 1 << phase_bits
    seen = set()
    for d in convergent_denominators(y, q):
        d = int(d)
        if d <= 1 or d > n or d in seen:
            continue
        seen.add(d)
        if pow(a, d, n) != 1:
            continue
        r = minimize_verified_order(a, n, d)
        if r <= 1 or r % 2:
            continue
        x = pow(a, r // 2, n)
        if x in (1, n - 1):
            continue
        factors = []
        for g in (math.gcd(x - 1, n), math.gcd(x + 1, n)):
            if 1 < g < n and n % g == 0:
                pair = (min(g, n // g), max(g, n // g))
                if pair not in factors:
                    factors.append(pair)
        if factors:
            return {
                "continued_fraction_denominator": d,
                "verified_order": r,
                "factors": list(factors[0]),
            }
    return None


def nearest_bin_and_probability(s: int, r: int, phase_bits: int) -> tuple[int, float]:
    """Exact probability of the nearest QPE grid point for phase s/r."""
    q = 1 << phase_bits
    scaled = q * s / r
    y_raw = int(math.floor(scaled + 0.5))
    y = y_raw % q
    delta = (s / r) - (y / q)
    delta -= round(delta)

    if abs(delta) < 1e-16:
        return y, 1.0
    den = math.sin(math.pi * delta)
    if abs(den) < 1e-16:
        return y, 1.0
    num = math.sin(math.pi * q * delta)
    p = (num / (q * den)) ** 2
    return y, min(1.0, max(0.0, float(p)))


def deterministic_rng(*parts) -> random.Random:
    text = "|".join(str(x) for x in parts).encode("utf-8")
    seed = int.from_bytes(hashlib.sha256(text).digest()[:8], "big")
    return random.Random(seed)


def stage_schedule(n: int, start_bits: int, step_bits: int) -> list[int]:
    cap = 2 * n.bit_length()
    start = max(2, min(int(start_bits), cap))
    step = max(1, int(step_bits))
    vals = list(range(start, cap + 1, step))
    if not vals or vals[-1] != cap:
        vals.append(cap)
    return vals


def simulate_session(
    n: int,
    a: int,
    true_order_validation_only: int,
    *,
    start_bits: int,
    step_bits: int,
    shots_per_stage: int,
    rng: random.Random,
) -> dict:
    stages = stage_schedule(n, start_bits, step_bits)
    attempts = 0
    nearest_credited = 0
    cumulative_phase_round_executions = 0

    for stage_index, m in enumerate(stages):
        for shot_in_stage in range(shots_per_stage):
            attempts += 1
            cumulative_phase_round_executions += m

            s = rng.randrange(true_order_validation_only)
            y, p_near = nearest_bin_and_probability(
                s, true_order_validation_only, m
            )

            # Conservative ideal audit: discard all non-nearest QPE outcomes.
            if rng.random() > p_near:
                continue
            nearest_credited += 1

            rec = recover_strict_verified(y, m, a, n)
            if rec is not None:
                return {
                    "success": True,
                    "stop_precision_bits": m,
                    "stage_index": stage_index,
                    "stages_attempted": stage_index + 1,
                    "shots_attempted": attempts,
                    "shot_in_stop_stage": shot_in_stage + 1,
                    "nearest_bin_events_credited": nearest_credited,
                    "cumulative_phase_round_executions": cumulative_phase_round_executions,
                    "recovery": rec,
                }

    return {
        "success": False,
        "stop_precision_bits": None,
        "stage_index": None,
        "stages_attempted": len(stages),
        "shots_attempted": attempts,
        "shot_in_stop_stage": None,
        "nearest_bin_events_credited": nearest_credited,
        "cumulative_phase_round_executions": cumulative_phase_round_executions,
        "recovery": None,
    }


def summarize_sessions(rows: list[dict], policy: str) -> dict:
    vals = []
    for row in rows:
        p = row["policies"][policy]
        if not p["eligible_quantum_row"]:
            continue
        vals.extend(p["sessions"])

    successes = [v for v in vals if v["success"]]

    def avg(key, src):
        data = [float(v[key]) for v in src if v.get(key) is not None]
        return mean(data) if data else None

    def med(key, src):
        data = [float(v[key]) for v in src if v.get(key) is not None]
        return median(data) if data else None

    return {
        "description": pre.POLICY_DESCRIPTIONS[policy],
        "eligible_sessions": len(vals),
        "adaptive_success_sessions": len(successes),
        "adaptive_success_rate_by_textbook_cap": (
            len(successes) / len(vals) if vals else None
        ),
        "mean_stop_precision_bits_successes": avg("stop_precision_bits", successes),
        "median_stop_precision_bits_successes": med("stop_precision_bits", successes),
        "mean_cumulative_phase_round_executions_successes": avg(
            "cumulative_phase_round_executions", successes
        ),
        "median_cumulative_phase_round_executions_successes": med(
            "cumulative_phase_round_executions", successes
        ),
        "mean_stages_attempted_successes": avg("stages_attempted", successes),
        "mean_shots_attempted_successes": avg("shots_attempted", successes),
        "simulation_boundary": (
            "Ideal nearest-bin-only conservative simulation; non-nearest QPE "
            "outcomes are discarded even when they might recover the order."
        ),
    }


def paired_vs_baseline(rows: list[dict], policy: str) -> dict:
    if policy == "baseline":
        return {}
    pairs = []
    for row in rows:
        b = row["policies"]["baseline"]
        p = row["policies"][policy]
        if not b["eligible_quantum_row"] or not p["eligible_quantum_row"]:
            continue
        for sb, sp in zip(b["sessions"], p["sessions"]):
            if sb["success"] and sp["success"]:
                pairs.append((sb, sp))

    if not pairs:
        return {
            "paired_success_sessions": 0,
            "mean_stop_precision_bits_saved": None,
            "median_stop_precision_bits_saved": None,
            "fraction_policy_stops_at_lower_precision": None,
            "mean_cumulative_round_ratio_policy_over_baseline": None,
        }

    precision_saved = [
        b["stop_precision_bits"] - p["stop_precision_bits"] for b, p in pairs
    ]
    round_ratios = [
        p["cumulative_phase_round_executions"]
        / b["cumulative_phase_round_executions"]
        for b, p in pairs
        if b["cumulative_phase_round_executions"] > 0
    ]
    return {
        "paired_success_sessions": len(pairs),
        "mean_stop_precision_bits_saved": mean(precision_saved),
        "median_stop_precision_bits_saved": median(precision_saved),
        "fraction_policy_stops_at_lower_precision": sum(x > 0 for x in precision_saved)
        / len(precision_saved),
        "fraction_policy_stops_at_equal_precision": sum(x == 0 for x in precision_saved)
        / len(precision_saved),
        "fraction_policy_stops_at_higher_precision": sum(x < 0 for x in precision_saved)
        / len(precision_saved),
        "mean_cumulative_round_ratio_policy_over_baseline": (
            mean(round_ratios) if round_ratios else None
        ),
    }


def n209_probe(
    *,
    start_bits: int,
    step_bits: int,
    shots_per_stage: int,
    replicates: int,
) -> dict:
    n = 209
    a = 3
    p, q = 11, 19
    lam = base.lcm(p - 1, q - 1)
    r = base.multiplicative_order_from_lambda(a, n, lam)

    out = {}
    for policy in ("baseline", "ptp3_conditional"):
        L = pre.exponent_for_policy(policy, n)
        b = pow(a, L, n)
        rb = base.multiplicative_order_from_lambda(b, n, lam)
        shortcut = qvalue.power2_chain_shortcut(b, n)
        sessions = []
        if not shortcut["factor_found"]:
            for rep in range(replicates):
                rng = deterministic_rng("n209", policy, rep)
                sessions.append(
                    simulate_session(
                        n,
                        b,
                        rb,
                        start_bits=start_bits,
                        step_bits=step_bits,
                        shots_per_stage=shots_per_stage,
                        rng=rng,
                    )
                )
        success = [s for s in sessions if s["success"]]
        out[policy] = {
            "exponent": L,
            "transformed_base": b,
            "order_validation_only": rb,
            "classical_shortcut_found": shortcut["factor_found"],
            "sessions": len(sessions),
            "success_rate": len(success) / len(sessions) if sessions else None,
            "mean_stop_precision_bits": (
                mean(s["stop_precision_bits"] for s in success) if success else None
            ),
            "median_stop_precision_bits": (
                median(s["stop_precision_bits"] for s in success) if success else None
            ),
            "mean_cumulative_phase_round_executions": (
                mean(s["cumulative_phase_round_executions"] for s in success)
                if success
                else None
            ),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU conservative staged QPE stopping-time audit"
    )
    ap.add_argument("--prime-min", type=int, default=101)
    ap.add_argument("--prime-max", type=int, default=2000)
    ap.add_argument("--semiprimes", type=int, default=600)
    ap.add_argument("--ratio-max", type=float, default=2.0)
    ap.add_argument("--bases", nargs="+", type=int, default=list(pre.DEFAULT_BASES))
    ap.add_argument("--seed", type=int, default=8778)
    ap.add_argument(
        "--policies",
        nargs="+",
        default=[
            "baseline",
            "cube_all",
            "ptp3_conditional",
            "oddpart_210",
            "oddpart_2310",
            "oddpart_30030",
        ],
        choices=list(pre.POLICY_DESCRIPTIONS),
    )
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--replicates", type=int, default=2)
    ap.add_argument("--n209-replicates", type=int, default=2000)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(
            "results/dark_star_ptp/dark_star_shor_staged_stopping_time_audit.json"
        ),
    )
    args = ap.parse_args()

    excluded = set(pre.EXCLUDED_WHEEL_PRIMES)
    primes = [
        p
        for p in base.sieve_primes(args.prime_max)
        if p >= args.prime_min and p not in excluded
    ]
    pairs = base.choose_semiprimes(
        primes, args.semiprimes, args.ratio_max, args.seed
    )
    if not pairs:
        raise SystemExit("no semiprime pairs matched the requested bounds")

    policies = list(dict.fromkeys(args.policies))
    if "baseline" not in policies:
        policies.insert(0, "baseline")

    rows = []
    theorem_violations = []

    for p, q in pairs:
        n = p * q
        lam = base.lcm(p - 1, q - 1)
        for a in args.bases:
            if math.gcd(a, n) != 1:
                continue

            r = base.multiplicative_order_from_lambda(a, n, lam)
            w0 = pre.factor_witness(a, r, n)
            item = {
                "N": n,
                "base": a,
                "p_validation_only": p,
                "q_validation_only": q,
                "lambda_validation_only": lam,
                "baseline_order_validation_only": r,
                "policies": {},
            }

            for policy in policies:
                L = pre.exponent_for_policy(policy, n)
                b = pow(a, L, n)
                rb = base.multiplicative_order_from_lambda(b, n, lam)
                expected = r // math.gcd(r, L)
                if rb != expected:
                    theorem_violations.append(
                        {
                            "N": n,
                            "base": a,
                            "policy": policy,
                            "type": "order_identity",
                        }
                    )

                w1 = pre.factor_witness(b, rb, n)
                shortcut = qvalue.power2_chain_shortcut(b, n)
                eligible = bool(w0["factor_success"]) and not shortcut["factor_found"]

                sessions = []
                if eligible:
                    for rep in range(args.replicates):
                        rng = deterministic_rng(
                            args.seed, n, a, policy, rep, "staged-nearest"
                        )
                        sessions.append(
                            simulate_session(
                                n,
                                b,
                                rb,
                                start_bits=args.start_bits,
                                step_bits=args.step_bits,
                                shots_per_stage=args.shots_per_stage,
                                rng=rng,
                            )
                        )

                item["policies"][policy] = {
                    "exponent": L,
                    "transformed_base": b,
                    "transformed_order_validation_only": rb,
                    "order_reduction_factor_validation_only": r / rb,
                    "baseline_factor_success": bool(w0["factor_success"]),
                    "transformed_factor_success": bool(w1["factor_success"]),
                    "classical_shortcut": shortcut,
                    "eligible_quantum_row": eligible,
                    "sessions": sessions,
                }

            rows.append(item)

    summary = {p: summarize_sessions(rows, p) for p in policies}
    paired = {
        p: paired_vs_baseline(rows, p)
        for p in policies
        if p != "baseline"
    }
    example = n209_probe(
        start_bits=args.start_bits,
        step_bits=args.step_bits,
        shots_per_stage=args.shots_per_stage,
        replicates=args.n209_replicates,
    )

    result = {
        "experiment": "dark_star_shor_staged_stopping_time_audit_v1",
        "zero_qpu": True,
        "semiprimes": len(pairs),
        "order_rows": len(rows),
        "simulation": {
            "start_bits": args.start_bits,
            "step_bits": args.step_bits,
            "shots_per_stage": args.shots_per_stage,
            "replicates_per_row": args.replicates,
            "cap": "2*bit_length(N)",
            "strict_denominator_rule": (
                "A CF denominator itself must satisfy pow(base,d,N)==1; "
                "no denominator-multiple search is allowed."
            ),
            "nearest_bin_only": True,
            "non_nearest_outcomes": "discarded as conservative failures",
            "stages_are_independent_reruns": True,
            "cumulative_phase_round_executions": (
                "sum of phase-bit precision over every attempted shot"
            ),
            "hidden_order_use": (
                "validation and ideal-QPE sample generation only; never used by "
                "policy, CF recovery, candidate verification, or stop rule"
            ),
        },
        "n209_probe": example,
        "summary": summary,
        "paired_vs_baseline": paired,
        "theorem_violations": theorem_violations,
        "rows": rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== N209 STAGED STOPPING PROBE =====")
    print(json.dumps(example, indent=2))
    print("\n===== STAGED STOPPING SUMMARY =====")
    print(json.dumps(summary, indent=2))
    print("\n===== PAIRED VS BASELINE =====")
    print(json.dumps(paired, indent=2))
    print("\n===== OVERALL =====")
    print(
        json.dumps(
            {
                "pass": not theorem_violations,
                "zero_qpu": True,
                "semiprimes": len(pairs),
                "order_rows": len(rows),
                "theorem_violations": theorem_violations,
                "saved": str(args.out.resolve()),
            },
            indent=2,
        )
    )
    return 0 if not theorem_violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
