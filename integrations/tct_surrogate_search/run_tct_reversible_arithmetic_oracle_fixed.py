#!/usr/bin/env python3
"""Compatibility runner for the TCT reversible arithmetic-oracle probe.

The current arithmetic-oracle benchmark expects the legacy interaction metadata
keys ``weighted_edges`` and ``total_2q_weight`` while the shared interaction
extractor returns ``weighted_edge_count`` and ``total_two_qubit_weight``.

This wrapper adds the two aliases without changing any circuit construction,
arithmetic, transpilation, or measured statistics, then delegates to the
original benchmark.  It is a zero-QPU compiler probe.
"""
from __future__ import annotations

import benchmark_tct_reversible_arithmetic_oracle as base


_original_extract = base.mapper.extract_two_qubit_interactions


def _extract_with_compat(compiled):
    pair_weights, meta = _original_extract(compiled)
    meta = dict(meta)
    meta.setdefault("weighted_edges", meta.get("weighted_edge_count", len(pair_weights)))
    meta.setdefault(
        "total_2q_weight",
        meta.get("total_two_qubit_weight", float(sum(pair_weights.values()))),
    )
    return pair_weights, meta


base.mapper.extract_two_qubit_interactions = _extract_with_compat


if __name__ == "__main__":
    raise SystemExit(base.main())
