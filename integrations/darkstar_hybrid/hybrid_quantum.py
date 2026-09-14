#!/usr/bin/env python3
"""Hybrid quantum research primitives for Dark Star.

Scope: self-generated toy semiprimes only. This is an order-finding/QPE
benchmark, not a tool for attacking third-party keys.

The simulator intentionally separates:
  * the phase/control register, which iterative QPE can recycle, and
  * the modular-arithmetic work register, which must remain quantum.

It uses an analytic/Monte-Carlo QPE surrogate rather than pretending to model
fault-tolerant modular exponentiation gate-for-gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd, pi
import random


@dataclass(frozen=True)
class NoiseModel:
    readout_error: float = 0.01
    controlled_u_error: float = 0.005
    reset_error: float = 0.002
    feedback_error: float = 0.003
    phase_jitter_bins: float = 0.05


@dataclass(frozen=True)
class ArchitectureWidth:
    n_bits: int
    phase_bits: int
    work_qubits: int
    wide_phase_qubits: int
    recycled_phase_qubits: int
    wide_total_model_qubits: int
    hybrid_total_model_qubits: int
    phase_width_reduction: float
    modeled_total_width_reduction: float


def width_model(n: int, phase_bits: int | None = None) -> ArchitectureWidth:
    """Minimal logical-width model, excluding modular-arithmetic ancillas."""
    w = n.bit_length()
    m = phase_bits if phase_bits is not None else 2 * w
    wide = w + m
    hybrid = w + 1
    return ArchitectureWidth(
        n_bits=w,
        phase_bits=m,
        work_qubits=w,
        wide_phase_qubits=m,
        recycled_phase_qubits=1,
        wide_total_model_qubits=wide,
        hybrid_total_model_qubits=hybrid,
        phase_width_reduction=m,
        modeled_total_width_reduction=wide / hybrid,
    )


def multiplicative_order(a: int, n: int) -> int:
    """Classical truth oracle for benchmarking small, self-generated cases."""
    if gcd(a, n) != 1:
        raise ValueError("a and n must be coprime")
    x = 1
    for r in range(1, n + 1):
        x = (x * a) % n
        if x == 1:
            return r
    raise RuntimeError("order not found within n steps")


def choose_base_with_nontrivial_order(n: int, rng: random.Random, tries: int = 128) -> tuple[int, int]:
    """Choose a Shor base whose true order can produce nontrivial factors."""
    for _ in range(tries):
        a = rng.randrange(2, n - 1)
        g = gcd(a, n)
        if 1 < g < n:
            continue
        if g != 1:
            continue
        r = multiplicative_order(a, n)
        if r % 2 == 0 and pow(a, r // 2, n) not in (1, n - 1):
            return a, r
    raise RuntimeError("could not find a useful order-finding base")


def factors_from_order(a: int, r: int, n: int) -> tuple[int, int] | None:
    if r <= 0 or r % 2:
        return None
    x = pow(a, r // 2, n)
    if x in (1, n - 1):
        return None
    p = gcd(x - 1, n)
    q = gcd(x + 1, n)
    candidates = [g for g in (p, q) if 1 < g < n and n % g == 0]
    if not candidates:
        return None
    p = min(candidates)
    q = n // p
    return (min(p, q), max(p, q))


def _flip_bits(y: int, bits: int, p: float, rng: random.Random) -> int:
    if p <= 0:
        return y
    for b in range(bits):
        if rng.random() < p:
            y ^= 1 << b
    return y


def _tail_offset(rng: random.Random, max_k: int = 16) -> int:
    ks = list(range(1, max_k + 1))
    weights = [1.0 / (k * k) for k in ks]
    k = rng.choices(ks, weights=weights, k=1)[0]
    return k if rng.random() < 0.5 else -k


def sample_phase_integer(
    phi: float,
    bits: int,
    rng: random.Random,
    bit_error: float = 0.0,
    phase_jitter: float = 0.0,
    capture_probability: float = 4.0 / (pi * pi),
) -> int:
    """Monte-Carlo QPE measurement surrogate."""
    q = 1 << bits
    if phase_jitter:
        phi = (phi + rng.gauss(0.0, phase_jitter)) % 1.0
    y0 = int(round(phi * q)) % q
    y = y0 if rng.random() < capture_probability else (y0 + _tail_offset(rng)) % q
    return _flip_bits(y, bits, bit_error, rng)


def recover_order_from_phase(a: int, n: int, y: int, bits: int, max_multiple: int = 32) -> int | None:
    if y == 0:
        return None
    q = 1 << bits
    frac = Fraction(y, q).limit_denominator(n)
    d = frac.denominator
    if d <= 0:
        return None
    for k in range(1, max_multiple + 1):
        cand = d * k
        if cand > n:
            break
        if pow(a, cand, n) == 1:
            return cand
    return None


def architecture_bit_error(arch: str, noise: NoiseModel) -> float:
    if arch == "wide":
        return 1.0 - (1.0 - noise.readout_error) * (1.0 - noise.controlled_u_error)
    if arch == "6C2Q":
        return 1.0 - (
            (1.0 - noise.readout_error)
            * (1.0 - noise.controlled_u_error)
            * (1.0 - noise.reset_error)
            * (1.0 - noise.feedback_error)
        )
    raise ValueError(f"unknown architecture {arch!r}")


def simulate_order_finding(
    n: int,
    a: int,
    true_order: int,
    arch: str,
    shots: int,
    rng: random.Random,
    noise: NoiseModel,
    phase_bits: int | None = None,
) -> dict:
    """Run an ideal/noisy order-finding Monte Carlo benchmark."""
    widths = width_model(n, phase_bits)
    m = widths.phase_bits
    bit_error = architecture_bit_error(arch, noise)
    successes = 0
    recovered_orders = 0
    exact_orders = 0

    for _ in range(shots):
        s = rng.randrange(0, true_order)
        phi = s / true_order
        y = sample_phase_integer(
            phi,
            m,
            rng,
            bit_error=bit_error,
            phase_jitter=noise.phase_jitter_bins / (1 << m),
        )
        rhat = recover_order_from_phase(a, n, y, m)
        if rhat is None:
            continue
        recovered_orders += 1
        if rhat == true_order:
            exact_orders += 1
        if factors_from_order(a, rhat, n) is not None:
            successes += 1

    return {
        "architecture": arch,
        "shots": shots,
        "successes": successes,
        "factor_success_probability": successes / shots,
        "order_recovery_probability": recovered_orders / shots,
        "exact_order_probability": exact_orders / shots,
        "modeled_bit_error": bit_error,
        "phase_jitter_bins": noise.phase_jitter_bins,
        **widths.__dict__,
    }


def guaranteed_lambda_small_factors(n: int, primes=(3, 5, 7, 11, 13, 17, 19)) -> dict:
    """Infer small prime divisors guaranteed to divide lambda(N) from N mod l."""
    guaranteed = [2]
    detail = {}
    for ell in primes:
        if n % ell == 0:
            detail[str(ell)] = {"skipped": "ell divides N"}
            continue
        pairs = []
        all_force = True
        for rp in range(1, ell):
            rq = (n * pow(rp, -1, ell)) % ell
            if rq == 0:
                continue
            force = (rp == 1 or rq == 1)
            pairs.append((rp, rq, force))
            if not force:
                all_force = False
        detail[str(ell)] = {
            "compatible_pair_count": len(pairs),
            "guaranteed_divides_lambda": all_force,
        }
        if all_force:
            guaranteed.append(ell)
    g = 1
    for x in guaranteed:
        g *= x
    return {"guaranteed_lambda_divisor": g, "guaranteed_prime_factors": guaranteed, "detail": detail}
