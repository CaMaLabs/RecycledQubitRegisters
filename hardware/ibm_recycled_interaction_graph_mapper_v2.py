#!/usr/bin/env python3
"""Congestion-aware v2 entry point for the recycled interaction-graph mapper.

v1 showed that post-HLS weighted interaction distance is strongly predictive of
compiled CZ/depth, but it also produced many tied patch scores and did not beat
Qiskit's best automatic layout.  This v2 keeps the same zero-QPU validation
harness while replacing the mapping objective with a richer topology score:

  * weighted logical-pair shortest-path distance;
  * physical-degree matching for high-pressure logical qubits;
  * routing flexibility through all shortest paths;
  * expected physical-edge congestion and peak edge pressure.

For the current 8-qubit recycled circuit, the exact mapper first enumerates all
8! logical-to-physical permutations using the cheap distance objective, retains
a broad shortlist, and only then evaluates the richer congestion score.  This
keeps the predictor inexpensive compared with compiling every candidate patch.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict
from pathlib import Path

import ibm_recycled_interaction_graph_mapper as base

REV = "2026-09-17-interaction-graph-placement-v2-congestion-aware"
OUT = Path("results/qubit_recycling/ibm_recycled_interaction_graph_mapper_v2.json")

# Keep enough near-optimal distance mappings that the richer routing score can
# choose among tied and almost-tied embeddings without enumerating congestion
# features for every permutation.
EXACT_SHORTLIST = 512

# The terms below are intentionally modest corrections to weighted distance.
# They are fixed before the validation compile; compiled CZ/depth are not used
# to tune a patch after the fact.
DEGREE_WEIGHT = 0.15
CONGESTION_WEIGHT = 0.25
PEAK_WEIGHT = 0.10
FLEXIBILITY_WEIGHT = 0.05


def shortest_path_catalog(cm):
    """Return (distance matrix, all shortest paths for every physical pair)."""
    dist = base.all_pairs_shortest(cm)
    adj = base.adjacency(cm)
    n = cm.size()
    catalog = {}

    for s in range(n):
        for t in range(s + 1, n):
            paths = []

            def walk(u, path):
                if u == t:
                    paths.append(tuple(path))
                    return
                # Any shortest s->t path must reduce remaining distance by one
                # at every step.  Sorted neighbors keep the result deterministic.
                for v in sorted(adj[u]):
                    if v in path:
                        continue
                    if dist[v][t] == dist[u][t] - 1:
                        walk(v, path + [v])

            walk(s, [s])
            if not paths:
                raise RuntimeError(f"no shortest path catalogued for {s}->{t}")
            catalog[(s, t)] = paths
    return dist, catalog


def logical_weighted_degree(n, pair_items):
    degree = [0.0] * n
    for (a, b), w in pair_items:
        degree[a] += float(w)
        degree[b] += float(w)
    return degree


def rich_mapping_score(mapping, pair_items, dist, path_catalog, physical_degree, logical_degree):
    total_weight = float(sum(float(w) for _, w in pair_items))
    if total_weight <= 0:
        raise RuntimeError("interaction graph has no weight")

    distance_cost = base.mapping_score(mapping, pair_items, dist)

    max_physical_degree = max(physical_degree) if physical_degree else 1
    degree_penalty = 0.0
    for logical_q, physical_q in enumerate(mapping):
        pd = max(1, int(physical_degree[physical_q]))
        degree_penalty += logical_degree[logical_q] * (max_physical_degree / pd - 1.0)

    edge_load = defaultdict(float)
    flexibility_penalty = 0.0
    for (a, b), w in pair_items:
        p, q = int(mapping[a]), int(mapping[b])
        key = (p, q) if p < q else (q, p)
        paths = path_catalog[key]
        share = float(w) / len(paths)
        flexibility_penalty += float(w) / len(paths)
        # Spread demand over all equally short routing alternatives.  This is
        # not a router simulation; it is a static pressure estimate.
        for path in paths:
            for u, v in zip(path, path[1:]):
                edge = (u, v) if u < v else (v, u)
                edge_load[edge] += share

    congestion_penalty = sum(load * load for load in edge_load.values()) / total_weight
    peak_pressure = max(edge_load.values()) if edge_load else 0.0

    score = (
        distance_cost
        + DEGREE_WEIGHT * degree_penalty
        + CONGESTION_WEIGHT * congestion_penalty
        + PEAK_WEIGHT * peak_pressure
        + FLEXIBILITY_WEIGHT * flexibility_penalty
    )
    return float(score)


def exact_mapping_v2(n, pair_items, dist, path_catalog, physical_degree):
    """Exact distance enumeration followed by congestion-aware reranking."""
    logical_degree = logical_weighted_degree(n, pair_items)

    # Max-heap represented with negative scores.  The tuple mapping gives a
    # deterministic tie-breaker.  We intentionally retain many tied candidates.
    heap = []
    for perm in __import__("itertools").permutations(range(n)):
        dscore = base.mapping_score(perm, pair_items, dist)
        entry = (-float(dscore), tuple(perm))
        if len(heap) < EXACT_SHORTLIST:
            heapq.heappush(heap, entry)
        else:
            worst = -heap[0][0]
            if dscore < worst - 1e-12:
                heapq.heapreplace(heap, entry)
            elif abs(dscore - worst) <= 1e-12:
                # Prefer a deterministic lexicographically smaller mapping at
                # the shortlist boundary.
                if tuple(perm) < heap[0][1]:
                    heapq.heapreplace(heap, entry)

    candidates = [list(mapping) for _, mapping in heap]
    if not candidates:
        raise RuntimeError("distance shortlist is empty")

    best_map = None
    best_score = math.inf
    for mapping in candidates:
        score = rich_mapping_score(
            mapping, pair_items, dist, path_catalog, physical_degree, logical_degree
        )
        if score < best_score - 1e-12 or (
            abs(score - best_score) <= 1e-12
            and (best_map is None or tuple(mapping) < tuple(best_map))
        ):
            best_map = list(mapping)
            best_score = float(score)

    return best_map, best_score


def local_mapping_v2(n, pair_items, dist, path_catalog, physical_degree, restarts, seed):
    """Fallback for widths above exact_limit: v1 seed + rich-score swap search."""
    seed_map, _, _ = base.local_mapping(n, pair_items, dist, restarts, seed) + (None,) if False else (None, None, None)
    # Call the actual v1 helper without the tuple trick above; kept explicit for
    # readability and compatibility.
    initial, _ = base.local_mapping(n, pair_items, dist, restarts, seed)
    logical_degree = logical_weighted_degree(n, pair_items)
    cur = list(initial)
    cur_score = rich_mapping_score(cur, pair_items, dist, path_catalog, physical_degree, logical_degree)
    improved = True
    while improved:
        improved = False
        best_swap = None
        best_score = cur_score
        for i in range(n):
            for j in range(i + 1, n):
                trial = list(cur)
                trial[i], trial[j] = trial[j], trial[i]
                score = rich_mapping_score(
                    trial, pair_items, dist, path_catalog, physical_degree, logical_degree
                )
                if score < best_score - 1e-12:
                    best_score = score
                    best_swap = (i, j)
        if best_swap is not None:
            i, j = best_swap
            cur[i], cur[j] = cur[j], cur[i]
            cur_score = best_score
            improved = True
    return cur, float(cur_score)


def optimize_mapping_v2(cm, pair_weights, exact_limit: int, restarts: int, seed: int):
    n = cm.size()
    pair_items = sorted(pair_weights.items())
    dist, path_catalog = shortest_path_catalog(cm)
    physical_degree = [len(x) for x in base.adjacency(cm)]

    if n <= exact_limit:
        mapping, score = exact_mapping_v2(
            n, pair_items, dist, path_catalog, physical_degree
        )
        return mapping, score, "exact_distance_congestion_v2"

    mapping, score = local_mapping_v2(
        n, pair_items, dist, path_catalog, physical_degree, restarts, seed
    )
    return mapping, score, "swap_hill_climb_congestion_v2"


# Patch only the predictor; retain v1's circuit construction, semantic checks,
# patch ensemble, fixed-vs-auto validation, statistics, and zero-QPU boundary.
base.optimize_mapping = optimize_mapping_v2
base.REV = REV
base.OUT = OUT


if __name__ == "__main__":
    raise SystemExit(base.main())
