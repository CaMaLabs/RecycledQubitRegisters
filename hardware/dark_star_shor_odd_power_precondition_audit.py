#!/usr/bin/env python3
"""Zero-QPU audit of odd-power base preconditioning for Shor factorization.

For a coprime base a with order r modulo N and any odd exponent L, define

    b = a^L mod N.

Then

    ord_N(b) = r / gcd(r, L).

Because gcd(r, L) is odd, the parity of the order is unchanged.  If r is even,
the Shor half-order witness is also unchanged:

    b^(ord(b)/2) = a^(r/2) mod N.

Therefore the standard gcd factor-extraction outcome is preserved exactly while
odd factors shared by r and L are stripped from the quantum order-finding
problem.

This audit measures how much order shortening occurs for public, factor-free
policies inspired by the Dark-Star/PTP wheel moduli.  It also measures whether
the powered base already exposes a factor through gcd(b-1, N), i.e. the classical
Pollard-p-1-style side effect.

True p, q, lambda(N), and r are validation labels only.  They are never used to
choose the exponent or construct b.  No IBM service is contacted and no QPU job
is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base

DEFAULT_BASES = tuple(base.DEFAULT_BASES)
EXCLUDED_WHEEL_PRIMES = (2, 3, 5, 7, 11, 13)

POLICY_DESCRIPTIONS = {
    "baseline": "L=1",
    "cube_all": "L=3 for every N",
    "ptp3_conditional": "L=3 only when public N mod 3 == 2; otherwise L=1",
    "oddpart_210": "L=3*5*7=105",
    "oddpart_2310": "L=3*5*7*11=1155",
    "oddpart_30030": "L=3*5*7*11*13=15015",
}


def exponent_for_policy(name: str, n: int) -> int:
    if name == "baseline":
        return 1
    if name == "cube_all":
        return 3
    if name == "ptp3_conditional":
        return 3 if n % 3 == 2 else 1
    if name == "oddpart_210":
        return 105
    if name == "oddpart_2310":
        return 1155
    if name == "oddpart_30030":
        return 15015
    raise KeyError(name)


def ceil_log2(x: int) -> int:
    if x <= 1:
        return 0
    return (x - 1).bit_length()


def cf_precision_proxy_bits(r: int) -> int:
    """Validation-only denominator-resolution proxy ceil(log2(2*r^2))."""
    return ceil_log2(2 * r * r)


def factor_witness(a: int, r: int, n: int) -> dict:
    if r % 2:
        return {
            "order_even": False,
            "half_power": None,
            "gcd_minus": None,
            "gcd_plus": None,
            "factor_success": False,
        }
    x = pow(a, r // 2, n)
    gm = math.gcd(x - 1, n)
    gp = math.gcd(x + 1, n)
    return {
        "order_even": True,
        "half_power": x,
        "gcd_minus": gm,
        "gcd_plus": gp,
        "factor_success": (1 < gm < n) or (1 < gp < n),
    }


def compact_factor_pair(w: dict, n: int) -> tuple[int, ...]:
    vals = []
    for key in ("gcd_minus", "gcd_plus"):
        g = w.get(key)
        if g is not None and 1 < g < n:
            vals.append(int(g))
    return tuple(sorted(set(vals)))


def summarize_policy(rows: list[dict], policy: str) -> dict:
    p_rows = [r["policies"][policy] for r in rows]
    quantum_remaining = [r for r in p_rows if not r["classical_prefactor_found"]]
    even = [r for r in p_rows if r["baseline_order_even"]]

    def avg(key: str, src):
        vals = [float(r[key]) for r in src]
        return mean(vals) if vals else None

    def med(key: str, src):
        vals = [float(r[key]) for r in src]
        return median(vals) if vals else None

    return {
        "description": POLICY_DESCRIPTIONS[policy],
        "rows": len(p_rows),
        "classical_prefactor_rate": (
            sum(r["classical_prefactor_found"] for r in p_rows) / len(p_rows)
            if p_rows else None
        ),
        "order_reduced_fraction": (
            sum(r["transformed_order"] < r["baseline_order"] for r in p_rows) / len(p_rows)
            if p_rows else None
        ),
        "mean_order_reduction_factor": avg("order_reduction_factor", p_rows),
        "median_order_reduction_factor": med("order_reduction_factor", p_rows),
        "mean_order_bitlength_saved": avg("order_bitlength_saved", p_rows),
        "mean_cf_precision_proxy_bits_saved": avg("cf_precision_proxy_bits_saved", p_rows),
        "quantum_remaining_rows_after_prefactor": len(quantum_remaining),
        "quantum_remaining_mean_order_reduction_factor": avg(
            "order_reduction_factor", quantum_remaining
        ),
        "quantum_remaining_median_order_reduction_factor": med(
            "order_reduction_factor", quantum_remaining
        ),
        "even_order_rows": len(even),
        "half_order_witness_preservation_rate": (
            sum(r["half_order_witness_preserved"] for r in even) / len(even)
            if even else None
        ),
        "factor_extraction_preservation_rate": (
            sum(r["factor_extraction_preserved"] for r in even) / len(even)
            if even else None
        ),
    }


def n35_example() -> dict:
    n = 35
    p, q = 5, 7
    a = 2
    lam = base.lcm(p - 1, q - 1)
    r = base.multiplicative_order_from_lambda(a, n, lam)
    L = 3 if n % 3 == 2 else 1
    b = pow(a, L, n)
    rb = base.multiplicative_order_from_lambda(b, n, lam)
    w0 = factor_witness(a, r, n)
    w1 = factor_witness(b, rb, n)
    return {
        "N": n,
        "public_condition_N_mod_3_eq_2": n % 3 == 2,
        "seed_base": a,
        "public_exponent": L,
        "transformed_base": b,
        "baseline_order_validation_only": r,
        "transformed_order_validation_only": rb,
        "order_reduction_factor": r / rb,
        "baseline_half_order_witness": w0["half_power"],
        "transformed_half_order_witness": w1["half_power"],
        "witness_preserved": w0["half_power"] == w1["half_power"],
        "baseline_factor_pair": list(compact_factor_pair(w0, n)),
        "transformed_factor_pair": list(compact_factor_pair(w1, n)),
        "factor_extraction_preserved": compact_factor_pair(w0, n)
        == compact_factor_pair(w1, n),
        "order_used_to_choose_exponent": False,
        "factor_used_to_choose_exponent": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU odd-power Shor base-preconditioning audit"
    )
    ap.add_argument("--prime-min", type=int, default=101)
    ap.add_argument("--prime-max", type=int, default=2000)
    ap.add_argument("--semiprimes", type=int, default=2000)
    ap.add_argument("--ratio-max", type=float, default=2.0)
    ap.add_argument("--bases", nargs="+", type=int, default=list(DEFAULT_BASES))
    ap.add_argument("--seed", type=int, default=8777)
    ap.add_argument(
        "--policies",
        nargs="+",
        default=list(POLICY_DESCRIPTIONS),
        choices=list(POLICY_DESCRIPTIONS),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(
            "results/dark_star_ptp/dark_star_shor_odd_power_precondition_audit.json"
        ),
    )
    args = ap.parse_args()

    excluded = set(EXCLUDED_WHEEL_PRIMES)
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
    by_base: dict[str, dict[int, list[float]]] = {
        p: defaultdict(list) for p in policies
    }

    for p, q in pairs:
        n = p * q
        lam = base.lcm(p - 1, q - 1)
        for a in args.bases:
            if math.gcd(a, n) != 1:
                continue
            r = base.multiplicative_order_from_lambda(a, n, lam)
            w0 = factor_witness(a, r, n)
            item = {
                "N": n,
                "p_validation_only": p,
                "q_validation_only": q,
                "base": a,
                "lambda_validation_only": lam,
                "baseline_order_validation_only": r,
                "N_mod_3": n % 3,
                "policies": {},
            }

            for policy in policies:
                L = exponent_for_policy(policy, n)
                if L % 2 == 0:
                    raise AssertionError("all tested preconditioning exponents must be odd")
                b = pow(a, L, n)
                rb = base.multiplicative_order_from_lambda(b, n, lam)
                expected = r // math.gcd(r, L)
                if rb != expected:
                    theorem_violations.append(
                        {
                            "type": "order_formula",
                            "N": n,
                            "base": a,
                            "policy": policy,
                            "L": L,
                            "r": r,
                            "got": rb,
                            "expected": expected,
                        }
                    )

                w1 = factor_witness(b, rb, n)
                witness_preserved = (
                    (not w0["order_even"])
                    or (w0["half_power"] == w1["half_power"])
                )
                factor_preserved = compact_factor_pair(w0, n) == compact_factor_pair(
                    w1, n
                )
                if not witness_preserved or not factor_preserved:
                    theorem_violations.append(
                        {
                            "type": "factor_witness",
                            "N": n,
                            "base": a,
                            "policy": policy,
                            "L": L,
                            "r": r,
                            "rb": rb,
                            "baseline": w0,
                            "transformed": w1,
                        }
                    )

                g = math.gcd(b - 1, n)
                prefactor = 1 < g < n
                reduction = r / rb
                by_base[policy][a].append(reduction)

                item["policies"][policy] = {
                    "exponent": L,
                    "transformed_base": b,
                    "baseline_order": r,
                    "transformed_order": rb,
                    "order_reduction_factor": reduction,
                    "order_bitlength_saved": r.bit_length() - rb.bit_length(),
                    "cf_precision_proxy_bits_saved": cf_precision_proxy_bits(r)
                    - cf_precision_proxy_bits(rb),
                    "classical_prefactor_found": prefactor,
                    "classical_prefactor": g if prefactor else None,
                    "baseline_order_even": w0["order_even"],
                    "transformed_order_even": w1["order_even"],
                    "half_order_witness_preserved": witness_preserved,
                    "factor_extraction_preserved": factor_preserved,
                }

            rows.append(item)

    summary = {p: summarize_policy(rows, p) for p in policies}

    base_summary = {}
    for policy in policies:
        base_summary[policy] = {}
        for a, vals in sorted(by_base[policy].items()):
            base_summary[policy][str(a)] = {
                "rows": len(vals),
                "fraction_order_reduced": sum(v > 1 for v in vals) / len(vals),
                "mean_order_reduction_factor": mean(vals),
                "median_order_reduction_factor": median(vals),
            }

    cube = "cube_all"
    split = {}
    if cube in policies:
        for cond_name, predicate in (
            ("N_mod_3_eq_2", lambda n: n % 3 == 2),
            ("N_mod_3_eq_1", lambda n: n % 3 == 1),
        ):
            vals = [
                r["policies"][cube]
                for r in rows
                if predicate(r["N"])
            ]
            split[cond_name] = {
                "rows": len(vals),
                "fraction_order_reduced": (
                    sum(v["transformed_order"] < v["baseline_order"] for v in vals)
                    / len(vals)
                    if vals else None
                ),
                "mean_order_reduction_factor": (
                    mean(v["order_reduction_factor"] for v in vals) if vals else None
                ),
                "median_order_reduction_factor": (
                    median(v["order_reduction_factor"] for v in vals) if vals else None
                ),
            }

    result = {
        "experiment": "dark_star_shor_odd_power_precondition_audit_v1",
        "zero_qpu": True,
        "semiprimes": len(pairs),
        "order_rows": len(rows),
        "bases": args.bases,
        "policies": policies,
        "theorem": {
            "order_identity": "ord(a^L) = ord(a) / gcd(ord(a), L)",
            "odd_L_preserves_order_parity": True,
            "odd_L_preserves_half_order_witness_when_order_even": True,
            "factor_extraction_consequence": (
                "For odd L, transforming a -> a^L preserves the standard Shor "
                "factor-extraction success/failure outcome for that sampled a."
            ),
            "resource_boundary": (
                "Smaller actual order does not by itself lower the textbook worst-case "
                "QPE width. The CF precision metric below is validation-only; an adaptive "
                "or recycled phase-estimation implementation would be needed to exploit "
                "actual shorter orders without knowing r in advance."
            ),
        },
        "n35_public_cube_example": n35_example(),
        "summary": summary,
        "cube_condition_split": split,
        "by_base": base_summary,
        "theorem_violations": theorem_violations,
        "rows": rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== N35 PUBLIC-CUBE EXAMPLE =====")
    print(json.dumps(result["n35_public_cube_example"], indent=2))
    print("\n===== POLICY SUMMARY =====")
    print(json.dumps(summary, indent=2))
    print("\n===== CUBE CONDITION SPLIT =====")
    print(json.dumps(split, indent=2))
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
