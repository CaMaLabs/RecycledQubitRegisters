#!/usr/bin/env python3
"""One fixed phase-exact Boolean OR-carry lowering in N35 public multiplier.

Original shortened-ripple comparator: c_i = x_i OR c_(i-1) compiled as
CX(x,cur), CX(prev,cur), RCCX(x,prev,cur).
Candidate: c_i = prev XOR (x AND NOT prev), compiled as
CX(prev,cur), X(prev), RCCX(x,prev,cur), X(prev).
Reverse temporary carry compute by the exact inverse operator in reverse order.
No semantic target or public modular arithmetic change. Direct ACTUAL emitted
complex-amplitude gate proof BEFORE any Fez backend target read.

Lead Chase Lunsford / CaMaLabs. Eight frozen matched seed comparisons per
public base2/cube8. No QPU job, no quantum Runtime paid/free consumption.
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

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import RCCXGate
from qiskit.quantum_info import Operator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_relative_phase_ripple_carry as previous

primitive=previous.primitive
N=35
BITS=6
BASES=(2,8)
SEEDS=(11,37,101,409,8776,12011,20261,45673)
REV="qrr-n35-or-carry-minimization-matched-seeds-v1-20261017"
ROOT=Path("results/ibm_shor35_or_carry_multi_seed")
EPS=1e-8

HISTORICAL={
    2:dict(cz=9263,depth=21772,
           source=dict(cx=1033,rccx=596,x=28,ccx=160)),
    8:dict(cz=9426,depth=21933,
           source=dict(cx=1077,rccx=616,x=28,ccx=162)),
}


def verify_public_boolean_or_identity():
    """Independent all-four-input Boolean test, NOT substitute for phase proof."""
    cases=0
    for x in (0,1):
        for p in (0,1):
            if (x | p)!=(p ^ (x & (1 ^ p))):
                raise AssertionError(f"Bad Boolean OR substitution x={x} p={p}")
            cases+=1
    if cases!=4:raise AssertionError("OR identity not exhaustively checked")
    op=np.asarray(Operator(RCCXGate()).data,dtype=complex)
    inv=np.asarray(Operator(RCCXGate().inverse()).data,dtype=complex)
    if not np.allclose(inv@op,np.eye(8),atol=EPS):
        raise AssertionError("RCCX inverse matrix isn't the actual adjoint")
    return dict(pass_all=True,independent_boolean_cases=4,
                exact_rccx_inverse_operator_identity=True,
                inverse_gate_name=RCCXGate().inverse().name)


def minimized_or_ripple_predicate(qc,x,threshold,flag,carry,chain,
                                  controls=(),geq=True):
    """Original carry recurrence U/flag/U-dagger; ONE CX per public OR step.

    b_i==1 uses p XOR (x AND NOT p) rather than x XOR p XOR (x AND p).
    All temporary x(prev) controls restored prior to next gate. Source
    xbits, carry recurrence, geq polarity, semantic final flag toggle,
    and exact reversible operation remain identical on clean carry input.
    Quantum-phase equivalence is validated on ACTUAL emitted instructions.
    """
    x=list(x)
    carry=list(carry)
    controls=list(controls)
    n=len(x)
    if len(carry)!=n or not (1<=threshold<(1<<n)):
        raise AssertionError("Bad threshold/width on public OR comparator")
    public_const=(1<<n)-threshold
    rccx=RCCXGate()
    inverse=rccx.inverse()

    # Compute temporary rippled carries, one clean workspace bit per source bit.
    for i in range(n):
        b=(public_const>>i)&1
        if i==0:
            if b:
                qc.cx(x[i],carry[i])
        elif b==0:
            qc.append(rccx,[x[i],carry[i-1],carry[i]])
        else:
            # p OR x = p XOR (x & NOT p), old 2-CX -> new 1-CX + 2 X.
            qc.cx(carry[i-1],carry[i])
            qc.x(carry[i-1])
            qc.append(rccx,[x[i],carry[i-1],carry[i]])
            qc.x(carry[i-1])

    # Semantic target flip stays EXACT old primitive implementation.
    if not geq:
        qc.x(carry[-1])
    primitive.multi_x(qc,controls+[carry[-1]],flag,chain)
    if not geq:
        qc.x(carry[-1])

    # Apply exact U-dagger, not an RCCX approximated as ordinary Toffoli.
    for i in reversed(range(n)):
        b=(public_const>>i)&1
        if i==0:
            if b:
                qc.cx(x[i],carry[i])
        elif b==0:
            qc.append(inverse,[x[i],carry[i-1],carry[i]])
        else:
            qc.x(carry[i-1])
            qc.append(inverse,[x[i],carry[i-1],carry[i]])
            qc.x(carry[i-1])
            qc.cx(carry[i-1],carry[i])


def exhaustive_new_comparator_phase_proof():
    """All 42,672 actual emitted gate complex-phase cases, all bit widths<=6."""
    circuits=0
    cases=0
    source_ops={}
    for width in range(1,BITS+1):
        for threshold in range(1,1<<width):
            for geq in (True,False):
                control=QuantumRegister(1,'control')
                x=QuantumRegister(width,'x')
                flag=QuantumRegister(1,'flag')
                carry=QuantumRegister(width,'carry')
                scratch=QuantumRegister(BITS+3,'scratch')
                qc=QuantumCircuit(control,x,flag,carry,scratch)
                minimized_or_ripple_predicate(
                    qc,x,threshold,flag[0],carry,scratch,
                    controls=[control[0]],geq=geq)
                idx,inst,gate_counts=previous.actual_complex_instructions(qc)
                for name,amount in gate_counts.items():
                    source_ops[name]=source_ops.get(name,0)+amount
                epos=idx[control[0]]
                fpos=idx[flag[0]]
                xpositions=[idx[q] for q in x]
                clean=[idx[q] for register in (carry,scratch) for q in register]
                circuits+=1
                for input_x in range(1<<width):
                    for enabled in (0,1):
                        for original_flag in (0,1):
                            initial=(enabled<<epos)|(original_flag<<fpos)
                            for b,pos in enumerate(xpositions):
                                initial|=((input_x>>b)&1)<<pos
                            final,phase=previous.evolve_basis(inst,initial)
                            value=sum(((final>>pos)&1)<<b
                                      for b,pos in enumerate(xpositions))
                            wanted=original_flag^int(bool(enabled) and (
                                input_x>=threshold if geq else input_x<threshold))
                            if ((final>>fpos)&1)!=wanted or value!=input_x or ((final>>epos)&1)!=enabled:
                                raise AssertionError(json.dumps(dict(
                                    stage='comparator',width=width,t=threshold,
                                    geq=geq,enabled=enabled,input_x=input_x,
                                    original_flag=original_flag,
                                    actual_flag=(final>>fpos)&1,wanted=wanted,
                                    actual_x=value)))
                            if any((final>>pos)&1 for pos in clean):
                                raise AssertionError(
                                   f"Comparator workspace dirty width={width} threshold={threshold} x={input_x}")
                            previous.check_exact_phase(phase,
                               f"OR comparator w={width} t={threshold} x={input_x} en={enabled} flag={original_flag}")
                            cases+=1
    if circuits!=240 or cases!=42672:
        raise AssertionError(f"Comparator gate proof coverage {circuits},{cases}")
    if not source_ops.get('rccx',0):
        raise AssertionError("The phase-aware comparator did not emit RCCX")
    return dict(pass_all=True,actual_emitted_gate_cases=cases,
                unique_signed_comparator_circuits=circuits,
                zero_workspace_after_every_case=True,
                correct_x_control_and_flag=True,
                final_complex_phase_plus_one_every_case=True,
                source_gate_distribution=source_ops)


def prove_both_sources_before_target(base):
    independent=verify_public_boolean_or_identity()

    # Import previous installs the immutable phase-aware original comparator.
    # Build and phase-check the exact original baseline before patching source.
    previous.primitive.predicate=previous.phase_aware_ripple_predicate
    old_circuit,old_regs=previous.verified.build(base)
    old_proof=previous.exhaustive_full_multiplier_phases(
        old_circuit,old_regs,base)
    if old_proof['quantum_source_gate_counts']!=HISTORICAL[base]['source']:
        raise AssertionError("Frozen original quantum source baseline drift")

    # This single monkeypatch is the ONLY actual changed arithmetic component.
    # best.optimized_modadd and verified.build resolve primitive.predicate
    # dynamically at Qiskit source-circuit construction.
    primitive.predicate=minimized_or_ripple_predicate

    comparator=exhaustive_new_comparator_phase_proof()
    modadd=previous.exhaustive_modadd_phases(previous.source_constants())
    assert modadd['pass_all'] and modadd['source_gate_cases']==1584
    assert modadd['exact_complex_phase_plus_one'] and modadd['clean_helpers']
    new_circuit,new_regs=previous.verified.build(base)
    candidate_proof=previous.exhaustive_full_multiplier_phases(
        new_circuit,new_regs,base)

    for name,qc,proof in (('original',old_circuit,old_proof),
                          ('or_minimized',new_circuit,candidate_proof)):
        assert qc.num_qubits==32
        assert proof['pass_all'] and proof['full_residue_control_basis_cases']==128
        assert proof['all_25_auxiliaries_clean'] and proof['control_unmodified']
        assert proof['exact_complex_output_phase_plus_one']
        assert proof['disabled_invalid_states_identity']
        print("ACTUAL COMPLEX SOURCE MULTIPLIER PROOF",name,"base",base,
              "128/128 exact phase +1, 25 helper qubits CLEAN",
              "source gates",proof['quantum_source_gate_counts'],flush=True)

    o=old_proof['quantum_source_gate_counts']
    n=candidate_proof['quantum_source_gate_counts']
    if n['rccx']!=o['rccx'] or n['ccx']!=o['ccx']:
        raise AssertionError(f"Candidate changed non-OR RCCX/semantic CCX counts old={o},new={n}")
    if not (n['cx']<o['cx'] and n['x']>o['x']):
        raise AssertionError(f"OR intervention not exercised old={o},new={n}")
    changed_or_steps=(o['cx']-n['cx'])//2
    if (o['cx']-n['cx'])!=2*changed_or_steps or (
          n['x']-o['x'])!=4*changed_or_steps:
        raise AssertionError(json.dumps(dict(
            intervention_wrong_gate_delta=True,old=o,new=n,or_steps=changed_or_steps)))
    if changed_or_steps<=0:
        raise AssertionError("No comparator OR steps actually modified")

    print("PUBLIC N35 OR-CARRY SOURCE GATE PROOFS PASSED",base,
          "BOOLEAN",independent['independent_boolean_cases'],
          "COMPARATOR",comparator['actual_emitted_gate_cases'],
          "MODADD",modadd['source_gate_cases'],
          "FULL OLD",old_proof['full_residue_control_basis_cases'],
          "FULL NEW",candidate_proof['full_residue_control_basis_cases'],
          "OR STEPS CHANGED",changed_or_steps,
          "CX SAVED",o['cx']-n['cx'],
          "X ADDED",n['x']-o['x'],
          "EXACT QUANTUM PHASE +1, ZERO QPU",flush=True)

    return old_circuit,new_circuit,dict(pass_all=True,
        boolean_or_identity=independent,
        minimized_comparator=comparator,
        new_public_modadd=modadd,
        original_full_multiplier=old_proof,
        candidate_full_multiplier=candidate_proof,
        both_source_32_qubits=True,
        all_25_auxiliaries_clean=True,
        all_actual_gate_phases_plus_one=True,
        or_carry_recurrence_steps_rewritten=changed_or_steps,
        source_gate_cx_saved=o['cx']-n['cx'],
        source_gate_x_added=n['x']-o['x'],
        semantic_rccx_and_ccx_unchanged=True)


def compile_only_native_cpu(pm,circuit):
    start=time.perf_counter()
    native=pm.run(circuit)
    elapsed=time.perf_counter()-start
    ops={str(k):int(v) for k,v in native.count_ops().items()}
    cz=int(ops.get('cz',0))
    depth=int(native.depth())
    if cz<=0 or depth<=0 or native.num_qubits<circuit.num_qubits:
        raise AssertionError("Invalid native Qiskit target compiler costs")
    return dict(cz=cz,depth=depth,
        native_count_ops=ops,compiled_isa_width=int(native.num_qubits),
        native_size=int(native.size()),compiler_seconds=elapsed)


def summarize(pairs,base):
    if len(pairs)!=len(SEEDS):
        raise AssertionError(f"Incomplete original seed pairs count={len(pairs)}")
    czdelta=[p['paired_delta_candidate_minus_original']['cz'] for p in pairs]
    depthdelta=[p['paired_delta_candidate_minus_original']['depth'] for p in pairs]
    wins=sum(c<0 and d<0 for c,d in zip(czdelta,depthdelta))
    cx=sum(z<0 for z in czdelta)
    dx=sum(d<0 for d in depthdelta)
    median_cz=statistics.median(czdelta)
    median_depth=statistics.median(depthdelta)
    frozen=HISTORICAL[base]
    anchor=next(p for p in pairs if p['seed']==8776)
    old_reproduced=(anchor['original']['cz']==frozen['cz'] and
                    anchor['original']['depth']==frozen['depth'])
    gate_pass=bool(old_reproduced and wins>=6 and
                   median_cz<0 and median_depth<0)
    return dict(complete_eight_pairs=True,
        exact_8776_original_baseline_reproduced=old_reproduced,
        anchor_drift_makes_historical_robustness_inconclusive=not old_reproduced,
        both_cz_and_depth_improve_count=wins,
        cz_strict_improvement_count=cx,
        depth_strict_improvement_count=dx,
        paired_cz_delta_median=median_cz,
        paired_depth_delta_median=median_depth,
        paired_cz_delta_min=min(czdelta),paired_cz_delta_max=max(czdelta),
        paired_depth_delta_min=min(depthdelta),
        paired_depth_delta_max=max(depthdelta),
        frozen_robust_threshold_six_of_eight=True,
        robust_engineering_this_base_pass=gate_pass,
        all_original_eight_layouts_fail_device_gate=all(
            not p['device_feasible_original'] for p in pairs),
        all_candidate_eight_layouts_fail_device_gate=all(
            not p['device_feasible_candidate'] for p in pairs),
        no_postselected_seeds=True)


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f"qrr_n35_or_carry_multiseed_base{base}.json"
    r=dict(revision=REV,research_lead='Chase Lunsford / CaMaLabs',
       utc=datetime.now(timezone.utc).isoformat(),
       preregistration='docs/QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_PREREG.md',
       experiment='N35 one controlled full-residue public multiplier, comparator public OR carry only',
       N=N,base=base,seed_list=list(SEEDS),
       original_historical_seed_8776=HISTORICAL[base],
       candidate_source_intervention='c[i]=p OR x as p XOR (x AND NOT p) for const b_i=1; RCCX exact adjoint',
       compiler_optimization_level=1,read_only_ibm_target='ibm_fez',
       device_native_cz_cutoff=800,device_native_depth_cutoff=2000,
       true_factorization_order_not_used=True,
       hidden_factors_not_used=True,
       precomputed_orbit_not_used=True,
       real_qpu_jobs=0,used_paid_runtime=False,used_free_qpu_runtime=False,
       paired_seed_metrics=[],status='STARTED',success=False)
    def save():path.write_text(json.dumps(r,indent=2,default=str)+'\n')
    save()
    try:
        original,candidate,proof=prove_both_sources_before_target(base)
        r['exact_source_phase_proofs']=proof
        r['status']='ALL_EMITTED_COMPLEX_PHASE_PROOFS_PASS'
        save()

        # Metadata only. Never create or run Sampler/Estimator or backend job.
        token=os.environ.get('IBM_QUANTUM_API_KEY','').strip()
        service=QiskitRuntimeService(
           channel='ibm_quantum_platform',plans_preference=['open'],
           **({'token':token} if token else {}))
        backend=service.backend('ibm_fez')
        if getattr(backend,'simulator',False) or backend.num_qubits<32:
            raise RuntimeError('Fez target missing physical ISA or inadequate qubits')
        r['backend_qubits']=backend.num_qubits
        r['status']='CPU_ONLY_MATCHED_NATIVE_COMPILATION'
        save()

        for seed in SEEDS:
            pm=generate_preset_pass_manager(
                backend=backend,optimization_level=1,seed_transpiler=seed)
            old=compile_only_native_cpu(pm,original)
            new=compile_only_native_cpu(pm,candidate)
            dc=new['cz']-old['cz']
            dd=new['depth']-old['depth']
            row=dict(seed=seed,original=old,candidate=new,
              paired_delta_candidate_minus_original=dict(cz=dc,depth=dd),
              strictly_better_both=(dc<0 and dd<0),
              device_feasible_original=(old['cz']<=800 and old['depth']<=2000),
              device_feasible_candidate=(new['cz']<=800 and new['depth']<=2000))
            r['paired_seed_metrics'].append(row)
            save()
            print('N35 PUBLIC OR-CARRY MATCHED NATIVE CPU',base,seed,
                  'OLD',old['cz'],old['depth'],
                  'NEW',new['cz'],new['depth'],
                  'DELTA',dc,dd,'BOTH',row['strictly_better_both'],
                  'DEVICE',row['device_feasible_candidate'],'NO QPU',flush=True)

        r['summary']=summarize(r['paired_seed_metrics'],base)
        r.update(status='COMPILE_SUCCESS',success=True,
          all_original_and_candidate_seed_runs_complete=True,
          no_real_quantum_runtime=True)
        save()
        print('N35 OR-CARRY FULL EIGHT-SEED RESULT',base,
              json.dumps(r['summary'],sort_keys=True),'NO QPU',flush=True)
        return 0
    except Exception as e:
        r.update(status='FAIL',success=False,
          failure_type=type(e).__name__,failure_message=str(e)[:1800],
          failure_traceback=traceback.format_exc()[-3000:],
          real_qpu_jobs=0,used_paid_runtime=False,
          used_free_qpu_runtime=False)
        save()
        print('N35 OR-CARRY EXPERIMENT FAILURE',base,type(e).__name__,
              str(e)[:800],traceback.format_exc()[-1300:],
              'NO QPU',flush=True)
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=int,choices=BASES,required=True)
    raise SystemExit(main(parser.parse_args().base))
