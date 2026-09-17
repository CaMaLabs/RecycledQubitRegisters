#!/usr/bin/env python3
"""Corrected entry point for the cross-N recycled-register generalization audit.

The initial v1 file accidentally reversed the star-transposition order when
reimplementing the already-validated N=35 cycle factorization.  This wrapper
patches the v1 module to use the repository's validated forward-order convention
before running the audit.  All exhaustive full-register semantic checks remain
active, so any future factorization mismatch fails before compilation.
"""
from __future__ import annotations

from pathlib import Path

import ibm_recycled_cross_n_generalization_audit as base


def validated_star_transpositions(cycle: list[int], pivot_index: int) -> list[tuple[int, int]]:
    rotated = cycle[pivot_index:] + cycle[:pivot_index]
    pivot = rotated[0]
    transpositions = [(pivot, other) for other in rotated[1:]]

    expected = {cycle[i]: cycle[(i + 1) % len(cycle)] for i in range(len(cycle))}
    got = {x: base.apply_transpositions(x, transpositions) for x in cycle}
    if got != expected:
        raise AssertionError(
            f"star factorization mismatch for pivot {pivot}: got={got}, expected={expected}"
        )
    return transpositions


base.star_transpositions = validated_star_transpositions
base.REV = "2026-09-16-cross-n-generalization-v2-forward-star-fix"
base.OUT = Path("results/qubit_recycling/ibm_recycled_cross_n_generalization_v2.json")


if __name__ == "__main__":
    raise SystemExit(base.main())
