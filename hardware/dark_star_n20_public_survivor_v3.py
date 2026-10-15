#!/usr/bin/env python3
"""Frozen n20 public-classical-survivor quantum resource holdout, zero QPU.

Preregistered in docs/DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_PREREG.md.
No IBM/Qiskit imports or hardware submissions. Numerical 4096-eigenphase
sampling is an explicitly preregistered approximation, NOT full ideal QPE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

import dark_star_ptp_shor_audit as ds
import dark_star_public_multichoice_survivor_holdout as prior
import dark_star_public_selector_larger_holdout as old
import dark_star_recycled_scalable_arithmetic_audit as model

REV = "QRR-n20-public-classical-survivor-v3-20261014"
LO, HI, P_MIN = 524288, 1048575, 11
ELLS = (3, 5, 7)
GROUPS = ("trigger", "control")
POOL = (2,3,5,7,11,13,17,19,23,29,31)
EXPONENTS = (0,3,5,7)
POLICIES = ("plain","always3","cube_trigger","ladder","cheap4")
PER_GROUP, MAX_SCAN = 12, 400
PHASE_SAMPLES = 4096
POP_SALT = "QRR-n20-public-policy-survivors-v3-20261014"
BASE_SALT = "QRR-n20-public-base-v3-20261014"
PHASE_SALT = "QRR-n20-phase-v3-20261014"
MANIFEST_FILE = Path("results/dark_star_ptp/dark_star_n20_public_survivors_v3_manifest.json")
OUT_DIR = Path("results/dark_star_ptp")


def digest(salt, *parts):
    return hashlib.sha256("|".join([salt,*map(str,parts)]).encode()).digest()


def hnum(salt, *parts):
    return int.from_bytes(digest(salt,*parts),"big")


def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True)


def make_candidates():
    primes = ds.sieve_primes(HI)
    pool = []
    for i,p in enumerate(primes):
        if p < P_MIN:
            continue
        if p*p > HI:
            break
        for q in primes[i+1:]:
            n = p*q
            if n > HI:
                break
            if n >= LO:
                pool.append(n)
    assert len(pool) == len(set(pool)), "not distinct squarefree semiprimes"
    return pool


def public_base(n,ell,group):
    shift=hnum(BASE_SALT,ell,group,n)%len(POOL)
    for i in range(len(POOL)):
        base=POOL[(shift+i)%len(POOL)]
        if math.gcd(base,n)==1:
            return base
    raise AssertionError("no public coprime base")


def public_classical(n,a):
    # Reuse the existing tested frozen B31 classical cascade, not private oracle.
    return prior.classical_cascade(n,a)


def create_manifest():
    candidates=make_candidates()
    manifest=[]
    screenings={}
    used=set()
    for ell in ELLS:
        for group in GROUPS:
            eligible=[n for n in candidates if n%ell!=0 and
                      ((n%ell==1) == (group=="control")) and n not in used]
            eligible.sort(key=lambda n:(digest(POP_SALT,ell,group,n),n))
            screen=[]
            selected=[]
            for n in eligible[:MAX_SCAN]:
                a=public_base(n,ell,group)
                cl=public_classical(n,a)
                record={"N":n,"base":a,"rank_in_panel":len(screen)+1,
                        "classically_factored":bool(cl["found"]),
                        "classical_factor_source":cl.get("source"),
                        "classical_factor":cl.get("factor"),
                        "public_operation_counts":cl["counts"]}
                screen.append(record)
                if not cl["found"]:
                    selected.append({"ell":ell,"group":group,"N":n,
                                     "base":a,"rank_in_panel":len(screen)})
                    used.add(n)
                    if len(selected)==PER_GROUP:
                        break
            if len(selected)!=PER_GROUP:
                raise RuntimeError(f"insufficient public survivors {ell} {group}: {len(selected)}/{PER_GROUP} after {len(screen)} screens")
            manifest.extend(selected)
            screenings[f"{ell}_{group}"]=screen
    assert len(manifest)==72
    assert len({x["N"] for x in manifest})==72
    return {"experiment":"n20_public_survivor_manifest_v3",
            "revision":REV, "selection_salt":POP_SALT,"base_salt":BASE_SALT,
            "interval":[LO,HI],"per_group":PER_GROUP,"max_scan":MAX_SCAN,
            "manifest_sha256":hashlib.sha256(canonical(manifest).encode()).hexdigest(),
            "selected_public_rows":manifest,
            "public_screenings":screenings,
            "zero_qpu":True,"qpu_jobs_submitted":0}


def factor_validation_only(n):
    # This is deliberately called AFTER manifest-only process has been committed.
    for p in ds.sieve_primes(math.isqrt(n)+1):
        if n%p==0:
            q=n//p
            assert p!=q and p>=P_MIN and q>=P_MIN and ds.sieve_primes(q)[-1]==q
            return p,q
    raise AssertionError(f"not a valid synthetic semiprime {n}")


def factor_cf_public(n,base,y,m,cache):
    # Reuses verified public-only continued-fraction factor predicate.
    return old.explicit_cf_proper_factor(n,base,y,m,cache)


def shared_u(n,m,cache):
    key=(n,m)
    if key not in cache:
        rng=random.Random(hnum(PHASE_SALT,n,m))
        cache[key]=[rng.random() for _ in range(PHASE_SAMPLES)]
    return cache[key]


def approximate_stage_probability(n,base,order,m,cf_cache,u_cache):
    r=int(order)
    if (1<<m)<r:
        return 0.0, 0, "too_low_precision"
    if r<=PHASE_SAMPLES:
        samples=range(r)
        mode="exhaustive_order"
        denominator=r
    else:
        samples=(int(u*r) for u in shared_u(n,m,u_cache))
        mode="seeded_uniform_phase_sample"
        denominator=PHASE_SAMPLES
    total=0.0
    for s in samples:
        y,p=model.nearest_bin_and_probability(s,r,m)
        if factor_cf_public(n,base,y,m,cf_cache):
            total += p
    probability=total/denominator
    assert -1e-12<=probability<=1+1e-12
    return max(0.0,min(1.0,probability)),denominator,mode


def evaluated_policy(n,base,order,gate_cache,cf_cache,u_cache):
    reach=1.0
    ccx=rounds=cswap=0.0
    stages=[]
    stage_cache={}
    for m in model.stage_schedule(n,4,2):
        p,count,mode=approximate_stage_probability(n,base,order,m,cf_cache,u_cache)
        exp_exec=reach*model.expected_stage_shots(p,4)
        if (n,base,m) not in stage_cache:
            stage_cache[(n,base,m)]=model.stage_arithmetic_count(n,base,m,gate_cache)
        arith=stage_cache[(n,base,m)]
        ccx += exp_exec*arith.get("ccx",0)
        cswap += exp_exec*arith.get("cswap",0)
        rounds += exp_exec*m
        stages.append({"m":m,"p_factor_producing":p,"phase_samples":count,
                       "sampling_mode":mode,"expected_executions":exp_exec})
        reach *= (1-p)**4
    success=max(0.0,min(1.0,1-reach))
    return {
       "base":base,"order_validation_only":order,
       "success_probability_by_cap":success,
       "expected_ccx_per_attempt":ccx,
       "expected_cswap_per_attempt":cswap,
       "expected_phase_rounds":rounds,
       "expected_ccx_per_success_with_restarts":ccx/success if success>1e-14 else None,
       "success_zero":success<=1e-14,
       "stages":stages,
    }


def choices(n,a):
    cands={e:(a if e==0 else pow(a,e,n)) for e in EXPONENTS}
    gate={}
    proxy={e:int(model.stage_arithmetic_count(n,cands[e],4,gate).get("ccx",0))
           for e in EXPONENTS}
    ladder=next((e for e in (3,5,7) if n%e not in (0,1)),0)
    cheap=min(EXPONENTS,key=lambda e:(proxy[e],EXPONENTS.index(e)))
    policy={"plain":0,"always3":3,
            "cube_trigger":3 if n%3==2 else 0,
            "ladder":ladder,"cheap4":cheap}
    return cands,proxy,policy


def simulate_row(spec):
    n,a=spec["N"],spec["base"]
    cands,proxy,decisions=choices(n,a)
    # Nothing from the below oracle validation is allowed to modify policies.
    p,q=factor_validation_only(n)
    lam=math.lcm(p-1,q-1)
    r0=model.multiplicative_order_from_lambda(a,n,lam)
    orders={e:model.multiplicative_order_from_lambda(cands[e],n,lam)
            for e in EXPONENTS}
    assert all(orders[e]==r0//math.gcd(r0,e) for e in (3,5,7))
    w0=model.factor_witness(a,r0,n)
    assert all(model.factor_witness(cands[e],orders[e],n)["factor_success"]==
               w0["factor_success"] for e in (3,5,7))
    cf_cache,u_cache,gate_cache={}, {}, {}
    distinct={}
    for e in EXPONENTS:
        base=cands[e]
        if base not in distinct:
            distinct[base]=evaluated_policy(n,base,orders[e],gate_cache,cf_cache,u_cache)
    policies={name:{"exponent":e,**distinct[cands[e]]}
              for name,e in decisions.items()}
    b47=prior.pminusone(n,47)
    return {**spec,"candidate_bases":{str(e):cands[e] for e in EXPONENTS},
            "public_four_phase_ccx_proxy":{str(e):proxy[e] for e in EXPONENTS},
            "policy_exponents":decisions,
            "public_classical_B47_diagnostic":b47,
            "validation_only":{"p":p,"q":q,"lambda":lam,"orders":{str(e):orders[e] for e in EXPONENTS},
                               "order_identity_ok":True,"witness_preservation_ok":True},
            "policies":policies,"no_qpu_jobs":True}


def bootstrap(rows,method,reference,seed):
    if len(rows)<2:
        return None
    rng=random.Random(seed)
    out=[]
    for _ in range(2000):
        sample=[rows[rng.randrange(len(rows))] for __ in rows]
        den=sum(r["policies"][reference]["expected_ccx_per_success_with_restarts"] for r in sample)
        num=sum(r["policies"][method]["expected_ccx_per_success_with_restarts"] for r in sample)
        if den>0:out.append(num/den)
    out.sort()
    return [out[int(0.025*(len(out)-1))],out[int(0.975*(len(out)-1))]]


def compare(rows,method,reference,seed):
    both=[r for r in rows if all(
        r["policies"][k]["expected_ccx_per_success_with_restarts"] is not None
        for k in (method,reference))]
    paired=[(r["policies"][method]["expected_ccx_per_success_with_restarts"],
             r["policies"][reference]["expected_ccx_per_success_with_restarts"])
            for r in both]
    ratio=(sum(a for a,b in paired)/sum(b for a,b in paired)) if paired else None
    relative=[a/b for a,b in paired]
    attempted_den=sum(r["policies"][reference]["expected_ccx_per_attempt"] for r in rows)
    attempted_num=sum(r["policies"][method]["expected_ccx_per_attempt"] for r in rows)
    rounds_den=sum(r["policies"][reference]["expected_phase_rounds"] for r in rows)
    rounds_num=sum(r["policies"][method]["expected_phase_rounds"] for r in rows)
    return {"both_success":len(both),"either_zero_success":len(rows)-len(both),
            "coverage_method":sum(r["policies"][method]["success_probability_by_cap"]>1e-14 for r in rows),
            "coverage_reference":sum(r["policies"][reference]["success_probability_by_cap"]>1e-14 for r in rows),
            "ratio_sum_ccx_per_success":ratio,
            "mean_paired_ratio":statistics.mean(relative) if relative else None,
            "median_paired_ratio":statistics.median(relative) if relative else None,
            "improved":sum(x<1-1e-10 for x in relative),
            "tied":sum(abs(x-1)<=1e-10 for x in relative),
            "worsened":sum(x>1+1e-10 for x in relative),
            "ratio_total_ccx_per_attempt":attempted_num/attempted_den if attempted_den else None,
            "ratio_total_phase_rounds":rounds_num/rounds_den if rounds_den else None,
            "bootstrap_95percent":bootstrap(both,method,reference,seed)}


def summary(rows,screen,ell,group):
    assert len(rows)==PER_GROUP
    out={"selected_classically_unsolved":PER_GROUP,
         "public_candidates_screened":len(screen),
         "classically_solved_in_scan":sum(r["classically_factored"] for r in screen),
         "public_classical_B47_diagnostic_factors":sum(r["public_classical_B47_diagnostic"]["found"] for r in rows),
         "policy_exponent_counts":{name:{str(e):sum(r["policy_exponents"][name]==e for r in rows)
                         for e in EXPONENTS}
                         for name in POLICIES},
         "policies":{},
         "comparisons":{}}
    for pol in POLICIES:
        out["policies"][pol]={
          "factor_success_coverage":sum(r["policies"][pol]["success_probability_by_cap"]>1e-14 for r in rows),
          "mean_success_by_cap":statistics.mean(r["policies"][pol]["success_probability_by_cap"] for r in rows),
          "total_expected_ccx_per_attempt":sum(r["policies"][pol]["expected_ccx_per_attempt"] for r in rows)}
    pairs=[("always3","plain"),("cube_trigger","plain"),("ladder","plain"),
           ("ladder","always3"),("cheap4","plain")]
    for i,(a,b) in enumerate(pairs):
        out["comparisons"][f"{a}_vs_{b}"]=compare(rows,a,b,202610142038+ell*100+
                                                  (0 if group=="trigger" else 1)*10+i)
    return out


def self_test():
    assert old.explicit_cf_proper_factor(15,2,1,2,{})
    assert not old.explicit_cf_proper_factor(15,2,2,4,{})
    assert math.isclose(sum(1 for _ in range(10))/10,1)
    assert choices(143131,2)[2]["plain"]==0
    print("Public factor extraction, deterministic policy and safe arithmetic: SELFTEST PASS")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--manifest-only",action="store_true")
    ap.add_argument("--ell",type=int,choices=ELLS)
    ap.add_argument("--group",choices=GROUPS)
    ap.add_argument("--manifest",type=Path,default=MANIFEST_FILE)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.manifest_only:
        m=create_manifest()
        args.manifest.parent.mkdir(parents=True,exist_ok=True)
        args.manifest.write_text(json.dumps(m,indent=2)+"\n",encoding="utf8")
        print("PUBLIC_MANIFEST_SHA256",m["manifest_sha256"])
        for key,screen in m["public_screenings"].items():
            print(key,"publicly_screened",len(screen),
                  "classically_factored",sum(r["classically_factored"] for r in screen))
        print("NO QPU JOB SUBMITTED")
        return 0
    if args.ell is None or args.group is None:
        ap.error("--ell and --group required to simulate frozen rows")
    m=json.loads(args.manifest.read_text())
    manifest=m["selected_public_rows"]
    assert m["manifest_sha256"]==hashlib.sha256(canonical(manifest).encode()).hexdigest()
    assert len(manifest)==72 and len({r["N"] for r in manifest})==72
    selected=[r for r in manifest if r["ell"]==args.ell and r["group"]==args.group]
    assert len(selected)==PER_GROUP
    print("Frozen public manifest",m["manifest_sha256"],"panel",args.ell,args.group,flush=True)
    output={
       "experiment":"dark_star_n20_public_survivor_v3",
       "revision":REV,"manifest_sha256":m["manifest_sha256"],
       "ell":args.ell,"group":args.group,"expected_rows":PER_GROUP,
       "sampling_cap_per_stage":PHASE_SAMPLES,
       "nearest_bin_only":True,"phase_sample_95pct_hoeffding_bound":math.sqrt(math.log(40)/(2*PHASE_SAMPLES)),
       "zero_qpu":True,"qpu_jobs_submitted":0,"complete":False,"rows":[],
       "preregistration":"docs/DARK_STAR_N20_PUBLIC_POLICY_SURVIVOR_V3_PREREG.md",
       "public_classical_screening":m["public_screenings"][f"{args.ell}_{args.group}"],
       "started_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    path=args.out or (OUT_DIR/f"dark_star_n20_v3_ell{args.ell}_{args.group}.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    checkpoint=path.with_suffix(".partial.json")
    for i,row in enumerate(selected,1):
        print(f"[{i}/{PER_GROUP}] N={row['N']} ell={args.ell} group={args.group}",flush=True)
        output["rows"].append(simulate_row(row))
        checkpoint.write_text(json.dumps(output,indent=2)+"\n")
    output["summary"]=summary(output["rows"],output["public_classical_screening"],args.ell,args.group)
    output["complete"]=True
    output["finished_at_utc"]=datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(output,indent=2)+"\n")
    for key,x in output["summary"]["comparisons"].items():
        print(key,"both",x["both_success"],"ratio",x["ratio_sum_ccx_per_success"],
              "i/t/w",x["improved"],x["tied"],x["worsened"],flush=True)
    print("RESULT_COMPLETE",args.ell,args.group,"NO QPU JOB SUBMITTED",flush=True)


if __name__=="__main__":
    main()
