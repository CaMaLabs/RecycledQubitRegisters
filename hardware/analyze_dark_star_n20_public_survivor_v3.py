#!/usr/bin/env python3
"""Validate/merge all six v3 preregistered classical-survivor shards."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import dark_star_n20_public_survivor_v3 as study


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",type=Path,default=Path("n20-v3-shards"))
    ap.add_argument("--manifest",type=Path,default=study.MANIFEST_FILE)
    ap.add_argument("--out",type=Path,default=Path(
        "results/dark_star_ptp/dark_star_n20_v3_full_holdout.json"))
    args=ap.parse_args()
    manifest=json.loads(args.manifest.read_text())
    spec=manifest["selected_public_rows"]
    h=hashlib.sha256(study.canonical(spec).encode()).hexdigest()
    assert h==manifest["manifest_sha256"]
    assert len(spec)==72 and len({r["N"] for r in spec})==72

    shards={}
    combined=[]
    for ell in study.ELLS:
        shards[str(ell)]={}
        for group in study.GROUPS:
            path=args.input_dir / f"ell{ell}_{group}" / f"ell{ell}_{group}.json"
            data=json.loads(path.read_text())
            assert data["complete"] and data["zero_qpu"] and data["qpu_jobs_submitted"]==0
            assert data["ell"]==ell and data["group"]==group
            assert data["manifest_sha256"]==h
            assert len(data["rows"])==study.PER_GROUP
            assert [r["N"] for r in data["rows"]]==[
                r["N"] for r in spec if r["ell"]==ell and r["group"]==group
            ]
            assert all(r["validation_only"]["order_identity_ok"] and
                       r["validation_only"]["witness_preservation_ok"] for r in data["rows"])
            assert all(r["no_qpu_jobs"] for r in data["rows"])
            shards[str(ell)][group]=data["summary"]
            combined.extend(data["rows"])
    assert len(combined)==len(spec)
    assert [{key:r[key] for key in ("ell","group","N","base","rank_in_panel")}
            for r in combined]==spec

    # Gate requires positive evidence in ALL trigger cells, including ell7.
    trigger_pass={}
    for ell in study.ELLS:
        s=shards[str(ell)]["trigger"]
        c=s["comparisons"]["ladder_vs_plain"]
        trigger_pass[str(ell)]=(
            c["coverage_method"]>=c["coverage_reference"] and
            c["both_success"]>0 and
            c["ratio_sum_ccx_per_success"] is not None and
            c["ratio_sum_ccx_per_success"]<1 and
            c["improved"]>c["both_success"]/2
        )
    ladder_vs_cube=[shards[str(ell)]["trigger"]["comparisons"]["ladder_vs_always3"]
                    for ell in study.ELLS]
    beats_cube=any(c["both_success"]>0 and c["ratio_sum_ccx_per_success"] is not None
                   and c["ratio_sum_ccx_per_success"]<1-1e-10
                   and c["improved"]>0 for c in ladder_vs_cube)
    no_worse_cube=all(c["ratio_sum_ccx_per_success"] is not None and
                      c["ratio_sum_ccx_per_success"]<=1+1e-10
                      for c in ladder_vs_cube)
    broad=all(trigger_pass.values()) and beats_cube and no_worse_cube
    width=study.model.arithmetic_width(spec[0]["N"])
    assert width["arithmetic_qubits_excluding_phase"]==63
    out={
      "experiment":"dark_star_n20_public_survivor_v3",
      "revision":study.REV,"complete":True,
      "zero_qpu":True,"qpu_jobs_submitted":0,
      "manifest_sha256":h,"selected_classical_survivors":len(combined),
      "total_public_candidates_screened":sum(
          len(v) for v in manifest["public_screenings"].values()),
      "total_public_classically_factored_in_scan":sum(
          sum(s["classically_factored"] for s in v)
          for v in manifest["public_screenings"].values()),
      "sampling":{"phase_samples_per_stage":study.PHASE_SAMPLES,
                  "nearest_bin_only":True,
                  "all_bin_distribution":False,
                  "per_stage_95pct_Hoeffding_absolute_bound":
                      __import__("math").sqrt(__import__("math").log(40)/(2*study.PHASE_SAMPLES))},
      "width_independent_of_dark_star":{
         "arithmetic_qubits_excluding_phase":63,
         "wide_peak_logical_qubits":103,
         "recycled_peak_logical_qubits":64,
         "recycled_width_reduction":39/103},
      "per_panel":shards,
      "frozen_primary_gate":{
         "trigger_pass_by_ell":trigger_pass,
         "ladder_better_than_always_cube_on_some_trigger":beats_cube,
         "ladder_not_worse_than_always_cube_on_all_triggers":no_worse_cube,
         "general_public_selector_pass":broad},
      "rows":combined,
      "claim_boundary":("Deterministic 4096-phase-sample approximation of an ideal "
                        "nearest-bin QPE resource model; exact public CF factor "
                        "verification. Not hardware fidelity, wall-clock speed, "
                        "quantum advantage, full all-bin distribution or RSA break."),
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print("VERIFIED public manifest",h)
    print("screened",out["total_public_candidates_screened"],
          "classically_solved",out["total_public_classically_factored_in_scan"],
          "public_survivors",len(combined))
    for ell in study.ELLS:
        for group in study.GROUPS:
            s=shards[str(ell)][group]
            print(ell,group,"ladder/plain",s["comparisons"]["ladder_vs_plain"],
                  "ladder/always3",s["comparisons"]["ladder_vs_always3"])
    print("FROZEN BROAD SELECTOR GATE",out["frozen_primary_gate"])
    print("ZERO QPU JOB SUBMITTED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
