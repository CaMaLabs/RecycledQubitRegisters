#!/usr/bin/env python3
"""Fresh N25 public-only SHA cohort with fixed, ACTUALLY EXECUTED B31+B47/rho64.

No order lookup, no QPE, no private factor witness used for selection.
Known original eight N25 public rows explicitly excluded before ranking.
CaMaLabs / Chase Lunsford. Zero QPU, no quantum SDK.
"""
from __future__ import annotations
import hashlib,json,math,time
from pathlib import Path
import dark_star_n25_online_public_manifest as pub
import dark_star_public_multichoice_survivor_holdout as mc
import dark_star_ptp_shor_audit as ds

SALT="QRR-N25-B47RHO64-FRESH-POP-20261028"
BASE_SALT="QRR-N25-B47RHO64-FRESH-BASE-20261028"
PREVIOUS=Path("results/dark_star_ptp/dark_star_n25_online_public_manifest.json")
OUT=Path("results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_manifest.json")
PREREG="docs/DARK_STAR_N25_POST_B47RHO_FRESH_COHORT_PREREG.md"
GROUPS=(("G1_mod3_1",1),("G2_mod3_2",2))
BASES=(2,3,5,7,11,13,17,19,23,29,31)
CAP=1200
TARGET=4
def h(*s):
    return hashlib.sha256("|".join(map(str,s)).encode()).hexdigest()
def base_for(n,g):
    i=int(h(BASE_SALT,g,n),16)%len(BASES)
    for j in range(len(BASES)):
        a=BASES[(i+j)%len(BASES)]
        if math.gcd(a,n)==1:return a
    raise AssertionError("No public coprime base")
def budget_b47rho64(n):
    """Public on-demand classical filter, identical policy to previous N25."""
    start=time.process_time()
    p47=mc.pminusone(n,47)
    rho=dict(attempts=0,iterations=0,gcd_calls=0,modular_squares=0,factor=None)
    trial=dict(checks=0,factor=None)
    factor=p47["factor"] if p47["found"] else None
    source="Pollard_p_minus_1_B47" if factor else None
    if not factor:
        for seed in (2,3):
            rho["attempts"]+=1
            x=y=seed%n
            for _ in range(64):
                x=(x*x+1)%n
                y=(y*y+1)%n
                y=(y*y+1)%n
                rho["modular_squares"]+=3
                rho["gcd_calls"]+=1
                rho["iterations"]+=1
                g=math.gcd(abs(x-y),n)
                if 1<g<n:
                    factor=g
                    rho["factor"]=g
                    source="Floyd_rho_64"
                    break
                if g==n:break
            if factor:break
    if not factor:
        for p in ds.sieve_primes(97):
            trial["checks"]+=1
            if n%p==0:
                factor=p
                trial["factor"]=p
                source="small_prime_trial_97"
                break
    if factor:
        assert 1<int(factor)<n and n%int(factor)==0
    return dict(classically_solved=bool(factor),
        factor=int(factor) if factor else None,
        source=source,B47=p47,rho=rho,trial97=trial,
        elapsed_CPU_ms=round(1000*(time.process_time()-start),5),
        quantum_needed_after_fixed_public_filter=not bool(factor))
def build():
    previous=json.loads(PREVIOUS.read_text())
    assert previous["selected_sha256"]=="66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
    old={int(z["N"]) for z in previous["selected_public_rows"]}
    assert len(old)==8
    # The original frame synthesizes N from prime pairs but exposes ONLY
    # an N set. No hidden prime witness enters the following operations.
    candidates=pub.public_frame()
    assert len(candidates)==80200
    assert old.issubset(candidates)
    chosen=[]
    screenings={}
    for group,mod in GROUPS:
        ranked=sorted((n for n in candidates if n%3==mod and n not in old),
                      key=lambda n:(h(SALT,group,n),n))
        scanned=[]
        for n in ranked[:CAP]:
            a=base_for(n,group)
            b31=mc.classical_cascade(n,a)
            row=dict(N=n,base=a,group=group,rank=len(scanned)+1,
                B31_factored=bool(b31["found"]),
                B31_factor=b31["factor"],B31_source=b31["source"],
                B31_operations=b31["counts"],B47rho64_executed=False,
                B47rho64_public_budget=None)
            if not b31["found"]:
                b47=budget_b47rho64(n)
                row["B47rho64_executed"]=True
                row["B47rho64_public_budget"]=b47
                if not b47["classically_solved"]:
                    chosen.append(dict(N=n,base=a,group=group,rank=row["rank"],
                        plain=a,cube=pow(a,3,n),B31_unfactored=True,
                        B47rho64_unsolved=True))
            scanned.append(row)
            if sum(z["group"]==group for z in chosen)==TARGET:break
        assert sum(z["group"]==group for z in chosen)==TARGET,(group,len(scanned))
        screenings[group]=scanned
        print("PUBLIC SELECTION",group,"screens",len(scanned),
              "chosen",[(z["N"],z["base"]) for z in chosen if z["group"]==group],
              flush=True)
    assert len(chosen)==8 and len({z["N"] for z in chosen})==8
    assert all(z["N"] not in old for z in chosen)
    SHA=hashlib.sha256(pub.canonical(chosen).encode()).hexdigest()
    out=dict(experiment="n25_fresh_public_post_b47rho64_nonsolved_manifest",
        research_lead="Chase Lunsford / CaMaLabs",
        preregistration=PREREG,
        original_n25_manifest_sha256=previous["selected_sha256"],
        previous_original_public_Ns_excluded=sorted(old),
        original_cohort_sample_overlap=0,
        selected_public_rows=chosen,selected_sha256=SHA,
        public_screenings=screenings,
        candidate_frame_unique_N=len(candidates),
        range_N=[1<<24,1<<25],
        prime_construction_range=[3500,11000],
        population_salt=SALT,base_salt=BASE_SALT,
        base_pool=list(BASES),screening_cap_per_group=CAP,
        selected_per_group=TARGET,
        selection_public_only_B31_and_B47rho64=True,
        factor_order_and_qpe_not_inspected_for_selection=True,
        zero_QPU=True,qpu_jobs_submitted=0,paid_runtime_used=False)
    return out
if __name__=="__main__":
    x=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(x,indent=2)+"\n")
    print("FROZEN NEW PUBLIC N25 SHA",x["selected_sha256"],
          "cases",len(x["selected_public_rows"]),
          "old overlap",x["original_cohort_sample_overlap"],
          "zero QPU",flush=True)
