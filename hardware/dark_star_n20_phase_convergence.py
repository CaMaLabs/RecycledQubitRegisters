#!/usr/bin/env python3
"""Independent fixed-N n20 v3 numerical convergence check; ZERO QPU."""
from __future__ import annotations
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import dark_star_n20_public_survivor_v3 as v3

INDEPENDENT_SALT="QRR-n20-phase-v3-independent-validation-20261014-2049"
SAMPLES=8192
REV="QRR-n20-phase-independent-replication-v1"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ell",type=int,choices=v3.ELLS,required=True)
    ap.add_argument("--group",choices=v3.GROUPS,required=True)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    original_path=Path(f"results/dark_star_ptp/dark_star_n20_v3_ell{args.ell}_{args.group}.json")
    original=json.loads(original_path.read_text())
    manifest=json.loads(v3.MANIFEST_FILE.read_text())
    expected=[r for r in manifest["selected_public_rows"]
              if r["ell"]==args.ell and r["group"]==args.group]
    assert manifest["manifest_sha256"]==original["manifest_sha256"]==v3.hashlib.sha256(
        v3.canonical(manifest["selected_public_rows"]).encode()).hexdigest()
    assert len(expected)==len(original["rows"])==v3.PER_GROUP
    assert [r["N"] for r in expected]==[r["N"] for r in original["rows"]]

    # Deliberately mutate ONLY numerical-sampling constants in-process.
    # Original committed v3 source/default/results are untouched.
    v3.PHASE_SAMPLES=SAMPLES
    v3.PHASE_SALT=INDEPENDENT_SALT
    result={
      "experiment":"dark_star_n20_v3_phase_convergence",
      "revision":REV,
      "zero_qpu":True,"qpu_jobs_submitted":0,
      "preregistration":"docs/DARK_STAR_N20_PHASE_CONVERGENCE_PREREG.md",
      "ell":args.ell,"group":args.group,
      "manifest_sha256":manifest["manifest_sha256"],
      "phase_sampling_salt":INDEPENDENT_SALT,
      "phase_samples":SAMPLES,
      "per_stage_95percent_Hoeffding":math.sqrt(math.log(40)/(2*SAMPLES)),
      "new_population":False,
      "rows":[],"complete":False
    }
    path=args.out or Path(f"results/dark_star_ptp/dark_star_n20_phase_validation_ell{args.ell}_{args.group}.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    checkpoint=path.with_suffix(".partial.json")
    for i,spec in enumerate(expected,1):
        print(f"[{i}/{len(expected)}] independent sampling N={spec['N']} ell={args.ell} {args.group}",flush=True)
        result["rows"].append(v3.simulate_row(spec))
        checkpoint.write_text(json.dumps(result,indent=2)+"\n")
    s=v3.summary(result["rows"],original["public_classical_screening"],args.ell,args.group)
    result["summary"]=s
    keys=("ladder_vs_plain","ladder_vs_always3")
    result["comparison_to_frozen_4096_run"]={}
    for key in keys:
        old=original["summary"]["comparisons"][key]
        new=s["comparisons"][key]
        assert new["both_success"]==old["both_success"],"factor success coverage changed unexpectedly"
        x=old["ratio_sum_ccx_per_success"]
        y=new["ratio_sum_ccx_per_success"]
        diff=(y-x) if (x is not None and y is not None) else None
        result["comparison_to_frozen_4096_run"][key]={
          "original_ratio":x,"independent_8192_ratio":y,
          "delta_new_minus_original":diff,
          "absolute_drift_gt_0p03":abs(diff)>0.03 if diff is not None else None,
          "original_improved_tied_worsened":[old["improved"],old["tied"],old["worsened"]],
          "new_improved_tied_worsened":[new["improved"],new["tied"],new["worsened"]],
        }
    result["complete"]=True
    result["completed_at_utc"]=datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(result,indent=2)+"\n")
    for k,v in result["comparison_to_frozen_4096_run"].items():
        print(k,v,flush=True)
    print("INDEPENDENT PHASE SAMPLING COMPLETE; ZERO QPU")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
