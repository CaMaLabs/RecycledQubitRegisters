#!/usr/bin/env python3
"""Independent native conditional feedforward phase certification, CPU ONLY.

Research lead Chase Lunsford / CaMaLabs. Rebuild the exact ORIGINAL Qiskit
32-qubit one-recycled-phase N35 source; transpile with the old read-only Fez
target, opt1 seed8776, bases2/8, b4/6/8. Verify Qiskit Operator of every
compiled if_else true-body against source PhaseGate(angle), UP TO A GLOBAL
PHASE PER *ALREADY CLASSICALLY MEASURED* measurement-history branch.
This is NOT physical quantum execution, no Sampler/Estimator/backend.run.
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

import numpy as np
from qiskit.circuit.library import PhaseGate
from qiskit.quantum_info import Operator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_true_recycled_dynamic_fez_isa as oldaudit

BASES=(2,8)
BITS=(4,6,8)
N=35
SEED=8776
REV="qrr-n35-fez-compiled-classical-feedback-phase-operator-v1-20261021"
ROOT=Path("results/ibm_shor35_true_recycled_dynamic_feedback_audit")
EPS=1e-9


def expected_feedback(bits):
    # Exact old Qiskit semi-classical IQFT convention, DO NOT tune.
    return [(bits-1-t, -2*math.pi/(1<<(t-j+1)),j,t)
             for j in range(bits-1,-1,-1) for t in range(bits-1,j,-1)]


def certify_branch_operators(compiled, bits):
    """Examine actual condition, native true-body matrix and phase-wire map.

    Source P(θ) = e^(iθ/2) RZ(θ). The phase discrepancy from RZ is
    unobservable IF its condition is an earlier classically measured bit.
    """
    ops={str(k):int(v) for k,v in compiled.count_ops().items()}
    expected=dict(if_else=bits*(bits-1)//2,measure=bits,reset=bits-1)
    issues=[]
    for name,n in expected.items():
        if ops.get(name,0)!=n:issues.append(
            f"{name} count changed {ops.get(name,0)} != {n}")
    if compiled.num_clbits!=bits:
        issues.append(f"classical width {compiled.num_clbits} != {bits}")
    if compiled.num_qubits<32:
        issues.append(f"compiler width {compiled.num_qubits} < 32 source qubits")
    native_dynamic=[]
    measured=[]
    resets=[]
    for item in compiled.data:
        name=item.operation.name
        physical=[compiled.find_bit(q).index for q in item.qubits]
        if name=="measure":
            if len(physical)!=1 or len(item.clbits)!=1:
                issues.append("unexpected multi-qubit/multicbit measurement")
            else:
                measured.append(dict(qubit=physical[0],
                                     classical_bit=compiled.find_bit(item.clbits[0]).index))
        if name=="reset":
            if len(physical)!=1:issues.append("reset has more than one physical qubit")
            else:resets.append(physical[0])
        if name!="if_else":continue
        op=item.operation
        condition=getattr(op,"condition",None)
        if not isinstance(condition,tuple) or len(condition)!=2:
            issues.append("native conditional is not (Clbit, literal)")
            native_dynamic.append(dict(unrecognized_condition=str(condition)))
            continue
        classical, required=condition
        try: bitidx=int(compiled.find_bit(classical).index)
        except Exception:
            bitidx=-1
            issues.append("native classical condition bit is unresolved")
        if required!=1:issues.append("native conditional tests a value other than 1")
        bodies=getattr(op,"blocks",None)
        if not bodies or bodies[0] is None:
            issues.append("native if_else lacks executable true-body")
            native_dynamic.append(dict(classical_bit=bitidx,
                physical_qubits=physical,condition_literal=required,
                body_present=False))
            continue
        true_body=bodies[0]
        row=dict(classical_bit=bitidx,condition_literal=required,
                 physical_qubits=physical,
                 body_present=True,
                 body_qubits=int(true_body.num_qubits),
                 body_original_operation_names=[instr.operation.name for instr in true_body.data],
                 body_global_phase=float(true_body.global_phase),
                 body_classical_bits=int(true_body.num_clbits),
                 has_nontrivial_else=(
                    len(bodies)>1 and bodies[1] is not None and len(bodies[1].data)>0))
        if row["has_nontrivial_else"]:
            issues.append("unpreregistered native ELSE branch unexpectedly acts")
        if true_body.num_qubits!=1 or len(physical)!=1:
            issues.append(f"native phase conditional is not single-qubit: {physical}")
        try:
            mat=np.asarray(Operator(true_body).data,dtype=complex)
            if mat.shape!=(2,2):
                issues.append("native conditional body not a 2x2 unitary")
            row["_matrix"]=mat
        except Exception as exc:
            row["operator_exception"]=type(exc).__name__+": "+str(exc)[:500]
            issues.append("could not evaluate native body Operator")
        native_dynamic.append(row)
    exp=expected_feedback(bits)
    if len(native_dynamic)!=len(exp):
        issues.append(f"conditional count {len(native_dynamic)} != expected {len(exp)}")
    for i,row in enumerate(native_dynamic):
        if i>=len(exp):break
        target_bit,angle,stage_j,earlier_t=exp[i]
        row["expected_classical_bit"]=target_bit
        row["expected_phase_angle"]=angle
        row["stage_j"]=stage_j
        row["earlier_stage_t"]=earlier_t
        if row.get("classical_bit")!=target_bit:
            issues.append(f"conditional #{i} wrong measured classical control bit")
        if row.get("condition_literal")!=1:
            issues.append(f"conditional #{i} not condition=1")
        if "_matrix" not in row:
            row["equivalent_to_source_phasegate_up_to_global_phase"]=False
            continue
        want=np.asarray(Operator(PhaseGate(angle)).data,dtype=complex)
        observed=row.pop("_matrix")
        overlap=complex(np.trace(want.conj().T@observed)/2)
        residual=float(np.max(np.abs(observed-overlap*want)))
        row["unitary_trace_overlap_magnitude"]=abs(overlap)
        row["phase_unitary_max_error_after_global_alignment"]=residual
        row["conditional_branch_global_phase_radians"]=float(np.angle(overlap))
        row["equivalent_to_source_phasegate_up_to_global_phase"]=bool(
              abs(abs(overlap)-1)<EPS and residual<EPS)
        if not row["equivalent_to_source_phasegate_up_to_global_phase"]:
            issues.append(f"conditional #{i} native 2x2 body not PhaseGate(theta) up to global")
    if [m["classical_bit"] for m in measured]!=list(range(bits)):
        issues.append("compiled measurements no longer populate classical bits in source order")
    # Extra physical location information is evidence; an ISA compiler may route
    # through multiple physical qubits. We assert one phase wire only if true.
    phase_locs=sorted(set(
        [m["qubit"] for m in measured]+resets+
        [row["physical_qubits"][0] for row in native_dynamic
         if len(row.get("physical_qubits",[]))==1]))
    single_phase_wire=len(phase_locs)==1
    if not single_phase_wire:
        issues.append("compiled phase operations map to multiple physical wires; reuse not independently certified")
    report=dict(
        pass_all=not issues,
        original_classical_feedback_count=len(exp),
        emitted_compiled_if_else_count=len(native_dynamic),
        all_native_condition_body_operators_proved=all(
            row.get("equivalent_to_source_phasegate_up_to_global_phase",False)
            for row in native_dynamic) and len(native_dynamic)==len(exp),
        measurement_classical_targets=[m["classical_bit"] for m in measured],
        measured_physical_phase_positions=[m["qubit"] for m in measured],
        reset_physical_phase_positions=resets,
        conditional_physical_phase_positions=[
            row.get("physical_qubits",[]) for row in native_dynamic],
        recycled_phase_single_compiled_physical_wire=single_phase_wire,
        unique_compiled_phase_locations=phase_locs,
        dynamic_operation_counts=ops,
        fully_certified_prior_classical_measurement_conditions=not any(
          "classical" in issue or "condition" in issue.lower() for issue in issues),
        branch_global_phase_equivalence_is_not_physical_noise_validation=True,
        native_device_fidelity_or_feedback_latency_not_measured=True,
        problems=issues,
        conditional_phase_unitaries=native_dynamic)
    return report


def run_base(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    output=ROOT/f"qrr_n35_native_dynamic_feedback_phase_base{base}.json"
    record=dict(
      revision=REV,research_lead="Chase Lunsford / CaMaLabs",
      timestamp_utc=datetime.now(timezone.utc).isoformat(),
      preregistration="docs/QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_PREREG.md",
      public_N=N,public_base=base,phase_widths=list(BITS),
      compiler_target_backend="ibm_fez",compiler_opt=1,compiler_seed=SEED,
      source_one_recycled_phase_qubit=True,source_quantum_qubits=32,
      physical_preflight_max_native_cz=800,physical_preflight_max_native_depth=2000,
      private_factors_used=False,true_order_injected=False,
      observed_real_quantum_jobs=0,
      zero_ibm_free_or_paid_qpu_runtime=True,no_runtime_job_submissions=True,
      compiled_feedback_proofs={},status="STARTED",study_completed=False,success=False)
    def save():output.write_text(json.dumps(record,indent=2,default=str)+"\n")
    save()
    try:
        circuits,prepared=oldaudit.original_structure_exact(base)
        old=json.loads(Path(
            f"results/ibm_shor35_true_recycled_dynamic_fez_isa/"
            f"qrr_n35_dynamic_isa_base{base}.json").read_text())
        assert old["study_completed"] and old["success"] and old["public_base"]==base
        assert old["summary"]["accepted_native_compiles"]==3
        assert old["summary"]["structurally_certified_dynamic_compiles"]==0
        record["source_integrity_from_unchanged_original"]=prepared
        record["original_exact_native_isa_receipt_reference"]=dict(
            original_revision=old["revision"],
            original_scientific_source_run_id=39729198098,
            independent_raw_original_audit_run_id=39729456702)
        record["status"]="SOURCE_B4_B6_B8_EXACT"
        save()
        print("FEEDBACK PHASE AUDIT ORIGINAL SOURCE EXACT",base,
           "b4/6/8, 32q, archived 768 clean operator tests, 336 exact wide IQFT",
           "before backend read",flush=True)
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
             plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        assert not getattr(backend,"simulator",False) and backend.num_qubits>=32
        operations=sorted(str(x) for x in backend.target.operation_names)
        assert all(x in operations for x in ("if_else","measure","reset"))
        record["actual_target_read_only_capabilities"]=dict(
           qubits=backend.num_qubits,instructions=operations,
           if_else_declared="if_else" in operations,reset_declared="reset" in operations,
           measure_declared="measure" in operations)
        save()
        for bits in BITS:
            row=dict(bits=bits,source_quantum_qubits=32,
              source_classical_result_bits=bits,status="COMPILER_ATTEMPT",
              native_phase_branch_operators_certified=False,
              historical_native_counts_reproduced=False,
              no_hardware_run=True)
            record["compiled_feedback_proofs"][str(bits)]=row
            save()
            try:
                pm=generate_preset_pass_manager(backend=backend,
                   optimization_level=1,seed_transpiler=SEED)
                t0=time.perf_counter()
                compiled=pm.run(circuits[bits])
                seconds=time.perf_counter()-t0
                inspected=certify_branch_operators(compiled,bits)
                native_ops={str(k):int(v) for k,v in compiled.count_ops().items()}
                cz=native_ops.get("cz",0)
                depth=int(compiled.depth())
                prior=old["per_precision"][str(bits)]
                historical=(prior["compiler_acceptance"] and
                     cz==prior["native_cz"] and depth==prior["native_depth"]
                     and native_ops==prior["native_operation_counts"])
                row.update(
                   status=("NATIVE_DYNAMIC_FEEDBACK_PHASE_CERTIFIED"
                      if inspected["pass_all"] and historical
                      else "NATIVE_DYNAMIC_FEEDBACK_PHASE_NOT_CERTIFIED"),
                   compiler_acceptance=True,
                   compiled_native_cz=cz,
                   compiled_native_depth=depth,
                   native_ops=native_ops,
                   compiled_qubit_width=int(compiled.num_qubits),
                   compiled_classical_width=int(compiled.num_clbits),
                   compile_elapsed_seconds=seconds,
                   actual_native_conditional_operators=inspected,
                   historical_native_counts_reproduced=bool(historical),
                   native_phase_branch_operators_certified=bool(
                      inspected["pass_all"] and historical),
                   device_cz_depth_feasibility=bool(cz<=800 and depth<=2000))
                print("FEZ TRUE DYNAMIC PHASE OPERATOR",base,"b",bits,
                   row["status"],"all classically conditioned matrices",
                   inspected["all_native_condition_body_operators_proved"],
                   "one physical phase wire",inspected["recycled_phase_single_compiled_physical_wire"],
                   "historical native anchor",historical,
                   "CZ",cz,"depth",depth,"problems",inspected["problems"][:3],
                   "ZERO QPU",flush=True)
            except Exception as exc:
                row.update(status="NATIVE_PHASE_AUDIT_EXCEPTION",
                   compiler_acceptance=False,exception_type=type(exc).__name__,
                   exception_message=str(exc)[:1800],
                   exception_traceback=traceback.format_exc()[-2400:])
                print("FEZ NATIVE FEEDBACK PHASE EXCEPTION",base,bits,
                    type(exc).__name__,str(exc)[:800],flush=True)
            save()
        ncert=sum(record["compiled_feedback_proofs"][str(b)]["native_phase_branch_operators_certified"]
                  for b in BITS)
        record["summary"]=dict(all_three_precision_widths_tested=True,
          strictly_certified_widths=ncert,
          all_original_native_costs_unchanged=all(
            record["compiled_feedback_proofs"][str(b)]["historical_native_counts_reproduced"]
            for b in BITS),
          all_conditional_phase_semantics_certified=(ncert==3),
          no_real_qpu_job_or_fidelity_claims=True,
          all_hardware_resource_gates_failed=all(
             not record["compiled_feedback_proofs"][str(b)].get("device_cz_depth_feasibility",False)
             for b in BITS))
        record.update(study_completed=True,success=True,
                      status="NATIVE_CONDITIONAL_PHASE_SOURCE_COMPARISON_COMPLETE")
        save()
        print("N35 FEZ DYNAMIC IF ELSE CONDITIONAL UNITARY STUDY",base,
            json.dumps(record["summary"],sort_keys=True),"ZERO QPU",flush=True)
        return 0
    except Exception as exc:
        record.update(study_completed=False,success=False,status="SOURCE_OR_BACKEND_FAILURE",
          failure_type=type(exc).__name__,failure_message=str(exc)[:1800],
          failure_stack=traceback.format_exc()[-2600:],
          observed_real_quantum_jobs=0)
        save()
        print("N35 FEZ NATIVE DYNAMIC PHASE SOURCE FAILURE",base,
             type(exc).__name__,str(exc)[:750],
             traceback.format_exc()[-1200:],"ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(run_base(p.parse_args().base))
