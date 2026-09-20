#!/usr/bin/env python3
"""Route the validated six-round grid-factored TCT arithmetic oracle.

Zero-QPU sparse-topology compiler experiment for the 25-qubit coherent
objective-evaluation circuit. The harness requires the passing grid-factored
validation artifact, rebuilds the validated six-round circuit, extracts its
compiled interaction graph on a fully connected exact-width backend, screens
exact-width physical patches, and compiles selected patches on:

- authenticated IBM Fez heavy-hex connectivity; and
- the explicitly labeled 10x12 square-lattice proxy used by the existing
  Nighthawk/Phoenix topology studies.

The default candidate set is intentionally smaller than the 10-qubit semantic
routing audit because this 25-qubit circuit is substantially more expensive to
transpile. Results are "best among screened patches" unless --exhaustive is
used.

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

import benchmark_tct_event_polynomial_oracle as poly
import benchmark_tct_grid_factored_shift_6round as multi
import benchmark_tct_grid_factored_shift_oracle as grid
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-19-tct-grid-factored-shift-routing-v1"
DEFAULT_VALIDATION = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_oracle_validation.json"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_routing_6round.json"


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


def build_validated_circuit(spec: dict, validation: dict, rounds: int):
    if not validation.get("all_passed"):
        raise RuntimeError("validation artifact is missing all_passed=True")

    factors = grid.derive_grid_factors(spec)
    enc = grid.transformed_encoding(spec, factors)
    if not enc.get("classification_exact"):
        raise RuntimeError("grid-factored transformed encoding is not classification-exact")
    contract = grid.verify_classical_circuit_contract(spec, factors, enc)

    base_values = grid.base_event_truth_table(spec, factors, enc)
    coeff = poly.mobius_coefficients(base_values)
    poly.verify_polynomial(base_values, coeff)
    bias_table, false_table = grid.transformed_additive_tables(spec, factors, enc)

    qc = multi.build_multi_round(spec, enc, coeff, bias_table, false_table, rounds)
    return qc, {
        "classification_exact": True,
        "validation_all_passed": True,
        "parameter_bits": int(spec["parameter_register_bits"]["total_parameter_bits"]),
        "accumulator_bits": int(contract["nacc"]),
        "logical_width": int(qc.num_qubits),
        "marked_count": len(enc["marked_indices"]),
        "base_event_nonzero_monomials": sum(1 for c in coeff if c),
        "qscale": int(enc["qscale"]),
        "threshold_int": int(enc["threshold_int"]),
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
    ap.add_argument("--candidate-patches", type=int, default=12)
    ap.add_argument("--patch-seed", type=int, default=314159)
    ap.add_argument("--control-patches", type=int, default=2)
    ap.add_argument("--mapping-restarts", type=int, default=96)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--probe-optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--transpiler-seeds", default="8776,2026")
    ap.add_argument("--exhaustive", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.grover_rounds < 1 or args.candidate_patches < 1 or args.control_patches < 0:
        raise SystemExit("invalid arguments")
    seeds = [int(x.strip()) for x in args.transpiler_seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("at least one transpiler seed is required")

    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    qc, oracle_meta = build_validated_circuit(spec, validation, args.grover_rounds)
    logical = qc.num_qubits

    print("ZERO-QPU TCT GRID-FACTORED SHIFT ROUTING BENCHMARK")
    print(
        f"logical_width={logical} parameter_bits={oracle_meta['parameter_bits']} "
        f"accumulator_bits={oracle_meta['accumulator_bits']} grover_rounds={args.grover_rounds} "
        f"marked={oracle_meta['marked_count']} validation_all_passed=True classification_exact=True"
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

    print("\n===== FULLY CONNECTED VALIDATED BASELINE =====")
    print(
        f"CZ={probe_stats['native_cz']} depth={probe_stats['compiled_depth']} "
        f"size={probe_stats['compiled_size']} weighted_edges={interaction_meta['weighted_edge_count']} "
        f"total_2q_weight={interaction_meta['total_two_qubit_weight']:.0f}"
    )

    result = {
        "experiment": "tct_grid_factored_shift_routing_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "validation_artifact": str(args.validation),
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
            "Sparse-topology compiler benchmark of a validated classification-exact transformed arithmetic oracle. "
            "It is not fusion-physics validation, not fault-tolerant resource estimation, and not an end-to-end quantum-speedup result."
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

    print("\n===== TCT GRID-FACTORED SHIFT ROUTING SUMMARY =====")
    for topology_name in topologies:
        rows = [
            row for row in result["compile_rows"]
            if row.get("success") and row.get("topology") == topology_name
        ]
        for mode in ("interaction_fixed", "qiskit_auto"):
            subset = [r for r in rows if r.get("layout_mode") == mode]
            if not subset:
                print(f"{topology_name} {mode}: no successful compile")
                continue
            best = min(subset, key=lambda r: (r["native_cz"], r["compiled_depth"]))
            print(
                f"{topology_name} {mode}: best_patch={best['patch_index']} "
                f"CZ={best['native_cz']} depth={best['compiled_depth']} "
                f"CZ_over_full={best['native_cz']/probe_stats['native_cz']:.3f} "
                f"depth_over_full={best['compiled_depth']/probe_stats['compiled_depth']:.3f}"
            )
            result["topologies"][topology_name][f"best_{mode}"] = compact(best)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
