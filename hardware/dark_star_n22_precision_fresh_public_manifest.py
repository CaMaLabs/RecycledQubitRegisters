#!/usr/bin/env python3
"""Freeze FRESH n22 PUBLIC N/base/B31-survivor manifest BEFORE quantum scoring.

Research lead Chase Lunsford / CaMaLabs. No private factor/order or QPE endpoints
written. Candidate synthetic semiprime frame is never ranked with p/q.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path

import dark_star_n22_public_manifest as oldn22
import dark_star_public_multichoice_survivor_holdout as mc

SALT="QRR-N22-FRESH-PRECISION-20261015"
BASE_SALT="QRR-N22-FRESH-PRECISION-BASE-20261015"
ROOT=Path("results/dark_star_ptp")
OUT=ROOT/"dark_star_n22_precision_fresh_public_manifest.json"
PER_GROUP=4
CAP=500
POOL=(2,3,5,7,11,13,17,19,23,29,31)


def sha(*items):
    return int.from_bytes(hashlib.sha256("|".join(map(str,items)).encode()).digest(),"big")


def canonical(rows):
    return json.dumps(rows,sort_keys=True,separators=(",",":"))


def public_base(n,group):
    start=sha(BASE_SALT,group,n)%len(POOL)
    for i in range(len(POOL)):
        a=int(POOL[(start+i)%len(POOL)])
        if math.gcd(a,n)==1:return a
    raise AssertionError("No coprime public base")


def create():
    old=json.loads((ROOT/"dark_star_n22_public_manifest.json").read_text())
    previous=json.loads((ROOT/"dark_star_n22_full_tail_public_manifest.json").read_text())
    excluded={r["N"] for r in old["selected_public_rows"]}
    excluded.update(r["N"] for r in previous["selected_public_rows"])
    assert len(excluded)==16
    ns=oldn22.semiprime_N_only()
    selections=[]
    screenings={}
    for group,mod in (("trigger",2),("control",1)):
        candidates=sorted((n for n in ns if n%3==mod and n not in excluded),
            key=lambda n:(sha(SALT,group,n),n))
        screen=[]
        chosen=[]
        for n in candidates[:CAP]:
            a=public_base(n,group)
            check=mc.classical_cascade(n,a)
            scan=dict(N=n,base=a,rank=len(screen)+1,
                public_B31_factored=bool(check["found"]),classical_first_source=check["source"],
                public_factor=check["factor"],primitive_operation_counts=check["counts"])
            screen.append(scan)
            if not check["found"]:
                chosen.append(dict(N=n,base=a,group=group,rank=scan["rank"],
                    public_policies=dict(plain=a,cube=pow(a,3,n))))
                if len(chosen)==PER_GROUP:break
        assert len(chosen)==PER_GROUP,(group,len(chosen),len(screen))
        selections+=chosen
        screenings[group]=screen
    assert len(selections)==8 and len({x["N"] for x in selections})==8
    assert not ({x["N"] for x in selections}&excluded)
    return dict(experiment="qrr_n22_independent_precision_holdout_public_manifest",
        preregistration="docs/DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_PREREG.md",
        selection_salt=SALT,base_salt=BASE_SALT,
        previous_n22_excluded=sorted(excluded),
        frame=[1<<21,(1<<22)-1],
        selected_public_rows=selections,public_screenings=screenings,
        selected_sha256=hashlib.sha256(canonical(selections).encode()).hexdigest(),
        zero_QPU=True,qpu_jobs_submitted=0,
        note="This contains ONLY public N, coprime base, public transforms and bounded classical results; private factors/orders intentionally absent.")

def main():
    v=create()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(v,indent=2)+"\n")
    print("FROZEN INDEPENDENT N22 PRECISION PUBLIC SHA",v["selected_sha256"],flush=True)
    for group in ("trigger","control"):
        rows=[r for r in v["selected_public_rows"] if r["group"]==group]
        scans=v["public_screenings"][group]
        print(group,"screened",len(scans),"B31 classically factored",
              sum(x["public_B31_factored"] for x in scans),
              "B31 survivors",[(r["N"],r["base"]) for r in rows],flush=True)
    print("ZERO QPU; NO ORDERS OR QPE COSTS CALCULATED",flush=True)

if __name__=="__main__":main()
