#!/usr/bin/env python3
"""Falsify idle-scratch hypothesis on genuine recycled-phase N35 dynamic circuits.

Lead Chase Lunsford / CaMaLabs. Rebuild the ORIGINAL fixed public Qiskit
phase-measure/reset/conditional circuit, prove all 9 scratch wires have no
actual instruction operands, then create 23q source with exactly identical
remaining instructions and same classical wires. Run 4 paired Fez CPU-target
compilation seeds for b4/6/8, bases2/8. Real IBM QPU jobs strictly ZERO.
"""
from __future__ import annotations
import argparse,json,os,time,traceback,statistics
from datetime import datetime,timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_true_recycled_dynamic_fez_isa as reference
import qrr_n35_native_dynamic_feedback_phase_audit as feedback

N=35
BASES=(2,8)
BITS=(4,6,8)
SEEDS=(509,1223,4093,8776)
OPT=1
REV="qrr-n35-true-recycled-23q-idle-scratch-prune-v1-20261022"
ROOT=Path("results/ibm_shor35_true_recycled_idle_scratch_pruning")
PREVIOUS_NATIVE={
    2:{4:(29813,69008),6:(43613,99325),8:(59446,138604)},
    8:{4:(14499,34259),6:(14499,34259),8:(14499,34259)}
}


def source_dynamic_audit(orig,bits):
    """Top-level instruction operands plus actual nested conditional body checks."""
    scratch=[reg for reg in orig.qregs if reg.name=="scratch"]
    if len(scratch)!=1 or len(scratch[0])!=9:
        raise AssertionError("Original exact dynamic source missing one 9q scratch register")
    unused=set(scratch[0])
    used_scratch=[]
    all_phase=set(reg[0] for reg in orig.qregs if reg.name=="recycled_phase")
    assert len(all_phase)==1
    for idx,ins in enumerate(orig.data):
        for qb in ins.qubits:
            if qb in unused:
                used_scratch.append(dict(instruction=idx,gate=ins.operation.name,
                                          qubit_source_index=orig.find_bit(qb).index))
        if ins.operation.name=="if_else":
            # Dynamic body local qubit arguments are attached to the ONE
            # parent phase wire. They cannot reference scratch.
            if len(ins.qubits)!=1 or ins.qubits[0] not in all_phase:
                raise AssertionError("Classical feedback block unexpectedly touches a non-phase source qubit")
            for block in ins.operation.blocks:
                if block is None:continue
                if block.num_qubits!=1:
                    raise AssertionError("Nested feedback block unexpectedly touches multiple quantum wires")
                for body in block.data:
                    if len(body.qubits)!=1:
                        raise AssertionError("Unknown multi-wire nested quantum feedback")
    counts={str(k):int(v) for k,v in orig.count_ops().items()}
    assert counts.get("measure")==bits and counts.get("reset")==bits-1
    assert counts.get("if_else")==bits*(bits-1)//2
    if used_scratch:
        raise AssertionError("SCRATCH IS LIVE: "+json.dumps(used_scratch[:6]))
    return scratch[0],dict(
       original_source_width=orig.num_qubits,
       original_classical_width=orig.num_clbits,
       scratch_qubits_checked=len(unused),
       scratch_live_instruction_count=0,
       scratch_all_nine_actually_unused=True,
       source_instruction_count=len(orig.data),
       source_gate_count=orig.size(),
       original_source_gate_counts=counts,
       source_phase_reused_qubit_count=1,
       all_conditionals_one_phase_wire=True,
       original_measurement_count=counts["measure"],
       original_reset_count=counts["reset"],
       original_conditional_count=counts["if_else"])


def reduction_with_exact_instruction_identity(original,bits):
    scratch,source_info=source_dynamic_audit(original,bits)
    kept=[reg for reg in original.qregs if reg.name!='scratch']
    assert len(kept)==len(original.qregs)-1
    assert not any(r.name=="scratch" for r in kept)
    pruned=QuantumCircuit(*kept,*original.cregs,
        name=f"N35_ONE_RECYCLED_PHASE_B{bits}_23Q_IDLE_SCRATCH_REMOVED")
    assert pruned.num_qubits==23 and original.num_qubits==32
    assert pruned.num_clbits==original.num_clbits==bits
    assert pruned.qubits==[qb for qb in original.qubits if qb not in scratch]
    assert pruned.clbits==original.clbits
    for i,ins in enumerate(original.data):
        if any(qb in scratch for qb in ins.qubits):
            raise AssertionError("Scratch operand encountered during exact quantum instruction replay")
        pruned.append(ins.operation,ins.qubits,ins.clbits)
    if len(pruned.data)!=len(original.data):
        raise AssertionError("Changed source instruction count")
    for idx,(old,new) in enumerate(zip(original.data,pruned.data)):
        if old.operation.name!=new.operation.name:
            raise AssertionError("Changed operation name at "+str(idx))
        if tuple(old.qubits)!=tuple(new.qubits) or tuple(old.clbits)!=tuple(new.clbits):
            raise AssertionError("Changed emitted operand identity at "+str(idx))
        if old.operation!=new.operation:
            raise AssertionError("Changed operation unitary/control-flow definition at "+str(idx))
        if old.operation.name=="if_else":
            if old.operation.condition!=new.operation.condition:
                raise AssertionError("Changed earlier measured classical control")
            if len(old.operation.blocks)!=len(new.operation.blocks):
                raise AssertionError("Changed feedback branch count")
            for ob,nb in zip(old.operation.blocks,new.operation.blocks):
                if ob is None or nb is None:
                    assert ob is None and nb is None
                else:
                    assert ob==nb
    same_ops={str(k):int(v) for k,v in pruned.count_ops().items()}
    assert same_ops==source_info["original_source_gate_counts"]
    return pruned,dict(**source_info,
       reduced_source_width=pruned.num_qubits,
       removed_idle_source_qubits=9,
       unchanged_original_instruction_order_and_operands=True,
       unchanged_original_gate_operations_and_params=True,
       unchanged_conditional_body_and_previous_classical_control=True,
       unchanged_original_native_gate_source_histogram=True,
       dynamic_measure_reset_and_feedback_preserved=True,
       mathematically_identical_reduced_source_instrument_on_live_registers=True,
       not_newly_rerunning_archived_768_stage_or_672_outcome_ideal_proofs=True)


def one_compilation(pass_manager,qc,bits,version):
    started=time.perf_counter()
    native=pass_manager.run(qc)
    elapsed=time.perf_counter()-started
    ops={str(k):int(v) for k,v in native.count_ops().items()}
    cz=ops.get("cz",0)
    depth=int(native.depth())
    branch=feedback.certify_branch_operators(native,bits)
    controlled=bool(branch["all_native_condition_body_operators_proved"] and
        branch["fully_certified_prior_classical_measurement_conditions"] and
        branch["emitted_compiled_if_else_count"]==bits*(bits-1)//2 and
        branch["measurement_classical_targets"]==list(range(bits)) and
        ops.get("measure")==bits and ops.get("reset")==bits-1)
    if not controlled:
        raise AssertionError("Native compiled classical feedforward branch operator mismatch: "+
                             str(branch["problems"])[:650])
    if cz<=0 or depth<=0:
        raise AssertionError("Bad native CZ/depth from CPU")
    physical=sorted(set(native.find_bit(q).index for inst in native.data for q in inst.qubits))
    return dict(version=version,compiled_native_cz=int(cz),compiled_native_depth=depth,
       native_operation_counts=ops,
       compiled_device_qubit_width=int(native.num_qubits),
       compiled_classical_result_width=int(native.num_clbits),
       compiled_total_native_ops=int(native.size()),
       distinct_physically_touched_addresses=len(physical),
       phase_related_physical_locations=branch["unique_compiled_phase_locations"],
       phase_single_fixed_physical_address_proven=branch["recycled_phase_single_compiled_physical_wire"],
       physical_phase_mapping_not_proven=not branch["recycled_phase_single_compiled_physical_wire"],
       conditional_if_else_operator_equivalence_pass=True,
       checked_compiled_conditional_count=branch["emitted_compiled_if_else_count"],
       compiled_feedforward_control_classical_bit_order_preserved=True,
       compiler_elapsed_seconds=elapsed,
       hardware_gate_pass=bool(cz<=800 and depth<=2000),
       hardware_backend_exec_or_latency_NOT_measured=True)


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    out=ROOT/f"qrr_n35_prune_idle_scratch_base{base}.json"
    receipt=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
       date_utc=datetime.now(timezone.utc).isoformat(),
       preregistration="docs/QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_PREREG.md",
       N=N,public_base=base,phase_precision_list=list(BITS),
       transpiler_seeds=list(SEEDS),transpiler_optimization_level=OPT,
       backend_target="ibm_fez",original_source_width=32,
       candidate_source_width=23,candidate_removed_only_nine_idle_scratch=True,
       previous_frozen_seed8776=PREVIOUS_NATIVE[base],
       original_real_recycled_phase_qubit_count=1,
       original_six_work_qubits_unmodified=True,
       original_improved_arithmetic_unchanged=True,
       previous_original_768_stage_proof_archived=True,
       original_336_phase_outcome_probabilities_per_base_archived=True,
       true_modular_order_not_injected=True,public_N35_factors_not_compiled=True,
       frozen_native_cz_gate=800,frozen_native_depth_gate=2000,
       physical_one_wire_phase_mapping_is_unresolved=True,
       physical_feedback_latency_not_measured=True,
       qpu_jobs_submitted=0,IBM_free_or_paid_quantum_runtime_used=False,
       all_source_proofs={},pairs=[],status="STARTED",success=False)
    def save():out.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        old,verified=reference.original_structure_exact(base)
        receipt["original_archived_source_integrity"]=verified
        pruned={}
        for bits in BITS:
            reduced,proof=reduction_with_exact_instruction_identity(old[bits],bits)
            pruned[bits]=reduced
            receipt["all_source_proofs"][str(bits)]=proof
            save()
            print("TRUE RECYCLED SOURCE EXACT IDLE SCRATCH",base,"b",bits,
                  "32->23 SOURCE QUBITS, all nine scratch bits unused,",
                  "ALL instructions and classical conditions byte-level semantic identical",
                  "NO QPU",flush=True)
        receipt["status"]="SIX_ORIGINAL_SOURCE_INSTRUCTION_EQUIVALENCE_PASS"
        save()
        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
           plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Expected physical IBM Fez read-only >=32 qubit target")
        target_names={str(x) for x in backend.target.operation_names}
        assert {"if_else","measure","reset","cz","rz"}<=target_names
        receipt["backend_device_width"]=int(backend.num_qubits)
        receipt["backend_required_dynamic_instruction_names_present"]=True
        receipt["status"]="COMPILING_MATCHED_SOURCE_WIDTHS_CPU_ONLY"
        save()

        for bits in BITS:
            for seed in SEEDS:
                row=dict(bits=bits,seed=seed,status="STARTED",source_counts_exact=True)
                receipt["pairs"].append(row)
                save()
                try:
                    pm=generate_preset_pass_manager(backend=backend,
                        optimization_level=OPT,seed_transpiler=seed)
                    orig=one_compilation(pm,old[bits],bits,"original_32q")
                    lean=one_compilation(pm,pruned[bits],bits,"pruned_23q")
                    dz=lean["compiled_native_cz"]-orig["compiled_native_cz"]
                    dd=lean["compiled_native_depth"]-orig["compiled_native_depth"]
                    row.update(status="MATCHED_TWO_COMPILATIONS_AND_FEEDBACK_OPERATOR_PASS",
                      original_32q=orig,pruned_23q=lean,
                      delta_candidate_minus_original=dict(cz=dz,depth=dd),
                      both_cz_depth_strictly_better=bool(dz<0 and dd<0))
                    print("TRUE 32Q->23Q FEZ CPU",base,"b",bits,"seed",seed,
                        "original CZ/depth",orig["compiled_native_cz"],orig["compiled_native_depth"],
                        "pruned CZ/depth",lean["compiled_native_cz"],lean["compiled_native_depth"],
                        "delta",dz,dd,"source 32->23, no QPU",flush=True)
                except Exception as e:
                    row.update(status="COMPILATION_OR_NATIVE_PHASE_REJECTED",
                        error_type=type(e).__name__,error_message=str(e)[:1200],
                        traceback=traceback.format_exc()[-1600:])
                    print("TRUE 23Q SOURCE COMPILER FAIL",base,"b",bits,"seed",seed,
                         type(e).__name__,str(e)[:350],"NO QPU",flush=True)
                save()

        anchors={}
        per_precision={}
        for bits in BITS:
            rows=[p for p in receipt["pairs"] if p["bits"]==bits]
            complete=[p for p in rows if p["status"]=="MATCHED_TWO_COMPILATIONS_AND_FEEDBACK_OPERATOR_PASS"]
            anchor=next((p for p in rows if p["seed"]==8776),None)
            target=PREVIOUS_NATIVE[base][bits]
            anchor_valid=bool(anchor and anchor["status"]=="MATCHED_TWO_COMPILATIONS_AND_FEEDBACK_OPERATOR_PASS"
                and (anchor["original_32q"]["compiled_native_cz"],
                     anchor["original_32q"]["compiled_native_depth"])==target)
            anchors[str(bits)]=anchor_valid
            if len(complete)==len(SEEDS):
                dc=[p["delta_candidate_minus_original"]["cz"] for p in complete]
                dd=[p["delta_candidate_minus_original"]["depth"] for p in complete]
                wins=sum(p["both_cz_depth_strictly_better"] for p in complete)
                metrics=dict(native_compiles_both_success=4,
                    candidate_both_metrics_improve_seed_count=wins,
                    median_paired_cz_delta=statistics.median(dc),
                    median_paired_depth_delta=statistics.median(dd),
                    min_paired_cz_delta=min(dc),max_paired_cz_delta=max(dc),
                    min_paired_depth_delta=min(dd),max_paired_depth_delta=max(dd),
                    exact_old_seed8776_anchor_reproduced=anchor_valid,
                    robust_native_gate_pass=bool(anchor_valid and wins>=3 and
                        statistics.median(dc)<0 and statistics.median(dd)<0),
                    all_candidate_device_gates_failed=all(not p["pruned_23q"]["hardware_gate_pass"] for p in complete))
            else:
                metrics=dict(native_compiles_both_success=len(complete),
                   exact_old_seed8776_anchor_reproduced=anchor_valid,
                   robust_native_gate_pass=False,
                   incomplete_or_rejected_pairs=len(rows)-len(complete))
            per_precision[str(bits)]=metrics
        successful=len(receipt["pairs"])==len(BITS)*len(SEEDS) and all(
             p["status"]=="MATCHED_TWO_COMPILATIONS_AND_FEEDBACK_OPERATOR_PASS"
             for p in receipt["pairs"])
        summary=dict(
           original_and_pruned_source_equivalence_pass=True,
           source_quantum_qubit_reduction=9,
           original_source_width=32,new_source_width=23,
           native_pair_count=sum(p["status"]=="MATCHED_TWO_COMPILATIONS_AND_FEEDBACK_OPERATOR_PASS"
                                 for p in receipt["pairs"]),
           intended_matched_pair_count=12,
           all_24_cpu_native_compiles_succeeded=successful,
           native_if_else_branch_operator_proof_all_compiles=successful,
           all_original_8776_anchors_exact=all(anchors.values()),
           robust_native_improvement_every_precision=all(x.get("robust_native_gate_pass",False)
              for x in per_precision.values()),
           per_precision=per_precision,
           existing_phase_wire_physical_mapping_uncertainty_retained=True,
           no_device_execution_or_shot_claims=True)
        receipt.update(summary=summary,status=(
           "ALL_NATIVE_PAIRS_COMPLETE" if successful else "SOURCE_REDUCTION_PASS_PARTIAL_NATIVE_FAIL"),
           success=bool(successful))
        save()
        print("TRUE RECYCLED 23Q SOURCE FEZ CPU FINAL",base,
           json.dumps(summary,sort_keys=True),"NO QPU",flush=True)
        return 0 if successful else 1
    except Exception as e:
        receipt.update(status="SOURCE_OR_BACKEND_FAILURE",success=False,
            error_type=type(e).__name__,error_message=str(e)[:1800],
            traceback=traceback.format_exc()[-2800:],
            qpu_jobs_submitted=0,IBM_free_or_paid_quantum_runtime_used=False)
        save()
        print("TRUE IDLE SCRATCH SOURCE REJECTION",base,
            type(e).__name__,str(e)[:800],traceback.format_exc()[-1200:],
            "NO QPU",flush=True)
        return 1


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--base",type=int,choices=BASES,required=True)
    raise SystemExit(main(parser.parse_args().base))
