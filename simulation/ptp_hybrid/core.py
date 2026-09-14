#!/usr/bin/env python3
"""Independent modulo-210 PTP core for the optional QRR hybrid track.

The implementation derives the residue classes and factor-pair table from
first principles. It does not copy a published lookup table.

Canonical PTP roots follow the papers' interval [11, 220]: residue 1 (mod 210)
is represented by 211. Thus every n > 7 coprime to 210 has a unique form

    n = r + 210*k,  r in ROOTS.

This module intentionally makes no quantum-resource claim. It is classical
number-theory infrastructure for later controlled experiments.
"""
from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache
from typing import Iterable

MODULUS = 2 * 3 * 5 * 7
BASE_PRIMES = (2, 3, 5, 7)
ROOT_MIN = 11
ROOT_MAX = ROOT_MIN + MODULUS - 1  # 220


def _generate_roots() -> tuple[int, ...]:
    roots = tuple(n for n in range(ROOT_MIN, ROOT_MAX + 1) if math.gcd(n, MODULUS) == 1)
    if len(roots) != 48:
        raise AssertionError(f"expected phi(210)=48 roots, got {len(roots)}")
    return roots


ROOTS = _generate_roots()
ROOT_TO_INDEX = {root: i + 1 for i, root in enumerate(ROOTS)}
RESIDUE_TO_ROOT = {root % MODULUS: root for root in ROOTS}


def is_ptp_candidate(n: int) -> bool:
    """Return True for integers > 7 not divisible by 2, 3, 5, or 7."""
    return int(n) > 7 and math.gcd(int(n), MODULUS) == 1


def root_for_integer(n: int) -> int:
    """Return the canonical root r in [11,220] for n = r + 210*k.

    The formula mirrors the period convention used in the PTP/kernel-factor
    papers. Values divisible by 2, 3, 5, or 7 are intentionally rejected.
    """
    n = int(n)
    if not is_ptp_candidate(n):
        raise ValueError(f"{n} is not a PTP candidate (must be >7 and coprime to 210)")
    # Equivalent to n - floor((n-10)/210)*210.
    root = n - math.floor((n - 10) / MODULUS) * MODULUS
    if root not in ROOT_TO_INDEX:
        raise AssertionError(f"internal root mapping failure for n={n}: root={root}")
    return root


def root_index(n: int, *, one_based: bool = True) -> int:
    """Return the canonical root index for n; one-based matches r_1..r_48."""
    idx = ROOT_TO_INDEX[root_for_integer(n)]
    return idx if one_based else idx - 1


def ptp_coordinate(n: int) -> tuple[int, int]:
    """Return (root, kin) such that n = root + 210*kin."""
    n = int(n)
    root = root_for_integer(n)
    kin, rem = divmod(n - root, MODULUS)
    if rem:
        raise AssertionError("non-integral PTP coordinate")
    return root, kin


def root_for_residue(residue: int) -> int:
    """Map a reduced residue modulo 210 to the canonical [11,220] root."""
    residue %= MODULUS
    try:
        return RESIDUE_TO_ROOT[residue]
    except KeyError as exc:
        raise ValueError(f"residue {residue} is not coprime to 210") from exc


def small_base_factor(n: int) -> int | None:
    """Return the first factor among 2,3,5,7, or None."""
    n = int(n)
    for p in BASE_PRIMES:
        if n % p == 0:
            return p
    return None


@lru_cache(maxsize=1)
def factor_pair_table() -> dict[int, tuple[tuple[int, int], ...]]:
    """Generate the unordered 48-root factor-pair table algorithmically.

    For each target root r, include every unordered pair (q_j,q_k) from ROOTS
    satisfying q_j*q_k == r (mod 210).
    """
    table: dict[int, tuple[tuple[int, int], ...]] = {}
    for target in ROOTS:
        pairs: list[tuple[int, int]] = []
        for i, qj in enumerate(ROOTS):
            for qk in ROOTS[i:]:
                if (qj * qk - target) % MODULUS == 0:
                    pairs.append((qj, qk))
        table[target] = tuple(pairs)
    return table


def candidate_factor_pairs(n: int) -> tuple[tuple[int, int], ...]:
    """Return residue-root factor pairs compatible with n modulo 210."""
    return factor_pair_table()[root_for_integer(n)]


def factor_pair_summary() -> dict:
    table = factor_pair_table()
    counts = Counter(len(pairs) for pairs in table.values())
    self_pair_counts = {
        root: sum(1 for a, b in pairs if a == b) for root, pairs in table.items()
    }
    all_unordered = len(ROOTS) * (len(ROOTS) + 1) // 2
    return {
        "modulus": MODULUS,
        "root_count": len(ROOTS),
        "all_unordered_root_pairs": all_unordered,
        "candidate_count_distribution": dict(sorted(counts.items())),
        "targets_with_28_pairs": [r for r, pairs in table.items() if len(pairs) == 28],
        "self_pair_counts": self_pair_counts,
        "reduction_fraction_by_target": {
            r: 1.0 - len(pairs) / all_unordered for r, pairs in table.items()
        },
    }


def is_prime_trial(n: int) -> bool:
    """Small deterministic primality helper used only by exhaustive tests."""
    n = int(n)
    if n < 2:
        return False
    if n in BASE_PRIMES:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def primes_in_range(stop: int, start: int = 2) -> Iterable[int]:
    for n in range(max(2, start), int(stop) + 1):
        if is_prime_trial(n):
            yield n


def exhaustive_core_report(prime_limit: int = 100_000) -> dict:
    """Reproduce Phase-1/2 properties without trusting published tables."""
    bad_primes = []
    checked_primes = 0
    for p in primes_in_range(prime_limit, 11):
        checked_primes += 1
        if not is_ptp_candidate(p) or root_for_integer(p) not in ROOTS:
            bad_primes.append(p)

    table = factor_pair_table()
    pair_counts = Counter(len(v) for v in table.values())
    bad_products = []
    for target, pairs in table.items():
        for a, b in pairs:
            if (a * b - target) % MODULUS:
                bad_products.append((target, a, b))

    self_28 = {
        target: [a for a, b in pairs if a == b]
        for target, pairs in table.items()
        if len(pairs) == 28
    }

    return {
        "pass": not bad_primes and not bad_products and pair_counts == Counter({24: 42, 28: 6})
        and all(len(v) == 8 for v in self_28.values()),
        "modulus": MODULUS,
        "roots": list(ROOTS),
        "root_count": len(ROOTS),
        "prime_limit": prime_limit,
        "checked_primes_gt_7": checked_primes,
        "bad_primes": bad_primes,
        "pair_count_distribution": dict(sorted(pair_counts.items())),
        "targets_with_28_pairs_and_self_roots": self_28,
        "bad_factor_pair_products": bad_products,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(exhaustive_core_report(), indent=2, sort_keys=True))
