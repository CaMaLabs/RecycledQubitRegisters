#!/usr/bin/env python3
"""Analyze frozen TCT routing-screen recall from an exhaustive routing JSON.

This is an offline, zero-QPU analysis helper for
benchmark_tct_semantic_factored_routing.py.  Given an exhaustive result, it
reconstructs the previously frozen screen

    minimum interaction-distance bucket
      union minimum physical-diameter bucket
      union random controls

using the same patch seed/control count, then compares the screened optimum with
the exhaustive global optimum for each topology and layout mode.

No compilation, IBM service access, or QPU execution is performed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import benchmark_tct_semantic_factored_routing as routing


def best(rows: list[dict]) -> dict | None:
    good = [r for r in rows if r.get("success")]
    if not good:
        return None
    return min(
        good,
        key=lambda r: (
            int(r["native_cz"]),
            int(r["compiled_depth"]),
            int(r.get("seed_transpiler", 0)),
            int(r["patch_index"]),
        ),
    )


def fmt(row: dict | None) -> str:
    if row is None:
        return "none"
    return (
        f"patch={row['patch_index']} rank={row.get('predictor_rank')} "
        f"CZ={row['native_cz']} depth={row['compiled_depth']}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("result", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    data = json.loads(args.result.read_text(encoding="utf-8"))
    if not data.get("exhaustive"):
        raise RuntimeError("input routing artifact is not exhaustive")

    patch_seed = int(data["patch_seed"])
    controls = int(data.get("control_patches", 4))
    compile_rows = [r for r in data.get("compile_rows", []) if r.get("success")]

    payload = {
        "experiment": "tct_routing_screen_recall_analysis_v1",
        "source": str(args.result),
        "zero_qpu": True,
        "patch_seed": patch_seed,
        "control_patches": controls,
        "topologies": {},
    }

    print("===== TCT ROUTING SCREEN RECALL ANALYSIS =====")
    print(f"patch_seed={patch_seed} controls={controls}")

    for topology_index, (topology_name, tmeta) in enumerate(data["topologies"].items()):
        predicted = list(tmeta["predicted"])
        deterministic_min_score = min(float(r["predictor_score"]) for r in predicted)
        deterministic_min_diam = min(int(r["patch_diameter"]) for r in predicted)
        deterministic = sorted(
            int(r["patch_index"])
            for r in predicted
            if abs(float(r["predictor_score"]) - deterministic_min_score) <= 1e-12
            or int(r["patch_diameter"]) == deterministic_min_diam
        )
        screened = routing.select_screen(
            predicted,
            controls,
            patch_seed + 17 * topology_index,
            False,
        )

        topo_out = {
            "deterministic_patch_indices": deterministic,
            "screened_patch_indices": screened,
            "candidate_count": len(predicted),
            "screened_count": len(screened),
            "compile_reduction": 1.0 - len(screened) / len(predicted),
            "layout_modes": {},
        }

        print(f"\n===== {topology_name} =====")
        print(
            f"deterministic={deterministic} screened={screened} "
            f"compile_reduction={topo_out['compile_reduction']:.2%}"
        )

        for mode in ("interaction_fixed", "qiskit_auto"):
            rows = [
                r for r in compile_rows
                if r.get("topology") == topology_name and r.get("layout_mode") == mode
            ]
            global_best = best(rows)
            deterministic_best = best([r for r in rows if int(r["patch_index"]) in deterministic])
            screened_best = best([r for r in rows if int(r["patch_index"]) in screened])
            if global_best is None or deterministic_best is None or screened_best is None:
                raise RuntimeError(f"missing successful rows for {topology_name}/{mode}")

            def comparison(candidate: dict) -> dict:
                cz_regret = int(candidate["native_cz"]) - int(global_best["native_cz"])
                depth_regret = int(candidate["compiled_depth"]) - int(global_best["compiled_depth"])
                return {
                    "best": candidate,
                    "cz_regret": cz_regret,
                    "depth_regret": depth_regret,
                    "cz_regret_fraction": cz_regret / int(global_best["native_cz"]),
                    "depth_regret_fraction": depth_regret / int(global_best["compiled_depth"]),
                    "zero_cz_regret": cz_regret == 0,
                    "exact_patch_recall": int(candidate["patch_index"]) == int(global_best["patch_index"]),
                }

            dcmp = comparison(deterministic_best)
            scmp = comparison(screened_best)
            topo_out["layout_modes"][mode] = {
                "global_best": global_best,
                "deterministic_screen": dcmp,
                "full_screen": scmp,
            }

            print(f"{mode}:")
            print(f"  global        {fmt(global_best)}")
            print(
                f"  deterministic {fmt(deterministic_best)} "
                f"CZ_regret={dcmp['cz_regret']} ({dcmp['cz_regret_fraction']:.3%}) "
                f"depth_regret={dcmp['depth_regret']} ({dcmp['depth_regret_fraction']:.3%})"
            )
            print(
                f"  full_screen   {fmt(screened_best)} "
                f"CZ_regret={scmp['cz_regret']} ({scmp['cz_regret_fraction']:.3%}) "
                f"depth_regret={scmp['depth_regret']} ({scmp['depth_regret_fraction']:.3%})"
            )

        payload["topologies"][topology_name] = topo_out

    out = args.out or args.result.with_name(args.result.stem + "_screen_recall.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
