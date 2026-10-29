#!/usr/bin/env python3
"""N27 DARK STAR public-only sample freeze: do not inspect factoring/order results."""
import hashlib
import json
import math
from pathlib import Path
from integrations.darkstar_hybrid import darkstar_v2 as ds

ROOT=Path("results/dark_star_unified")
OUT=ROOT/"unified_n27_restored_public_manifest.json"
SALT="QRR-UNIFIED-N27-RESTORED-POP-20261028"
BASE_SALT="QRR-UNIFIED-N27-RESTORED-BASE-20261028"
BASES=(2,3,5,7,11,13,17,19,23,29,31)
N_MIN,N_MAX=1<<26,1<<27
P_MIN,P_MAX=6800,18500
GROUPS={"G1_mod3_1":1,"G2_mod3_2":2}

def sha(*args):
    return hashlib.sha256("|".join(str(x) for x in args).encode()).hexdigest()

def row_digest(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def base_for(n,g):
    i=int(sha(BASE_SALT,g,n),16)%len(BASES)
    for j in range(len(BASES)):
        a=BASES[(i+j)%len(BASES)]
        if math.gcd(a,n)==1:
            return a
    raise RuntimeError("no coprime public base")

def make():
    ps=[p for p in ds.primes_up_to(P_MAX) if P_MIN<=p]
    ns=set()
    for i,p in enumerate(ps):
        for q in ps[i+1:]:
            n=p*q
            if n>=N_MAX:
                break
            if n>=N_MIN and math.gcd(n,210)==1:
                ns.add(n)
    assert len(ns)>1000
    rows=[]
    sizes={}
    for group,res in GROUPS.items():
        frame=sorted((n for n in ns if n%3==res),key=lambda n:(sha(SALT,group,n),n))
        assert len(frame)>6
        sizes[group]=len(frame)
        for rank,n in enumerate(frame[:6],1):
            a=base_for(n,group)
            rows.append(dict(N=n,base=a,group=group,rank=rank,
                             public_N_mod3=n%3,public_N_mod210=n%210,
                             public_cube=pow(a,3,n)))
    assert len(rows)==len({z["N"] for z in rows})==12
    return dict(experiment="fresh_N27_restored_PTP_public_only_frozen_before_any_outcomes",
                protocol="docs/DARK_STAR_N27_RESTORED_PLUS_IDENTITY_PRUNING_PREREG.md",
                source_primes_only_for_synthetic_construction=True,
                no_private_pq_or_order_in_ranking_or_base_selection=True,
                no_classical_filter_or_quantum_outcome_used_to_select=True,
                pop_salt=SALT,base_salt=BASE_SALT,public_base_pool=list(BASES),
                n_range=[N_MIN,N_MAX],prime_frame=[P_MIN,P_MAX],
                candidate_count=len(ns),candidate_group_counts=sizes,
                selected_public_rows=rows,selected_sha256=row_digest(rows),
                zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False)

if __name__=="__main__":
    j=make()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(j,indent=2)+"\n")
    print("PRE-FROZEN N27 SHA",j["selected_sha256"],"public frame",j["candidate_count"])
    for r in j["selected_public_rows"]:
        print(r["group"],r["rank"],r["N"],r["base"])
    print("NO validation factors, multiplicative order, classical filters or QPU used")
