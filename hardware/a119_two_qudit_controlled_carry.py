#!/usr/bin/env python3
"""A119: exact two-qudit (d=8) controlled carry baseline.

Pure logical simulation, NOT a pulse implementation or hardware speedup.
Registers: binary control c and two octits lo, hi; value = lo + 8*hi.
Operation: if c, add one modulo 64. This is a building block, not
modular multiplication or Shor order finding. No noise or QPU involved.
"""
import argparse
import json
import numpy as np

D = 8
SIZE = 2 * D * D

def index(c, lo, hi):
    return (c * D + hi) * D + lo

def decode(i):
    lo = i % D
    hi = (i // D) % D
    c = i // (D * D)
    return c, lo, hi

def map_increment(i):
    c, lo, hi = decode(i)
    if not c:
        return i
    return index(c, (lo + 1) % D, (hi + int(lo == D - 1)) % D)

def gate_matrix(mapping):
    out = np.zeros((SIZE, SIZE), dtype=np.complex128)
    for i in range(SIZE):
        out[mapping(i), i] = 1
    return out

def local_low(i):
    c, lo, hi = decode(i)
    return index(c, (lo + c) % D, hi)

def carry_high(i):
    c, lo, hi = decode(i)
    # After low increment, a wrap occurred precisely when lo == 0.
    return index(c, lo, (hi + int(bool(c) and lo == 0)) % D)

def run(trials=1000, seed=119):
    target = gate_matrix(map_increment)
    low = gate_matrix(local_low)
    high = gate_matrix(carry_high)
    composed = high @ low
    basis_error = float(np.max(np.abs(composed - target)))
    unitarity_error = float(np.max(np.abs(target.conj().T @ target - np.eye(SIZE))))
    inverse_error = float(np.max(np.abs(composed.conj().T @ composed - np.eye(SIZE))))
    rng = np.random.default_rng(seed)
    state_error = 0.
    for _ in range(trials):
        psi = rng.normal(size=SIZE) + 1j * rng.normal(size=SIZE)
        psi /= np.linalg.norm(psi)
        state_error = max(state_error, float(np.max(np.abs(composed @ psi - target @ psi))))
    assert max(basis_error, unitarity_error, inverse_error, state_error) < 1e-12
    return {
        "status": "PASS_EXACT_LOGICAL_MODEL",
        "dimension": D,
        "carriers": {"control_qubits": 1, "data_qudits": 2},
        "qubit_equivalent_data_capacity": 6,
        "basis_inputs_verified": SIZE,
        "random_superpositions_verified": trials,
        "max_basis_error": basis_error,
        "max_unitarity_error": unitarity_error,
        "max_inverse_error": inverse_error,
        "max_superposition_error": state_error,
        "logical_stages": ["control_low_increment", "control_and_low_zero_high_increment"],
        "inter_carrier_entangling_gate_decomposition": "NOT_IMPLEMENTED",
        "pulse_duration": None,
        "noise_or_leakage_model": None,
        "hardware_claim": False,
        "notes": "Second stage is a three-carrier conditional gate. It must be decomposed and costed before any speedup claim."
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=119)
    ap.add_argument("--out", default="results/a119_two_qudit_carry.json")
    args = ap.parse_args()
    if args.trials < 0:
        ap.error("--trials must be nonnegative")
    result = run(args.trials, args.seed)
    from pathlib import Path
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
