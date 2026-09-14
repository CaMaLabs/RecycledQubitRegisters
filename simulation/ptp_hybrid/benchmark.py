#!/usr/bin/env python3
"""Deterministic classical benchmark matrix for the optional PTP/QRR track.

This intentionally compares PTP/kernel search against a conventional wheel-210
baseline (H5), not just naive trial division. Raw JSON and CSV are written under
results/ptp_hybrid/ by default. No quantum backend is contacted.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from pathlib import Path

try:
    from .core import is_prime_trial, root_for_integer, small_base_factor
    from .kernel import lfk_factor, trial_division_factor, verify_actual_pair_present, wheel210_factor
    from .symmetry import full_symmetry_report
except ImportError:
    from core import is_prime_trial, root_for_integer, small_base_factor  # type: ignore
    from kernel import lfk_factor, trial_division_factor, verify_actual_pair_present, wheel210_factor  # type: ignore
    from symmetry import full_symmetry_report  # type: ignore

REFERENCE_N = [15, 21, 33, 35, 39, 51, 55, 65, 77, 85, 91, 143, 187, 221, 323, 437, 899]


def prime_list(lo: int, hi: int) -> list[int]:
    return [n for n in range(max(2, lo), hi + 1) if is_prime_trial(n)]


def generate_semiprimes(seed: int, count: int) -> list[dict]:
    rng = random.Random(seed)
    small = prime_list(11, 199)
    medium = prime_list(211, 997)
    rows = []
    for i in range(count):
        balanced = (i % 2 == 0)
        if balanced:
            pool = medium
            p = rng.choice(pool)
            q = rng.choice(pool)
            shape = "balanced"
        else:
            p = rng.choice(small)
            q = rng.choice(medium)
            shape = "unbalanced"
        if p > q:
            p, q = q, p
        rows.append({"N": p * q, "p": p, "q": q, "shape": shape})
    return rows


def known_factors(n: int) -> tuple[int, int] | None:
    for d in range(2, math.isqrt(n) + 1):
        if n % d == 0:
            return (d, n // d)
    return None


def sympy_factor(n: int) -> dict | None:
    try:
        import sympy  # type: ignore
    except Exception:
        return None
    t0 = time.perf_counter()
    f = sympy.factorint(n)
    elapsed = time.perf_counter() - t0
    expanded = []
    for p, e in f.items():
        expanded.extend([int(p)] * int(e))
    factors = expanded if len(expanded) == 2 else None
    return {"factors": factors, "elapsed_seconds": elapsed}


def benchmark_case(n: int, truth: tuple[int, int] | None = None, label: str = "reference") -> dict:
    if truth is None:
        truth = known_factors(n)
    if truth is None:
        raise ValueError(f"benchmark N={n} is not composite")
    p, q = truth
    if p > q:
        p, q = q, p

    methods = [trial_division_factor(n), wheel210_factor(n), lfk_factor(n)]
    for result in methods:
        if result.factors != (p, q):
            raise AssertionError(
                f"{result.method} failed N={n}: got={result.factors}, truth={(p,q)}"
            )

    base_factor = small_base_factor(n)
    pair_present = True if base_factor is not None else verify_actual_pair_present(p, q)
    if not pair_present:
        raise AssertionError(f"actual PTP factor-root pair missing for N={n}")

    ptp = None
    factor_roots = None
    if base_factor is None:
        ptp = root_for_integer(n)
        factor_roots = sorted((root_for_integer(p), root_for_integer(q)))

    return {
        "label": label,
        "N": n,
        "p": p,
        "q": q,
        "N_root": ptp,
        "factor_roots": factor_roots,
        "small_base_factor_edge_case": base_factor,
        "actual_root_pair_present": pair_present,
        "trial_division": methods[0].to_dict(),
        "wheel210": methods[1].to_dict(),
        "lfk210": methods[2].to_dict(),
        "sympy": sympy_factor(n),
    }


def flatten(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        flat = {
            "label": row["label"], "N": row["N"], "p": row["p"], "q": row["q"],
            "N_root": row["N_root"], "factor_roots": row["factor_roots"],
            "small_base_factor_edge_case": row["small_base_factor_edge_case"],
            "actual_root_pair_present": row["actual_root_pair_present"],
        }
        for name in ("trial_division", "wheel210", "lfk210"):
            stats = row[name]
            for key in ("candidate_pairs", "pair_checks", "integer_search_steps", "divisibility_tests", "elapsed_seconds"):
                flat[f"{name}_{key}"] = stats[key]
        if row["sympy"] is not None:
            flat["sympy_elapsed_seconds"] = row["sympy"]["elapsed_seconds"]
        else:
            flat["sympy_elapsed_seconds"] = None
        out.append(flat)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="PTP/kernel-factor classical benchmark; no QPU use.")
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument("--generated", type=int, default=24)
    ap.add_argument("--outdir", type=Path, default=Path("results/ptp_hybrid"))
    ap.add_argument("--symmetry-prime-limit", type=int, default=2000)
    args = ap.parse_args()

    cases: list[tuple[int, tuple[int, int] | None, str]] = [
        (n, None, "reference") for n in REFERENCE_N
    ]
    for row in generate_semiprimes(args.seed, args.generated):
        cases.append((row["N"], (row["p"], row["q"]), row["shape"]))

    rows = [benchmark_case(n, truth, label) for n, truth, label in cases]
    symmetry = full_symmetry_report(args.symmetry_prime_limit)

    summary = {
        "seed": args.seed,
        "reference_cases": REFERENCE_N,
        "generated_cases": args.generated,
        "case_count": len(rows),
        "qpu_submitted": False,
        "hypothesis_H5_wheel210_baseline_present": True,
        "all_factor_methods_correct": True,
        "all_actual_ptp_pairs_present": all(r["actual_root_pair_present"] for r in rows),
        "symmetry_fixed_n_reduction_safe": symmetry["factor_search_audit"]["safe_for_fixed_n_factor_search"],
        "scope": (
            "Classical constant-factor/residue benchmark only. No complexity-class improvement is inferred."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / "ptp_hybrid_benchmark.json"
    csv_path = args.outdir / "ptp_hybrid_benchmark.csv"
    json_path.write_text(json.dumps({"summary": summary, "symmetry": symmetry, "rows": rows}, indent=2) + "\n")
    flat = flatten(rows)
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat[0].keys()))
        writer.writeheader()
        writer.writerows(flat)

    print(json.dumps(summary, indent=2))
    print("Saved:", json_path.resolve())
    print("Saved:", csv_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
