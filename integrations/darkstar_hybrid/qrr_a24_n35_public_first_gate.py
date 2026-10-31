#!/usr/bin/env python3
"""A24: public-only Dark Star first-stage truth gate for A23's N=35.

Stdlib only. No factor/order oracle, Qiskit, Quaspy, or QPU jobs.
A successful public classical split is recorded as CLASSICAL_FIRST, never as
quantum-assisted factoring. This guards against double-counting the A23 result.
"""
from __future__ import annotations

import json
import math
from collections import Counter

N35_BASES = (2, 8)
PUBLIC_WHEEL_PRIMES = (2, 3, 5, 7)


def public_preflight(n: int, base: int) -> dict:
    if n < 9 or n % 2 == 0:
        raise ValueError("Use odd composite candidate N>=9")
    if not 1 < base < n:
        raise ValueError("Require 1 < base < N")
    count = Counter()
    g = math.gcd(n, base)
    count["gcd_calls"] += 1
    if 1 < g < n:
        return dict(n=n, base=base, route="CLASSICAL_FIRST_GCD",
                    factors=[g, n // g], work=dict(count),
                    quantum_required=False, estimated_quantum_gain=None)
    for p in PUBLIC_WHEEL_PRIMES:
        count["small_prime_divisions"] += 1
        if n % p == 0 and p < n:
            return dict(n=n, base=base, route="CLASSICAL_FIRST_WHEEL",
                        factors=[p, n // p], work=dict(count),
                        quantum_required=False, estimated_quantum_gain=None)
    return dict(n=n, base=base, route="UNRESOLVED_PUBLIC_PREFLIGHT",
                factors=None, work=dict(count), quantum_required=None,
                estimated_quantum_gain=None)


def main() -> None:
    rows = [public_preflight(35, base) for base in N35_BASES]
    for row in rows:
        assert math.prod(row["factors"]) == row["n"] if row["factors"] else True
        assert row["route"] == "CLASSICAL_FIRST_WHEEL"
        assert row["factors"] == [5, 7]
        assert row["quantum_required"] is False
    print(json.dumps({
        "audit": "A24_PUBLIC_FIRST_N35",
        "status": "PASS_CLASSICAL_FIRST_GATE",
        "qpu_jobs": 0,
        "interpretation": "A23 ideal phase/recovery bridge is a valid component test, "
                          "but N=35 supplies no evidence of quantum factoring advantage "
                          "because public wheel preprocessing factors it first.",
        "rows": rows,
    }, indent=2))


if __name__ == "__main__":
    main()
