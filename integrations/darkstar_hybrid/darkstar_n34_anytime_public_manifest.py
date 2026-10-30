#!/usr/bin/env python3
"""Fresh 34-bit SHA public-N only manifest; synthetic separation is selection ONLY.

Streaming top-8 SHA ranks, no factor algorithm invoked before committing inputs.
"""
import bisect
import hashlib
import heapq
import json
import math
from pathlib import Path
from integrations.darkstar_hybrid import darkstar_v2 as ds
from integrations.darkstar_hybrid import midpoint_qr_pruner as qr

ROOT=Path("results/dark_star_unified")
OUT=ROOT/"darkstar_n34_anytime_public_frozen_manifest.json"
SALT="DARKSTAR-N34-ADAPTIVE-20261029"
POLICY_SHA="afdc1e69a94ebfdd7d73fd2b6d5ada6d8c589753"
P_MIN=55000
P_MAX=260000
N_LO,N_HI=1<<33,1<<34
STRATA={"near_0_8":(0,8),
        "middle_64_640":(64,640),
        "far_4096_16384":(4096,16384)}
PICK=8

def group_for(d):
    for group,(lower,upper) in STRATA.items():
        if lower<=d<=upper:
            return group
    return None

def row_sha(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def rank(group,n):
    return int.from_bytes(hashlib.sha256(f"{SALT}|{group}|{n}".encode()).digest(),"big")

def create_manifest():
    ps=ds.primes_up_to(P_MAX)
    heaps={name:[] for name in STRATA}
    sizes={name:0 for name in STRATA}
    for p in ps:
        if p<P_MIN:continue
        if p*p>=N_HI:break
        lo=max(p+1,(N_LO+p-1)//p)
        hi=min(P_MAX,(N_HI-1)//p)
        if lo>hi:continue
        first=bisect.bisect_left(ps,lo)
        last=bisect.bisect_right(ps,hi)
        for q in ps[first:last]:
            n=p*q
            if math.gcd(n,210)!=1:continue
            d=(p+q)//2 - qr.ceil_sqrt(n)
            g=group_for(d)
            if g is None:continue
            sizes[g]+=1
            # Since p<q with both prime, unique factorization makes N unique.
            hash_int=rank(g,n)
            candidate=(-hash_int,-n,n)
            heap=heaps[g]
            if len(heap)<PICK:
                heapq.heappush(heap,candidate)
            elif candidate>heap[0]:
                heapq.heapreplace(heap,candidate)
    assert all(len(h)==PICK for h in heaps.values()),sizes
    rows=[]
    for group in STRATA:
        chosen=sorted(heaps[group],key=lambda item:(-item[0],item[2]))
        for i,(_,_,n) in enumerate(chosen,1):
            rows.append(dict(N=n,group=group,rank=i,public_N_mod210=n%210,
                public_N_bitlength=n.bit_length()))
    assert len(rows)==len({r["N"] for r in rows})==24
    assert all(N_LO<=z["N"]<N_HI and math.gcd(z["N"],210)==1 for z in rows)
    return dict(experiment="DarkStar_N34_NEW_original_24_public_immutable_selection",
        protocol="docs/DARK_STAR_N34_ANYTIME_INTERLEAVED_PREREG.md",
        selection_salt=SALT,
        immutable_policy_source_sha=POLICY_SHA,
        prime_generation_only_for_synthetic_separation_selection=True,
        hidden_factors_not_in_manifest=True,
        group_labels_are_population_metadata_not_factor_algorithm_inputs=True,
        factorization_not_performed_before_manifest_freeze=True,
        strata={k:list(v) for k,v in STRATA.items()},
        candidate_population_counts=sizes,
        public_N_range=[N_LO,N_HI],synthetic_prime_frame=[P_MIN,P_MAX],
        original_public_rows=rows,
        row_SHA256=row_sha(rows),
        zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False)

if __name__=="__main__":
    z=create_manifest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(z,indent=2)+"\n")
    print("PRE-FROZEN N34 PUBLIC SHA",z["row_SHA256"],
          "FRAME",z["candidate_population_counts"],flush=True)
    for r in z["original_public_rows"]:
        print("PUBLIC INPUT",r["group"],r["rank"],r["N"],flush=True)
    print("NO factorization, no private factors exposed, NO QPU",flush=True)
