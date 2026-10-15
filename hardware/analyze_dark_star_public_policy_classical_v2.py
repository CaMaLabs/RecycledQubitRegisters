#!/usr/bin/env python3
"""Merge and validate the three independently executed preregistered v2 shards."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import dark_star_public_policy_classical_v2 as study


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shard-dir",type=Path,default=Path("v2-shards"))
    ap.add_argument("--out",type=Path,default=Path(
        "results/dark_star_ptp/dark_star_public_policy_classical_v2.json"))
    args=ap.parse_args()
    manifest,_,sha=study.public_manifest()
    shards=[]
    for ell in study.ELLS:
        p=args.shard_dir / f"ell{ell}" / f"ell{ell}.json"
        obj=json.loads(p.read_text())
        assert obj.get("complete") and obj.get("zero_qpu") and obj.get("qpu_jobs_submitted")==0
        assert obj.get("manifest_sha256")==sha and obj.get("ell")==ell
        assert len(obj["rows"])==2*study.PER_GROUP
        assert all(r["ell"]==ell for r in obj["rows"])
        for group in ("trigger","control"):
            assert len([r for r in obj["rows"] if r["group"]==group])==study.PER_GROUP
        shards.append(obj)
    rows=[row for shard in shards for row in shard["rows"]]
    assert len(rows)==len(manifest)==144
    assert [{k:r[k] for k in ("ell","group","N","base","transformed_base")}
            for r in rows] == manifest, "Shard rows do not match frozen manifest/order"
    assert all(r["validation_only"]["order_identity_pass"] and
               r["validation_only"]["witness_preservation_pass"] for r in rows)
    summary={str(s["ell"]):s["summaries"] for s in shards}
    all_unsolved=[r for r in rows if r["quantum_required"]]
    ccx_den=sum(r["policy"]["never"]["expected_ccx"] for r in all_unsolved)
    def global_ratio(k):
        return (sum(r["policy"][k]["expected_ccx"] for r in all_unsolved) /
                ccx_den) if ccx_den else None
    out={
        "experiment":"dark_star_public_policy_classical_v2",
        "revision":study.REV,
        "preregistration":"docs/DARK_STAR_PUBLIC_POLICY_CLASSICAL_V2_PREREG.md",
        "manifest_sha256":sha,
        "selected_rows":len(rows),
        "zero_qpu":True,"qpu_jobs_submitted":0,
        "complete":True,
        "classically_solved_common":len(rows)-len(all_unsolved),
        "all_unresolved_rows":len(all_unsolved),
        "paired_eligible_rows":sum(r["eligible_paired_quantum"] for r in rows),
        "population_policy_unresolved_ccx_ratio":{
            k:global_ratio(k) for k in ("always","trigger","conservative_ell3")
        },
        "per_ell_summaries":summary,
        "rows":rows,
        "claim_boundary":("Exact ideal nearest-bin QPE plus explicit public convergent "
                          "factor witness and polynomial logical reversible-arithmetic "
                          "CCX, after bounded cheap classical prefilters; not QPU "
                          "fidelity/runtime, RSA-scale factoring, or universal speedup."),
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print("V2 FROZEN MANIFEST",sha)
    print("total rows",len(rows),"classical solved",out["classically_solved_common"],
          "paired eligible",out["paired_eligible_rows"])
    for ell in study.ELLS:
        for group in ("trigger","control"):
            s=summary[str(ell)][group]
            q=s["paired"]["trigger"]
            a=s["paired"]["always"]
            print("ell",ell,group,"eligible",s["eligible_paired"],
                  "always/never",a["aggregate_ccx_ratio"],
                  "trigger/never",q["aggregate_ccx_ratio"],
                  "always bootstrap 95%",a["bootstrap_95pct_aggregate_ratio"])
    print("All unsolved population policy ratios",out["population_policy_unresolved_ccx_ratio"])
    print("NO QPU JOB SUBMITTED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
