#!/usr/bin/env python3
"""Frozen 23-bit public-selected full-outcome QPE bound shard (one N only).

Reuses the previously independently vetted 22-bit FFT/65-bin/empirical-
Bernstein implementation without fitting on any new N23 phase outcome.
ZERO QPU jobs; no IBM account, runtime, backend or Qiskit imports.
Research direction: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
import time
from pathlib import Path

import dark_star_n22_numerical_precision_audit as prec
import dark_star_n22_full_tail_qpe_holdout as tail
import dark_star_n22_selector_vs_cube as classical
import dark_star_recycled_scalable_arithmetic_audit as model

ROOT=Path("results/dark_star_ptp")
MANIFEST=ROOT/"dark_star_n23_full_outcome_public_manifest.json"
PREREG="docs/DARK_STAR_N23_FULL_OUTCOME_CUBE_PREREG.md"
N_PER_GROUP=4
N_ALL=8
BITS=23
STAGES=tuple(range(4,47,2))
FAMILY=N_ALL*2*len(STAGES)*2*2
ALPHA=.01
assert len(STAGES)==22 and FAMILY==1408

# Prespecified extension from previously verified 22-bit high-precision
# model: same 131072 samples, W32, full FFT <=18, alpha/seed, only 22nd
# stage m46 and the correct simultaneous test family denominator change.
prec.STAGES=STAGES
prec.TOTAL_TESTS=FAMILY
prec.DELTA=ALPHA/FAMILY
prec.LOG=math.log(2/prec.DELTA)
assert prec.N_SAMPLES==131072 and prec.EXACT_M==18 and prec.W==32
assert prec.SALT=="QRR-n22-precision-audit-iid-20261015"


def manifest_read():
    d=json.loads(MANIFEST.read_text())
    rows=d["selected_public_rows"]
    canonical=json.dumps(rows,sort_keys=True,separators=(",",":"))
    assert hashlib.sha256(canonical.encode()).hexdigest()==d["selected_sha256"]
    assert d["zero_QPU"] and d["qpu_jobs_submitted"]==0
    assert len(rows)==8 and len({r["N"] for r in rows})==8
    assert all((1<<22)<=r["N"]<(1<<23) for r in rows)
    for group in ("trigger","control"):
        rr=[r for r in rows if r["group"]==group]
        assert len(rr)==4
        assert all(r["N"]%3==(2 if group=="trigger" else 1) for r in rr)
        assert all(r["public_policies"]=={"plain":r["base"],"cube":pow(r["base"],3,r["N"])}
                   for r in rr)
        for r in rr:
            src=next(x for x in d["public_screenings"][group] if x["N"]==r["N"])
            assert src["base"]==r["base"] and src["rank"]==r["rank"] and not src["public_B31_factored"]
    return d


def score_one(spec):
    n,a=spec["N"],spec["base"]
    b=pow(a,3,n)
    # Selection was committed on main BEFORE any of this model/oracle work.
    t=time.process_time()
    cl=classical.public_additional_classical(n)
    assert cl["classically_factored"],(n,cl)
    f=int(cl["factor"])
    assert 1<f<n and n%f==0,(n,f)
    certified_plain=tail.public_factor_certificates(n,a)
    certified_cube=tail.public_factor_certificates(n,b)
    # Public result, including the proper gcd witnesses, generated before
    # hidden p/q/validation r are used for simulating eigenphases.
    p,q=tail.validation_factors(n)
    assert p*q==n and p!=q and p>=11 and q>=11
    lam=math.lcm(p-1,q-1)
    r=model.multiplicative_order_from_lambda(a,n,lam)
    r3=model.multiplicative_order_from_lambda(b,n,lam)
    assert r3==r//math.gcd(r,3)
    gatecache={}
    phasecache={}
    plain=prec.score_base(n,a,r,certified_plain,gatecache,phasecache)
    cube=prec.score_base(n,b,r3,certified_cube,gatecache,phasecache)
    assert len(plain["all_stages"])==len(cube["all_stages"])==22
    assert plain["all_stages"][-1]["m"]==cube["all_stages"][-1]["m"]==46
    result=tail.classify(plain,cube)
    # No hidden factor enters the online CF acceptance.
    assert all(0<=z["lower"]<=z["upper"]<=1+1e-7
               for pol in (plain,cube) for z in pol["all_stages"])
    return {**spec,"additional_public_classical":cl,
            "validation_only":{"p":p,"q":q,"order_plain":r,
                  "order_cube":r3,"odd_power_order_identity_verified":True},
            "plain":plain,"cube":cube,"cube_vs_plain":result,
            "model_CPU_seconds":round(time.process_time()-t,5),
            "zero_QPU":True}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--group",choices=("trigger","control"),required=True)
    ap.add_argument("--index",choices=(0,1,2,3),type=int,required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    manifest=manifest_read()
    group=args.group
    entries=[x for x in manifest["selected_public_rows"] if x["group"]==group]
    spec=entries[args.index]
    print("PUBLIC N23 FROZEN SHA",manifest["selected_sha256"],"group",group,
          "index",args.index,"N",spec["N"],"base",spec["base"],flush=True)
    selftests=prec.check_selftests()
    assert selftests["passed"] and prec.TOTAL_TESTS==FAMILY
    row=score_one(spec)
    result=dict(
        experiment="dark_star_n23_full_outcome_new_size_v1",
        preregistration=PREREG,
        public_manifest_sha256=manifest["selected_sha256"],
        selected_index=args.index,
        group=group,complete=True,rows=[row],
        public_screened_in_panel=manifest["public_screenings"][group],
        numerical_method={
           "full_outcome_FFT_m_max":prec.EXACT_M,
           "centered_head_halfwidth":prec.W,
           "eigenphase_draws_if_order_large":prec.N_SAMPLES,
           "seed_salt":prec.SALT,
           "simultaneous_alpha":ALPHA,"union_family":FAMILY,
           "phase_bits_stages":list(STAGES),
           "sampling_assumption":"99% empirical Bernstein conditional on independent uniform eigenphase draws; seeded CPython PRNG not a certified random source",
           "omitted_outcome_bound":1/(2*prec.W-1),
           "floating_point_caveat":"Not formally outward-rounded machine intervals"},
        selftests=selftests,
        zero_QPU=True,qpu_jobs_submitted=0,
        claim_boundary="Classically factored 23bit public N; ideal-QPE full-outcome head and probabilistically bounded tails; generic logical CCX only, not QPU/hardware/rsa/fault-tolerant advantage",
        completed_utc=datetime.now(timezone.utc).isoformat())
    width=model.arithmetic_width(spec["N"])
    assert width["arithmetic_qubits_excluding_phase"]==72
    result["logical_width"]={
        "arithmetic_workspace":72,"wide_peak":118,"recycled_peak":73}
    out=args.out or ROOT/f"dark_star_n23_full_outcome_{group}_index{args.index}.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print("RESULT",group,args.index,spec["N"],
          "classical",row["additional_public_classical"]["first_factor_source"],
          "ord",row["validation_only"]["order_plain"],"->",row["validation_only"]["order_cube"],
          "certificates",row["plain"]["strict_public_CF_certificate_count"],
          row["cube"]["strict_public_CF_certificate_count"],
          "bounded_ratio",row["cube_vs_plain"]["ratio"],
          "status",row["cube_vs_plain"]["status"],
          "CPU",row["model_CPU_seconds"],"ZERO QPU",flush=True)


if __name__=="__main__":
    main()
