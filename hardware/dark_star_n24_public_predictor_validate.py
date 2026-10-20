#!/usr/bin/env python3
"""Evaluate PRECOMMITTED 16 independent N24 public predictor cases only.

No labels, orders or prime factorization were used to select new N/a.
First publicly factor all via B47/rho/trial, then validate two public
predictors against exact order reduction AND original half-order Shor
factor witness; explicitly prove cubing cannot change that witness.
No QPE/abstract gate costs, no Qiskit, no IBM/QPU jobs or runtime.
Research lead Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

import dark_star_n24_public_predictor_manifest as public
import dark_star_n22_selector_vs_cube as classical
import dark_star_recycled_scalable_arithmetic_audit as model

ROOT=Path("results/dark_star_ptp")
MANIFEST=ROOT/"dark_star_n24_public_predictor_manifest.json"
DEST=ROOT/"dark_star_n24_public_predictor_validation.json"
FROZEN_SHA="d20a59ede42509cb3fd85ce5c6e1a61bd5edb70621964ebbd3ddea5d6ea2b889"
FROZEN_PREREG="docs/DARK_STAR_N24_PUBLIC_PREDICTOR_PREREG.md"


def check_manifest():
    d=json.loads(MANIFEST.read_text())
    rows=d["selected_public_rows"]
    assert d["selected_sha256"]==FROZEN_SHA
    assert hashlib.sha256(public.canonical(rows).encode()).hexdigest()==FROZEN_SHA
    assert d["preregistered_document"]==FROZEN_PREREG
    assert d["no_QPU"] and d["qpu_jobs_submitted"]==0
    assert d["no_validation_factors_or_orders"] and d["labels_not_evaluated_or_used_for_selection"]
    assert d["prime_construction_range"]==[2000,6000]
    assert d["interval"]==[1<<23,1<<24]
    assert len(rows)==16 and len({z["N"] for z in rows})==16
    assert d["selection_salt"]==public.SALT and d["base_salt"]==public.BASE_SALT
    for group,mod in public.GROUPS:
        group_rows=[z for z in rows if z["group"]==group]
        assert len(group_rows)==8
        for z in group_rows:
            n=z["N"];a=z["base"];b=z["public_cube"]
            assert (1<<23)<=n<(1<<24) and n%3==mod
            assert math.gcd(n,a)==1 and b==pow(a,3,n)
            assert a==public.public_base(n,group)
            assert z["jacobi_symbol"]==public.jacobi(a,n) in (-1,1)
            assert z["P1_mod3_1_predict_positive"]==(mod==1)
            assert z["P2_public_bitweight_proxy"]==public.public_costs(n,a)
            source=next(r for r in d["public_screenings"][group] if r["N"]==n)
            assert source["rank"]==z["rank"] and source["base"]==a
            assert not source["public_B31_factored"]
    return d


def witness(base,order,n):
    result=model.factor_witness(base,order,n)
    assert result["factor_success"]==bool(result["factors"])
    if result["factor_success"]:
        assert result["x"] is not None and result["x"]%n not in (1,n-1)
        for p,q in result["factors"]:
            assert p*q==n and 1<p<n and 1<q<n
    return result


def score_case(row):
    t0=time.process_time()
    n=int(row["N"]);a=int(row["base"]);b=int(row["public_cube"])
    # Only public classical recovery, explicitly before validation order.
    cascade=classical.public_additional_classical(n)
    assert cascade["classically_factored"]
    factor=int(cascade["factor"])
    assert 1<factor<n and n%factor==0
    p,q=sorted((factor,n//factor))
    assert 2000<=p<q<=6000
    # Independent primality validation, tiny public frame; NOT selection.
    for z in (p,q):
        assert all(z%d!=0 for d in range(2,math.isqrt(z)+1)),z
    lam=math.lcm(p-1,q-1)
    r=model.multiplicative_order_from_lambda(a,n,lam)
    r3=model.multiplicative_order_from_lambda(b,n,lam)
    assert 1<r<=lam and 1<=r3<=r
    assert pow(a,r,n)==1 and pow(b,r3,n)==1
    assert r3==r//math.gcd(r,3),(n,a,r,r3)
    # Independent minimality check for both true orders.
    for base,order in ((a,r),(b,r3)):
        for z in model.factor_int(order):
            assert pow(base,order//z,n)!=1,(n,base,order,z)
    wa=witness(a,r,n);wb=witness(b,r3,n)
    assert bool(wa["factor_success"])==bool(wb["factor_success"]),(
       "odd-cube must preserve factor witness capability",n,a)
    assert wa["factors"]==wb["factors"],("different proper witnesses",n,a)
    if r%2==0:
        assert r3%2==0
        assert wa["x"]==wb["x"]==pow(a,r//2,n)==pow(b,r3//2,n)
    else:
        assert r3%2==1 and wa["x"] is wb["x"] is None
    shrunk=(r3*3==r)
    target=bool(shrunk and wa["factor_success"])
    assert target==(r%3==0 and wa["factor_success"])
    prediction1=bool(row["P1_mod3_1_predict_positive"])
    prediction2=bool(row["P2_public_bitweight_proxy"]["P2_source_proxy_predict_positive"])
    result=dict(**row,
      public_post_B31_classical=cascade,
      validation_only=dict(
          factors=[p,q],lambda_N=lam,
          order_plain=r,order_cube=r3,
          order_cube_identity_verified=True,
          shrunk_by_exact_factor_three=shrunk,
          plain_witness=wa,cube_witness=wb,
          exact_cube_half_order_witness_invariance_verified=True),
      label_T_shrunk_and_factor_witness=target,
      P1_correct=(prediction1==target),
      P2_correct=(prediction2==target),
      public_post_B31_CPU_ms=cascade["total_public_classical_CPU_ms"],
      validation_CPU_ms=round((time.process_time()-t0)*1000,4),
      zero_QPU=True)
    print("VALIDATED",row["group"],"N",n,"base",a,
          "r",r,"r3",r3,"factor_witness",wa["factor_success"],
          "T",target,"P1",prediction1,"P2",prediction2,
          "classical_source",cascade["first_factor_source"],
          "invariance OK; ZERO QPU",flush=True)
    return result


def confusion(rows,key):
    tp=sum(bool(z[key]) and z["label_T_shrunk_and_factor_witness"] for z in rows)
    fp=sum(bool(z[key]) and not z["label_T_shrunk_and_factor_witness"] for z in rows)
    fn=sum(not bool(z[key]) and z["label_T_shrunk_and_factor_witness"] for z in rows)
    tn=sum(not bool(z[key]) and not z["label_T_shrunk_and_factor_witness"] for z in rows)
    assert tp+fp+fn+tn==len(rows)
    positive=tp+fn
    negative=fp+tn
    bal=(.5*(tp/positive+tn/negative)) if positive and negative else None
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,
          positive_labels=positive,negative_labels=negative,
          sensitivity=(tp/positive if positive else None),
          specificity=(tn/negative if negative else None),
          accuracy=(tp+tn)/len(rows),balanced_accuracy=bal)


def exact_enrichment_tail(N,K,n,at_least):
    """One-sided Fisher hypergeometric tail for fixed group size, descriptive."""
    den=math.comb(N,n)
    return sum(math.comb(K,x)*math.comb(N-K,n-x)
       for x in range(at_least,min(n,K)+1)
       if 0<=n-x<=N-K)/den


def main():
    manifest=check_manifest()
    sha=manifest["selected_sha256"]
    print("FROZEN PUBLIC N24 MANIFEST CHECKED BEFORE VALIDATION",sha,flush=True)
    results=[score_case(z) for z in manifest["selected_public_rows"]]
    assert len(results)==16
    assert all(z["validation_only"]["exact_cube_half_order_witness_invariance_verified"]
               for z in results)
    group_summary={}
    for group,mod in public.GROUPS:
        group_rows=[x for x in results if x["group"]==group]
        assert len(group_rows)==8
        positives=sum(z["label_T_shrunk_and_factor_witness"] for z in group_rows)
        shrunk=sum(z["validation_only"]["shrunk_by_exact_factor_three"] for z in group_rows)
        witness=sum(z["validation_only"]["plain_witness"]["factor_success"] for z in group_rows)
        group_summary[group]=dict(n=8,target_T_positive=positives,
          order_shrinks_by_3=shrunk,plain_and_cube_good_witness=witness,
          first_classical_sources=dict(Counter(z["public_post_B31_classical"]["first_factor_source"]
                         for z in group_rows)))
    g1=group_summary["G1_mod3_1"]["target_T_positive"]
    g2=group_summary["G2_mod3_2"]["target_T_positive"]
    criterion=(g1>=6 and g2<=2)
    p1=confusion(results,"P1_mod3_1_predict_positive")
    # P2 is nested under already frozen public bitweight proxy.
    with_p2=[{**z,"P2_binary":z["P2_public_bitweight_proxy"]["P2_source_proxy_predict_positive"]}
             for z in results]
    p2=confusion(with_p2,"P2_binary")
    jc={}
    for sym in (-1,1):
        cases=[z for z in results if z["jacobi_symbol"]==sym]
        jc[str(sym)]=dict(n=len(cases),
           original_witness_capable=sum(z["validation_only"]["plain_witness"]["factor_success"] for z in cases),
           T_positive=sum(z["label_T_shrunk_and_factor_witness"] for z in cases))
    total_positive=g1+g2
    tail=exact_enrichment_tail(16,total_positive,8,g1)
    summary=dict(
        predeclared_P1_group_mod3_1_target_positive=g1,
        predeclared_P1_group_mod3_2_target_positive=g2,
        predeclared_P1_thresholds=dict(g1_min_positive=6,g2_max_positive=2),
        predeclared_P1_gate_pass=criterion,
        P1_confusion=p1,P2_public_bitweight_confusion=p2,
        always_negative_accuracy=(16-total_positive)/16,
        exact_one_sided_enrichment_hypergeom_p_descriptive=tail,
        jacobi_descriptive=jc,
        group_results=group_summary,
        all_16_prelabel_manifest_sha_matched=True,
        all_16_classically_factored_by_public_algorithm=True,
        all_16_odd_cube_factor_witness_invariant=True,
        zero_QPU=True,qpu_jobs_submitted=0,
        inference_caveat="16 balanced selected B31 survivors, classically factored; P1 posthoc from N23 controls, no QPE probabilities or hardware, P2 descriptive only")
    out=dict(
        experiment="n24_public_only_reversal_predictor_vs_full_exact_order_witness_labels",
        preregistered_document=FROZEN_PREREG,
        research_lead="Chase Lunsford / CaMaLabs",
        completed_utc=datetime.now(timezone.utc).isoformat(),
        source_public_manifest_sha256=sha,
        source_public_manifest_commit="6a3eb458d63c15b57468ceafadae6c94ebe5c260",
        immutable_population=manifest["interval"],
        source_public_frame_prime_construction=manifest["prime_construction_range"],
        exact_algebra_not_a_novel_theorem=True,
        QPE_not_scored=True,
        native_backend_not_read=True,
        no_QPU=True,qpu_jobs_submitted=0,free_runtime_used=False,paid_runtime_used=False,
        summary=summary,rows=results,
        original_public_screenings=manifest["public_screenings"])
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(out,indent=2)+"\n")
    print("FINAL N24 P1 INVERTED MOD3",g1,"/8 vs",g2,"/8",
          "PREDECLARED GATE",criterion,"P1",p1,"P2",p2,
          "FISHER TAIL",tail,
          "CUBING WITNESS INVARIANT 16/16, classical factor 16/16, NO QPU",flush=True)


if __name__=="__main__":
    main()
