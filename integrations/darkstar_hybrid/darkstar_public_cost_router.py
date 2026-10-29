#!/usr/bin/env python3
"""Fixed public-only cost-budget factoring router for Dark Star.

Classic-only 28-bit proof-of-function. No synthetic prime factors, orders, QPU
or hidden outcome fed to the router; every branch uses only public N.
Research lead Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import math
import time
from collections import Counter

from simulation.ptp_hybrid import kernel
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr

POLICY_ID="darkstar_public_router_v1_20261029"
RHO_SQUARING_BUDGETS=((1,2,256),(3,3,128))
RHO_BLOCK=16
EARLY_FERMAT_TESTS=8
QR_MAX_OFFSET=127
QR_MAX_SQUARE_TESTS=8

def factors_of(g,n):
    if 1<g<n and n%g==0:
        return [min(g,n//g),max(g,n//g)]
    return None

def early_fermat(n,count=EARLY_FERMAT_TESTS):
    x=qr.ceil_sqrt(n)
    for k in range(count):
        v=(x+k)**2-n
        y=math.isqrt(v)
        if y*y==v:
            f=factors_of(x+k-y,n)
            if f:
                return dict(factors=f,exact_square_tests=k+1,first_offset=k)
    return dict(factors=None,exact_square_tests=count,first_offset=None)

def brent_attempt(n,c,seed,budget,block=RHO_BLOCK):
    """Public deterministic Brent batch-gcd; tightly bound modular squarings."""
    y=seed%n
    r=1
    ops=Counter()
    while ops["modular_squarings"]<budget:
        x=y
        # Advance r polynomial steps; if budget ends, stop WITHOUT making
        # an assumption that no factor exists.
        for _ in range(r):
            if ops["modular_squarings"]>=budget:
                return dict(factors=None,ops=dict(ops),exhausted=True)
            y=(y*y+c)%n
            ops["modular_squarings"]+=1
        k=0
        while k<r:
            if ops["modular_squarings"]>=budget:
                return dict(factors=None,ops=dict(ops),exhausted=True)
            ys=y
            q=1
            take=min(block,r-k)
            for _ in range(take):
                if ops["modular_squarings"]>=budget:
                    break
                y=(y*y+c)%n
                ops["modular_squarings"]+=1
                q=(q*abs(x-y))%n
                ops["modular_products"]+=1
            ops["gcd_calls"]+=1
            g=math.gcd(q,n)
            if 1<g<n:
                return dict(factors=factors_of(g,n),ops=dict(ops),exhausted=False)
            if g==n:
                # Check individual items of the last batch, subject to the
                # SAME public modular-squaring budget.
                ops["collision_blocks"]+=1
                for _ in range(take):
                    if ops["modular_squarings"]>=budget:
                        break
                    ys=(ys*ys+c)%n
                    ops["modular_squarings"]+=1
                    ops["gcd_calls"]+=1
                    h=math.gcd(abs(x-ys),n)
                    if 1<h<n:
                        return dict(factors=factors_of(h,n),ops=dict(ops),exhausted=False)
                return dict(factors=None,ops=dict(ops),exhausted=False,collision=True)
            k+=take
        r*=2
    return dict(factors=None,ops=dict(ops),exhausted=True)

def public_router(n):
    """No prime factors, no secret multiplicative order, no success oracle."""
    if n<9:
        raise ValueError("N>=9 required")
    begin=time.perf_counter()
    stages=[]
    counts=Counter()

    def stop(name,found):
        return dict(policy=POLICY_ID,N=n,factors=found,
            method=name,success=bool(found),
            stages=stages,operation_totals=dict(counts),
            elapsed_seconds=time.perf_counter()-begin,
            order_or_factors_used_for_routing=False,
            uses_quantum_hardware=False,paid_runtime=False)

    # Wheel base-prime prefilter is necessary for non-coprime composites.
    for p in (2,3,5,7):
        counts["divisibility_tests"]+=1
        if n%p==0:
            f=factors_of(p,n)
            stages.append(dict(stage="public_wheel_small_prime",prime=p,factors=f))
            if f: return stop("public_wheel_small_prime",f)

    close=early_fermat(n)
    counts["exact_square_root_tests"]+=close["exact_square_tests"]
    stages.append(dict(stage="early_fermat_8",**close))
    if close["factors"]:
        return stop("early_fermat_8",close["factors"])

    # The two explicit polynomial/restart budgets are frozen before N28
    # selection, and the running total is at most 384 modular squarings.
    for c,seed,budget in RHO_SQUARING_BUDGETS:
        z=brent_attempt(n,c,seed,budget)
        for k,v in z["ops"].items():
            counts["rho_"+k]+=v
        stages.append(dict(stage="brent_public_rho",c=c,seed=seed,max_modular_squarings=budget,**z))
        if z["factors"]:
            return stop("brent_public_rho",z["factors"])

    # Public-only exploratory proximity trigger; no p/q/hidden order is read.
    first=qr.ceil_sqrt(n)
    x0_gap=first*first-n
    route_QR=(4*x0_gap<=first)
    stages.append(dict(stage="public_QR_route_decision",
        initial_square_gap=x0_gap,threshold="4*gap<=ceil_sqrt(N)",
        selected=route_QR,method_if_selected="M255255_128positions_8roots"))
    if route_QR:
        candidate=qr.fast_public_midpoint_factor(n,qr.WHEELS[255255],
            max_offset=QR_MAX_OFFSET,max_square_tests=QR_MAX_SQUARE_TESTS)
        counts["QR_modular_membership_checks"]+=candidate["modular_membership_checks"]
        counts["QR_exact_square_root_tests"]+=candidate["exact_square_root_tests"]
        counts["QR_scanned_midpoint_positions"]+=candidate["scanned_midpoint_positions"]
        stages.append(dict(stage="restored_QR_255255_bounded",**candidate))
        if candidate["factors"]:
            return stop("restored_QR_255255_bounded",candidate["factors"])

    # IMPORTANT full, separately priced classical guarantee for toy composites.
    full=kernel.wheel210_factor(n)
    counts["wheel210_fallback_divisibility_tests"]+=full.divisibility_tests
    stages.append(dict(stage="complete_wheel210_fallback",**full.to_dict()))
    return stop("complete_wheel210_fallback",
                list(full.factors) if full.factors else None)
