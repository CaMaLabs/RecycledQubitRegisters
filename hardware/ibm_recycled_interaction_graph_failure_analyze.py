#!/usr/bin/env python3
"""Diagnose structural failures of the v3 interaction-graph patch predictor.

This tool does NOT modify or retune the predictor. It analyzes an already
completed exhaustive result and compares:

  * the minimum predictor-score bucket;
  * the global-best fixed-layout patch;
  * the global-best Qiskit-auto patch.

For each patch it reconstructs the induced physical subgraph and reports graph
invariants plus static routing-pressure features under the frozen post-HLS
logical interaction graph.

No QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict, deque
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


def distances(adj):
    n = len(adj)
    out = []
    for s in range(n):
        d = [10**9] * n
        d[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if d[v] > d[u] + 1:
                    d[v] = d[u] + 1
                    q.append(v)
        out.append(d)
    return out


def articulation_points(adj):
    n = len(adj)
    disc = [-1] * n
    low = [-1] * n
    parent = [-1] * n
    ap = set()
    t = 0

    def dfs(u):
        nonlocal t
        disc[u] = low[u] = t
        t += 1
        children = 0
        for v in adj[u]:
            if disc[v] == -1:
                parent[v] = u
                children += 1
                dfs(v)
                low[u] = min(low[u], low[v])
                if parent[u] == -1 and children > 1:
                    ap.add(u)
                if parent[u] != -1 and low[v] >= disc[u]:
                    ap.add(u)
            elif v != parent[u]:
                low[u] = min(low[u], disc[v])

    for u in range(n):
        if disc[u] == -1:
            dfs(u)
    return sorted(ap)


def all_shortest_paths(adj, dist, s, t):
    paths = []

    def walk(u, path):
        if u == t:
            paths.append(tuple(path))
            return
        for v in sorted(adj[u]):
            if v in path:
                continue
            if dist[v][t] == dist[u][t] - 1:
                walk(v, path + [v])

    walk(s, [s])
    return paths


def graph_features(cm):
    adj = adjacency(cm)
    n = len(adj)
    deg = [len(x) for x in adj]
    e = sum(deg) // 2
    dist = distances(adj)
    pair_d = [dist[i][j] for i in range(n) for j in range(i + 1, n)]
    return {
        "nodes": n,
        "undirected_edges": e,
        "degree_sequence": sorted(deg, reverse=True),
        "degree_mean": statistics.fmean(deg),
        "degree_max": max(deg),
        "leaves": sum(d == 1 for d in deg),
        "cycle_rank": e - n + 1,
        "diameter": max(pair_d),
        "mean_pair_distance": statistics.fmean(pair_d),
        "articulation_points": articulation_points(adj),
        "articulation_count": len(articulation_points(adj)),
    }, adj, dist


def pair_weights(data):
    rows = data["interaction_probe"]["pair_weights"]
    return [
        ((int(r["logical_a"]), int(r["logical_b"])), float(r["weight"]))
        for r in rows
    ]


def routing_features(cm, logical_pairs, mapping):
    features, adj, dist = graph_features(cm)
    total_w = sum(w for _, w in logical_pairs)
    edge_load = defaultdict(float)
    route_choices = []
    weighted_distance = 0.0

    for (a, b), w in logical_pairs:
        p, q = int(mapping[a]), int(mapping[b])
        weighted_distance += w * dist[p][q]
        paths = all_shortest_paths(adj, dist, p, q)
        route_choices.append((w, len(paths)))
        share = w / len(paths)
        for path in paths:
            for u, v in zip(path, path[1:]):
                edge = (u, v) if u < v else (v, u)
                edge_load[edge] += share

    loads = list(edge_load.values())
    features.update({
        "weighted_distance": weighted_distance,
        "weighted_mean_shortest_path_multiplicity": (
            sum(w * c for w, c in route_choices) / total_w
        ),
        "weighted_inverse_path_multiplicity": (
            sum(w / c for w, c in route_choices) / total_w
        ),
        "edge_load_mean": statistics.fmean(loads) if loads else 0.0,
        "edge_load_max": max(loads) if loads else 0.0,
        "edge_load_l2_per_weight": (
            math.sqrt(sum(x*x for x in loads)) / total_w if loads else 0.0
        ),
        "edge_load_cv": (
            statistics.pstdev(loads) / statistics.fmean(loads)
            if len(loads) > 1 and statistics.fmean(loads) else 0.0
        ),
    })
    return features


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result", type=Path)
    ap.add_argument(
        "--topology",
        default="nighthawk_square_lattice_topology",
        choices=["fez_heavy_hex_topology", "nighthawk_square_lattice_topology"],
    )
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    data = json.loads(args.result.read_text())
    predictions = data["patch_predictions"][args.topology]["ranked"]
    pred_by_patch = {int(r["patch_index"]): r for r in predictions}
    rows = [
        r for r in data["compile_rows"]
        if r.get("success") and r.get("topology") == args.topology
    ]
    fixed = [r for r in rows if r.get("layout_mode") == "interaction_fixed"]
    auto = [r for r in rows if r.get("layout_mode") == "qiskit_auto"]

    best_fixed = min(
        fixed, key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"])
    )
    best_auto = min(
        auto, key=lambda r: (r["native_cz"], r["compiled_depth"], r["patch_index"])
    )
    min_score = min(float(r["predictor_score"]) for r in predictions)
    min_bucket = [
        int(r["patch_index"]) for r in predictions
        if abs(float(r["predictor_score"]) - min_score) <= 1e-12
    ]

    service = width.ref.ibm_base.make_service()
    if args.topology == "fez_heavy_hex_topology":
        fez = width.ref.ibm_base.select_backend(service, int(data["logical_qubits"]), "ibm_fez")
        full_cm = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    else:
        full_cm, _ = topo.nighthawk_map(service)

    logical_pairs = pair_weights(data)

    selected = sorted(set(min_bucket + [
        int(best_fixed["patch_index"]), int(best_auto["patch_index"])
    ]))
    out = {
        "source_result": str(args.result),
        "topology": args.topology,
        "minimum_predictor_score": min_score,
        "minimum_score_bucket": min_bucket,
        "best_fixed_patch": int(best_fixed["patch_index"]),
        "best_auto_patch": int(best_auto["patch_index"]),
        "patches": {},
    }

    fixed_by_patch = {int(r["patch_index"]): r for r in fixed}
    auto_by_patch = {int(r["patch_index"]): r for r in auto}

    for patch_index in selected:
        pred = pred_by_patch[patch_index]
        nodes = [int(x) for x in pred["patch_nodes"]]
        subcm = cap.relabeled_subgraph(full_cm, nodes)
        fixed_row = fixed_by_patch.get(patch_index)
        auto_row = auto_by_patch.get(patch_index)
        mapping = pred["initial_layout"]
        feats = routing_features(subcm, logical_pairs, mapping)
        out["patches"][str(patch_index)] = {
            "predictor_rank": int(pred["predictor_rank"]),
            "predictor_score": float(pred["predictor_score"]),
            "in_minimum_score_bucket": patch_index in min_bucket,
            "patch_nodes": nodes,
            "fixed_native_cz": None if fixed_row is None else int(fixed_row["native_cz"]),
            "fixed_depth": None if fixed_row is None else int(fixed_row["compiled_depth"]),
            "auto_native_cz": None if auto_row is None else int(auto_row["native_cz"]),
            "auto_depth": None if auto_row is None else int(auto_row["compiled_depth"]),
            "fixed_mapping": mapping,
            "features": feats,
        }

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(out, indent=2) + "\n")

    print("===== FAILURE STRUCTURE SUMMARY =====")
    print(f"topology={args.topology}")
    print(f"minimum_score={min_score} bucket={min_bucket}")
    print(
        f"best_fixed=p{best_fixed['patch_index']} rank={best_fixed['predictor_rank']} "
        f"score={best_fixed['predictor_score']} CZ={best_fixed['native_cz']} "
        f"depth={best_fixed['compiled_depth']}"
    )
    print(
        f"best_auto=p{best_auto['patch_index']} rank={best_auto['predictor_rank']} "
        f"score={best_auto['predictor_score']} CZ={best_auto['native_cz']} "
        f"depth={best_auto['compiled_depth']}"
    )

    for patch_index in selected:
        p = out["patches"][str(patch_index)]
        f = p["features"]
        print(
            f"p{patch_index:02d} rank={p['predictor_rank']:02d} "
            f"minbucket={p['in_minimum_score_bucket']} score={p['predictor_score']:.0f} "
            f"fixedCZ={p['fixed_native_cz']} autoCZ={p['auto_native_cz']} | "
            f"edges={f['undirected_edges']} cycle_rank={f['cycle_rank']} "
            f"diam={f['diameter']} meanD={f['mean_pair_distance']:.3f} "
            f"artic={f['articulation_count']} maxdeg={f['degree_max']} "
            f"pathmult={f['weighted_mean_shortest_path_multiplicity']:.3f} "
            f"loadCV={f['edge_load_cv']:.3f} loadMax={f['edge_load_max']:.1f}"
        )

    if args.json_out is not None:
        print(f"wrote {args.json_out}")
    print("NO QPU JOB SUBMITTED.")


if __name__ == "__main__":
    main()
