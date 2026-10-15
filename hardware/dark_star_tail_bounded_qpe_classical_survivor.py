#!/usr/bin/env python3
"""Public-survivor Dark Star cube: all-outcome QPE error BOUNDS + classical cascade.

Research lead / original program: Chase Lunsford (CaMaLabs). No QPU.
No factor/order oracle enters the PUBLIC N, base, classical ledger, policy,
valid-denominator set, or the CF/GCD acceptance predicate. Synthetic p,q/r
are used AFTER public selection solely for IDEAL eigenphase modeling.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

import numpy as np

import dark_star_ptp_shor_audit as ds
import dark_star_recycled_scalable_arithmetic_audit as model
import dark_star_public_selector_larger_holdout as selector
import dark_star_public_multichoice_survivor_holdout as multichoice
import dark_star_full_qpe_outcome_holdout as exact

REV="2026-10-14-tail-bounded-qpe-classical-survivor-v1"
SELECT_SALT="QRR-tailbound-n17n18-survivors-v1-20261014"
BASE_SALT="QRR-tailbound-n17n18-base-v1-20261014"
BASE_POOL=(2,3,5,7,11,13,17,19,23,29,31)
STAGES_START=4
STAGES_STEP=2
STAGE_SHOTS=4
W=32
EXACT_M_CAP=12
MAX_PUBLIC_SCAN=1500
SAMPLE_PER_CELL=2
ROOT=Path("results/dark_star_ptp")


def hashval(*a):
    return int.from_bytes(hashlib.sha256("|".join(map(str,a)).encode("utf8")).digest(),"big")


def previous_sample_ns():
    names=[
      "dark_star_scalable_resource_population_holdout.json",
      "dark_star_public_policy_classical_v2.json",
      *(f"dark_star_public_selector_n18_ell{e}.json" for e in (3,5,7)),
      *(f"dark_star_public_multichoice_{c}_{g}.json" for c in ("replication","holdout")
                                                 for g in ("trigger","control"))
    ]
    out=set()
    for name in names:
        p=ROOT/name
        o=json.loads(p.read_text())
        rows=o["rows"]
        assert rows and all("N" in x for x in rows)
        out.update(int(x["N"]) for x in rows)
    return out


def population(bits):
    low=1<<(bits-1)
    high=(1<<bits)-1
    primes=ds.sieve_primes(high)
    out=[]
    for i,p in enumerate(primes):
        if p<11:continue
        if p*p>high:break
        for q in primes[i+1:]:
            n=p*q
            if n>high:break
            if n>=low:out.append((int(n),int(p),int(q)))
    return out


def choose_public_base(n,bits,group):
    start=hashval(BASE_SALT,bits,group,n)%len(BASE_POOL)
    for t in range(len(BASE_POOL)):
        a=int(BASE_POOL[(start+t)%len(BASE_POOL)])
        if math.gcd(a,n)==1:return a
    raise AssertionError("no public base")


def screen_public_sample(bits,group,excluded):
    candidates=[(n,p,q) for n,p,q in population(bits)
       if n%3==(2 if group=="trigger" else 1) and n not in excluded]
    ordered=sorted(candidates,key=lambda t:(hashval(SELECT_SALT,bits,group,t[0]),t[0]))
    screened=[]
    selected=[]
    for n,p,q in ordered[:MAX_PUBLIC_SCAN]:
        a=choose_public_base(n,bits,group)
        pre=multichoice.classical_cascade(n,a)
        row=dict(N=n,base=a,screen_rank=len(screened)+1,public_B31_factored=bool(pre["found"]),
                 public_B31_source=pre["source"],classical_operation_counts=pre["counts"])
        screened.append(row)
        if not pre["found"]:
            selected.append((n,p,q,a,row["screen_rank"]))
            if len(selected)==SAMPLE_PER_CELL:break
    assert len(selected)==SAMPLE_PER_CELL,(bits,group,len(screened),len(selected))
    return screened,selected


def pollard_rho(n,iteration_cap=512):
    counts=dict(gcd_calls=0,modular_squares=0,iterations=0,attempts=0)
    for seed in (2,3):
        counts["attempts"]+=1
        x=y=seed%n
        for _ in range(iteration_cap):
            x=(x*x+1)%n
            y=(y*y+1)%n
            y=(y*y+1)%n
            counts["modular_squares"]+=3
            counts["gcd_calls"]+=1
            counts["iterations"]+=1
            d=math.gcd(abs(x-y),n)
            if 1<d<n:
                assert n%d==0
                return dict(found=True,public_factor=int(d),counts=counts)
            if d==n:break
    return dict(found=False,public_factor=None,counts=counts)


def cumulative_classical(n):
    # Fixed study policy: B31 already exhausted, followed sequentially by B47,
    # bounded rho Floyd seeds 2/3, complete prime trial division.
    p47=multichoice.pminusone(n,47)
    if p47["found"]:
        factor=p47["factor"]
        return dict(first_additional_source="Pollard_p1_B47",factor=factor,
            B47=p47,rho=None,full_prime_trial=None,classically_complete=True)
    rho=pollard_rho(n)
    if rho["found"]:
        return dict(first_additional_source="Pollard_rho_floyd",factor=rho["public_factor"],
            B47=p47,rho=rho,full_prime_trial=None,classically_complete=True)
    tested=0
    factor=None
    for prime in ds.sieve_primes(math.isqrt(n)):
        tested+=1
        if n%prime==0:
            factor=prime
            break
    assert factor is not None and 1<factor<n and n%factor==0
    return dict(first_additional_source="complete_prime_trial",factor=factor,
        B47=p47,rho=rho,full_prime_trial=dict(modulo_checks=tested,
        division_factor=int(factor)),classically_complete=True)


def public_factor_denominators(n,a):
    good=exact.factor_producing_denominators(n,a)
    assert all(1<d<=n and d%2==0 for d in good)
    return good


def public_success_y(n,a,m,y,good):
    return exact.cf_public_success_fast(int(y),1<<m,n,good)


def exact_stage(n,a,r,m,good):
    P,diag=exact.full_qpe_probabilities(r,m)
    Q=len(P)
    accept=np.fromiter((public_success_y(n,a,m,y,good) for y in range(Q)),
                       count=Q,dtype=np.bool_)
    lower=float(P[accept].sum())
    assert -1e-9<=lower<=1.+1e-9
    return dict(m=m,lower=max(0.,min(1.,lower)),upper=max(0.,min(1.,lower)),
        tail_mass=0.,nearest_included_probability=None,
        outcome_bins_examined=Q,phase_count=r,method="exact_full_FFT",
        fft_diagnostic=diag,public_CF_unique_bins_checked=Q)


def bounded_stage(n,a,r,m,good,width=W):
    Q=1<<m
    assert Q>2*width+1 and width>=1
    start=time.process_time()
    offsets=np.arange(-width,width+1,dtype=np.int64).reshape(1,-1)
    cache={}
    accepted_probability_sum=0.
    selected_mass_sum=0.
    nearest_accepted_sum=0.
    max_oversum=0.
    min_mass=1.
    evaluated=0
    for start_s in range(0,r,512):
        s=np.arange(start_s,min(r,start_s+512),dtype=np.int64).reshape(-1,1)
        y0=((2*s*Q+r)//(2*r)).astype(np.int64)
        yr=y0+offsets
        t=s*Q-r*yr
        tfloat=t.astype(np.float64)
        num=np.sin(np.pi*tfloat/r)
        den=Q*np.sin(np.pi*tfloat/(r*Q))
        with np.errstate(invalid="ignore",divide="ignore"):
            probs=np.where(t==0,1.,(num/den)**2)
        assert np.isfinite(probs).all()
        assert (probs>=0).all()
        per_s=probs.sum(axis=1)
        max_oversum=max(max_oversum,float(per_s.max())-1.)
        min_mass=min(min_mass,float(per_s.min()))
        assert np.all(per_s<=1.+1e-9),(n,a,r,m,max_oversum)
        selected_mass_sum+=float(per_s.sum())
        wrapped=np.remainder(yr,Q)
        unique,inverse=np.unique(wrapped.ravel(),return_inverse=True)
        mask_unique=np.empty(len(unique),dtype=bool)
        for i,y in enumerate(unique):
            iy=int(y)
            if iy not in cache:
                cache[iy]=public_success_y(n,a,m,iy,good)
            mask_unique[i]=cache[iy]
        mask=mask_unique[inverse].reshape(probs.shape)
        accepted_probability_sum+=float((probs*mask).sum())
        nearest_accepted_sum+=float((probs[:,width]*mask[:,width]).sum())
        evaluated+=probs.size
    total_selected=selected_mass_sum/r
    tail=max(0.,1.-total_selected)
    lo=max(0.,min(1.,accepted_probability_sum/r))
    hi=min(1.,lo+tail)
    if hi<lo and hi>lo-1e-9:hi=lo
    assert hi+1e-9>=lo
    assert total_selected<=1.+1e-9
    analytic_bound=1./(2*width-1)
    assert tail<=analytic_bound+1e-9,(m,tail,analytic_bound)
    assert lo+1e-9>=nearest_accepted_sum/r
    assert hi<=1.+1e-9
    return dict(m=m,lower=lo,upper=hi,tail_mass=tail,
        nearest_included_probability=float(nearest_accepted_sum/r),
        outcome_bins_examined=evaluated,phase_count=r,
        method=f"center_plus_minus_{width}_analytic_tail",
        publicly_checked_distinct_bins=len(cache),
        head_probability_mass=total_selected,
        universal_analytic_tail_bound=analytic_bound,
        maximum_single_phase_head_oversum=max_oversum,
        minimum_single_phase_head_mass=min_mass,
        total_CPU_seconds=round(time.process_time()-start,5))


def one_policy_cost(n,a,intervals,gate_cache,where):
    assert where in ("lower","upper")
    reach=1.
    ccx=0.
    round_count=0.
    for z in intervals:
        # Cost is monotone decreasing in the per-shot success probability.
        p=z["upper"] if where=="lower" else z["lower"]
        E=reach*model.expected_stage_shots(p,STAGE_SHOTS)
        gates=model.stage_arithmetic_count(n,a,z["m"],gate_cache)
        ccx+=E*gates.get("ccx",0)
        round_count+=E*z["m"]
        reach*=(1.-p)**STAGE_SHOTS
    return float(ccx),float(round_count)


def score_base(n,a,r,gate_cache):
    good=public_factor_denominators(n,a)
    intervals=[]
    for m in model.stage_schedule(n,STAGES_START,STAGES_STEP):
        z=exact_stage(n,a,r,m,good) if m<=EXACT_M_CAP else bounded_stage(n,a,r,m,good)
        intervals.append(z)
    Ls=[z["lower"] for z in intervals]
    Us=[z["upper"] for z in intervals]
    fail_lo=math.prod((1.-u)**STAGE_SHOTS for u in Us)
    fail_hi=math.prod((1.-l)**STAGE_SHOTS for l in Ls)
    s_lo=max(0.,1.-fail_hi)
    s_hi=min(1.,1.-fail_lo)
    C_lo,round_lo=one_policy_cost(n,a,intervals,gate_cache,"lower")
    C_hi,round_hi=one_policy_cost(n,a,intervals,gate_cache,"upper")
    assert C_lo<=C_hi+1e-6 and round_lo<=round_hi+1e-6
    assert s_lo<=s_hi+1e-9
    cost_s_lo=C_lo/s_hi if s_hi>0 else None
    cost_s_hi=C_hi/s_lo if s_lo>0 else None
    return dict(base=a,order_validation_only=r,
       success_probability_by_cap_interval=[s_lo,s_hi],
       expected_CCX_attempt_interval=[C_lo,C_hi],
       expected_phase_round_interval=[round_lo,round_hi],
       CCX_per_factor_success_interval=[cost_s_lo,cost_s_hi],
       high_precision_stage_max_tail=max(z["tail_mass"] for z in intervals),
       total_examined_bins=sum(z["outcome_bins_examined"] for z in intervals),
       all_stages=intervals,public_valid_factor_producing_denominators=len(good))


def classify_ratio(plain,cube):
    a=plain["CCX_per_factor_success_interval"]
    b=cube["CCX_per_factor_success_interval"]
    if None in a or None in b:
        return dict(classification="uncertain_or_no_factor_success",ratio_interval=[None,None])
    low=b[0]/a[1] if a[1]>0 else None
    high=b[1]/a[0] if a[0]>0 else None
    assert low is not None and high is not None
    assert low<=high+1e-9
    cls="certified_cube_win" if high<1 else ("certified_cube_loss" if low>1 else "inconclusive")
    return dict(classification=cls,ratio_interval=[low,high])


def numeric_selftests():
    assert exact.selftests()["passed"]
    # Validate analytic partial geometric distribution brackets against
    # independently enumerated *every* output y using FFT.
    comparisons=[]
    for n,a in ((35,2),(77,2),(143,2)):
        assert math.gcd(n,a)==1
        lam=math.lcm(*[p-1 for p in ds.prime_factors_distinct(n)])
        r=model.multiplicative_order_from_lambda(a,n,lam)
        good=public_factor_denominators(n,a)
        for m in (8,10,12):
            approx=bounded_stage(n,a,r,m,good,width=8)
            full=exact_stage(n,a,r,m,good)
            assert approx["lower"]-1e-9<=full["lower"]<=approx["upper"]+1e-9,(n,a,m,approx,full)
            assert approx["tail_mass"]<=1./15.+1e-9
            comparisons.append([n,a,m,full["lower"],approx["lower"],approx["upper"]])
    return dict(passed=True,exact_complete_FFT_against_geometric_direct=True,
       public_CF_matches_original_slow_verifier=True,
       independent_exact_probabilities_bracketed=len(comparisons),
       bracketed_samples=comparisons)


def run(bits,group):
    previous=previous_sample_ns()
    selected_before=True
    screen,selected=screen_public_sample(bits,group,previous)
    assert all(not z["public_B31_factored"] for z in screen if
         z["N"] in {v[0] for v in selected})
    selftest=numeric_selftests()
    data=dict(experiment="dark_star_tail_bounded_qpe_classical_survivor_v1",
       revision=REV,bits=bits,group=group,selected_public_N=[n for n,p,q,a,idx in selected],
       timestamp_utc=datetime.now(timezone.utc).isoformat(),zero_QPU=True,
       qpu_jobs_submitted=0,
       preregistration="docs/DARK_STAR_TAIL_BOUNDED_QPE_CLASSICAL_SURVIVOR_PREREG.md",
       public_hash_salts=dict(selection=SELECT_SALT,base=BASE_SALT),
       all_public_candidates_scanned=screen,
       selftests=selftest,rows=[],summary={},
       mathematical_tail_bound="Exact outcome head + omitted probability mass in ideal model; float evaluated with tolerance, not formally interval-arithmetic certified",
       claim_boundary="counterfactual IDEAL-QPE logical CCX on tiny public-classically-factorable n17/18 semiprimes; not hardware/physical/runtime/RSA factoring advantage")
    for i,(n,p,q,a,idx) in enumerate(selected,1):
        post=cumulative_classical(n)
        lam=math.lcm(p-1,q-1)
        r0=model.multiplicative_order_from_lambda(a,n,lam)
        b=pow(a,3,n)
        r1=model.multiplicative_order_from_lambda(b,n,lam)
        assert r1==r0//math.gcd(r0,3)
        gates={}
        t=time.process_time()
        x=score_base(n,a,r0,gates)
        y=score_base(n,b,r1,gates)
        cmp=classify_ratio(x,y)
        item=dict(N=n,bits=bits,group=group,rank_index=idx,
             base=a,cube_base=b,p_validation_only=p,q_validation_only=q,
             classical_after_B31=post,
             baseline_order_validation_only=r0,cube_order_validation_only=r1,
             order_identity_verified=True,
             conditional_ideal_QPE_even_though_classically_factored=True,
             plain=x,cube=y,cube_vs_plain=cmp,
             process_CPU_seconds=round(time.process_time()-t,5))
        data["rows"].append(item)
        print(f"[{i}/{len(selected)}] n={n} public_B31_survivor=True "
           f"classical_next={post['first_additional_source']} "
           f"order={r0}->{r1} "
           f"ratio=[{cmp['ratio_interval'][0]},{cmp['ratio_interval'][1]}] "
           f"class={cmp['classification']} "
           f"CPU={item['process_CPU_seconds']}s",flush=True)
    width=model.arithmetic_width(selected[0][0])
    data["logical_width"]=dict(arithmetic_workspace=width["arithmetic_qubits_excluding_phase"],
        wide_peak=width["arithmetic_qubits_excluding_phase"]+2*bits,
        recycled_peak=width["recycled_logical_qubits"])
    data["summary"]=dict(selected=len(selected),screened=len(screen),
         prefilter_B31_factored=sum(z["public_B31_factored"] for z in screen),
         classical_remaining_after_cumulative=sum(not row["classical_after_B31"]["classically_complete"] for row in data["rows"]),
         post_B31_sources=dict(Counter(row["classical_after_B31"]["first_additional_source"]
             for row in data["rows"])),
         classifications=dict(Counter(row["cube_vs_plain"]["classification"] for row in data["rows"])),
         model_only=True)
    assert len(data["rows"])==SAMPLE_PER_CELL
    assert data["summary"]["classical_remaining_after_cumulative"]==0
    return data


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bits",type=int,choices=(17,18),required=True)
    ap.add_argument("--group",choices=("trigger","control"),required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    print(f"starting frozen tail bound n{args.bits} {args.group} W={W}",flush=True)
    result=run(args.bits,args.group)
    out=args.out or ROOT/f"dark_star_tail_bounded_n{args.bits}_{args.group}.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("===== TAIL-BOUNDED QPE AND CUMULATIVE PUBLIC CLASSICAL =====",flush=True)
    print(f"bits={args.bits} group={args.group} "
      f"screened={result['summary']['screened']} "
      f"B31_classically_factored={result['summary']['prefilter_B31_factored']} "
      f"public_B31_survivors={result['summary']['selected']} "
      f"classical_remaining_after_cumulative=0 "
      f"certified_classifications={result['summary']['classifications']} "
      f"modeled_width={result['logical_width']}",flush=True)
    print(f"ZERO QPU JOBS. wrote {out}",flush=True)


if __name__=="__main__":
    main()
