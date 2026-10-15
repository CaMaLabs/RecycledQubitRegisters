#!/usr/bin/env python3
"""Pre-registered n22 full-outcome-head + confidence-bounded phase-tail QPE.

PUBLIC preselection is in a different, already-committed immutable manifest.
No IBM Runtime import, hardware backend, cloud QPU or billed QPU use.
Research direction: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from numba import njit

import dark_star_ptp_shor_audit as ds
import dark_star_recycled_scalable_arithmetic_audit as gates
import dark_star_full_qpe_outcome_holdout as full
import dark_star_public_multichoice_survivor_holdout as mc
import dark_star_tail_bounded_qpe_classical_survivor as tail

ROOT = Path("results/dark_star_ptp")
MANIFEST = ROOT / "dark_star_n22_full_tail_public_manifest.json"
REV = "QRR-n22-fresh-all-outcome-tail-v1"
SAMPLE_SALT = "QRR-n22-full-tail-phase-v1-20261014"
M_SAMPLES = 16384
WINDOW = 32
ALPHA = 0.01
COMPARISON_CAP = 168
ERROR = math.sqrt(math.log(2*COMPARISON_CAP/ALPHA)/(2*M_SAMPLES))
TAIL_BOUND = 1/(2*WINDOW-1)
MAX_M = 44
SHOTS = 4


def canonical(a):
    return json.dumps(a, sort_keys=True, separators=(",", ":"))


def good_public_denominators(n:int,a:int):
    """All even d<=N, PUBLIC modular recurrence; no factor/order oracle.
    
    A certificate already exposes public nontrivial factors: record explicitly.
    """
    good = np.zeros(n+1, dtype=np.uint8)
    factor_first = None
    n_good = n_pow = gcds = 0
    a_mod = a % n
    a2 = a_mod*a_mod % n
    x_full = a2        # base^(2)
    x_half = a_mod     # base^(1)
    for d in range(2,n+1,2):
        if x_full == 1:
            f1=math.gcd(x_half-1,n)
            f2=math.gcd(x_half+1,n)
            gcds += 2
            f=f1 if 1<f1<n else (f2 if 1<f2<n else None)
            if f is not None:
                assert n % f==0
                good[d]=1
                n_good+=1
                if factor_first is None:factor_first=int(f)
        x_full = x_full*a2 %n
        x_half = x_half*a_mod %n
        n_pow += 2
    return good,dict(valid_denominators=n_good,
                     first_public_factor=factor_first,
                     all_even_d_checked=n//2,
                     public_modmult_equiv=n_pow,
                     public_gcd_calls=gcds,
                     public_precomputation_factors_N=(factor_first is not None))


@njit(cache=False)
def public_cf_mask(ys, q, n, good):
    """Numba-compiled equivalent of PUBLIC Euclidean CF denominator scan."""
    out=np.zeros(ys.size,dtype=np.uint8)
    for i in range(ys.size):
        y=int(ys[i])
        if y==0:
            continue
        a=y
        b=q
        pp=1
        prev=0
        while b!=0:
            quot=a//b
            rem=a%b
            d=quot*prev+pp
            if d>n:
                break
            if d>1 and good[d] != 0:
                out[i]=1
                break
            pp=prev
            prev=d
            a=b
            b=rem
    return out


def public_classical_after_b31(n):
    first=mc.pminusone(n,47)
    if first["found"]:
        f=first["factor"]
        assert 1<f<n and n%f==0
        return dict(factored=True,method="Pollard_p1_B47",factor=f,
                    p1_b47=first,rho=None,prime_trial=None)
    rho=tail.pollard_rho(n,iteration_cap=64)
    if rho["found"]:
        f=rho["public_factor"]
        assert 1<f<n and n%f==0
        return dict(factored=True,method="Pollard_rho_64x2",
                    factor=f,p1_b47=first,rho=rho,prime_trial=None)
    tested=0
    for p in ds.sieve_primes(math.isqrt(n)):
        tested+=1
        if n%p==0:
            return dict(factored=True,method="complete_prime_trial",
                        factor=p,p1_b47=first,rho=rho,
                        prime_trial=dict(primes_checked=tested))
    raise AssertionError(f"synthetic semiprime not factored by public classical fallback: N={n}")


def validation_pair(n):
    for p in ds.sieve_primes(math.isqrt(n)):
        if n%p==0:
            q=n//p
            assert p!=q and p>=11 and q>=11 and p*q==n
            return p,q
    raise AssertionError("validation-only synthetic p,q unavailable")


def uniform_phases(n,m):
    seed=int.from_bytes(hashlib.sha256(f"{SAMPLE_SALT}|{n}|{m}".encode()).digest(),"big")
    rng=random.Random(seed)
    return [rng.random() for _ in range(M_SAMPLES)]


def full_exact_stage(n,base,order,m,good):
    hist,diag=full.full_qpe_probabilities(order,m)
    q=1<<m
    ys=np.arange(q,dtype=np.int64)
    mask=public_cf_mask(ys,q,n,good)
    p=float(hist[mask.astype(bool)].sum())
    assert -1e-8<=p<=1+1e-8
    p=min(1.0,max(0.0,p))
    return {"m":m,"lower":p,"upper":p,
            "method":"exact_all_Q_bins_via_fft","phase_samples":order,
            "all_outcome_bins":q,"valid_public_accepting_bins":int(mask.sum()),
            "fft_diagnostic":diag,"tail_upper_bound":0,"phase_sample_error":0}


def bounded_head_stage(n,base,order,m,good,shared_draws):
    q=1<<m
    assert 14<=m<=MAX_M and q > 2*WINDOW+1
    sampled = order > M_SAMPLES
    values=[int(u*order) for u in shared_draws] if sampled else list(range(order))
    nsamples=len(values)
    assert nsamples>0
    offs=np.arange(-WINDOW,WINDOW+1,dtype=np.int64)
    acc=mass=0.0
    maximum_mass=0.
    examined=0
    # Integer-safe nearest-bin arithmetic: s*Q may exceed signed int64.
    for k in range(0,nsamples,512):
        s=values[k:k+512]
        y0=np.asarray([(2*x*q+order)//(2*order) for x in s],dtype=np.int64)
        t0=np.asarray([x*q-order*int(y) for x,y in zip(s,y0)],dtype=np.int64)
        y=np.remainder(y0[:,None]+offs[None,:],q)
        t=t0[:,None]-order*offs[None,:]
        tf=t.astype(np.float64)
        numerator=np.sin(np.pi*tf/order)
        denominator=q*np.sin(np.pi*tf/(float(order)*q))
        with np.errstate(divide="ignore",invalid="ignore",over="raise"):
            prob=np.where(t==0,1.,(numerator/denominator)**2)
        assert np.isfinite(prob).all() and (prob>=0).all(),(n,m,order)
        mx=float(prob.sum(axis=1).max())
        maximum_mass=max(maximum_mass,mx)
        assert mx<=1+1e-8,(n,m,mx)
        acc += float((prob*public_cf_mask(
            y.reshape(-1),q,n,good).reshape(prob.shape)).sum())
        mass+=float(prob.sum())
        examined+=prob.size
    mean_head=acc/nsamples
    mean_mass=mass/nsamples
    assert mean_head<=mean_mass+1e-8
    assert mean_mass<=1+1e-8
    eps=ERROR if sampled else 0.0
    # Sampled head acceptance mass is random; omitted tail bound holds for
    # EVERY eigenphase. For exhaustive r, exact omitted mass is available.
    tail_value=TAIL_BOUND if sampled else max(0.,1.-mean_mass)
    assert tail_value<=TAIL_BOUND+1e-8
    low=max(0.,mean_head-eps)
    high=min(1.,mean_head+eps+tail_value)
    assert high>=low-1e-10
    return {"m":m,"lower":low,"upper":high,
            "method":"65_exact_head_bins_phase_sampled" if sampled
                else "65_exact_head_bins_exhaustive_eigenphases",
            "phase_samples":nsamples,
            "head_success_estimate":mean_head,
            "mean_head_mass":mean_mass,
            "measured_head_tail_mean":max(0.,1.-mean_mass),
            "max_single_phase_head_mass":maximum_mass,
            "phase_sample_error":eps,
            "tail_upper_bound":tail_value,
            "outcome_bins_checked":examined,
            "universal_omitted_tail_bound":TAIL_BOUND}


def score_base(n,base,r,good,gate_cache,draw_cache):
    # Public empty-certificate proof of exactly zero factor-producing success.
    if not good.any():
        intervals=[{"m":m,"lower":0.,"upper":0.,
                    "method":"public_empty_denominator_certificate_zero",
                    "phase_samples":0,"tail_upper_bound":0.}
                   for m in gates.stage_schedule(n,4,2)]
    else:
        intervals=[]
        for m in gates.stage_schedule(n,4,2):
            if m<=12:
                z=full_exact_stage(n,base,r,m,good)
            else:
                if (n,m) not in draw_cache:
                    draw_cache[(n,m)]=uniform_phases(n,m)
                z=bounded_head_stage(n,base,r,m,good,draw_cache[(n,m)])
            intervals.append(z)
    # Monotone work/success intervals propagated through staged 4-shot stop.
    L=[z["lower"] for z in intervals]
    U=[z["upper"] for z in intervals]
    assert len(L)==21 and intervals[-1]["m"]==44
    success_low=max(0.,1-math.prod((1-x)**SHOTS for x in L))
    success_high=min(1.,1-math.prod((1-x)**SHOTS for x in U))
    ccx_low,phase_low=tail.one_policy_cost(n,base,intervals,gate_cache,"lower")
    ccx_high,phase_high=tail.one_policy_cost(n,base,intervals,gate_cache,"upper")
    assert success_low<=success_high+1e-10
    assert ccx_low<=ccx_high+1e-5
    return {"base":base,"order_validation_only":r,
            "success_probability_interval":[success_low,success_high],
            "ccx_attempt_interval":[ccx_low,ccx_high],
            "phase_round_interval":[phase_low,phase_high],
            "ccx_per_factor_success_interval":[
                (ccx_low/success_high if success_high>0 else None),
                (ccx_high/success_low if success_low>0 else None)],
            "stages":intervals}


def ratio_interval(plain,cube):
    a=plain["ccx_per_factor_success_interval"]
    b=cube["ccx_per_factor_success_interval"]
    if any(x is None for x in a+b) or any(x<=0 for x in a+b):
        return {"interval":[None,None],"class":"factor_incapable_or_unresolved",
                "both_positive_success":False}
    low=b[0]/a[1]
    high=b[1]/a[0]
    assert low<=high+1e-9
    return {"interval":[low,high],
            "class":("robust_cube_win" if high<1 else
                     ("robust_cube_loss" if low>1 else "numerically_inconclusive")),
            "both_positive_success":True}


def selftest():
    from dark_star_full_qpe_outcome_holdout import factor_producing_denominators
    from dark_star_public_selector_larger_holdout import explicit_cf_proper_factor
    for n,a in ((35,2),(77,2),(143,2)):
        b,ledger=good_public_denominators(n,a)
        expected=factor_producing_denominators(n,a)
        assert set(np.nonzero(b)[0])==expected
        for m in (4,6,8):
            q=1<<m
            ys=np.arange(q,dtype=np.int64)
            actual=public_cf_mask(ys,q,n,b)
            for y in range(q):
                assert bool(actual[y])==explicit_cf_proper_factor(n,a,int(y),m,{})
        assert ledger["public_precomputation_factors_N"]==bool(expected)
    # Stable sinc-squared kernel vs exhaustive FFT true distribution for tiny N.
    n,a=35,2
    good,_=good_public_denominators(n,a)
    r=gates.multiplicative_order_from_lambda(a,n,math.lcm(4,6))
    for m in (8,10):
        q=1<<m
        fft=full_exact_stage(n,a,r,m,good)["lower"]
        rng=bounded_head_stage(n,a,r,m,good,uniform_phases(n,m)) if m>=14 else None
        assert 0<=fft<=1
    return {"public_d_checked_vs_independent_modular_pow":True,
            "numba_Euclid_matches_python_public_CF":True,
            "exact_full_QPE_fft_checks":True,
            "integer_safe_sQ_t_mod_Q":True}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--group",choices=("trigger","control"))
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.self_test:
        print("SELFTEST",selftest())
        return 0
    if not args.group:
        ap.error("--group required")
    manifest=json.loads(MANIFEST.read_text())
    selections=manifest["selected_public_rows"]
    expected_sha=hashlib.sha256(canonical(selections).encode()).hexdigest()
    assert expected_sha==manifest["selected_sha256"]
    assert len(selections)==4 and len({x["N"] for x in selections})==4
    assert not set(x["N"] for x in selections)&set(manifest["previous_n22_excluded"])
    selected=[row for row in selections if row["group"]==args.group]
    assert len(selected)==2
    tests=selftest()
    result={
      "experiment":"dark_star_n22_full_outcome_tail_bounded",
      "preregistration":"docs/DARK_STAR_N22_FULL_OUTCOME_BOUNDED_PREREG.md",
      "revision":REV,"group":args.group,"public_manifest_sha256":expected_sha,
      "zero_qpu":True,"qpu_jobs_submitted":0,"complete":False,
      "sampling":{"all_bin_exact_m_up_to":12,"head_width_plus_minus":WINDOW,
                  "max_phase_samples_per_stage":M_SAMPLES,
                  "confidence_total_alpha":ALPHA,
                  "predeclared_total_tests":COMPARISON_CAP,
                  "simultaneous_99pct_per_stage_epsilon":ERROR,
                  "worst_case_deterministic_tail_per_eigenphase":TAIL_BOUND,
                  "seed_salt":SAMPLE_SALT},
      "public_screening":manifest["public_screenings"][args.group],
      "selftests":tests,"rows":[],"started_utc":datetime.now(timezone.utc).isoformat(),
      "claim_boundary":("Analytically tail-bounded, probabilistic phase-draw "
                        "interval for FULL ideal-QPE outcome model on 22bit "
                        "toy semiprimes. Not exact QPE, device, physical qubits, "
                        "wall-clock quantum advantage or RSA-scale factoring.")
    }
    target=args.out or ROOT/f"dark_star_n22_full_tail_{args.group}.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    partial=target.with_suffix(".partial.json")
    for k,entry in enumerate(selected,1):
        t0=time.process_time()
        n,a=entry["N"],entry["base"]
        print(f"[{k}/2] group={args.group} public N={n} base={a}",flush=True)
        classical=public_classical_after_b31(n)
        p,q=validation_pair(n)
        lam=math.lcm(p-1,q-1)
        cube=pow(a,3,n)
        r0=gates.multiplicative_order_from_lambda(a,n,lam)
        r3=gates.multiplicative_order_from_lambda(cube,n,lam)
        assert r3==r0//math.gcd(r0,3)
        gates_cache,draw_cache={},{}
        good0,cert0=good_public_denominators(n,a)
        good3,cert3=good_public_denominators(n,cube)
        print(f"  public certificates a={cert0['valid_denominators']} cube={cert3['valid_denominators']} "
              f"classical={classical['method']} orders_validation={r0}->{r3}",flush=True)
        plain=score_base(n,a,r0,good0,gates_cache,draw_cache)
        transformed=score_base(n,cube,r3,good3,gates_cache,draw_cache)
        cmp=ratio_interval(plain,transformed)
        out={**entry,"validation_only":{"p":p,"q":q,"lambda":lam,
              "baseline_order":r0,"cube_order":r3,"order_identity_ok":True},
             "classical_after_B31":classical,
             "public_CF_denominator_certificates":{"plain":cert0,"cube":cert3},
             "plain":plain,"cube":transformed,"cube_vs_plain":cmp,
             "cpu_seconds":round(time.process_time()-t0,6)}
        result["rows"].append(out)
        partial.write_text(json.dumps(result,indent=2)+"\n")
        print(f"  result={cmp['class']} ratio={cmp['interval']} cpu={out['cpu_seconds']}s",flush=True)
    result["complete"]=True
    result["completed_utc"]=datetime.now(timezone.utc).isoformat()
    result["summary"]={"rows":2,
        "public_B31_factored_in_screen":sum(s["public_B31_factored"]
                                           for s in result["public_screening"]),
        "classical_completed_after_B31":sum(r["classical_after_B31"]["factored"] for r in result["rows"]),
        "classifications":dict(Counter(r["cube_vs_plain"]["class"] for r in result["rows"])),
        "both_positive_success":sum(r["cube_vs_plain"]["both_positive_success"] for r in result["rows"]),
        "primary_trigger_pass":(
          args.group=="trigger" and all(
              r["cube_vs_plain"]["class"]=="robust_cube_win" for r in result["rows"]))}
    aw=gates.arithmetic_width(selected[0]["N"])
    assert aw["arithmetic_qubits_excluding_phase"]==69
    result["logical_width"]={"coherent_arithmetic_qubits":69,
        "wide_peak_logical":69+44,"recycled_peak_logical":70}
    target.write_text(json.dumps(result,indent=2)+"\n")
    print("COMPLETED",args.group,result["summary"],"NO QPU",flush=True)


if __name__=="__main__":
    main()
