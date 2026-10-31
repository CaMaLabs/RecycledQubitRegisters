#!/usr/bin/env python3
"""A27 stage 1: reversible gate-level binary incrementer vs A26 ideal Fourier adder.

Transparent limited experiment: MCX is a logical primitive, not decomposed
Toffoli/T native gate. Fourier path is still an ideal mathematical kernel.
No factoring speedup claim, no QPU runtime, stdlib only.
"""
import json
import math
from pathlib import Path
import importlib.util

A26 = Path(__file__).with_name("qrr_a26_fourier_kernel_audit.py")
spec = importlib.util.spec_from_file_location("qrr_a26", A26)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def increment_gates(bits):
    # Apply high target first, so lower controls refer to old input bits.
    return [(tuple(range(k)), k) for k in range(bits - 1, -1, -1)]

def apply_mcx(value, controls, target):
    if all(value & (1 << c) for c in controls):
        value ^= 1 << target
    return value

def reversible_add(value, constant, bits):
    gates = increment_gates(bits)
    operations = 0
    for _ in range(constant % (1 << bits)):
        for controls, target in gates:
            value = apply_mcx(value, controls, target)
            operations += 1
    return value, operations

def audit(bits):
    size = 1 << bits
    max_error = 0.0
    cases = 0
    gate_total = 0
    for x in range(size):
        for a in range(size):
            actual, operations = reversible_add(x, a, bits)
            assert actual == (x + a) % size
            ideal = mod.fourier_add_basis(x, a, bits)
            max_error = max(max_error, max(
                abs(amplitude - (1 if k == actual else 0))
                for k, amplitude in enumerate(ideal)))
            gate_total += operations
            cases += 1
    assert max_error < 1e-9
    return dict(bits=bits, cases=cases, max_fourier_error=max_error,
                reversible_logical_gates_total=gate_total,
                reusable_ancilla_assumed=0,
                mcx_decomposition_cost=None,
                qft_compiled_cost=None,
                actual_speedup=None)

def main():
    rows = [audit(bits) for bits in range(1, 5)]
    assert sum(r["cases"] for r in rows) == 340
    print(json.dumps(dict(
        experiment="A27_REVERSIBLE_BINARY_VS_IDEAL_FOURIER_KERNEL",
        status="PASS_LOGICAL_EQUIVALENCE_NO_QUANTUM_ADVANTAGE_CLAIM",
        qpu_jobs=0, measurements=340,
        limitations="Repeated logical MCX incrementer, not optimized reversible multiplier. "
                    "MCX controls not decomposed; Fourier ideal kernel not gate compiled. "
                    "Dark Star Fourier/NTT pruning and full hybrid remain unintegrated.",
        rows=rows), indent=2))

if __name__ == "__main__":
    main()
