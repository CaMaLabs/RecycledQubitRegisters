#!/usr/bin/env python3
"""Exact all-bin ideal-QPE factor-producing outcome distribution vs nearest only.

Fully public deterministic choice and classical evaluation precede validation
factor/order generation. The phase-distribution model is analytically exact up
to floating roundoff via FFT of an averaged eigenphase autocorrelation.
NO QPU jobs. Lead/original questions: Chase Lunsford (CaMaLabs).
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
import dark_star_public_selector_larger_holdout as old
import dark_star_public_multichoice_survivor_holdout as prior

REV="2026-10-14-full-qpe-eigenphase-fft-v1"
SELECT_SALT="QRR-full-QPE-outcome-holdout-v1-20261014"
BASE_SALT="QRR-full-QPE-bases-v1-20261014"
N_MIN=512
N_MAX=1023
COUNT=3
COHORTS=("replication","locked_holdout")
GROUPS=("trigger","control")
STAGES=(4,6,8,10,12,14,16,18,20)
MAX_Q=1<<20
SHOTS=4
DEFAULT_DIR=Path("results/dark_star_ptp")


def hashed(salt,*values):
    return int.from_bytes(hashlib.sha256("|".join(str(s) for s in (salt,*values)).encode()).digest(),"big")


def enumerate_population():
    primes=ds.sieve_primes(N_MAX)
    result=[]
    for i,p in enumerate(primes):
        if p<11:continue
        if p*p>N_MAX:break
        for q in primes[i+1:]:
            n=p*q
            if n>N_MAX:break
            if n>=N_MIN:
                result.append((int(n),int(p),int(q)))
    return result


def selection(pop,cohort,group,exclude=None):
    banned=set(exclude or ())
    choices=[x for x in pop if
             x[0] not in banned and
             (x[0]%3!=1 if group=="trigger" else x[0]%3==1)
             and x[0]%3!=0]
    ranked=sorted(choices,key=lambda x:(hashed(SELECT_SALT,cohort,group,x[0]),x[0]))
    if len(ranked)<COUNT:raise ValueError(f"too few public N: {cohort} {group}")
    return ranked[:COUNT]


def public_base(n,cohort,group):
    start=hashed(BASE_SALT,cohort,group,n)%len(old.BASE_POOL)
    for j in range(len(old.BASE_POOL)):
        a=int(old.BASE_POOL[(start+j)%len(old.BASE_POOL)])
        if math.gcd(n,a)==1:return a
    raise AssertionError("No public coprime base")


def public_classical(n,a):
    """Frozen sequential GCD, bounded power2/GCD, B7 Pollard stage1."""
    assert math.gcd(a,n)==1
    gcd_calls=1
    modular_squares=0
    limit=2*n.bit_length()+2
    x=a%n
    factor=None
    source=None
    for step in range(limit+1):
        gm=old.nontrivial(math.gcd(x-1,n),n)
        gp=old.nontrivial(math.gcd(x+1,n),n)
        gcd_calls+=2
        if gm is not None or gp is not None:
            factor=gm if gm is not None else gp
            source="power2_chain"
            break
        if x==1:break
        x=(x*x)%n
        modular_squares+=1
    b7=None
    if factor is None:
        b7=prior.pminusone(n,7)
        gcd_calls+=b7["gcd_calls"]
        if b7["found"]:
            factor=b7["factor"]
            source="Pollard_p_minus_1_B7"
    if factor is not None:assert 1<factor<n and n%factor==0
    b31=prior.pminusone(n,31)
    b47=prior.pminusone(n,47)
    for receipt in (b31,b47):
        if receipt["found"]:assert 1<receipt["factor"]<n and n%receipt["factor"]==0
    return dict(found=factor is not None,public_factor=factor,
       first_source=source,gcd_calls=gcd_calls,
       modular_square_calls=modular_squares,
       B7_pollard_modular_pow_calls=(b7["modular_pow_calls"] if b7 is not None else 0),
       independent_B31_public_diagnostic=dict(found=b31["found"],
           modular_pow_calls=b31["modular_pow_calls"],proper_factor=b31["factor"]),
       independent_B47_public_diagnostic=dict(found=b47["found"],
           modular_pow_calls=b47["modular_pow_calls"],proper_factor=b47["factor"]))


def full_qpe_probabilities(r,m):
    """Analytical Fourier-lag identity for uniform order-r eigenphase mixture."""
    Q=1<<m
    assert 1<=r and Q<=MAX_Q
    k=np.arange(Q,dtype=np.int64)
    C=((Q-k)*(k%r==0)+k*((Q-k)%r==0)).astype(np.float64)/float(Q*Q)
    P=np.fft.fft(C).real
    normalization=float(P.sum())
    min_probability=float(P.min())
    assert abs(normalization-1.)<1e-9,(r,m,normalization)
    assert min_probability>=-1e-11,(r,m,min_probability)
    P=np.maximum(P,0.)
    # Do not silently renormalize any omitted probability: FFT is complete.
    assert abs(float(P.sum())-1.)<1e-9
    return P,dict(outcome_count=Q,probability_sum_before_clip=normalization,
       minimum_probability_before_clip=min_probability,
       max_probability=float(P.max()))


def factor_producing_denominators(n,base):
    """Public all-even-d candidate check; never uses validation order or p/q."""
    valid=set()
    for d in range(2,n+1,2):
        if pow(base,d,n)!=1:continue
        z=pow(base,d//2,n)
        if old.nontrivial(math.gcd(z-1,n),n) is not None or old.nontrivial(math.gcd(z+1,n),n) is not None:
            valid.add(d)
    return valid


def cf_public_success_fast(y,q,n,good):
    if y==0 or not good:return False
    # Recomputes ordinary continued fraction denominators of y/q via Euclid.
    a,b=int(y),int(q)
    den_preprev,den_prev=1,0
    while b:
        quot,rem=divmod(a,b)
        den=quot*den_prev+den_preprev
        if den in good:return True
        if den>n:break
        den_preprev,den_prev=den_prev,den
        a,b=b,rem
    return False


def full_stage_probability(n,base,r,m,valid_denoms):
    start=time.process_time()
    P,diagnostic=full_qpe_probabilities(r,m)
    fft_cpu=time.process_time()-start
    st=time.process_time()
    Q=len(P)
    mask=np.fromiter((cf_public_success_fast(y,Q,n,valid_denoms)
                      for y in range(Q)),count=Q,dtype=np.bool_)
    success=float(P[mask].sum())
    cpu=time.process_time()-st
    assert -1e-10<=success<=1+1e-10
    diagnostic.update(public_CF_accepting_outcome_bins=int(mask.sum()),
                      factor_producing_probability=min(1.,max(0.,success)),
                      FFT_CPU_seconds=round(fft_cpu,7),
                      public_CF_mask_CPU_seconds=round(cpu,7),
                      all_outcomes_evaluated=True)
    return min(1.,max(0.,success)),diagnostic


def scored_both_modes(n,base,r,modmul_cache):
    valid=factor_producing_denominators(n,base)
    assert all(d%2==0 and 1<d<=n for d in valid)
    stages=[]
    stage_probs={"full":[],"nearest":[]}
    for m in STAGES:
        exact,info=full_stage_probability(n,base,r,m,valid)
        nearest=old.true_factor_producing_probability(n,base,r,m,{})
        assert exact+2e-8>=nearest,(n,base,r,m,exact,nearest)
        stage_probs["full"].append(exact)
        stage_probs["nearest"].append(nearest)
        info.update(phase_bits=m,
            nearest_bin_only_factor_probability=nearest,
            exact_minus_nearest=exact-nearest)
        stages.append(info)
    summary={}
    for kind,ps in stage_probs.items():
        reach=1.
        total=Counter()
        expected_rounds=0.
        expected_shots=0.
        for m,p in zip(STAGES,ps):
            execution=reach*model.expected_stage_shots(p,SHOTS)
            gates=model.stage_arithmetic_count(n,base,m,modmul_cache)
            overhead=model.architecture_overhead("recycled",m)
            for gate,count in (gates+overhead).items():
                total[gate]+=execution*count
            expected_rounds+=execution*m
            expected_shots+=execution
            reach*=(1.-p)**SHOTS
        prob=max(0.,min(1.,1.-reach))
        ccx=float(total.get("ccx",0.))
        summary[kind]=dict(success_probability_by_cap=prob,
             expected_CCX_per_attempt=ccx,
             expected_phase_rounds=expected_rounds,
             expected_shots=expected_shots,
             expected_CCX_per_factor_success_with_restarts=(
                  ccx/prob if prob>0 else None),
             success_possible=prob>0)
    assert summary["full"]["success_probability_by_cap"]+2e-8>=summary["nearest"]["success_probability_by_cap"]
    return dict(valid_public_CF_denominators=len(valid),stages=stages,
                modes=summary)


def direct_probability(r,Q,y):
    z=np.arange(Q)
    out=0.
    for s in range(r):
        phased=np.exp(2j*np.pi*z*(s/r-y/Q))
        out+=float(abs(phased.sum()/Q)**2)/r
    return out


def selftests():
    for Q in (8,16,32):
        for r in (1,2,3,5,7,33):
            p,diag=full_qpe_probabilities(r,int(math.log2(Q)))
            direct=np.array([direct_probability(r,Q,y) for y in range(Q)])
            assert np.allclose(p,direct,atol=2e-12,rtol=0),(r,Q,np.max(abs(p-direct)))
            assert abs(diag["probability_sum_before_clip"]-1)<1e-12
    for n,a in ((15,2),(21,2),(35,2),(77,2)):
        if math.gcd(n,a)!=1:continue
        good=factor_producing_denominators(n,a)
        for m in (4,6,8):
            Q=1<<m
            for y in range(Q):
                f=cf_public_success_fast(y,Q,n,good)
                slow=old.explicit_cf_proper_factor(n,a,y,m,{})
                assert f==slow,(n,a,m,y,f,slow)
    return dict(passed=True,exact_FFT_matches_all_order_r_geometric_sums=True,
                complete_probability_mass=True,
                public_CF_fast_matches_original_oracle_free_factor_verifier=True)


def aggregate(rows,mode,chosen):
    relevant=[r for r in rows if not r["public_classical"]["found"]]
    compare=[]
    for r in relevant:
        x=r["bases"]["plain"]["modes"][mode]
        y=r["bases"]["cube"]["modes"][mode]
        p=x["expected_CCX_per_factor_success_with_restarts"]
        q=y["expected_CCX_per_factor_success_with_restarts"]
        if p is not None and q is not None:
            compare.append((p,q))
    wins=sum(q<p*(1.-1e-10) for p,q in compare)
    losses=sum(q>p*(1.+1e-10) for p,q in compare)
    ties=len(compare)-wins-losses
    ratio=sum(q for p,q in compare)/sum(p for p,q in compare) if compare else None
    return dict(
       eligible_unresolved=len(relevant),both_factor_success_positive=len(compare),
       either_success_zero=len(relevant)-len(compare),
       plain_success_positive=sum(r["bases"]["plain"]["modes"][mode]["success_possible"] for r in relevant),
       cube_success_positive=sum(r["bases"]["cube"]["modes"][mode]["success_possible"] for r in relevant),
       improved=wins,tied=ties,worsened=losses,
       ratio_sum_model_CCX_per_success_cube_over_plain=ratio,
       median_row_cost_ratio=(statistics.median(q/p for p,q in compare) if compare else None),
       success_coverage_preserved=(
          sum(r["bases"]["cube"]["modes"][mode]["success_possible"] for r in relevant)>=
          sum(r["bases"]["plain"]["modes"][mode]["success_possible"] for r in relevant)))


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--cohort",choices=COHORTS,required=True)
    args.add_argument("--group",choices=GROUPS,required=True)
    args.add_argument("--out",type=Path)
    opt=args.parse_args()
    tests=selftests()
    pop=enumerate_population()
    excluded=set()
    if opt.cohort=="locked_holdout":
        for g in GROUPS:
            excluded.update(n for n,p,q in selection(pop,"replication",g))
    chosen=selection(pop,opt.cohort,opt.group,excluded)
    result=dict(experiment="dark_star_full_qpe_outcome_holdout_v1",
      revision=REV,cohort=opt.cohort,group=opt.group,
      preregistration="docs/DARK_STAR_FULL_QPE_OUTCOME_HOLDOUT_PREREG.md",
      selection_salt=SELECT_SALT,base_salt=BASE_SALT,
      timestamp_utc=datetime.now(timezone.utc).isoformat(),
      zero_QPU=True,qpu_jobs_submitted=0,
      all_selected_included=True,
      ideal_model_only=True,no_privates_in_public_selector=True,
      selftests=tests,
      selected_public_N=[n for n,p,q in chosen],rows=[],summary={})
    for i,(n,p,q) in enumerate(chosen,1):
        base=public_base(n,opt.cohort,opt.group)
        public=public_classical(n,base)
        row=dict(N=n,cohort=opt.cohort,group=opt.group,
                 base=base,transformed_base=pow(base,3,n),
                 p_validation_only=p,q_validation_only=q,
                 public_classical=public,modeled_ideal_quantum=False,
                 odd_power_order_identity_verified=False,bases={})
        # Factor/order learned only after public base, choice and classical status.
        lam=math.lcm(p-1,q-1)
        r=model.multiplicative_order_from_lambda(base,n,lam)
        b=pow(base,3,n)
        r_cube=model.multiplicative_order_from_lambda(b,n,lam)
        assert r_cube==r//math.gcd(r,3)
        row.update(validation_plain_order=r,validation_cube_order=r_cube,
                   odd_power_order_identity_verified=True)
        if not public["found"]:
            cached={}
            row["bases"]["plain"]=scored_both_modes(n,base,r,cached)
            row["bases"]["cube"]=scored_both_modes(n,b,r_cube,cached)
            row["modeled_ideal_quantum"]=True
        result["rows"].append(row)
        print(f"[{i}/{COUNT}] {opt.cohort} {opt.group} N={n} "
              f"classical_B7={public['found']} B31={public['independent_B31_public_diagnostic']['found']} "
              f"order_validation={r}->{r_cube} full_outcomes_evaluated={row['modeled_ideal_quantum']}",flush=True)
    result["summary"]=dict(
       selected=len(chosen),
       classically_B7_factored=sum(r["public_classical"]["found"] for r in result["rows"]),
       classically_unresolved=sum(not r["public_classical"]["found"] for r in result["rows"]),
       B31_public_factor_found=sum(r["public_classical"]["independent_B31_public_diagnostic"]["found"] for r in result["rows"]),
       B47_public_factor_found=sum(r["public_classical"]["independent_B47_public_diagnostic"]["found"] for r in result["rows"]),
       B31_additional_from_B7_survivors=sum(
          (not r["public_classical"]["found"]) and
           r["public_classical"]["independent_B31_public_diagnostic"]["found"]
           for r in result["rows"]),
       B47_additional_from_B7_survivors=sum(
          (not r["public_classical"]["found"]) and
           r["public_classical"]["independent_B47_public_diagnostic"]["found"]
           for r in result["rows"]),
       full=aggregate(result["rows"],"full",chosen),
       nearest=aggregate(result["rows"],"nearest",chosen))
    width=model.arithmetic_width(chosen[0][0])
    result["logical_width"]=dict(arithmetic_workspace=width["arithmetic_qubits_excluding_phase"],
        wide_peak=width["arithmetic_qubits_excluding_phase"]+20,
        recycled_peak=width["recycled_logical_qubits"])
    result["claim_boundary"]="Exact all-bin IDEAL eigenphase mixture and strict public CF factoring on 10bit semiprimes; zero QPU; no hardware/physical/realtime or practical cryptanalytic advantage."
    assert len(result["rows"])==COUNT
    out=opt.out or (DEFAULT_DIR/f"dark_star_full_qpe_{opt.cohort}_{opt.group}.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("===== FULL IDEAL QPE OUTCOME HOLDOUT =====",flush=True)
    for mode in ("full","nearest"):
        s=result["summary"][mode]
        print(f"mode={mode} classically_unresolved={s['eligible_unresolved']} "
             f"joint_factor_success={s['both_factor_success_positive']} "
             f"improve/tie/worse={s['improved']}/{s['tied']}/{s['worsened']} "
             f"cube/plain CCX_per_success={s['ratio_sum_model_CCX_per_success_cube_over_plain']}",
             flush=True)
    print(f"B7_factored={result['summary']['classically_B7_factored']} "
          f"B31_extra={result['summary']['B31_additional_from_B7_survivors']} "
          f"B47_extra={result['summary']['B47_additional_from_B7_survivors']} "
          f"peak_width={result['logical_width']} ZERO QPU JOBS. wrote {out}",flush=True)


if __name__=="__main__":
    main()
