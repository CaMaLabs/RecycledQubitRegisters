#!/usr/bin/env python3
"""Exhaustive holdout validation for the v3 recycled interaction-graph mapper.

This wrapper keeps the v3 two-stage predictor/mapping algorithm unchanged but
forces the validation harness to compile every candidate patch.  It is intended
to measure true predictor recall@k and regret against the exhaustive patch set.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

from pathlib import Path

import ibm_recycled_interaction_graph_mapper as base
import ibm_recycled_interaction_graph_mapper_v3 as v3

REV = "2026-09-17-interaction-graph-placement-v3-exhaustive-holdout"
OUT = Path(
    "results/qubit_recycling/"
    "ibm_recycled_interaction_graph_mapper_v3_exhaustive_holdout.json"
)


def select_all_validation_indices(ranked, top_k: int, controls: int, seed: int):
    # ranked is already ordered by the v1 patch-ranking score.
    return [int(row["patch_index"]) for row in ranked]


# Importing v3 has already installed the v3 two-stage optimize_mapping function
# into the shared base module.  Patch only candidate selection here.
base.select_validation_indices = select_all_validation_indices
base.optimize_mapping = v3.optimize_mapping_v3
base.REV = REV
base.OUT = OUT


if __name__ == "__main__":
    raise SystemExit(base.main())
