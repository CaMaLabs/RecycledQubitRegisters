#!/usr/bin/env python3
"""Analyze top-k and score-bucket recall/regret from an exhaustive v3 mapper result."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def pct(x):
    return None if x is None else 100.0 * float(x)


def eq_score(a, b, tol=1e-12):
    return abs(float(a) - float(b)) <= tol


def score_bucket_metrics(ranked, patch_index):
    by_patch = {int(r["patch_index"]): r for r in ranked}
    target = by_patch[int(patch_index)]
    score = float(target["predictor_score"])
    scores = [float(r["predictor_score"]) for r in ranked]
    unique = sorted(set(scores))
    dense_rank = 1 + sum(1 for s in unique if s < score and not eq_score(s, score))
    return {
        "predictor_score": score,
        "dense_score_rank": int(dense_rank),
        "equal_score_bucket_size": int(sum(eq_score(s, score) for s in scores)),
        "score_threshold_patch_count": int(sum(s <= score or eq_score(s, score) for s in scores)),
        "minimum_score": float(min(scores)),
        "minimum_score_bucket_size": int(sum(eq_score(s, min(scores)) for s in scores)),
        "is_minimum_score_bucket": bool(eq_score(score, min(scores))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result", type=Path)
    ap.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 6, 10])
    ap.add_argument("--json-out", type=Path, default=None)
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

        best_fixed = min(
            fixed,
            key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"]),
        )
        best_auto = min(
            auto,
            key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"]),
        )

        fixed_by_rank = sorted(fixed, key=lambda r: rank_by_patch[int(r["patch_index"])])
        auto_by_rank = sorted(auto, key=lambda r: rank_by_patch[int(r["patch_index"])])

        fixed_bucket = score_bucket_metrics(ranked, int(best_fixed["patch_index"]))
        auto_bucket = score_bucket_metrics(ranked, int(best_auto["patch_index"]))

        result = {
            "candidate_patch_count": len(ranked),
            "best_fixed_patch": int(best_fixed["patch_index"]),
            "best_fixed_predictor_rank": rank_by_patch[int(best_fixed["patch_index"])],
            "best_fixed_score_bucket": fixed_bucket,
            "best_auto_patch": int(best_auto["patch_index"]),
            "best_auto_predictor_rank": rank_by_patch[int(best_auto["patch_index"])],
            "best_auto_score_bucket": auto_bucket,
            "k": {},
        }

        for k in ks:
            fk = [r for r in fixed_by_rank if rank_by_patch[int(r["patch_index"])] <= k]
            ak = [r for r in auto_by_rank if rank_by_patch[int(r["patch_index"])] <= k]
            bfk = min(fk, key=lambda r: (r["native_cz"], r["compiled_depth"])) if fk else None
            bak = min(ak, key=lambda r: (r["native_cz"], r["compiled_depth"])) if ak else None
            result["k"][str(k)] = {
                "fixed_recall_global_best_patch": bool(
                    rank_by_patch[int(best_fixed["patch_index"])] <= k
                ),
                "auto_recall_global_best_patch": bool(
                    rank_by_patch[int(best_auto["patch_index"])] <= k
                ),
                "fixed_cz_regret_fraction": (
                    None if bfk is None
                    else bfk["native_cz"] / best_fixed["native_cz"] - 1.0
                ),
                "fixed_depth_regret_fraction": (
                    None if bfk is None
                    else bfk["compiled_depth"] / best_fixed["compiled_depth"] - 1.0
                ),
                "auto_cz_regret_fraction": (
                    None if bak is None
                    else bak["native_cz"] / best_auto["native_cz"] - 1.0
                ),
                "auto_depth_regret_fraction": (
                    None if bak is None
                    else bak["compiled_depth"] / best_auto["compiled_depth"] - 1.0
                ),
                "compile_reduction_fraction": 1.0 - min(k, len(ranked)) / len(ranked),
            }

        out[topology] = result

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(out, indent=2) + "\n")

    print(json.dumps(out, indent=2))
    print("\n===== TOP-K + SCORE-BUCKET SUMMARY =====")
    for topology, result in out.items():
        fb = result["best_fixed_score_bucket"]
        ab = result["best_auto_score_bucket"]
        print(topology)
        print(
            f"  global best fixed rank={result['best_fixed_predictor_rank']} "
            f"auto rank={result['best_auto_predictor_rank']}"
        )
        print(
            f"  fixed score={fb['predictor_score']:.6g} "
            f"dense_score_rank={fb['dense_score_rank']} "
            f"equal_bucket={fb['equal_score_bucket_size']} "
            f"threshold_count={fb['score_threshold_patch_count']} "
            f"minimum_bucket={fb['is_minimum_score_bucket']}"
        )
        print(
            f"  auto  score={ab['predictor_score']:.6g} "
            f"dense_score_rank={ab['dense_score_rank']} "
            f"equal_bucket={ab['equal_score_bucket_size']} "
            f"threshold_count={ab['score_threshold_patch_count']} "
            f"minimum_bucket={ab['is_minimum_score_bucket']}"
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
