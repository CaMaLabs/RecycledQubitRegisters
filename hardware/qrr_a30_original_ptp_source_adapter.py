#!/usr/bin/env python3
"""A30: execute original Dark Star PTP source, unchanged, alongside A27 kernel.

This directly imports the existing PTP factor-pair/kernel search and the
original Dark Star midpoint filter. No reimplemented substitute is used.
This is not yet the independent Fourier/NTT spectral pruner.
"""
from __future__ import annotations
import importlib.util
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulation.ptp_hybrid.core import candidate_factor_pairs, root_for_integer
from simulation.ptp_hybrid.kernel import (
    lfk_factor, wheel210_factor, trial_division_factor, verify_actual_pair_present,
)

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

audit=load("darkstar_original",ROOT/"hardware/dark_star_ptp_shor_audit.py")
a27=load("a27",ROOT/"hardware/qrr_a27_reversible_fourier_comparison.py")

def run():
    samples=(143,221,899,1763,2491)
    qrs=audit.quadratic_residues(210)
    rows=[]
    for n in samples:
        baseline=trial_division_factor(n)
        wheel=wheel210_factor(n)
        ptp=lfk_factor(n)
        fermat=audit.fermat_search_counts(n)
        filtered=audit.fermat_search_counts(n,210,qrs)
        assert baseline.factors==wheel.factors==ptp.factors
        p,q=ptp.factors
        assert p*q==n and verify_actual_pair_present(p,q)
        assert filtered["solution_x"]==fermat["solution_x"]
        assert filtered["solution_y"]==fermat["solution_y"]
        # Same small arithmetic correctness test on all rows; not an
        # assertion that Fourier changes factor search costs.
        x=n%16
        value,ops=a27.reversible_add(x,2,4)
        ideal=a27.mod.fourier_add_basis(x,2,4)
        err=max(abs(z-(1 if k==value else 0)) for k,z in enumerate(ideal))
        assert err<1e-9
        rows.append({
          "n":n,"factors":[p,q],"ptp_root":root_for_integer(n),
          "original_ptp_pair_count":len(candidate_factor_pairs(n)),
          "original_ptp_pair_present":True,
          "trial_divisions":baseline.divisibility_tests,
          "wheel210_divisions":wheel.divisibility_tests,
          "original_lfk_pair_checks":ptp.pair_checks,
          "original_lfk_integer_steps":ptp.integer_search_steps,
          "original_lfk_divisions":ptp.divisibility_tests,
          "original_fermat_x_steps":fermat["x_steps"],
          "original_fermat_square_tests":fermat["exact_square_tests"],
          "original_midpoint_square_tests":filtered["exact_square_tests"],
          "original_midpoint_residue_checks":filtered["residue_checks"],
          "original_midpoint_square_test_savings":fermat["exact_square_tests"]-filtered["exact_square_tests"],
          "reversible_logical_ops_fixed_kernel":ops,
          "ideal_fourier_kernel_error":err,
          "real_gate_compilation":None,
          "fourier_ntt_spectral_pruning_integrated":False,
        })
    return {"experiment":"A30_ORIGINAL_DARK_STAR_PTP_SOURCE_ADAPTER",
            "status":"PASS_ORIGINAL_PTP_SOURCE_INTEGRATION_PENDING_RUN",
            "qpu_jobs":0,
            "provenance":["simulation/ptp_hybrid/core.py",
                          "simulation/ptp_hybrid/kernel.py",
                          "hardware/dark_star_ptp_shor_audit.py",
                          "hardware/qrr_a27_reversible_fourier_comparison.py"],
            "limitations":"Runs actual original PTP and midpoint source; Fourier/NTT spectral pruning is still separate. All test moduli are easy classical instances. The arithmetic kernel is fixed-size and not a Shor multiplier. Different operation categories cannot be aggregated as equivalent costs; no practical speedup asserted.",
            "rows":rows}

if __name__=="__main__":
    print(json.dumps(run(),indent=2))
