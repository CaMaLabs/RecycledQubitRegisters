#!/usr/bin/env python3
"""N25 independent public-only 8-row freeze. NEVER use p/q for public selection."""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import dark_star_ptp_shor_audit as ds
import dark_star_public_multichoice_survivor_holdout as mc

LO,HI=1<<24,1<<25
PRIMES_MIN,PRIMES_MAX=3500,11000
SALT="QRR-N25-ONLINE-ARITH-POP-20261025"
BASE_SALT="QRR-N25-ONLINE-ARITH-BASE-20261025"
GROUPS=(("G1_mod3_1",1),("G2_mod3_2",2))
BASES=(2,3,5,7,11,13,17,19,23,29,31)
TARGET=4
CAP=600
PREREG="docs/DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_PREREG.md"
DEST=Path("results/dark_star_ptp/dark_star_n25_online_public_manifest.json")

def h(*xs):
    return hashlib.sha256("|".join(map(str,xs)).encode()).hexdigest()
def canonical(rows):
    return json.dumps(rows,sort_keys=True,separators=(",",":"))
def base_for(n,group):
    ix=int(h(BASE_SALT,group,n),16)%len(BASES)
    for k in range(len(BASES)):
        a=BASES[(ix+k)%len(BASES)]
        if math.gcd(a,n)==1:
            return a
    raise AssertionError("No coprime base")
def public_frame():
    primes=[p for p in ds.sieve_primes(PRIMES_MAX) if p>=PRIMES_MIN]
    ns=set()
    for i,p in enumerate(primes):
        for q in primes[i+1:]:
            n=p*q
            if n>=HI:break
            if LO<=n and n%3 in (1,2):
                ns.add(n)
    assert len(ns)>200
    return ns
def build():
    ns=public_frame()
    selected=[]
    screens={}
    for g,mod in GROUPS:
        ranked=sorted((n for n in ns if n%3==mod),key=lambda n:(h(SALT,g,n),n))
        checked=[]
        for n in ranked[:CAP]:
            a=base_for(n,g)
            s=mc.classical_cascade(n,a)
            x=dict(N=n,base=a,rank=len(checked)+1,
                   B31_factored=bool(s["found"]),B31_factor=s["factor"],
                   B31_source=s["source"],B31_operations=s["counts"])
            checked.append(x)
            if not s["found"]:
                selected.append(dict(N=n,base=a,group=g,rank=x["rank"],
                    plain=a,cube=pow(a,3,n),B31_unfactored=True))
                if len([z for z in selected if z["group"]==g])==TARGET:break
        assert len([z for z in selected if z["group"]==g])==TARGET,(g,len(checked))
        screens[g]=checked
    assert len(selected)==8 and len(set(z["N"] for z in selected))==8
    out=dict(experiment="n25_online_public_manifest_only",
        preregistration=PREREG,selected_public_rows=selected,
        selected_sha256=hashlib.sha256(canonical(selected).encode()).hexdigest(),
        public_screenings=screens, n_in_frame=len(ns),range_N=[LO,HI],
        prime_construction_range=[PRIMES_MIN,PRIMES_MAX],
        salt_population=SALT,salt_base=BASE_SALT,pool=list(BASES),
        factor_order_and_qpe_not_inspected_for_selection=True,
        zero_QPU=True,qpu_jobs_submitted=0)
    return out
if __name__=="__main__":
    j=build()
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(j,indent=2)+"\n")
    print("N25 PUBLIC SHA",j["selected_sha256"],"frame",j["n_in_frame"],flush=True)
    for g in screens if False else ("G1_mod3_1","G2_mod3_2"):
        print(g,"B31 screens",len(j["public_screenings"][g]),
            "selected",[(x["N"],x["base"]) for x in j["selected_public_rows"] if x["group"]==g],flush=True)
    print("no model scoring / no QPU")
