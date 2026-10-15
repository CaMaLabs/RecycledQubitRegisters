#!/usr/bin/env python3
"""Frozen N22 public-survivor holdout scoring: ladder versus unconditional cube.

Runs only AFTER committed public-only manifest. This is an IDEAL nearest-bin-QPE
+ generic logical CCX model, not quantum hardware. Validation-only p,q and
orders are never used to decide N, base, exponent or online CF/GCD verdict.
Lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import argparse,hashlib,json,math,time
from collections import Counter
from pathlib import Path

import dark_star_ptp_shor_audit as ds
import dark_star_recycled_scalable_arithmetic_audit as model
import dark_star_n20_public_survivor_v3 as v3
import dark_star_public_multichoice_survivor_holdout as mc

MANIFEST=Path("results/dark_star_ptp/dark_star_n22_public_manifest.json")
ROOT=Path("results/dark_star_ptp")
SALTS={"A":"QRR-n22-phase-seed-A-20261014",
       "B":"QRR-n22-phase-seed-B-20261014"}
SAMPLES=8192
ALL_POLICIES=("plain","always3","ladder")


def public_additional_classical(n):
    """Public B47 → Floyd rho 64/seed → trial ≤97 → full prime trial."""
    begin=time.process_time()
    p47=mc.pminusone(n,47)
    results={"B47":p47,"rho":None,"prime_trial_97":None,
             "full_trial":None,"first_factor_source":None,"factor":None}
    if p47["found"]:
        results.update(first_factor_source="Pollard_p_minus_1_B47",
                       factor=int(p47["factor"]))
    else:
        c=dict(iterations=0,gcd_calls=0,modular_square_calls=0,attempts=0)
        got=None
        for seed in (2,3):
            c["attempts"]+=1
            x=y=seed%n
            for _ in range(64):
                x=(x*x+1)%n
                y=(y*y+1)%n
                y=(y*y+1)%n
                c["modular_square_calls"]+=3
                c["gcd_calls"]+=1
                c["iterations"]+=1
                d=math.gcd(abs(x-y),n)
                if 1<d<n:
                    got=int(d)
                    break
                if d==n:break
            if got is not None:break
        results["rho"]={**c,"found":got is not None,"factor":got}
        if got is not None:
            results.update(first_factor_source="Pollard_rho_floyd_64",factor=got)
    if results["factor"] is None:
        found=None
        checks=0
        for p in ds.sieve_primes(97):
            checks+=1
            if n%p==0:
                found=int(p)
                break
        results["prime_trial_97"]=dict(found=found is not None,checks=checks,factor=found)
        if found is not None:
            results.update(first_factor_source="prime_trial_97",factor=found)
    if results["factor"] is None:
        found=None
        checks=0
        for p in ds.sieve_primes(math.isqrt(n)):
            if p<=97:continue
            checks+=1
            if n%p==0:
                found=int(p)
                break
        results["full_trial"]=dict(found=found is not None,checks=checks,factor=found)
        if found is not None:
            results.update(first_factor_source="complete_prime_trial",factor=found)
    factor=results["factor"]
    assert factor is not None and 1<factor<n and n%factor==0
    results["total_public_classical_CPU_ms"]=round((time.process_time()-begin)*1000,4)
    results["classically_factored"]=True
    return results


def validate_semiprime_for_simulation(n):
    """Validation ONLY after public manifest is committed."""
    primes=ds.sieve_primes(math.isqrt(n))
    for p in primes:
        if n%p==0:
            q=n//p
            assert p<q and p>=11 and q>=11
            assert all(q%d for d in range(2,math.isqrt(q)+1))
            return int(p),int(q)
    raise AssertionError(f"manifest frame not semiprime: N={n}")


def seed_config(seed):
    # Existing n20 implementation is REUSED unchanged; only documented
    # per-process sample count and sampling salt are overridden before calls.
    v3.PHASE_SAMPLES=SAMPLES
    v3.PHASE_SALT=SALTS[seed]


def score(spec,seed):
    n=int(spec["N"])
    a=int(spec["base"])
    group=spec["group"]
    expected={"plain":0,"always3":3,
        "ladder":next((e for e in (3,5,7) if n%e not in (0,1)),0)}
    assert spec["public_policy_exponents"]==expected
    assert math.gcd(a,n)==1
    # Strong classical procedures act on public N,a and cannot consult p/q.
    classical=public_additional_classical(n)
    # Reveal validation factors and true orders ONLY after the public
    # manifest and classical method are frozen. This is a toy simulator.
    p,q=validate_semiprime_for_simulation(n)
    lam=math.lcm(p-1,q-1)
    bases={e:(a if e==0 else pow(a,e,n)) for e in set(expected.values())}
    r0=model.multiplicative_order_from_lambda(a,n,lam)
    orders={e:model.multiplicative_order_from_lambda(base,n,lam)
            for e,base in bases.items()}
    assert all(orders[e]==r0//math.gcd(r0,e) for e in orders if e)
    initial_witness=model.factor_witness(a,r0,n)["factor_success"]
    assert all(model.factor_witness(bases[e],orders[e],n)["factor_success"]==
         initial_witness for e in orders)
    gate_cache,cf_cache,u_cache={},{},{}
    scored={}
    for e in sorted(bases):
        scored[e]=v3.evaluated_policy(n,bases[e],orders[e],gate_cache,cf_cache,u_cache)
        assert len(scored[e]["stages"])==21
    policies={name:{"exponent":e,**scored[e]} for name,e in expected.items()}
    assert policies["always3"]["base"]==pow(a,3,n)
    assert (policies["ladder"]["base"]==policies["always3"]["base"]) if group=="trigger" else True
    return {**spec,"seed":seed,"additional_classical":classical,
         "validation_only":dict(p=p,q=q,lambda_N=lam,base_orders={str(e):r for e,r in orders.items()},
             known_order_identity_ok=True,half_order_witness_preservation_ok=True,
             factors_used_in_selection=False),
         "policies":policies,"zero_QPU_jobs":True}


def summarize(rows,group,seed):
    pairs=(("ladder","always3"),("ladder","plain"),("always3","plain"))
    # Compare on same full cohort and keep zero-success rows explicit.
    comparisons={}
    for i,(name,ref) in enumerate(pairs):
        comparisons[f"{name}_vs_{ref}"]=v3.compare(rows,name,ref,202610142341+i+
            (0 if group=="trigger" else 100))
    return dict(selected=len(rows),
        classical_additional_factored=sum(r["additional_classical"]["classically_factored"] for r in rows),
        classical_sources=dict(Counter(r["additional_classical"]["first_factor_source"] for r in rows)),
        mean_public_CPU_ms=sum(r["additional_classical"]["total_public_classical_CPU_ms"] for r in rows)/len(rows),
        policy_factor_success_coverage={name:sum(r["policies"][name]["success_probability_by_cap"]>1e-14
                                   for r in rows) for name in ALL_POLICIES},
        public_ladder_exponents=dict(Counter(str(r["public_policy_exponents"]["ladder"]) for r in rows)),
        comparisons=comparisons,
        numerical_seed=seed)


def selftest():
    assert v3.factor_cf_public(15,2,1,2,{})
    assert not v3.factor_cf_public(15,2,2,4,{})
    for n in (143,899,713,10403):
        if n>=1<<22:continue
        out=public_additional_classical(n)
        assert out["classically_factored"] and n%out["factor"]==0
    return {"passes":True,"public_classical_factor_verification":True,
        "online_CF_no_factor_order_oracle":True}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--group",choices=("trigger","control"),required=True)
    parser.add_argument("--seed",choices=("A","B"),required=True)
    parser.add_argument("--manifest",type=Path,default=MANIFEST)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    seed_config(args.seed)
    frozen=json.loads(args.manifest.read_text())
    digest=hashlib.sha256(v3.canonical(frozen["selected_public_rows"]).encode()).hexdigest()
    assert digest==frozen["selected_manifest_sha256"]
    assert len(frozen["selected_public_rows"])==12
    assert set(r["group"] for r in frozen["selected_public_rows"])=={"trigger","control"}
    rows=[r for r in frozen["selected_public_rows"] if r["group"]==args.group]
    assert len(rows)==6
    print("FROZEN PUBLIC N22 MANIFEST",digest,"GROUP",args.group,
          "NUMERIC SEED",args.seed,"PHASE_SAMPLES",SAMPLES,flush=True)
    out={"experiment":"dark_star_n22_ladder_vs_cube_public_survivor_v1",
       "preregistration":"docs/DARK_STAR_N22_SELECTOR_VS_CUBE_PREREG.md",
       "manifest_sha256":digest,"bits":22,"group":args.group,
       "seed":args.seed,"phase_salt":SALTS[args.seed],"samples_per_stage":SAMPLES,
       "nearest_bin_only_ideal_QPE":True,"zero_qpu":True,"qpu_jobs_submitted":0,
       "selftests":selftest(),"full_classical_screening":frozen["public_screenings"][args.group],
       "rows":[],"summary":{},"complete":False,
       "claim_boundary":"ideal nearest-bin QPE and generic logical CCX; all selected semiprimes classically factorable; zero QPU; not a practical quantum advantage"}
    for i,r in enumerate(rows,1):
        t=time.process_time()
        x=score(r,args.seed)
        out["rows"].append(x)
        print(f"[{i}/6] N={r['N']} group={args.group} ladder_ell={r['public_policy_exponents']['ladder']} "
              f"classical={x['additional_classical']['first_factor_source']} "
              f"cube_ideal_success={x['policies']['always3']['success_probability_by_cap']:.5f} "
              f"CPU_model_s={time.process_time()-t:.2f}",flush=True)
    out["summary"]=summarize(out["rows"],args.group,args.seed)
    assert all(x["validation_only"]["known_order_identity_ok"] for x in out["rows"])
    width=model.arithmetic_width(rows[0]["N"])
    out["logical_width"]={"arithmetic_workspace":width["arithmetic_qubits_excluding_phase"],
           "wide_peak":width["arithmetic_qubits_excluding_phase"]+44,
           "recycled_peak":width["recycled_logical_qubits"]}
    out["complete"]=True
    path=args.out or ROOT/f"dark_star_n22_{args.group}_seed_{args.seed}.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2)+"\n")
    print("===== N22 PUBLIC-SELECTOR RESULTS =====",flush=True)
    for name,x in out["summary"]["comparisons"].items():
        print(name,"both",x["both_success"],"coverage",x["coverage_method"],x["coverage_reference"],
          "ratio",x["ratio_sum_ccx_per_success"],"wins/ties/loss",x["improved"],x["tied"],x["worsened"],flush=True)
    print("NO QPU JOBS; RECEIPT",path,flush=True)


if __name__=="__main__":main()
