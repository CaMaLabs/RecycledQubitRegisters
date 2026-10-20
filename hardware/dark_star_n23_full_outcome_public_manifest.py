#!/usr/bin/env python3
"""PUBLIC-only selection of new 23-bit QRR semiprime B31 survivors.
No factors/orders, QPE results or oracle labels are written to frozen manifest.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

import dark_star_ptp_shor_audit as ds
import dark_star_public_multichoice_survivor_holdout as mc

LO,HI=1<<22,(1<<23)-1
SALT="QRR-N23-FULLOUTCOME-V1-POP-20261020"
BASE_SALT="QRR-N23-FULLOUTCOME-V1-BASE-20261020"
POOL=(2,3,5,7,11,13,17,19,23,29,31)
PER_GROUP=4
CAP=700
DEST=Path("results/dark_star_ptp/dark_star_n23_full_outcome_public_manifest.json")

def hash_int(*parts):
    return int.from_bytes(hashlib.sha256("|".join(map(str,parts)).encode()).digest(),"big")

def canonical(rows):
    return json.dumps(rows,sort_keys=True,separators=(",",":"))

def public_base(n,group):
    first=hash_int(BASE_SALT,group,n)%len(POOL)
    for k in range(len(POOL)):
        a=POOL[(first+k)%len(POOL)]
        if math.gcd(a,n)==1:return a
    raise AssertionError("No coprime public base")

def semiprimes():
    primes=ds.sieve_primes(HI)
    ns=set()
    for i,p in enumerate(primes):
        if p<11:continue
        if p*p>HI:break
        for q in primes[i+1:]:
            n=p*q
            if n>HI:break
            if n>=LO and n%3!=0 and q>p:ns.add(n)
    return ns

def build():
    ns=semiprimes()
    rows=[]
    screens={}
    for group,mod in (("trigger",2),("control",1)):
        ranked=sorted((n for n in ns if n%3==mod),
                      key=lambda n:(hash_int(SALT,group,n),n))
        seen=[]
        selected=[]
        for n in ranked[:CAP]:
            a=public_base(n,group)
            cl=mc.classical_cascade(n,a)
            record=dict(N=n,base=a,rank=len(seen)+1,
                        public_B31_factored=bool(cl["found"]),
                        public_factor=cl["factor"],
                        source=cl["source"],
                        primitive_operation_counts=cl["counts"])
            seen.append(record)
            if not cl["found"]:
                selected.append(dict(N=n,base=a,group=group,rank=record["rank"],
                                     public_policies=dict(plain=a,cube=pow(a,3,n))))
                if len(selected)==PER_GROUP:break
        if len(selected)!=PER_GROUP:
            raise RuntimeError(f"{group} expected 4 B31 survivors, got {len(selected)} after {len(seen)} of {CAP}")
        rows.extend(selected)
        screens[group]=seen
    assert len(rows)==8 and len({x["N"] for x in rows})==8
    assert all(LO<=x["N"]<=HI and x["N"]%3==(2 if x["group"]=="trigger" else 1)
               for x in rows)
    return dict(experiment="QRR-independent-N23-full-outcome-public-manifest",
                preregistration="docs/DARK_STAR_N23_FULL_OUTCOME_CUBE_PREREG.md",
                N_interval=[LO,HI],
                selection_salt=SALT,base_salt=BASE_SALT,selected_public_rows=rows,
                public_screenings=screens,
                selected_sha256=hashlib.sha256(canonical(rows).encode()).hexdigest(),
                zero_QPU=True,qpu_jobs_submitted=0,
                note="Only public N,base,group,sha-rank,B31 factor/screen ledger. No validation factor/order or QPE cost.")

if __name__=="__main__":
    j=build()
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(j,indent=2)+"\n")
    print("MANIFEST",j["selected_sha256"],"new 23bit cases",len(j["selected_public_rows"]),flush=True)
    for g,s in j["public_screenings"].items():
        print(g,"screened",len(s),"B31 factored",sum(x["public_B31_factored"] for x in s),
              "selected",[(a["N"],a["base"]) for a in j["selected_public_rows"] if a["group"]==g],flush=True)
    print("NO QPU AND NO SECRET ORDER OR PHASE ANALYSIS",flush=True)
