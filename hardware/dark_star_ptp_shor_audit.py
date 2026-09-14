#!/usr/bin/env python3
"""Dark-Star / Periodic-Table-of-Primes / Shor audit.

This is a classical, zero-QPU experiment. It asks three separate questions:

1. How much does a primorial wheel (210, 2310, 30030) reduce candidate
   factor residues?
2. How much stronger is the Fermat-midpoint filter
      x^2 - N is a quadratic residue modulo M
   than ordinary wheel filtering?
3. Does the public information N mod M carry enough information about Shor's
   multiplicative order r to plausibly reduce phase-estimation work?

The script deliberately separates:
- usable information: N and N mod M;
- oracle information: the true p mod M / q mod M classes, used only to verify
  the kernel-pair construction;
- validation information: p, q, lambda(N), and r for synthetic semiprimes.

No known factors or order are used by the tested filters/search constructors.
No IBM service is contacted and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

DEFAULT_MODULI = (210, 2310, 30030)
DEFAULT_BASES = (2, 3, 5, 7, 11, 13, 17, 19)


def factor_int(n: int) -> dict[int, int]:
    out: dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            out[d] = out.get(d, 0) + 1
            n //= d
        d = 3 if d == 2 else d + 2
    if n > 1:
        out[n] = out.get(n, 0) + 1
    return out


def prime_factors_distinct(n: int) -> list[int]:
    return sorted(factor_int(n))


def phi(n: int) -> int:
    out = n
    for p in prime_factors_distinct(n):
        out -= out // p
    return out


def sieve_primes(limit: int) -> list[int]:
    if limit < 2:
        return []
    s = bytearray(b"\x01") * (limit + 1)
    s[0:2] = b"\x00\x00"
    for p in range(2, math.isqrt(limit) + 1):
        if s[p]:
            s[p * p : limit + 1 : p] = b"\x00" * (((limit - p * p) // p) + 1)
    return [i for i in range(2, limit + 1) if s[i]]


def ceil_sqrt(n: int) -> int:
    r = math.isqrt(n)
    return r if r * r == n else r + 1


def is_square(n: int) -> bool:
    if n < 0:
        return False
    r = math.isqrt(n)
    return r * r == n


def units_mod(m: int) -> list[int]:
    return [x for x in range(m) if math.gcd(x, m) == 1]


def quadratic_residues(m: int) -> set[int]:
    return {(x * x) % m for x in range(m)}


def kernel_factor_pairs(n: int, m: int) -> list[tuple[int, int]]:
    """Unordered residue pairs (p mod M, q mod M) consistent with pq=N mod M."""
    if math.gcd(n, m) != 1:
        return []
    pairs = set()
    for r in units_mod(m):
        s = (n * pow(r, -1, m)) % m
        pairs.add(tuple(sorted((r, s))))
    return sorted(pairs)


def kernel_pair_theory(m: int) -> dict:
    """Closed-form pair-count structure for square-free primorial-style M."""
    fs = prime_factors_distinct(m)
    if math.prod(fs) != m:
        raise ValueError(f"M={m} must be square-free for this audit")
    odd = [p for p in fs if p != 2]
    ph = phi(m)
    root_count_if_qr = 2 ** len(odd)
    ordinary = ph // 2
    special = (ph + root_count_if_qr) // 2
    special_residue_count = ph // (2 ** len(odd))
    return {
        "modulus": m,
        "prime_factors": fs,
        "phi": ph,
        "unit_density": ph / m,
        "classical_wheel_reduction_factor": m / ph,
        "ideal_grover_query_reduction_from_wheel": math.sqrt(m / ph),
        "kernel_pairs_ordinary": ordinary,
        "kernel_pairs_when_N_is_unit_quadratic_residue": special,
        "unit_N_residues_with_special_count": special_residue_count,
        "unit_N_residues_total": ph,
    }


def midpoint_filter_theory(m: int) -> dict:
    """Average QR survival fraction for x^2-N modulo square-free M."""
    odd_prime_count = sum(1 for p in prime_factors_distinct(m) if p != 2)
    survival = 1.0 / (2 ** odd_prime_count)
    return {
        "modulus": m,
        "odd_prime_count": odd_prime_count,
        "mean_midpoint_residue_survival_fraction": survival,
        "mean_midpoint_residue_reduction_factor": 1.0 / survival,
        "ideal_grover_query_reduction_from_midpoint_filter": math.sqrt(1.0 / survival),
    }


def fermat_search_counts(n: int, m: int | None = None, qrs: set[int] | None = None) -> dict:
    """Count Fermat x steps and expensive exact-square tests."""
    x = ceil_sqrt(n)
    start = x
    exact_square_tests = 0
    residue_checks = 0
    if m is not None and qrs is None:
        qrs = quadratic_residues(m)

    while True:
        z = x * x - n
        residue_checks += 1
        allowed = m is None or (z % m) in qrs
        if allowed:
            exact_square_tests += 1
            if is_square(z):
                y = math.isqrt(z)
                return {
                    "start_x": start,
                    "solution_x": x,
                    "solution_y": y,
                    "x_steps": x - start + 1,
                    "residue_checks": residue_checks,
                    "exact_square_tests": exact_square_tests,
                }
        x += 1


def lcm(a: int, b: int) -> int:
    return a // math.gcd(a, b) * b


def multiplicative_order_from_lambda(a: int, n: int, lam: int) -> int | None:
    if math.gcd(a, n) != 1:
        return None
    r = lam
    for p, e in factor_int(lam).items():
        for _ in range(e):
            if r % p == 0 and pow(a, r // p, n) == 1:
                r //= p
            else:
                break
    if pow(a, r, n) != 1:
        raise AssertionError("order reduction failed")
    return r


def entropy_from_counts(counts: Counter) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


def mutual_information(rows: list[dict], feature_key: str, target_key: str) -> float:
    joint = Counter((row[feature_key], row[target_key]) for row in rows)
    fx = Counter(row[feature_key] for row in rows)
    ty = Counter(row[target_key] for row in rows)
    total = len(rows)
    if total == 0:
        return 0.0
    mi = 0.0
    for (x, y), c in joint.items():
        pxy = c / total
        px = fx[x] / total
        py = ty[y] / total
        mi += pxy * math.log2(pxy / (px * py))
    return mi


def deterministic_split_key(n: int) -> int:
    # Split by N so all bases for one semiprime stay in the same fold.
    x = n * 0x9E3779B1
    x ^= x >> 16
    x *= 0xC2B2AE3D
    x ^= x >> 13
    return x & 0xFFFFFFFF


def heldout_majority_accuracy(rows: list[dict], feature_key: str, target_key: str) -> dict:
    train = [r for r in rows if deterministic_split_key(r["N"]) % 5 != 0]
    test = [r for r in rows if deterministic_split_key(r["N"]) % 5 == 0]
    if not train or not test:
        return {
            "train": len(train),
            "test": len(test),
            "baseline_accuracy": None,
            "feature_accuracy": None,
            "accuracy_gain": None,
        }

    global_counts = Counter(r[target_key] for r in train)
    global_guess = global_counts.most_common(1)[0][0]

    by_feature: dict[object, Counter] = defaultdict(Counter)
    for r in train:
        by_feature[r[feature_key]][r[target_key]] += 1

    baseline_correct = 0
    feature_correct = 0
    for r in test:
        y = r[target_key]
        baseline_correct += int(y == global_guess)
        counts = by_feature.get(r[feature_key])
        guess = counts.most_common(1)[0][0] if counts else global_guess
        feature_correct += int(y == guess)

    return {
        "train": len(train),
        "test": len(test),
        "baseline_accuracy": baseline_correct / len(test),
        "feature_accuracy": feature_correct / len(test),
        "accuracy_gain": (feature_correct - baseline_correct) / len(test),
    }


def choose_semiprimes(primes: list[int], count: int, ratio_max: float, seed: int) -> list[tuple[int, int]]:
    candidates = []
    for i, p in enumerate(primes):
        for q in primes[i + 1 :]:
            if q / p > ratio_max:
                break
            candidates.append((p, q))
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[: min(count, len(candidates))]


def fermat_audit(pairs: list[tuple[int, int]], moduli: list[int]) -> dict:
    qrs = {m: quadratic_residues(m) for m in moduli}
    rows = []
    for p, q in pairs:
        n = p * q
        baseline = fermat_search_counts(n)
        item = {
            "p": p,
            "q": q,
            "N": n,
            "factor_ratio": q / p,
            "baseline": baseline,
            "moduli": {},
        }
        for m in moduli:
            if math.gcd(n, m) != 1:
                continue
            filt = fermat_search_counts(n, m, qrs[m])
            pairs_m = kernel_factor_pairs(n, m)
            true_pair = tuple(sorted((p % m, q % m)))
            item["moduli"][str(m)] = {
                **filt,
                "square_test_reduction_factor": baseline["exact_square_tests"]
                / filt["exact_square_tests"],
                "kernel_pair_count": len(pairs_m),
                "true_factor_residue_pair_present": true_pair in set(pairs_m),
                "true_factor_residue_pair": list(true_pair),
            }
        rows.append(item)

    summary = {}
    for m in moduli:
        vals = [
            r["moduli"][str(m)]["square_test_reduction_factor"]
            for r in rows
            if str(m) in r["moduli"]
        ]
        surv = [
            r["moduli"][str(m)]["exact_square_tests"]
            / r["baseline"]["exact_square_tests"]
            for r in rows
            if str(m) in r["moduli"]
        ]
        summary[str(m)] = {
            "cases": len(vals),
            "mean_square_test_reduction_factor": mean(vals) if vals else None,
            "median_square_test_reduction_factor": median(vals) if vals else None,
            "mean_observed_survival_fraction": mean(surv) if surv else None,
            "median_observed_survival_fraction": median(surv) if surv else None,
            "theory": {**kernel_pair_theory(m), **midpoint_filter_theory(m)},
        }
    return {"summary": summary, "rows": rows}


def shor_information_audit(pairs: list[tuple[int, int]], bases: list[int], moduli: list[int]) -> dict:
    rows = []
    for p, q in pairs:
        n = p * q
        lam = lcm(p - 1, q - 1)
        for a in bases:
            if math.gcd(a, n) != 1:
                continue
            r = multiplicative_order_from_lambda(a, n, lam)
            row = {
                "N": n,
                "p": p,
                "q": q,
                "base": a,
                "lambda": lam,
                "order": r,
                "order_bits": max(1, r.bit_length()),
            }
            for m in moduli:
                row[f"N_mod_{m}"] = n % m
            for d in (2, 3, 4, 5, 7, 8, 12):
                row[f"r_div_{d}"] = r % d == 0
            for d in (3, 5, 7, 15, 21, 35, 105):
                row[f"lambda_div_{d}"] = lam % d == 0
            rows.append(row)

    report = {"rows": len(rows), "by_modulus": {}}
    for m in moduli:
        feature = f"N_mod_{m}"
        targets = {}
        target_names = [f"r_div_{d}" for d in (2, 3, 4, 5, 7, 8, 12)] + [
            f"lambda_div_{d}" for d in (3, 5, 7, 15, 21, 35, 105)
        ]
        for target in target_names:
            targets[target] = {
                "mutual_information_bits": mutual_information(rows, feature, target),
                "heldout_majority": heldout_majority_accuracy(rows, feature, target),
                "target_entropy_bits": entropy_from_counts(Counter(r[target] for r in rows)),
            }
        report["by_modulus"][str(m)] = {
            "usable_feature": feature,
            "targets": targets,
        }

    report["interpretation_boundary"] = {
        "N_mod_M_is_public": True,
        "p_mod_M_and_q_mod_M_are_oracle_validation_only": True,
        "order_or_lambda_are_validation_only": True,
        "purpose": "measure information available before factorization, not after",
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Dark-Star/PTP hybrid search-space and Shor-order audit")
    ap.add_argument("--moduli", nargs="+", type=int, default=list(DEFAULT_MODULI))
    ap.add_argument("--prime-min", type=int, default=101)
    ap.add_argument("--prime-max", type=int, default=2000)
    ap.add_argument("--semiprimes", type=int, default=600)
    ap.add_argument("--ratio-max", type=float, default=1.5)
    ap.add_argument("--order-semiprimes", type=int, default=2000)
    ap.add_argument("--order-ratio-max", type=float, default=2.0)
    ap.add_argument("--bases", nargs="+", type=int, default=list(DEFAULT_BASES))
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("results/dark_star_ptp/dark_star_ptp_shor_audit.json"),
    )
    args = ap.parse_args()

    moduli = list(dict.fromkeys(args.moduli))
    for m in moduli:
        fs = prime_factors_distinct(m)
        if math.prod(fs) != m:
            raise SystemExit(f"modulus {m} is not square-free")
        if 2 not in fs:
            raise SystemExit(f"modulus {m} must include 2 for this primorial audit")

    excluded_primes = {f for m in moduli for f in prime_factors_distinct(m)}
    all_primes = [
        p
        for p in sieve_primes(args.prime_max)
        if p >= args.prime_min and p not in excluded_primes
    ]
    if len(all_primes) < 2:
        raise SystemExit("prime range leaves too few primes after wheel exclusions")

    fermat_pairs = choose_semiprimes(all_primes, args.semiprimes, args.ratio_max, args.seed)
    order_pairs = choose_semiprimes(
        all_primes, args.order_semiprimes, args.order_ratio_max, args.seed + 1
    )
    if not fermat_pairs or not order_pairs:
        raise SystemExit("no semiprime pairs matched the requested ratio bounds")

    theory = {
        str(m): {"kernel": kernel_pair_theory(m), "midpoint": midpoint_filter_theory(m)}
        for m in moduli
    }

    result = {
        "experiment": "dark_star_ptp_shor_audit_v1",
        "zero_qpu": True,
        "known_order_used_to_construct_search_filter": False,
        "known_factors_used_to_construct_search_filter": False,
        "moduli": moduli,
        "theory": theory,
        "fermat": fermat_audit(fermat_pairs, moduli),
        "shor_information": shor_information_audit(order_pairs, args.bases, moduli),
        "notes": [
            "Wheel and midpoint filters are necessary-condition filters, not factoring breakthroughs.",
            "Kernel residue pairs organize candidates; N mod M does not identify the true pair.",
            "Midpoint QR filtering reduces expensive exact-square tests but still scans x positions.",
            "Any Grover reduction quoted by the theory block ignores oracle-construction overhead.",
            "Order-information audit tests only information available from N mod M; p,q,r,lambda are validation labels.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== THEORY =====")
    print(json.dumps(theory, indent=2))
    print("\n===== FERMAT MIDPOINT SUMMARY =====")
    print(json.dumps(result["fermat"]["summary"], indent=2))
    print("\n===== SHOR ORDER INFORMATION SUMMARY =====")
    compact = {}
    for m, block in result["shor_information"]["by_modulus"].items():
        compact[m] = {}
        for target, vals in block["targets"].items():
            compact[m][target] = {
                "mi_bits": vals["mutual_information_bits"],
                "baseline_accuracy": vals["heldout_majority"]["baseline_accuracy"],
                "feature_accuracy": vals["heldout_majority"]["feature_accuracy"],
                "accuracy_gain": vals["heldout_majority"]["accuracy_gain"],
            }
    print(json.dumps(compact, indent=2))
    print("\n===== OVERALL =====")
    print(
        json.dumps(
            {
                "pass": True,
                "zero_qpu": True,
                "fermat_cases": len(fermat_pairs),
                "order_semiprimes": len(order_pairs),
                "order_rows": result["shor_information"]["rows"],
                "saved": str(args.out.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
