#!/usr/bin/env python3
"""A26: exact small-width adder comparison and conservative operation ledger.

This is an arithmetic-kernel study, NOT a complete Shor modular multiplier,
compiled FT circuit, physical-qubit estimate or quantum speedup claim.
Stdlib only, no backend/QPU, and no factoring oracle.
"""
import argparse
import cmath
import json
import math
import time

def dft(vec, inverse=False):
    size = len(vec)
    sign = 1 if inverse else -1
    return [sum(vec[x] * cmath.exp(sign * 2j * math.pi * x * k / size)
                for x in range(size)) / math.sqrt(size)
            for k in range(size)]

def fourier_add_basis(x, a, bits):
    """DFT, diagonal phases, inverse DFT: |x> -> |x+a mod 2**bits>."""
    size = 1 << bits
    vec = [0j] * size
    vec[x] = 1
    freq = dft(vec)
    rotated = [z * cmath.exp(-2j * math.pi * k * a / size)
               for k, z in enumerate(freq)]
    return dft(rotated, inverse=True)

def classical_add(x, a, bits):
    return (x + a) % (1 << bits)

def cancelled_ops(ops):
    """Only remove adjacent self-inverse gates with identical operands."""
    stack = []
    for op in ops:
        if stack and stack[-1] == op:
            stack.pop()
        else:
            stack.append(op)
    return stack

def audit(bits, sample_limit):
    size = 1 << bits
    cases = [(x, a) for x in range(size) for a in range(size)]
    if sample_limit:
        cases = cases[:sample_limit]
    maximum_error = 0.0
    started = time.perf_counter()
    for x, a in cases:
        actual = fourier_add_basis(x, a, bits)
        expected = classical_add(x, a, bits)
        err = max(abs(z - (1 if i == expected else 0))
                  for i, z in enumerate(actual))
        maximum_error = max(maximum_error, err)
        if err > 1e-9:
            raise AssertionError((bits, x, a, err))
    runtime = time.perf_counter() - started

    # Deterministic symbolic optimization sanity check: does not claim
    # these gates form a fully synthesized modular-adder circuit.
    ops = [("X", 0), ("X", 0), ("CNOT", 0, 1), ("CNOT", 0, 1),
           ("X", 1), ("CNOT", 0, 1)]
    optimized = cancelled_ops(ops)
    assert optimized == [("X", 1), ("CNOT", 0, 1)]

    # These counts are the ideal abstract QFT adder's high-level rotations,
    # not native backend gates or surface-code T/Toffoli costs.
    qft_rotations = bits * (bits - 1) // 2
    phase_rotations = bits
    qft_hadamards = 2 * bits
    fourier_rotations = 2 * qft_rotations + phase_rotations
    return {
        "bits": bits, "checked_inputs": len(cases),
        "maximum_amplitude_error": maximum_error,
        "seconds_classical_simulation": round(runtime, 6),
        "variants": {
            "baseline": {"kernel": "binary_integer_addition",
                         "exact_result": True,
                         "gate_cost": None, "circuit_synthesized": False},
            "compiler": {"kernel": "binary_integer_addition",
                         "symbolic_involution_test_before": len(ops),
                         "symbolic_involution_test_after": len(optimized),
                         "gate_cost": None, "circuit_synthesized": False},
            "fourier": {"kernel": "ideal_qft_diagonal_phase_inverse_qft",
                        "abstract_hadamards": qft_hadamards,
                        "abstract_controlled_phase_rotations": 2 * qft_rotations,
                        "abstract_single_phase_rotations": phase_rotations,
                        "abstract_total_rotations": fourier_rotations,
                        "circuit_synthesized": False},
            "hybrid": {"kernel": "fourier_plus_symbolic_cancel_pass",
                       "symbolic_involution_test_before": len(ops),
                       "symbolic_involution_test_after": len(optimized),
                       "actual_fourier_cost_reduction": None,
                       "circuit_synthesized": False}
        },
        "verified": maximum_error <= 1e-9
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-bits", type=int, default=4)
    ap.add_argument("--sample-limit", type=int, default=0,
                    help="0 means exhaustive")
    args = ap.parse_args()
    if not 1 <= args.max_bits <= 6:
        ap.error("max-bits must be 1..6 (exact DFT simulator)")
    if args.sample_limit < 0:
        ap.error("sample-limit must be nonnegative")
    rows = [audit(b, args.sample_limit) for b in range(1, args.max_bits + 1)]
    print(json.dumps({
        "experiment": "A26_SMALL_ADDER_FOUR_WAY_KERNEL_AUDIT",
        "status": "PASS_SMALL_KERNEL_EQUIVALENCE_NOT_FACTORIZATION_BENCHMARK",
        "qpu_jobs": 0, "classical_preconditioning": "A24 retained as separate public-first gate",
        "important_limit": "Four variants are architecture placeholders; only exact QFT adder action and a local rewrite rule are verified. No reversible ripple/modular multiplication circuit, compiler comparison, gate-level hybrid, native error model or speedup is measured.",
        "rows": rows
    }, indent=2))

if __name__ == "__main__":
    main()
