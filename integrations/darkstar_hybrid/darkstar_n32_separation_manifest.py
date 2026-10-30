#!/usr/bin/env python3
"""Prospective N32 original separation cohort: selection only, no factor scoring.

Construction uses p,q to create three known-separation synthetic populations.
The manifest contains NO p/q or measured factorization scores.  The public
factoring algorithms receive N alone; the stratum is EXPERIMENT METADATA ONLY.
"""
import bisect
import hashlib
import json
import math
from pathlib import Path
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr

ROOT=Path("results/dark_star_unified")
OUT=ROOT/"darkstar_n32_separation_frozen_manifest.json"
SALT="DARKSTAR-N32-SEPARATION-20261029"
PRIME_MIN,PRIME_MAX=21000,155000
LOW,HIGH=1<<31,1<<32
STRATA={"near_0_8":(0,8),
        "middle_64_640":(64,640),
        "far_4096_16384":(4096,16384)}
PICK=8

def stratum_for(distance):
    for name,(minimum,maximum) in STRATA.items():
        if minimum<=distance<=maximum:
            return name
    return None

def digest(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def rank(stratum,N):
    return hashlib.sha256(f"{SALT}|{stratum}|{N}".encode()).hexdigest()

def create():
    ps=ds.primes_up_to(PRIME_MAX)
    buckets={x:set() for x in STRATA}
    for p in ps:
        if p<PRIME_MIN:continue
        if p*p>=HIGH:break
        lo=max(p+1,(LOW+p-1)//p)
        hi=min(PRIME_MAX,(HIGH-1)//p)
        first=bisect.bisect_left(ps,lo)
        last=bisect.bisect_right(ps,hi)
        for q in ps[first:last]:
            n=p*q
            if n<LOW or n>=HIGH or math.gcd(n,210)!=1:
                continue
            displacement=(p+q)//2-qr.ceil_sqrt(n)
            group=stratum_for(displacement)
            if group is not None:
                buckets[group].add(n)
    assert all(len(x)>=PICK for x in buckets.values()), {k:len(x) for k,x in buckets.items()}
    rows=[]
    for group in STRATA:
        ranked=sorted(buckets[group],key=lambda n:(rank(group,n),n))
        for j,n in enumerate(ranked[:PICK],1):
            rows.append(dict(N=n,group=group,rank=j,
                Nmod210=n%210,N_bits=n.bit_length()))
    assert len(rows)==24 and len({x["N"] for x in rows})==24
    return dict(experiment="DarkStar_N32_synthetic_factor_separation_PREREG_PUBLIC_INPUTS_ONLY",
        prereg="docs/DARK_STAR_N32_SEPARATION_VS_BRENT_PREREG.md",
        selection_salt=SALT,prime_frame=[PRIME_MIN,PRIME_MAX],
        N_range=[LOW,HIGH],
        original_strata={k:list(v) for k,v in STRATA.items()},
        candidate_counts={k:len(v) for k,v in buckets.items()},
        public_manifest_contains_prime_factors=False,
        population_generated_using_pq_separation=True,
        no_factors_or_order_in_public_manifest=True,
        no_routing_algorithm_receives_construction_stratum=True,
        no_factorization_results_scored_before_freeze=True,
        algorithm_only_uses_public_N=True,
        selected_public_rows=rows,sha256_canonical_rows=digest(rows),
        zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False)

if __name__=="__main__":
    x=create()
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(x,indent=2)+"\n")
    print("ORIGINAL PUBLIC N32 FROZEN",x["sha256_canonical_rows"],
          "population candidate frames",x["candidate_counts"],flush=True)
    for z in x["selected_public_rows"]:
        print("PUBLIC_N_ONLY",z["group"],z["rank"],z["N"])
    print("NO FACTOR ALGORITHMS, TRUE ORDER, OR QPU INVOKED")
