#!/usr/bin/env python3
"""Analyze top-k recall and regret from an exhaustive v3 mapper JSON result."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def pct(x):
    return None if x is None else 100.0 * float(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result", type=Path)
    ap.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 6, 10])
    args = ap.parse_args()

    data = json.loads(args.result.read_text())
    ks = sorted(set(args.k))
    out = {}

    for topology, pred_obj in data["patch_predictions"].items():
        ranked = pred_obj["ranked"]
        rank_by_patch = {int(r["patch_index"]): int(r["predictor_rank"]) for r in ranked}

        rows = [
            r for r in data["compile_rows"]
            if r.get("success") and r.get("topology") == topology
        ]
        fixed = [r for r in rows if r.get("layout_mode") == "interaction_fixed"]
        auto = [r for r in rows if r.get("layout_mode") == "qiskit_auto"]
        if not fixed or not auto:
            continue

        best_fixed = min(fixed, key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"]))
        best_auto = min(auto, key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"]))

        fixed_by_rank = sorted(fixed, key=lambda r: rank_by_patch[int(r["patch_index"])])
        auto_by_rank = sorted(auto, key=lambda r: rank_by_patch[int(r["patch_index"])])

        result = {
            "candidate_patch_count": len(ranked),
            "best_fixed_patch": int(best_fixed["patch_index"]),
            "best_fixed_predictor_rank": rank_by_patch[int(best_fixed["patch_index"])],
            "best_auto_patch": int(best_auto["patch_index"]),
            "best_auto_predictor_rank": rank_by_patch[int(best_auto["patch_index"])],
            "k": {},
        }

        for k in ks:
            fk = [r for r in fixed_by_rank if rank_by_patch[int(r["patch_index"])] <= k]
            ak = [r for r in auto_by_rank if rank_by_patch[int(r["patch_index"])] <= k]
            bfk = min(fk, key=lambda r: (r["native_cz"], r["compiled_depth"])) if fk else None
            bak = min(ak, key=lambda r: (r["native_cz"], r["compiled_depth"])) if ak else None
            result["k"][str(k)] = {
                "fixed_recall_global_best_patch": bool(
                    best_fixed and rank_by_patch[int(best_fixed["patch_index"])] <= k
                ),
                "auto_recall_global_best_patch": bool(
                    best_auto and rank_by_patch[int(best_auto["patch_index"])] <= k
                ),
                "fixed_cz_regret_fraction": None if bfk is None else bfk["native_cz"] / best_fixed["native_cz"] - 1.0,
                "fixed_depth_regret_fraction": None if bfk is None else bfk["compiled_depth"] / best_fixed["compiled_depth"] - 1.0,
                "auto_cz_regret_fraction": None if bak is None else bak["native_cz"] / best_auto["native_cz"] - 1.0,
                "auto_depth_regret_fraction": None if bak is None else bak["compiled_depth"] / best_auto["compiled_depth"] - 1.0,
                "compile_reduction_fraction": 1.0 - min(k, len(ranked)) / len(ranked),
            }

        out[topology] = result

    print(json.dumps(out, indent=2))
    print("\n===== TOP-K SUMMARY =====")
    for topology, result in out.items():
        print(topology)
        print(
            f"  global best fixed rank={result['best_fixed_predictor_rank']} "
            f"auto rank={result['best_auto_predictor_rank']}"
        )
        for k, row in result["k"].items():
            print(
                f"  k={k}: fixed_recall={row['fixed_recall_global_best_patch']} "
                f"auto_recall={row['auto_recall_global_best_patch']} "
                f"fixed_CZ_regret={pct(row['fixed_cz_regret_fraction']):.3f}% "
                f"compile_reduction={pct(row['compile_reduction_fraction']):.2f}%"
            )


if __name__ == "__main__":
    main()
