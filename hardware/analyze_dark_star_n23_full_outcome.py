#!/usr/bin/env python3
"""Merge/verify 8 original N23 full-outcome QPE numerical shards, zero QPU."""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter
from pathlib import Path

from dark_star_n23_full_outcome_public_manifest import canonical

ROOT=Path("results/dark_star_ptp")
MANIFEST=ROOT/"dark_star_n23_full_outcome_public_manifest.json"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shards",type=Path,default=Path("n23-shards"))
    ap.add_argument("--output",type=Path,
                    default=ROOT/"dark_star_n23_full_outcome_all_eight.json")
    a=ap.parse_args()
    m=json.loads(MANIFEST.read_text())
    sha=hashlib.sha256(canonical(m["selected_public_rows"]).encode()).hexdigest()
    assert m["selected_sha256"]==sha
    seen=set()
    rows=[]
    sources=[]
    for group in ("trigger","control"):
        entries=[x for x in m["selected_public_rows"] if x["group"]==group]
        assert len(entries)==4
        for index,spec in enumerate(entries):
            src=a.shards/f"{group}_{index}"/f"{group}_{index}.json"
            d=json.loads(src.read_text())
            assert d["public_manifest_sha256"]==sha and d["complete"]
            assert d["zero_QPU"] and d["qpu_jobs_submitted"]==0
            assert d["group"]==group and d["selected_index"]==index and len(d["rows"])==1
            r=d["rows"][0]
            assert all(r[k]==spec[k] for k in ("N","base","group","rank","public_policies"))
            assert r["N"] not in seen
            seen.add(r["N"])
            assert r["validation_only"]["odd_power_order_identity_verified"]
            assert r["validation_only"]["order_cube"]==r["validation_only"]["order_plain"]//__import__("math").gcd(r["validation_only"]["order_plain"],3)
            assert r["additional_public_classical"]["classically_factored"]
            f=r["additional_public_classical"]["factor"]
            assert 1<f<r["N"] and r["N"]%f==0
            assert len(r["plain"]["all_stages"])==len(r["cube"]["all_stages"])==22
            assert all(z["m"] in range(4,47,2) and
                       0<=z["lower"]<=z["upper"]<=1+1e-7
                       for pol in ("plain","cube") for z in r[pol]["all_stages"])
            assert r["zero_QPU"]
            src_status=r["cube_vs_plain"]["status"]
            ratio=r["cube_vs_plain"]["ratio"]
            if r["plain"]["exact_factor_incapable"] or r["cube"]["exact_factor_incapable"]:
                assert src_status=="factor_incapable_or_uncertified" and ratio==[None,None]
            elif src_status=="cube_model_win":
                assert ratio[1]<1
            elif src_status=="cube_model_loss":
                assert ratio[0]>1
            else:
                assert src_status in ("inconclusive","ratio_unbounded","factor_incapable_or_uncertified")
            rows.append(r)
            sources.append(str(src))
            print("VERIFIED",group,index,"N",r["N"],"classical",r["additional_public_classical"]["first_factor_source"],
                  "CF certificates",r["plain"]["strict_public_CF_certificate_count"],
                  r["cube"]["strict_public_CF_certificate_count"],
                  "ratio",ratio,"status",src_status,flush=True)
    assert len(rows)==8 and len(seen)==8
    group_summaries={}
    for group in ("trigger","control"):
        grp=[r for r in rows if r["group"]==group]
        coverage_plain=sum(not r["plain"]["exact_factor_incapable"] for r in grp)
        coverage_cube=sum(not r["cube"]["exact_factor_incapable"] for r in grp)
        both=sum(not r["plain"]["exact_factor_incapable"] and
                 not r["cube"]["exact_factor_incapable"] for r in grp)
        statuses=Counter(r["cube_vs_plain"]["status"] for r in grp)
        pass_gate=(both>=3 and coverage_cube>=coverage_plain and
                   statuses["cube_model_win"]>=3) if group=="trigger" else None
        group_summaries[group]=dict(n=len(grp),coverage_plain=coverage_plain,
            coverage_cube=coverage_cube,both_capable=both,
            statuses=dict(statuses),predeclared_trigger_primary_pass=pass_gate,
            public_screened=len(m["public_screenings"][group]),
            B31_factored=sum(x["public_B31_factored"] for x in m["public_screenings"][group]),
            post_B31_all_classically_factored=all(r["additional_public_classical"]["classically_factored"]
                                             for r in grp))
    out=dict(experiment="dark_star_fresh_23bit_full_outcome_head_and_tail",
        zero_QPU=True,qpu_jobs_submitted=0,complete=True,manifest_sha256=sha,
        selected_public_rows=m["selected_public_rows"],
        public_screening=m["public_screenings"],
        predeclared_primary_trigger_pass=group_summaries["trigger"]["predeclared_trigger_primary_pass"],
        group_summaries=group_summaries,
        sample_method="full FFT m<=18, centered 65 ideal bins m>18, 131072 sampled/eigenphase-exhaustive, nominal 99%-simultaneous EB 1408 tests",
        confidence_caveat="fixed PRNG not certified IID; floating-point trigonometry not formally interval rounded; no QPU",
        logical_width=dict(coherent_arithmetic=72,wide_peak=118,recycled_peak=73),
        rows=rows,sources=sources)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2)+"\n")
    print("8/8 VERIFIED; B31 SELECTED ONLY; PRIMARY",out["predeclared_primary_trigger_pass"],"ZERO QPU",flush=True)

if __name__=="__main__":
    main()
