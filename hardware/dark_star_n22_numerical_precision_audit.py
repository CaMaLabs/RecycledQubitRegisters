#!/usr/bin/env python3
"""Frozen-sample N22 QPE precision-only audit: 131072 eigenphases + empirical Bernstein.

NOT a new independent population or hardware result. Reuses exact immutable
N/base selection and the original strict public CF/GCD, stage arithmetic and
classical factoring rules; compares uncertainty WIDTH, not cherry-picked wins.
Research lead: Chase Lunsford / CaMaLabs. ZERO QPU.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import random
import time
from pathlib import Path

import numpy as np
from numba import njit

import dark_star_full_qpe_outcome_holdout as exact
import dark_star_n22_full_tail_qpe_holdout as old
import dark_star_n22_full_tail_public_manifest as frozen
import dark_star_n22_selector_vs_cube as n22classical
import dark_star_recycled_scalable_arithmetic_audit as model

ROOT=Path("results/dark_star_ptp")
MANIFEST=ROOT/"dark_star_n22_full_tail_public_manifest.json"
SALT="QRR-n22-precision-audit-iid-20261015"
N_SAMPLES=131072
ALPHA=0.01
W=32
EXACT_M=18
TOTAL_TESTS=4*2*21*2*2  # four frozen Ns, two policies, 21 stages, H/T, two tails
DELTA=ALPHA/TOTAL_TESTS
LOG=math.log(2/DELTA)
STAGES=tuple(range(4,45,2))
SHOTS=4
assert TOTAL_TESTS==672 and len(STAGES)==21


@njit
def head_moments(centers,residuals,r,Q,valid,n,width):
    total_h=0.
    total_h2=0.
    total_t=0.
    total_t2=0.
    minimum_total=1.
    max_oversum=0.
    for i in range(len(centers)):
        local_h=0.
        local_mass=0.
        for j in range(-width,width+1):
            t=residuals[i]-r*j
            if t==0:
                prob=1.
            else:
                numerator=math.sin(math.pi*(float(t)/float(r)))
                denominator=float(Q)*math.sin(math.pi*float(t)/(float(r)*float(Q)))
                prob=(numerator/denominator)**2
            if not math.isfinite(prob) or prob<0:raise ValueError("invalid geometric QPE mass")
            local_mass+=prob
            y=(centers[i]+j)%Q
            if old.cf_valid(y,Q,valid,n):
                local_h+=prob
        if local_mass>1.+1e-8:raise ValueError("probability head exceeds 1")
        if local_mass<minimum_total:minimum_total=local_mass
        if local_mass-1.>max_oversum:max_oversum=local_mass-1.
        if local_h>1.+1e-8 or local_h<-1e-8:raise ValueError("head success outside probability range")
        omission=max(0.,1.-local_mass)
        total_h+=local_h
        total_h2+=local_h*local_h
        total_t+=omission
        total_t2+=omission*omission
    return total_h,total_h2,total_t,total_t2,minimum_total,max_oversum


def bernstein_eps(mean,second,n):
    assert n>1 and 0<=mean<=1+1e-8
    variance=max(0.,(n*second-n*mean*mean)/(n-1))
    # Theorem 4 (Maurer & Pontil, 2009): one-sided empirical Bernstein
    # bound for [0,1] IID; symmetrize and union-budget both tails.
    eps=math.sqrt(2*variance*LOG/n)+7*LOG/(3*(n-1))
    return float(eps),float(variance)


def eigenphase_stream(n,m,r,cache):
    if r<=N_SAMPLES:
        return range(r),"exhaustive_all_eigenphases"
    k=(n,m)
    if k not in cache:
        seed=int.from_bytes(hashlib.sha256(f"{SALT}|{n}|{m}".encode()).digest(),"big")
        rng=random.Random(seed)
        cache[k]=tuple(rng.random() for _ in range(N_SAMPLES))
    return (min(r-1,int(u*r)) for u in cache[k]),"seeded_iid_uniform_eigenphase_estimate"


def high_stage(n,base,r,m,valid,cache):
    Q=1<<m
    samples,mode=eigenphase_stream(n,m,r,cache)
    centers=[]
    residuals=[]
    # Use arbitrary precision integer multiplication, unlike naive int64 s*Q.
    for s in samples:
        q,rem=divmod(s*Q,r)
        if rem*2>=r:
            centers.append(q+1)
            residuals.append(rem-r)
        else:
            centers.append(q)
            residuals.append(rem)
    c=np.array(centers,dtype=np.int64)
    t=np.array(residuals,dtype=np.int64)
    assert len(c)>0
    h,h2,om,om2,minmass,over=head_moments(c,t,int(r),int(Q),valid,int(n),W)
    nn=len(c)
    H=h/nn
    T=om/nn
    if mode=="exhaustive_all_eigenphases":
        eps_H=eps_T=0.
        var_H=var_T=0.
    else:
        eps_H,var_H=bernstein_eps(H,h2/nn,nn)
        eps_T,var_T=bernstein_eps(T,om2/nn,nn)
    residual_up=min(1/(2*W-1),T+eps_T)
    lo=max(0.,H-eps_H)
    hi=min(1.,H+eps_H+residual_up)
    assert 0<=lo<=hi<=1+1e-10
    assert 0<=T<=1/(2*W-1)+1e-7,(n,base,m,T)
    assert over<=1e-8
    return dict(m=m,mode=mode,n_eigenphase_values=nn,phase_denominator_Q=Q,
       centered_outcome_bins_per_eigenphase=65,lower=lo,upper=hi,
       accepted_head_mean=H,head_variance_unbiased=var_H,
       head_eb_epsilon=eps_H,omitted_tail_mean=T,
       omitted_variance_unbiased=var_T,omitted_eb_epsilon=eps_T,
       omitted_tail_upper_bound=residual_up,
       universal_analytic_tail_bound=1/63,
       min_per_eigenphase_head_total_mass=minmass,
       max_per_eigenphase_head_oversum=over)


def exact_stage(n,base,r,m,valid):
    P,diag=exact.full_qpe_probabilities(r,m)
    mask=old.good_y_mask(len(P),valid,n)
    value=float(P[mask].sum())
    assert 0<=value<=1+1e-9
    return dict(m=m,mode="exact_all_bin_FFT",n_eigenphase_values=r,
       phase_denominator_Q=1<<m,lower=value,upper=value,
       full_probability_sum=diag["probability_sum_before_clip"],
       omitted_tail_upper_bound=0.,head_eb_epsilon=0.,omitted_eb_epsilon=0.)


def score_base(n,base,r,publiccert,gatecache,phasecache):
    good,prep=publiccert
    if len(good)==0:
        stages=[dict(m=m,mode="PUBLIC_CF_EMPTY_EXACT_ZERO",
             lower=0.,upper=0.,n_eigenphase_values=0,
             omitted_tail_upper_bound=0.) for m in STAGES]
    else:
        stages=[exact_stage(n,base,r,m,good) if m<=EXACT_M
                else high_stage(n,base,r,m,good,phasecache) for m in STAGES]
    s_low=1-math.prod((1-z["lower"])**SHOTS for z in stages)
    s_high=1-math.prod((1-z["upper"])**SHOTS for z in stages)
    c_low,round_low=old.cost_for_bound(n,base,stages,gatecache,"lower")
    c_high,round_high=old.cost_for_bound(n,base,stages,gatecache,"upper")
    assert 0<=s_low<=s_high<=1+1e-8
    assert 0<=c_low<=c_high+1e-6
    return dict(base=base,validation_only_order=r,
       strict_public_CF_certificate_count=len(good),
       public_CF_precomputation=prep,
       exact_factor_incapable=len(good)==0,
       factor_probability_by_cap_interval=[s_low,s_high],
       modeled_CCX_attempt_interval=[c_low,c_high],
       modeled_phase_round_interval=[round_low,round_high],
       modeled_CCX_per_factor_success_interval=[
           c_low/s_high if s_high>0 else None,
           c_high/s_low if s_low>0 else None],
       all_stages=stages)


def check_selftests():
    # Fixed miniature exhaustive cases; count public good d without validation
    # factor/order in CF acceptance.
    assert old.selftests()["passed"]
    vals=[]
    for n,a in ((15,2),(35,2),(77,2),(143,2),(899,2)):
        good,prep=old.public_factor_certificates(n,a)
        for m in (4,6,8):
            mask=old.good_y_mask(1<<m,good,n)
            assert all(bool(mask[y])==bool(old.old.explicit_cf_proper_factor(n,a,y,m,{}))
                       for y in range(1<<m))
        vals.append([n,len(good)])
    # empirical Bernstein boundedness and constant outcomes
    eps,var=bernstein_eps(0.,0.,N_SAMPLES)
    assert 0<eps<.001 and var==0
    ep2,v2=bernstein_eps(.5,.5,N_SAMPLES)
    assert ep2>=eps and v2>=0
    # exact FFT convergence through new cap, even at 2^18 outcomes
    P,diag=exact.full_qpe_probabilities(31,18)
    assert abs(float(P.sum())-1)<1e-9 and len(P)==1<<18
    return dict(passed=True,public_CF_crosscheck=vals,
        exact_full_FFT_m18_probability_normalized=True,
        empirical_Bernstein_positive_bounded=True,
        n_cases_in_original_manifest=4)


def row_eval(entry,old_row,phasecache):
    n=entry["N"];a=entry["base"];b=entry["public_policies"]["cube"]
    assert b==pow(a,3,n)
    # Explicit PUBLIC computations/classical costs BEFORE validation orders.
    classical=n22classical.public_additional_classical(n)
    cert_a=old.public_factor_certificates(n,a)
    cert_b=old.public_factor_certificates(n,b)
    p,q=old.validation_factors(n)
    lam=math.lcm(p-1,q-1)
    order_a=model.multiplicative_order_from_lambda(a,n,lam)
    order_b=model.multiplicative_order_from_lambda(b,n,lam)
    assert order_b==order_a//math.gcd(order_a,3)
    assert order_a==old_row["validation_only"]["plain_order"]
    assert order_b==old_row["validation_only"]["cube_order"]
    cache={}
    plain=score_base(n,a,order_a,cert_a,cache,phasecache)
    cube=score_base(n,b,order_b,cert_b,cache,phasecache)
    cmp=old.classify(plain,cube)
    prev=old_row["cube_vs_plain"]
    old_width=(prev["ratio"][1]-prev["ratio"][0]) if None not in prev["ratio"] else None
    new_width=(cmp["ratio"][1]-cmp["ratio"][0]) if None not in cmp["ratio"] else None
    return dict(N=n,base=a,group=entry["group"],
       exact_same_frozen_base_policy=entry["public_policies"],
       additional_public_classical=classical,
       validation_only=dict(p=p,q=q,plain_order=order_a,cube_order=order_b,
          odd_power_identity_passed=True),
       plain=plain,cube=cube,cube_vs_plain=cmp,
       previous_original_experiment=dict(status=prev["status"],ratio=prev["ratio"],
           confidence_interval_width=old_width),
       numerical_accuracy=dict(new_interval_width=new_width,
           old_interval_width=old_width,
           narrowed=(new_width<old_width) if old_width is not None and new_width is not None else None,
           all_frozen_rows_retained=True))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--group",choices=("trigger","control"),required=True)
    args=ap.parse_args()
    manifest=json.loads(MANIFEST.read_text())
    digest=hashlib.sha256(frozen.canonical(manifest["selected_public_rows"]).encode()).hexdigest()
    assert digest==manifest["selected_sha256"]=="d0cfd98eab0b92bc07c39a896e2e0039c3e065f6c6521c525dbefd676c2e49ff"
    oldfile=ROOT/f"dark_star_n22_full_tail_{args.group}.json"
    previous=json.loads(oldfile.read_text())
    assert previous["public_manifest_sha256"]==digest
    entries=[r for r in manifest["selected_public_rows"] if r["group"]==args.group]
    assert len(entries)==len(previous["rows"])==2
    assert [x["N"] for x in entries]==[x["N"] for x in previous["rows"]]
    print("PRECISION-ONLY AUDIT, SAME PUBLIC SAMPLE",digest,
         "group",args.group,"N",N_SAMPLES,"exact FFT m <=",EXACT_M,
         "two-sided EB union-budget tests",TOTAL_TESTS,flush=True)
    tests=check_selftests()
    phasecache={}
    rows=[]
    for i,(entry,old_row) in enumerate(zip(entries,previous["rows"]),1):
        st=time.process_time()
        item=row_eval(entry,old_row,phasecache)
        rows.append(item)
        print(f"[{i}/2] {args.group} n={entry['N']} classic={item['additional_public_classical']['first_factor_source']} "
             f"old_ratio={item['previous_original_experiment']['ratio']} "
             f"new_ratio={item['cube_vs_plain']['ratio']} "
             f"new_status={item['cube_vs_plain']['status']} "
             f"narrower={item['numerical_accuracy']['narrowed']} "
             f"CPU={time.process_time()-st:.3f}s",flush=True)
    valid=[z for z in rows if z["numerical_accuracy"]["narrowed"] is not None]
    improvements=sum(z["numerical_accuracy"]["narrowed"] for z in valid)
    # Primary methodological gate checked ACROSS BOTH CI jobs at preservation.
    out=dict(experiment="dark_star_n22_on_frozen_four_precision_only_audit_v1",
      preregistration="docs/DARK_STAR_N22_NUMERICAL_PRECISION_AUDIT_PREREG.md",
      original_manifest_sha256=digest,
      reuses_identical_frozen_n_and_bases=True,not_independent_holdout=True,
      group=args.group,n_phase_samples=N_SAMPLES,
      exact_full_outcome_FFT_phase_cap=EXACT_M,
      sampled_stage_centered_window=W,
      phase_salt=SALT,
      simultaneous_alpha=ALPHA,union_budget_test_count=TOTAL_TESTS,
      EB_log_factor=LOG,
      phase_sampling_claim="99 percent simultaneous empirical Bernstein under i.i.d. uniform eigenphases; fixed PRNG is not a certified random source; numba numerical evaluation is not directed rounding",
      zero_QPU=True,qpu_jobs_submitted=0,
      selftests=tests,rows=rows,
      summary=dict(selected=2,n_comparable_to_old=len(valid),
        n_interval_narrower=improvements,
        model_outcome_classes=dict(Counter(z["cube_vs_plain"]["status"] for z in rows)),
        all_classically_factored=sum(x["additional_public_classical"]["classically_factored"] for x in rows)),
      claim_boundary="Same frozen 4 n22 samples, exploratory precision-method audit; not new independent positive discovery or physical quantum advantage")
    width=model.arithmetic_width(entries[0]["N"])
    out["logical_width"]=dict(arithmetic_workspace=width["arithmetic_qubits_excluding_phase"],
       wide_peak=width["arithmetic_qubits_excluding_phase"]+44,
       recycled_peak=width["recycled_logical_qubits"])
    dst=ROOT/f"dark_star_n22_precision_audit_{args.group}.json"
    dst.write_text(json.dumps(out,indent=2)+"\n")
    print("===== FROZEN N22 NUMERICAL PRECISION AUDIT =====")
    print(args.group,"comparable",len(valid),"narrower",improvements,
        "statuses",out["summary"]["model_outcome_classes"],"ZERO QPU, wrote",dst,flush=True)


if __name__=="__main__":
    main()
