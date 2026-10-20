#!/usr/bin/env python3
"""Pre-registered FOUR public N35 controlled powers + coherent QFT readout.

Research lead Chase Lunsford / CaMaLabs. Reuse exact prior sign-selected/
original 35-qubit clean arithmetic, prepend |work=1> and H^4, append 4-qubit
INVERSE QFT and 4 terminal measurements. Validate 1024+1024 complex-phase
source basis maps and analytic 16x16 QFT inverse before reading backend.
Eight matched seeds × two public bases × two circuits, read-only IBM Fez
hardware TARGET with CPU transpiler. ZERO QPU/IBM Runtime jobs or runtime.
NOT single-qubit phase recycling, NOT an executed Shor factoring experiment.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, ClassicalRegister
from qiskit.circuit.library import QFTGate
from qiskit.quantum_info import Operator,Statevector
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_static_sign_four_controlled_powers as prior

N=35
BASES=(2,8)
SEEDS=(239,647,1453,3701,6211,9421,16673,27191)
REV="qrr-n35-four-control-wide-phase-iqft-measure-v1-20261020"
ROOT=Path("results/ibm_shor35_four_phase_iqft_readout")


def verify_inverse_fourier():
    """Independent analytic QFT† matrix and four ideal Hadamard amplitudes."""
    gate=QFTGate(4)
    raw=np.asarray(Operator(gate).data,dtype=complex)
    inv=np.asarray(Operator(gate.inverse()).data,dtype=complex)
    k=np.arange(16,dtype=np.float64)
    phase=(k[:,None]*k[None,:])/16.0
    expected_inv=np.exp(-2j*np.pi*phase)/4.0
    expected_fwd=np.exp(+2j*np.pi*phase)/4.0
    if not np.allclose(raw,expected_fwd,rtol=0,atol=1e-9):
        raise AssertionError("QFTGate actual 4-qubit matrix differs from mathematical DFT")
    if not np.allclose(inv,expected_inv,rtol=0,atol=1e-9):
        raise AssertionError("QFTGate inverse does not match mathematical DFT† in Qiskit basis order")
    if not np.allclose(inv@raw,np.eye(16),rtol=0,atol=1e-9):
        raise AssertionError("QFT and inverse not exact unitaries")
    prep=QuantumCircuit(4)
    for bit in range(4):prep.h(bit)
    amplitudes=np.asarray(Statevector.from_instruction(prep).data,dtype=complex)
    if not np.allclose(amplitudes,np.ones(16,dtype=complex)/4,rtol=0,atol=1e-9):
        raise AssertionError("Prepared four control Hadamards not uniform positive amplitude")
    return dict(pass_all=True,phase_qubits=4,
                actual_QFT_and_inverse_exact_DFT_matrices=True,
                actual_inverse_times_QFT_identity=True,
                analytic_QFT_inverse_matrix_16x16_checked=True,
                H4_uniform_positive_16_amplitudes=True,
                numeric_tolerance=1e-9)


def readout_circuit(power,regs,base,variant):
    """Literal coherent |1>, H^4, previous controlled powers, inverse QFT, 4 measures."""
    assert power.num_qubits==35 and power.num_clbits==0
    measured=ClassicalRegister(4,"phase_out")
    q=QuantumCircuit(*(list(power.qregs)+[measured]),
        name=f"N35_fourwide_iqft_{variant}_base{base}")
    assert len(regs["phase"])==4 and len(regs["work"])==6
    q.x(regs["work"][0])
    for phase in regs["phase"]:q.h(phase)
    q.compose(power,qubits=power.qubits,inplace=True)
    q.append(QFTGate(4).inverse(),regs["phase"])
    for i,bit in enumerate(regs["phase"]):
        q.measure(bit,measured[i])
    items=list(q.data)
    assert len(items)>=6
    assert [z.operation.name for z in items[:5]]==["x","h","h","h","h"]
    # Gate display names vary by Qiskit version: verify the actual unitary.
    assert np.allclose(np.asarray(Operator(items[-5].operation).data),
                       np.asarray(Operator(QFTGate(4).inverse()).data),
                       rtol=0,atol=1e-9)
    assert all(z.operation.name=="measure" for z in items[-4:])
    assert q.num_qubits==35 and q.num_clbits==4
    assert sum(z.operation.name=="measure" for z in items)==4
    assert sum(z.operation.name=="h" for z in items)==4
    assert len([z for z in items if z.operation.name in ("reset","if_else")])==0
    return q,dict(pass_all=True,
         source_qubits=35,source_classical_bits=4,
         exactly_four_terminal_measurements=True,
         four_H_initial_phase_preparations=True,initial_work_basis_one=True,
         public_multiplier_schedule=prior.public_schedule(base),
         older_power_block_unmodified=True,
         neither_recycled_phase_nor_semiclassical_feedback=True)


def compile_cpu(pm,qc):
    start=time.perf_counter()
    native=pm.run(qc)
    ops={str(k):int(v) for k,v in native.count_ops().items()}
    depth=int(native.depth());cz=int(ops.get("cz",0))
    if not (cz>0 and depth>0):
        raise AssertionError("Native Fez CPU compilation returned invalid metrics")
    if native.num_qubits<35 or native.num_clbits!=4 or ops.get("measure",0)!=4:
        raise AssertionError(f"Native wide readout missing 4 measured bits {native.num_clbits} {ops}")
    return dict(native_cz=cz,native_depth=depth,
        native_ops=ops,compiled_device_width=int(native.num_qubits),
        compiled_classical_bits=int(native.num_clbits),
        native_total_ops=int(native.size()),
        compiler_seconds=time.perf_counter()-start,
        exactly_four_native_terminal_measurements=True)


def summary(pairs):
    assert len(pairs)==8 and [p["seed"] for p in pairs]==list(SEEDS)
    dz=[p["paired_delta"]["cz"] for p in pairs]
    dd=[p["paired_delta"]["depth"] for p in pairs]
    joint=sum(z<0 and d<0 for z,d in zip(dz,dd))
    return dict(pairs=8,paired_joint_both_resource_wins=joint,
        paired_CZ_wins=sum(x<0 for x in dz),
        paired_depth_wins=sum(x<0 for x in dd),
        median_paired_CZ_delta=statistics.median(dz),
        median_paired_depth_delta=statistics.median(dd),
        delta_CZ_range=[min(dz),max(dz)],
        delta_depth_range=[min(dd),max(dd)],
        robustness_both_cz_and_depth_gate_pass=bool(
            joint>=6 and statistics.median(dz)<0 and statistics.median(dd)<0),
        all_eight_source_old_and_new_readout_compilations_present=True,
        all_qpu_preflights_fail=all(
             not p["original_device_feasible"] and not p["selected_device_feasible"]
             for p in pairs))


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f"qrr_n35_four_phase_iqft_base{base}.json"
    past=Path("results/ibm_shor35_four_power_sign_selector")/f"qrr_n35_four_power_sign_source_base{base}.json"
    prev=json.loads(past.read_text())
    assert prev["success"] and prev["status"]=="COMPILE_SUCCESS"
    assert prev["eight_NEW_seeds"]==list(SEEDS)
    assert prev["public_base"]==base
    receipt=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
       created_utc=datetime.now(timezone.utc).isoformat(),
       preregistered_document="docs/QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_PREREG.md",
       public_N=N,public_base=base,
       original_public_powers=prior.public_schedule(base),
       seeds=list(SEEDS),optimization_level=1,
       source_logical_qubits=35,source_classical_bits=4,
       no_midcircuit_recycling_or_feedback=True,
       original_frozen_four_power_block_receipt=str(past),
       source_original_four_power_native_seed_metrics=prev["eight_seed_native_pairs"],
       experiment_kind="four coherent phase H preps, controlled modular powers, four-QFT-inverse and four classical readouts CPU target only",
       backend_target="ibm_fez",frozen_native_CZ_cutoff=800,
       frozen_native_depth_cutoff=2000,
       true_order_not_injected=True,private_factors_not_used=True,orbit_not_injected=True,
       no_measurement_outcomes_sampled=True,number_of_factor_recoveries_measured=0,
       zero_QPU=True,qpu_jobs_submitted=0,free_runtime_used=False,paid_runtime_used=False,
       source_all_phase_prechecks_completed=False,
       native_seed_pairs=[],status="STARTED",success=False)
    def save():path.write_text(json.dumps(receipt,indent=2,default=str)+"\n")
    save()
    try:
        receipt["analytic_inverse_QFT_prebackend"]=verify_inverse_fourier()
        save()
        archived=prior.archived_original(base)
        mapping,single,source=prior.phase_source_preflight(base,archived)
        old,r_old,rounds_old=prior.build_four_controlled_powers(base,"original",mapping)
        new,r_new,rounds_new=prior.build_four_controlled_powers(base,"selected",mapping)
        old_proof=prior.exhaustive_four_controlled_power_phase(old,r_old,base)
        new_proof=prior.exhaustive_four_controlled_power_phase(new,r_new,base)
        frozen=prev["four_power_source_phase_proofs"]
        assert old_proof["source_gate_histogram"]==frozen["original"]["source_gate_histogram"]
        assert new_proof["source_gate_histogram"]==frozen["selected"]["source_gate_histogram"]
        assert old_proof["pass_all"] and new_proof["pass_all"]
        assert old_proof["exact_source_operator_basis_cases"]==new_proof["exact_source_operator_basis_cases"]==1024
        assert old_proof["all_25_helpers_clean"] and new_proof["all_25_helpers_clean"]
        assert old_proof["exact_complex_phase_plus_one"] and new_proof["exact_complex_phase_plus_one"]
        assert rounds_old==frozen["source_rounds_original"]
        assert rounds_new==frozen["source_rounds_selected"]
        assert [z["public_multiplier"] for z in rounds_old[:4]]==prior.public_schedule(base)
        qc_old,structure_old=readout_circuit(old,r_old,base,"original")
        qc_new,structure_new=readout_circuit(new,r_new,base,"selected")
        receipt["prebackend_phase_proofs"]=dict(
             old_source=old_proof,selected_source=new_proof,
             public_source_safety=source,
             source_histograms_exactly_frozen=True,
             four_power_schedule_exactly_frozen=True)
        receipt["prebackend_readout_structure"]=dict(original=structure_old,selected=structure_new)
        receipt["source_all_phase_prechecks_completed"]=True
        receipt["status"]="ALL_SOURCE_QUANTUM_AND_QFT_PRECHECKS_PASS"
        save()
        print("N35 FOUR-WIDE READOUT SOURCE PASSED",base,
             "old 1024 + new 1024 phase amplitude +1 all 25 helpers clean;",
             "analytic IQFT 16x16 PASS; terminal measure4; 35 qubits and classical4",
             flush=True)

        token=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(channel="ibm_quantum_platform",
           plans_preference=["open"],**({"token":token} if token else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<35:
            raise RuntimeError("Target is simulator or too narrow")
        receipt["backend_device_qubits"]=int(backend.num_qubits)
        receipt["status"]="NATIVE_CPU_COMPILING_MATCHED_SEEDS"
        save()
        for seed,archived_pair in zip(SEEDS,prev["eight_seed_native_pairs"]):
            assert archived_pair["seed"]==seed
            pm=generate_preset_pass_manager(backend=backend,
                optimization_level=1,seed_transpiler=seed)
            o=compile_cpu(pm,qc_old)
            n=compile_cpu(pm,qc_new)
            delta=dict(cz=n["native_cz"]-o["native_cz"],
                      depth=n["native_depth"]-o["native_depth"])
            historical=dict(
              original_archived_CZ=archived_pair["original"]["native_cz"],
              original_archived_depth=archived_pair["original"]["native_depth"],
              selected_archived_CZ=archived_pair["selected"]["native_cz"],
              selected_archived_depth=archived_pair["selected"]["native_depth"])
            row=dict(seed=seed,original=o,selected=n,paired_delta=delta,
               archived_no_QFT_same_seed_descriptive_only=historical,
               full_minus_historical_noQFT_delta_descriptive_only=dict(
                 original_CZ=o["native_cz"]-historical["original_archived_CZ"],
                 original_depth=o["native_depth"]-historical["original_archived_depth"],
                 selected_CZ=n["native_cz"]-historical["selected_archived_CZ"],
                 selected_depth=n["native_depth"]-historical["selected_archived_depth"]),
               jointly_CZ_and_depth_lower=(delta["cz"]<0 and delta["depth"]<0),
               original_device_feasible=(o["native_cz"]<=800 and o["native_depth"]<=2000),
               selected_device_feasible=(n["native_cz"]<=800 and n["native_depth"]<=2000))
            receipt["native_seed_pairs"].append(row)
            save()
            print("FOUR-WIDE READOUT N35 CPU SEED",base,seed,
                "original",o["native_cz"],o["native_depth"],
                "selected",n["native_cz"],n["native_depth"],
                "paired",delta,"joint",row["jointly_CZ_and_depth_lower"],
                "READOUT4 NO QPU",flush=True)

        result=summary(receipt["native_seed_pairs"])
        receipt.update(status="COMPILE_SUCCESS",success=True,
           summary=result,no_QPU_jobs_generated=True)
        save()
        print("N35 FOUR-WIDE IQFT READOUT SUMMARY",base,json.dumps(result,sort_keys=True),
            "native read-only CPU, no factor shots, ZERO QPU",flush=True)
        return 0
    except Exception as exc:
        receipt.update(status="FAIL",success=False,
           failure_type=type(exc).__name__,failure_message=str(exc)[:1500],
           failure_trace=traceback.format_exc()[-2000:],
           zero_QPU=True,qpu_jobs_submitted=0)
        save()
        print("FOUR-WIDE READOUT FAILURE",base,type(exc).__name__,
             str(exc)[:800],traceback.format_exc()[-1400:],"NO QPU",flush=True)
        return 1


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(p.parse_args().base))
