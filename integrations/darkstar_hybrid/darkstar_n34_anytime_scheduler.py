#!/usr/bin/env python3
"""Dark Star N34 true resumable Brent + chunked safe QR anytime scheduler.

Research lead: Chase Lunsford / CaMaLabs.
Only N and named arm enter algorithms. No factors, stratum, hidden order, QPU.
"""
from __future__ import annotations
from collections import Counter
import math
import time
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr
from integrations.darkstar_hybrid import darkstar_public_cost_router as classic
from simulation.ptp_hybrid import kernel

POLICY="darkstar_N34_anytime_Brent_PTP_v1_20261029"
METHODS=("A","B","F","Q","W","L","M")
BASE_PRIMES=(2,3,5,7)
BRENT_RUNS=((1,2,1024),(3,3,512))
BRENT_BLOCK=16
FERMAT_COUNT=8
QR_TOTAL_ROOT_CAP=64
QR_P=(3,5,7,11,13,17)
QR_SCHEDULE=((8,72),(72,200),(200,640))
BRENT_C1_CHECKPOINTS=(96,384,1024)


def pair(g,n):
    if 1<g<n and n%g==0:
        return [min(g,n//g),max(g,n//g)]
    return None


class BrentState:
    """Stateful deterministic batch-gcd Brent. Partial batches persist at pauses.

    Checkpoints never rerun a polynomial step. GCD checks at completed batches
    execute before returning, including when checkpoint precisely coincides
    with the batch's final square. At FINAL budget, check partial last batch
    and terminate without exceeding square budget.
    """
    def __init__(self,n,c,seed,budget,block=BRENT_BLOCK):
        if n<9 or budget<1 or block<1:
            raise ValueError("invalid public rho state")
        self.n,self.c,self.seed,self.budget,self.block=n,c,seed,budget,block
        self.y=seed%n
        self.r=1
        self.x=0
        self.k=0
        self.advance_left=0
        self.batch_left=0
        self.batch_take=0
        self.collision_left=0
        self.ys=0
        self.q=1
        self.phase="start"
        self.done=False
        self.factors=None
        self.ops=Counter()
        self.collision=False

    def _square(self,x):
        self.ops["modular_squarings"]+=1
        return (x*x+self.c)%self.n

    def run_until(self,target):
        """Advance to cumulative target squares; never reset, never exceed."""
        if not 0<=target<=self.budget:
            raise ValueError("checkpoint exceeds declared rho budget")
        start=Counter(self.ops)
        while not self.done:
            count=self.ops["modular_squarings"]
            if self.phase=="batch_gcd":
                self.ops["gcd_calls"]+=1
                g=math.gcd(self.q,self.n)
                if 1<g<self.n:
                    self.factors=pair(g,self.n)
                    self.done=True
                    self.phase="factor"
                    break
                if g==self.n:
                    self.ops["collision_blocks"]+=1
                    self.collision_left=self.batch_take
                    self.phase="collision"
                else:
                    self.k+=self.batch_take
                    self.phase="block_start"
                continue

            if count>=self.budget:
                # At the final hard budget, a partial product can be checked
                # once, but this may never spend more modular squarings.
                if self.phase=="block" and self.batch_take>self.batch_left:
                    self.phase="batch_gcd"
                    self.batch_take-=self.batch_left
                    self.batch_left=0
                    continue
                self.done=True
                self.phase="budget_exhausted"
                break
            if count>=target:
                break

            if self.phase=="start":
                self.x=self.y
                self.advance_left=self.r
                self.phase="advance"
            elif self.phase=="advance":
                self.y=self._square(self.y)
                self.advance_left-=1
                if self.advance_left==0:
                    self.k=0
                    self.phase="block_start"
            elif self.phase=="block_start":
                if self.k>=self.r:
                    self.r*=2
                    self.phase="start"
                else:
                    self.ys=self.y
                    self.q=1
                    self.batch_take=min(self.block,self.r-self.k)
                    self.batch_left=self.batch_take
                    self.phase="block"
            elif self.phase=="block":
                self.y=self._square(self.y)
                self.q=(self.q*abs(self.x-self.y))%self.n
                self.ops["modular_products"]+=1
                self.batch_left-=1
                if self.batch_left==0:
                    self.phase="batch_gcd"
            elif self.phase=="collision":
                if self.collision_left<=0:
                    self.done=True
                    self.collision=True
                    self.phase="collision_exhausted"
                    break
                self.ys=self._square(self.ys)
                self.ops["gcd_calls"]+=1
                self.collision_left-=1
                g=math.gcd(abs(self.x-self.ys),self.n)
                if 1<g<self.n:
                    self.factors=pair(g,self.n)
                    self.done=True
                    self.phase="factor"
                    break
            else:
                raise AssertionError("unexpected phase "+self.phase)
        delta=Counter(self.ops)-start
        return dict(c=self.c,seed=self.seed,target_squarings=target,
            cumulative_squarings=self.ops["modular_squarings"],
            operations_increment=dict(delta),
            cumulative_operations=dict(self.ops),
            phase=self.phase,completed=self.done,factors=self.factors,
            collision=self.collision)


def qr_scan(n,x0,masks,start,end,roots_before=0):
    if not (0<=start<end<=640):
        raise ValueError("public window outside frozen span")
    checks=survivors=roots=positions=0
    found=None
    offset_found=None
    root_cap=False
    for offset in range(start,end):
        if roots_before+roots>=QR_TOTAL_ROOT_CAP:
            root_cap=True
            break
        x=x0+offset
        positions+=1
        allowed=True
        for p,mask in zip(QR_P,masks):
            checks+=1
            if not mask[x%p]:
                allowed=False
                break
        if not allowed:
            continue
        survivors+=1
        roots+=1
        d=x*x-n
        y=math.isqrt(d)
        if y*y==d:
            found=pair(x-y,n)
            if found:
                offset_found=offset
                break
    return dict(start_offset=start,end_offset_exclusive=end,
        scanned_midpoint_positions=positions,modular_membership_checks=checks,
        qualified_midpoints=survivors,exact_square_root_tests=roots,
        root_cap_hit=root_cap,found_at_offset=offset_found,
        factors=found,public_congruence_necessary_condition=True)


def factor_public(n,method):
    """Fully charged factoring; inputs only public N and frozen method code."""
    if not isinstance(n,int) or n<9 or method not in METHODS:
        raise ValueError("public integer or method invalid")
    t0=time.perf_counter()
    stages=[]
    totals=Counter()

    def finish(factors,stage,complete):
        return dict(N=n,arm=method,factors=factors,successful_stage=stage,
            complete=complete,stages=stages,operation_counts=dict(totals),
            elapsed_seconds=time.perf_counter()-t0,
            only_public_N_used=True,no_factor_or_stratum_or_order_input=True,
            quantum_jobs=0)

    if method in ("W","L"):
        result=kernel.wheel210_factor(n) if method=="W" else kernel.lfk_factor(n)
        totals["divisibility_tests"]+=result.divisibility_tests
        totals["LFK_integer_search_steps"]+=result.integer_search_steps
        stages.append(dict(stage="full_"+method,**result.to_dict()))
        return finish(list(result.factors) if result.factors else None,"full_"+method,True)
    if method=="M":
        result=qr.ordinary_fermat_window(n,639)
        totals["plain_exact_square_root_tests"]+=result["exact_square_root_tests"]
        stages.append(dict(stage="bounded_plain_fermat",**result))
        return finish(result["factors"],
            "bounded_plain_fermat" if result["factors"] else "unresolved",False)

    for p in BASE_PRIMES:
        totals["base_divisibility_tests"]+=1
        if n%p==0:
            f=pair(p,n)
            if f:
                stages.append(dict(stage="small_base_prime",p=p,factors=f))
                return finish(f,"small_base_prime",True)

    if method in ("F","Q","A"):
        test=classic.early_fermat(n,FERMAT_COUNT)
        totals["early_plain_square_roots"]+=test["exact_square_tests"]
        stages.append(dict(stage="early_plain_fermat8",**test))
        if test["factors"]:
            return finish(test["factors"],"early_plain_fermat8",True)

    x0=qr.ceil_sqrt(n)
    masks=None
    roots_used=0

    def scan(first,end):
        nonlocal masks,roots_used
        if masks is None:
            # Charge per-N QR table setup on EVERY method call; do not let a
            # preceding interleaved arm subsidize N-specific mask creation.
            qr.allowed_mask.cache_clear()
            start=time.perf_counter()
            masks=tuple(qr.allowed_mask(p,n%p) for p in QR_P)
            elapsed=time.perf_counter()-start
            totals["QR_public_mask_tables"]+=len(QR_P)
            stages.append(dict(stage="QR_public_per_N_mask_setup",primes=list(QR_P),
                               elapsed_seconds=elapsed))
        step=qr_scan(n,x0,masks,first,end,roots_used)
        roots_used+=step["exact_square_root_tests"]
        totals["QR_modular_membership_checks"]+=step["modular_membership_checks"]
        totals["QR_midpoint_positions"]+=step["scanned_midpoint_positions"]
        totals["QR_exact_square_root_tests"]+=step["exact_square_root_tests"]
        stages.append(dict(stage="public_QR_segment",**step))
        assert roots_used<=QR_TOTAL_ROOT_CAP
        return step["factors"]

    rho1=BrentState(n,*BRENT_RUNS[0])

    def rho(cumulative):
        result=rho1.run_until(cumulative)
        for key,val in result["operations_increment"].items():
            totals["Brent_c1_"+key]+=val
        stages.append(dict(stage="public_resumed_Brent_c1",**result))
        assert totals["Brent_c1_modular_squarings"]<=1024
        return result["factors"]

    if method=="Q":
        f=scan(8,640)
        if f:return finish(f,"PTP_full_QR640",True)
        f=rho(1024)
        if f:return finish(f,"Brent_c1",True)
    elif method=="A":
        for budget,segment in zip(BRENT_C1_CHECKPOINTS,QR_SCHEDULE):
            f=rho(budget)
            if f:return finish(f,"resumed_Brent_c1",True)
            f=scan(*segment)
            if f:return finish(f,"anytime_QR_segment",True)
    else:
        f=rho(1024)
        if f:return finish(f,"Brent_c1",True)

    # One independent c3 restart, identical across ALL arms.
    rho3=BrentState(n,*BRENT_RUNS[1])
    r=rho3.run_until(512)
    for key,val in r["operations_increment"].items():
        totals["Brent_c3_"+key]+=val
    stages.append(dict(stage="public_Brent_c3",**r))
    assert totals["Brent_c1_modular_squarings"]+totals["Brent_c3_modular_squarings"]<=1536
    if r["factors"]:
        return finish(r["factors"],"Brent_c3",True)

    full=kernel.wheel210_factor(n)
    totals["full_wheel_fallback_divisions"]+=full.divisibility_tests
    stages.append(dict(stage="full_wheel_fallback",**full.to_dict()))
    return finish(list(full.factors) if full.factors else None,"full_wheel_fallback",True)
