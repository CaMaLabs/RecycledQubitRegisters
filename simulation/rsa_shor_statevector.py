#!/usr/bin/env python3
"""
Explicit-statevector toy RSA/Shor validation.

This file explicitly evolves the modular-arithmetic work register for the
recycled architecture and explicitly constructs the wide
post-modular-exponentiation state in block-sparse form before applying the
inverse QFT.

The controlled modular unitary is the reversible permutation:
    U_a |y> = |a*y mod N>   for 0 <= y < N
              |y>           for N <= y < 2^n
with gcd(a,N)=1.

Toy-size validation only; not a practical RSA-breaking tool.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import time
from pathlib import Path

import numpy as np

from rsa_shor_end_to_end import (
    denominator_from_qpe,
    decrypt_with_factors,
    factors_from_order,
    generate_toy_rsa,
    minimize_order,
    recover_order_from_denominators,
)


def modular_permutation(n: int, a_power: int, work_bits: int) -> np.ndarray:
    w = 1 << work_bits
    perm = np.arange(w, dtype=np.int64)
    vals = np.arange(n, dtype=np.int64)
    perm[:n] = (vals * a_power) % n
    if np.unique(perm).size != w:
        raise RuntimeError("modular map is not a permutation")
    return perm


def apply_controlled_permutation(state: np.ndarray, perm: np.ndarray) -> None:
    src = state[1].copy()
    state[1].fill(0)
    state[1, perm] = src


def apply_h_ancilla(state: np.ndarray) -> None:
    a = state[0].copy()
    b = state[1].copy()
    inv = 1.0 / math.sqrt(2.0)
    state[0] = (a + b) * inv
    state[1] = (a - b) * inv


def recycled_qpe_shot(n: int, a: int, phase_bits: int, rng: random.Random) -> int:
    work_bits = n.bit_length()
    w = 1 << work_bits
    state = np.zeros((2, w), dtype=np.complex128)
    state[0, 1] = 1.0
    c = [0] * phase_bits
    powers = [pow(a, 1 << k, n) for k in range(phase_bits)]

    for k in range(phase_bits - 1, -1, -1):
        apply_h_ancilla(state)
        perm = modular_permutation(n, powers[k], work_bits)
        apply_controlled_permutation(state, perm)

        correction = 0.0
        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            if c[prior_c]:
                correction -= 2.0 * math.pi / (1 << (j - k + 1))
        if correction:
            state[1] *= np.exp(1j * correction)

        apply_h_ancilla(state)
        p0 = float(np.vdot(state[0], state[0]).real)
        p0 = min(1.0, max(0.0, p0))
        bit = 0 if rng.random() < p0 else 1
        row = state[bit].copy()
        norm = np.linalg.norm(row)
        if norm == 0:
            raise RuntimeError("zero-norm measurement branch")
        row /= norm

        c[phase_bits - 1 - k] = bit
        state.fill(0)
        state[0] = row

    return int("".join(str(x) for x in reversed(c)), 2)


def wide_qpe_probabilities(n: int, a: int, phase_bits: int) -> np.ndarray:
    q = 1 << phase_bits
    work_values = np.empty(q, dtype=np.int64)
    x = 1
    for exponent in range(q):
        work_values[exponent] = x
        x = (x * a) % n

    probs = np.zeros(q, dtype=np.float64)
    amp = 1.0 / math.sqrt(q)
    for y in np.unique(work_values):
        v = np.zeros(q, dtype=np.complex128)
        v[work_values == y] = amp
        out = np.fft.fft(v) / math.sqrt(q)
        probs += np.abs(out) ** 2
    probs /= probs.sum()
    return probs


def sample_from_probs(probs: np.ndarray, shots: int, rng: random.Random) -> list[int]:
    cdf = np.cumsum(probs)
    out = []
    for _ in range(shots):
        u = rng.random()
        y = int(np.searchsorted(cdf, u, side="right"))
        out.append(min(y, len(probs) - 1))
    return out


def postprocess_samples(n: int, a: int, ys: list[int], phase_bits: int):
    denominators = []
    for y in ys:
        d = denominator_from_qpe(y, phase_bits, n)
        if d is None:
            continue
        denominators.append(d)
        if pow(a, d, n) == 1:
            r = minimize_order(a, n, d)
            fac = factors_from_order(a, r, n)
            if fac:
                return fac
        r = recover_order_from_denominators(a, n, denominators)
        if r is not None:
            fac = factors_from_order(a, r, n)
            if fac:
                return fac
    return None


def factor_both_architectures(n: int, rng_seed: int, shots_per_base: int,
                              max_bases: int, phase_bits: int | None = None):
    work_bits = n.bit_length()
    m = phase_bits or 2 * work_bits
    base_rng = random.Random(rng_seed ^ 0xA5A5A5A5)
    wide_rng = random.Random(rng_seed ^ 0x12345678)
    recycled_rng = random.Random(rng_seed ^ 0x87654321)

    bases = []
    while len(bases) < max_bases:
        a = base_rng.randrange(2, n - 1)
        if math.gcd(a, n) == 1:
            bases.append(a)

    wide_fac = recycled_fac = None
    wide_shots = recycled_shots = 0
    wide_bases = recycled_bases = 0

    for idx, a in enumerate(bases, 1):
        if wide_fac is None:
            probs = wide_qpe_probabilities(n, a, m)
            ys = sample_from_probs(probs, shots_per_base, wide_rng)
            for used in range(1, len(ys) + 1):
                fac = postprocess_samples(n, a, ys[:used], m)
                if fac:
                    wide_fac = fac
                    wide_shots += used
                    wide_bases = idx
                    break
            else:
                wide_shots += len(ys)

        if recycled_fac is None:
            ys = []
            for used in range(1, shots_per_base + 1):
                ys.append(recycled_qpe_shot(n, a, m, recycled_rng))
                fac = postprocess_samples(n, a, ys, m)
                if fac:
                    recycled_fac = fac
                    recycled_shots += used
                    recycled_bases = idx
                    break
            else:
                recycled_shots += shots_per_base

        if wide_fac is not None and recycled_fac is not None:
            break

    return {
        "phase_bits": m,
        "work_qubits": work_bits,
        "wide_total_qubits": work_bits + m,
        "recycled_total_qubits": work_bits + 1,
        "full_wide_statevector_amplitudes": (1 << work_bits) * (1 << m),
        "full_wide_statevector_bytes_complex128": (1 << work_bits) * (1 << m) * 16,
        "wide_factors": wide_fac,
        "recycled_factors": recycled_fac,
        "wide_qpe_shots": wide_shots,
        "recycled_qpe_shots": recycled_shots,
        "wide_bases": wide_bases or max_bases,
        "recycled_bases": recycled_bases or max_bases,
    }


def run_trial(bits: int, trial: int, seed: int, shots_per_base: int, max_bases: int):
    krng = random.Random((seed << 20) ^ (bits << 10) ^ trial)
    key = generate_toy_rsa(bits, krng)
    t0 = time.perf_counter()
    r = factor_both_architectures(
        key.n, (seed << 24) ^ (bits << 12) ^ trial,
        shots_per_base, max_bases,
    )
    elapsed = time.perf_counter() - t0
    truth = (key.p, key.q)
    wide_ok = r["wide_factors"] == truth
    recycled_ok = r["recycled_factors"] == truth
    wide_decrypt_ok = wide_ok and decrypt_with_factors(
        key.n, key.e, key.ciphertext, r["wide_factors"]
    ) == key.message
    recycled_decrypt_ok = recycled_ok and decrypt_with_factors(
        key.n, key.e, key.ciphertext, r["recycled_factors"]
    ) == key.message
    return {
        "bits": bits, "trial": trial, "n": key.n,
        "truth_p": key.p, "truth_q": key.q,
        "wide_factor_ok": bool(wide_ok),
        "recycled_factor_ok": bool(recycled_ok),
        "wide_decrypt_ok": bool(wide_decrypt_ok),
        "recycled_decrypt_ok": bool(recycled_decrypt_ok),
        "wide_qpe_shots": r["wide_qpe_shots"],
        "recycled_qpe_shots": r["recycled_qpe_shots"],
        "wide_bases": r["wide_bases"],
        "recycled_bases": r["recycled_bases"],
        "phase_bits": r["phase_bits"],
        "work_qubits": r["work_qubits"],
        "wide_total_qubits": r["wide_total_qubits"],
        "recycled_total_qubits": r["recycled_total_qubits"],
        "full_wide_statevector_amplitudes": r["full_wide_statevector_amplitudes"],
        "full_wide_statevector_mib": r["full_wide_statevector_bytes_complex128"] / (1024**2),
        "elapsed_seconds": elapsed,
    }


def summarize(rows):
    out = []
    for bits in sorted(set(r["bits"] for r in rows)):
        rr = [r for r in rows if r["bits"] == bits]
        out.append({
            "bits": bits, "trials": len(rr),
            "wide_factor_success": sum(r["wide_factor_ok"] for r in rr) / len(rr),
            "recycled_factor_success": sum(r["recycled_factor_ok"] for r in rr) / len(rr),
            "wide_decrypt_success": sum(r["wide_decrypt_ok"] for r in rr) / len(rr),
            "recycled_decrypt_success": sum(r["recycled_decrypt_ok"] for r in rr) / len(rr),
            "median_wide_qpe_shots": statistics.median(r["wide_qpe_shots"] for r in rr),
            "median_recycled_qpe_shots": statistics.median(r["recycled_qpe_shots"] for r in rr),
            "wide_total_qubits": rr[0]["wide_total_qubits"],
            "recycled_total_qubits": rr[0]["recycled_total_qubits"],
            "full_wide_statevector_mib": rr[0]["full_wide_statevector_mib"],
            "median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in rr),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", type=int, nargs="+", default=[6, 7, 8])
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--shots-per-base", type=int, default=8)
    ap.add_argument("--max-bases", type=int, default=8)
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument("--outdir", type=Path, default=Path("results/rsa_statevector"))
    args = ap.parse_args()

    rows = []
    for bits in args.bits:
        for trial in range(args.trials):
            r = run_trial(bits, trial, args.seed, args.shots_per_base, args.max_bases)
            rows.append(r)
            print(f"bits={bits} trial={trial} N={r['n']} wide={'PASS' if r['wide_factor_ok'] else 'FAIL'} recycled={'PASS' if r['recycled_factor_ok'] else 'FAIL'} width={r['wide_total_qubits']}Q->{r['recycled_total_qubits']}Q wide_state={r['full_wide_statevector_mib']:.1f} MiB elapsed={r['elapsed_seconds']:.3f}s")

    summary = summarize(rows)
    args.outdir.mkdir(parents=True, exist_ok=True)
    with (args.outdir / "statevector_trials.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (args.outdir / "statevector_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    (args.outdir / "statevector_results.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n"
    )
    print("\nSUMMARY")
    for s in summary:
        print(json.dumps(s, sort_keys=True))


if __name__ == "__main__":
    main()
