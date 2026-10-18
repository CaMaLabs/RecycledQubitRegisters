#!/usr/bin/env python3
"""Matched eight-seed N35 original vs negative-control OR-carry comparator.

Research lead Chase Lunsford / CaMaLabs. ONE source change to temporary
public threshold complement b=1 comparator carries:
 old x OR p = x XOR p XOR x&p -> CX(x); CX(p); RCCX(x,p)
 new x OR p = x XOR (~x&p)    -> CX(x); X(x); RCCX(x,p); X(x)
with the actual Qiskit RCCX inverse on clean uncomputation.

Qiskit source unitary Operator phases MUST prove exact +1 across exhaustive
comparators and all public full-residue controlled modular-multiply cases,
for BOTH old and new, BEFORE reading IBM Fez target metadata.
All native comparisons are 8 matched CPU compiler seeds, ZERO QPU.
"""
from __future__ import annotations
import argparse
import json
import os
import statistics
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from qiskit.circuit.library import RCCXGate
from qiskit.quantum_info import Operator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_relative_phase_ripple_carry as previous

primitive=previous.primitive
N=35
BASES=(2,8)
SEEDS=(11,37,101,409,8776,12011,20261,45673)
REV="qrr-n35-or-carry-negative-control-matched-seeds-v1-20261017"
OUT=Path("results/ibm_shor35_or_carry_polarity_seeds")
BASELINE={
    2:dict(cz=9263,depth=21772,source=dict(cx=1033,rccx=596,x=28,ccx=160)),
    8:dict(cz=9426,depth=21933,source=dict(cx=1077,rccx=616,x=28,ccx=162)),
}
EPS=1e-8


def negative_or_carry_predicate(qc,x,threshold,flag,carry,chain,controls=(),geq=True):
    """Original unsigned ripple Boolean recurrence, different b=1 gate polarity.

    Compute carries on clean registers; exact operator adjoint restores them.
    No relative-phase gate may directly change the semantic predicate flag.
    """
    x=list(x)
    carry=list(carry)
    controls=list(controls)
    n=len(x)
    if len(carry)!=n or not (1<=int(threshold)<(1<<n)):
        raise AssertionError("Invalid comparator register width/threshold")
    const=(1<<n)-int(threshold)
    rccx=RCCXGate()
    adj=rccx.inverse()
    if not np.allclose(
         np.asarray(Operator(adj).data) @ np.asarray(Operator(rccx).data),
         np.eye(8),atol=EPS):
        raise AssertionError("RCCX inverse operator is not exact adjoint")
    for i in range(n):
        b=(const>>i)&1
        if i==0:
            if b: qc.cx(x[i],carry[i])
        elif b==0:
            qc.append(rccx,[x[i],carry[i-1],carry[i]])
        else:
            # Compute x OR prior = x XOR ((NOT x) AND prior).
            # Input x restored immediately; one less CX than old recurrence.
            qc.cx(x[i],carry[i])
            qc.x(x[i])
            qc.append(rccx,[x[i],carry[i-1],carry[i]])
            qc.x(x[i])
    if not geq:
        qc.x(carry[-1])
    # Semantic output stays exact X/CX/CCX, never relative-phase.
    primitive.multi_x(qc,controls+[carry[-1]],flag,chain)
    if not geq:
        qc.x(carry[-1])
    for i in reversed(range(n)):
        b=(const>>i)&1
        if i==0:
            if b: qc.cx(x[i],carry[i])
        elif b==0:
            qc.append(adj,[x[i],carry[i-1],carry[i]])
        else:
            # Exactly reverse the entire forward b=1 operation: U-dagger.
            qc.x(x[i])
            qc.append(adj,[x[i],carry[i-1],carry[i]])
            qc.x(x[i])
            qc.cx(x[i],carry[i])


def verify_original_and_candidate_before_backend(base):
    """Full actual emitted-gate complex phase proof of both source variants."""
    original_cmp=previous.exhaustive_comparator_phase_proof()
    assert original_cmp["pass_all"] and original_cmp["actual_gate_comparator_cases"]==42672
    original_add=previous.exhaustive_modadd_phases(previous.source_constants())
    assert original_add["pass_all"] and original_add["source_gate_cases"]==1584
    orig_c,orig_regs=previous.verified.build(base)
    original_full=previous.exhaustive_full_multiplier_phases(orig_c,orig_regs,base)
    old_ops=original_full["quantum_source_gate_counts"]
    assert old_ops==BASELINE[base]["source"]
    assert orig_c.num_qubits==32 and original_full["all_25_auxiliaries_clean"]
    assert original_full["exact_complex_output_phase_plus_one"]

    # Modify only comparator construction at the exactly frozen boundary.
    # The original circuit object is already emitted; won't be affected.
    primitive.predicate=negative_or_carry_predicate
    previous.phase_aware_ripple_predicate=negative_or_carry_predicate
    candidate_cmp=previous.exhaustive_comparator_phase_proof()
    assert candidate_cmp["pass_all"] and candidate_cmp["actual_gate_comparator_cases"]==42672
    candidate_add=previous.exhaustive_modadd_phases(previous.source_constants())
    assert candidate_add["pass_all"] and candidate_add["source_gate_cases"]==1584
    candidate_c,candidate_regs=previous.verified.build(base)
    candidate_full=previous.exhaustive_full_multiplier_phases(candidate_c,candidate_regs,base)
    new_ops=candidate_full["quantum_source_gate_counts"]
    assert candidate_c.num_qubits==32 and candidate_full["all_25_auxiliaries_clean"]
    assert candidate_full["exact_complex_output_phase_plus_one"]
    assert candidate_full["full_residue_control_basis_cases"]==128
    assert new_ops.get('x',0)>old_ops.get('x',0),("negative OR intervention not exercised",old_ops,new_ops)
    assert new_ops.get('cx',0)<old_ops.get('cx',0),("no removed CX",old_ops,new_ops)
    assert new_ops.get('rccx',0)==old_ops.get('rccx',0),("RCCX changed",old_ops,new_ops)
    assert new_ops.get('ccx',0)==old_ops.get('ccx',0),("semantic CCX changed",old_ops,new_ops)
    assert candidate_cmp['comparator_total_source_gate_distribution'].get('x',0)>(
        original_cmp['comparator_total_source_gate_distribution'].get('x',0))
    assert candidate_cmp['comparator_total_source_gate_distribution'].get('cx',0)<(
        original_cmp['comparator_total_source_gate_distribution'].get('cx',0))
    print("ORIGINAL+CANDIDATE TRUE COMPLEX UNITARY EMITTED GATE PROOF base",base,
          "comparator 42672 EACH, modulo35 1584 EACH, full128 EACH,",
          "all25 CLEAN +1 PHASE, original source",old_ops,
          "candidate source",new_ops,flush=True)
    return orig_c,candidate_c,dict(pass_all=True,
        original_comparator=original_cmp,candidate_comparator=candidate_cmp,
        original_modadd=original_add,candidate_modadd=candidate_add,
        original_full=original_full,candidate_full=candidate_full,
        all_source_phase_plus_one=True,all_25_helpers_clean=True,
        original_source_counts=old_ops,candidate_source_counts=new_ops,
        source_qubits_original=32,source_qubits_candidate=32,
        negative_or_carry_intervention_confirmed=True)


def native_compile(pm,source):
    t0=time.perf_counter()
    circuit=pm.run(source)
    seconds=time.perf_counter()-t0
    ops={str(k):int(v) for k,v in circuit.count_ops().items()}
    cz=int(ops.get('cz',0))
    depth=int(circuit.depth())
    if cz<=0 or depth<=0 or circuit.num_qubits < source.num_qubits:
        raise AssertionError("Invalid native compiled circuit metrics")
    return dict(cz=cz,depth=depth,ops=ops,
        compiled_device_width=circuit.num_qubits,
        native_size=int(circuit.size()),elapsed_sec=seconds)


def summarize(pairs):
    assert len(pairs)==len(SEEDS)
    dz=[p['delta_candidate_minus_original']['cz'] for p in pairs]
    dd=[p['delta_candidate_minus_original']['depth'] for p in pairs]
    both=sum(z<0 and d<0 for z,d in zip(dz,dd))
    medz=statistics.median(dz)
    medd=statistics.median(dd)
    return dict(
        exact_seed_pairs=len(pairs),
        both_metrics_strictly_improved_seeds=both,
        cz_only_improved_seeds=sum(z<0 for z in dz),
        depth_only_improved_seeds=sum(d<0 for d in dd),
        median_paired_cz_delta=medz,median_paired_depth_delta=medd,
        min_paired_cz_delta=min(dz),max_paired_cz_delta=max(dz),
        min_paired_depth_delta=min(dd),max_paired_depth_delta=max(dd),
        at_least_six_of_eight_joint_better=both>=6,
        both_paired_medians_negative=medz<0 and medd<0,
        all_original_and_candidate_compiles_present=True)


def main(base):
    assert base in BASES
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/f"qrr_n35_or_carry_polarity_base{base}.json"
    row=dict(revision=REV,
       research_lead="Chase Lunsford / CaMaLabs",
       utc=datetime.now(timezone.utc).isoformat(),
       prereg="docs/QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_PREREG.md",
       public_modulus=35,base=base,
       experiment="one public N35 full-residue controlled multiplication; compare negated-OR-carry vs comparator-only baseline",
       seeds_frozen=list(SEEDS),optimization_level=1,target_backend="ibm_fez",
       historical_seed_8776_baseline=BASELINE[base],
       native_hardware_cz_limit=800,native_hardware_depth_limit=2000,
       modulus_factors_not_injected=True,true_order_not_injected=True,
       multiplicative_orbit_not_encoded=True,
       qpu_jobs_submitted=0,quantum_runtime_used=False,paid_runtime_used=False,
       matched_seed_pairs=[],status="STARTED",success=False)
    def save():target.write_text(json.dumps(row,indent=2,default=str)+"\n")
    save()
    try:
        original,candidate,proof=verify_original_and_candidate_before_backend(base)
        row["actual_emitted_quantum_phase_proof"]=proof
        row["status"]="SOURCE_UNITARY_GATES_PROVED"
        save()
        key=os.environ.get("IBM_QUANTUM_API_KEY","").strip()
        service=QiskitRuntimeService(
             channel="ibm_quantum_platform",plans_preference=["open"],
             **({"token":key} if key else {}))
        backend=service.backend("ibm_fez")
        if getattr(backend,"simulator",False) or backend.num_qubits<32:
            raise RuntimeError("Read-only physical Fez target unavailable")
        row["target_device_qubits"]=int(backend.num_qubits)
        row["status"]="NATIVE_CPU_COMPILING"
        save()
        for seed in SEEDS:
            pm=generate_preset_pass_manager(backend=backend,
                    optimization_level=1,seed_transpiler=seed)
            orig=native_compile(pm,original)
            new=native_compile(pm,candidate)
            dz=new['cz']-orig['cz']
            dd=new['depth']-orig['depth']
            p=dict(seed=seed,original=orig,candidate=new,
                   delta_candidate_minus_original=dict(cz=dz,depth=dd),
                   joint_strict_improvement=dz<0 and dd<0,
                   original_fits_device=orig['cz']<=800 and orig['depth']<=2000,
                   candidate_fits_device=new['cz']<=800 and new['depth']<=2000)
            row['matched_seed_pairs'].append(p)
            save()
            print("OR-CARRY MATCHED",base,seed,
                "ORIGINAL",orig['cz'],orig['depth'],
                "CANDIDATE",new['cz'],new['depth'],
                "DELTA",dz,dd,"JOINT",p['joint_strict_improvement'],
                "DEVICE",p['candidate_fits_device'],
                "NO QPU",flush=True)
        summary=summarize(row['matched_seed_pairs'])
        anchor=next(p for p in row['matched_seed_pairs'] if p['seed']==8776)
        hist=BASELINE[base]
        anchor_ok=anchor['original']['cz']==hist['cz'] and anchor['original']['depth']==hist['depth']
        summary['8776_original_seed_exact_reproduction']=anchor_ok
        summary['historical_anchor_drift']=not anchor_ok
        summary['robust_engineering_base_pass']=bool(
            anchor_ok and summary['at_least_six_of_eight_joint_better']
                      and summary['both_paired_medians_negative'])
        summary['every_candidate_fails_device_gate']=all(
            not p['candidate_fits_device'] for p in row['matched_seed_pairs'])
        summary['every_original_fails_device_gate']=all(
            not p['original_fits_device'] for p in row['matched_seed_pairs'])
        row.update(status="COMPILE_SUCCESS",success=True,
                   all_8_matched_native_pairs_complete=True,summary=summary,
                   qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print("OR-CARRY EIGHT-SEED SUMMARY",base,
              json.dumps(summary,sort_keys=True),"NO QPU",flush=True)
        return 0
    except Exception as exc:
        row.update(status="FAIL",success=False,
                   failure_type=type(exc).__name__,
                   failure_message=str(exc)[:1900],
                   failure_traceback=traceback.format_exc()[-3500:],
                   qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print("OR-CARRY SOURCE PHASE/COMPILER FAIL",base,
             type(exc).__name__,str(exc)[:1000],
             traceback.format_exc()[-1800:],
             "NO QPU",flush=True)
        return 1


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,required=True,choices=BASES)
    raise SystemExit(main(p.parse_args().base))
