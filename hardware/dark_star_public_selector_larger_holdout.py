#!/usr/bin/env python3
"""Preregistered n18 Dark Star PUBLIC selector vs plain base and stage-1 Pollard p-1.

Only oracle use: AFTER deterministic public-N selection, factor-derived orders
define ideal-QPE phase distribution. CF acceptance itself executes PUBLIC
modular exponentiation and public gcd tests, never validates with known order.
No QPU jobs are contacted.
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

import dark_star_ptp_shor_audit as dsbase
import dark_star_recycled_scalable_arithmetic_audit as model

REV="2026-10-14-public-selector-n18-exact-cf-v1"
ELLS=(3,5,7)
BASE_POOL=(2,3,5,7,11,13,17,19,23,29,31)
SELECTION_SALT="QRR-public-selector-population-v2-20261014"
BASE_SALT="QRR-public-selector-base-v2-20261014"
N_MIN=131072
N_MAX=262143
PER_GROUP=20
CLASSICAL_P1_BOUND=31
STAGE_START=4
STAGE_STEP=2
STAGE_SHOTS=4
POLICIES=("plain","unconditional","public_selector")
DEFAULT_DIR=Path("results/dark_star_ptp")


def hashed(salt,*parts):
    return int.from_bytes(hashlib.sha256("|".join(
        (salt,*(str(x) for x in parts))).encode("utf-8")).digest(),"big")


def pairs_for_range():
    primes=dsbase.sieve_primes(N_MAX)
    result=[]
    for i,p in enumerate(primes):
        if p<11:continue
        if p*p>N_MAX:break
        for q in primes[i+1:]:
            n=p*q
            if n>N_MAX:break
            if n>=N_MIN:result.append((p,q))
    return result


def choose_base(n,ell):
    start=hashed(BASE_SALT,ell,n)%len(BASE_POOL)
    for j in range(len(BASE_POOL)):
        a=BASE_POOL[(start+j)%len(BASE_POOL)]
        if math.gcd(a,n)==1:return int(a)
    raise AssertionError("No public coprime base available")


def select(pairs,ell):
    groups={"trigger":[],"control":[]}
    for p,q in pairs:
        n=p*q
        if n%ell==0:continue
        group="control" if n%ell==1 else "trigger"
        groups[group].append((p,q))
    ans=[]
    for group in ("trigger","control"):
        values=sorted(groups[group],key=lambda pq:(
            hashed(SELECTION_SALT,ell,group,pq[0]*pq[1]),pq[0]*pq[1]))
        if len(values)<PER_GROUP:
            raise RuntimeError(f"ell {ell} group {group}: only {len(values)}")
        ans.extend((group,int(p),int(q)) for p,q in values[:PER_GROUP])
    assert len(ans)==2*PER_GROUP
    return ans


def nontrivial(g,n):
    return int(g) if 1<int(g)<n and n%g==0 else None


def pollard_p1(n):
    """Fixed public base2 stage-one B31; count modular POW operations exactly."""
    if (f:=nontrivial(math.gcd(2,n),n)) is not None:
        return dict(found=True,factor=f,pow_count=0,prime_power_exponents=[],
                    gcd_calls=1)
    x=2%n
    ops=[]
    for p in dsbase.sieve_primes(CLASSICAL_P1_BOUND):
        pk=p
        while pk*p<=CLASSICAL_P1_BOUND:
            pk*=p
        x=pow(x,pk,n)
        ops.append([int(p),int(pk)])
    f=nontrivial(math.gcd(x-1,n),n)
    return dict(found=f is not None,factor=f,pow_count=len(ops),
                prime_power_exponents=ops,gcd_calls=2)


def common_classical(n,a):
    initial=nontrivial(math.gcd(a,n),n)
    chain=model.power2_chain_shortcut(a,n,max_steps=2*n.bit_length()+2)
    pp=pollard_p1(n)
    if initial is not None:
        kind="gcd"
        result=initial
    elif chain["factor_found"]:
        kind="power2_chain"
        result=int(chain["factor"])
    elif pp["found"]:
        kind="Pollard_p_minus_1_B31"
        result=int(pp["factor"])
    else:
        kind=None
        result=None
    # Retain full precommitted baseline audit even if early step succeeds;
    # effective stopping source records FIRST discovered factor.
    if result is not None:assert n%result==0 and 1<result<n
    return dict(found=result is not None,factor=result,
       found_at=kind,baseline_gcd_factor=initial,
       baseline_power2_chain=chain,pollard_p_minus_1=pp,
       pollard_p_minus_1_B=CLASSICAL_P1_BOUND)


def public_selector(n,a,ell):
    b=pow(a,ell,n)
    return int(b if (n%ell!=1 and b!=a) else a)


def explicit_cf_proper_factor(n,base,y,m,cache):
    """PUBLIC factor extraction from actual CF candidate denominator and gcd."""
    key=(base,m,y)
    if key in cache:return cache[key]
    if y==0:
        cache[key]=False
        return False
    for d in model.convergent_denominators(y,1<<m):
        d=int(d)
        if d<=1 or d>n or (d&1):continue
        if pow(base,d,n)!=1:continue
        x=pow(base,d//2,n)
        if nontrivial(math.gcd(x-1,n),n) is not None or nontrivial(math.gcd(x+1,n),n) is not None:
            cache[key]=True
            return True
    cache[key]=False
    return False


def true_factor_producing_probability(n,base,validation_order,m,cache):
    """Enumerate nearest-bin ideal eigenphases; public CF/GCD verdict."""
    r=int(validation_order)
    if (1<<m)<r:return 0.0
    total=0.0
    for phase_numerator in range(r):
        y,p=model.nearest_bin_and_probability(phase_numerator,r,m)
        if explicit_cf_proper_factor(n,base,y,m,cache):
            total+=p
    return min(1.,max(0.,float(total/r)))


def evaluated_policy(n,base,order,modmul_cache):
    # Mirrors existing model.evaluate_policy, but with *explicit public CF
    # factor extraction*, not "convergent denominator divisible by r".
    stages=model.stage_schedule(n,STAGE_START,STAGE_STEP)
    assert stages[-1]==2*n.bit_length()
    cache={}
    reach=1.
    total=Counter()
    exp_rounds=0.
    exp_shots=0.
    per_stage=[]
    for m in stages:
        p=true_factor_producing_probability(n,base,order,m,cache)
        survival=(1.-p)**STAGE_SHOTS
        exp_exec=reach*model.expected_stage_shots(p,STAGE_SHOTS)
        arith=model.stage_arithmetic_count(n,base,m,modmul_cache)
        overhead=model.architecture_overhead("recycled",m)
        for gate,c in (arith+overhead).items():
            total[gate]+=exp_exec*c
        exp_rounds+=exp_exec*m
        exp_shots+=exp_exec
        per_stage.append(dict(phase_bits=m,success_probability=p,
                              expected_shots_reaching_stage=exp_exec))
        reach*=survival
    success=max(0.,min(1.,1.-reach))
    ccx=float(total.get("ccx",0.))
    return dict(base=base,order_validation_only=order,
       success_probability_by_cap=success,
       expected_phase_rounds=exp_rounds,
       expected_executions=exp_shots,
       expected_arithmetic_ccx_per_attempt=ccx,
       expected_ccx_per_success_with_restarts=(
           ccx/success if success>0 else None),
       success_zero=(success==0),
       quantum_modeled=True,stages=per_stage)


def evaluate_row(group,p,q,ell):
    n=int(p*q)
    a=choose_base(n,ell)
    b=pow(a,ell,n)
    choice=public_selector(n,a,ell)
    assert (choice==b) == (n%ell!=1 and b!=a) or (a==b)
    common=common_classical(n,a)
    # Validation-only factors and hidden multiplicative orders below. No
    # selection/conditional population membership based on this information.
    lam=math.lcm(p-1,q-1)
    order0=model.multiplicative_order_from_lambda(a,n,lam)
    order1=model.multiplicative_order_from_lambda(b,n,lam)
    identity=(order1==order0//math.gcd(order0,ell))
    assert identity
    w0=model.factor_witness(a,order0,n)
    w1=model.factor_witness(b,order1,n)
    b_shortcut=model.power2_chain_shortcut(b,n,max_steps=2*n.bit_length()+2)
    row=dict(N=n,ell=ell,group=group,N_mod_ell=n%ell,
        p_validation_only=p,q_validation_only=q,
        base=a,transformed_base=b,public_selector_base=choice,
        selector_transforms=(choice!=a),
        common_classical=common,
        b_specific_power2_chain_diagnostic=b_shortcut,
        baseline_order_validation_only=order0,
        transformed_order_validation_only=order1,
        order_reduced_validation_only=order1<order0,
        order_identity_ok=identity,
        baseline_half_order_factor_witness_validation_only=w0["factor_success"],
        transformed_half_order_factor_witness_validation_only=w1["factor_success"],
        policies={},no_qpu_job=True)
    if not common["found"]:
        basis={a:order0,b:order1}
        qcost={}
        modeled={}
        for name in POLICIES:
            use={"plain":a,"unconditional":b,"public_selector":choice}[name]
            if use not in modeled:
                modeled[use]=evaluated_policy(n,use,basis[use],qcost)
            # deep-copy object to avoid accidental mutable alias to other methods
            row["policies"][name]=dict(modeled[use])
    assert all(row["policies"].get(k,{}).get("base")==
               {"plain":a,"unconditional":b,"public_selector":choice}[k]
               for k in POLICIES if not common["found"])
    return row


def median(xs):
    v=list(xs)
    return statistics.median(v) if v else None


def summarize(rows):
    assert len(rows)==PER_GROUP
    unresolved=[r for r in rows if not r["common_classical"]["found"]]
    classical=[r for r in rows if r["common_classical"]["found"]]
    out=dict(selected=len(rows),common_classical_factored=len(classical),
      common_classical_unresolved=len(unresolved),
      classical_sources=dict(Counter(r["common_classical"]["found_at"] for r in classical)),
      selector_changes=sum(r["selector_transforms"] for r in rows),
      selector_changes_among_unresolved=sum(r["selector_transforms"] for r in unresolved),
      order_reduced_validation_only_among_unresolved=sum(r["order_reduced_validation_only"] for r in unresolved))
    for pol in POLICIES:
        costs=[r["policies"][pol] for r in unresolved]
        success=[x["success_probability_by_cap"] for x in costs]
        out[pol]=dict(remaining_rows=len(costs),
            capable=sum(p>0 for p in success),
            zero_success=sum(p==0 for p in success),
            mean_success_probability=(statistics.mean(success) if success else None),
            median_success_probability=median(success),
            sum_expected_ccx_attempted=sum(x["expected_arithmetic_ccx_per_attempt"] for x in costs),
            median_ccx_attempted=median(x["expected_arithmetic_ccx_per_attempt"] for x in costs))
    pairs=[]
    both=[]
    for r in unresolved:
        x=r["policies"]["plain"]
        y=r["policies"]["public_selector"]
        pb=x["success_probability_by_cap"]
        ps=y["success_probability_by_cap"]
        if pb>0 and ps>0:
            xb=x["expected_ccx_per_success_with_restarts"]
            ys=y["expected_ccx_per_success_with_restarts"]
            ratio=ys/xb if xb else None
            if ratio is not None:
                both.append((xb,ys))
                pairs.append(ratio)
    eps=1e-10
    out["comparison_selector_vs_plain"]=dict(
        both_positive_success_count=len(both),
        either_zero_success_count=len(unresolved)-len(both),
        improved=sum(x<1.-eps for x in pairs),
        tied=sum(abs(x-1.)<=eps for x in pairs),
        worsened=sum(x>1.+eps for x in pairs),
        median_per_row_CCX_per_success_ratio=median(pairs),
        aggregate_CCX_per_success_T_over_B=(
            sum(y for x,y in both)/sum(x for x,y in both)
            if both and sum(x for x,y in both) else None),
        selector_success_coverage_at_least_plain=(
          out["public_selector"]["capable"]>=out["plain"]["capable"]),
        aggregate_ccx_attempted_ratio=(
           out["public_selector"]["sum_expected_ccx_attempted"]/
           out["plain"]["sum_expected_ccx_attempted"]
           if out["plain"]["sum_expected_ccx_attempted"] else None),
        primary_criterion_pass=None)
    c=out["comparison_selector_vs_plain"]
    c["primary_criterion_pass"]=bool(
      c["both_positive_success_count"]>0
      and c["selector_success_coverage_at_least_plain"]
      and c["aggregate_CCX_per_success_T_over_B"]<1.
      and c["improved"]>c["worsened"]
      and c["improved"]>c["both_positive_success_count"]/2.)
    return out


def selftests():
    # Public CF verifier recovers a nontrivial factor of 15 from a true order-4
    # denominator 4 (y/2^m=1/4) but not denominator 8 (x == 1).
    n,base=15,2
    assert explicit_cf_proper_factor(n,base,1,2,{}) is True
    assert explicit_cf_proper_factor(n,base,2,4,{}) is False
    assert math.gcd(2,n)==1
    assert pollard_p1(15)["pow_count"]==len(dsbase.sieve_primes(31))
    assert public_selector(22,3,3)==pow(3,3,22)
    for ell in ELLS:
        for n0 in (137*1009,107*1901):
            if n0%ell:
                expected=2 if n0%ell==1 else pow(2,ell,n0)
                assert public_selector(n0,2,ell)==expected
    return dict(selftest=True,public_CF_GCD_checks=True,public_selector_no_order_oracle=True,
                classical_B31_fixed=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ell",type=int,choices=ELLS,required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    ell=args.ell
    result=dict(experiment="dark_star_public_selector_n18_v1",
      revision=REV,ell=ell,utc_timestamp=datetime.now(timezone.utc).isoformat(),
      preregistration="docs/DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_PREREG.md",
      selection_salt=SELECTION_SALT,base_salt=BASE_SALT,
      population=dict(n_min=N_MIN,n_max=N_MAX,
            p_q_min=11,per_group=PER_GROUP,groups=("trigger","control")),
      stage_policy=dict(start_bits=STAGE_START,step_bits=STAGE_STEP,shots=STAGE_SHOTS,
           nearest_bin_only_ideal_QPE=True,
           explicitly_verified_CF_and_factor_GCD=True),
      common_classical=dict(pollard_stage_one_bound=CLASSICAL_P1_BOUND,
         baseline_power2_chain_cap_formula="2*bit_length(N)+2"),
      zero_QPU=True,qpu_jobs_submitted=0,
      selftests=selftests(),rows=[],summaries={},violations=[],
      claim_boundary="ideal nearest-bin QPE & generic logical CCX; not real quantum speedup or actual RSA-scale attack")
    all_pairs=pairs_for_range()
    chosen=select(all_pairs,ell)
    print(f"ell={ell}: preregistered {len(chosen)} rows in n18 range",flush=True)
    for i,(group,p,q) in enumerate(chosen,1):
        row=evaluate_row(group,p,q,ell)
        result["rows"].append(row)
        print(f"  [{i:02d}/{len(chosen)}] {group} N={row['N']} "
              f"classical={row['common_classical']['found']} "
              f"selector={'transform' if row['selector_transforms'] else 'plain'} "
              f"orders={row['baseline_order_validation_only']}"
              f"->{row['transformed_order_validation_only']}",flush=True)
        assert row["order_identity_ok"]
    for group in ("trigger","control"):
        group_rows=[r for r in result["rows"] if r["group"]==group]
        result["summaries"][group]=summarize(group_rows)
    width=model.arithmetic_width(result["rows"][0]["N"])
    cap=2*result["rows"][0]["N"].bit_length()
    result["logical_width"]=dict(workspace=width["arithmetic_qubits_excluding_phase"],
      wide_peak=width["arithmetic_qubits_excluding_phase"]+cap,
      recycled_peak=width["recycled_logical_qubits"])
    assert len(result["rows"])==2*PER_GROUP
    assert not result["violations"]
    out=args.out or (DEFAULT_DIR/f"dark_star_public_selector_n18_ell{ell}.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("\n===== PUBLIC SELECTOR LARGER HOLDOUT =====",flush=True)
    for group,info in result["summaries"].items():
        c=info["comparison_selector_vs_plain"]
        print(f"ell={ell} {group} selected={info['selected']} "
              f"classical_factored={info['common_classical_factored']} "
              f"quantum_unresolved={info['common_classical_unresolved']} "
              f"selector_changes={info['selector_changes_among_unresolved']} "
              f"success_plain/selector={info['plain']['capable']}/{info['public_selector']['capable']} "
              f"both_success={c['both_positive_success_count']} "
              f"improve/tie/worsen={c['improved']}/{c['tied']}/{c['worsened']} "
              f"cost_per_success_T/B={c['aggregate_CCX_per_success_T_over_B']} "
              f"primary_pass={c['primary_criterion_pass']}",flush=True)
    print("zero QPU jobs; wrote",out,flush=True)


if __name__=="__main__":
    main()
