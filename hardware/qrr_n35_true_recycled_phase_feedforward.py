#!/usr/bin/env python3
"""Build TRUE one-reused-phase-qubit N35 dynamic inverse-QFT source (ZERO QPU).

Research lead Chase Lunsford / CaMaLabs. Actual Qiskit 32-qubit gate-source:
ONE phase qubit, 6 WORK, 25 clean arithmetic ancillas, b=4/6/8 CLASSICAL bits,
public controlled powers using proven reversible sign-selected arithmetic,
midcircuit measurement, phase-qubit reset, conditioned phase feedback.

Prove each distinct nonidentity controlled-power gate instruction with exact
complex amplitude+1 on 128 control/work basis cases, and independent branch
simulation of all adaptive measurement histories against prior verified WIDE
four/six/eight-bit IQFT distributions. NOT a noisy dynamic-device simulation,
hardware ISA compilation, or IBM QPU job. No backend API or credentials.
"""
from __future__ import annotations
import argparse
import json
import math
import cmath
import traceback
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister
import qrr_n35_static_sign_four_controlled_powers as powers

oldsel=powers.oldsel
previous=oldsel.previous
N=35
WORK_BITS=6
ANCILLAS=25
BASES=(2,8)
BITS=(4,6,8)
REV="qrr-n35-one-true-recycled-phase-qubit-adaptive-iqft-v1-20261020"
ROOT=Path("results/n35_true_recycled_phase_feedforward")
EPS=1e-9


def configure_original_public_arithmetic():
    """Regenerate exact frozen public k-source selector; no backend or order."""
    oldsel.bootstrap_original_best()
    mapping,details,_,_=oldsel.prebackend_static_source_selector()
    assert len(mapping)==34 and all(
        mapping[k]==("signed" if k%2 else "positive") for k in range(1,N))
    for base in BASES:
        hist=powers.archived_original(base)
        assert {str(k):mapping[k] for k in sorted(mapping)}==hist["public_k_sign_selection"]
        assert details==hist["prebackend_public_k_source_score_table"]
    oldsel.SELECTION=dict(mapping)
    oldsel.SIGNED_CALLS=0
    oldsel.POSITIVE_CALLS=0
    oldsel.primitive.modadd=oldsel.structural_selected_modadd
    oldsel.best.optimized_modadd=oldsel.structural_selected_modadd
    return dict(pass_all=True,selection=dict((str(k),mapping[k]) for k in mapping),
                original_public_34_source_rows_exact=True,
                selection_uses_no_order_or_backend=True,
                positive_even_signed_odd=True)


def source_registers(bits=None):
    """One phase QUBIT, shared 6-work+25-helper QUBITS, optional b classical."""
    phase=QuantumRegister(1,"recycled_phase")
    work=QuantumRegister(6,"work")
    acc=QuantumRegister(6,"acc")
    wrap=QuantumRegister(1,"wrap")
    valid=QuantumRegister(1,"valid")
    carry=QuantumRegister(6,"carry")
    scratch=QuantumRegister(9,"scratch")
    active=QuantumRegister(1,"active")
    enable=QuantumRegister(1,"enable")
    registers=[phase,work,acc,wrap,valid,carry,scratch,active,enable]
    classic=ClassicalRegister(bits,"readout") if bits is not None else None
    if classic is not None:registers.append(classic)
    qc=QuantumCircuit(*registers,name="N35_TRUE_ONE_RECYCLED_PHASE")
    r=dict(phase=list(phase),work=list(work),acc=list(acc),wrap=list(wrap),
           valid=list(valid),carry=list(carry),scratch=list(scratch),
           active=list(active),enable=list(enable))
    assert qc.num_qubits==32 and qc.num_clbits==(bits or 0)
    return qc,r,classic


def emit_public_controlled_power(qc,r,power):
    """Verbatim original public 4-wide arithmetic lowering, ONE phase control.

    The common valid flag must already be correctly computed from work<35.
    This part is an actual X/CX/CCX/RCCX source gate sequence, NOT a custom
    UnitaryGate, precomputed orbit, truth table, or integer modular-power oracle.
    """
    power=int(power)%N
    if power==1:return 0
    if not (1<power<N and math.gcd(power,N)==1):
        raise AssertionError("Public multiplier must be a unit modulo35")
    primitive=oldsel.primitive
    ctrl=r["phase"][0]
    active=r["active"][0]
    enable=r["enable"][0]
    valid=r["valid"][0]
    wrap=r["wrap"][0]
    work=r["work"]
    acc=r["acc"]
    carry=r["carry"]
    scratch=r["scratch"]
    inverse=pow(power,-1,N)  # PUBLIC modular inverse, NOT true period/order.
    qc.ccx(ctrl,valid,active)
    for i in range(WORK_BITS):
        qc.ccx(active,work[i],enable)
        primitive.modadd(qc,acc,power*(1<<i),N,
                         [enable],wrap,carry,scratch)
        qc.ccx(active,work[i],enable)
    for before,after in zip(work,acc):
        primitive.controlled_swap(qc,before,after,[active],scratch)
    for i in range(WORK_BITS):
        qc.ccx(active,work[i],enable)
        primitive.modadd(qc,acc,-inverse*(1<<i),N,
                         [enable],wrap,carry,scratch)
        qc.ccx(active,work[i],enable)
    qc.ccx(ctrl,valid,active)
    return 12


def phase_exact_public_stage_proof(power):
    """Real emitted quantum gate proof for ALL 128 c/y with all25 helper clean."""
    qc,r,_=source_registers()
    oldsel.primitive.predicate(qc,r["work"],N,r["valid"][0],
                               r["carry"],r["scratch"],geq=False)
    emitted=emit_public_controlled_power(qc,r,power)
    oldsel.primitive.predicate(qc,r["work"],N,r["valid"][0],
                               r["carry"],r["scratch"],geq=False)
    assert emitted==12
    exact=previous.exhaustive_full_multiplier_phases(qc,r,power)
    assert exact["pass_all"] and exact["full_residue_control_basis_cases"]==128
    assert exact["all_25_auxiliaries_clean"] and exact["exact_complex_output_phase_plus_one"]
    assert exact["control_unmodified"] and exact["disabled_invalid_states_identity"]
    assert exact["quantum_source_gate_counts"] and qc.num_qubits==32
    return dict(public_multiplier=power,source_gate_counts=exact["quantum_source_gate_counts"],
        true_emitted_source_instruction_count=exact["source_instruction_count"],
        actual_gate_basis_cases=128,source_logical_qubits=32,
        all_25_ancilla_bits_clean=True,complex_output_phase_plus_one=True,
        correct_public_residue_modular_multiplication=True)


def build_dynamic_source(base,bits):
    """A Qiskit circuit, NOT merely an analytically forecast circuit."""
    qc,r,c=source_registers(bits)
    assert c is not None
    qc.x(r["work"][0])   # prepare |work=1>
    oldsel.primitive.predicate(qc,r["work"],N,r["valid"][0],
                               r["carry"],r["scratch"],geq=False)
    schedule=[]
    feedback=[]
    for j in range(bits-1,-1,-1):
        phase=r["phase"][0]
        multiplier=pow(base,1<<j,N)
        qc.h(phase)
        addcount=emit_public_controlled_power(qc,r,multiplier)
        # Earlier measured steps t>j contain LOW bits of phase fraction.
        # Output k's bit-position is bits-1-t, not phase power-index t.
        for t in range(bits-1,j,-1):
            angle=-2*math.pi/(1<<(t-j+1))
            prior_bit_index=bits-1-t
            with qc.if_test((c[prior_bit_index],1)):
                qc.p(angle,phase)
            feedback.append(dict(stage_j=j,earlier_stage_t=t,
                classical_control_index=prior_bit_index,
                conditional_bit_value=1,phase_gate_angle_radians=angle))
        qc.h(phase)
        destination=bits-1-j
        qc.measure(phase,c[destination])
        if j>0:qc.reset(phase)
        schedule.append(dict(stage_j=j,public_multiplier=multiplier,
            weighted_mod35_additions=addcount,
            identity_stage_skipped=(multiplier==1),
            measured_classical_index=destination,
            reset_after_measurement=(j>0)))
    # Work+valid coherent correlation is uncomputed without measuring work.
    oldsel.primitive.predicate(qc,r["work"],N,r["valid"][0],
                               r["carry"],r["scratch"],geq=False)
    return qc,r,c,schedule,feedback


def inspect_dynamic_source(qc,r,c,base,bits,schedule,feedback):
    """Check source control-flow structure/conditional gates, no QPU call."""
    assert qc.num_qubits==32 and qc.num_clbits==bits
    assert len(r["phase"])==1 and len(r["work"])==6
    assert sum(len(r[z]) for z in ("acc","wrap","valid","carry","scratch","active","enable"))==25
    assert [z["stage_j"] for z in schedule]==list(range(bits-1,-1,-1))
    assert [z["measured_classical_index"] for z in schedule]==list(range(bits))
    assert [z["public_multiplier"] for z in schedule]==[
           pow(base,1<<j,N) for j in range(bits-1,-1,-1)]
    counts={str(k):int(v) for k,v in qc.count_ops().items()}
    expected_if=bits*(bits-1)//2
    assert counts.get("h",0)==bits*2,(counts,bits)
    assert counts.get("measure",0)==bits,(counts,bits)
    assert counts.get("reset",0)==bits-1,(counts,bits)
    assert counts.get("if_else",0)==expected_if,(counts,bits)
    assert len(feedback)==expected_if
    actual_feedback=[]
    actual_measure_bits=[]
    actual_reset=0
    for inst in qc.data:
        op=inst.operation
        if op.name=="if_else":
            ctrl,expected=op.condition
            assert expected==1 and ctrl in c
            blocks=op.blocks
            assert len(blocks)==2 or len(blocks)==1
            body=blocks[0]
            assert body is not None and len(body.data)==1
            assert body.data[0].operation.name=="p"
            assert len(inst.qubits)==1 and inst.qubits[0]==r["phase"][0]
            actual_feedback.append((list(c).index(ctrl),
                                    float(body.data[0].operation.params[0])))
        elif op.name=="measure":
            assert len(inst.qubits)==1 and inst.qubits[0]==r["phase"][0]
            actual_measure_bits.append(list(c).index(inst.clbits[0]))
        elif op.name=="reset":
            assert len(inst.qubits)==1 and inst.qubits[0]==r["phase"][0]
            actual_reset+=1
    assert actual_measure_bits==list(range(bits))
    assert actual_reset==bits-1
    expected_feedback=[(f["classical_control_index"],f["phase_gate_angle_radians"])
                       for f in feedback]
    assert len(actual_feedback)==len(expected_feedback)
    for (a,aa),(b,bb) in zip(actual_feedback,expected_feedback):
        assert a==b and abs(aa-bb)<1e-12,(actual_feedback,expected_feedback)
    names=set(counts)
    assert names.issubset({"h","x","cx","ccx","rccx","measure","reset","if_else"}),names
    assert all(row["weighted_mod35_additions"]==(0 if row["identity_stage_skipped"] else 12)
               for row in schedule)
    return dict(pass_all=True,source_quantum_qubits=32,
       source_classical_result_bits=bits,
       actual_midcircuit_measure_count=counts["measure"],
       actual_midcircuit_reset_count=counts["reset"],
       actual_H_count=counts["h"],
       actual_classical_if_else_feedback_count=counts["if_else"],
       public_stage_build_sequence=schedule,
       all_conditional_feedback_gates_inspected=True,
       exact_feedback_angles_and_prior_classical_bit_controls=True,
       IQFT_measurements_lsb_first_in_classical_output=True,
       actual_Qiskit_dynamic_gate_operation_counts=counts,
       physical_ISA_native_cost_not_computed=True,
       actual_qpu_jobs=0)


def emit_branch_model_probabilities(base,bits):
    """Ideal sequential quantum instrument on coherent SIX WORK qubits.

    Unnormalized 64-work vectors for every measurement-history branch are
    propagated through H, public controlled multiplier, classical P feedback,
    H and projective measurement. This is NOT a Qiskit dynamic hardware run.
    """
    branches={0:np.eye(64,dtype=complex)[1]}
    stage_details=[]
    for j in range(bits-1,-1,-1):
        multiplier=pow(base,1<<j,N)
        next_branches={}
        for k_so_far,work in branches.items():
            rotated=np.zeros_like(work)
            for y,amplitude in enumerate(work):
                after=(multiplier*y)%N if y<N else y
                rotated[after]+=amplitude
            if abs(float(np.vdot(work,work).real)-
                   float(np.vdot(rotated,rotated).real))>1e-10:
                raise AssertionError("Controlled public multiplier not norm-preserving")
            phase_angle=-2*math.pi*sum(
              ((k_so_far>>(bits-1-t))&1)/(1<<(t-j+1))
              for t in range(bits-1,j,-1))
            feedback=np.exp(1j*phase_angle)
            plus=(work+feedback*rotated)/2
            minus=(work-feedback*rotated)/2
            next_branches[k_so_far]=plus
            next_branches[k_so_far | (1<<(bits-1-j))]=minus
        branches=next_branches
        norm=sum(float(np.vdot(v,v).real) for v in branches.values())
        if abs(norm-1)>1e-10:
            raise AssertionError(f"Recycled phase quantum branch norm violated j={j} total={norm}")
        stage_details.append(dict(stage_j=j,public_multiplier=multiplier,
            active_branches=len(branches),branch_probability_sum=norm,
            all_work_register_amplitudes_retained=True))
    M=1<<bits
    assert len(branches)==M and set(branches)==set(range(M))
    probabilities=[float(np.vdot(branches[k],branches[k]).real)
                   for k in range(M)]
    if abs(sum(probabilities)-1)>1e-10 or min(probabilities)<-1e-10:
        raise AssertionError("Final ideal recycled branch distribution invalid")
    return probabilities,dict(
       pass_all=True,source_phase_qubits_reused=1,work_register_bits=6,
       input_work_basis_one=True,full_work_coherence_preserved=True,
       branch_result_count=M,all_histories_enumerated=True,
       all_stage_probability_sums_equal_one=True,
       final_probability_sum=sum(probabilities),
       bits_output_convention="stage j -> classical bit bits-1-j",
       phase_feedback_convention="angle -2pi sum_{t>j} measured_stage_t / 2^(t-j+1)",
       no_true_order_or_factor_used=True,
       conditional_work_branch_distribution_simulated=True,
       not_an_end_to_end_Qiskit_dynamic_shot_simulation=True,
       stage_norm_summaries=stage_details)


def preserved_wide_ideal(base,bits):
    src=json.loads(Path(
        f"results/n35_ideal_phase_precision/qrr_n35_ideal_phase_precision_base{base}.json"
    ).read_text())
    assert src["success"] and src["N"]==N and src["public_base"]==base
    z=src["outcomes_by_phase_bits"][str(bits)]
    p=z["quantum_probability_verification"]
    assert p["pass_all"] and p["independent_Numpy_complex_FFT"]
    assert p["independent_literal_Qiskit_QFTGate_Statevector"]
    assert p["actual_complex_amplitude_comparison_count"]==(1<<bits)*64
    assert p["max_complex_amplitude_difference"]<EPS
    return z


def run_base(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    output=ROOT/f"qrr_n35_recycled_phase_feedforward_base{base}.json"
    data=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
        computed_utc=datetime.now(timezone.utc).isoformat(),
        preregistration="docs/QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_PREREG.md",
        N=N,public_base=base,phase_precision_bits=list(BITS),
        one_reused_phase_qubit=True,source_logical_qubits=32,
        original_six_work_plus_25_helpers_preserved=True,
        original_wide_source_verification_only_for_4bit=True,
        original_higher_width_projections_only_ideal=True,
        native_compiler_not_called=True,
        IBM_backend_or_token_not_used=True,
        actual_QPU_jobs=0,actual_device_shots=0,quantum_runtime_used=False,
        full_results={},phase_exact_stage_proofs={},
        success=False,status="STARTED")
    def save():output.write_text(json.dumps(data,indent=2,default=str)+"\n")
    save()
    try:
        selector=configure_original_public_arithmetic()
        data["original_public_source_selection_exact"]=selector
        required=sorted(set(pow(a,1<<j,N) for a in BASES
                            for bits in BITS for j in range(bits) if pow(a,1<<j,N)!=1))
        assert required==[2,4,8,11,16,29],required
        data["verified_distinct_nonidentity_public_powers"]=required
        for power in required:
            # Standalone actual gate phase proof has 32 qubits, 128 inputs.
            p=phase_exact_public_stage_proof(power)
            data["phase_exact_stage_proofs"][str(power)]=p
            save()
            print("ACTUAL SELECTED MODARITH 32Q PHASE PROOF",
                  power,"128/128 full six-bit and control; 25 AUX CLEAN, phase +1",
                  flush=True)
        data["total_distinct_stage_gate_semantic_cases"]=len(required)*128
        assert data["total_distinct_stage_gate_semantic_cases"]==768
        for bits in BITS:
            qc,r,c,stage,feedback=build_dynamic_source(base,bits)
            structure=inspect_dynamic_source(qc,r,c,base,bits,stage,feedback)
            predict,branch=emit_branch_model_probabilities(base,bits)
            wide=preserved_wide_ideal(base,bits)
            wide_prob=wide["exact_ideal_probabilities_all_outcomes"]
            assert len(predict)==len(wide_prob)==(1<<bits)
            errors=[abs(a-b) for a,b in zip(predict,wide_prob)]
            max_error=max(errors)
            if max_error>EPS:
                idx=int(np.argmax(errors))
                raise AssertionError(json.dumps(dict(
                    stage="recycled versus wide exact ideal outcome",
                    bits=bits,base=base,k=idx,
                    recycled=predict[idx],wide=wide_prob[idx],
                    max_delta=max_error)))
            score=wide["public_postprocessing"]
            strict_dynamic=sum(v*int(row["strict_CF_convergents"]["success"])
                 for v,row in zip(predict,wide["outcomes"]))
            bounded_dynamic=sum(v*int(row["bounded_public_multiples_upto_four"]["success"])
                 for v,row in zip(predict,wide["outcomes"]))
            if abs(strict_dynamic-score["strict_CF_ideal_success_probability"])>EPS:
                raise AssertionError("Changed STRICT public CF score")
            if abs(bounded_dynamic-score["bounded_4_public_multiples_ideal_success_probability"])>EPS:
                raise AssertionError("Changed BOUNDED public CF score")
            data["full_results"][str(bits)]=dict(
                phase_precision_bits=bits,public_base=base,
                dynamic_gate_source_structure=structure,
                ideal_conditional_quantum_branch_proof=branch,
                all_outcome_probabilities_recycled=predict,
                archived_wide_ideal_reference_probabilities=wide_prob,
                exact_recycled_vs_wide_probability_comparisons=len(predict),
                maximum_absolute_probability_difference=max_error,
                all_outcomes_match_independent_wide_IQFT=True,
                public_factor_strict_ideal_probability=strict_dynamic,
                public_factor_bounded_ideal_probability=bounded_dynamic,
                public_factor_policy_unchanged=True,
                quantum_gate_source_built_32_qubits=True,
                real_hardware_runtime_or_native_compilation=False)
            data["status"]=f"DYNAMIC_RECYCLING_IDEAL_{bits}BIT_PASS"
            save()
            print("TRUE RECYCLED ONE PHASE QUBIT IDEAL",base,
                "bits",bits,"QUANTUM_WIDTH",qc.num_qubits,
                "CLASSICAL_MEASUREMENTS",qc.num_clbits,
                "branch_vs_wide_max_prob_delta",max_error,
                "STRICT",strict_dynamic,"BOUNDED",bounded_dynamic,
                "MIDCIRCUIT_RESETS",structure["actual_midcircuit_reset_count"],
                "IF_FEEDFORWARD",structure["actual_classical_if_else_feedback_count"],
                "NO BACKEND NO QPU",flush=True)
        assert sum(x["exact_recycled_vs_wide_probability_comparisons"]
                   for x in data["full_results"].values())==336
        data["total_exact_phase_outcome_probabilities_compared"]=336
        data["status"]="ALL_4_6_8_TRUE_RECYCLED_DYNAMIC_SOURCE_AND_IDEAL_BRANCH_PROOFS_PASS"
        data["success"]=True
        save()
        print("COMPLETE TRUE ONE-RECYCLED PHASE QUBIT",base,
              "32 actual source qubits; 768 standalone emitted-phase cases",
              "336 adaptive-vs-wide ideal outcome checks, all agree, no QPU",flush=True)
        return 0
    except Exception as exc:
        data.update(success=False,status="FAIL",
            failure_type=type(exc).__name__,failure_message=str(exc)[:1800],
            failure_traceback=traceback.format_exc()[-3000:],
            actual_QPU_jobs=0,quantum_runtime_used=False)
        save()
        print("TRUE RECYCLED N35 SEMICLASSICAL IQFT FAIL",base,
              type(exc).__name__,str(exc)[:750],
              traceback.format_exc()[-1500:],"ZERO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(run_base(parser.parse_args().base))
