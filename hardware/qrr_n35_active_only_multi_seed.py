#!/usr/bin/env python3
"""Preregistered 8 matched transpiler seeds of phase-correct active-only vs neither.

Lead Chase Lunsford / CaMaLabs. No QPU. Native IBM Fez backend TARGET read
only; CPU Qiskit compiler. Full source complex-phase proof BEFORE target read.
Records EVERY seed and regression; validates old 8776 anchor and 6/8 matched
improvements per public N35 base, not a biased best-seed postselection.
"""
from __future__ import annotations
import argparse
import json
import os
import statistics
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_relative_phase_latch_families as family

# Imports above install the previously phase-exact comparator carry circuit.
previous=family.previous

N=35
BASES=(2,8)
SEEDS=(11,37,101,409,8776,12011,20261,45673)
REV="qrr-n35-active-only-matched-multiseed-v1-20261017"
ROOT=Path("results/ibm_shor35_active_only_multi_seed")

HISTORICAL={
  2:dict(neither=dict(cz=9263,depth=21772,
      source=dict(cx=1033,rccx=596,x=28,ccx=160)),
         active_only=dict(cz=9042,depth=21541,
      source=dict(cx=1033,rccx=598,x=28,ccx=158))),
  8:dict(neither=dict(cz=9426,depth=21933,
      source=dict(cx=1077,rccx=616,x=28,ccx=162)),
         active_only=dict(cz=9156,depth=21820,
      source=dict(cx=1077,rccx=618,x=28,ccx=160)))
}


def prove_before_backend_read(base):
    """One fixed source proof per original circuit, independent of compiler seed."""
    local=family.shared.local_latch_unitary_test()
    assert local["pass_all"] and local["direct_actual_operator_cases"]==8
    assert local["output_complex_phase_exactly_plus_one"]
    comparator=previous.exhaustive_comparator_phase_proof()
    assert comparator["pass_all"] and comparator["actual_gate_comparator_cases"]==42672
    assert comparator["all_carry_scratch_clean"] and comparator["exact_complex_phase_plus_one"]
    modadd=previous.exhaustive_modadd_phases(previous.source_constants())
    assert modadd["pass_all"] and modadd["source_gate_cases"]==1584
    assert modadd["unique_constants"]==16 and modadd["exact_complex_phase_plus_one"]

    # Neither old comparator-only nor new active-only changes its source with
    # the compiler seed. Verify both ACTUAL emitted complex operator streams.
    old_circuit,old_regs=previous.verified.build(base)
    new_circuit,new_regs=family.build_variant(base,"active_only")
    old_proof=previous.exhaustive_full_multiplier_phases(old_circuit,old_regs,base)
    new_proof=previous.exhaustive_full_multiplier_phases(new_circuit,new_regs,base)
    prior=HISTORICAL[base]
    for name,circuit,p in (("neither",old_circuit,old_proof),
                           ("active_only",new_circuit,new_proof)):
        assert circuit.num_qubits==32
        assert p["pass_all"] and p["full_residue_control_basis_cases"]==128
        assert p["all_25_auxiliaries_clean"] and p["control_unmodified"]
        assert p["exact_complex_output_phase_plus_one"]
        assert p["disabled_invalid_states_identity"]
        assert p["quantum_source_gate_counts"]==prior[name]["source"],(
           name,p["quantum_source_gate_counts"],prior[name]["source"])
    old_ops=old_proof["quantum_source_gate_counts"]
    new_ops=new_proof["quantum_source_gate_counts"]
    assert new_ops["rccx"]==old_ops["rccx"]+2
    assert new_ops["ccx"]==old_ops["ccx"]-2
    assert new_ops["cx"]==old_ops["cx"] and new_ops["x"]==old_ops["x"]
    print("SOURCE EXACT COMPLEX PHASE PROOFS",base,
          "8 LOCAL + 42672 COMPARATOR + 1584 MODADD + 128 NEITHER + 128 ACTIVE",
          "25 CLEAN, +1 AMPLITUDE, active RCCX+2 CCX-2",flush=True)
    return old_circuit,new_circuit,dict(local=local,comparator=comparator,
        modadd=modadd,neither_full=old_proof,active_only_full=new_proof,
        all_complex_phases_plus_one=True,both_source_32_logical_qubits=True,
        all_25_helpers_clean=True,active_only_source_rccx_gain=2,
        active_only_source_ccx_reduction=2)


def compile_record(pm,circuit):
    """CPU-only passmanager, NO backend runtime execution."""
    ts=time.perf_counter()
    compiled=pm.run(circuit)
    elapsed=time.perf_counter()-ts
    ops={str(k):int(v) for k,v in compiled.count_ops().items()}
    cz=int(ops.get("cz",0))
    depth=int(compiled.depth())
    if not (cz>0 and depth>0 and int(compiled.num_qubits)>=circuit.num_qubits):
        raise AssertionError("Native compiler returned invalid resource metrics")
    return dict(cz=cz,depth=depth,
       compiled_device_width=int(compiled.num_qubits),
       compiled_native_ops=ops,
       compiled_total_ops=int(compiled.size()),
       compiler_elapsed_seconds=elapsed)


def summarize(pairs):
    assert len(pairs)==len(SEEDS)
    metrics=[]
    wins_both=0
    wins_cz=0
    wins_depth=0
    for p in pairs:
        dz=p["delta_active_minus_neither"]["cz"]
        dd=p["delta_active_minus_neither"]["depth"]
        metrics.append((dz,dd))
        wins_both+=int(dz<0 and dd<0)
        wins_cz+=int(dz<0)
        wins_depth+=int(dd<0)
    dzs=[z for z,_ in metrics]
    dds=[d for _,d in metrics]
    med_z=statistics.median(dzs)
    med_d=statistics.median(dds)
    return dict(
      pairs=len(pairs),
      both_metrics_strict_improvement_seed_count=wins_both,
      cz_strict_improvement_seed_count=wins_cz,
      depth_strict_improvement_seed_count=wins_depth,
      paired_cz_delta_median=med_z,
      paired_depth_delta_median=med_d,
      paired_cz_delta_min=min(dzs),paired_cz_delta_max=max(dzs),
      paired_depth_delta_min=min(dds),paired_depth_delta_max=max(dds),
      both_metric_seed_rule_at_least_six_of_eight=(wins_both>=6),
      both_paired_delta_medians_negative=(med_z<0 and med_d<0),
      every_seed_paired_and_reported=True
    )


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    output=ROOT/f"qrr_n35_active_only_multiseed_base{base}.json"
    receipt=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
       utc=datetime.now(timezone.utc).isoformat(),
       preregistration="docs/QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_PREREG.md",
       experiment="matched eight-seed original neither vs phase-exact active-only, ONE N35 controlled modular multiplier",
       N=N,base=base,seed_list=list(SEEDS),compiler_optimization_level=1,
       read_only_backend_target="ibm_fez",
       original_8776_historical_controls=HISTORICAL[base],
       source_seed_invariant=True,
       device_cz_limit=800,device_depth_limit=2000,
       factorization_order_not_used=True,private_factors_not_used=True,
       multiplicative_orbit_not_hardcoded=True,
       qpu_jobs_submitted=0,quantum_runtime_used=False,paid_runtime_used=False,
       seed_pair_results=[],
       status="STARTED",success=False)
    def save():
        output.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        old_c,new_c,proof=prove_before_backend_read(base)
        receipt["source_complex_phase_proofs"]=proof
        receipt["status"]="SOURCE_PHASE_GATES_PROVED_BEFORE_TARGET"
        save()

        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Expected physical Fez BACKEND TARGET >=32 qubits")
        receipt["backend_reported_qubits"]=int(backend.num_qubits)
        receipt["status"]="MATCHED_COMPILER_SEED_RUNS"
        save()

        for seed in SEEDS:
            # SAME backend, same pass-manager generation settings, same seed,
            # same physical target snapshot within each paired control test.
            pm=generate_preset_pass_manager(
                backend=backend,optimization_level=1,seed_transpiler=seed)
            ref=compile_record(pm,old_c)
            active=compile_record(pm,new_c)
            dz=active["cz"]-ref["cz"]
            dd=active["depth"]-ref["depth"]
            row=dict(seed=seed,neither=ref,active_only=active,
                     delta_active_minus_neither=dict(cz=dz,depth=dd),
                     matched_seed_improves_both=(dz<0 and dd<0),
                     device_feasible_neither=(ref["cz"]<=800 and ref["depth"]<=2000),
                     device_feasible_active=(active["cz"]<=800 and active["depth"]<=2000))
            receipt["seed_pair_results"].append(row)
            save()
            print("MATCHED N35 CPU SEED",base,seed,
                  "neither CZ/depth",ref["cz"],ref["depth"],
                  "active CZ/depth",active["cz"],active["depth"],
                  "paired deltas",dz,dd,
                  "both_improve",row["matched_seed_improves_both"],
                  "DEVICE",row["device_feasible_active"],"NO QPU",flush=True)

        summary=summarize(receipt["seed_pair_results"])
        anchor=next(p for p in receipt["seed_pair_results"] if p["seed"]==8776)
        reference=HISTORICAL[base]
        anchor_pass=all(
            anchor[name]["cz"]==reference[name]["cz"] and
            anchor[name]["depth"]==reference[name]["depth"]
            for name in ("neither","active_only"))
        summary["frozen_seed_8776_exact_historical_reproduction"]=anchor_pass
        summary["robust_engineering_per_base_pass"]=bool(
            anchor_pass and
            summary["both_metric_seed_rule_at_least_six_of_eight"] and
            summary["both_paired_delta_medians_negative"])
        summary["historical_comparability_inconclusive_if_anchor_drift"]=not anchor_pass
        summary["all_eight_active_layouts_fail_device_gate"]=all(
            not p["device_feasible_active"] for p in receipt["seed_pair_results"])
        summary["all_eight_neither_layouts_fail_device_gate"]=all(
            not p["device_feasible_neither"] for p in receipt["seed_pair_results"])
        receipt.update(status="COMPILE_SUCCESS",success=True,
                       summary=summary,all_seeds_completed=True,
                       no_real_quantum_hardware_submission=True)
        save()
        print("N35 MULTISEED SUMMARY",base,json.dumps(summary,sort_keys=True),
              "NO QPU",flush=True)
        return 0
    except Exception as exc:
        receipt.update(status="FAIL",success=False,
           failure_type=type(exc).__name__,
           failure_message=str(exc)[:1800],
           failure_traceback=traceback.format_exc()[-3000:],
           qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print("N35 MATCHED SEED EXPERIMENT FAILURE",base,
              type(exc).__name__,str(exc)[:800],
              traceback.format_exc()[-1200:],"NO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(parser.parse_args().base))
