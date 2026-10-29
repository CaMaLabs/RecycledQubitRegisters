#!/usr/bin/env python3
"""Public-only exact quadratic-residue Fermat midpoint pruning.

Reject x only if x*x-N fails a necessary quadratic-residue test modulo a
public small odd prime. No factors/order/oracle enter selection. Full setups
and modular work explicitly counted. CPU ONLY. Lead Chase Lunsford.
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, asdict
from functools import lru_cache

WHEELS={
    105: (3,5,7),
    15015: (3,5,7,11,13),
    255255: (3,5,7,11,13,17),
}


@lru_cache(maxsize=None)
def prime_quadratic_residues(prime):
    """Reusable lookup depends on public prime alone, not N."""
    if prime<3 or prime%2==0:
        raise ValueError("only odd prime moduli supported")
    return frozenset((v*v)%prime for v in range(prime))


@lru_cache(maxsize=8192)
def allowed_mask(prime, nmod):
    """One public N mod ell lookup, prepared once per N residue."""
    qr=prime_quadratic_residues(prime)
    return tuple((((x*x-nmod)%prime) in qr) for x in range(prime))


def ceil_sqrt(n):
    s=math.isqrt(n)
    return s+(s*s<n)


def valid_wheel(primes):
    ps=tuple(int(p) for p in primes)
    if len(ps)!=len(set(ps)) or not ps:
        raise ValueError("wheel primes must be unique and nonempty")
    for p in ps:
        if p<3 or p%2==0 or any(p%d==0 for d in range(3,math.isqrt(p)+1,2)):
            raise ValueError("modulus must be an odd prime")
    return ps


def fast_public_midpoint_factor(n, primes=(3,5,7,11,13), max_offset=4095,
                                max_square_tests=None):
    """All recorded costs include per-N mask setup and scanning every x.

    Coordinate budget x in [ceil(sqrt(N)),ceil(sqrt(N))+max_offset] is fixed
    identically for plain Fermat and each wheel; unlike a cap on square tests,
    it does not secretly permit arbitrary extra search distance.
    """
    if not isinstance(n,int) or n<9 or n%2==0:
        raise ValueError("odd N>=9 required")
    ps=valid_wheel(primes)
    if not 0<=max_offset<=1000000:
        raise ValueError("finite midpoint offset budget required")
    if max_square_tests is not None and max_square_tests<1:
        raise ValueError("square-test budget must be positive")
    begin=time.perf_counter()
    masks=tuple(allowed_mask(p,n%p) for p in ps)
    setup=time.perf_counter()-begin
    t0=time.perf_counter()
    x0=ceil_sqrt(n)
    limit=x0+max_offset
    probes=0
    mods=0
    squares=0
    factors=None
    candidate_end=None
    eliminated=0
    cap_hit=False
    for x in range(x0,limit+1):
        probes+=1
        matched=True
        for p,mask in zip(ps,masks):
            mods+=1
            if not mask[x%p]:
                matched=False
                eliminated+=1
                break
        if not matched:
            continue
        if max_square_tests is not None and squares>=max_square_tests:
            cap_hit=True
            break
        squares+=1
        v=x*x-n
        y=math.isqrt(v)
        if y*y==v:
            p,q=x-y,x+y
            if 1<p<=q and p*q==n:
                factors=[p,q]
                candidate_end=x
                break
    search=time.perf_counter()-t0
    return dict(N=n,method="public_QR_midpoint_sieve",modulus=math.prod(ps),
        primes=list(ps),max_midpoint_offset=max_offset,
        exact_square_test_cap=max_square_tests,
        factors=factors,found=bool(factors),
        stopped_due_to_square_test_cap=cap_hit,
        scanned_midpoint_positions=probes,
        modular_membership_checks=mods,
        midpoint_positions_rejected=eliminated,
        exact_square_root_tests=squares,
        found_at_offset=(candidate_end-x0 if factors else None),
        one_time_public_mask_setup_seconds=setup,
        scan_seconds=search,
        total_seconds=setup+search,
        no_private_prime_factors_or_order_used=True,
        skipped_candidate_proof="if x*x-N is a square, it is quadratic residue mod every tested prime")


def ordinary_fermat_window(n,max_offset=4095):
    t0=time.perf_counter()
    first=ceil_sqrt(n)
    for k in range(max_offset+1):
        x=first+k
        v=x*x-n
        y=math.isqrt(v)
        if y*y==v:
            p,q=x-y,x+y
            if 1<p<=q and p*q==n:
                t=time.perf_counter()-t0
                return dict(factors=[p,q],found=True,exact_square_root_tests=k+1,
                    scanned_midpoint_positions=k+1,found_at_offset=k,
                    total_seconds=t,max_midpoint_offset=max_offset)
    return dict(factors=None,found=False,exact_square_root_tests=max_offset+1,
        scanned_midpoint_positions=max_offset+1,found_at_offset=None,
        total_seconds=time.perf_counter()-t0,max_midpoint_offset=max_offset)
