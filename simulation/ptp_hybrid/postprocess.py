#!/usr/bin/env python3
"""Standard vs PTP-aware Shor order postprocessing controls.

The initial PTP-aware path is intentionally conservative. It leaves Shor's
order mathematics unchanged and only validates any recovered nontrivial factor
against the generated modulo-210 factor-pair row. Until a proven pre-gcd filter
exists, :func:`ptp_order_candidate_allowed` accepts every order candidate.

This gives a clean falsification baseline: PTP annotation alone should not
magically improve factor recovery. Any future improvement must come from a new,
proved filter or reduced classical/quantum work and must preserve zero false
rejection on valid factorizations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

try:
    from .core import candidate_factor_pairs, root_for_integer, small_base_factor
except ImportError:
    from core import candidate_factor_pairs, root_for_integer, small_base_factor  # type: ignore


@dataclass
class PostprocessResult:
    mode: str
    n: int
    a: int
    order_candidate: int
    accepted_order_candidate: bool
    factors: tuple[int, int] | None
    modular_exponentiations: int
    gcd_operations: int
    ptp_pair_checks: int
    ptp_validated: bool | None
    rejection_reason: str | None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["factors"] = None if self.factors is None else list(self.factors)
        return d


def _ordered(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a <= b else (b, a)


def standard_from_order(n: int, a: int, r: int) -> PostprocessResult:
    """Exact Shor gcd recovery from a candidate order with explicit counters."""
    n, a, r = int(n), int(a), int(r)
    modexp = 0
    gcds = 0
    if r <= 1:
        return PostprocessResult("standard", n, a, r, False, None, modexp, gcds, 0, None, "order<=1")
    modexp += 1
    if pow(a, r, n) != 1:
        return PostprocessResult("standard", n, a, r, False, None, modexp, gcds, 0, None, "a^r mod N != 1")
    if r % 2:
        return PostprocessResult("standard", n, a, r, False, None, modexp, gcds, 0, None, "odd order")
    modexp += 1
    x = pow(a, r // 2, n)
    if x in (1, n - 1):
        return PostprocessResult("standard", n, a, r, True, None, modexp, gcds, 0, None, "trivial square root")
    found = None
    for value in (x - 1, x + 1):
        gcds += 1
        g = math.gcd(value, n)
        if 1 < g < n and n % g == 0:
            found = _ordered(g, n // g)
            break
    return PostprocessResult(
        "standard", n, a, r, True, found, modexp, gcds, 0, None,
        None if found else "no nontrivial gcd"
    )


def ptp_order_candidate_allowed(n: int, a: int, r: int) -> tuple[bool, str]:
    """Current proven-safe pre-gcd filter: accept all candidates.

    No residue-only theorem has yet been established that safely rejects an
    otherwise Shor-valid order candidate. This explicit no-op prevents hidden
    factor leakage and gives H3 a clean null baseline.
    """
    return True, "no proven residue-only order filter"


def _validate_factor_pair(n: int, factors: tuple[int, int]) -> tuple[bool, int]:
    p, q = factors
    if p * q != n:
        return False, 0
    if small_base_factor(n) is not None:
        return True, 1
    actual = _ordered(root_for_integer(p), root_for_integer(q))
    pairs = candidate_factor_pairs(n)
    checks = 0
    for pair in pairs:
        checks += 1
        if pair == actual:
            return True, checks
    return False, checks


def ptp_aware_from_order(n: int, a: int, r: int) -> PostprocessResult:
    """Run standard Shor recovery, then validate the exact factor-root pair."""
    allowed, reason = ptp_order_candidate_allowed(n, a, r)
    if not allowed:
        return PostprocessResult("ptp_aware", n, a, r, False, None, 0, 0, 0, None, reason)

    std = standard_from_order(n, a, r)
    if std.factors is None:
        return PostprocessResult(
            "ptp_aware", n, a, r, std.accepted_order_candidate, None,
            std.modular_exponentiations, std.gcd_operations, 0, None,
            std.rejection_reason,
        )

    valid, checks = _validate_factor_pair(n, std.factors)
    if not valid:
        # This path is treated as an invariant failure, not a useful filter.
        return PostprocessResult(
            "ptp_aware", n, a, r, std.accepted_order_candidate, None,
            std.modular_exponentiations, std.gcd_operations, checks, False,
            "PTP validation rejected an exact Shor factorization",
        )
    return PostprocessResult(
        "ptp_aware", n, a, r, std.accepted_order_candidate, std.factors,
        std.modular_exponentiations, std.gcd_operations, checks, True, None,
    )


def compare_order_candidate(n: int, a: int, r: int) -> dict:
    standard = standard_from_order(n, a, r)
    ptp = ptp_aware_from_order(n, a, r)
    false_rejection = standard.factors is not None and ptp.factors != standard.factors
    return {
        "standard": standard.to_dict(),
        "ptp_aware": ptp.to_dict(),
        "same_factors": standard.factors == ptp.factors,
        "false_rejection": false_rejection,
        "extra_ptp_pair_checks": ptp.ptp_pair_checks,
    }
