#!/usr/bin/env python3
"""Exact Dark-Star/PTP -> Shor constraint audit.

This is a follow-up to `dark_star_ptp_shor_audit.py`.

The first audit showed that the Fermat midpoint quadratic-residue filter gives
real classical candidate pruning, while raw `N mod M` categories gave weak and
sometimes non-generalizing prediction of Shor-order divisibility.

This audit asks a narrower, structural question:

    Given only public N mod M and the kernel factor-pair set
        p*q == N (mod M),
    what divisibility facts about lambda(N)=lcm(p-1,q-1) are actually forced?

For each admissible residue pair we record which odd wheel primes divide at
least one of p-1 or q-1.  Across all residue pairs consistent with N mod M we
then compute:

- guaranteed small-prime divisors of lambda(N): present for every pair;
- possible small-prime divisors: present for at least one pair;
- the number of distinct lambda small-prime support signatures still possible.

The true factors, lambda(N), and multiplicative orders are used only as
validation labels.  They are never used to construct the kernel constraints.

No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import dark_star_ptp_shor_audit as base

DEFAULT_MODULI = (210, 2310, 30030)
DEFAULT_BASES = base.DEFAULT_BASES


def odd_wheel_primes(m: int) -> list[int]:
    return [p for p in base.prime_factors_distinct(m) if p != 2]


def pair_support_mask(pair: tuple[int, int], primes: list[int]) -> int:
    """Bits for wheel primes forced into lambda by this particular pair."""
    r, s = pair
    mask = 0
    for i, ell in enumerate(primes):
        if r % ell == 1 or s % ell == 1:
            mask |= 1 << i
    return mask


def constraint_from_public_residue(n_mod_m: int, m: int) -> dict:
    """Derive lambda small-prime constraints from N mod M only."""
    primes = odd_wheel_primes(m)
    pairs = base.kernel_factor_pairs(n_mod_m, m)
    if not pairs:
        raise ValueError(f"N residue {n_mod_m} is not a unit modulo {m}")

    support_counts = Counter(pair_support_mask(pair, primes) for pair in pairs)
    masks = sorted(support_counts)
    full_mask = (1 << len(primes)) - 1

    guaranteed = full_mask
    possible = 0
    for mask in masks:
        guaranteed &= mask
        possible |= mask

    def mask_primes(mask: int) -> list[int]:
        return [ell for i, ell in enumerate(primes) if mask & (1 << i)]

    return {
        "modulus": m,
        "N_mod_M": int(n_mod_m),
        "odd_wheel_primes": primes,
        "kernel_pair_count": len(pairs),
        "distinct_lambda_support_signatures": len(masks),
        "full_signature_space": 1 << len(primes),
        "signature_reduction_factor": (1 << len(primes)) / len(masks),
        "guaranteed_mask": guaranteed,
        "guaranteed_lambda_primes": mask_primes(guaranteed),
        "possible_mask": possible,
        "possible_lambda_primes": mask_primes(possible),
        "full_support_signature_present": full_mask in support_counts,
        "support_counts": {str(mask): int(count) for mask, count in sorted(support_counts.items())},
    }


def exact_residue_theory(m: int) -> dict:
    """Enumerate every public unit N residue modulo M."""
    primes = odd_wheel_primes(m)
    rows = [constraint_from_public_residue(n, m) for n in base.units_mod(m)]
    full_space = 1 << len(primes)

    guarantee_frequency = {}
    possible_frequency = {}
    for ell in primes:
        guarantee_frequency[str(ell)] = mean(
            1.0 if ell in row["guaranteed_lambda_primes"] else 0.0 for row in rows
        )
        possible_frequency[str(ell)] = mean(
            1.0 if ell in row["possible_lambda_primes"] else 0.0 for row in rows
        )

    signature_counts = [row["distinct_lambda_support_signatures"] for row in rows]
    reductions = [row["signature_reduction_factor"] for row in rows]

    return {
        "modulus": m,
        "unit_N_residues": len(rows),
        "odd_wheel_primes": primes,
        "full_lambda_support_signature_space": full_space,
        "mean_distinct_support_signatures": mean(signature_counts),
        "median_distinct_support_signatures": median(signature_counts),
        "min_distinct_support_signatures": min(signature_counts),
        "max_distinct_support_signatures": max(signature_counts),
        "mean_signature_reduction_factor": mean(reductions),
        "guarantee_frequency_by_prime": guarantee_frequency,
        "possible_frequency_by_prime": possible_frequency,
        "full_support_signature_present_for_every_N_residue": all(
            row["full_support_signature_present"] for row in rows
        ),
        "interpretation": (
            "Guaranteed means every kernel factor-residue pair consistent with public N mod M "
            "forces that prime to divide lambda(N). Possible means at least one consistent pair does."
        ),
    }


def choose_pairs(prime_min: int, prime_max: int, count: int, ratio_max: float, seed: int):
    primes = [
        p
        for p in base.sieve_primes(prime_max)
        if p >= prime_min and p > max(max(base.prime_factors_distinct(m)) for m in DEFAULT_MODULI)
    ]
    pairs = base.choose_semiprimes(primes, count, ratio_max, seed)
    if not pairs:
        raise SystemExit("no semiprime pairs matched requested bounds")
    return pairs


def empirical_audit(
    semiprime_pairs: list[tuple[int, int]],
    bases: list[int],
    moduli: list[int],
) -> dict:
    cache: dict[tuple[int, int], dict] = {}
    by_modulus = {}

    # Build one semiprime-level label row and many order rows per base.
    semiprime_rows = []
    order_rows = []
    for p, q in semiprime_pairs:
        n = p * q
        lam = base.lcm(p - 1, q - 1)
        constraints = {}
        for m in moduli:
            key = (m, n % m)
            if key not in cache:
                cache[key] = constraint_from_public_residue(n % m, m)
            constraints[str(m)] = cache[key]

        semiprime_rows.append({
            "N": n,
            "p": p,
            "q": q,
            "lambda": lam,
            "constraints": constraints,
        })

        for a in bases:
            if math.gcd(a, n) != 1:
                continue
            r = base.multiplicative_order_from_lambda(a, n, lam)
            order_rows.append({
                "N": n,
                "base": a,
                "order": r,
                "lambda": lam,
                "constraints": constraints,
            })

    for m in moduli:
        primes = odd_wheel_primes(m)
        prime_report = {}
        for ell in primes:
            lambda_true = [row["lambda"] % ell == 0 for row in semiprime_rows]
            guaranteed = [
                ell in row["constraints"][str(m)]["guaranteed_lambda_primes"]
                for row in semiprime_rows
            ]

            guarantee_indices = [i for i, g in enumerate(guaranteed) if g]
            violations = [
                semiprime_rows[i]["N"]
                for i in guarantee_indices
                if not lambda_true[i]
            ]

            order_target = [row["order"] % ell == 0 for row in order_rows]
            order_guaranteed = [
                ell in row["constraints"][str(m)]["guaranteed_lambda_primes"]
                for row in order_rows
            ]
            idx_g = [i for i, g in enumerate(order_guaranteed) if g]
            idx_ng = [i for i, g in enumerate(order_guaranteed) if not g]

            baseline_order_rate = mean(order_target) if order_target else None
            g_order_rate = mean(order_target[i] for i in idx_g) if idx_g else None
            ng_order_rate = mean(order_target[i] for i in idx_ng) if idx_ng else None

            by_base = {}
            for a in bases:
                rows_a = [row for row in order_rows if row["base"] == a]
                if not rows_a:
                    continue
                target_a = [row["order"] % ell == 0 for row in rows_a]
                guar_a = [
                    ell in row["constraints"][str(m)]["guaranteed_lambda_primes"]
                    for row in rows_a
                ]
                gi = [i for i, g in enumerate(guar_a) if g]
                ngi = [i for i, g in enumerate(guar_a) if not g]
                by_base[str(a)] = {
                    "rows": len(rows_a),
                    "baseline_r_div_prime_rate": mean(target_a),
                    "r_div_prime_rate_when_lambda_prime_guaranteed": (
                        mean(target_a[i] for i in gi) if gi else None
                    ),
                    "r_div_prime_rate_when_not_guaranteed": (
                        mean(target_a[i] for i in ngi) if ngi else None
                    ),
                }

            prime_report[str(ell)] = {
                "semiprime_rows": len(semiprime_rows),
                "guarantee_coverage": len(guarantee_indices) / len(semiprime_rows),
                "lambda_div_prime_baseline_rate": mean(lambda_true),
                "guarantee_violations": violations,
                "guarantee_precision": (
                    1.0 - len(violations) / len(guarantee_indices)
                    if guarantee_indices else None
                ),
                "order_rows": len(order_rows),
                "r_div_prime_baseline_rate": baseline_order_rate,
                "r_div_prime_rate_when_lambda_prime_guaranteed": g_order_rate,
                "r_div_prime_rate_when_not_guaranteed": ng_order_rate,
                "r_div_prime_lift_when_guaranteed": (
                    g_order_rate - baseline_order_rate
                    if g_order_rate is not None and baseline_order_rate is not None
                    else None
                ),
                "by_base": by_base,
            }

        signature_counts = [
            row["constraints"][str(m)]["distinct_lambda_support_signatures"]
            for row in semiprime_rows
        ]
        reductions = [
            row["constraints"][str(m)]["signature_reduction_factor"]
            for row in semiprime_rows
        ]
        full_present = all(
            row["constraints"][str(m)]["full_support_signature_present"]
            for row in semiprime_rows
        )

        by_modulus[str(m)] = {
            "semiprimes": len(semiprime_rows),
            "order_rows": len(order_rows),
            "mean_distinct_lambda_support_signatures": mean(signature_counts),
            "mean_signature_reduction_factor": mean(reductions),
            "full_support_signature_present_for_every_tested_N": full_present,
            "prime_constraints": prime_report,
        }

    return {
        "semiprime_rows": len(semiprime_rows),
        "order_rows": len(order_rows),
        "by_modulus": by_modulus,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Exact kernel-pair constraints on lambda(N) and Shor order")
    ap.add_argument("--moduli", nargs="+", type=int, default=list(DEFAULT_MODULI))
    ap.add_argument("--prime-min", type=int, default=101)
    ap.add_argument("--prime-max", type=int, default=2000)
    ap.add_argument("--semiprimes", type=int, default=2000)
    ap.add_argument("--ratio-max", type=float, default=2.0)
    ap.add_argument("--bases", nargs="+", type=int, default=list(DEFAULT_BASES))
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("results/dark_star_ptp/dark_star_shor_constraint_audit.json"),
    )
    args = ap.parse_args()

    moduli = list(dict.fromkeys(args.moduli))
    for m in moduli:
        fs = base.prime_factors_distinct(m)
        if math.prod(fs) != m or 2 not in fs:
            raise SystemExit(f"M={m} must be square-free and include 2")

    # Choose primes above every wheel prime so every synthetic factor is a unit.
    max_wheel_prime = max(max(base.prime_factors_distinct(m)) for m in moduli)
    primes = [
        p
        for p in base.sieve_primes(args.prime_max)
        if p >= max(args.prime_min, max_wheel_prime + 1)
    ]
    pairs = base.choose_semiprimes(primes, args.semiprimes, args.ratio_max, args.seed)
    if not pairs:
        raise SystemExit("no semiprime pairs matched requested bounds")

    theory = {str(m): exact_residue_theory(m) for m in moduli}
    empirical = empirical_audit(pairs, args.bases, moduli)

    result = {
        "experiment": "dark_star_shor_constraint_audit_v1",
        "zero_qpu": True,
        "known_factors_used_to_construct_constraints": False,
        "known_order_used_to_construct_constraints": False,
        "moduli": moduli,
        "bases": args.bases,
        "theory": theory,
        "empirical": empirical,
        "interpretation_boundary": {
            "kernel_pairs_come_only_from_N_mod_M": True,
            "true_factors_lambda_order_are_validation_labels_only": True,
            "full_support_signature_note": (
                "The residue pair (1, N mod M) is always kernel-consistent for unit N, "
                "so the support signature containing every wheel prime is always possible."
            ),
            "qpe_claim": (
                "A guaranteed divisor of lambda(N) is not automatically a guaranteed divisor of order r. "
                "This audit therefore does not claim a QPE-width reduction."
            ),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== EXACT KERNEL-CONSTRAINT THEORY =====")
    print(json.dumps(theory, indent=2))

    print("\n===== EMPIRICAL CONSTRAINT SUMMARY =====")
    compact = {}
    for m, block in empirical["by_modulus"].items():
        compact[m] = {
            "semiprimes": block["semiprimes"],
            "order_rows": block["order_rows"],
            "mean_distinct_lambda_support_signatures": block["mean_distinct_lambda_support_signatures"],
            "mean_signature_reduction_factor": block["mean_signature_reduction_factor"],
            "full_support_signature_present_for_every_tested_N": block["full_support_signature_present_for_every_tested_N"],
            "prime_constraints": {},
        }
        for ell, pblock in block["prime_constraints"].items():
            compact[m]["prime_constraints"][ell] = {
                "guarantee_coverage": pblock["guarantee_coverage"],
                "guarantee_precision": pblock["guarantee_precision"],
                "lambda_div_prime_baseline_rate": pblock["lambda_div_prime_baseline_rate"],
                "r_div_prime_baseline_rate": pblock["r_div_prime_baseline_rate"],
                "r_div_prime_rate_when_lambda_prime_guaranteed": pblock["r_div_prime_rate_when_lambda_prime_guaranteed"],
                "r_div_prime_lift_when_guaranteed": pblock["r_div_prime_lift_when_guaranteed"],
            }
    print(json.dumps(compact, indent=2))

    violations = []
    for m, block in empirical["by_modulus"].items():
        for ell, pblock in block["prime_constraints"].items():
            if pblock["guarantee_violations"]:
                violations.extend((m, ell, n) for n in pblock["guarantee_violations"])

    overall = {
        "pass": not violations,
        "zero_qpu": True,
        "semiprimes": len(pairs),
        "order_rows": empirical["order_rows"],
        "guarantee_violations": violations,
        "saved": str(args.out.resolve()),
    }
    print("\n===== OVERALL =====")
    print(json.dumps(overall, indent=2))
    return 0 if overall["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
