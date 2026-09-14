#!/usr/bin/env python3
"""Ideal, zero-QPU validation for the order/orbit-independent N=35 Shor path.

The circuit constructor under test derives each controlled modular power only
from N, a, and the QPE bit index.  This validator checks the corresponding
full-residue permutations, computes the exact wide-QPE distribution directly
from modular exponentiation, and independently simulates the iterative
recycled-QPE measurement/feed-forward branches.

The known multiplicative order is used only by the existing reference
postprocessor after the generated distributions have been produced.  It is not
used to construct either simulated path.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import ibm_shor35_generic_full_permutation_preflight as base
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-full-permutation-ideal-v1"
N = base.N
A = base.A
WORK_BITS = base.WORK_BITS
WORK_DIM = 1 << WORK_BITS


def discover_order_for_validation_only() -> int:
    x = 1
    for r in range(1, N + 1):
        x = (x * A) % N
        if x == 1:
            return r
    raise RuntimeError("order not found")


def validate_generated_permutations(phase_bits: int) -> list[dict]:
    rows = []
    for k in range(phase_bits):
        multiplier = pow(A, 1 << k, N)
        perm = base.modular_permutation(multiplier)
        swaps, meta = base.synthesize_swaps(perm)
        ok = base.validate_swap_network(perm, swaps)
        if not ok:
            raise AssertionError(f"swap network failed at qpe bit {k}")
        expected = [((multiplier * y) % N) if y < N else y for y in range(WORK_DIM)]
        exact = perm == expected
        if not exact:
            raise AssertionError(f"full-register modular permutation mismatch at qpe bit {k}")
        rows.append(
            {
                "qpe_bit": k,
                "multiplier": multiplier,
                "full_register_exact": exact,
                "swap_network_exact": ok,
                **meta,
            }
        )
    return rows


def wide_distribution_from_N_a(phase_bits: int) -> np.ndarray:
    """Exact wide-QPE distribution using only N, a and modular exponentiation."""
    q = 1 << phase_bits
    amplitudes = np.zeros((q, WORK_DIM), dtype=np.complex128)
    norm = math.sqrt(q)
    for x in range(q):
        work_value = pow(A, x, N)
        amplitudes[x, work_value] = 1.0 / norm

    # Qiskit's inverse QFT convention corresponds to the normalized forward FFT
    # for this phase-register integer convention.
    after_iqft = np.fft.fft(amplitudes, axis=0) / norm
    probs = np.sum(np.abs(after_iqft) ** 2, axis=1).real
    probs /= probs.sum()
    return probs


def apply_permutation(vec: np.ndarray, perm: list[int]) -> np.ndarray:
    out = np.zeros_like(vec)
    for y, mapped in enumerate(perm):
        out[mapped] += vec[y]
    return out


def recycled_distribution_from_N_a(phase_bits: int) -> np.ndarray:
    """Exact branch simulation of iterative QPE with measurement/feed-forward."""
    zero_bits = (0,) * phase_bits
    initial_work = np.zeros(WORK_DIM, dtype=np.complex128)
    initial_work[1] = 1.0
    branches: dict[tuple[int, ...], np.ndarray] = {zero_bits: initial_work}

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        multiplier = pow(A, 1 << k, N)
        perm = base.modular_permutation(multiplier)
        new_branches: dict[tuple[int, ...], np.ndarray] = {}

        for bits, work in branches.items():
            anc0 = work / math.sqrt(2.0)
            anc1 = apply_permutation(work, perm) / math.sqrt(2.0)

            correction = 0.0
            for j in range(k + 1, phase_bits):
                prior_c = phase_bits - 1 - j
                if bits[prior_c]:
                    correction += -2.0 * math.pi / (2 ** (j - k + 1))
            anc1 = anc1 * np.exp(1j * correction)

            out0 = (anc0 + anc1) / math.sqrt(2.0)
            out1 = (anc0 - anc1) / math.sqrt(2.0)

            for outcome, branch_state in ((0, out0), (1, out1)):
                next_bits = list(bits)
                next_bits[dest] = outcome
                key = tuple(next_bits)
                if key in new_branches:
                    new_branches[key] = new_branches[key] + branch_state
                else:
                    new_branches[key] = branch_state

        branches = new_branches

    probs = np.zeros(1 << phase_bits, dtype=float)
    for bits, work in branches.items():
        y = sum(bit << i for i, bit in enumerate(bits))
        probs[y] += float(np.vdot(work, work).real)
    probs /= probs.sum()
    return probs


def direct_recovery_probability(probabilities: np.ndarray, phase_bits: int) -> float:
    total = 0.0
    for y, p in enumerate(probabilities):
        rec = ref.recover_from_phase_integer(y, phase_bits)
        if rec and rec.get("recovery_mode") == "direct":
            total += float(p)
    return total


def permissive_recovery_probability(probabilities: np.ndarray, phase_bits: int) -> float:
    return float(
        sum(
            p
            for y, p in enumerate(probabilities)
            if ref.recover_from_phase_integer(y, phase_bits) is not None
        )
    )


def comparison_metrics(observed: np.ndarray, reference: np.ndarray) -> dict:
    tv = 0.5 * float(np.sum(np.abs(observed - reference)))
    affinity = float(np.sum(np.sqrt(np.clip(observed, 0, None) * np.clip(reference, 0, None))))
    return {
        "max_abs_probability_error": float(np.max(np.abs(observed - reference))),
        "total_variation_distance": tv,
        "hellinger_fidelity": affinity * affinity,
    }


def top_rows(probabilities: np.ndarray, phase_bits: int, limit: int = 16) -> list[dict]:
    return [
        {
            "y": int(y),
            "bitstring": format(int(y), f"0{phase_bits}b"),
            "probability": float(probabilities[y]),
        }
        for y in np.argsort(probabilities)[::-1][:limit]
    ]


def run_case(phase_bits: int, tolerance: float) -> dict:
    permutation_rows = validate_generated_permutations(phase_bits)
    wide = wide_distribution_from_N_a(phase_bits)
    recycled = recycled_distribution_from_N_a(phase_bits)
    reference = np.asarray(ref.ideal_order_distribution(phase_bits), dtype=float)

    wide_vs_ref = comparison_metrics(wide, reference)
    recycled_vs_ref = comparison_metrics(recycled, reference)
    recycled_vs_wide = comparison_metrics(recycled, wide)

    passed = (
        all(r["full_register_exact"] and r["swap_network_exact"] for r in permutation_rows)
        and wide_vs_ref["max_abs_probability_error"] <= tolerance
        and recycled_vs_ref["max_abs_probability_error"] <= tolerance
        and recycled_vs_wide["max_abs_probability_error"] <= tolerance
    )

    return {
        "pass": passed,
        "phase_bits": phase_bits,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "validation_order_not_used_by_construction": discover_order_for_validation_only(),
        "round_multipliers": [r["multiplier"] for r in permutation_rows],
        "round_adjacent_basis_swaps": [r["adjacent_basis_swaps"] for r in permutation_rows],
        "permutations": permutation_rows,
        "wide_vs_reference": wide_vs_ref,
        "recycled_vs_reference": recycled_vs_ref,
        "recycled_vs_wide": recycled_vs_wide,
        "wide_probability_sum": float(wide.sum()),
        "recycled_probability_sum": float(recycled.sum()),
        "wide_permissive_factor_recovery": permissive_recovery_probability(wide, phase_bits),
        "recycled_permissive_factor_recovery": permissive_recovery_probability(recycled, phase_bits),
        "wide_direct_order_factor_recovery": direct_recovery_probability(wide, phase_bits),
        "recycled_direct_order_factor_recovery": direct_recovery_probability(recycled, phase_bits),
        "reference_permissive_factor_recovery": permissive_recovery_probability(reference, phase_bits),
        "reference_direct_order_factor_recovery": direct_recovery_probability(reference, phase_bits),
        "top_recycled": top_rows(recycled, phase_bits),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU ideal validation for the generic full-residue N=35 Shor path."
    )
    ap.add_argument("--phase-bits", type=int, nargs="+", default=[2, 4, 6, 8])
    ap.add_argument("--tolerance", type=float, default=1e-10)
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor35_generic_permutation"),
    )
    args = ap.parse_args()

    bits_list = sorted(set(args.phase_bits))
    if not bits_list or bits_list[0] < 1:
        raise SystemExit("all --phase-bits values must be >= 1")

    rows = []
    for bits in bits_list:
        row = run_case(bits, args.tolerance)
        rows.append(row)
        print(f"\n===== IDEAL VALIDATION: {bits} PHASE BITS =====")
        print(json.dumps(row, indent=2))

    overall = all(r["pass"] for r in rows)
    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "N": N,
        "a": A,
        "phase_bits": bits_list,
        "tolerance": args.tolerance,
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "validation_order_not_used_by_construction": discover_order_for_validation_only(),
        "pass": overall,
        "results": rows,
        "scope_note": (
            "Exact ideal validation of the full-register small-N permutation path. "
            "The construction is order/orbit-independent but remains truth-table/permutation "
            "synthesis rather than scalable modular arithmetic."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    path = args.outdir / "generic_full_permutation_ideal_validation.json"
    path.write_text(json.dumps(out, indent=2) + "\n")

    print("\n===== OVERALL =====")
    print(json.dumps({"pass": overall, "saved": str(path.resolve())}, indent=2))
    print("NO QPU JOB SUBMITTED.")
    return 0 if overall else 2


if __name__ == "__main__":
    raise SystemExit(main())
