#!/usr/bin/env python3
"""Full ideal QPE outcome head + conservative omitted-tail bound at n22.

Separate eigenphase Monte Carlo uncertainty is explicitly Hoeffding bounded
under ideal independent uniform draws; reproducible PRNG is NOT formal random
certification. Strict public CF/GCD factoring, never secret order in verdict.
Research lead/original concept: Chase Lunsford / CaMaLabs. ZERO QPU jobs.
"""
from __future__ import annotations
import argparse,hashlib,json,math,random,time
from collections import Counter
from pathlib import Path

import numpy as np
from numba import njit

import dark_star_ptp_shor_audit as ds
import dark_star_recycled_scalable_arithmetic_audit as model
import dark_star_full_qpe_outcome_holdout as full
import dark_star_n22_selector_vs_cube as pastn22
import dark_star_public_selector_larger_holdout as old
import dark_star_n22_full_tail_public_manifest as selected

W=32
SAMPLES=16384
ALPHA=0.01
BIT_SIZE=22
START=4
STEP=2
SHOTS=4
EXACT_M=12
SALTING="QRR-n22-full-tail-phase-v1-20261014"
MANIFEST=Path("results/dark_star_ptp/dark_star_n22_full_tail_public_manifest.json")
ROOT=Path("results/dark_star_ptp")
TOTAL_UNION_TESTS=2*2*2*21
EPS=math.sqrt(math.log(2*TOTAL_UNION_TESTS/ALPHA)/(2*SAMPLES))
TAIL=1/(2*W-1)


@njit
def cf_valid(y,Q,good,n):
    if y==0 or len(good)==0:
        return False
    a=y
    b=Q
    den_prevprev=1
    den_prev=0
    while b!=0:
        q=a//b
        rem=a%b
        d=q*den_prev+den_prevprev
        if 1<d<=n and d%2==0:
            left=0
            right=len(good)
            while left<right:
                mid=(left+right)//2
                if good[mid]<d:left=mid+1
                else:right=mid
            if left<len(good) and good[left]==d:return True
        if d>n:break
        den_prevprev=den_prev
        den_prev=d
        a=b
        b=rem
    return False


@njit
def head_accumulate(centers,t0s,r,Q,good,n,width):
    accepted=0.
    total_mass=0.
    max_perphase_oversum=0.
    # The center/t offset is computed in Python big integers to prevent
    # 22-bit order × 44-bit Q from overflowing int64. t0 is always small.
    for i in range(len(centers)):
        local_mass=0.
        for j in range(-width,width+1):
            t=t0s[i]-r*j
            if t==0:
                p=1.
            else:
                numerator=math.sin(math.pi*(float(t)/float(r)))
                denominator=float(Q)*math.sin(math.pi*float(t)/(float(r)*float(Q)))
                p=(numerator/denominator)**2
            if p<0.:raise ValueError("negative probability")
            local_mass+=p
            y=(centers[i]+j)%Q
            if cf_valid(y,Q,good,n):
                accepted+=p
        if local_mass>1.+1e-8:raise ValueError("per-phase probability exceeds 1")
        if local_mass-1.>max_perphase_oversum:max_perphase_oversum=local_mass-1.
        total_mass+=local_mass
    return accepted,total_mass,max_perphase_oversum


@njit
def good_y_mask(Q,good,n):
    flag=np.zeros(Q,dtype=np.bool_)
    for y in range(1,Q):
        flag[y]=cf_valid(y,Q,good,n)
    return flag


def public_factor_certificates(n,base):
    """O(n) public modular multiplication ledger, no validation p/q/r oracle.

    This preparation can itself CLASSICALLY recover factors. It is an
    evaluation aid, not a free quantum subroutine or public speedup.
    """
    begin=time.process_time()
    z=base%n                    # z=a^(d/2), d=2 initially
    x=(z*z)%n                  # x=a^d
    valid=[]
    factors=set()
    gcount=0
    multiplication_count=1
    for half in range(1,n//2+1):
        d=2*half
        if x==1:
            g=math.gcd(z-1,n)
            h=math.gcd(z+1,n)
            gcount+=2
            if (1<g<n and n%g==0) or (1<h<n and n%h==0):
                valid.append(d)
                if 1<g<n:factors.add(int(g))
                if 1<h<n:factors.add(int(h))
        z=(z*base)%n
        x=(z*z)%n
        multiplication_count+=2
    return np.array(valid,dtype=np.int64),dict(
        public_modular_multiplications=multiplication_count,
        public_gcd_calls=gcount,
        candidate_denominators_checked=n//2,
        factor_producing_denominators=len(valid),
        public_factors_found_by_precomputation=sorted(factors),
        public_CPU_seconds=round(time.process_time()-begin,5),
        explicitly_classical_factor_recovery=True)


def sample_eigenphases(n,m,r,u_cache):
    if r<=SAMPLES:
        samples=range(r)
        mode="exhaustive_all_eigenphases"
    else:
        key=(n,m)
        if key not in u_cache:
            raw=f"{SALTING}|{n}|{m}".encode()
            h=int.from_bytes(hashlib.sha256(raw).digest(),"big")
            rng=random.Random(h)
            u_cache[key]=[rng.random() for _ in range(SAMPLES)]
        samples=(min(r-1,int(u*r)) for u in u_cache[key])
        mode="seeded_iid_uniform_eigenphase_estimate"
    return samples,mode


def sampled_head_stage(n,base,r,m,good,u_cache):
    Q=1<<m
    assert m>EXACT_M and Q>2*W+1
    samples,mode=sample_eigenphases(n,m,r,u_cache)
    # IMPORTANT: Python arbitrary precision divmod prevents 64-bit overflow
    # even when s up to millions and Q=2^44.
    centers=[]
    residuals=[]
    for s in samples:
        quotient,remainder=divmod(s*Q,r)
        if 2*remainder>=r:
            centers.append(quotient+1)
            residuals.append(remainder-r)
        else:
            centers.append(quotient)
            residuals.append(remainder)
    centers=np.asarray(centers,dtype=np.int64)
    residuals=np.asarray(residuals,dtype=np.int64)
    accepted,mass,oversum=head_accumulate(
        centers,residuals,int(r),int(Q),good,int(n),W)
    head=accepted/len(centers)
    total=mass/len(centers)
    assert -1e-8<=head<=total+1e-8
    assert total<=1+1e-8,(n,base,m,total)
    if mode=="exhaustive_all_eigenphases":
        eps=0.
        omission=max(0.,1-total)
    else:
        eps=EPS
        omission=TAIL
    lo=max(0.,head-eps)
    hi=min(1.,head+eps+omission)
    assert -1e-12<=lo<=hi<=1+1e-12
    return dict(m=m,mode=mode,n_eigenphase_values=len(centers),
        outcome_bins_per_eigenphase=2*W+1,
        lower=lo,upper=hi,head_success_mean=head,
        head_total_mass_mean=total,
        omission_upper_bound=omission,
        eigenphase_Hoeffding_epsilon=eps,
        max_per_eigenphase_mass_oversum=oversum,
        phase_denominator_Q=Q)


def exact_stage(n,base,r,m,good):
    P,diag=full.full_qpe_probabilities(r,m)
    Q=len(P)
    found=good_y_mask(Q,good,n)
    p=float(P[found].sum())
    assert 0<=p<=1+1e-9
    return dict(m=m,mode="exact_all_bin_FFT",n_eigenphase_values=r,
        outcome_bins_per_eigenphase=Q,
        lower=p,upper=p,head_success_mean=p,
        head_total_mass_mean=1.,
        omission_upper_bound=0.,eigenphase_Hoeffding_epsilon=0.,
        fft_normalization=diag["probability_sum_before_clip"],
        phase_denominator_Q=Q)


def cost_for_bound(n,base,stages,gate_cache,which):
    assert which in ("lower","upper")
    reach=1.
    ccx=0.
    phase_rounds=0.
    for stage in stages:
        # Upper success bound => fewer attempted shots and fewer CCX.
        p=stage["upper"] if which=="lower" else stage["lower"]
        E=reach*model.expected_stage_shots(p,SHOTS)
        gates=model.stage_arithmetic_count(n,base,stage["m"],gate_cache)
        ccx+=E*float(gates.get("ccx",0))
        phase_rounds+=E*stage["m"]
        reach*=(1.-p)**SHOTS
    return float(ccx),float(phase_rounds)


def score_base(n,base,r,gate_cache,u_cache):
    good,public_prep=public_factor_certificates(n,base)
    stages=[]
    for m in model.stage_schedule(n,START,STEP):
        if len(good)==0:
            # Exact public logical proof for ANY phase y, even omitted tails.
            z=dict(m=m,mode="public_certificate_set_empty_exact_zero",
                lower=0.,upper=0.,head_success_mean=0.,
                omission_upper_bound=0.,
                eigenphase_Hoeffding_epsilon=0.,
                n_eigenphase_values=0,outcome_bins_per_eigenphase=0,
                phase_denominator_Q=1<<m)
        else:
            z=(exact_stage(n,base,r,m,good) if m<=EXACT_M
               else sampled_head_stage(n,base,r,m,good,u_cache))
        stages.append(z)
    s_lo=1-math.prod((1-z["lower"])**SHOTS for z in stages)
    s_hi=1-math.prod((1-z["upper"])**SHOTS for z in stages)
    c_lo,r_lo=cost_for_bound(n,base,stages,gate_cache,"lower")
    c_hi,r_hi=cost_for_bound(n,base,stages,gate_cache,"upper")
    assert -1e-10<=s_lo<=s_hi<=1+1e-10
    assert 0<=c_lo<=c_hi+1e-6
    lo=(c_lo/s_hi) if s_hi>0 else None
    hi=(c_hi/s_lo) if s_lo>0 else None
    return dict(base=base,validation_only_order=r,
        public_CF_precomputation=public_prep,
        public_factor_producing_denominator_count=len(good),
        exact_factor_incapable=(len(good)==0),
        factor_probability_by_cap_interval=[max(0,s_lo),min(1,s_hi)],
        modeled_CCX_attempt_interval=[c_lo,c_hi],
        modeled_phase_round_interval=[r_lo,r_hi],
        modeled_CCX_per_factor_success_interval=[lo,hi],
        all_stages=stages)


def classify(plain,cube):
    a=plain["modeled_CCX_per_factor_success_interval"]
    b=cube["modeled_CCX_per_factor_success_interval"]
    if None in a or None in b:
        return dict(status="factor_incapable_or_uncertified",ratio=[None,None])
    low=b[0]/a[1] if a[1]>0 else None
    high=b[1]/a[0] if a[0]>0 else None
    if low is None or high is None:return dict(status="ratio_unbounded",ratio=[low,high])
    status="cube_model_win" if high<1 else ("cube_model_loss" if low>1 else "inconclusive")
    return dict(status=status,ratio=[low,high])


def selftests():
    # Certificate production is public and fast compiled CF must agree with
    # the unmodified original strict public factor extraction.
    trials=[]
    for n,a in ((15,2),(21,2),(35,2),(77,2),(143,2),(899,2)):
        assert math.gcd(n,a)==1
        good,prep=public_factor_certificates(n,a)
        for m in (4,6,8):
            q=1<<m
            mask=good_y_mask(q,good,n)
            for y in range(q):
                assert bool(mask[y])==bool(old.explicit_cf_proper_factor(n,a,y,m,{})),(
                     n,a,m,y,bool(mask[y]))
        trials.append((n,len(good),len(prep["public_factors_found_by_precomputation"])))
    # Independently checked full-QPE probability-mass normalization.
    assert abs(float(full.full_qpe_probabilities(7,6)[0].sum())-1)<1e-9
    assert math.isclose(EPS,math.sqrt(math.log(2*TOTAL_UNION_TESTS/ALPHA)/(2*SAMPLES)))
    assert EPS>0 and TAIL==1/63
    # Guard against bigint overflow at the stage with Q=2^44.
    s=3_456_789
    Q=1<<44
    r=3_456_791
    q,rem=divmod(s*Q,r)
    assert abs(q-Q*s/r)<=1
    assert rem<r
    return dict(passed=True,public_certificates_match_slow_factor_verifier=True,
        direct_test_cases=trials,
        full_FFT_mass_pass=True,large_Q_bigint_guard_pass=True)


def validation_factors(n):
    for p in ds.sieve_primes(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p<q and p>=11
            assert all(q%d for d in range(2,math.isqrt(q)+1))
            return p,q
    raise AssertionError("not a valid distinct-prime semiprime")


def one_row(r,u_cache):
    n=int(r["N"])
    a=int(r["base"])
    b=pow(a,3,n)
    assert r["public_policies"]==dict(plain=a,cube=b)
    # Public factorization and public candidate denominator precomputation
    # are deliberately performed before computing validation-only r.
    classical=pastn22.public_additional_classical(n)
    pre_a=public_factor_certificates(n,a)
    pre_b=public_factor_certificates(n,b)
    # PRIVATES: validation simulation only AFTER all public decisions.
    p,q=validation_factors(n)
    lam=math.lcm(p-1,q-1)
    order0=model.multiplicative_order_from_lambda(a,n,lam)
    order1=model.multiplicative_order_from_lambda(b,n,lam)
    assert order1==order0//math.gcd(order0,3)
    gate_cache={}
    # Score public certs without recomputing expensive enumeration.
    out={}
    for key,base,order,public_cert in (("plain",a,order0,pre_a),("cube",b,order1,pre_b)):
        out[key]=score_base_cached(n,base,order,gate_cache,u_cache,public_cert)
    cmp=classify(out["plain"],out["cube"])
    return {**r, "additional_public_classical":classical,
        "validation_only":dict(p=p,q=q,plain_order=order0,cube_order=order1,
            known_odd_power_identity=True),
        "plain":out["plain"],"cube":out["cube"],"cube_vs_plain":cmp,
        "no_qpu":True}


def score_base_cached(n,base,r,gate_cache,u_cache,public_cert):
    # Same scorer as score_base but uses PRECOMPUTED strict public certificates
    # from before the private validation-order calculation.
    good,prep=public_cert
    stages=[]
    for m in model.stage_schedule(n,START,STEP):
        if len(good)==0:
            z=dict(m=m,mode="public_certificate_set_empty_exact_zero",
                lower=0.,upper=0.,head_success_mean=0.,
                omission_upper_bound=0.,eigenphase_Hoeffding_epsilon=0.,
                n_eigenphase_values=0,outcome_bins_per_eigenphase=0,
                phase_denominator_Q=1<<m)
        else:
            z=exact_stage(n,base,r,m,good) if m<=EXACT_M else sampled_head_stage(n,base,r,m,good,u_cache)
        stages.append(z)
    s_lo=1-math.prod((1-z["lower"])**SHOTS for z in stages)
    s_hi=1-math.prod((1-z["upper"])**SHOTS for z in stages)
    c_lo,round_lo=cost_for_bound(n,base,stages,gate_cache,"lower")
    c_hi,round_hi=cost_for_bound(n,base,stages,gate_cache,"upper")
    assert 0<=s_lo<=s_hi<=1+1e-9 and 0<=c_lo<=c_hi+1e-6
    return dict(base=base,validation_only_order=r,
        public_CF_precomputation=prep,
        public_factor_producing_denominator_count=len(good),
        exact_factor_incapable=(len(good)==0),
        factor_probability_by_cap_interval=[s_lo,s_hi],
        modeled_CCX_attempt_interval=[c_lo,c_hi],
        modeled_phase_round_interval=[round_lo,round_hi],
        modeled_CCX_per_factor_success_interval=[
            c_lo/s_hi if s_hi>0 else None,
            c_hi/s_lo if s_lo>0 else None],
        all_stages=stages)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--group",choices=("trigger","control"),required=True)
    p.add_argument("--manifest",type=Path,default=MANIFEST)
    p.add_argument("--out",type=Path)
    o=p.parse_args()
    m=json.loads(o.manifest.read_text())
    assert hashlib.sha256(selected.canonical(m["selected_public_rows"]).encode()).hexdigest()==m["selected_sha256"]
    rows=[r for r in m["selected_public_rows"] if r["group"]==o.group]
    assert len(rows)==2
    assert m["zero_QPU"] and m["qpu_jobs_submitted"]==0
    print("FROZEN FRESH N22 full-tail SHA",m["selected_sha256"],"group",o.group,
          "phase samples",SAMPLES,"W",W,"simultaneous alpha",ALPHA,
          "eigenphase epsilon",EPS,flush=True)
    ans=dict(experiment="dark_star_n22_fresh_fulloutcome_tail_with_phase_sampling_v1",
        preregistration="docs/DARK_STAR_N22_FULL_OUTCOME_BOUNDED_PREREG.md",
        public_manifest_sha256=m["selected_sha256"],group=o.group,bits=22,
        alpha=ALPHA,simultaneous_union_tests=TOTAL_UNION_TESTS,
        samples=SAMPLES,eigenphase_hoeffding_epsilon=EPS,
        outcome_half_window=W,
        analytic_omitted_tail_universal_bound=TAIL,
        zero_QPU=True,qpu_jobs_submitted=0,
        screening=m["public_screenings"][o.group],
        selftests=selftests(),rows=[],summary={},
        claim_boundary="Ideal QPE complete-outcome tail + 99%-simultaneous statistical eigenphase-sampling bound, not deterministic all-order certification, QPU, hardware speed or practical factoring.")
    u_cache={}
    for i,r in enumerate(rows,1):
        start=time.process_time()
        item=one_row(r,u_cache)
        ans["rows"].append(item)
        print(f"[{i}/2] group={o.group} N={item['N']} "
              f"public_classical={item['additional_public_classical']['first_factor_source']} "
              f"CF_good_plain/cube={item['plain']['public_factor_producing_denominator_count']}/"
              f"{item['cube']['public_factor_producing_denominator_count']} "
              f"ratio={item['cube_vs_plain']['ratio']} status={item['cube_vs_plain']['status']} "
              f"CPU={time.process_time()-start:.2f}s",flush=True)
    summary=dict(selected=2,screened=len(ans["screening"]),
        earlier_B31_factored=sum(s["public_B31_factored"] for s in ans["screening"]),
        additional_classically_factored=sum(r["additional_public_classical"]["classically_factored"] for r in ans["rows"]),
        cases_by_status=dict(Counter(r["cube_vs_plain"]["status"] for r in ans["rows"])),
        public_CF_precompute_disclosed=True,
        factor_capable_plain=sum(not r["plain"]["exact_factor_incapable"] for r in ans["rows"]),
        factor_capable_cube=sum(not r["cube"]["exact_factor_incapable"] for r in ans["rows"]))
    width=model.arithmetic_width(rows[0]["N"])
    ans["logical_width"]=dict(arithmetic_workspace=width["arithmetic_qubits_excluding_phase"],
        wide_peak=width["arithmetic_qubits_excluding_phase"]+44,
        recycled_peak=width["recycled_logical_qubits"])
    ans["summary"]=summary
    assert len(ans["rows"])==2
    out=o.out or ROOT/f"dark_star_n22_full_tail_{o.group}.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(ans,indent=2)+"\n")
    print("===== N22 FULL-OUTCOME-TAIL & EIGENPHASE-CONFIDENCE HOLDOUT =====",flush=True)
    print("selected",summary["selected"],"public screen",summary["screened"],
          "classical before/after",summary["earlier_B31_factored"],
          summary["additional_classically_factored"],"model classifications",
          summary["cases_by_status"],"width",ans["logical_width"],flush=True)
    print("ZERO QPU JOBS; wrote",out,flush=True)


if __name__=="__main__":
    main()
