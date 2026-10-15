#!/usr/bin/env python3
"""PUBLIC-only deterministic 22-bit selection manifest, BEFORE any QPE/order scoring.

No private p,q/order or simulated outcome is saved in the frozen manifest.
All acceptance/exclusion is based on N, public hash rank and public B31 GCD/p−1.
Research lead: Chase Lunsford / CaMaLabs. NO QPU.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import dark_star_ptp_shor_audit as ds
import dark_star_public_multichoice_survivor_holdout as mc

NLO=1<<21
NHI=(1<<22)-1
SALT="QRR-n22-ladder-versus-cube-v1-20261014"
BASE_SALT="QRR-n22-public-base-v1-20261014"
POOL=(2,3,5,7,11,13,17,19,23,29,31)
TARGET=6
CAP=400
OUT=Path("results/dark_star_ptp/dark_star_n22_public_manifest.json")


def hash_int(*args):
    return int.from_bytes(hashlib.sha256("|".join(map(str,args)).encode()).digest(),"big")


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"))


def public_base(n,group):
    offset=hash_int(BASE_SALT,group,n)%len(POOL)
    return next(int(POOL[(offset+i)%len(POOL)]) for i in range(len(POOL))
                if math.gcd(n,POOL[(offset+i)%len(POOL)])==1)


def semiprime_N_only():
    primes=ds.sieve_primes(NHI)
    out=set()
    for i,p in enumerate(primes):
        if p<11:continue
        if p*p>NHI:break
        for q in primes[i+1:]:
            n=p*q
            if n>NHI:break
            if n>=NLO and n%3 and q>p:
                out.add(n)
    return out


def policy_exponents(n):
    ladder=next((e for e in (3,5,7) if n%e not in (0,1)),0)
    return {"plain":0,"always3":3,"ladder":ladder}


def build():
    Ns=semiprime_N_only()
    selected=[]
    panels={}
    for group,mod in (("trigger",2),("control",1)):
        candidates=sorted((n for n in Ns if n%3==mod),
                    key=lambda n:(hash_int(SALT,group,n),n))
        screen=[]
        chosen=[]
        for n in candidates[:CAP]:
            a=public_base(n,group)
            cl=mc.classical_cascade(n,a)
            entry={"N":n,"base":a,"scan_rank":len(screen)+1,
                "public_B31_factored":bool(cl["found"]),
                "public_factor":cl["factor"],
                "classical_source":cl["source"],
                "primitive_operation_counts":cl["counts"]}
            screen.append(entry)
            if not cl["found"]:
                chosen.append({"N":n,"base":a,"group":group,
                    "scan_rank":len(screen),"public_policy_exponents":policy_exponents(n)})
                if len(chosen)==TARGET:break
        if len(chosen)!=TARGET:
            raise RuntimeError(f"{group}: {len(chosen)} B31 survivors from {len(screen)} screened; prereg cap {CAP}")
        selected.extend(chosen)
        panels[group]=screen
    assert len(selected)==12 and len({r["N"] for r in selected})==12
    for s in selected:
        g=s["group"]
        assert s["N"]%3==(2 if g=="trigger" else 1)
        assert s["public_policy_exponents"]["ladder"]==(
           3 if g=="trigger" else next((e for e in (5,7) if s["N"]%e not in (0,1)),0))
    return {"experiment":"dark_star_n22_public_survivor_manifest_v1",
       "preregistration":"docs/DARK_STAR_N22_SELECTOR_VS_CUBE_PREREG.md",
       "selection_salt":SALT,"base_salt":BASE_SALT,
       "N_range":[NLO,NHI],"target_per_group":TARGET,
       "max_public_screens_per_group":CAP,
       "public_screenings":panels,
       "selected_public_rows":selected,
       "selected_manifest_sha256":hashlib.sha256(canonical(selected).encode()).hexdigest(),
       "zero_qpu":True,"qpu_jobs_submitted":0,
       "claim_boundary":"PUBLIC-only selection; no p/q/order or quantum cost disclosed before manifest freeze"}


def main():
    obj=build()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(obj,indent=2)+"\n")
    print("PUBLIC N22 SELECTED MANIFEST",obj["selected_manifest_sha256"])
    for g in ("trigger","control"):
        scans=obj["public_screenings"][g]
        rows=[z for z in obj["selected_public_rows"] if z["group"]==g]
        print(g,"screened",len(scans),"B31_factored",sum(x["public_B31_factored"] for x in scans),
              "selected",len(rows),
              "public_only_n",[x["N"] for x in rows],flush=True)
    print("NO VALIDATION FACTORS/ORDERS/QUANTUM SCORE CALCULATED. NO QPU.")
if __name__=="__main__":main()
