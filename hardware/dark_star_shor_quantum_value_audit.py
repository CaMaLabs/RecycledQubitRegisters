#!/usr/bin/env python3
"""Zero-QPU audit of whether odd-power Shor preconditioning leaves real quantum work.

This follows `dark_star_shor_odd_power_precondition_audit.py` but adds a strict
classical-shortcut gate.  For each public transformed base

    b = a^L mod N

we test the cheap classical operations that would be available before any QPU
submission:

1. gcd(b - 1, N) and gcd(b + 1, N);
2. repeated squaring x_k = b^(2^k) mod N, checking gcd(x_k - 1, N) and
   gcd(x_k + 1, N) at every step.

If any of these reveals a non-trivial factor, that row is *not* counted as a
quantum-useful Shor reduction, even if the transformed order is much smaller.

The true p, q, lambda(N), and multiplicative orders are validation labels only.
They are never used to choose L, construct b, or perform the classical shortcut
checks.  No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre


def nontrivial_factor(g: int, n: int) -> int | None:
    return int(g) if 1 < g < n else None


def power2_chain_shortcut(b: int, n: int, max_steps: int | None = None) -> dict:
    """Classical repeated-squaring/GCD audit using only public b and N.

    At step k, x = b^(2^k) mod N.  A non-trivial gcd(x-1,N) or gcd(x+1,N)
    is an immediately available classical factor and therefore disqualifies the
    case as evidence that the order reduction still requires quantum work.
    """
    if max_steps is None:
        # ord_N(b) <= lambda(N) < N for the semiprimes tested here.  This is a
        # public-size bound; no hidden order information is used.
        max_steps = max(2, n.bit_length() + 1)

    direct = nontrivial_factor(math.gcd(b, n), n)
    if direct is not None:
        return {
            "factor_found": True,
            "factor": direct,
            "source": "gcd(b,N)",
            "step": None,
            "power_exponent": None,
            "events": [],
        }

    x = b % n
    events = []
    for k in range(max_steps + 1):
        gm = nontrivial_factor(math.gcd(x - 1, n), n)
        gp = nontrivial_factor(math.gcd(x + 1, n), n)
        event = {
            "step": k,
            "power_exponent": 1 << k,
            "x": int(x),
            "gcd_minus": int(math.gcd(x - 1, n)),
            "gcd_plus": int(math.gcd(x + 1, n)),
        }
        events.append(event)
        factor = gm if gm is not None else gp
        if factor is not None:
            return {
                "factor_found": True,
                "factor": factor,
                "source": "power2_chain_gcd_minus" if gm is not None else "power2_chain_gcd_plus",
                "step": k,
                "power_exponent": 1 << k,
                "events": events,
            }
        if x == 1:
            return {
                "factor_found": False,
                "factor": None,
                "source": "hit_one_without_nontrivial_gcd",
                "step": k,
                "power_exponent": 1 << k,
                "events": events,
            }
        x = (x * x) % n

    return {
        "factor_found": False,
        "factor": None,
        "source": "step_limit",
        "step": max_steps,
        "power_exponent": 1 << max_steps,
        "events": events,
    }


def summarize_policy(rows: list[dict], policy: str) -> dict:
    vals = [row["policies"][policy] for row in rows]
    successful = [v for v in vals if v["baseline_factor_success"]]
    quantum_remaining = [
        v for v in successful if not v["classical_shortcut"]["factor_found"]
    ]
    quantum_reduced = [
        v for v in quantum_remaining if v["transformed_order"] < v["baseline_order"]
    ]

    def frac(num: int, den: int):
        return num / den if den else None

    def avg(key: str, src: list[dict]):
        return mean(float(v[key]) for v in src) if src else None

    def med(key: str, src: list[dict]):
        return median(float(v[key]) for v in src) if src else None

    return {
        "description": pre.POLICY_DESCRIPTIONS[policy],
        "rows": len(vals),
        "baseline_shor_success_rows": len(successful),
        "order_reduced_fraction_all_rows": frac(
            sum(v["transformed_order"] < v["baseline_order"] for v in vals), len(vals)
        ),
        "classical_shortcut_rate_all_rows": frac(
            sum(v["classical_shortcut"]["factor_found"] for v in vals), len(vals)
        ),
        "classical_shortcut_rate_on_shor_success_rows": frac(
            sum(v["classical_shortcut"]["factor_found"] for v in successful),
            len(successful),
        ),
        "quantum_remaining_success_rows": len(quantum_remaining),
        "quantum_remaining_fraction_of_success_rows": frac(
            len(quantum_remaining), len(successful)
        ),
        "quantum_useful_order_reduction_rows": len(quantum_reduced),
        "quantum_useful_order_reduction_fraction_of_remaining": frac(
            len(quantum_reduced), len(quantum_remaining)
        ),
        "quantum_remaining_mean_order_reduction_factor": avg(
            "order_reduction_factor", quantum_remaining
        ),
        "quantum_remaining_median_order_reduction_factor": med(
            "order_reduction_factor", quantum_remaining
        ),
        "quantum_reduced_mean_order_reduction_factor": avg(
            "order_reduction_factor", quantum_reduced
        ),
        "quantum_reduced_mean_order_bitlength_saved": avg(
            "order_bitlength_saved", quantum_reduced
        ),
        "quantum_reduced_mean_cf_precision_proxy_bits_saved": avg(
            "cf_precision_proxy_bits_saved", quantum_reduced
        ),
    }


def n35_guardrail() -> dict:
    n = 35
    a = 2
    L = 3 if n % 3 == 2 else 1
    b = pow(a, L, n)
    shortcut = power2_chain_shortcut(b, n)
    return {
        "N": n,
        "seed_base": a,
        "public_rule": "L=3 when N mod 3 == 2",
        "N_mod_3": n % 3,
        "exponent": L,
        "transformed_base": b,
        "immediate_gcd_b_minus_1": math.gcd(b - 1, n),
        "immediate_gcd_b_plus_1": math.gcd(b + 1, n),
        "classical_shortcut": shortcut,
        "quantum_demonstration_valid_after_this_preconditioning": not shortcut["factor_found"],
        "interpretation": (
            "If the public preconditioning already exposes a non-trivial factor, "
            "a subsequent QPU run is a compiler/hardware exercise, not evidence that "
            "quantum order finding was required for that instance."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Audit whether odd-power Shor preconditioning leaves genuine quantum work"
    )
    ap.add_argument("--prime-min", type=int, default=101)
    ap.add_argument("--prime-max", type=int, default=2000)
    ap.add_argument("--semiprimes", type=int, default=2000)
    ap.add_argument("--ratio-max", type=float, default=2.0)
    ap.add_argument("--bases", nargs="+", type=int, default=list(pre.DEFAULT_BASES))
    ap.add_argument("--seed", type=int, default=8777)
    ap.add_argument(
        "--policies",
        nargs="+",
        default=list(pre.POLICY_DESCRIPTIONS),
        choices=list(pre.POLICY_DESCRIPTIONS),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("results/dark_star_ptp/dark_star_shor_quantum_value_audit.json"),
    )
    args = ap.parse_args()

    excluded = set(pre.EXCLUDED_WHEEL_PRIMES)
    primes = [
        p
        for p in base.sieve_primes(args.prime_max)
        if p >= args.prime_min and p not in excluded
    ]
    pairs = base.choose_semiprimes(primes, args.semiprimes, args.ratio_max, args.seed)
    if not pairs:
        raise SystemExit("no semiprime pairs matched the requested bounds")

    policies = list(dict.fromkeys(args.policies))
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
                if L % 2 == 0:
                    raise AssertionError("preconditioning exponent must be odd")
                b = pow(a, L, n)
                rb = base.multiplicative_order_from_lambda(b, n, lam)
                expected = r // math.gcd(r, L)
                if rb != expected:
                    theorem_violations.append(
                        {"N": n, "base": a, "policy": policy, "type": "order_identity"}
                    )

                w1 = pre.factor_witness(b, rb, n)
                same_witness = (
                    (not w0["order_even"])
                    or w0["half_power"] == w1["half_power"]
                )
                same_factors = pre.compact_factor_pair(w0, n) == pre.compact_factor_pair(w1, n)
                if not same_witness or not same_factors:
                    theorem_violations.append(
                        {"N": n, "base": a, "policy": policy, "type": "witness_preservation"}
                    )

                shortcut = power2_chain_shortcut(b, n)
                item["policies"][policy] = {
                    "exponent": L,
                    "transformed_base": b,
                    "baseline_order": r,
                    "transformed_order": rb,
                    "order_reduction_factor": r / rb,
                    "order_bitlength_saved": r.bit_length() - rb.bit_length(),
                    "cf_precision_proxy_bits_saved": pre.cf_precision_proxy_bits(r)
                    - pre.cf_precision_proxy_bits(rb),
                    "baseline_factor_success": bool(w0["factor_success"]),
                    "transformed_factor_success": bool(w1["factor_success"]),
                    "half_order_witness_preserved": same_witness,
                    "factor_extraction_preserved": same_factors,
                    "classical_shortcut": shortcut,
                }

            rows.append(item)

    summary = {policy: summarize_policy(rows, policy) for policy in policies}
    guardrail = n35_guardrail()

    result = {
        "experiment": "dark_star_shor_quantum_value_audit_v1",
        "zero_qpu": True,
        "known_factors_used_to_choose_policy": False,
        "known_order_used_to_choose_policy": False,
        "semiprimes": len(pairs),
        "order_rows": len(rows),
        "policies": policies,
        "n35_guardrail": guardrail,
        "summary": summary,
        "theorem_violations": theorem_violations,
        "notes": [
            "A transformed-order reduction counts as quantum-useful only when the baseline Shor row succeeds and public classical GCD/repeated-squaring checks do not already reveal a factor.",
            "The repeated-squaring step limit is derived from public N bit length, not hidden order information.",
            "Order and factor labels are used only after construction to score the experiment.",
        ],
        "rows": rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== N35 GUARDRAIL =====")
    print(json.dumps(guardrail, indent=2))
    print("\n===== QUANTUM-VALUE POLICY SUMMARY =====")
    print(json.dumps(summary, indent=2))
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
