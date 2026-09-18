#!/usr/bin/env python3
"""Run the preregistered v4 distance-plus-diameter screening test.

The frozen screening rule is defined in docs/RECYCLED_INTERACTION_GRAPH_V4_PREREG.md:

    screen = minimum interaction-distance bucket
             UNION minimum induced-subgraph-diameter bucket

This script first runs the unchanged v3 exhaustive harness on a fresh patch seed,
then evaluates the preregistered screen against exhaustive ground truth. The
screen itself uses only predictor scores and physical-subgraph topology; compiled
CZ/depth are used only afterward to measure recall/regret.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import deque
from pathlib import Path

import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width


def adjacency(cm):
    n = cm.size()
    adj = [set() for _ in range(n)]
    for u, v in cm.get_edges():
        u, v = int(u), int(v)
        if u != v:
            adj[u].add(v)
            adj[v].add(u)
    return adj


def diameter(cm):
    adj = adjacency(cm)
    n = len(adj)
    best = 0
    for s in range(n):
        dist = [-1] * n
        dist[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] == -1:
                    dist[v] = dist[u] + 1
                    q.append(v)
        if any(d < 0 for d in dist):
            raise RuntimeError("candidate patch is disconnected")
        best = max(best, max(dist))
    return int(best)


def best_row(rows):
    return min(
        rows,
        key=lambda r: (int(r["native_cz"]), int(r["compiled_depth"]), int(r["patch_index"])),
    )


def screen_best(rows, screen):
    kept = [r for r in rows if int(r["patch_index"]) in screen]
    return best_row(kept) if kept else None


def analyze(data, full_maps):
    result = {}
    for topology_name, pred_obj in data["patch_predictions"].items():
        ranked = pred_obj["ranked"]
        full_cm = full_maps[topology_name]

        # Candidate selection uses ONLY frozen predictor scores and physical graph
        # diameter. Do this before reading compiled ground-truth rows below.
        min_score = min(float(r["predictor_score"]) for r in ranked)
        distance_bucket = {
            int(r["patch_index"]) for r in ranked
            if abs(float(r["predictor_score"]) - min_score) <= 1e-12
        }

        patch_diameters = {}
        for r in ranked:
            idx = int(r["patch_index"])
            nodes = [int(x) for x in r["patch_nodes"]]
            subcm = cap.relabeled_subgraph(full_cm, nodes)
            patch_diameters[idx] = diameter(subcm)
        min_diameter = min(patch_diameters.values())
        diameter_bucket = {
            idx for idx, d in patch_diameters.items() if d == min_diameter
        }
        union_screen = set(distance_bucket) | set(diameter_bucket)

        rows = [
            r for r in data["compile_rows"]
            if r.get("success") and r.get("topology") == topology_name
        ]
        fixed = [r for r in rows if r.get("layout_mode") == "interaction_fixed"]
        auto = [r for r in rows if r.get("layout_mode") == "qiskit_auto"]
        if not fixed or not auto:
            continue

        global_fixed = best_row(fixed)
        global_auto = best_row(auto)
        dist_fixed = screen_best(fixed, distance_bucket)
        dist_auto = screen_best(auto, distance_bucket)
        union_fixed = screen_best(fixed, union_screen)
        union_auto = screen_best(auto, union_screen)

        def metrics(global_row, screened_row, screen):
            return {
                "global_best_patch": int(global_row["patch_index"]),
                "global_best_native_cz": int(global_row["native_cz"]),
                "screen_recall_global_best": int(global_row["patch_index"]) in screen,
                "screen_best_patch": None if screened_row is None else int(screened_row["patch_index"]),
                "screen_best_native_cz": None if screened_row is None else int(screened_row["native_cz"]),
                "cz_regret_fraction": None if screened_row is None else (
                    float(screened_row["native_cz"]) / float(global_row["native_cz"]) - 1.0
                ),
            }

        result[topology_name] = {
            "candidate_patch_count": len(ranked),
            "minimum_distance_score": min_score,
            "minimum_distance_bucket": sorted(distance_bucket),
            "minimum_distance_bucket_size": len(distance_bucket),
            "minimum_physical_diameter": min_diameter,
            "minimum_diameter_bucket": sorted(diameter_bucket),
            "minimum_diameter_bucket_size": len(diameter_bucket),
            "union_screen": sorted(union_screen),
            "union_screen_size": len(union_screen),
            "union_compile_reduction_fraction": 1.0 - len(union_screen) / len(ranked),
            "patch_diameters": {str(k): int(v) for k, v in sorted(patch_diameters.items())},
            "baseline_distance_only": {
                "fixed": metrics(global_fixed, dist_fixed, distance_bucket),
                "auto": metrics(global_auto, dist_auto, distance_bucket),
            },
            "v4_union": {
                "fixed": metrics(global_fixed, union_fixed, union_screen),
                "auto": metrics(global_auto, union_auto, union_screen),
            },
        }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch-seed", type=int, default=118021)
    ap.add_argument("--transpiler-seeds", default="8776,2026,9401")
    ap.add_argument("--phase-bits", type=int, default=32)
    ap.add_argument("--candidate-patches", type=int, default=48)
    ap.add_argument(
        "--result-out",
        type=Path,
        default=Path(
            "results/qubit_recycling/interaction_graph_replications/"
            "v4_preregistered_exhaustive_patchseed_118021.json"
        ),
    )
    ap.add_argument(
        "--analysis-out",
        type=Path,
        default=Path(
            "results/qubit_recycling/interaction_graph_replications/"
            "v4_preregistered_analysis_patchseed_118021.json"
        ),
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    child = root / "hardware" / "ibm_recycled_interaction_graph_mapper_v3_exhaustive.py"
    args.result_out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(child),
        "--phase-bits", str(args.phase_bits),
        "--candidate-patches", str(args.candidate_patches),
        "--patch-seed", str(args.patch_seed),
        "--transpiler-seeds", args.transpiler_seeds,
        "--out", str(args.result_out),
    ]
    print("===== V4 PREREGISTERED FRESH EXHAUSTIVE RUN =====")
    print(" ".join(cmd))
    subprocess.run(cmd, cwd=root, check=True)

    data = json.loads(args.result_out.read_text())
    logical = int(data["logical_qubits"])
    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, logical, "ibm_fez")
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    night_full, _ = topo.nighthawk_map(service)
    full_maps = {
        "fez_heavy_hex_topology": fez_full,
        "nighthawk_square_lattice_topology": night_full,
    }

    analysis = {
        "experiment": "ibm_recycled_interaction_graph_v4_preregistered_test",
        "zero_qpu": True,
        "patch_seed": args.patch_seed,
        "transpiler_seeds": args.transpiler_seeds,
        "screen_rule": "minimum interaction-distance bucket UNION minimum physical-diameter bucket",
        "source_result": str(args.result_out),
        "topologies": analyze(data, full_maps),
    }
    args.analysis_out.parent.mkdir(parents=True, exist_ok=True)
    args.analysis_out.write_text(json.dumps(analysis, indent=2) + "\n")

    print("\n===== V4 PREREGISTERED SCREEN SUMMARY =====")
    for topology_name, obj in analysis["topologies"].items():
        print(topology_name)
        print(
            f"  distance_bucket={obj['minimum_distance_bucket_size']} "
            f"diameter={obj['minimum_physical_diameter']} "
            f"diameter_bucket={obj['minimum_diameter_bucket_size']} "
            f"union={obj['union_screen_size']}/{obj['candidate_patch_count']} "
            f"compile_reduction={100*obj['union_compile_reduction_fraction']:.2f}%"
        )
        for mode in ("fixed", "auto"):
            b = obj["baseline_distance_only"][mode]
            u = obj["v4_union"][mode]
            print(
                f"  {mode}: baseline_recall={b['screen_recall_global_best']} "
                f"baseline_CZ_regret={100*b['cz_regret_fraction']:.3f}% | "
                f"v4_recall={u['screen_recall_global_best']} "
                f"v4_CZ_regret={100*u['cz_regret_fraction']:.3f}%"
            )

    print(f"\nwrote {args.analysis_out}")
    print("NO QPU JOB SUBMITTED.")


if __name__ == "__main__":
    main()
