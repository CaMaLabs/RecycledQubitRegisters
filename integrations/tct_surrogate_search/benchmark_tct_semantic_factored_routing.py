#!/usr/bin/env python3
"""Route the validated six-round TCT semantic-factored ESOP oracle.

This is a zero-QPU compiler/topology experiment. It rebuilds the exact
three-term ESOP/shared-common-control oracle from the frozen TCT arithmetic
specification, requires a passing exhaustive statevector-validation artifact,
and compiles the six-round 10-qubit circuit on exact-width physical patches
sampled from:

- authenticated IBM Fez heavy-hex connectivity; and
- the explicitly labeled 10x12 square-lattice Nighthawk/Phoenix proxy when an
  exact Phoenix/Nighthawk map is unavailable.

It compares interaction-graph fixed placement with Qiskit automatic layout.
No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_boolean_oracle_compression as audit
import benchmark_tct_reversible_arithmetic_oracle as arithmetic
import benchmark_tct_semantic_factored_oracle as semantic
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-18-tct-semantic-factored-routing-v1"
DEFAULT_VALIDATION = ROOT / "results" / "tct_surrogate_search" / "tct_semantic_factored_oracle_validation.json"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_semantic_factored_routing_6round.json"


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
    remaining = [
        int(row["patch_index"])
        for row in predicted
        if int(row["patch_index"]) not in chosen
    ]
    rng = random.Random(seed)
    if controls > 0 and remaining:
        chosen.update(rng.sample(remaining, min(controls, len(remaining))))
    return sorted(chosen)


def build_validated_esop(spec: dict, rounds: int):
    enc = arithmetic.factorized_encoding(spec)
    widths = spec["parameter_register_bits"]
    n = int(widths["total_parameter_bits"])
    marked, decoded = semantic.decode_marked(spec, enc)
    common = semantic.common_constraints(marked, n)
    local_bits = [bit for bit in range(n) if bit not in common]
    local_marked = {semantic.local_state(state, local_bits) for state in marked}
    esop_local = semantic.minimum_esop(local_marked, len(local_bits))
    esop_full = [semantic.merge_local_cube(c, local_bits, common, n) for c in esop_local]
    semantic.verify_xor_cubes(esop_full, set(marked), n)
    qc = semantic.build_variant(
        n,
        marked,
        None,
        rounds,
        factored=True,
        local_cubes=esop_local,
        local_bits=local_bits,
        common=common,
    )
    return qc, {
        "parameter_bits": n,
        "logical_width": qc.num_qubits,
        "marked_states": marked,
        "decoded_marked_rows": decoded,
        "common_constraints": {str(k): int(v) for k, v in sorted(common.items())},
        "local_bits": local_bits,
        "esop_local": [audit.compact_cube(c) for c in esop_local],
    }


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
    ap.add_argument("spec", type=Path)
    ap.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--grover-rounds", type=int, default=6)
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

    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    if not validation.get("all_passed"):
        raise RuntimeError("statevector validation artifact is missing all_passed=True")
    validated = {
        row.get("name"): bool(row.get("passed"))
        for row in validation.get("results", [])
    }
    if not validated.get("three_term_esop_common_factored"):
        raise RuntimeError("three_term_esop_common_factored was not validated successfully")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    qc, oracle_meta = build_validated_esop(spec, args.grover_rounds)
    logical = qc.num_qubits
    if list(validation.get("marked_states", [])) != list(oracle_meta["marked_states"]):
        raise RuntimeError("validation marked-state set does not match rebuilt oracle")

    print("ZERO-QPU TCT SEMANTIC-FACTORED ROUTING BENCHMARK")
    print(
        f"logical_width={logical} parameter_bits={oracle_meta['parameter_bits']} "
        f"grover_rounds={args.grover_rounds} marked={len(oracle_meta['marked_states'])} "
        f"statevector_validation=True"
    )
    print(f"esop_local={oracle_meta['esop_local']} common={oracle_meta['common_constraints']}")

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

    print("\n===== FULLY CONNECTED VALIDATED BASELINE =====")
    print(
        f"CZ={probe_stats['native_cz']} depth={probe_stats['compiled_depth']} "
        f"size={probe_stats['compiled_size']} weighted_edges={interaction_meta['weighted_edge_count']} "
        f"total_2q_weight={interaction_meta['total_two_qubit_weight']:.0f}"
    )

    result = {
        "experiment": "tct_semantic_factored_routing_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "validation_artifact": str(args.validation),
        "validation_all_passed": True,
        "oracle": oracle_meta,
        "grover_rounds": args.grover_rounds,
        "candidate_patches": args.candidate_patches,
        "patch_seed": args.patch_seed,
        "control_patches": args.control_patches,
        "transpiler_seeds": seeds,
        "exhaustive": bool(args.exhaustive),
        "nighthawk_source": night_source,
        "fully_connected_probe": {**interaction_meta, **probe_stats},
        "topologies": {},
        "compile_rows": [],
        "claim_boundary": (
            "Sparse-topology compiler benchmark of an exhaustively statevector-validated, "
            "fixed-instance Boolean/ESOP oracle. It is not a scalable coherent surrogate, "
            "not an end-to-end quantum-speedup result, and not fusion-physics validation."
        ),
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

        min_score = min(float(row["predictor_score"]) for row in predicted)
        min_diameter = min(int(row["patch_diameter"]) for row in predicted)
        for row in predicted:
            reasons = []
            if abs(float(row["predictor_score"]) - min_score) <= 1e-12:
                reasons.append("minimum_interaction_distance")
            if int(row["patch_diameter"]) == min_diameter:
                reasons.append("minimum_physical_diameter")
            row["screen_reason"] = "+".join(reasons) if reasons else "control_or_unscreened"

        selected = select_screen(
            predicted,
            args.control_patches,
            args.patch_seed + 17 * topology_index,
            args.exhaustive,
        )
        by_index = {int(row["patch_index"]): row for row in predicted}
        patch_by_index = {int(p["patch_index"]): p for p in patches}

        print(f"\n===== {topology_name} =====")
        print(
            f"candidate_patches={len(predicted)} selected={len(selected)} "
            f"compile_reduction={1-len(selected)/len(predicted):.2%} "
            f"min_score={min_score:.0f} min_diameter={min_diameter}"
        )

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
        args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("\n===== TCT SEMANTIC-FACTORED ROUTING SUMMARY =====")
    baseline_cz = int(probe_stats["native_cz"])
    baseline_depth = int(probe_stats["compiled_depth"])
    for topology_name in topologies:
        rows = [r for r in result["compile_rows"] if r.get("success") and r.get("topology") == topology_name]
        for mode in ("interaction_fixed", "qiskit_auto"):
            candidates = [r for r in rows if r.get("layout_mode") == mode]
            best = min(candidates, key=lambda r: (r["native_cz"], r["compiled_depth"])) if candidates else None
            if best is None:
                print(f"{topology_name} {mode}: no successful compile")
                continue
            print(
                f"{topology_name} {mode}: best_patch={best['patch_index']} "
                f"CZ={best['native_cz']} depth={best['compiled_depth']} "
                f"CZ_over_full={best['native_cz']/baseline_cz:.3f} "
                f"depth_over_full={best['compiled_depth']/baseline_depth:.3f}"
            )

    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
