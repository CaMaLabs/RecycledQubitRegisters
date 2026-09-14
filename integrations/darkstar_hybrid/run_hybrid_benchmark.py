#!/usr/bin/env python3
"""Integrated Dark Star + hybrid-QPE benchmark on self-generated semiprimes."""
from __future__ import annotations

import argparse
import csv
import json
from math import gcd, lcm
from pathlib import Path
import random
import statistics
import time

from darkstar_v2 import (
    darkstar_fermat_factor,
    fermat_factor,
    generated_close_semiprime,
    midpoint_residues,
    random_prime,
)
from hybrid_quantum import (
    NoiseModel,
    choose_base_with_nontrivial_order,
    guaranteed_lambda_small_factors,
    simulate_order_finding,
    width_model,
)


def random_balanced_semiprime(bits: int, rng: random.Random) -> tuple[int, int, int]:
    while True:
        p = random_prime(bits, rng)
        q = random_prime(bits, rng)
        if p != q:
            return p*q, min(p,q), max(p,q)


def median(xs):
    return statistics.median(xs) if xs else None


def run(args):
    rng = random.Random(args.seed)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    noise = NoiseModel(
        readout_error=args.readout_error,
        controlled_u_error=args.controlled_u_error,
        reset_error=args.reset_error,
        feedback_error=args.feedback_error,
        phase_jitter_bins=args.phase_jitter_bins,
    )

    rows = []
    t0 = time.perf_counter()

    for bits in args.close_bits:
        for trial in range(args.trials):
            n,p,q = generated_close_semiprime(bits, args.close_steps, rng)
            _, xstats = midpoint_residues(n, args.midpoint_modulus)
            base = fermat_factor(n)
            ds = darkstar_fermat_factor(n, args.midpoint_modulus)
            route = "darkstar_classical" if ds.square_tests <= args.classical_square_budget else "hybrid_order_finding"
            rows.append({
                "suite": "close_semiprime_router",
                "factor_bits": bits,
                "trial": trial,
                "n": n,
                "n_bits": n.bit_length(),
                "p": p,
                "q": q,
                "factor_gap": q-p,
                "fermat_square_tests": base.square_tests,
                "darkstar_square_tests": ds.square_tests,
                "darkstar_reduction": base.square_tests/ds.square_tests,
                "darkstar_seconds": ds.setup_seconds+ds.search_seconds,
                "midpoint_modulus": args.midpoint_modulus,
                "midpoint_allowed": xstats.allowed_count,
                "midpoint_density": xstats.density,
                "midpoint_pruning_factor": xstats.pruning_factor,
                "router_decision": route,
            })

    quantum_rows = []
    for bits in args.quantum_bits:
        for trial in range(args.trials):
            n,p,q = random_balanced_semiprime(bits, rng)
            a,r = choose_base_with_nontrivial_order(n, rng)
            phase_bits = args.phase_bits if args.phase_bits else 2*n.bit_length()
            widths = width_model(n, phase_bits)
            _, xstats = midpoint_residues(n, args.midpoint_modulus)
            lam_hint = guaranteed_lambda_small_factors(n)
            lam_true = lcm(p-1,q-1)
            guaranteed = lam_hint["guaranteed_lambda_divisor"]
            hint_valid = (lam_true % guaranteed == 0)
            order_hint_overlap = gcd(r, guaranteed)

            seed_w = rng.randrange(1<<63)
            seed_h = rng.randrange(1<<63)
            ideal_noise = NoiseModel(0.0,0.0,0.0,0.0,0.0)
            wide_ideal = simulate_order_finding(
                n,a,r,"wide",args.shots,random.Random(seed_w),ideal_noise,phase_bits
            )
            hyb_ideal = simulate_order_finding(
                n,a,r,"6C2Q",args.shots,random.Random(seed_h),ideal_noise,phase_bits
            )
            wide_noisy = simulate_order_finding(
                n,a,r,"wide",args.shots,random.Random(seed_w ^ 0xA5A5),noise,phase_bits
            )
            hyb_noisy = simulate_order_finding(
                n,a,r,"6C2Q",args.shots,random.Random(seed_h ^ 0x5A5A),noise,phase_bits
            )

            common = {
                "suite": "hybrid_order_finding",
                "factor_bits": bits,
                "trial": trial,
                "n": n,
                "n_bits": n.bit_length(),
                "p": p,
                "q": q,
                "base_a": a,
                "true_order": r,
                "lambda_true": lam_true,
                "guaranteed_lambda_divisor": guaranteed,
                "lambda_hint_valid": hint_valid,
                "order_gcd_with_lambda_hint": order_hint_overlap,
                "order_contains_full_lambda_hint": (r % guaranteed == 0),
                "midpoint_modulus": args.midpoint_modulus,
                "midpoint_allowed": xstats.allowed_count,
                "midpoint_pruning_factor": xstats.pruning_factor,
                "phase_bits": phase_bits,
                "work_qubits_model": widths.work_qubits,
                "wide_total_model_qubits": widths.wide_total_model_qubits,
                "hybrid_total_model_qubits": widths.hybrid_total_model_qubits,
                "modeled_total_width_reduction": widths.modeled_total_width_reduction,
            }
            for regime,result in (("ideal",wide_ideal),("ideal",hyb_ideal),("noisy",wide_noisy),("noisy",hyb_noisy)):
                qr = {**common, "regime": regime, **result}
                quantum_rows.append(qr)
                rows.append(qr)

    csv_path = outdir / "darkstar_hybrid_trials.csv"
    fieldnames = sorted({k for row in rows for k in row})
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    close = [r for r in rows if r["suite"]=="close_semiprime_router"]
    wide_ideal_rows = [r for r in quantum_rows if r["architecture"]=="wide" and r["regime"]=="ideal"]
    hyb_ideal_rows = [r for r in quantum_rows if r["architecture"]=="6C2Q" and r["regime"]=="ideal"]
    wide_noisy_rows = [r for r in quantum_rows if r["architecture"]=="wide" and r["regime"]=="noisy"]
    hyb_noisy_rows = [r for r in quantum_rows if r["architecture"]=="6C2Q" and r["regime"]=="noisy"]

    summary = {
        "scope": "self-generated semiprimes only",
        "seed": args.seed,
        "trials_per_case": args.trials,
        "shots_per_quantum_case": args.shots,
        "noise_model": noise.__dict__,
        "darkstar": {
            "midpoint_modulus": args.midpoint_modulus,
            "median_square_test_reduction": median([r["darkstar_reduction"] for r in close]),
            "median_midpoint_pruning_factor": median([r["midpoint_pruning_factor"] for r in close]),
            "classical_route_fraction": sum(r["router_decision"]=="darkstar_classical" for r in close)/len(close) if close else None,
        },
        "hybrid_quantum": {
            "median_ideal_wide_factor_success_probability": median([r["factor_success_probability"] for r in wide_ideal_rows]),
            "median_ideal_6C2Q_factor_success_probability": median([r["factor_success_probability"] for r in hyb_ideal_rows]),
            "median_noisy_wide_factor_success_probability": median([r["factor_success_probability"] for r in wide_noisy_rows]),
            "median_noisy_6C2Q_factor_success_probability": median([r["factor_success_probability"] for r in hyb_noisy_rows]),
            "median_wide_total_model_qubits": median([r["wide_total_model_qubits"] for r in wide_ideal_rows]),
            "median_6C2Q_total_model_qubits": median([r["hybrid_total_model_qubits"] for r in hyb_ideal_rows]),
            "median_total_width_reduction": median([r["modeled_total_width_reduction"] for r in hyb_ideal_rows]),
            "note": "total width excludes modular-arithmetic ancillas; 6C2Q recycles only the phase/control qubit",
        },
        "order_structure": {
            "lambda_hint_valid_fraction": sum(r["lambda_hint_valid"] for r in wide_ideal_rows)/len(wide_ideal_rows) if wide_ideal_rows else None,
            "order_contains_full_hint_fraction": sum(r["order_contains_full_lambda_hint"] for r in wide_ideal_rows)/len(wide_ideal_rows) if wide_ideal_rows else None,
            "median_guaranteed_lambda_divisor": median([r["guaranteed_lambda_divisor"] for r in wide_ideal_rows]),
            "median_gcd_order_with_hint": median([r["order_gcd_with_lambda_hint"] for r in wide_ideal_rows]),
            "note": "lambda divisibility hints are inferred from N residues only; they are diagnostics, not assumed speedups",
        },
        "elapsed_seconds": time.perf_counter()-t0,
    }

    summary_path = outdir / "darkstar_hybrid_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    text = []
    text.append("Dark Star + Hybrid Quantum Benchmark")
    text.append("="*44)
    text.append("Self-generated semiprimes only")
    text.append("")
    text.append(f"Dark Star median square-test reduction: {summary['darkstar']['median_square_test_reduction']:.3f}x")
    text.append(f"Dark Star median midpoint pruning: {summary['darkstar']['median_midpoint_pruning_factor']:.3f}x")
    text.append(f"Classical router fraction: {summary['darkstar']['classical_route_fraction']:.3f}")
    text.append("")
    text.append(f"Ideal wide QPE median factor success: {summary['hybrid_quantum']['median_ideal_wide_factor_success_probability']:.3f}")
    text.append(f"Ideal 6C2Q median factor success: {summary['hybrid_quantum']['median_ideal_6C2Q_factor_success_probability']:.3f}")
    text.append(f"Noisy wide QPE median factor success: {summary['hybrid_quantum']['median_noisy_wide_factor_success_probability']:.3f}")
    text.append(f"Noisy 6C2Q median factor success: {summary['hybrid_quantum']['median_noisy_6C2Q_factor_success_probability']:.3f}")
    text.append(f"Median modeled total width reduction: {summary['hybrid_quantum']['median_total_width_reduction']:.3f}x")
    text.append("(Width excludes modular-arithmetic ancillas; only the QPE phase register is recycled.)")
    text.append("")
    text.append(f"Lambda-hint validity: {summary['order_structure']['lambda_hint_valid_fraction']:.3f}")
    text.append(f"Order contains full lambda hint: {summary['order_structure']['order_contains_full_hint_fraction']:.3f}")
    text.append(f"Median guaranteed lambda divisor: {summary['order_structure']['median_guaranteed_lambda_divisor']}")
    text.append(f"Elapsed: {summary['elapsed_seconds']:.3f} s")
    report_path = outdir / "RESULTS_HYBRID.txt"
    report_path.write_text("\n".join(text)+"\n")
    print("\n".join(text))
    print(f"\nWrote {csv_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--shots", type=int, default=256)
    ap.add_argument("--close-bits", type=int, nargs="+", default=[24,28,32])
    ap.add_argument("--close-steps", type=int, default=50000)
    ap.add_argument("--quantum-bits", type=int, nargs="+", default=[5,6,7])
    ap.add_argument("--phase-bits", type=int, default=0, help="0 => 2*N.bit_length()")
    ap.add_argument("--midpoint-modulus", type=int, default=1155)
    ap.add_argument("--classical-square-budget", type=int, default=10000)
    ap.add_argument("--readout-error", type=float, default=0.005)
    ap.add_argument("--controlled-u-error", type=float, default=0.002)
    ap.add_argument("--reset-error", type=float, default=0.001)
    ap.add_argument("--feedback-error", type=float, default=0.001)
    ap.add_argument("--phase-jitter-bins", type=float, default=0.05, help="Gaussian phase jitter in QPE-bin units")
    ap.add_argument("--outdir", default="hybrid_results")
    args = ap.parse_args()
    run(args)

if __name__ == "__main__":
    main()
