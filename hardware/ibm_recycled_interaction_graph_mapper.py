#!/usr/bin/env python3
"""Zero-QPU interaction-graph placement mapper for recycled QPE.

The placement audits showed that the narrow recycled circuit is much more
placement-sensitive than the wide circuit. This tool turns that observation into
an explicit compiler heuristic:

1. Build the exact N=35 recycled circuit.
2. Compile once on an exact-width fully connected synthetic backend so HLS is
   performed without routing.
3. Extract native two-qubit interactions as a weighted logical graph.
4. Sample many connected exact-width patches from Fez and Nighthawk/Phoenix
   connectivity.
5. Optimize the logical-to-physical permutation by minimizing weighted shortest
   path distance on each patch.
6. Compile only the top predicted patches plus controls and compare the fixed
   interaction-aware mapping against Qiskit's automatic layout.

No Sampler is instantiated and no QPU job is submitted. This remains an exact
small-N compiler/topology experiment, not scalable RSA modular arithmetic.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler import CouplingMap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

REV = "2026-09-17-interaction-graph-placement-v1"
OUT = Path("results/qubit_recycling/ibm_recycled_interaction_graph_mapper.json")


def logical_labels(scratch_bits: int) -> list[str]:
    return (["phase_recycled"]
            + [f"work[{i}]" for i in range(direct.WORK_BITS)]
            + [f"scratch[{i}]" for i in range(scratch_bits)])


def full_coupling(n: int) -> CouplingMap:
    return CouplingMap([[i, j] for i in range(n) for j in range(n) if i != j])


def compile_circuit(qc, backend, profile: str, level: int, seed: int, initial_layout=None):
    kwargs = {
        "backend": backend,
        "optimization_level": int(level),
        "seed_transpiler": int(seed),
        "qubits_initially_zero": True,
    }
    hls = direct.hls_for_profile(profile)
    if hls is not None:
        kwargs["hls_config"] = hls
    if initial_layout is not None:
        kwargs["initial_layout"] = list(initial_layout)
    pm = generate_preset_pass_manager(**kwargs)
    t0 = time.perf_counter()
    compiled = pm.run(qc)
    return compiled, time.perf_counter() - t0


def compiled_stats(qc, compiled, elapsed: float) -> dict:
    ops = {str(k): int(v) for k, v in compiled.count_ops().items()}
    touched, touched_indices = width.touched_qubits(compiled)
    return {
        "compiled_depth": int(compiled.depth()),
        "compiled_size": int(compiled.size()),
        "native_cz": int(ops.get("cz", 0)),
        "compiled_ops": ops,
        "compiled_touched_qubits": int(touched),
        "compiled_touched_qubit_indices": touched_indices,
        "compile_seconds": float(elapsed),
    }


def extract_two_qubit_interactions(compiled):
    pair_weights: dict[tuple[int, int], float] = {}
    op_counts: dict[str, int] = {}
    for item in compiled.data:
        if len(item.qubits) != 2:
            continue
        a = int(compiled.find_bit(item.qubits[0]).index)
        b = int(compiled.find_bit(item.qubits[1]).index)
        if a == b:
            continue
        key = tuple(sorted((a, b)))
        pair_weights[key] = pair_weights.get(key, 0.0) + 1.0
        name = str(item.operation.name)
        op_counts[name] = op_counts.get(name, 0) + 1
    if not pair_weights:
        raise RuntimeError("probe compilation produced no two-qubit interactions")
    weighted_degree = [0.0] * compiled.num_qubits
    for (a, b), w in pair_weights.items():
        weighted_degree[a] += w
        weighted_degree[b] += w
    return pair_weights, {
        "two_qubit_operation_counts": op_counts,
        "weighted_edge_count": len(pair_weights),
        "total_two_qubit_weight": float(sum(pair_weights.values())),
        "weighted_degree": weighted_degree,
    }


def adjacency(cm: CouplingMap) -> list[set[int]]:
    n = cm.size()
    out = [set() for _ in range(n)]
    for u, v in cm.get_edges():
        u, v = int(u), int(v)
        if u != v:
            out[u].add(v)
            out[v].add(u)
    return out


def all_pairs_shortest(cm: CouplingMap) -> list[list[int]]:
    adj = adjacency(cm)
    n = len(adj)
    inf = 10**9
    dist = [[inf] * n for _ in range(n)]
    for s in range(n):
        dist[s][s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[s][v] == inf:
                    dist[s][v] = dist[s][u] + 1
                    q.append(v)
    if any(dist[i][j] >= inf for i in range(n) for j in range(n)):
        raise RuntimeError("candidate subgraph is disconnected")
    return dist


def mapping_score(mapping, pair_items, dist) -> float:
    return float(sum(w * dist[mapping[a]][mapping[b]] for (a, b), w in pair_items))


def exact_mapping(n: int, pair_items, dist):
    best_map = None
    best_score = math.inf
    for perm in itertools.permutations(range(n)):
        score = mapping_score(perm, pair_items, dist)
        if score < best_score:
            best_score = score
            best_map = list(perm)
    if best_map is None:
        raise RuntimeError("exact mapping search returned no mapping")
    return best_map, float(best_score)


def local_mapping(n: int, pair_items, dist, restarts: int, seed: int):
    rng = random.Random(seed)
    logical_degree = [0.0] * n
    for (a, b), w in pair_items:
        logical_degree[a] += w
        logical_degree[b] += w
    physical_centrality = [sum(row) for row in dist]
    logical_order = sorted(range(n), key=lambda q: (-logical_degree[q], q))
    physical_order = sorted(range(n), key=lambda p: (physical_centrality[p], p))
    seed_map = [0] * n
    for q, p in zip(logical_order, physical_order):
        seed_map[q] = p

    starts = [seed_map]
    for _ in range(max(0, restarts - 1)):
        p = list(range(n))
        rng.shuffle(p)
        starts.append(p)

    best_map = None
    best_score = math.inf
    for start in starts:
        cur = list(start)
        cur_score = mapping_score(cur, pair_items, dist)
        improved = True
        while improved:
            improved = False
            best_swap = None
            best_swap_score = cur_score
            for i in range(n):
                for j in range(i + 1, n):
                    trial = list(cur)
                    trial[i], trial[j] = trial[j], trial[i]
                    s = mapping_score(trial, pair_items, dist)
                    if s < best_swap_score - 1e-12:
                        best_swap_score = s
                        best_swap = (i, j)
            if best_swap is not None:
                i, j = best_swap
                cur[i], cur[j] = cur[j], cur[i]
                cur_score = best_swap_score
                improved = True
        if cur_score < best_score:
            best_map, best_score = list(cur), cur_score
    if best_map is None:
        raise RuntimeError("local mapping search returned no mapping")
    return best_map, float(best_score)


def optimize_mapping(cm, pair_weights, exact_limit: int, restarts: int, seed: int):
    n = cm.size()
    pair_items = sorted(pair_weights.items())
    dist = all_pairs_shortest(cm)
    if n <= exact_limit:
        mapping, score = exact_mapping(n, pair_items, dist)
        return mapping, score, "exact_permutation"
    mapping, score = local_mapping(n, pair_items, dist, restarts, seed)
    return mapping, score, "swap_hill_climb"


def average_tied_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(order):
        end = pos + 1
        while end < len(order) and values[order[end]] == values[order[pos]]:
            end += 1
        avg = (pos + 1 + end) / 2.0
        for k in range(pos, end):
            ranks[order[k]] = avg
        pos = end
    return ranks


def pearson(x, y):
    if len(x) < 2 or len(y) != len(x):
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    dx, dy = [v - mx for v in x], [v - my for v in y]
    den = math.sqrt(sum(v*v for v in dx) * sum(v*v for v in dy))
    if den == 0:
        return None
    return float(sum(a*b for a, b in zip(dx, dy)) / den)


def spearman(x, y):
    return None if len(x) < 2 else pearson(average_tied_ranks(x), average_tied_ranks(y))


def select_validation_indices(ranked, top_k: int, controls: int, seed: int):
    top = [int(r["patch_index"]) for r in ranked[:top_k]]
    remaining = [int(r["patch_index"]) for r in ranked[top_k:]]
    chosen = list(top)
    if 0 not in chosen and 0 in remaining and controls > 0:
        chosen.append(0)
        remaining.remove(0)
        controls -= 1
    rng = random.Random(seed)
    if controls > 0 and remaining:
        chosen.extend(rng.sample(remaining, min(controls, len(remaining))))
    return list(dict.fromkeys(chosen))


def compact(row):
    if row is None:
        return None
    keys = ("topology", "patch_index", "patch_mode", "layout_mode",
            "predictor_rank", "predictor_score", "mapping_method",
            "initial_layout", "native_cz", "compiled_depth", "compiled_size",
            "compiled_touched_qubits", "seed_transpiler", "compile_seconds")
    return {k: row.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-QPU interaction-graph placement mapper")
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=32)
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0,1,2,3], default=3)
    ap.add_argument("--probe-optimization-level", type=int, choices=[0,1,2,3], default=1)
    ap.add_argument("--probe-seed", type=int, default=8776)
    ap.add_argument("--candidate-patches", type=int, default=48)
    ap.add_argument("--patch-seed", type=int, default=73177)
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--control-patches", type=int, default=6)
    ap.add_argument("--mapping-exact-limit", type=int, default=8)
    ap.add_argument("--mapping-restarts", type=int, default=64)
    ap.add_argument("--transpiler-seeds", default="2026")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if (args.phase_bits < 1 or args.scratch_bits < 0 or args.candidate_patches < 1
            or args.top_k < 1 or args.control_patches < 0 or args.mapping_restarts < 1):
        raise SystemExit("invalid arguments")
    seeds = [int(x.strip()) for x in args.transpiler_seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("at least one transpiler seed is required")

    qc, rounds, semantic = width.build("recycled", args.phase_bits,
                                       args.scratch_bits, use_measure2=False)
    if not semantic["pass"]:
        raise SystemExit("semantic validation failed")
    logical = int(qc.num_qubits)
    labels = logical_labels(args.scratch_bits)
    if len(labels) != logical:
        raise AssertionError("logical label count mismatch")

    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, logical, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    night_full, night_src = topo.nighthawk_map(service)

    probe_backend = topo.generic(logical, full_coupling(logical))
    probe_compiled, probe_elapsed = compile_circuit(
        qc, probe_backend, args.profile, args.probe_optimization_level,
        args.probe_seed, list(range(logical)))
    pair_weights, interaction_meta = extract_two_qubit_interactions(probe_compiled)
    probe_stats = compiled_stats(qc, probe_compiled, probe_elapsed)
    pair_rows = [{
        "logical_a": int(a), "logical_b": int(b),
        "label_a": labels[a], "label_b": labels[b], "weight": float(w)
    } for (a,b), w in sorted(pair_weights.items(), key=lambda item: (-item[1], item[0]))]

    print("ZERO-QPU INTERACTION-GRAPH MAPPER: no Sampler or QPU job is used.")
    print(f"N={direct.N} phase_bits={args.phase_bits} scratch={args.scratch_bits} "
          f"logical_width={logical} profile={args.profile}")
    print(f"probe native_CZ={probe_stats['native_cz']} "
          f"weighted_edges={interaction_meta['weighted_edge_count']} "
          f"total_2q_weight={interaction_meta['total_two_qubit_weight']:.0f}")
    if night_src.get("proxy"):
        print("IMPORTANT: Nighthawk side is a square-lattice PROXY, not exact Phoenix.")

    result = {
        "experiment": "ibm_recycled_interaction_graph_mapper_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "N": int(direct.N), "base": int(direct.A), "work_bits": int(direct.WORK_BITS),
        "phase_bits": int(args.phase_bits), "scratch_bits": int(args.scratch_bits),
        "logical_qubits": logical, "logical_labels": labels,
        "profile": args.profile, "optimization_level": int(args.optimization_level),
        "probe_optimization_level": int(args.probe_optimization_level),
        "probe_seed": int(args.probe_seed), "candidate_patches": int(args.candidate_patches),
        "top_k": int(args.top_k), "control_patches": int(args.control_patches),
        "mapping_exact_limit": int(args.mapping_exact_limit),
        "mapping_restarts": int(args.mapping_restarts), "transpiler_seeds": seeds,
        "nighthawk_source": night_src, "semantic_pass": bool(semantic["pass"]),
        "order_used_in_circuit_construction": False, "orbit_encoding_used": False,
        "interaction_probe": {**interaction_meta, **probe_stats, "pair_weights": pair_rows,
            "note": "Native 2Q interactions after HLS/basis translation on an exact-width fully connected target with identity layout."},
        "scope_boundary": "Topology/compiler predictor validation only; no calibration, QPU execution, fidelity claim, or scalable RSA arithmetic.",
        "patch_predictions": {}, "compile_rows": []
    }

    topologies = {"fez_heavy_hex_topology": fez_full,
                  "nighthawk_square_lattice_topology": night_full}

    for topo_index, (topology_name, full_cm) in enumerate(topologies.items()):
        patches = ens.patch_ensemble(full_cm, logical, args.candidate_patches,
                                     args.patch_seed + 1_000_003 * topo_index)
        predicted = []
        for patch in patches:
            subcm = cap.relabeled_subgraph(full_cm, patch["nodes"])
            mapping, score, method = optimize_mapping(
                subcm, pair_weights, args.mapping_exact_limit, args.mapping_restarts,
                args.patch_seed + 104729 * int(patch["patch_index"]) + topo_index)
            predicted.append({
                "patch_index": int(patch["patch_index"]), "patch_mode": patch["mode"],
                "patch_nodes": [int(x) for x in patch["nodes"]],
                "patch_undirected_edges": int(patch["stats"]["undirected_edges"]),
                "patch_mean_degree": float(patch["stats"]["degree_mean"]),
                "predictor_score": float(score), "mapping_method": method,
                "initial_layout": [int(x) for x in mapping]
            })
        predicted.sort(key=lambda r: (r["predictor_score"], -r["patch_undirected_edges"], r["patch_index"]))
        for rank, row in enumerate(predicted, start=1):
            row["predictor_rank"] = rank

        selected = select_validation_indices(predicted, min(args.top_k, len(predicted)),
                                             args.control_patches,
                                             args.patch_seed + 17 * topo_index)
        pred_by_idx = {r["patch_index"]: r for r in predicted}
        patch_by_idx = {int(p["patch_index"]): p for p in patches}

        print(f"\n===== {topology_name} =====")
        print(f"candidate_patches={len(predicted)} validation_patches={len(selected)} "
              f"compile_reduction={1 - len(selected)/len(predicted):.1%}")
        print("top predicted: " + ", ".join(
            f"p{r['patch_index']}={r['predictor_score']:.0f}" for r in predicted[:5]))
        result["patch_predictions"][topology_name] = {
            "ranked": predicted, "selected_validation_patch_indices": selected}

        for patch_index in selected:
            pred = pred_by_idx[patch_index]
            patch = patch_by_idx[patch_index]
            subcm = cap.relabeled_subgraph(full_cm, patch["nodes"])
            backend = topo.generic(logical, subcm)
            for layout_mode, layout in (("interaction_fixed", pred["initial_layout"]),
                                        ("qiskit_auto", None)):
                good = []
                for seed in seeds:
                    try:
                        compiled, elapsed = compile_circuit(qc, backend, args.profile,
                            args.optimization_level, seed, layout)
                        stat = compiled_stats(qc, compiled, elapsed)
                        touched = int(stat["compiled_touched_qubits"])
                        if touched > logical:
                            raise AssertionError(f"capacity lock violated: touched {touched}>{logical}")
                        good.append({
                            "success": True, "topology": topology_name,
                            "patch_index": int(patch_index), "patch_mode": pred["patch_mode"],
                            "patch_nodes": pred["patch_nodes"],
                            "patch_undirected_edges": pred["patch_undirected_edges"],
                            "patch_mean_degree": pred["patch_mean_degree"],
                            "predictor_rank": int(pred["predictor_rank"]),
                            "predictor_score": float(pred["predictor_score"]),
                            "mapping_method": pred["mapping_method"], "layout_mode": layout_mode,
                            "initial_layout": None if layout is None else [int(x) for x in layout],
                            "seed_transpiler": int(seed), **stat})
                    except Exception as exc:
                        result["compile_rows"].append({
                            "success": False, "topology": topology_name,
                            "patch_index": int(patch_index),
                            "predictor_rank": int(pred["predictor_rank"]),
                            "predictor_score": float(pred["predictor_score"]),
                            "layout_mode": layout_mode, "seed_transpiler": int(seed),
                            "error_type": type(exc).__name__, "error": str(exc)})
                if good:
                    best = min(good, key=lambda r: (r["native_cz"], r["compiled_depth"], r["seed_transpiler"]))
                    result["compile_rows"].append(best)
                    print(f"patch={patch_index:02d} rank={pred['predictor_rank']:02d} "
                          f"mode={layout_mode:17s} score={pred['predictor_score']:.0f} "
                          f"CZ={best['native_cz']} depth={best['compiled_depth']}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    summaries = {}
    for topology_name in topologies:
        fixed = [r for r in result["compile_rows"] if r.get("success")
                 and r["topology"] == topology_name and r["layout_mode"] == "interaction_fixed"]
        auto = [r for r in result["compile_rows"] if r.get("success")
                and r["topology"] == topology_name and r["layout_mode"] == "qiskit_auto"]
        fixed_by_patch = {int(r["patch_index"]): r for r in fixed}
        scores = [float(r["predictor_score"]) for r in fixed]
        czs = [float(r["native_cz"]) for r in fixed]
        depths = [float(r["compiled_depth"]) for r in fixed]
        ranked = result["patch_predictions"][topology_name]["ranked"]
        top1_fixed = fixed_by_patch.get(int(ranked[0]["patch_index"]))
        dense_fixed = fixed_by_patch.get(0)
        best_fixed = min(fixed, key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"])) if fixed else None
        best_auto = min(auto, key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"])) if auto else None
        summaries[topology_name] = {
            "validated_patch_count": len(fixed), "candidate_patch_count": len(ranked),
            "fraction_of_candidates_compiled": len(fixed)/len(ranked) if ranked else None,
            "predictor_spearman_vs_fixed_cz": spearman(scores, czs),
            "predictor_spearman_vs_fixed_depth": spearman(scores, depths),
            "predicted_top1_fixed": compact(top1_fixed),
            "best_validated_fixed": compact(best_fixed),
            "best_validated_auto": compact(best_auto),
            "dense_patch_fixed": compact(dense_fixed),
            "top1_is_best_validated_fixed_cz": bool(top1_fixed and best_fixed and top1_fixed["patch_index"] == best_fixed["patch_index"]),
            "top1_fixed_over_best_auto_cz_ratio": None if not top1_fixed or not best_auto or not best_auto["native_cz"] else float(top1_fixed["native_cz"] / best_auto["native_cz"]),
            "best_fixed_over_best_auto_cz_ratio": None if not best_fixed or not best_auto or not best_auto["native_cz"] else float(best_fixed["native_cz"] / best_auto["native_cz"]),
            "best_fixed_over_best_auto_depth_ratio": None if not best_fixed or not best_auto or not best_auto["compiled_depth"] else float(best_fixed["compiled_depth"] / best_auto["compiled_depth"])
        }

    result["summary"] = summaries
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    print("\n===== INTERACTION GRAPH =====")
    print(f"logical_width={logical} weighted_edges={interaction_meta['weighted_edge_count']} "
          f"total_2q_weight={interaction_meta['total_two_qubit_weight']:.0f}")
    for row in pair_rows[:10]:
        print(f"{row['label_a']} <-> {row['label_b']}: weight={row['weight']:.0f}")

    print("\n===== PREDICTOR VALIDATION SUMMARY =====")
    for topology_name, s in summaries.items():
        print(f"{topology_name}: compiled={s['validated_patch_count']}/{s['candidate_patch_count']} "
              f"spearman(score,CZ)={s['predictor_spearman_vs_fixed_cz']} "
              f"spearman(score,depth)={s['predictor_spearman_vs_fixed_depth']}")
        print(f"  predicted_top1={json.dumps(s['predicted_top1_fixed'], default=str)}")
        print(f"  best_fixed={json.dumps(s['best_validated_fixed'], default=str)}")
        print(f"  best_auto={json.dumps(s['best_validated_auto'], default=str)}")
        print(f"  best_fixed/best_auto CZ={s['best_fixed_over_best_auto_cz_ratio']} "
              f"depth={s['best_fixed_over_best_auto_depth_ratio']}")

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
