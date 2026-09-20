#!/usr/bin/env python3
"""Zero-QPU calibration-weighted mapping experiment for the routed TCT oracle.

This benchmark takes the validated six-round 25-qubit grid-factored TCT
coherent-arithmetic circuit and the frozen exhaustive routing artifact.  It
selects a requested Fez patch (default: patch 9, the best patch in the first
live-calibration sweep), reads current ibm_fez CZ calibration metadata, and
compares four mapping strategies on the *same physical patch*:

1. qiskit_auto          - topology-only automatic layout/routing baseline;
2. topology_fixed       - the frozen interaction-distance initial mapping;
3. calibration_fixed    - initial mapping optimized on CZ error-risk paths;
4. hybrid_fixed         - initial mapping optimized on hop + normalized
                          CZ error-risk paths.

All fixed mappings optimize the same logical two-qubit interaction graph from
an exact-width fully-connected probe.  The calibration cost on an edge is

    risk = -log(1 - p_CZ)

and the hybrid edge cost is

    1 + risk / median_patch_risk.

The compiled circuits are still routed on a topology-only exact-width synthetic
backend; current Fez calibration metadata are used to choose the initial
mapping and to audit the resulting physical circuit.  This isolates whether a
calibration-aware initial placement materially improves exposure without
pretending the synthetic router itself is pulse- or noise-aware.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import heapq
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_grid_factored_shift_fez_calibration as cal
import benchmark_tct_grid_factored_shift_routing as routing
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-20-tct-fez-calibration-weighted-mapping-v1"
DEFAULT_VALIDATION = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_oracle_validation.json"
DEFAULT_ROUTING = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_routing_6round_exhaustive_seed314159.json"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_fez_calibration_weighted_mapping_patch9.json"


def weighted_all_pairs(n: int, adjacency: list[list[tuple[int, float]]]) -> list[list[float]]:
    out = [[math.inf] * n for _ in range(n)]
    for source in range(n):
        out[source][source] = 0.0
        pq = [(0.0, source)]
        while pq:
            d, u = heapq.heappop(pq)
            if d != out[source][u]:
                continue
            for v, w in adjacency[u]:
                nd = d + float(w)
                if nd < out[source][v] - 1e-15:
                    out[source][v] = nd
                    heapq.heappush(pq, (nd, v))
    if any(not math.isfinite(out[i][j]) for i in range(n) for j in range(n)):
        raise RuntimeError("weighted patch graph is disconnected")
    return out


def patch_calibration_distances(fez, patch_nodes: list[int], subcm) -> tuple[list[list[float]], list[list[float]], dict]:
    local_edges = sorted({tuple(sorted((int(u), int(v)))) for u, v in subcm.get_edges() if int(u) != int(v)})
    raw = []
    for a, b in local_edges:
        pa, pb = int(patch_nodes[a]), int(patch_nodes[b])
        prop, used, found = cal.target_instruction_properties(fez, "cz", (pa, pb))
        p = None if prop is None else getattr(prop, "error", None)
        if p is not None and math.isfinite(float(p)):
            p = min(max(float(p), 0.0), 1.0 - 1e-15)
        else:
            p = None
        raw.append({
            "local_edge": [a, b],
            "physical_edge": [pa, pb],
            "lookup_edge": None if used is None else list(used),
            "calibration_found": bool(found),
            "cz_error": p,
        })

    available = [float(r["cz_error"]) for r in raw if r["cz_error"] is not None]
    if not available:
        raise RuntimeError("no CZ calibration errors available on patch")
    median_p = statistics.median(available)
    fallback_p = min(max(median_p * 2.0, median_p + 1e-6), 0.5)

    risks = []
    for row in raw:
        p = fallback_p if row["cz_error"] is None else float(row["cz_error"])
        risk = -math.log1p(-p)
        row["effective_error"] = p
        row["risk"] = risk
        row["used_fallback"] = row["cz_error"] is None
        risks.append(risk)
    median_risk = max(statistics.median(risks), 1e-15)

    n = len(patch_nodes)
    risk_adj = [[] for _ in range(n)]
    hybrid_adj = [[] for _ in range(n)]
    for row in raw:
        a, b = row["local_edge"]
        risk_norm = float(row["risk"]) / median_risk
        # Pure calibration risk still gets a tiny positive floor so a zero-error
        # metadata value cannot create zero-cost cycles.
        rw = max(float(row["risk"]), 1e-12)
        hw = 1.0 + risk_norm
        risk_adj[a].append((b, rw)); risk_adj[b].append((a, rw))
        hybrid_adj[a].append((b, hw)); hybrid_adj[b].append((a, hw))

    return (
        weighted_all_pairs(n, risk_adj),
        weighted_all_pairs(n, hybrid_adj),
        {
            "edge_rows": raw,
            "available_fraction": len(available) / len(raw),
            "median_cz_error": median_p,
            "fallback_cz_error": fallback_p,
            "median_edge_risk": median_risk,
        },
    )


def predicted_patch(routing_json: dict, patch_index: int) -> dict:
    predicted = routing_json.get("topologies", {}).get("fez_heavy_hex_topology", {}).get("predicted", [])
    row = next((r for r in predicted if int(r["patch_index"]) == int(patch_index)), None)
    if row is None:
        raise RuntimeError(f"routing JSON has no Fez predicted patch {patch_index}")
    if not row.get("patch_nodes"):
        raise RuntimeError(f"routing JSON patch {patch_index} has no patch_nodes")
    return row


def summarize_candidate(compiled, stats: dict, fez, patch_nodes: list[int], strategy: str, seed: int) -> dict:
    op_rows = cal.op_calibration_rows(compiled, fez, patch_nodes)
    cz = cal.cz_edge_summary(op_rows)
    allerr = cal.error_summary(op_rows)
    timing = cal.critical_path_duration(compiled, op_rows)
    qprops = cal.qubit_properties(fez, patch_nodes)
    t1med = qprops.get("t1_s", {}).get("median")
    t2med = qprops.get("t2_s", {}).get("median")
    dur = float(timing["critical_path_duration_s"])
    return {
        "strategy": strategy,
        "seed_transpiler": int(seed),
        "native_cz": int(stats["native_cz"]),
        "compiled_depth": int(stats["compiled_depth"]),
        "compiled_size": int(stats["compiled_size"]),
        "compile_seconds": float(stats["compile_seconds"]),
        "cz_mean_error": cz.get("per_operation_error", {}).get("mean"),
        "cz_sum_p": cz.get("expected_error_events_sum_p"),
        "cz_log10_no_error_proxy": cz.get("log10_independent_no_error_proxy"),
        "all_gate_sum_p": allerr.get("all_gates", {}).get("expected_error_events_sum_p"),
        "critical_path_s": dur,
        "duration_over_median_t1": None if not t1med else dur / float(t1med),
        "duration_over_median_t2": None if not t2med else dur / float(t2med),
        "cz_calibration_coverage": cz.get("calibration_coverage_fraction"),
        "duration_coverage": timing.get("duration_calibration_coverage_fraction"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    ap.add_argument("--routing-json", type=Path, default=DEFAULT_ROUTING)
    ap.add_argument("--patch-index", type=int, default=9)
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--grover-rounds", type=int, default=6)
    ap.add_argument("--mapping-restarts", type=int, default=96)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--probe-optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--transpiler-seeds", default="8776,2026")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in args.transpiler_seeds.split(",") if x.strip()]
    if not seeds or args.mapping_restarts < 1:
        raise SystemExit("invalid arguments")

    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    routing_json = json.loads(args.routing_json.read_text(encoding="utf-8"))
    qc, oracle_meta = routing.build_validated_circuit(spec, validation, args.grover_rounds)
    logical = int(qc.num_qubits)

    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, logical, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))

    pred = predicted_patch(routing_json, args.patch_index)
    patch_nodes = [int(x) for x in pred["patch_nodes"]]
    subcm = cap.relabeled_subgraph(fez_full, patch_nodes)
    patch_backend = topo.generic(logical, subcm)

    # Logical interaction graph from the exact-width fully-connected probe.
    probe_backend = topo.generic(logical, mapper.full_coupling(logical))
    probe_compiled, _ = mapper.compile_circuit(
        qc, probe_backend, args.profile, args.probe_optimization_level, 8776, list(range(logical))
    )
    pair_weights, interaction_meta = mapper.extract_two_qubit_interactions(probe_compiled)
    pair_items = sorted(pair_weights.items())

    unit_dist = mapper.all_pairs_shortest(subcm)
    risk_dist, hybrid_dist, calibration_meta = patch_calibration_distances(fez, patch_nodes, subcm)

    topology_map, topology_score, topology_method = mapper.optimize_mapping(
        subcm,
        pair_weights,
        8,
        args.mapping_restarts,
        314159 + 104729 * args.patch_index,
    )
    calibration_map, calibration_score = mapper.local_mapping(
        logical, pair_items, risk_dist, args.mapping_restarts, 271828 + args.patch_index
    )
    hybrid_map, hybrid_score = mapper.local_mapping(
        logical, pair_items, hybrid_dist, args.mapping_restarts, 161803 + args.patch_index
    )

    strategies = {
        "qiskit_auto": None,
        "topology_fixed": topology_map,
        "calibration_fixed": calibration_map,
        "hybrid_fixed": hybrid_map,
    }

    result = {
        "experiment": "tct_fez_calibration_weighted_mapping_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": str(fez.name),
        "calibration_last_update": cal.calibration_timestamp(fez),
        "source_spec": str(args.spec),
        "validation_artifact": str(args.validation),
        "routing_artifact": str(args.routing_json),
        "patch_index": int(args.patch_index),
        "patch_nodes": patch_nodes,
        "oracle": oracle_meta,
        "logical_interaction": interaction_meta,
        "calibration_edges": calibration_meta,
        "mapping_scores": {
            "topology_fixed_unit_distance": float(topology_score),
            "calibration_fixed_risk_distance": float(calibration_score),
            "hybrid_fixed_distance": float(hybrid_score),
            "topology_mapping_method": topology_method,
        },
        "mappings": {k: None if v is None else [int(x) for x in v] for k, v in strategies.items()},
        "rows": [],
        "claim_boundary": (
            "Calibration-aware initial-placement and compiler feasibility experiment. "
            "Calibration-weighted error products are engineering proxies, not measured fidelity; "
            "the router itself remains topology-only. No QPU job is submitted."
        ),
    }

    print("ZERO-QPU TCT FEZ CALIBRATION-WEIGHTED MAPPING")
    print(
        f"backend={fez.name} calibration_last_update={result['calibration_last_update']} "
        f"patch={args.patch_index} logical_width={logical} rounds={args.grover_rounds}"
    )
    print(
        f"patch_edges_calibrated={calibration_meta['available_fraction']:.3%} "
        f"median_patch_CZ_error={calibration_meta['median_cz_error']:.6g}"
    )

    for strategy, initial_layout in strategies.items():
        candidates = []
        for seed in seeds:
            compiled, elapsed = mapper.compile_circuit(
                qc,
                patch_backend,
                args.profile,
                args.optimization_level,
                seed,
                initial_layout,
            )
            stats = mapper.compiled_stats(qc, compiled, elapsed)
            if int(stats["compiled_touched_qubits"]) > logical:
                raise AssertionError("exact-width capacity lock violated")
            row = summarize_candidate(compiled, stats, fez, patch_nodes, strategy, seed)
            candidates.append(row)
        # Calibration-weighted experiment chooses by actual audited CZ exposure,
        # not by CZ count. CZ/depth break ties deterministically.
        best = min(
            candidates,
            key=lambda r: (
                math.inf if r["cz_sum_p"] is None else float(r["cz_sum_p"]),
                int(r["native_cz"]),
                int(r["compiled_depth"]),
                int(r["seed_transpiler"]),
            ),
        )
        result["rows"].append(best)
        print(
            f"{strategy:18s} seed={best['seed_transpiler']} CZ={best['native_cz']} "
            f"depth={best['compiled_depth']} mean_CZ_error={best['cz_mean_error']:.6g} "
            f"sum_p_CZ={best['cz_sum_p']:.3f} log10_noerr={best['cz_log10_no_error_proxy']:.3f} "
            f"duration_ms={1000*best['critical_path_s']:.3f}"
        )

    best = min(
        result["rows"],
        key=lambda r: (
            math.inf if r["cz_sum_p"] is None else float(r["cz_sum_p"]),
            int(r["native_cz"]),
            int(r["compiled_depth"]),
        ),
    )
    auto = next(r for r in result["rows"] if r["strategy"] == "qiskit_auto")
    result["best_strategy"] = best["strategy"]
    result["best"] = best
    result["qiskit_auto"] = auto
    result["best_vs_auto"] = {
        "cz_ratio": float(best["native_cz"] / auto["native_cz"]),
        "depth_ratio": float(best["compiled_depth"] / auto["compiled_depth"]),
        "cz_sum_p_ratio": None if not auto["cz_sum_p"] else float(best["cz_sum_p"] / auto["cz_sum_p"]),
        "duration_ratio": None if not auto["critical_path_s"] else float(best["critical_path_s"] / auto["critical_path_s"]),
    }

    print("\n===== CALIBRATION-WEIGHTED MAPPING SUMMARY =====")
    print(
        f"best_strategy={best['strategy']} CZ={best['native_cz']} depth={best['compiled_depth']} "
        f"sum_p_CZ={best['cz_sum_p']:.3f} log10_noerr={best['cz_log10_no_error_proxy']:.3f}"
    )
    print(
        f"best_vs_auto: CZ_ratio={result['best_vs_auto']['cz_ratio']:.6f} "
        f"depth_ratio={result['best_vs_auto']['depth_ratio']:.6f} "
        f"sum_p_ratio={result['best_vs_auto']['cz_sum_p_ratio']:.6f} "
        f"duration_ratio={result['best_vs_auto']['duration_ratio']:.6f}"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=cal.jsonable) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
