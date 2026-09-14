#!/usr/bin/env python3
"""Zero-QPU adaptive-precision bound audit for Dark-Star/Shor preconditioning.

This experiment asks the next resource question after
`dark_star_shor_quantum_value_audit.py`:

    If a public odd-power transformation b = a^L mod N shortens the true order,
    how much *phase precision* could a recycled/adaptive order-finding workflow
    potentially save without being told the order?

The tested public workflow is conceptually:

1. choose L from a fixed public policy using only N;
2. construct b = a^L mod N;
3. run a chosen phase-estimation precision;
4. continued-fraction postprocess the measured phase;
5. verify every candidate denominator with public modular arithmetic;
6. increase precision only if no verified factor/order candidate is obtained.

This file does NOT simulate the full stopping-time distribution.  Instead it
scores the conservative continued-fraction precision proxy already used in the
project,

    m_cf(r) = ceil(log2(2 r^2)),

using the true order only as a validation label.  The public algorithm does not
know m_cf(r); it only knows whether a candidate verifies.  Therefore the reported
bit/round savings are an *available precision-bound reduction*, not a demonstrated
expected-runtime speedup.

For rows where textbook Shor factor extraction succeeds, the script also reports
an elementary single-shot lower bound valid once this conservative precision is
reached:

    (4/pi^2) * phi(r)/r.

This combines the standard nearest-QPE-bin lower bound with the probability that
the sampled eigenphase numerator is coprime to r.  It is a lower bound for full
order recovery under the sufficient-precision condition, not a hardware-fidelity
prediction.

As in the previous audit, a row only counts as quantum-relevant if cheap public
GCD/repeated-squaring checks on the transformed base do not already reveal a
factor.  No IBM service is contacted and no QPU job is submitted.
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


def qpe_full_order_lower_bound(r: int) -> float:
    if r <= 0:
        raise ValueError("order must be positive")
    return (4.0 / (math.pi * math.pi)) * (base.phi(r) / r)


def n209_example() -> dict:
    """Small public-cube example that survives the classical shortcut guardrail."""
    n = 209  # validation identity: 11 * 19
    a = 3
    L = 3 if n % 3 == 2 else 1
    b = pow(a, L, n)

    # p,q are validation labels only; they are not used to choose L or b.
    p, q = 11, 19
    lam = base.lcm(p - 1, q - 1)
    r = base.multiplicative_order_from_lambda(a, n, lam)
    rb = base.multiplicative_order_from_lambda(b, n, lam)
    w0 = pre.factor_witness(a, r, n)
    w1 = pre.factor_witness(b, rb, n)
    shortcut = qvalue.power2_chain_shortcut(b, n)

    return {
        "N": n,
        "seed_base": a,
        "public_rule": "L=3 when N mod 3 == 2",
        "N_mod_3": n % 3,
        "exponent": L,
        "transformed_base": b,
        "classical_shortcut_found": shortcut["factor_found"],
        "classical_shortcut": shortcut,
        "baseline_order_validation_only": r,
        "transformed_order_validation_only": rb,
        "order_reduction_factor": r / rb,
        "baseline_cf_precision_proxy_bits_validation_only": pre.cf_precision_proxy_bits(r),
        "transformed_cf_precision_proxy_bits_validation_only": pre.cf_precision_proxy_bits(rb),
        "cf_precision_proxy_bits_saved": pre.cf_precision_proxy_bits(r)
        - pre.cf_precision_proxy_bits(rb),
        "baseline_factor_success": w0["factor_success"],
        "transformed_factor_success": w1["factor_success"],
        "half_order_witness_preserved": w0["half_power"] == w1["half_power"],
        "factor_pair_preserved": pre.compact_factor_pair(w0, n)
        == pre.compact_factor_pair(w1, n),
        "baseline_full_order_single_shot_lower_bound_at_proxy_precision": qpe_full_order_lower_bound(r),
        "transformed_full_order_single_shot_lower_bound_at_proxy_precision": qpe_full_order_lower_bound(rb),
        "order_used_to_choose_exponent": False,
        "factor_used_to_choose_exponent": False,
    }


def summarize(rows: list[dict], policy: str) -> dict:
    vals = [row["policies"][policy] for row in rows]
    successful = [v for v in vals if v["baseline_factor_success"]]
    remaining = [v for v in successful if not v["classical_shortcut"]["factor_found"]]
    reduced = [v for v in remaining if v["transformed_order"] < v["baseline_order"]]

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
        "quantum_remaining_success_rows": len(remaining),
        "quantum_reduced_rows": len(reduced),
        "quantum_reduced_fraction_of_remaining": frac(len(reduced), len(remaining)),
        "mean_baseline_cf_precision_proxy_bits_remaining": avg("baseline_cf_bits", remaining),
        "mean_transformed_cf_precision_proxy_bits_remaining": avg("transformed_cf_bits", remaining),
        "mean_cf_precision_proxy_bits_saved_remaining": avg("cf_bits_saved", remaining),
        "median_cf_precision_proxy_bits_saved_remaining": med("cf_bits_saved", remaining),
        "mean_cf_precision_proxy_bits_saved_reduced_only": avg("cf_bits_saved", reduced),
        "mean_fractional_precision_reduction_reduced_only": avg(
            "cf_fraction_saved", reduced
        ),
        "mean_baseline_full_order_lower_bound_remaining": avg(
            "baseline_full_order_lower_bound", remaining
        ),
        "mean_transformed_full_order_lower_bound_remaining": avg(
            "transformed_full_order_lower_bound", remaining
        ),
        "mean_lower_bound_ratio_transformed_over_baseline_remaining": avg(
            "full_order_lower_bound_ratio", remaining
        ),
        "fixed_textbook_qpe_width_changed_by_policy": False,
        "interpretation": (
            "Savings describe a validation-only sufficient-precision proxy for an adaptive/recycled "
            "workflow. A conventional fixed-width Shor circuit sized from N is not automatically shorter."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Audit adaptive phase-precision bounds after public odd-power Shor preconditioning"
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
        default=Path("results/dark_star_ptp/dark_star_shor_adaptive_precision_bound_audit.json"),
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
        nbits = n.bit_length()
        for a in args.bases:
            if math.gcd(a, n) != 1:
                continue
            r = base.multiplicative_order_from_lambda(a, n, lam)
            w0 = pre.factor_witness(a, r, n)
            item = {
                "N": n,
                "base": a,
                "N_bits": nbits,
                "fixed_textbook_phase_bits": 2 * nbits,
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

                shortcut = qvalue.power2_chain_shortcut(b, n)
                mb = pre.cf_precision_proxy_bits(r)
                mt = pre.cf_precision_proxy_bits(rb)
                lb0 = qpe_full_order_lower_bound(r)
                lb1 = qpe_full_order_lower_bound(rb)

                item["policies"][policy] = {
                    "exponent": L,
                    "transformed_base": b,
                    "baseline_order": r,
                    "transformed_order": rb,
                    "order_reduction_factor": r / rb,
                    "baseline_factor_success": bool(w0["factor_success"]),
                    "transformed_factor_success": bool(w1["factor_success"]),
                    "classical_shortcut": shortcut,
                    "baseline_cf_bits": mb,
                    "transformed_cf_bits": mt,
                    "cf_bits_saved": mb - mt,
                    "cf_fraction_saved": ((mb - mt) / mb) if mb else 0.0,
                    "baseline_full_order_lower_bound": lb0,
                    "transformed_full_order_lower_bound": lb1,
                    "full_order_lower_bound_ratio": lb1 / lb0 if lb0 else None,
                    "fixed_textbook_phase_bits": 2 * nbits,
                    "fixed_textbook_phase_bits_saved": 0,
                }

            rows.append(item)

    summary = {policy: summarize(rows, policy) for policy in policies}
    example = n209_example()

    result = {
        "experiment": "dark_star_shor_adaptive_precision_bound_audit_v1",
        "zero_qpu": True,
        "known_factors_used_to_choose_policy": False,
        "known_order_used_to_choose_policy": False,
        "semiprimes": len(pairs),
        "order_rows": len(rows),
        "public_stop_rule": (
            "Increase phase precision only when continued-fraction candidates fail public modular-order/factor verification."
        ),
        "validation_proxy": "ceil(log2(2*r^2)); r is used only after construction to score sufficient precision",
        "fixed_width_boundary": (
            "A conventional Shor circuit that always allocates 2*bit_length(N) phase bits receives no automatic width reduction. "
            "Any practical saving requires adaptive/staged or otherwise variable-precision phase estimation."
        ),
        "n209_public_cube_example": example,
        "summary": summary,
        "theorem_violations": theorem_violations,
        "rows": rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== N209 PUBLIC-CUBE EXAMPLE =====")
    print(json.dumps(example, indent=2))
    print("\n===== ADAPTIVE PRECISION BOUND SUMMARY =====")
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
