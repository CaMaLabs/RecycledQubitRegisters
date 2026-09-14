#!/usr/bin/env python3
"""
End-to-end toy RSA/Shor benchmark for RecycledQubitRegisters.

This is an exact *functional* simulator of Shor order finding for small,
self-generated RSA-like semiprimes. It does not construct a gate-level
reversible modular multiplier. Instead, the simulator classically determines
the cyclic order of U_a: |y> -> |a*y mod N> so it can sample the exact ideal
QPE measurement statistics efficiently. Crucially, the factoring/post-
processing code receives only N and QPE measurement samples; it is never given
p, q, or the simulator's internal order.

The conventional-wide and recycled-iterative phase registers are
mathematically equivalent in the ideal model, so they share the same ideal
measurement distribution. Their modeled logical width differs:
  wide      : n work qubits + m phase qubits
  recycled  : n work qubits + 1 recyclable phase qubit
where m defaults to 2*n, excluding modular-arithmetic ancillas equally.

Scope: self-generated toy keys only; not a practical RSA-breaking tool.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

_MR_BASES_64 = (2, 3, 5, 7, 11, 13, 17)


def is_probable_prime(n: int) -> bool:
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n == p:
            return True
        if n % p == 0:
            return False
    d, s = n - 1, 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for a in _MR_BASES_64:
        if a >= n:
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


def random_prime(bits: int, rng: random.Random) -> int:
    if bits < 2:
        raise ValueError("prime bits must be >=2")
    while True:
        x = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
        if is_probable_prime(x):
            return x


def choose_e(phi: int) -> int:
    for e in (65537, 257, 17, 5, 3):
        if math.gcd(e, phi) == 1:
            return e
    raise RuntimeError("could not choose RSA public exponent")


@dataclass
class ToyRSA:
    bits: int
    n: int
    e: int
    ciphertext: int
    message: int
    p: int
    q: int


def generate_toy_rsa(bits: int, rng: random.Random) -> ToyRSA:
    if bits < 6:
        raise ValueError("use at least 6 bits")
    pbits = bits // 2
    qbits = bits - pbits
    while True:
        p = random_prime(pbits, rng)
        q = random_prime(qbits, rng)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        phi = (p - 1) * (q - 1)
        e = choose_e(phi)
        msg = rng.randrange(2, n - 1)
        while math.gcd(msg, n) != 1:
            msg = rng.randrange(2, n - 1)
        c = pow(msg, e, n)
        return ToyRSA(bits, n, e, c, msg, min(p, q), max(p, q))


def _unitary_order(a: int, n: int) -> int:
    if math.gcd(a, n) != 1:
        raise ValueError("a and n must be coprime")
    x = 1
    for r in range(1, n + 1):
        x = (x * a) % n
        if x == 1:
            return r
    raise RuntimeError("order not found")


def _sample_iterative_qpe_integer(phi: float, bits: int, rng: random.Random) -> int:
    c = [0] * bits
    for k in range(bits - 1, -1, -1):
        alpha = 2.0 * math.pi * phi * (1 << k)
        for j in range(k + 1, bits):
            prior_c = bits - 1 - j
            if c[prior_c]:
                alpha -= 2.0 * math.pi / (1 << (j - k + 1))
        p0 = math.cos(alpha / 2.0) ** 2
        c[bits - 1 - k] = 0 if rng.random() < p0 else 1
    return int("".join(str(bit) for bit in reversed(c)), 2)


class ModularMultiplyOrderOracle:
    def __init__(self, n: int, a: int):
        self.n = n
        self.a = a
        self.__order = _unitary_order(a, n)

    def qpe_shot(self, phase_bits: int, rng: random.Random) -> int:
        s = rng.randrange(self.__order)
        return _sample_iterative_qpe_integer(s / self.__order, phase_bits, rng)


def convergent_denominators(num: int, den: int) -> Iterable[int]:
    if den <= 0:
        return
    coeffs = []
    n, d = num, den
    while d:
        q, r = divmod(n, d)
        coeffs.append(q)
        n, d = d, r
    p_nm2, p_nm1 = 0, 1
    q_nm2, q_nm1 = 1, 0
    for coeff in coeffs:
        p = coeff * p_nm1 + p_nm2
        q = coeff * q_nm1 + q_nm2
        if q:
            yield q
        p_nm2, p_nm1 = p_nm1, p
        q_nm2, q_nm1 = q_nm1, q


def _prime_divisors(n: int) -> list[int]:
    out = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d = 3 if d == 2 else d + 2
    if n > 1:
        out.append(n)
    return out


def minimize_order(a: int, n: int, candidate: int) -> int:
    r = candidate
    for p in _prime_divisors(candidate):
        while r % p == 0 and pow(a, r // p, n) == 1:
            r //= p
    return r


def denominator_from_qpe(y: int, phase_bits: int, n: int) -> int | None:
    if y == 0:
        return None
    q = 1 << phase_bits
    d = Fraction(y, q).limit_denominator(n).denominator
    return d if 1 < d <= n else None


def recover_order_from_denominators(a: int, n: int, denominators: list[int]) -> int | None:
    candidate = 1
    for d in denominators:
        candidate = math.lcm(candidate, d)
        if candidate > n:
            return None
        if pow(a, candidate, n) == 1:
            return minimize_order(a, n, candidate)
    return None


def factors_from_order(a: int, r: int, n: int) -> tuple[int, int] | None:
    if r <= 0 or r % 2:
        return None
    x = pow(a, r // 2, n)
    if x in (1, n - 1):
        return None
    for g in (math.gcd(x - 1, n), math.gcd(x + 1, n)):
        if 1 < g < n and n % g == 0:
            p, q = g, n // g
            return min(p, q), max(p, q)
    return None


@dataclass
class FactorRun:
    success: bool
    factors: tuple[int, int] | None
    bases_tried: int
    qpe_shots: int
    gcd_shortcut: bool
    phase_bits: int
    work_qubits: int
    wide_total_qubits: int
    recycled_total_qubits: int
    wide_phase_qubits: int
    recycled_phase_qubits: int
    controlled_modmul_calls_per_shot: int
    feedback_rounds_per_shot: int


def factor_via_simulated_shor(
    n: int,
    rng: random.Random,
    shots_per_base: int = 8,
    max_bases: int = 16,
    phase_bits: int | None = None,
) -> FactorRun:
    work = n.bit_length()
    m = phase_bits if phase_bits is not None else 2 * work
    qpe_shots = 0

    for base_idx in range(1, max_bases + 1):
        for _pick in range(256):
            a = rng.randrange(2, n - 1)
            if math.gcd(a, n) == 1:
                break
        else:
            raise RuntimeError("could not choose a coprime Shor base")

        oracle = ModularMultiplyOrderOracle(n, a)
        denominators: list[int] = []
        for _ in range(shots_per_base):
            y = oracle.qpe_shot(m, rng)
            qpe_shots += 1
            d = denominator_from_qpe(y, m, n)
            if d is None:
                continue
            denominators.append(d)
            candidates = []
            if pow(a, d, n) == 1:
                candidates.append(minimize_order(a, n, d))
            rhat = recover_order_from_denominators(a, n, denominators)
            if rhat is not None:
                candidates.append(rhat)
            for order_candidate in candidates:
                fac = factors_from_order(a, order_candidate, n)
                if fac is not None:
                    return FactorRun(True, fac, base_idx, qpe_shots, False, m, work,
                                     work + m, work + 1, m, 1, m, m)

    return FactorRun(False, None, max_bases, qpe_shots, False, m, work,
                     work + m, work + 1, m, 1, m, m)


def decrypt_with_factors(n: int, e: int, ciphertext: int, factors: tuple[int, int]) -> int:
    p, q = factors
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    return pow(ciphertext, d, n)


def run_case(bits: int, trial: int, seed: int, shots_per_base: int, max_bases: int) -> dict:
    key_rng = random.Random((seed << 24) ^ (bits << 12) ^ trial)
    alg_rng = random.Random((seed << 28) ^ (bits << 14) ^ (trial * 0x9E3779B1))
    key = generate_toy_rsa(bits, key_rng)
    t0 = time.perf_counter()
    fr = factor_via_simulated_shor(key.n, alg_rng, shots_per_base, max_bases)
    elapsed = time.perf_counter() - t0
    factor_match = fr.success and fr.factors == (key.p, key.q)
    decrypt_ok = False
    if factor_match and fr.factors:
        decrypt_ok = decrypt_with_factors(key.n, key.e, key.ciphertext, fr.factors) == key.message
    return {
        "bits": bits, "trial": trial, "n": key.n, "e": key.e,
        "ciphertext": key.ciphertext, "truth_p": key.p, "truth_q": key.q,
        "factor_success": bool(fr.success), "factor_match": bool(factor_match),
        "decrypt_ok": bool(decrypt_ok),
        "recovered_p": fr.factors[0] if fr.factors else None,
        "recovered_q": fr.factors[1] if fr.factors else None,
        "bases_tried": fr.bases_tried, "qpe_shots": fr.qpe_shots,
        "gcd_shortcut": fr.gcd_shortcut, "phase_bits": fr.phase_bits,
        "work_qubits": fr.work_qubits,
        "wide_total_qubits_excl_arith_ancilla": fr.wide_total_qubits,
        "recycled_total_qubits_excl_arith_ancilla": fr.recycled_total_qubits,
        "phase_width_reduction": fr.wide_phase_qubits / fr.recycled_phase_qubits,
        "modeled_total_width_reduction": fr.wide_total_qubits / fr.recycled_total_qubits,
        "controlled_modmul_calls_per_shot": fr.controlled_modmul_calls_per_shot,
        "feedback_rounds_per_shot": fr.feedback_rounds_per_shot,
        "elapsed_seconds": elapsed,
    }


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    for bits in sorted({r["bits"] for r in rows}):
        rr = [r for r in rows if r["bits"] == bits]
        out.append({
            "bits": bits, "trials": len(rr),
            "factor_success_rate": sum(r["factor_match"] for r in rr) / len(rr),
            "decrypt_success_rate": sum(r["decrypt_ok"] for r in rr) / len(rr),
            "median_bases_tried": statistics.median(r["bases_tried"] for r in rr),
            "median_qpe_shots": statistics.median(r["qpe_shots"] for r in rr),
            "gcd_shortcut_fraction": sum(r["gcd_shortcut"] for r in rr) / len(rr),
            "wide_total_qubits_excl_arith_ancilla": rr[0]["wide_total_qubits_excl_arith_ancilla"],
            "recycled_total_qubits_excl_arith_ancilla": rr[0]["recycled_total_qubits_excl_arith_ancilla"],
            "modeled_total_width_reduction": rr[0]["modeled_total_width_reduction"],
            "median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in rr),
        })
    return out


def write_outputs(outdir: Path, rows: list[dict], summary: list[dict], args: argparse.Namespace) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "rsa_shor_results.json").write_text(json.dumps({
        "benchmark": "self-generated toy RSA / exact functional Shor simulator",
        "seed": args.seed, "bits": args.bits, "trials": args.trials,
        "shots_per_base": args.shots_per_base, "max_bases": args.max_bases,
        "important_limit": "Simulator classically computes the modular-multiplication order internally to sample exact ideal QPE statistics; factoring post-processing receives only N and QPE samples. This is not gate-level modular arithmetic.",
        "summary": summary, "rows": rows,
    }, indent=2) + "\n")
    with (outdir / "rsa_shor_trials.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (outdir / "rsa_shor_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", type=int, nargs="+", default=[10, 12, 14, 16, 18, 20])
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--shots-per-base", type=int, default=8)
    ap.add_argument("--max-bases", type=int, default=16)
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument("--outdir", type=Path, default=Path("results/rsa_shor"))
    args = ap.parse_args()
    rows = []
    for bits in args.bits:
        for trial in range(args.trials):
            row = run_case(bits, trial, args.seed, args.shots_per_base, args.max_bases)
            rows.append(row)
            print(f"bits={bits:2d} trial={trial:02d} N={row['n']} factor={'PASS' if row['factor_match'] else 'FAIL'} decrypt={'PASS' if row['decrypt_ok'] else 'FAIL'} bases={row['bases_tried']} qpe_shots={row['qpe_shots']} width={row['wide_total_qubits_excl_arith_ancilla']}Q->{row['recycled_total_qubits_excl_arith_ancilla']}Q")
    summary = summarize(rows)
    write_outputs(args.outdir, rows, summary, args)
    print("\nSUMMARY")
    for s in summary:
        print(json.dumps(s, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
