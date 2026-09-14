#!/usr/bin/env python3
"""Audit saved compiled-Shor hardware JSON against a uniform-output baseline.

Usage:
    python hardware/analyze_shor_noise_floor.py results/ibm_shor35/<result>.json

The script imports the matching N=21 or N=35 runner, reuses its exact
post-processing rules, enumerates every phase-register bitstring under a uniform
distribution, and compares observed factor recovery and distribution metrics to
that random-output baseline. It also reports the strict direct-order metric and
its exact ideal finite-precision expectation.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path


def direct_recovery_probability(mod, phase_bits: int, probabilities):
    total = 0.0
    for y, p in enumerate(probabilities):
        rec = mod.recover_from_phase_integer(y, phase_bits)
        if rec and rec.get("recovery_mode") == "direct":
            total += p
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result", type=Path)
    args = ap.parse_args()

    data = json.loads(args.result.read_text())
    n = int(data["N"])
    phase_bits = int(data["phase_bits"])
    module_name = {21: "ibm_shor21_matched", 35: "ibm_shor35_matched"}.get(n)
    if module_name is None:
        raise SystemExit(f"Unsupported N={n}; currently supports 21 and 35.")

    mod = importlib.import_module(module_name)
    q = 1 << phase_bits
    uniform_counts = {format(y, f"0{phase_bits}b"): 1 for y in range(q)}
    uniform_analysis = mod.analyze_counts(uniform_counts, phase_bits)
    uniform_distribution = mod.distribution_metrics(uniform_counts, phase_bits)

    ideal_probs = mod.ideal_order_distribution(phase_bits)
    ideal_direct = direct_recovery_probability(mod, phase_bits, ideal_probs)
    ideal_metrics = mod.ideal_metrics(phase_bits)

    rows = []
    for item in data.get("results", []):
        a = item["analysis"]
        d = item.get("distribution") or mod.distribution_metrics(item["counts"], phase_bits)
        factor_success = a.get("factor_success_probability_per_shot")
        direct_success = a.get("direct_order_factor_probability_per_shot")
        rows.append({
            "kind": item["kind"],
            "factor_success_probability": factor_success,
            "direct_order_factor_probability": direct_success,
            "factor_success_minus_uniform": (
                factor_success - uniform_analysis["factor_success_probability_per_shot"]
            ),
            "direct_order_minus_uniform": (
                direct_success - uniform_analysis.get("direct_order_factor_probability_per_shot", 0.0)
            ),
            "factor_success_fraction_of_ideal_margin": (
                None
                if ideal_metrics["ideal_factor_recovery_under_same_postprocessor"]
                == uniform_analysis["factor_success_probability_per_shot"]
                else (
                    factor_success - uniform_analysis["factor_success_probability_per_shot"]
                )
                / (
                    ideal_metrics["ideal_factor_recovery_under_same_postprocessor"]
                    - uniform_analysis["factor_success_probability_per_shot"]
                )
            ),
            "direct_order_fraction_of_ideal_margin": (
                None
                if ideal_direct == uniform_analysis.get("direct_order_factor_probability_per_shot", 0.0)
                else (
                    direct_success - uniform_analysis.get("direct_order_factor_probability_per_shot", 0.0)
                )
                / (
                    ideal_direct - uniform_analysis.get("direct_order_factor_probability_per_shot", 0.0)
                )
            ),
            "hellinger_fidelity_to_ideal": d.get("hellinger_fidelity_to_ideal"),
            "total_variation_distance_to_ideal": d.get("total_variation_distance_to_ideal"),
        })

    out = {
        "N": n,
        "phase_bits": phase_bits,
        "ideal_reference": {
            "factor_success_probability": ideal_metrics["ideal_factor_recovery_under_same_postprocessor"],
            "direct_order_factor_probability": ideal_direct,
        },
        "uniform_baseline": {
            "factor_success_probability": uniform_analysis["factor_success_probability_per_shot"],
            "direct_order_factor_probability": uniform_analysis.get("direct_order_factor_probability_per_shot"),
            "hellinger_fidelity_to_ideal": uniform_distribution["hellinger_fidelity_to_ideal"],
            "total_variation_distance_to_ideal": uniform_distribution["total_variation_distance_to_ideal"],
        },
        "observed": rows,
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
