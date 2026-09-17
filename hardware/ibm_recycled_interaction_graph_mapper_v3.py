#!/usr/bin/env python3
"""Two-stage v3 interaction-graph mapper for recycled QPE.

v1 established that minimum weighted logical-interaction distance is a strong
predictor of patch quality, especially on Fez. v2 showed that richer topology
features (degree, routing flexibility and congestion) can improve the logical
permutation inside a good patch, but those richer terms degraded global patch
ranking.

This v3 cleanly separates those roles:

  1. PATCH RANKING uses the v1 minimum weighted-distance score.
  2. IN-PATCH MAPPING uses the v2 congestion-aware logical permutation.

The validation harness, exact-width capacity lock, HLS interaction probe, and
zero-QPU boundaries are inherited from v1.
"""
from __future__ import annotations

from pathlib import Path

import ibm_recycled_interaction_graph_mapper as base
import ibm_recycled_interaction_graph_mapper_v2 as v2

REV = "2026-09-17-interaction-graph-placement-v3-two-stage"
OUT = Path("results/qubit_recycling/ibm_recycled_interaction_graph_mapper_v3.json")


def optimize_mapping_v3(cm, pair_weights, exact_limit: int, restarts: int, seed: int):
    n = cm.size()
    pair_items = sorted(pair_weights.items())
    dist = base.all_pairs_shortest(cm)

    # Stage 1: compute the minimum v1 weighted-distance score. This score alone
    # is returned to the outer harness for global patch ranking.
    if n <= exact_limit:
        _, patch_score = base.exact_mapping(n, pair_items, dist)
    else:
        _, patch_score = base.local_mapping(n, pair_items, dist, restarts, seed)

    # Stage 2: independently select the logical permutation using v2's richer
    # congestion-aware objective. The patch's global rank is NOT changed by
    # this richer score.
    _, path_catalog = v2.shortest_path_catalog(cm)
    physical_degree = [len(x) for x in base.adjacency(cm)]

    if n <= exact_limit:
        mapping, rich_score = v2.exact_mapping_v2(
            n, pair_items, dist, path_catalog, physical_degree
        )
        method = "v1_distance_rank_v2_congestion_map_exact"
    else:
        mapping, rich_score = v2.local_mapping_v2(
            n, pair_items, dist, path_catalog, physical_degree, restarts, seed
        )
        method = "v1_distance_rank_v2_congestion_map_local"

    # Keep the outer predictor score as pure v1 distance so the validation
    # summary measures the patch-ranking hypothesis directly. Encode the rich
    # score into the method string only through the resulting mapping; the JSON
    # compile rows still preserve that mapping explicitly.
    _ = rich_score
    return mapping, float(patch_score), method


base.optimize_mapping = optimize_mapping_v3
base.REV = REV
base.OUT = OUT


if __name__ == "__main__":
    raise SystemExit(base.main())
