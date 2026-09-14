#!/usr/bin/env python3
"""Audit saved compiled-Shor hardware JSON against a uniform-output baseline.

Usage:
    python hardware/analyze_shor_noise_floor.py results/ibm_shor35/<result>.json

The script imports the matching N=21 or N=35 runner, reuses its exact
post-processing rules, enumerates every phase-register bitstring under a uniform
distribution, and compares observed factor recovery and distribution metrics to
that random-output baseline. It also surfaces the stricter direct-order metric
already stored in each result's analysis block.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path


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

    rows = []
    for item in data.get("results", []):
        a = item["analysis"]
        d = item.get("distribution") or mod.distribution_metrics(item["counts"], phase_bits)
        rows.append({
            "kind": item["kind"],
            "factor_success_probability": a.get("factor_success_probability_per_shot"),
            "direct_order_factor_probability": a.get("direct_order_factor_probability_per_shot"),
            "factor_success_minus_uniform": (
                a.get("factor_success_probability_per_shot", 0.0)
                - uniform_analysis["factor_success_probability_per_shot"]
            ),
            "hellinger_fidelity_to_ideal": d.get("hellinger_fidelity_to_ideal"),
            "total_variation_distance_to_ideal": d.get("total_variation_distance_to_ideal"),
        })

    out = {
        "N": n,
        "phase_bits": phase_bits,
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
