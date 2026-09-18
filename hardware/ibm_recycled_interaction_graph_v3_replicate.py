#!/usr/bin/env python3
"""Run independent exhaustive v3 patch-predictor replications and aggregate recall.

This runner does not modify the predictor. It launches the already-frozen v3
exhaustive harness on independent patch seeds, then summarizes both ordinal
recall@k and score-bucket recall. The score-bucket metric is important because
multiple physical patches can share the same minimum weighted-distance score.

No Sampler is instantiated and no QPU job is submitted by the child harness.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def analyze_one(path: Path, ks):
    data = json.loads(path.read_text())
    out = {}
    for topology, pred_obj in data["patch_predictions"].items():
        ranked = pred_obj["ranked"]
        rank_by_patch = {
            int(r["patch_index"]): int(r["predictor_rank"]) for r in ranked
        }
        score_by_patch = {
            int(r["patch_index"]): float(r["predictor_score"]) for r in ranked
        }
        minimum_score = min(score_by_patch.values())
        minimum_bucket = {
            p for p, s in score_by_patch.items()
            if abs(s - minimum_score) <= 1e-12
        }

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
        bfp = int(best_fixed["patch_index"])
        bap = int(best_auto["patch_index"])
        bfs = score_by_patch[bfp]
        bas = score_by_patch[bap]

        entry = {
            "candidate_patch_count": len(ranked),
            "minimum_predictor_score": minimum_score,
            "minimum_score_bucket_size": len(minimum_bucket),
            "minimum_score_compile_reduction_fraction": 1.0 - len(minimum_bucket) / len(ranked),
            "best_fixed_patch": bfp,
            "best_fixed_predictor_rank": rank_by_patch[bfp],
            "best_fixed_predictor_score": bfs,
            "best_fixed_score_threshold_count": sum(
                float(r["predictor_score"]) <= bfs + 1e-12 for r in ranked
            ),
            "best_fixed_in_minimum_score_bucket": bfp in minimum_bucket,
            "best_auto_patch": bap,
            "best_auto_predictor_rank": rank_by_patch[bap],
            "best_auto_predictor_score": bas,
            "best_auto_score_threshold_count": sum(
                float(r["predictor_score"]) <= bas + 1e-12 for r in ranked
            ),
            "best_auto_in_minimum_score_bucket": bap in minimum_bucket,
            "k": {},
        }

        for k in ks:
            fixed_k = [
                r for r in fixed
                if rank_by_patch[int(r["patch_index"])] <= k
            ]
            auto_k = [
                r for r in auto
                if rank_by_patch[int(r["patch_index"])] <= k
            ]
            best_fk = min(
                fixed_k, key=lambda r: (r["native_cz"], r["compiled_depth"])
            ) if fixed_k else None
            best_ak = min(
                auto_k, key=lambda r: (r["native_cz"], r["compiled_depth"])
            ) if auto_k else None
            entry["k"][str(k)] = {
                "fixed_recall": rank_by_patch[bfp] <= k,
                "auto_recall": rank_by_patch[bap] <= k,
                "fixed_cz_regret_fraction": (
                    None if best_fk is None
                    else best_fk["native_cz"] / best_fixed["native_cz"] - 1.0
                ),
                "auto_cz_regret_fraction": (
                    None if best_ak is None
                    else best_ak["native_cz"] / best_auto["native_cz"] - 1.0
                ),
            }

        out[topology] = entry
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch-seeds", nargs="+", type=int, default=[45137, 62026])
    ap.add_argument("--transpiler-seeds", default="8776,2026,9401")
    ap.add_argument("--phase-bits", type=int, default=32)
    ap.add_argument("--candidate-patches", type=int, default=48)
    ap.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 6, 10])
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/qubit_recycling/interaction_graph_replications"),
    )
    ap.add_argument(
        "--aggregate-out",
        type=Path,
        default=Path(
            "results/qubit_recycling/"
            "ibm_recycled_interaction_graph_v3_replication_summary.json"
        ),
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    child = root / "hardware" / "ibm_recycled_interaction_graph_mapper_v3_exhaustive.py"
    args.outdir.mkdir(parents=True, exist_ok=True)

    aggregate = {
        "experiment": "ibm_recycled_interaction_graph_v3_independent_replications",
        "zero_qpu": True,
        "patch_seeds": args.patch_seeds,
        "transpiler_seeds": args.transpiler_seeds,
        "phase_bits": args.phase_bits,
        "candidate_patches": args.candidate_patches,
        "k": sorted(set(args.k)),
        "runs": [],
    }

    for seed in args.patch_seeds:
        out = args.outdir / f"v3_exhaustive_patchseed_{seed}.json"
        cmd = [
            sys.executable,
            str(child),
            "--phase-bits", str(args.phase_bits),
            "--candidate-patches", str(args.candidate_patches),
            "--patch-seed", str(seed),
            "--transpiler-seeds", args.transpiler_seeds,
            "--out", str(out),
        ]
        print("\n===== REPLICATION patch_seed=" + str(seed) + " =====")
        print(" ".join(cmd))
        subprocess.run(cmd, cwd=root, check=True)
        analysis = analyze_one(out, sorted(set(args.k)))
        aggregate["runs"].append({
            "patch_seed": seed,
            "result_file": str(out),
            "analysis": analysis,
        })
        args.aggregate_out.parent.mkdir(parents=True, exist_ok=True)
        args.aggregate_out.write_text(json.dumps(aggregate, indent=2) + "\n")

    topologies = sorted({
        topology
        for run in aggregate["runs"]
        for topology in run["analysis"]
    })
    summary = {}
    for topology in topologies:
        rows = [
            run["analysis"][topology]
            for run in aggregate["runs"]
            if topology in run["analysis"]
        ]
        obj = {
            "replication_count": len(rows),
            "best_fixed_predictor_ranks": [
                r["best_fixed_predictor_rank"] for r in rows
            ],
            "best_auto_predictor_ranks": [
                r["best_auto_predictor_rank"] for r in rows
            ],
            "minimum_score_bucket_sizes": [
                r["minimum_score_bucket_size"] for r in rows
            ],
            "minimum_score_bucket_fixed_recall_fraction": sum(
                r["best_fixed_in_minimum_score_bucket"] for r in rows
            ) / len(rows),
            "minimum_score_bucket_auto_recall_fraction": sum(
                r["best_auto_in_minimum_score_bucket"] for r in rows
            ) / len(rows),
            "minimum_score_bucket_compile_reduction_fractions": [
                r["minimum_score_compile_reduction_fraction"] for r in rows
            ],
            "k": {},
        }
        for k in sorted(set(args.k)):
            key = str(k)
            fixed_hits = [r["k"][key]["fixed_recall"] for r in rows]
            auto_hits = [r["k"][key]["auto_recall"] for r in rows]
            obj["k"][key] = {
                "fixed_recall_fraction": sum(fixed_hits) / len(fixed_hits),
                "auto_recall_fraction": sum(auto_hits) / len(auto_hits),
                "fixed_max_cz_regret_fraction": max(
                    r["k"][key]["fixed_cz_regret_fraction"] for r in rows
                ),
                "auto_max_cz_regret_fraction": max(
                    r["k"][key]["auto_cz_regret_fraction"] for r in rows
                ),
                "compile_reduction_fraction": (
                    1.0 - min(k, args.candidate_patches) / args.candidate_patches
                ),
            }
        summary[topology] = obj

    aggregate["summary"] = summary
    args.aggregate_out.write_text(json.dumps(aggregate, indent=2) + "\n")

    print("\n===== REPLICATION SUMMARY =====")
    for topology, obj in summary.items():
        print(topology)
        print("  fixed global-best ranks=" + str(obj["best_fixed_predictor_ranks"]))
        print("  auto  global-best ranks=" + str(obj["best_auto_predictor_ranks"]))
        print(
            "  minimum-score bucket sizes="
            + str(obj["minimum_score_bucket_sizes"])
        )
        print(
            f"  minimum-score bucket recall fixed="
            f"{obj['minimum_score_bucket_fixed_recall_fraction']:.3f} "
            f"auto={obj['minimum_score_bucket_auto_recall_fraction']:.3f}"
        )
        for k, row in obj["k"].items():
            print(
                f"  k={k}: fixed_recall={row['fixed_recall_fraction']:.3f} "
                f"auto_recall={row['auto_recall_fraction']:.3f} "
                f"fixed_max_CZ_regret={100*row['fixed_max_cz_regret_fraction']:.3f}% "
                f"compile_reduction={100*row['compile_reduction_fraction']:.2f}%"
            )

    print(f"\nwrote {args.aggregate_out}")
    print("NO QPU JOB SUBMITTED.")


if __name__ == "__main__":
    main()
