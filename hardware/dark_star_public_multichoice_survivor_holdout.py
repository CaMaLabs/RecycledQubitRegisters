#!/usr/bin/env python3
"""Pre-registered public multi-exponent Dark Star selector with classical survivors.

Only classically-public data determine which candidate N/base survives, and
which exponent policy is chosen. Synthetic private factors/orders appear ONLY
in the validation/ideal-QPE simulation AFTER public population selection.
Research lead and originating direction: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

import dark_star_ptp_shor_audit as ds
import dark_star_recycled_scalable_arithmetic_audit as model
import dark_star_public_selector_larger_holdout as old

REV="2026-10-14-multichoice-classical-survivor-v1"
SALT="QRR-public-multichoice-survivors-v1-20261014"
BASE_SALT="QRR-public-multichoice-base-v1-20261014"
RANDOM_SALT="QRR-public-multichoice-random-v1-20261014"
COHORTS=("replication","holdout")
GROUPS=("trigger","control")
EXPS=(0,3,5,7)
POLICIES=("plain","always3","ladder","cheap4","random4")
TARGET=10
MAX_SCAN=1500
OLD_FILES=tuple(Path("results/dark_star_ptp")/
                f"dark_star_public_selector_n18_ell{e}.json" for e in (3,5,7))
DEFAULT=Path("results/dark_star_ptp")


def digest(salt,*parts):
    return int.from_bytes(hashlib.sha256("|".join(
      (salt,*(str(x) for x in parts))).encode("utf8")).digest(),"big")


def previous_ns():
    values=set()
    for path in OLD_FILES:
        data=json.loads(path.read_text())
        assert len(data["rows"])==40,(path,len(data["rows"]))
        values.update(int(r["N"]) for r in data["rows"])
    return values


def candidates(pairs,group,excluded):
    vals=[(p*q,p,q) for p,q in pairs if
        ((p*q)%3!=1 if group=="trigger" else (p*q)%3==1)
        and (p*q)%3!=0 and (p*q) not in excluded]
    return vals


def public_base(n,cohort,group):
    idx=digest(BASE_SALT,cohort,group,n)%len(old.BASE_POOL)
    for j in range(len(old.BASE_POOL)):
        a=int(old.BASE_POOL[(idx+j)%len(old.BASE_POOL)])
        if math.gcd(a,n)==1:return a
    raise RuntimeError("No public coprime base")


def pminusone(n,bound=31):
    """Count actual executed operations; public stage-one from base2 only."""
    g=math.gcd(2,n)
    if (factor:=old.nontrivial(g,n)) is not None:
        return dict(found=True,factor=factor,bound=bound,modular_pow_calls=0,
                    gcd_calls=1,prime_power_exponents=[])
    x=2%n
    ops=[]
    for p in ds.sieve_primes(bound):
        pk=p
        while pk*p<=bound:pk*=p
        x=pow(x,pk,n)
        ops.append(int(pk))
    factor=old.nontrivial(math.gcd(x-1,n),n)
    return dict(found=(factor is not None),factor=factor,bound=bound,
                modular_pow_calls=len(ops),gcd_calls=2,
                prime_power_exponents=ops)


def classical_cascade(n,a):
    g=old.nontrivial(math.gcd(a,n),n)
    counts=dict(gcd_calls=1,modular_square_calls=0,pminusone_modular_pow_calls=0,
                executed_pminusone=False)
    if g is not None:
        return dict(found=True,factor=g,source="gcd_base",counts=counts)
    x=a%n
    limit=2*n.bit_length()+2
    for k in range(limit+1):
        gm=old.nontrivial(math.gcd(x-1,n),n)
        gp=old.nontrivial(math.gcd(x+1,n),n)
        counts["gcd_calls"]+=2
        if gm is not None or gp is not None:
            g=gm if gm is not None else gp
            assert 1<g<n and n%g==0
            return dict(found=True,factor=g,source="power2_chain",
                        power_step=k,counts=counts)
        if x==1:break
        x=(x*x)%n
        counts["modular_square_calls"]+=1
    p1=pminusone(n,31)
    counts["executed_pminusone"]=True
    counts["gcd_calls"]+=p1["gcd_calls"]
    counts["pminusone_modular_pow_calls"]+=p1["modular_pow_calls"]
    if p1["found"]:
        assert n%int(p1["factor"])==0
        return dict(found=True,factor=int(p1["factor"]),source="Pollard_p1_B31",
                    counts=counts)
    return dict(found=False,factor=None,source=None,counts=counts)


def ranked_public_survivors(pairs,group,cohort,old_exclusions,reserved=None):
    ex=set(old_exclusions)
    if reserved:ex.update(reserved)
    pool=candidates(pairs,group,ex)
    ranked=sorted(pool,key=lambda row:(digest(SALT,cohort,group,row[0]),row[0]))
    screened=[]
    selected=[]
    for n,p,q in ranked:
        if len(screened)>=MAX_SCAN:break
        a=public_base(n,cohort,group)
        x=classical_cascade(n,a)
        receipt=dict(N=int(n),base=a,rank_index=len(screened)+1,
           public_classical_found=x["found"],
           classical_factor_source=x["source"],
           public_operation_counts=x["counts"])
        screened.append(receipt)
        if not x["found"]:
            # The public classical procedure, not the hidden prime factors,
            # determines whether this synthetic semiprime joins the cohort.
            assert p*q==n
            selected.append((n,p,q,a,len(screened)))
            if len(selected)==TARGET:break
    assert len(selected)==TARGET,(cohort,group,len(selected),len(screened))
    return screened,selected


def choose_public_policies(n,a,cohort,group,costs):
    powers={0:a,3:pow(a,3,n),5:pow(a,5,n),7:pow(a,7,n)}
    ell=next((e for e in (3,5,7) if n%e not in (0,1)),0)
    cheap=min(EXPS,key=lambda e:(costs[e],EXPS.index(e)))
    random_exp=EXPS[digest(RANDOM_SALT,cohort,group,n)%len(EXPS)]
    choices=dict(plain=0,always3=3,ladder=ell,cheap4=cheap,random4=random_exp)
    assert set(choices)==set(POLICIES)
    return powers,choices


def score_row(n,p,q,a,scan_index,cohort,group):
    lam=math.lcm(p-1,q-1)  # VALIDATION ONLY, never used to choose policy.
    powers={e:(a if e==0 else pow(a,e,n)) for e in EXPS}
    cheap_cache={}
    proxy={e:int(model.stage_arithmetic_count(n,powers[e],4,cheap_cache).get("ccx",0))
           for e in EXPS}
    values,choices=choose_public_policies(n,a,cohort,group,proxy)
    assert powers==values
    base_orders={}
    modmul_cache={}
    model_by_base={}
    order0=model.multiplicative_order_from_lambda(a,n,lam)
    for e,base in powers.items():
        if base not in base_orders:
            order=model.multiplicative_order_from_lambda(base,n,lam)
            base_orders[base]=order
            assert order==order0//math.gcd(order0,e) if e else order==order0
        order=base_orders[base]
        if base not in model_by_base:
            model_by_base[base]=old.evaluated_policy(n,base,order,modmul_cache)
    policies={}
    for name,e in choices.items():
        v=model_by_base[powers[e]]
        policies[name]=dict(exponent=e,selected_base=powers[e],
           model_success_probability=float(v["success_probability_by_cap"]),
           expected_ccx_attempted=float(v["expected_arithmetic_ccx_per_attempt"]),
           expected_ccx_per_success=v["expected_ccx_per_success_with_restarts"],
           expected_phase_rounds=float(v["expected_phase_rounds"]),
           zero_success=(float(v["success_probability_by_cap"])==0))
    oracle_choices=[e for e in EXPS if
        model_by_base[powers[e]]["expected_ccx_per_success_with_restarts"] is not None]
    oracle_e=min(oracle_choices,key=lambda e:(
          model_by_base[powers[e]]["expected_ccx_per_success_with_restarts"],e)
        ) if oracle_choices else None
    diagnostic_p47=pminusone(n,47)
    return dict(N=n,cohort=cohort,group=group,rank_index=scan_index,
       base=a,p_validation_only=p,q_validation_only=q,
       valid_semiprime=p*q==n,
       public_candidate_bases={str(e):powers[e] for e in EXPS},
       cheap4_CCX_proxy_by_exponent={str(e):proxy[e] for e in EXPS},
       choice_exponents=choices,
       transformed_order_validation_only={str(e):base_orders[powers[e]] for e in EXPS},
       true_order_identity_verified=all(
          base_orders[powers[e]]==order0//math.gcd(order0,e)
          for e in (3,5,7)),
       policies=policies,
       B47_public_classical_diagnostic=dict(found=diagnostic_p47["found"],
            source="Pollard_p1_B47",modular_pow_calls=diagnostic_p47["modular_pow_calls"]),
       oracle_best_exponent_validation_only=oracle_e,
       oracle_best_CCX_per_success_validation_only=(
          model_by_base[powers[oracle_e]]["expected_ccx_per_success_with_restarts"]
          if oracle_e is not None else None))


def exact_sign(w,l):
    t=w+l
    if not t:return 1.
    return min(1.,2.*sum(math.comb(t,i) for i in range(min(w,l)+1))/2**t)


def compare(rows,name,ref):
    both=[]
    pairs=[]
    losses=0
    gains=0
    ties=0
    for r in rows:
        a=r["policies"][name]["expected_ccx_per_success"]
        b=r["policies"][ref]["expected_ccx_per_success"]
        if a is None or b is None:continue
        both.append((a,b))
        rel=a/b
        pairs.append(rel)
        if rel<1-1e-10:gains+=1
        elif rel>1+1e-10:losses+=1
        else:ties+=1
    covered_name=sum(r["policies"][name]["model_success_probability"]>0 for r in rows)
    covered_ref=sum(r["policies"][ref]["model_success_probability"]>0 for r in rows)
    return dict(complete_rows=len(rows),both_success=len(both),
      either_zero_success=len(rows)-len(both),
      coverage_method=covered_name,coverage_comparator=covered_ref,
      coverage_non_decreased=covered_name>=covered_ref,
      improved=gains,tied=ties,worsened=losses,
      exact_unadjusted_two_sided_sign_p=exact_sign(gains,losses),
      aggregate_sum_cost_per_success_ratio=(
         sum(a for a,b in both)/sum(b for a,b in both) if both else None),
      median_paired_cost_per_success_ratio=(
         __import__("statistics").median(pairs) if pairs else None))


def summarize(rows,screen):
    assert len(rows)==TARGET
    classical_counts=Counter(s["classical_factor_source"] for s in screen
                             if s["public_classical_found"])
    result=dict(selected_survivors=len(rows),screened_public_candidates=len(screen),
        classical_factored_in_scan=sum(s["public_classical_found"] for s in screen),
        public_factor_sources=dict(classical_counts),
        B47_classically_factorable_among_selected=sum(r["B47_public_classical_diagnostic"]["found"] for r in rows),
        selected_exponents_by_policy={name:dict(Counter(
            str(r["choice_exponents"][name]) for r in rows)) for name in POLICIES},
        true_order_reduction_count_by_policy={name:sum(
            r["transformed_order_validation_only"][str(r["choice_exponents"][name])]
            <r["transformed_order_validation_only"]["0"] for r in rows)
            for name in POLICIES},
        policies={})
    for name in POLICIES:
        result["policies"][name]=dict(factor_capable=sum(
            r["policies"][name]["model_success_probability"]>0 for r in rows),
            mean_factor_success_probability=sum(
            r["policies"][name]["model_success_probability"] for r in rows)/len(rows),
            total_expected_CCX_per_attempt=sum(
            r["policies"][name]["expected_ccx_attempted"] for r in rows))
    result["comparisons"]={f"{name}_vs_{ref}":compare(rows,name,ref) for name,ref in
        (("ladder","plain"),("ladder","always3"),("ladder","random4"),
         ("cheap4","plain"),("cheap4","random4"),("always3","plain"),
         ("random4","plain"))}
    return result


def selftests():
    assert exact_sign(7,1)==0.0703125
    assert exact_sign(4,3)==1.
    assert old.explicit_cf_proper_factor(15,2,1,2,{})
    assert not old.explicit_cf_proper_factor(15,2,2,4,{})
    assert public_base(143131,"replication","trigger") in old.BASE_POOL
    for n in (15*17,11*31,71*73):
        for a in (2,3):
            if math.gcd(a,n)==1:
                c=classical_cascade(n,a)
                assert not c["found"] or (1<c["factor"]<n and n%c["factor"]==0)
    return dict(public_and_CF_selftest=True,frozen_policy_decision_public_only=True)


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--cohort",choices=COHORTS,required=True)
    arg.add_argument("--group",choices=GROUPS,required=True)
    arg.add_argument("--out",type=Path)
    args=arg.parse_args()
    # Prior research IDs come from file N only; no previous outcomes read.
    old_ids=previous_ns()
    pairs=old.pairs_for_range()
    # Exclude replication-selected N from holdout without depending on another
    # concurrent job or on any validation order/resource result.
    reserved=set()
    if args.cohort=="holdout":
        for g in GROUPS:
            _,xs=ranked_public_survivors(pairs,g,"replication",old_ids)
            reserved.update(n for n,p,q,a,idx in xs)
    screened,selected=ranked_public_survivors(
        pairs,args.group,args.cohort,old_ids,reserved)
    assert len(selected)==TARGET
    result=dict(experiment="dark_star_public_multichoice_survivor_holdout_v1",
       revision=REV, timestamp_utc=datetime.now(timezone.utc).isoformat(),
       preregistration="docs/DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_PREREG.md",
       selection_salt=SALT,base_salt=BASE_SALT,random_salt=RANDOM_SALT,
       cohort=args.cohort,group=args.group,
       policies=list(POLICIES),exponents=list(EXPS),
       zero_QPU=True,qpu_jobs_submitted=0,
       classical_screened=screened,
       selftests=selftests(),rows=[],summary=None,
       claim_boundary="conditional public B31 survivor sample of toy 18bit N; ideal nearest-bin factor-producing CF and logical CCX; not hardware/runtime/physical resource or RSA-scale factoring")
    width=model.arithmetic_width(selected[0][0])
    result["logical_width"]=dict(arithmetic_workspace=width["arithmetic_qubits_excluding_phase"],
       wide_peak=width["arithmetic_qubits_excluding_phase"]+36,
       recycled_peak=width["recycled_logical_qubits"])
    for i,(n,p,q,a,rank_index) in enumerate(selected,1):
        item=score_row(n,p,q,a,rank_index,args.cohort,args.group)
        result["rows"].append(item)
        print(f"  [{i:02d}/{TARGET}] cohort={args.cohort} group={args.group} "
              f"N={n} order_plain={item['transformed_order_validation_only']['0']} "
              f"ladder={item['choice_exponents']['ladder']} "
              f"cheap4={item['choice_exponents']['cheap4']}",flush=True)
        assert item["true_order_identity_verified"]
    result["summary"]=summarize(result["rows"],screened)
    assert len(result["rows"])==TARGET
    assert not any(s["N"] in old_ids for s in screened)
    assert all(not s["public_classical_found"] for s in screened if
               s["N"] in {r["N"] for r in result["rows"]})
    output=args.out or DEFAULT/f"dark_star_public_multichoice_{args.cohort}_{args.group}.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("===== MULTICHOICE SURVIVOR HOLDOUT =====")
    for comparison,data in result["summary"]["comparisons"].items():
        print(f"{comparison}: both={data['both_success']} "
              f"coverage={data['coverage_method']}/{data['coverage_comparator']} "
              f"improve/tie/worse={data['improved']}/{data['tied']}/{data['worsened']} "
              f"CCX_success_ratio={data['aggregate_sum_cost_per_success_ratio']}",
              flush=True)
    print(f"public_scan={len(screened)} public_B31_factored={result['summary']['classical_factored_in_scan']} "
          f"selected={len(result['rows'])} B47_still_classical={result['summary']['B47_classically_factorable_among_selected']} "
          f"width={result['logical_width']} NO QPU JOB SUBMITTED.",flush=True)
    print("wrote",output,flush=True)


if __name__=="__main__":
    main()
