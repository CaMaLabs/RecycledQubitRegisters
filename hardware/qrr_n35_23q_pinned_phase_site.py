#!/usr/bin/env python3
"""IBM Fez READ-ONLY CPU initial physical pin 85 for genuine N35 recycled phase.

Original single-phase 23q dynamic program unchanged. Freeze both public bases,
b4/6/8, two seeds [509,8776], target read only, transpiler opt1.
A partial initial_layout pin is NOT a hard physical no-SWAP constraint.
Independently audit actual source phase SWAP-token via Qiskit routed stage,
and every final native phase event/conditional quantum Operator.
All negative/inconclusive cases are evidence, never QPU submissions.
Chase Lunsford / CaMaLabs, 2026-10-24.
"""
from __future__ import annotations
import argparse,json,os,traceback,time
from datetime import datetime,timezone
from pathlib import Path

from qiskit.transpiler import StagedPassManager
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_23q_routed_phase_lineage as lineage

prune=lineage.prune
feedback=lineage.feedback
N=35
BASES=(2,8)
PRECISIONS=(4,6,8)
SEEDS=(509,8776)
PIN_SITE=85
REV="qrr-n35-23q-initial-phase-pin-site85-v1-20261024"
ROOT=Path("results/ibm_shor35_23q_initial_phase_site85")


def archived_original_source_and_native(base):
    """REUSE immutable actual full two-stage SWAP lineage source-run receipts."""
    source=Path(
       f"results/ibm_shor35_true_recycled_phase_route_lineage/"
       f"qrr_n35_23q_routed_phase_lineage_base{base}.json")
    d=json.loads(source.read_text())
    assert d["success"] and d["public_base"]==base and d["N"]==35
    assert d["source_quantum_width"]==23 and d["source_phase_qubits"]==1
    assert d["seed_list"]==list(SEEDS) and d["bits_list"]==list(PRECISIONS)
    assert d["summary"]["source_phase_lineage_to_native_certified"]==6
    assert d["summary"]["hardware_feasible_count"]==0
    assert d["actual_qpu_jobs"]==0 and not d["IBM_free_or_paid_quantum_runtime_used"]
    lookup={}
    for row in d["results"]:
        assert row["status"]=="STAGED_ROUTING_AND_FEZ_NATIVE_CPU_COMPLETE"
        assert row["routed_to_native_lineage_pass"]
        assert row["routed_swap_lineage_pass"]
        lookup[(row["bits"],row["seed"])]=row
    assert len(lookup)==6
    return d,lookup


def prove_same_23q_source(base):
    """Recreate exact dynamic source before any target metadata access."""
    originals,integrity=prune.reference.original_structure_exact(base)
    circuits={}
    proofs={}
    for bits in PRECISIONS:
        qc,detail=prune.reduction_with_exact_instruction_identity(originals[bits],bits)
        assert qc.num_qubits==23 and qc.num_clbits==bits
        assert next(reg for reg in qc.qregs if reg.name=="recycled_phase")[0]==qc.qubits[0]
        assert detail["scratch_all_nine_actually_unused"]
        assert detail["unchanged_original_instruction_order_and_operands"]
        assert detail["unchanged_conditional_body_and_previous_classical_control"]
        ops=qc.count_ops()
        assert ops["measure"]==bits and ops["reset"]==bits-1
        assert ops["if_else"]==bits*(bits-1)//2
        circuits[bits]=qc
        proofs[str(bits)]=detail
    return circuits,dict(
        parent_32q_source_integrity=integrity,
        dynamic_23q_exact_instruction_identity=proofs,
        original_archived_768_source_gate_cases_per_base_not_rerun=True,
        original_archived_336_ideal_outcome_probabilities_per_base_not_rerun=True,
        both_conditions_original_source_mathematically_unchanged=True)


def validate_final_native(native,bits,route):
    """Actual routed token and native event/operator quantum semantics."""
    native_ops={str(k):int(v) for k,v in native.count_ops().items()}
    required={"measure":bits,"reset":bits-1,"if_else":bits*(bits-1)//2}
    if any(native_ops.get(n,0)!=v for n,v in required.items()):
        raise AssertionError(
           "Native dynamic operation count altered "+str((native_ops,required)))
    branch=feedback.certify_branch_operators(native,bits)
    if not (branch["all_native_condition_body_operators_proved"] and
            branch["fully_certified_prior_classical_measurement_conditions"] and
            branch["emitted_compiled_if_else_count"]==required["if_else"] and
            branch["measurement_classical_targets"]==list(range(bits))):
        raise AssertionError(
           "Native conditional body/earlier classical history FAILED "+str(branch["problems"])[:700])
    physical=lineage.compare_routed_and_native(route,native,bits)
    return native_ops,branch,physical


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    target=ROOT/f"qrr_n35_site85_pinned_base{base}.json"
    r=dict(revision=REV,
       research_lead="Chase Lunsford / CaMaLabs",
       timestamp_utc=datetime.now(timezone.utc).isoformat(),
       preregistration="docs/QRR_N35_23Q_PINNED_PHASE_SITE_PREREG.md",
       N=N,public_base=base,phase_precisions=list(PRECISIONS),seeds=list(SEEDS),
       source_one_recycled_phase_bit=True,unchanged_source_qubits=23,
       pinned_start_site=PIN_SITE,
       initial_layout_pin_NOT_a_no_swap_routing_constraint=True,
       backend_target="ibm_fez",optimization_level=1,
       old_exact_source_run_id=40144331011,
       old_audit_run_id=40144473764,
       hardware_native_cz_limit=800,hardware_native_depth_limit=2000,
       quantum_processor_jobs_submitted=0,
       free_or_paid_quantum_runtime_used=False,
       backend_run_never_invoked=True,
       results=[],success=False,status="STARTED")
    def save():target.write_text(json.dumps(r,indent=2,default=str)+"\n")
    save()
    try:
        archived,lookup=archived_original_source_and_native(base)
        circuits,source=prove_same_23q_source(base)
        r["prior_unchanged_source_and_ideal_proofs"]=source
        r["source_original_lineage_anchors_pass_before_backend"]=True
        r["status"]="SOURCE_PROOFS_PASSED"
        save()
        print("FROZEN SOURCE 23Q EXACT",base,
              "3 b levels and old mathematical source semantics unchanged",
              "phase1 work6 live16, zero QPU",flush=True)

        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
            plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<=PIN_SITE:
            raise RuntimeError("READ-ONLY IBM Fez target no physical site85")
        r["backend_reported_target_qubits"]=int(backend.num_qubits)
        r["status"]="PINNED_COMPILER_EXPERIMENT"
        save()
        for bits in PRECISIONS:
            for seed in SEEDS:
                old=lookup[(bits,seed)]
                row=dict(bits=bits,seed=seed,status="ATTEMPT",
                  old_archived_unpinned_source_run_id=40144331011,
                  archived_unpinned_native_cz=old["native_cz"],
                  archived_unpinned_native_depth=old["native_depth"],
                  archived_unpinned_start_address=old["staged_routing"]["initial_phase_physical_address"],
                  archived_unpinned_phase_event_sites=old["native_lineage_comparison"]["native_phase_event_unique_physical_addresses"],
                  source_changed=False,initial_pin_site85_requested=True,
                  qpu_jobs=0)
                r["results"].append(row)
                save()
                try:
                    qc=circuits[bits]
                    phase=next(reg[0] for reg in qc.qregs if reg.name=="recycled_phase")
                    assert phase==qc.qubits[0]
                    # Qiskit initial_layout dict pins exact VIRTUAL source
                    # qubit to native physical address85. All other placement
                    # decisions and SWAP routing remain the normal pass manager.
                    pinned_layout={phase:PIN_SITE}
                    pm=generate_preset_pass_manager(backend=backend,
                        optimization_level=1,seed_transpiler=seed,
                        initial_layout=pinned_layout)
                    pre=StagedPassManager(stages=["init","layout","routing"],
                        init=pm.init,layout=pm.layout,routing=pm.routing)
                    t0=time.perf_counter()
                    routed=pre.run(qc)
                    route_time=time.perf_counter()-t0
                    info=lineage.track_routed_stage(qc,routed,bits)
                    t0=time.perf_counter()
                    native=pm.run(qc)
                    native_time=time.perf_counter()-t0
                    native_ops,branch,phys=validate_final_native(native,bits,info)
                    native_cz=int(native_ops.get("cz",0))
                    native_depth=int(native.depth())
                    if native_cz<=0 or native_depth<=0:
                        raise AssertionError("Native cost metric is zero")
                    actual_start=info.get("initial_phase_physical_address")
                    pin_respected=(actual_start==PIN_SITE)
                    lineage_pass=bool(info["phase_token_trace_certified"] and
                                      phys["source_phase_lineage_to_native_certified"])
                    sites=phys["native_phase_event_unique_physical_addresses"]
                    dynamic_all_at_pin=bool(pin_respected and sites==[PIN_SITE] and
                                            lineage_pass)
                    # Strict fixed physical SITE throughout the routed
                    # circuit requires not one single phase-moving SWAP,
                    # not merely returning to 85 for dynamic instructions.
                    phase_swaps=int(info.get("phase_token_swap_ops",-1))
                    strictly_fixed=bool(dynamic_all_at_pin and phase_swaps==0)
                    delta_cz=native_cz-old["native_cz"]
                    delta_depth=native_depth-old["native_depth"]
                    row.update(status="COMPLETE_PINNED_NATIVE_CPU",
                        pinned_layout_initial_phase_physical=actual_start,
                        phase_pin_respected=pin_respected,
                        staged_routed_phase_trace=info,
                        native_routed_phase_comparison=phys,
                        native_conditional_phase_operator_count=branch["emitted_compiled_if_else_count"],
                        native_conditional_phase_quantum_operator_equivalence_pass=True,
                        staged_routed_token_lineage_and_native_pass=lineage_pass,
                        all_dynamic_events_at_pinned_site85=dynamic_all_at_pin,
                        strict_no_phase_swap_fixed_85_site=strictly_fixed,
                        pinned_native_cz=native_cz,pinned_native_depth=native_depth,
                        paired_cz_change_vs_archived=delta_cz,
                        paired_depth_change_vs_archived=delta_depth,
                        both_compiler_cost_metrics_improve=bool(delta_cz<0 and delta_depth<0),
                        native_ops=native_ops,native_compiled_target_width=int(native.num_qubits),
                        routed_cpu_seconds=route_time,native_cpu_seconds=native_time,
                        pinned_candidate_physical_gate_pass=bool(
                            native_cz<=800 and native_depth<=2000))
                    print("N35 PHYSICAL INITIAL PIN CPU ONLY base",base,
                      "b",bits,"seed",seed,"start",actual_start,
                      "phase swaps",phase_swaps,
                      "dynamic sites",sites,
                      "native phase operators",row["native_conditional_phase_operator_count"],
                      "native CZ/depth",native_cz,native_depth,
                      "vs old",delta_cz,delta_depth,
                      "strict fixed site",strictly_fixed,
                      "hardware",row["pinned_candidate_physical_gate_pass"],
                      "ZERO QPU",flush=True)
                except Exception as exc:
                    row.update(status="INCONCLUSIVE_COMPILER_OR_PIN",
                        failure_type=type(exc).__name__,
                        failure_message=str(exc)[:1500],
                        failure_traceback=traceback.format_exc()[-1900:],
                        strict_no_phase_swap_fixed_85_site=False,
                        pinned_candidate_physical_gate_pass=False)
                    print("N35 SITE PIN COMPILER ISSUE",base,bits,seed,
                      type(exc).__name__,str(exc)[:470],
                      traceback.format_exc()[-750:],
                      "NO QPU",flush=True)
                save()
        full=[x for x in r["results"] if x["status"]=="COMPLETE_PINNED_NATIVE_CPU"]
        pinned=[x for x in full if x["phase_pin_respected"]]
        r["summary"]=dict(
          requested_cases=len(PRECISIONS)*len(SEEDS),
          native_completes=len(full),initial_site85_respected=len(pinned),
          true_logical_phase_routed_native_lineage_pass=sum(
             x["staged_routed_token_lineage_and_native_pass"] for x in full),
          pinned_site85_all_dynamic_events=sum(
             x["all_dynamic_events_at_pinned_site85"] for x in full),
          pinned_phase_site85_strict_no_swap_success=sum(
             x["strict_no_phase_swap_fixed_85_site"] for x in full),
          native_conditional_source_phase_operators_verified=sum(
             x["native_conditional_phase_operator_count"] for x in full),
          native_compiler_both_CZ_and_depth_better_than_archived_count=sum(
             x["both_compiler_cost_metrics_improve"] for x in full),
          hardware_feasible_count=sum(
             x["pinned_candidate_physical_gate_pass"] for x in full),
          strict_site85_global_gate_pass=bool(
             len(full)==len(PRECISIONS)*len(SEEDS) and
             all(x["strict_no_phase_swap_fixed_85_site"] for x in full)),
          phase_register_count_SOURCE_only_one=True,
          phase_physical_device_site_NOT_guaranteed_by_source=True,
          actual_QPU_jobs=0,
          physical_measurement_reset_feedback_latency_NOT_TESTED=True)
        r["success"]=len(full)==len(PRECISIONS)*len(SEEDS)
        r["status"]="ALL_PINNED_LAYOUT_CPU_CASES_COMPLETE" if r["success"] else "PARTIAL_OR_UNSUPPORTED_PIN"
        save()
        print("N35 SITE85 LAYOUT STUDY SUMMARY",base,json.dumps(r["summary"],sort_keys=True),
            "NO QPU",flush=True)
        return 0 if r["success"] else 1
    except Exception as exc:
        r.update(status="FAIL",success=False,
            error_type=type(exc).__name__,
            error_message=str(exc)[:1800],
            error_traceback=traceback.format_exc()[-2900:],
            quantum_processor_jobs_submitted=0,
            free_or_paid_quantum_runtime_used=False)
        save()
        print("N35 INITIAL PHASE PIN GLOBAL FAILURE",base,
              type(exc).__name__,str(exc)[:850],
              traceback.format_exc()[-1300:],
              "ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=int,choices=BASES,required=True)
    raise SystemExit(main(parser.parse_args().base))
