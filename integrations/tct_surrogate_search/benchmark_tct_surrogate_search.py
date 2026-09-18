#!/usr/bin/env python3
"""Zero-QPU compiler benchmark for a FAIR-MAST TCT surrogate search.

The input JSON is produced by Fusion_Blanket_Design_TCT's
fair_mast_tct_quantum_search_export.py.  It contains a classically precomputed
320-point reduced-order parameter surface plus marked low-loss settings.

This script builds a Grover-style *table oracle* over those marked indices and
measures how the resulting narrow/deep circuit compiles on exact-width physical
patches.  It uses the recycled-register project's interaction-graph machinery
for patch scoring and logical placement.

Important: the table oracle is not a reversible implementation of the fusion
surrogate.  Therefore this is a compiler/workload experiment and an idealized
oracle-query model, not evidence of end-to-end quantum speedup or fusion physics.
No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "hardware"
if str(HARDWARE) not in sys.path:
    sys.path.insert(0, str(HARDWARE))

import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-18-tct-surrogate-search-compiler-v1"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_surrogate_search_compiler.json"


def apply_marked_phase(qc: QuantumCircuit, qubits: list[int], index: int) -> None:
    """Flip the phase of one computational basis state, little-endian index."""
    n = len(qubits)
    if n == 1:
        if index == 0:
            qc.x(qubits[0])
        qc.z(qubits[0])
        if index == 0:
            qc.x(qubits[0])
        return

    zero_mask = [q for bit, q in enumerate(qubits) if ((index >> bit) & 1) == 0]
    for q in zero_mask:
        qc.x(q)
    target = qubits[-1]
    controls = qubits[:-1]
    qc.h(target)
    qc.mcx(controls, target)
    qc.h(target)
    for q in reversed(zero_mask):
        qc.x(q)


def apply_oracle(qc: QuantumCircuit, qubits: list[int], marked: list[int]) -> None:
    for index in marked:
        apply_marked_phase(qc, qubits, index)


def apply_diffuser(qc: QuantumCircuit, qubits: list[int]) -> None:
    qc.h(qubits)
    qc.x(qubits)
    if len(qubits) == 1:
        qc.z(qubits[0])
    else:
        target = qubits[-1]
        qc.h(target)
        qc.mcx(qubits[:-1], target)
        qc.h(target)
    qc.x(qubits)
    qc.h(qubits)


def build_grover(index_qubits: int, marked: list[int], rounds: int) -> QuantumCircuit:
    qc = QuantumCircuit(index_qubits, name="tct_surrogate_grover")
    q = list(range(index_qubits))
    qc.h(q)
    for _ in range(rounds):
        apply_oracle(qc, q, marked)
        apply_diffuser(qc, q)
    return qc


def graph_diameter(cm) -> int:
    dist = mapper.all_pairs_shortest(cm)
    return int(max(max(row) for row in dist))


def select_screen(predicted: list[dict], controls: int, seed: int, exhaustive: bool) -> list[int]:
    if exhaustive:
        return [int(row["patch_index"]) for row in predicted]
    min_score = min(float(row["predictor_score"]) for row in predicted)
    min_diameter = min(int(row["patch_diameter"]) for row in predicted)
    chosen = {
        int(row["patch_index"])
        for row in predicted
        if abs(float(row["predictor_score"]) - min_score) <= 1e-12
        or int(row["patch_diameter"]) == min_diameter
    }
    remaining = [int(row["patch_index"]) for row in predicted if int(row["patch_index"]) not in chosen]
    rng = random.Random(seed)
    if controls > 0 and remaining:
        chosen.update(rng.sample(remaining, min(controls, len(remaining))))
    return sorted(chosen)


def compact(row):
    if row is None:
        return None
    keys = (
        "topology", "patch_index", "predictor_rank", "predictor_score",
        "patch_diameter", "screen_reason", "layout_mode", "mapping_method",
        "initial_layout", "native_cz", "compiled_depth", "compiled_size",
        "compiled_touched_qubits", "seed_transpiler", "compile_seconds",
    )
    return {k: row.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dataset", type=Path)
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--grover-rounds", type=int, default=1)
    ap.add_argument("--candidate-patches", type=int, default=24)
    ap.add_argument("--patch-seed", type=int, default=118021)
    ap.add_argument("--control-patches", type=int, default=4)
    ap.add_argument("--mapping-restarts", type=int, default=96)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--probe-optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--transpiler-seeds", default="8776,2026,9401")
    ap.add_argument("--exhaustive", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.grover_rounds < 1 or args.candidate_patches < 1 or args.control_patches < 0:
        raise SystemExit("invalid arguments")
    seeds = [int(x.strip()) for x in args.transpiler_seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("at least one transpiler seed is required")

    data = json.loads(args.dataset.read_text())
    valid_count = int(data["valid_candidate_count"])
    marked = [int(x) for x in data["marked_indices"]]
    search_meta = data["search_metadata"]
    logical = int(search_meta["index_qubits"])
    padded = 1 << logical
    if padded != int(search_meta["padded_search_space"]):
        raise RuntimeError("dataset index-width metadata is inconsistent")
    if not marked or any(x < 0 or x >= valid_count for x in marked):
        raise RuntimeError("dataset marked indices are invalid")

    qc = build_grover(logical, marked, args.grover_rounds)

    print("ZERO-QPU TCT SURROGATE SEARCH COMPILER BENCHMARK")
    print(
        f"valid_candidates={valid_count} padded={padded} marked={len(marked)} "
        f"index_qubits={logical} compiled_grover_rounds={args.grover_rounds}"
    )
    print(
        f"dataset_idealized_grover_iterations={search_meta.get('optimal_grover_iterations_idealized')} "
        f"objective={data.get('objective')}"
    )

    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, logical, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    night_full, night_source = topo.nighthawk_map(service)
    if night_source.get("proxy"):
        print("IMPORTANT: Nighthawk side is a 10x12 square-lattice PROXY, not exact Phoenix.")

    probe_backend = topo.generic(logical, mapper.full_coupling(logical))
    probe_compiled, probe_elapsed = mapper.compile_circuit(
        qc,
        probe_backend,
        args.profile,
        args.probe_optimization_level,
        8776,
        list(range(logical)),
    )
    pair_weights, interaction_meta = mapper.extract_two_qubit_interactions(probe_compiled)
    probe_stats = mapper.compiled_stats(qc, probe_compiled, probe_elapsed)

    result = {
        "experiment": "tct_surrogate_search_compiler_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "dataset": str(args.dataset),
        "dataset_experiment": data.get("experiment"),
        "objective": data.get("objective"),
        "valid_candidate_count": valid_count,
        "padded_search_space": padded,
        "marked_count": len(marked),
        "index_qubits": logical,
        "compiled_grover_rounds": args.grover_rounds,
        "dataset_search_metadata": search_meta,
        "candidate_patches": args.candidate_patches,
        "patch_seed": args.patch_seed,
        "control_patches": args.control_patches,
        "exhaustive": bool(args.exhaustive),
        "transpiler_seeds": seeds,
        "nighthawk_source": night_source,
        "interaction_probe": {**interaction_meta, **probe_stats},
        "scope_boundary": (
            "Compiler/topology benchmark over a classically precomputed table oracle. "
            "The Grover query model does not include reversible surrogate evaluation, "
            "state-preparation cost, fault tolerance, QPU error, or fusion-physics validation."
        ),
        "topologies": {},
        "compile_rows": [],
    }

    topologies = {
        "fez_heavy_hex_topology": fez_full,
        "nighthawk_square_lattice_topology": night_full,
    }

    for topology_index, (topology_name, full_cm) in enumerate(topologies.items()):
        patches = ens.patch_ensemble(
            full_cm,
            logical,
            args.candidate_patches,
            args.patch_seed + topology_index * 1_000_003,
        )
        predicted = []
        for patch in patches:
            subcm = cap.relabeled_subgraph(full_cm, patch["nodes"])
            mapping, score, method = mapper.optimize_mapping(
                subcm,
                pair_weights,
                8,
                args.mapping_restarts,
                args.patch_seed + 104729 * int(patch["patch_index"]) + topology_index,
            )
            predicted.append(
                {
                    "patch_index": int(patch["patch_index"]),
                    "patch_mode": patch["mode"],
                    "patch_nodes": [int(x) for x in patch["nodes"]],
                    "patch_undirected_edges": int(patch["stats"]["undirected_edges"]),
                    "patch_mean_degree": float(patch["stats"]["degree_mean"]),
                    "patch_diameter": graph_diameter(subcm),
                    "predictor_score": float(score),
                    "mapping_method": method,
                    "initial_layout": [int(x) for x in mapping],
                }
            )
        predicted.sort(
            key=lambda row: (
                row["predictor_score"],
                row["patch_diameter"],
                -row["patch_undirected_edges"],
                row["patch_index"],
            )
        )
        for rank, row in enumerate(predicted, start=1):
            row["predictor_rank"] = rank

        selected = select_screen(
            predicted,
            args.control_patches,
            args.patch_seed + 17 * topology_index,
            args.exhaustive,
        )
        by_index = {int(row["patch_index"]): row for row in predicted}
        min_score = min(float(row["predictor_score"]) for row in predicted)
        min_diameter = min(int(row["patch_diameter"]) for row in predicted)
        for row in predicted:
            reasons = []
            if abs(float(row["predictor_score"]) - min_score) <= 1e-12:
                reasons.append("minimum_interaction_distance")
            if int(row["patch_diameter"]) == min_diameter:
                reasons.append("minimum_physical_diameter")
            row["screen_reason"] = "+".join(reasons) if reasons else "control_or_unscreened"

        print(f"\n===== {topology_name} =====")
        print(
            f"candidate_patches={len(predicted)} selected={len(selected)} "
            f"compile_reduction={1-len(selected)/len(predicted):.2%} "
            f"min_score={min_score:.0f} min_diameter={min_diameter}"
        )

        patch_by_index = {int(p["patch_index"]): p for p in patches}
        for patch_index in selected:
            pred = by_index[patch_index]
            patch = patch_by_index[patch_index]
            subcm = cap.relabeled_subgraph(full_cm, patch["nodes"])
            backend = topo.generic(logical, subcm)
            for layout_mode, layout in (
                ("interaction_fixed", pred["initial_layout"]),
                ("qiskit_auto", None),
            ):
                good = []
                for seed in seeds:
                    try:
                        compiled, elapsed = mapper.compile_circuit(
                            qc,
                            backend,
                            args.profile,
                            args.optimization_level,
                            seed,
                            layout,
                        )
                        stats = mapper.compiled_stats(qc, compiled, elapsed)
                        if int(stats["compiled_touched_qubits"]) > logical:
                            raise AssertionError("exact-width capacity lock violated")
                        good.append(
                            {
                                "success": True,
                                "topology": topology_name,
                                "patch_index": patch_index,
                                "predictor_rank": int(pred["predictor_rank"]),
                                "predictor_score": float(pred["predictor_score"]),
                                "patch_diameter": int(pred["patch_diameter"]),
                                "screen_reason": pred["screen_reason"],
                                "layout_mode": layout_mode,
                                "mapping_method": pred["mapping_method"],
                                "initial_layout": None if layout is None else list(layout),
                                "seed_transpiler": seed,
                                **stats,
                            }
                        )
                    except Exception as exc:
                        result["compile_rows"].append(
                            {
                                "success": False,
                                "topology": topology_name,
                                "patch_index": patch_index,
                                "layout_mode": layout_mode,
                                "seed_transpiler": seed,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            }
                        )
                if good:
                    best = min(
                        good,
                        key=lambda row: (
                            row["native_cz"], row["compiled_depth"], row["seed_transpiler"]
                        ),
                    )
                    result["compile_rows"].append(best)
                    print(
                        f"patch={patch_index:02d} rank={pred['predictor_rank']:02d} "
                        f"diam={pred['patch_diameter']} mode={layout_mode:17s} "
                        f"CZ={best['native_cz']} depth={best['compiled_depth']}"
                    )

        result["topologies"][topology_name] = {
            "predicted": predicted,
            "selected_patch_indices": selected,
            "minimum_predictor_score": min_score,
            "minimum_physical_diameter": min_diameter,
            "selected_fraction": len(selected) / len(predicted),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    summary = {}
    for topology_name in topologies:
        fixed = [
            row for row in result["compile_rows"]
            if row.get("success") and row.get("topology") == topology_name
            and row.get("layout_mode") == "interaction_fixed"
        ]
        auto = [
            row for row in result["compile_rows"]
            if row.get("success") and row.get("topology") == topology_name
            and row.get("layout_mode") == "qiskit_auto"
        ]
        best_fixed = min(fixed, key=lambda r: (r["native_cz"], r["compiled_depth"])) if fixed else None
        best_auto = min(auto, key=lambda r: (r["native_cz"], r["compiled_depth"])) if auto else None
        summary[topology_name] = {
            "best_screened_fixed": compact(best_fixed),
            "best_screened_auto": compact(best_auto),
            "fixed_over_auto_cz_ratio": (
                None if not best_fixed or not best_auto or not best_auto["native_cz"]
                else best_fixed["native_cz"] / best_auto["native_cz"]
            ),
            "fixed_over_auto_depth_ratio": (
                None if not best_fixed or not best_auto or not best_auto["compiled_depth"]
                else best_fixed["compiled_depth"] / best_auto["compiled_depth"]
            ),
        }
    result["summary"] = summary
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    print("\n===== TCT SEARCH INTERACTION GRAPH =====")
    print(
        f"logical_width={logical} weighted_edges={interaction_meta['weighted_edge_count']} "
        f"total_2q_weight={interaction_meta['total_two_qubit_weight']:.0f} "
        f"probe_CZ={probe_stats['native_cz']} probe_depth={probe_stats['compiled_depth']}"
    )
    print("\n===== TCT SEARCH COMPILER SUMMARY =====")
    for topology_name, row in summary.items():
        print(topology_name)
        print("  best_fixed=" + json.dumps(row["best_screened_fixed"], default=str))
        print("  best_auto=" + json.dumps(row["best_screened_auto"], default=str))
        print(
            f"  fixed/auto CZ={row['fixed_over_auto_cz_ratio']} "
            f"depth={row['fixed_over_auto_depth_ratio']}"
        )
    print("\n===== QUERY MODEL (IDEALIZED) =====")
    print(json.dumps(search_meta, indent=2, sort_keys=True))
    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
