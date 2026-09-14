#!/usr/bin/env python3
"""Dark Star v2 research primitives.

This module is intentionally scoped to self-generated semiprime experiments.
It contains no network, persistence, key-handling, or arbitrary-target attack code.
"""
from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_left
from functools import lru_cache
from math import gcd, isqrt, log2, prod
import random
import time
from typing import Sequence

ORIGINAL_WHEEL_PRIMES = (2, 3, 5, 7)
ORIGINAL_WHEEL_MODULUS = 210
DEFAULT_MIDPOINT_PRIMES = (3, 5, 7, 11, 13)
DEFAULT_MIDPOINT_MODULUS = prod(DEFAULT_MIDPOINT_PRIMES)
_MR64_BASES = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)


def is_probable_prime(n: int) -> bool:
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    bases = _MR64_BASES if n < (1 << 64) else small
    for a in bases:
        a %= n
        if a in (0, 1):
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


def next_prime(n: int) -> int:
    if n <= 2:
        return 2
    n |= 1
    while not is_probable_prime(n):
        n += 2
    return n


def random_prime(bits: int, rng: random.Random) -> int:
    if bits < 4:
        raise ValueError("bits must be >= 4")
    while True:
        n = rng.getrandbits(bits)
        n |= (1 << (bits - 1)) | 1
        n = next_prime(n)
        if n.bit_length() == bits:
            return n


def primes_up_to(limit: int) -> list[int]:
    if limit < 2:
        return []
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[:2] = b"\x00\x00"
    for p in range(2, isqrt(limit) + 1):
        if sieve[p]:
            sieve[p*p:limit+1:p] = b"\x00" * (((limit - p*p)//p) + 1)
    return [i for i, v in enumerate(sieve) if v]


@lru_cache(maxsize=None)
def admissible_residues(modulus: int) -> tuple[int, ...]:
    return tuple(r for r in range(modulus) if gcd(r, modulus) == 1)


@lru_cache(maxsize=None)
def unit_residues_with_inverses(modulus: int) -> tuple[tuple[int, int], ...]:
    return tuple((r, pow(r, -1, modulus)) for r in admissible_residues(modulus))


@dataclass(frozen=True)
class WheelStats:
    modulus: int
    residue_count: int
    density_all_integers: float
    eliminated_fraction: float
    integer_sieve_bits: float


def wheel_stats(modulus: int) -> WheelStats:
    count = len(admissible_residues(modulus))
    density = count / modulus
    return WheelStats(modulus, count, density, 1.0-density, log2(modulus/count))


@dataclass(frozen=True)
class CouplingStats:
    modulus: int
    p_residue_count: int
    q_residue_count: int
    pair_count: int
    pair_pruning_bits_vs_prime_residues: float
    is_bijection: bool


def factor_residue_coupling(n: int, modulus: int) -> tuple[dict[int, int], CouplingStats]:
    if gcd(n, modulus) != 1:
        raise ValueError("benchmark semiprime must be coprime to the wheel modulus")
    residues = admissible_residues(modulus)
    allowed = set(residues)
    mapping = {}
    for rp, inv_rp in unit_residues_with_inverses(modulus):
        rq = (n * inv_rp) % modulus
        if rq in allowed:
            mapping[rp] = rq
    qset = set(mapping.values())
    pair_count = len(mapping)
    bits = log2(len(residues)/pair_count) if pair_count else float("inf")
    return mapping, CouplingStats(
        modulus, len(residues), len(qset), pair_count, bits,
        pair_count == len(residues) == len(qset),
    )


@dataclass(frozen=True)
class MidpointResidueStats:
    modulus: int
    allowed_count: int
    density: float
    pruning_factor: float
    pruning_bits: float


def midpoint_residues(n: int, modulus: int = DEFAULT_MIDPOINT_MODULUS) -> tuple[tuple[int, ...], MidpointResidueStats]:
    if modulus % 2 == 0:
        raise ValueError("midpoint modulus must be odd")
    mapping, _ = factor_residue_coupling(n, modulus)
    inv2 = pow(2, -1, modulus)
    xs = sorted({((rp + rq) * inv2) % modulus for rp, rq in mapping.items()})
    density = len(xs)/modulus
    stats = MidpointResidueStats(modulus, len(xs), density, 1.0/density, log2(1.0/density))
    return tuple(xs), stats


@dataclass
class FactorResult:
    p: int
    q: int
    square_tests: int
    x_span: int
    setup_seconds: float
    search_seconds: float
    algorithm: str
    midpoint_allowed_count: int | None = None
    midpoint_modulus: int | None = None


def _ceil_sqrt(n: int) -> int:
    x = isqrt(n)
    return x if x*x == n else x + 1


def fermat_factor(n: int, max_square_tests: int | None = None) -> FactorResult:
    if n % 2 == 0:
        return FactorResult(2, n//2, 1, 0, 0.0, 0.0, "fermat")
    start = _ceil_sqrt(n)
    x = start
    tests = 0
    t0 = time.perf_counter()
    while max_square_tests is None or tests < max_square_tests:
        y2 = x*x - n
        y = isqrt(y2)
        tests += 1
        if y*y == y2:
            p, q = x-y, x+y
            if p > 1 and p*q == n:
                return FactorResult(min(p,q), max(p,q), tests, x-start, 0.0, time.perf_counter()-t0, "fermat")
        x += 1
    raise RuntimeError("Fermat square-test limit reached")


def darkstar_fermat_factor(n: int, midpoint_modulus: int = DEFAULT_MIDPOINT_MODULUS, max_square_tests: int | None = None) -> FactorResult:
    if n % 2 == 0:
        return FactorResult(2, n//2, 1, 0, 0.0, 0.0, "darkstar_fermat")
    setup0 = time.perf_counter()
    allowed, _ = midpoint_residues(n, midpoint_modulus)
    if not allowed:
        raise RuntimeError("no midpoint residues survived")
    setup_seconds = time.perf_counter() - setup0
    start = _ceil_sqrt(n)
    r0 = start % midpoint_modulus
    i = bisect_left(allowed, r0)
    if i == len(allowed):
        x = start + (midpoint_modulus-r0) + allowed[0]
        i = 0
    else:
        x = start + (allowed[i]-r0)
    tests = 0
    t0 = time.perf_counter()
    L = len(allowed)
    while max_square_tests is None or tests < max_square_tests:
        y2 = x*x - n
        y = isqrt(y2)
        tests += 1
        if y*y == y2:
            p, q = x-y, x+y
            if p > 1 and p*q == n:
                return FactorResult(min(p,q), max(p,q), tests, x-start, setup_seconds, time.perf_counter()-t0, "darkstar_fermat", L, midpoint_modulus)
        j = i + 1
        if j < L:
            x += allowed[j] - allowed[i]
            i = j
        else:
            x += (midpoint_modulus - allowed[i]) + allowed[0]
            i = 0
    raise RuntimeError("Dark Star Fermat square-test limit reached")


def smooth_part(n: int, bound: int, prime_table: Sequence[int] | None = None) -> tuple[int, int]:
    table = prime_table if prime_table is not None else primes_up_to(bound)
    rem = n
    sm = 1
    for p in table:
        if p > bound:
            break
        while rem % p == 0:
            sm *= p
            rem //= p
        if rem == 1:
            break
    return sm, rem


def generated_close_semiprime(bits: int, target_fermat_steps: int, rng: random.Random) -> tuple[int, int, int]:
    p = random_prime(bits, rng)
    gap = max(4, isqrt(8*p*max(1,target_fermat_steps)))
    if gap % 2:
        gap += 1
    q = next_prime(p + gap)
    if q.bit_length() != bits:
        return generated_close_semiprime(bits, target_fermat_steps, rng)
    return p*q, min(p,q), max(p,q)
