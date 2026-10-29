#!/usr/bin/env python3
"""Preselection only for fresh N28 Dark Star cost router; NO factoring outcomes."""
import hashlib
import json
import math
from pathlib import Path
from integrations.darkstar_hybrid import darkstar_v2 as ds

ROOT=Path("results/dark_star_unified")
OUT=ROOT/"darkstar_public_router_n28_frozen_manifest.json"
SALT="DARKSTAR-ROUTER-N28-PUBLIC-20261029"
ROUTER_REV="darkstar_public_router_v1_20261029"
ROUTER_GIT_BLOB="4420a5d5d83869ccc41ab2396cde15d84f98a4c1"
LO,HI=1<<27,1<<28
P_MIN,P_MAX=9500,28000
GROUPS={"G1_mod3_1":1,"G2_mod3_2":2}

def rankhash(group,n):
    return hashlib.sha256(f"{SALT}|{group}|{n}".encode()).hexdigest()

def digest(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def generate():
    primes=[p for p in ds.primes_up_to(P_MAX) if p>=P_MIN]
    public_ns=set()
    for i,p in enumerate(primes):
        for q in primes[i+1:]:
            n=p*q
            if n>=HI: break
            if n>=LO and math.gcd(n,210)==1:
                public_ns.add(n)
    assert len(public_ns)>10000
    out=[]
    group_sizes={}
    for group,residue in GROUPS.items():
        all_in_group=sorted((n for n in public_ns if n%3==residue),
            key=lambda n:(rankhash(group,n),n))
        group_sizes[group]=len(all_in_group)
        assert len(all_in_group)>=8
        for rank,n in enumerate(all_in_group[:8],1):
            out.append(dict(N=n,group=group,rank=rank,
                public_mod3=n%3,public_mod210=n%210,
                fixed_router_policy=ROUTER_REV))
    assert len(out)==len({r["N"] for r in out})==16
    assert all(LO<=z["N"]<HI and math.gcd(z["N"],210)==1 for z in out)
    return dict(experiment="DARKSTAR_N28_ORIGINAL_PUBLIC_ROUTER_HOLDOUT_FROZEN_INPUTS_ONLY",
        prereg="docs/DARK_STAR_PUBLIC_COST_ROUTER_N28_PREREG.md",
        selection_salt=SALT,
        selected_public_rows=out,
        row_canonical_sha256=digest(out),
        candidate_frame_count=len(public_ns),
        group_candidate_counts=group_sizes,
        synthetic_prime_frame=[P_MIN,P_MAX],
        N_range=[LO,HI],
        router_revision=ROUTER_REV,
        router_source_git_blob_SHA=ROUTER_GIT_BLOB,
        no_hidden_prime_factor_or_order_used_to_rank=True,
        no_classical_or_quantum_outcomes_inspected_before_freeze=True,
        no_user_keys_used=True,
        zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False)

if __name__=="__main__":
    j=generate()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(j,indent=2)+"\n")
    print("DARK STAR N28 PUBLIC SELECTED SHA",j["row_canonical_sha256"],flush=True)
    print("CANDIDATE FRAME",j["candidate_frame_count"],j["group_candidate_counts"],flush=True)
    for r in j["selected_public_rows"]:
        print("PUBLIC INPUT ONLY",r["group"],r["rank"],r["N"],flush=True)
    print("ZERO factoring / validation outcome examined. ZERO QPU",flush=True)
