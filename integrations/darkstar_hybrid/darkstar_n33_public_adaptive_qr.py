#!/usr/bin/env python3
"""Public-N-only adaptive QR/Fermat/strong Brent router, frozen before N33 cases.

All costs include QR mask construction, pilot, failed QR, rho, fallback.
Research lead: Chase Lunsford / CaMaLabs. Zero QPU.
"""
from __future__ import annotations
from collections import Counter
import math
import time

from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from integrations.darkstar_hybrid import darkstar_public_cost_router as classic
from simulation.ptp_hybrid import kernel

POLICY="darkstar_public_adaptive_qr_33_v1_20261029"
METHODS=("A","B","F","Q","W","L","M")
PRIMES=qr.WHEELS[255255]
FERMAT_EARLY=8
PILOT_START=8
PILOT_LENGTH=64
EXTENDED_END_OFFSET=639
QUALIFYING_PILOT_MAX=2
QR_MAX_SQUARE_TESTS=64
BRENT_BUDGETS=((1,2,1024),(3,3,512))

def safe_pair(g,n):
    if 1<g<n and n%g==0:
        return [min(g,n//g),max(g,n//g)]
    return None

def scan_public_midpoints(n, x0, masks, start, stop_exclusive, max_squares, totals,
                          prior_squares=0):
    """Exact online square-residue filter, with real factor checks.

    Neither signature nor implementation sees p/q, stratum or true D.
    """
    if not 0<=start<=stop_exclusive<=640:raise ValueError("out of-range window")
    roots=0
    survivors=0
    checks=0
    positions=0
    result=None
    found_offset=None
    cap_hit=False
    for offset in range(start,stop_exclusive):
        x=x0+offset
        positions+=1
        valid=True
        for ell, mask in zip(PRIMES,masks):
            checks+=1
            if not mask[x%ell]:
                valid=False
                break
        if not valid:continue
        survivors+=1
        if prior_squares+roots>=max_squares:
            cap_hit=True
            break
        roots+=1
        v=x*x-n
        y=math.isqrt(v)
        if y*y==v:
            result=safe_pair(x-y,n)
            if result:
                found_offset=offset
                break
    totals["QR_midpoint_positions"]+=positions
    totals["QR_modular_membership_checks"]+=checks
    totals["QR_qualifying_positions"]+=survivors
    totals["QR_exact_square_tests"]+=roots
    return dict(factors=result,found_at_offset=found_offset,
                midpoint_positions=positions,modular_membership_checks=checks,
                qualifying_positions=survivors,
                exact_square_root_tests=roots,
                root_cap_hit=cap_hit,
                offset_start=start,offset_stop_exclusive=stop_exclusive)

def public_factor(n,method):
    """Factor or (M only) bounded-test one N. Never consult construction data."""
    if not isinstance(n,int) or n<9:raise ValueError("N>=9")
    if method not in METHODS:raise ValueError(method)
    t0=time.perf_counter()
    totals=Counter()
    stages=[]
    def finish(pair,which,complete):
        return dict(N=n,arm=method,factors=pair,successful_stage=which,
                    complete=complete,stages=stages,operations=dict(totals),
                    own_total_seconds=time.perf_counter()-t0,
                    public_N_only=True,has_private_factor_or_stratum_input=False,
                    QPU_jobs=0)
    if method=="W":
        z=kernel.wheel210_factor(n)
        totals["wheel_divisibility_tests"]+=z.divisibility_tests
        stages.append(dict(stage="wheel210",**z.to_dict()))
        return finish(list(z.factors) if z.factors else None,"wheel210",True)
    if method=="L":
        z=kernel.lfk_factor(n)
        totals["LFK_divisibility_tests"]+=z.divisibility_tests
        totals["LFK_steps"]+=z.integer_search_steps
        stages.append(dict(stage="LFK",**z.to_dict()))
        return finish(list(z.factors) if z.factors else None,"LFK",True)
    if method=="M":
        z=qr.ordinary_fermat_window(n,EXTENDED_END_OFFSET)
        totals["plain_sqrt_calls"]+=z["exact_square_root_tests"]
        stages.append(dict(stage="plain_fermat_640",**z))
        return finish(z["factors"],"plain_fermat_640" if z["factors"] else "unresolved",False)

    # A B F Q guaranteed complete for these synthetic semiprimes.
    for p in (2,3,5,7):
        totals["small_divisions"]+=1
        if n%p==0:
            f=safe_pair(p,n)
            stages.append(dict(stage="small_prime",p=p,factors=f))
            if f:return finish(f,"small_prime",True)

    x0=qr.ceil_sqrt(n)
    if method in ("A","F","Q"):
        z=classic.early_fermat(n,FERMAT_EARLY)
        totals["early_fermat_exact_square_tests"]+=z["exact_square_tests"]
        stages.append(dict(stage="plain_fermat_first_8",**z))
        if z["factors"]:
            return finish(z["factors"],"plain_fermat_first_8",True)

    if method in ("A","Q"):
        # Eliminate cross-case global lru_cache subsidies for N-dependent masks.
        qr.allowed_mask.cache_clear()
        setup=time.perf_counter()
        masks=tuple(qr.allowed_mask(p,n%p) for p in PRIMES)
        setup_sec=time.perf_counter()-setup
        totals["QR_mask_builds"]+=len(masks)
        stages.append(dict(stage="QR_public_mask_setup",
            primes=list(PRIMES),cost_seconds=setup_sec,
            no_pq_or_hidden_D=True))
        start=scan_public_midpoints(n,x0,masks,PILOT_START,
            PILOT_START+PILOT_LENGTH,QR_MAX_SQUARE_TESTS,totals)
        stages.append(dict(stage="public_QR_64_position_pilot",**start))
        if start["factors"]:
            return finish(start["factors"],"public_QR_64_position_pilot",True)

        choose_extend=(method=="Q" or
            (start["qualifying_positions"]<=QUALIFYING_PILOT_MAX and
             not start["root_cap_hit"]))
        stages.append(dict(stage="public_eligibility_decision",
            qualifying_pilot_positions=start["qualifying_positions"],
            pilot_positions=PILOT_LENGTH,
            max_eligible_for_extension=QUALIFYING_PILOT_MAX,
            extend=choose_extend,
            reason="fixed Q baseline" if method=="Q" else "public-only pilot QR density"))
        if choose_extend:
            more=scan_public_midpoints(n,x0,masks,
                PILOT_START+PILOT_LENGTH,EXTENDED_END_OFFSET+1,
                QR_MAX_SQUARE_TESTS,totals,
                prior_squares=start["exact_square_root_tests"])
            stages.append(dict(stage="extended_QR_midpoint_scan",**more))
            if more["factors"]:
                return finish(more["factors"],"extended_QR_midpoint_scan",True)

    # EXACT same rho budgets and wheel fallback for all completed methods.
    for c,seed,budget in BRENT_BUDGETS:
        z=classic.brent_attempt(n,c,seed,budget)
        for key,num in z["ops"].items():
            totals["rho_"+key]+=num
        assert z["ops"].get("modular_squarings",0)<=budget
        stages.append(dict(stage="strong_Brent",c=c,seed=seed,budget=budget,**z))
        if z["factors"]:
            return finish(z["factors"],"strong_Brent",True)
    w=kernel.wheel210_factor(n)
    totals["full_wheel_fallback_divisions"]+=w.divisibility_tests
    stages.append(dict(stage="full_wheel_fallback",**w.to_dict()))
    return finish(list(w.factors) if w.factors else None,"full_wheel_fallback",True)
