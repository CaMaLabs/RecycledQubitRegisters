#!/usr/bin/env python3
"""CPU-only IBM Fez TARGET compiler capability audit for true 32q N35 recycled phase.

Research lead: Chase Lunsford / CaMaLabs.
Do not change Qiskit original dynamic source, phase-power arithmetic,
measure/reset/if_else feedforward, or historic observed ideal probabilities.
NO backend.run/IBM Sampler/Estimator/jobs/free-or-paid QPU execution.

Each base job compiles original b4/b6/b8 circuit independently, retaining
per-arm genuine compiler rejection as scientific NEGATIVE results.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_true_recycled_phase_feedforward as source

N=35
BITS=(4,6,8)
BASES=(2,8)
REV="qrr-n35-dynamic-fez-readonly-native-lowerability-v1-20261021"
ROOT=Path("results/ibm_shor35_true_recycled_dynamic_fez_isa")
FROZEN_SEED=8776
FROZEN_OPTIMIZATION=1


def archived_ideal_anchors(base):
    """Require PREVIOUSLY audited exact stage and 4/6/8 branch results."""
    receipt=json.loads(Path(
        f"results/n35_true_recycled_phase_feedforward/"
        f"qrr_n35_recycled_phase_feedforward_base{base}.json").read_text())
    assert receipt["success"] and receipt["N"]==N
    assert receipt["public_base"]==base and receipt["phase_precision_bits"]==list(BITS)
    assert receipt["actual_QPU_jobs"]==0
    assert receipt["total_distinct_stage_gate_semantic_cases"]==768
    assert receipt["total_exact_phase_outcome_probabilities_compared"]==336
    assert set(receipt["phase_exact_stage_proofs"])=={str(p) for p in (2,4,8,11,16,29)}
    for s in receipt["phase_exact_stage_proofs"].values():
        assert s["actual_gate_basis_cases"]==128
        assert s["all_25_ancilla_bits_clean"] and s["complex_output_phase_plus_one"]
    for bits in BITS:
        v=receipt["full_results"][str(bits)]
        st=v["dynamic_gate_source_structure"]
        assert st["pass_all"] and st["source_quantum_qubits"]==32
        assert st["source_classical_result_bits"]==bits
        assert st["actual_midcircuit_measure_count"]==bits
        assert st["actual_midcircuit_reset_count"]==bits-1
        assert st["actual_classical_if_else_feedback_count"]==bits*(bits-1)//2
        assert v["all_outcomes_match_independent_wide_IQFT"]
        assert v["exact_recycled_vs_wide_probability_comparisons"]==1<<bits
        assert v["maximum_absolute_probability_difference"]<1e-9
    return receipt


def original_structure_exact(base):
    """Rebuild exact existing dynamic circuit, compare historical source ops.

    The preceding 768 emitted-gate unitary tests are independently preserved
    in source receipts. DO NOT call this a fresh execution of 768 cases.
    """
    selector=source.configure_original_public_arithmetic()
    assert selector["pass_all"] and selector["original_public_34_source_rows_exact"]
    prior=archived_ideal_anchors(base)
    assembled={}
    circuits={}
    for bits in BITS:
        qc,regs,cbits,schedule,feedback=source.build_dynamic_source(base,bits)
        inspected=source.inspect_dynamic_source(qc,regs,cbits,base,bits,schedule,feedback)
        saved=prior["full_results"][str(bits)]["dynamic_gate_source_structure"]
        assert inspected["actual_Qiskit_dynamic_gate_operation_counts"]==saved["actual_Qiskit_dynamic_gate_operation_counts"],(
            base,bits,inspected["actual_Qiskit_dynamic_gate_operation_counts"],
            saved["actual_Qiskit_dynamic_gate_operation_counts"])
        assert inspected["public_stage_build_sequence"]==saved["public_stage_build_sequence"]
        assert inspected["source_quantum_qubits"]==32
        assert inspected["source_classical_result_bits"]==bits
        assert inspected["exact_feedback_angles_and_prior_classical_bit_controls"]
        assert inspected["IQFT_measurements_lsb_first_in_classical_output"]
        circuits[bits]=qc
        assembled[str(bits)]=dict(
            source_quantum_qubits=qc.num_qubits,source_classical_bits=qc.num_clbits,
            source_gate_count=int(qc.size()),
            source_operation_counts={str(k):int(v) for k,v in qc.count_ops().items()},
            source_structure_matches_immutable_original=True,
            archived_independent_ideal_outcomes_matched=1<<bits,
            existing_stage_source_phase_proofs_true=768)
    return circuits,dict(original_archived_reference_valid=True,
        original_unmodified_public_source_selection=True,
        six_distinct_stage_phase_proof_cases_from_original_receipt=768,
        original_ideal_adaptive_outcomes_from_archived_source=336,
        source_gate_structures_exact=assembled,
        no_new_source_stage_proof_reexecution_claimed=True)


def inspect_native_dynamic(native,bits,original_qc):
    """Strictly check source dynamic controls survive compilation.

    This is deliberately conservative. A different native decomposition may
    be mathematically equivalent but is UNCERTIFIED without separate proof.
    We never claim 'supported on hardware' solely from compiler acceptance.
    """
    gate_counts={str(k):int(v) for k,v in native.count_ops().items()}
    evidence=dict(
       compiled_qubits=int(native.num_qubits),
       compiled_classical_bits=int(native.num_clbits),
       compiled_depth=int(native.depth()),
       native_operations=gate_counts,
       compiler_preserved_source_feedback=False,
       compiled_exact_conditional_phase_body=False,
       classical_feedforward_semantics_certified=False,
       physical_feedback_latency_verified=False,
       physical_device_execution_supported_not_proven=True,
       problems=[])
    problems=evidence["problems"]
    if native.num_clbits!=bits:
        problems.append(f"classical bit width {native.num_clbits} != original {bits}")
    if native.num_qubits<original_qc.num_qubits:
        problems.append(f"compiled width {native.num_qubits} < source {original_qc.num_qubits}")
    expected=dict(measure=bits,reset=bits-1,if_else=bits*(bits-1)//2)
    for key,num in expected.items():
        if gate_counts.get(key,0)!=num:
            problems.append(f"dynamic {key}: compiled {gate_counts.get(key,0)}, source required {num}")
    observed=[]
    for instruction in native.data:
        operation=instruction.operation
        if operation.name!="if_else":
            continue
        condition=getattr(operation,"condition",None)
        if not isinstance(condition,tuple) or len(condition)!=2:
            problems.append("native if_else lacks single-bit condition tuple")
            continue
        clbit,expected_bit=condition
        try:
            bitidx=native.find_bit(clbit).index
        except Exception:
            problems.append("native classical condition cannot be matched to a bit")
            continue
        if expected_bit!=1:
            problems.append("native classical comparison not equal to one")
        bodies=getattr(operation,"blocks",None)
        if not bodies or bodies[0] is None:
            problems.append("native if_else missing branch body")
            continue
        body=bodies[0]
        insts=list(body.data)
        if len(insts)!=1 or insts[0].operation.name!="p":
            problems.append("compiler decomposed/rewrote conditional P without independent phase proof")
            observed.append(dict(classical_bit_index=bitidx,body_ops=[z.operation.name for z in insts],
                                 phase_angle=None))
            continue
        angle=float(insts[0].operation.params[0])
        observed.append(dict(classical_bit_index=bitidx,body_ops=["p"],phase_angle=angle))
    expected_conditions=[]
    for j in range(bits-1,-1,-1):
        for t in range(bits-1,j,-1):
            expected_conditions.append(dict(
                classical_bit_index=bits-1-t,
                body_ops=["p"],
                phase_angle=-2*math.pi/(1<<(t-j+1))))
    if len(observed)!=len(expected_conditions):
        problems.append(f"certifiable conditional blocks {len(observed)} != {len(expected_conditions)}")
    else:
        for i,(have,want) in enumerate(zip(observed,expected_conditions)):
            if have["classical_bit_index"]!=want["classical_bit_index"]:
                problems.append(f"conditional block {i} reads wrong classical bit")
            if have["body_ops"]!=["p"] or have["phase_angle"] is None:
                problems.append(f"conditional block {i} phase body not certified")
            elif abs(have["phase_angle"]-want["phase_angle"])>1e-10:
                problems.append(f"conditional block {i} wrong phase angle")
    # Distinguish preservation of dynamic opcode counts from full phase semantics.
    structurally_preserved=(native.num_clbits==bits and all(
       gate_counts.get(k,0)==v for k,v in expected.items()))
    evidence["compiler_preserved_source_feedback"]=structurally_preserved
    evidence["compiled_exact_conditional_phase_body"]=(
        len(observed)==len(expected_conditions) and
        all(x["body_ops"]==["p"] for x in observed))
    evidence["classical_feedforward_semantics_certified"]=len(problems)==0
    evidence["observed_certifiable_feedback"]=observed
    evidence["expected_source_feedback"]=expected_conditions
    return evidence


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    output=ROOT/f"qrr_n35_dynamic_isa_base{base}.json"
    data=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        date_utc=datetime.now(timezone.utc).isoformat(),
        preregistration="docs/QRR_N35_TRUE_RECYCLED_PHASE_DYNAMIC_FEZ_ISA_PREREG.md",
        N=N,public_base=base,phase_precisions=list(BITS),
        source_true_recycled_phase_qubits=1,source_logical_qubits=32,
        n35_public_cube_has_trivial_classical_gcd=True,
        original_arithmetic_order_not_injected=True,private_factors_not_used=True,
        hardware_target_name="ibm_fez",transpile_optimization_level=FROZEN_OPTIMIZATION,
        transpile_seed=FROZEN_SEED,
        physical_feasibility_native_cz_limit=800,
        physical_feasibility_native_depth_limit=2000,
        qpu_jobs_submitted=0,hardware_shots=0,
        no_ibm_runtime_primitives=True,
        read_only_backend_metadata_only=True,
        free_or_paid_qpu_runtime_used=False,
        per_precision={},
        study_completed=False,success=False,status="STARTED")
    def save():output.write_text(json.dumps(data,indent=2,default=str)+"\n")
    save()
    try:
        circuits,prepared=original_structure_exact(base)
        data["before_backend_source_validation"]=prepared
        data["status"]="SOURCE_6_ARMS_STRUCTURALLY_VERIFIED"
        save()
        print("DYNAMIC ORIGINAL SOURCE VERIFIED",base,
              "32q all 4/6/8 bits; 768 archived stage gates and 336 ideal outcomes PER BASE",
              "no source arithmetic modification",flush=True)
        # Actual Fez target metadata READ only; never execute physical quantum.
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
             plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Read-only target did not return a physical >=32q Fez backend")
        operations=sorted(str(x) for x in backend.target.operation_names)
        support={k:k in operations for k in ("if_else","measure","reset","p","h","cz","rz","sx")}
        data["backend_target_read_only_snapshot"]=dict(
            reported_qubits=int(backend.num_qubits),
            supported_target_instruction_names=operations,
            dynamic_capability_names_present=support,
            source_control_flow_isa_support_declared=bool(support["if_else"]),
            source_measurement_isa_support_declared=bool(support["measure"]),
            source_reset_isa_support_declared=bool(support["reset"]),
            target_metadata_only_no_hardware_job=True)
        save()
        print("FEZ READ ONLY TARGET CAPABILITIES",base,
              json.dumps(support,sort_keys=True),"qubits",backend.num_qubits,flush=True)
        for bits in BITS:
            qc=circuits[bits]
            row=dict(bits=bits,source_quantum_qubits=qc.num_qubits,
                     source_classical_bits=qc.num_clbits,
                     original_source_operation_counts=prepared["source_gate_structures_exact"][str(bits)]["source_operation_counts"],
                     original_dynamic_structure_preserved_before_compile=True,
                     compiler_acceptance=False,
                     native_costs_available=False,
                     classical_feedback_structurally_preserved=False,
                     classical_feedback_semantics_certified=False,
                     native_hardware_gate_pass=False,
                     runtime_submissions=0,status="ATTEMPTING_CPU_COMPILER")
            data["per_precision"][str(bits)]=row
            save()
            try:
                pm=generate_preset_pass_manager(backend=backend,
                     optimization_level=FROZEN_OPTIMIZATION,seed_transpiler=FROZEN_SEED)
                t0=time.perf_counter()
                native=pm.run(qc)
                elapsed=time.perf_counter()-t0
                examined=inspect_native_dynamic(native,bits,qc)
                native_cz=int(examined["native_operations"].get("cz",0))
                native_depth=int(examined["compiled_depth"])
                row.update(compiler_acceptance=True,
                   native_costs_available=True,
                   native_cz=native_cz,native_depth=native_depth,
                   compiled_isa_width=int(native.num_qubits),
                   compiled_total_gate_count=int(native.size()),
                   native_operation_counts=examined["native_operations"],
                   full_compiled_dynamic_semantics_inspection=examined,
                   classical_feedback_structurally_preserved=examined["compiler_preserved_source_feedback"],
                   classical_feedback_semantics_certified=examined["classical_feedforward_semantics_certified"],
                   native_hardware_gate_pass=native_cz<=800 and native_depth<=2000,
                   compiler_elapsed_seconds=elapsed,
                   status=("COMPILED_STRUCTURALLY_CERTIFIED"
                           if examined["classical_feedforward_semantics_certified"]
                           else "COMPILED_UNCERTIFIED_DYNAMIC_SEMANTICS"))
                print("DYNAMIC FEZ CPU COMPILE",base,bits,row["status"],
                      "CZ",native_cz,"depth",native_depth,
                      "if_else",examined["native_operations"].get("if_else",0),
                      "hardware_feasible",row["native_hardware_gate_pass"],
                      "ZERO QPU",flush=True)
            except Exception as exc:
                row.update(status="COMPILER_REJECTED_DYNAMIC_SOURCE",
                   compiler_acceptance=False,
                   native_costs_available=False,
                   compilation_error_type=type(exc).__name__,
                   compilation_error_message=str(exc)[:2400],
                   compilation_error_trace=traceback.format_exc()[-2900:])
                print("DYNAMIC FEZ CPU COMPILE REJECTION",base,bits,
                      type(exc).__name__,str(exc)[:750],"ZERO QPU",flush=True)
            save()
        full=all(data["per_precision"][str(bits)]["status"]=="COMPILED_STRUCTURALLY_CERTIFIED"
                 for bits in BITS)
        data["summary"]=dict(
           all_three_widths_tested=True,
           accepted_native_compiles=sum(
             data["per_precision"][str(b)]["compiler_acceptance"] for b in BITS),
           rejected_native_compiles=sum(
             not data["per_precision"][str(b)]["compiler_acceptance"] for b in BITS),
           structurally_certified_dynamic_compiles=sum(
             data["per_precision"][str(b)]["classical_feedback_semantics_certified"] for b in BITS),
           full_dynamic_lowerability_per_base_certified=full,
           target_supports_declared_if_else=support["if_else"],
           target_supports_declared_measure=support["measure"],
           target_supports_declared_reset=support["reset"],
           no_hardware_compatibility_guarantee_even_if_cpu_compiled=True,
           no_hardware_submission_under_any_condition=True)
        data.update(study_completed=True,success=True,status="SOURCE_AND_CPU_TARGET_SUPPORT_STUDY_COMPLETE")
        save()
        print("N35 DYNAMIC FEZ TARGET CPU STUDY COMPLETE",base,
              json.dumps(data["summary"],sort_keys=True),"NO QPU",flush=True)
        return 0
    except Exception as exc:
        data.update(study_completed=False,success=False,status="SETUP_OR_SOURCE_FAILURE",
                    failure_type=type(exc).__name__,
                    failure_message=str(exc)[:2400],
                    failure_trace=traceback.format_exc()[-2900:],
                    qpu_jobs_submitted=0,hardware_shots=0)
        save()
        print("DYNAMIC FEZ TARGET SETUP FAILURE",base,
              type(exc).__name__,str(exc)[:850],
              traceback.format_exc()[-1200:],"ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(parser.parse_args().base))
