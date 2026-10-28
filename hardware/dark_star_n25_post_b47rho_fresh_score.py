#!/usr/bin/env python3
"""New SHA-FROZEN 8-case post-B47rho64 N25 QPE on-demand CF/GCD holdout.

Research lead Chase Lunsford / CaMaLabs. ZERO QPU.
Reuse original N25 24-stage, 4096 IID ideal-QPE and public measured-y
on-demand CF/GCD + structural source-gate scorer with a NEW precommitted
fully public B31+B47 rho64 classical-survivor cohort. No changes to sampling
physics, statistical confidence, stage counts, original results or classifier.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math
from pathlib import Path
import dark_star_n25_online_qpe_arithmetic as verified
import dark_star_n25_online_public_manifest as pub

ROOT=Path("results/dark_star_ptp")
MANIFEST=ROOT/"dark_star_n25_post_b47rho_fresh_manifest.json"
PREREG="docs/DARK_STAR_N25_POST_B47RHO_FRESH_COHORT_PREREG.md"
FROZEN_SHA="e46425355e422ff32d167920d7ddc80ada0ed8733c73048912133db6f79526d2"
BASE_SALT="QRR-N25-B47RHO64-FRESH-BASE-20261028"
PHASE_SALT="QRR-N25-B47RHO64-FRESH-PHASE-20261028"
OUT_ALL=ROOT/"dark_star_n25_post_b47rho_fresh_all8.json"
REV="dark-star-n25-post-b47rho64-fresh-8-24stage-v1-20261028"

def enforce_manifest():
    manifest=json.loads(MANIFEST.read_text())
    rows=manifest["selected_public_rows"]
    sha=hashlib.sha256(pub.canonical(rows).encode()).hexdigest()
    if sha!=FROZEN_SHA or manifest["selected_sha256"]!=FROZEN_SHA:
        raise AssertionError("FROZEN PUBLIC ROW SHA does not match permanent manifest")
    original=json.loads((ROOT/"dark_star_n25_online_public_manifest.json").read_text())
    assert manifest["original_n25_manifest_sha256"]==original["selected_sha256"]=="66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7"
    prior_Ns={int(r["N"]) for r in original["selected_public_rows"]}
    assert len(rows)==8 and len(set(r["N"] for r in rows))==8
    assert prior_Ns.isdisjoint({r["N"] for r in rows})
    assert manifest["original_cohort_sample_overlap"]==0
    assert manifest["selection_public_only_B31_and_B47rho64"]
    assert manifest["factor_order_and_qpe_not_inspected_for_selection"]
    assert manifest["zero_QPU"] and manifest["qpu_jobs_submitted"]==0
    assert manifest["population_salt"]=="QRR-N25-B47RHO64-FRESH-POP-20261028"
    assert manifest["base_salt"]==BASE_SALT
    assert manifest["screening_cap_per_group"]==1200
    assert manifest["selected_per_group"]==4
    for r in rows:
        assert 1<<24 <= r["N"] <1<<25
        assert r["B31_unfactored"] and r["B47rho64_unsolved"]
        assert r["cube"]==pow(r["base"],3,r["N"])
        orig=next(x for x in manifest["public_screenings"][r["group"]] if x["N"]==r["N"])
        assert orig["rank"]==r["rank"] and orig["base"]==r["base"]
        assert not orig["B31_factored"]
        assert orig["B47rho64_executed"]
        assert not orig["B47rho64_public_budget"]["classically_solved"]
    return manifest


def set_original_scoring_engine_for_new_frozen_manifest():
    verified.MANIFEST=MANIFEST
    verified.PREREG=PREREG
    verified.SHA=FROZEN_SHA
    verified.SEED=PHASE_SALT
    # old code's read_public() checks public base SHA; supply NEW fixed salt.
    pub.BASE_SALT=BASE_SALT
    assert verified.STAGES==tuple(range(4,51,2))
    assert verified.SAMPLES==4096 and verified.W==32 and verified.SHOTS==4
    assert verified.FAMILY==1536 and verified.ALPHA==.01
    assert verified.LOG==math.log(2/(verified.ALPHA/verified.FAMILY))
    assert verified.prec.LOG==verified.LOG


def score_one(index):
    mf=enforce_manifest()
    set_original_scoring_engine_for_new_frozen_manifest()
    selected=mf["selected_public_rows"][index]
    # True original proven numerical method and original output schema,
    # differing ONLY in frozen new public rows and distinct phase random salt.
    verified.score(index)
    raw=Path(f"n25_{index:02d}.json")
    original=json.loads(raw.read_text())
    assert original["selected_index"]==index
    assert original["manifest_sha256"]==FROZEN_SHA
    assert original["preregistration"]==PREREG
    assert original["rows"][0]["N"]==selected["N"]
    assert original["rows"][0]["base"]==selected["base"]
    assert not original["rows"][0]["public_classical_after_B31"]["classically_solved"],(
        "Fresh selected public survivor unexpectedly solved after freeze")
    public=next(z for z in mf["public_screenings"][selected["group"]]
         if z["N"]==selected["N"])
    assert not public["B47rho64_public_budget"]["classically_solved"]
    assert original["rows"][0]["public_classical_after_B31"]["B47"]["found"]==public["B47rho64_public_budget"]["B47"]["found"]
    assert original["rows"][0]["public_classical_after_B31"]["rho"]["attempts"]==public["B47rho64_public_budget"]["rho"]["attempts"]
    assert original["rows"][0]["cube_vs_plain"]==verified.tail.classify(
        original["rows"][0]["model_plain"],original["rows"][0]["model_cube"])
    assert original["sampling"]["stages"]==list(range(4,51,2))
    assert original["sampling"]["samples_per_stage"]==4096
    assert original["sampling"]["union_family"]==1536
    assert original["sampling"]["phase_salt"]==PHASE_SALT
    assert original["selftests"]["online_CF_matches_legacy_direct_public_factor_extractor"]==1680
    original.update(experiment="dark_star_n25_post_b47rho_fresh_public_survivor_model",
         revision=REV,research_lead="Chase Lunsford / CaMaLabs",
         prior_cohort_disjoint=True,public_classical_selection_is_new=True,
         newly_frozen_selected_SHA=FROZEN_SHA,
         previous_original_N25_sample_sha=mf["original_n25_manifest_sha256"],
         full_source_unchanged_except_manifest_SHA_phase_seed=True,
         online_CF_true_public_N_base_y_only=True,
         zero_QPU=True,qpu_jobs_submitted=0,paid_runtime_used=False,
         true_QPU_hardware_run=False)
    result_path=Path(f"fresh_n25_{index:02d}.json")
    result_path.write_text(json.dumps(original,indent=2)+"\n")
    raw.unlink()
    print("COMPLETE NEW FRESH PUBLIC N25",index,
        "N",selected["N"],"a",selected["base"],"a^3",selected["cube"],
        "classical_unsolved",True,"status",
        original["rows"][0]["cube_vs_plain"]["status"],
        "SHA",FROZEN_SHA,"QPU ZERO",flush=True)


def merge(shard_dir):
    mf=enforce_manifest()
    set_original_scoring_engine_for_new_frozen_manifest()
    rows=[]
    source_files=[]
    for index,selected in enumerate(mf["selected_public_rows"]):
        path=shard_dir/f"fresh-n25-row-{index}"/f"fresh_n25_{index:02d}.json"
        raw=path.read_bytes()
        j=json.loads(raw)
        assert j["revision"]==REV
        assert j["preregistration"]==PREREG
        assert j["manifest_sha256"]==FROZEN_SHA
        assert j["newly_frozen_selected_SHA"]==FROZEN_SHA
        assert j["selected_index"]==index and j["result_complete"]
        assert j["zero_QPU"] and j["qpu_jobs_submitted"]==0 and not j["paid_runtime_used"]
        assert j["sampling"]["phase_salt"]==PHASE_SALT
        assert j["sampling"]["samples_per_stage"]==4096
        assert j["sampling"]["stages"]==list(range(4,51,2))
        assert j["sampling"]["head_bins"]==65
        assert j["sampling"]["union_family"]==1536
        assert j["selftests"]["online_CF_matches_legacy_direct_public_factor_extractor"]==1680
        assert len(j["rows"])==1
        row=j["rows"][0]
        assert all(row[k]==v for k,v in selected.items())
        assert not row["public_classical_after_B31"]["classically_solved"]
        assert row["public_classical_after_B31"]["quantum_needed_after_fixed_public_filter"]
        assert row["validation_only"]["odd_cube_identity"]
        assert row["validation_only"]["half_witness_invariant"]
        assert row["cube_vs_plain"]==verified.tail.classify(row["model_plain"],row["model_cube"])
        assert len(row["model_plain"]["stages"])==len(row["model_cube"]["stages"])==24
        assert row["model_plain"]["precomputed_factor_producing_denominators"]==0
        assert row["model_cube"]["precomputed_factor_producing_denominators"]==0
        for name,arm in (("plain",row["model_plain"]),("cube",row["model_cube"])):
            assert len(arm["structural_modular_arithmetic_per_stage"])==24
            assert arm["online_CF_evaluation_only_operations"]["modpow_calls"]>=0
            assert arm["online_CF_evaluation_only_operations"]["gcd_calls"]>=0
            assert 0<=arm["factor_probability_by_cap_interval"][0]<=arm["factor_probability_by_cap_interval"][1]<=1
        rows.append(row)
        source_files.append((path,raw))
        print("ORIGINAL SHARD AUDITED",index,selected["N"],"status",
             row["cube_vs_plain"]["status"],"public classical unsolved",flush=True)
    classes=collections.Counter(r["cube_vs_plain"]["status"] for r in rows)
    useful_plain=sum(r["model_plain"]["factor_probability_by_cap_interval"][0]>0 for r in rows)
    useful_cube=sum(r["model_cube"]["factor_probability_by_cap_interval"][0]>0 for r in rows)
    model_win=classes["cube_model_win"]>=3 and classes["cube_model_loss"]<=1 and useful_cube>=useful_plain
    summary=dict(total=8,statuses=dict(classes),
       bounded_cube_win=classes["cube_model_win"],
       bounded_cube_loss=classes["cube_model_loss"],
       plain_success_lower_positive=useful_plain,
       cube_success_lower_positive=useful_cube,
       preregistered_model_gate_pass=bool(model_win),
       all_eight_unsolved_after_public_B31_B47rho64=True,
       quantum_work_remaining_after_public_fixed_filter=8,
       real_quantum_speedup_claim_supported=False,
       no_native_QPU_test=True)
    result=dict(experiment="dark_star_fresh_post_b47rho_eight_public_cases_complete",
       revision=REV,research_lead="Chase Lunsford / CaMaLabs",
       preregistration=PREREG,
       source_public_manifest=MANIFEST.as_posix(),
       source_manifest_sha256=FROZEN_SHA,
       original_eight_N25_manifest_sha256=mf["original_n25_manifest_sha256"],
       complete=True,public_manifest_selected_before_hidden_order_QPE=True,
       initial_public_cohort_all_eight_classically_unbroken_by_FIXED_budget=True,
       proof_original_source_model_reused=True,
       model_sampling=rows and dict(samples_per_stage=4096,stages=24,
             phases_salt=PHASE_SALT,alpha=.01,union_family=1536),
       summary=summary,rows=rows,
       zero_QPU=True,qpu_jobs_submitted=0,paid_runtime_used=False,
       note="Independent original prospective N25 8-case public B31+B47rho64 survivors, ideal-QPE online CF/GCD model and SOURCE CCX only. This is NOT quantum hardware, native CZ nor practical factoring advantage.")
    ROOT.mkdir(parents=True,exist_ok=True)
    OUT_ALL.write_text(json.dumps(result,indent=2)+"\n")
    for i,(path,raw) in enumerate(source_files):
        (ROOT/f"dark_star_n25_post_b47rho_fresh_index{i:02d}.json").write_bytes(raw)
    print("FRESH PUBLIC COMPLETE EIGHT",json.dumps(summary,sort_keys=True),
        "source SHA",FROZEN_SHA,"ZERO QPU",flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    mx=p.add_mutually_exclusive_group(required=True)
    mx.add_argument("--index",type=int,choices=range(8))
    mx.add_argument("--merge",action="store_true")
    p.add_argument("--shards",type=Path,default=Path("fresh-n25-shards"))
    args=p.parse_args()
    if args.merge:merge(args.shards)
    else:score_one(args.index)
