#!/usr/bin/env python3
"""A28 first integrated cost ledger: public-first Dark Star wheel + A27 kernels.

This is a reproducible *proxy* integration: the original spectral Fourier/NTT
pruner is NOT yet wired into this script. Counts are logical gate operations
for a repeated-MCX incrementer, NOT decomposed fault-tolerant resource costs.
No RSA break, quantum advantage, or performance projection is claimed.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

gate = load("a24_gate", ROOT / "integrations/darkstar_hybrid/qrr_a24_n35_public_first_gate.py")
a27 = load("a27_kernel", ROOT / "hardware/qrr_a27_reversible_fourier_comparison.py")

def cohort():
    # N=35 is a deliberately classically-solved guard, 143=11*13 survives
    # the limited (2,3,5,7) wheel, and 221=13*17 also survives.
    return ((35, 2), (35, 8), (143, 2), (221, 2))

def run():
    rows = []
    for n, base in cohort():
        pre = gate.public_preflight(n, base)
        classical = pre["factors"] is not None
        assert (not classical) or pre["factors"][0] * pre["factors"][1] == n
        # Use fixed, tiny arithmetic kernel workloads, not claimed order
        # finding circuits or factor recovery on the unresolved semiprimes.
        bits, x, addend = 4, (n + base) % 16, base % 16
        binary, binary_ops = a27.reversible_add(x, addend, bits)
        amps = a27.mod.fourier_add_basis(x, addend, bits)
        err = max(abs(z - (1 if i == binary else 0)) for i, z in enumerate(amps))
        assert binary == (x + addend) % 16 and err < 1e-9
        rows.append({
            "n": n, "base": base, "public_first_route": pre["route"],
            "classically_factored": classical,
            "wheel_work": pre["work"],
            "arithmetic_validation_even_when_skipped": True,
            "fourier_kernel_error": err,
            "standalone_reversible_logical_mcx_or_x": binary_ops,
            "after_public_first_reversible_logical_mcx_or_x": 0 if classical else binary_ops,
            "after_public_first_ideal_fourier_rotations_proxy": 0 if classical else 16,
            "actual_full_shor_gate_count": None,
            "original_fourier_ntt_pruner_integrated": False,
            "factor_recovered_for_unresolved_case": False,
        })
    assert sum(r["classically_factored"] for r in rows) == 2
    return {
        "experiment": "A28_PUBLIC_FIRST_ARITHMETIC_PROXY",
        "status": "PASS_PROXY_INTEGRATION_NOT_FULL_FOURIER_PRUNING",
        "qpu_jobs": 0,
        "note": "Preserves A24 public-wheel gate and A27 exact reversible/Fourier kernel checks. The original Dark Star spectral Fourier/NTT pruner, modular multiplication, quantum compilation, Quaspy, recycled register lifecycle and true end-to-end resources are NOT integrated. Skipping arithmetic on wheel-factored N is not quantum speedup.",
        "rows": rows
    }

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
