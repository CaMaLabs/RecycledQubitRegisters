#!/usr/bin/env python3
"""First NEW public 26-bit unified Dark Star cohort, before any QPE/classical run.

Synthetic semiprimes constructed with known p,q; only N is ranked/published.
No p/q, multiplicative order, classical factor labels or model outcomes enter
the SHA rank or public base selection. ZERO IBM QPU.
"""
import hashlib
import json
import math
from pathlib import Path

from integrations.darkstar_hybrid import darkstar_v2 as ds

ROOT=Path("results/dark_star_unified")
OUT=ROOT/"unified_n26_public_manifest.json"
PRE="docs/DARK_STAR_UNIFIED_N26_FRESH_POPULATION_PREREG.md"
POP_SALT="QRR-UNIFIED-N26-POP-20261028"
BASE_SALT="QRR-UNIFIED-N26-BASE-20261028"
BASES=(2,3,5,7,11,13,17,19,23,29,31)
LOW,HIGH=1<<25,1<<26
PRIME_MIN,PRIME_MAX=4500,14000
GROUPS={"G1_mod3_1":1,"G2_mod3_2":2}
SAMPLE_PER_GROUP=6


def digest(*values):
    return hashlib.sha256("|".join(map(str,values)).encode()).hexdigest()


def base_for(n,group):
    start=int(digest(BASE_SALT,group,n),16)%len(BASES)
    for j in range(len(BASES)):
        a=BASES[(start+j)%len(BASES)]
        if math.gcd(a,n)==1:
            return a
    raise AssertionError("No public coprime base")


def rows_hash(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def make_manifest():
    primes=[p for p in ds.primes_up_to(PRIME_MAX) if p>=PRIME_MIN]
    candidate_n=set()
    for i,p in enumerate(primes):
        for q in primes[i+1:]:
            n=p*q
            if n>=HIGH:
                break
            if n>=LOW and math.gcd(n,210)==1 and n%3 in (1,2):
                candidate_n.add(n)
    assert len(candidate_n)>4000
    selected=[]
    group_counts={}
    for group,residue in GROUPS.items():
        ns=[n for n in candidate_n if n%3==residue]
        ranked=sorted(ns,key=lambda n:(digest(POP_SALT,group,n),n))
        assert len(ranked)>=SAMPLE_PER_GROUP
        group_counts[group]=len(ranked)
        for rank,n in enumerate(ranked[:SAMPLE_PER_GROUP],start=1):
            a=base_for(n,group)
            selected.append(dict(N=n,base=a,group=group,rank=rank,
                                 public_N_mod3=n%3,public_N_mod210=n%210,
                                 public_cube=pow(a,3,n)))
    assert len(selected)==12 and len({z["N"] for z in selected})==12
    assert all(LOW<=r["N"]<HIGH and math.gcd(r["N"],210)==1 for r in selected)
    return dict(experiment="unified_Dark_Star_fresh_N26_public_selection_only",
                preregistration=PRE, selected_public_rows=selected,
                selected_sha256=rows_hash(selected),
                candidate_population_count=len(candidate_n),
                group_frame_counts=group_counts,
                sampling_salt=POP_SALT,base_salt=BASE_SALT,base_pool=list(BASES),
                bitlength=26,range_N=[LOW,HIGH],
                synthetic_prime_frame=[PRIME_MIN,PRIME_MAX],
                no_prime_factors_or_orders_used_for_selection=True,
                no_classical_budget_or_model_score_used_for_selection=True,
                no_prime_factors_published_in_manifest=True,
                no_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False)


if __name__=="__main__":
    m=make_manifest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(m,indent=2)+"\n")
    print("PRE-FROZEN PUBLIC 26-bit cohort SHA",m["selected_sha256"],flush=True)
    print("Candidate frame",m["candidate_population_count"],m["group_frame_counts"],flush=True)
    for row in m["selected_public_rows"]:
        print("PUBLIC ONLY",row["group"],row["rank"],"N",row["N"],"base",row["base"],flush=True)
    print("NO classical filters, factor labels, QPE scores or IBM hardware inspected",flush=True)
