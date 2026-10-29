#!/usr/bin/env python3
"""Post-hoc N26 classical-only replay after restored exact midpoint pruning.
Original N26 11/12 outcome stays frozen; NO quantum models rerun or QPU used.
"""
from __future__ import annotations
import json, math
from datetime import datetime,timezone
from pathlib import Path
from integrations.darkstar_hybrid import darkstar_unified as u

ROOT=Path("results/dark_star_unified")
SHA="0c25e448b646a5ade7d919ca78597c8c2883fd8fd450181dd4504c18252fb939"
OLD=ROOT/"unified_n26_all_12_summary.json"
RESTRICTED=ROOT/"unified_n26_midpoint_pruning_reaudit.json"
DEST=ROOT/"unified_n26_midpoint_restoration_classical_replay.json"


def main():
    frozen=json.loads((ROOT/"unified_n26_public_manifest.json").read_text())
    old=json.loads(OLD.read_text())
    audit=json.loads(RESTRICTED.read_text())
    assert frozen["selected_sha256"]==old["frozen_public_sha256"]==audit["original_frozen_public_manifest_sha256"]==SHA
    assert len(frozen["selected_public_rows"])==12
    assert old["summary"]["classically_solved_by_unified_preflight"]==11
    assert audit["summary"]["no_false_pruning_or_valid_factor_loss"]
    rows=[]
    for i,item in enumerate(frozen["selected_public_rows"]):
        source=json.loads((ROOT/f"unified_n26_original_{i:02d}.json").read_text())
        assert source["frozen_manifest_sha256"]==SHA and source["index"]==i
        original=source["rows"][0]
        assert original["frozen_public"]==item
        n,a=item["N"],item["base"]
        truth=original["validation_only_original_synthetic_factors"]
        assert math.prod(truth)==n
        classical=u.public_classical_preflight(n,a,fermat_tests=12,
            restored_prune_max_offset=4095,restored_prune_square_tests=12)
        assert classical["factors"]==truth
        assert classical["classically_solved"]
        if original["classical_first_solved"]:
            assert classical["method"]==original["classical_first_method"],(i,n)
            assert not any(z["name"]=="restored_midpoint_QR_255255" for z in classical["stages"])
        else:
            assert classical["method"]=="restored_midpoint_QR_255255"
            s=classical["stages"][-1]
            assert s["name"]=="restored_midpoint_QR_255255"
            assert s["exact_square_root_tests"]==8
            assert s["scanned_midpoint_positions"]<=4096
        rows.append(dict(index=i,public_frozen=item,
            original_classical_first_solved=original["classical_first_solved"],
            original_classical_method=original["classical_first_method"],
            restored_classical_factors=classical["factors"],
            restored_classical_method=classical["method"],
            restored_public_classical_receipt=classical,
            original_populated_ideal_QPE_counterfactual_unmodified=True))
        print("REPLAY",i,n,original["classical_first_method"],"->",classical["method"],flush=True)
    assert len(rows)==12
    summary=dict(original_N26_classical_first_solved=11,
        secondary_replay_after_QR_255255_classical_first_solved=12,
        delta_newly_classically_solved_under_same_old_12_root_cap=1,
        only_original_quantum_fallback_N49273331_now_classically_solved=True,
        original_unmodified_ideal_QPE_counterfactual_cases=12,
        no_practical_speedup_claim=audit["summary"]["end_to_end_speed_gate_pass"] is False,
        no_QPU=True)
    output=dict(experiment="unified_N26_post_hoc_classical_pruner_restored_replay",
        source_N26_public_sha256=SHA,
        scope="post_hoc_algorithm_change_not_new_independent_holdout",
        original_summary_immutable=str(OLD),
        restored_pruning_audit_immutable=str(RESTRICTED),
        whole_pipeline_original_QPE_results_not_recalculated=True,
        summary=summary,complete=True,rows=rows,
        zero_QPU=True,IBM_runtime_jobs=0,paid_runtime_used=False,
        date_utc=datetime.now(timezone.utc).isoformat())
    DEST.write_text(json.dumps(output,indent=2)+"\n")
    print("CLASSICAL RESTORATION REPLAY SUCCESS 12/12",json.dumps(summary),flush=True)


if __name__=="__main__":
    main()
