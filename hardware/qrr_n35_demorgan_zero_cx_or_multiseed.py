#!/usr/bin/env python3
"""One fixed De Morgan ZERO-CNOT temporary public OR carry lowering.

Research lead Chase Lunsford / CaMaLabs. Phase-aware N35 comparator exact
RCCX/inverse, unchanged controlled arithmetic, both original/oneCX controls.
Before any authenticated ibm_fez CPU target read, validate 4 Boolean
identity, 42672 comparator +1584 modadd +3*128 whole complex+1 phase gate
cases, zero 25 scratch per whole, original source counts and positive
literals. Eight fixed paired native compiler seeds per base, 48 CPU compiles.
ZERO QPU jobs, quantum Runtime usage, free/paid device execution.
"""
from __future__ import annotations
import argparse,json,os,statistics,time,traceback
from datetime import datetime,timezone
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit,QuantumRegister
from qiskit.circuit.library import RCCXGate
from qiskit.quantum_info import Operator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_relative_phase_ripple_carry as previous
import qrr_n35_or_carry_multi_seed as orbase

primitive=previous.primitive
N=35
BITS=6
BASES=(2,8)
SEEDS=(11,37,101,409,8776,12011,20261,45673)
REV="qrr-n35-demorgan-zero-cx-or-eight-matched-seeds-v1-20261018"
ROOT=Path("results/ibm_shor35_demorgan_zero_cx_or")
EPS=1e-8
HISTORICAL={
  2:dict(original=dict(cz=9263,depth=21772,
          source=dict(cx=1033,rccx=596,x=28,ccx=160)),
         one_cx_or=dict(cz=8311,depth=19981,
          source=dict(cx=691,rccx=596,x=712,ccx=160)),
         or_steps=171),
  8:dict(original=dict(cz=9426,depth=21933,
          source=dict(cx=1077,rccx=616,x=28,ccx=162)),
         one_cx_or=dict(cz=9141,depth=21528,
          source=dict(cx=717,rccx=616,x=748,ccx=162)),
         or_steps=180)
}


def boolean_and_inverse_operator_proof():
    cases=0
    for x in (0,1):
        for p in (0,1):
            wanted=x|p
            actual=1 ^ ((1^x)&(1^p))
            if wanted!=actual:
                raise AssertionError(f"De Morgan public OR identity failed x={x} p={p}")
            cases+=1
    assert cases==4
    op=np.asarray(Operator(RCCXGate()).data,dtype=complex)
    opi=np.asarray(Operator(RCCXGate().inverse()).data,dtype=complex)
    if not np.allclose(opi @ op,np.eye(8),atol=EPS):
        raise AssertionError("Actual Qiskit RCCX inverse NOT exact inverse")
    return dict(pass_all=True,public_boolean_or_cases=4,
                actual_rccx_inverse_operator_product_identity=True,
                inverse_gate_name=RCCXGate().inverse().name)


def demorgan_ripple_predicate(qc,x,threshold,flag,carry,chain,
                               controls=(),geq=True):
    """Same original ripple carry semantics; XOR U-Dagger with zero-CX OR steps.

    For clean c: x OR p = 1 XOR (NOT x & NOT p).
    All NOT control inversions restored before next ripple step. Temporary
    RCCX gates must be canceled by their exact inverse in full comparator,
    proved via actual complex Qiskit operator instruction interpreter.
    """
    x=list(x);carry=list(carry);controls=list(controls)
    n=len(x)
    if len(carry)!=n or not (1<=threshold<(1<<n)):
        raise AssertionError("Invalid public compare threshold/width")
    const=(1<<n)-threshold
    compute=RCCXGate()
    uncompute=compute.inverse()
    for i in range(n):
        bit=(const>>i)&1
        if i==0:
            if bit:qc.cx(x[i],carry[i])
        elif bit==0:
            qc.append(compute,[x[i],carry[i-1],carry[i]])
        else:
            # EXACT zero-CX De Morgan OR compute, with clean carry[i].
            qc.x(carry[i])
            qc.x(x[i]);qc.x(carry[i-1])
            qc.append(compute,[x[i],carry[i-1],carry[i]])
            qc.x(carry[i-1]);qc.x(x[i])
    if not geq: qc.x(carry[-1])
    # Identical true semantic X/CX/CCX controlled flag flip.
    primitive.multi_x(qc,controls+[carry[-1]],flag,chain)
    if not geq: qc.x(carry[-1])
    for i in reversed(range(n)):
        bit=(const>>i)&1
        if i==0:
            if bit:qc.cx(x[i],carry[i])
        elif bit==0:
            qc.append(uncompute,[x[i],carry[i-1],carry[i]])
        else:
            # Exact U-dagger in literal reverse instruction order.
            qc.x(x[i]);qc.x(carry[i-1])
            qc.append(uncompute,[x[i],carry[i-1],carry[i]])
            qc.x(carry[i-1]);qc.x(x[i])
            qc.x(carry[i])


def exhaustive_demorgan_comparator_phase_proof():
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
                demorgan_ripple_predicate(
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
                               f"DEMORGAN comparator w={width} t={threshold} x={input_x} en={enabled} flag={original_flag}")
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





def prove_all_three_sources_before_any_target_read(base):
    identity=boolean_and_inverse_operator_proof()
    h=HISTORICAL[base]
    # Build same original comparator SOURCE before changing the shared
    # primitive.predicate through which verified.build resolves arithmetic.
    primitive.predicate=previous.phase_aware_ripple_predicate
    original,or_reg=previous.verified.build(base)
    proof_original=previous.exhaustive_full_multiplier_phases(original,or_reg,base)
    assert proof_original['quantum_source_gate_counts']==h['original']['source']

    # Exact previous verified 1-CX OR candidate as matched SECOND control.
    primitive.predicate=orbase.minimized_or_ripple_predicate
    one_cx,one_reg=previous.verified.build(base)
    proof_one=previous.exhaustive_full_multiplier_phases(one_cx,one_reg,base)
    assert proof_one['quantum_source_gate_counts']==h['one_cx_or']['source']

    # Only one NEW logic component: disjoint public De Morgan OR lowering.
    primitive.predicate=demorgan_ripple_predicate
    proof_compare=exhaustive_demorgan_comparator_phase_proof()
    modadd=previous.exhaustive_modadd_phases(previous.source_constants())
    assert modadd['pass_all'] and modadd['source_gate_cases']==1584
    assert modadd['exact_complex_phase_plus_one'] and modadd['clean_helpers']
    new,new_reg=previous.verified.build(base)
    proof_new=previous.exhaustive_full_multiplier_phases(new,new_reg,base)

    for name,qc,proof in (('original',original,proof_original),
                          ('one_cx_or',one_cx,proof_one),
                          ('demorgan_zero_cx',new,proof_new)):
        assert qc.num_qubits==32,(base,name,qc.num_qubits)
        assert proof['pass_all'] and proof['full_residue_control_basis_cases']==128
        assert proof['exact_complex_output_phase_plus_one']
        assert proof['all_25_auxiliaries_clean'] and proof['control_unmodified']
        assert proof['disabled_invalid_states_identity']
        print('N35 PUBLIC SOURCE PHASE-EXACT',base,name,
              '128/128 ALL 25 HELPERS CLEAN EXACT +1 PHASE',
              proof['quantum_source_gate_counts'],flush=True)

    prior=proof_one['quantum_source_gate_counts']
    now=proof_new['quantum_source_gate_counts']
    k=h['or_steps']
    expected=dict(cx=prior['cx']-2*k,rccx=prior['rccx'],
                  x=prior['x']+6*k,ccx=prior['ccx'])
    if now!=expected:
        raise AssertionError(json.dumps(dict(
            stage='Source De Morgan zero-CX intervention missing/wrong',
            base=base,previous_source=prior,new_source=now,
            expected_source=expected,public_or_steps=k)))
    if not (k>0 and now['cx']<prior['cx'] and now['x']>prior['x']):
        raise AssertionError('No De Morgan reduction exercised')
    result=dict(pass_all=True,
        boolean_identity_and_rccx_inverse=identity,
        candidate_comparator_phase_proof=proof_compare,
        candidate_public_modadd_phase_proof=modadd,
        original_full_multiplier_phase_proof=proof_original,
        one_cx_or_full_multiplier_phase_proof=proof_one,
        demorgan_full_multiplier_phase_proof=proof_new,
        all_source_phase_amplitudes_exactly_plus_one=True,
        all_three_source_logical_qubits_32=True,
        all_three_25_helpers_clean=True,
        public_or_steps_rewritten=k,
        eliminated_cx_relative_to_one_cx_or=2*k,
        added_public_literal_x_relative_to_one_cx_or=6*k,
        exact_ccx_and_rccx_unchanged=True)
    print('N35 ZERO-CX DEMORGAN SOURCE VERIFIED',base,
          'BOOL',identity['public_boolean_or_cases'],
          'CMP',proof_compare['actual_emitted_gate_cases'],
          'MODADD',modadd['source_gate_cases'],'THREE FULL 128 EACH',
          'OR_STEPS',k,'CX_REMOVED',2*k,'X_ADDED',6*k,
          'ALL PHASE EXACT +1 ZERO QPU',flush=True)
    return dict(original=original,one_cx_or=one_cx,demorgan_zero_cx=new),result


def compile_native_cpu(pm,qc):
    start=time.perf_counter()
    result=pm.run(qc)
    elapsed=time.perf_counter()-start
    ops={str(k):int(v) for k,v in result.count_ops().items()}
    cz=int(ops.get('cz',0));depth=int(result.depth())
    if cz<=0 or depth<=0 or result.num_qubits<qc.num_qubits:
        raise AssertionError('Invalid IBM native target ISA compiler receipt')
    return dict(cz=cz,depth=depth,
                native_count_ops=ops,
                compiled_isa_width=int(result.num_qubits),
                native_size=int(result.size()),
                compiler_seconds=elapsed)


def comparison_summary(rows,reference):
    deltas=[p['deltas']['demorgan_minus_'+reference] for p in rows]
    dz=[d['cz'] for d in deltas]
    dd=[d['depth'] for d in deltas]
    wins=sum(a<0 and b<0 for a,b in zip(dz,dd))
    return dict(pairs=len(rows),
        strictly_lower_cz_count=sum(a<0 for a in dz),
        strictly_lower_depth_count=sum(b<0 for b in dd),
        jointly_better_cz_and_depth_count=wins,
        paired_cz_median=statistics.median(dz),
        paired_depth_median=statistics.median(dd),
        paired_cz_min=min(dz),paired_cz_max=max(dz),
        paired_depth_min=min(dd),paired_depth_max=max(dd),
        six_of_eight_joint_rule_pass=wins>=6,
        paired_medians_both_negative=(
            statistics.median(dz)<0 and statistics.median(dd)<0))


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f'qrr_n35_demorgan_zero_cx_base{base}.json'
    r=dict(revision=REV,research_lead='Chase Lunsford / CaMaLabs',
        utc=datetime.now(timezone.utc).isoformat(),
        preregistration='docs/QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_PREREG.md',
        experiment='One full-residue six-bit N35 controlled modular multiplier, three fixed comparator variants',
        N=N,base=base,seed_list=list(SEEDS),
        historical_8776_controls=HISTORICAL[base],
        exact_one_component_intervention='OR carry c=1 xor((not x)&(not p)); temporary RCCX+actual inverse',
        read_only_target='ibm_fez',optimization_level=1,
        physical_cz_cutoff=800,physical_depth_cutoff=2000,
        true_multiplicative_order_not_injected=True,
        hidden_prime_factors_not_used=True,
        source_orbit_not_precomputed=True,
        real_qpu_jobs=0,used_free_quantum_runtime=False,used_paid_quantum_runtime=False,
        seed_triple_metrics=[],status='STARTED',success=False)
    def save():path.write_text(json.dumps(r,indent=2,default=str)+'\n')
    save()
    try:
        circuits,proof=prove_all_three_sources_before_any_target_read(base)
        r['source_complex_phase_proofs']=proof
        r['status']='SOURCE_PHASE_EXACT_PROOFS_PASS'
        save()
        # Only metadata read; NEVER submit a quantum job or use Sampler.
        token=os.environ.get('IBM_QUANTUM_API_KEY','').strip()
        service=QiskitRuntimeService(channel='ibm_quantum_platform',
            plans_preference=['open'],**({'token':token} if token else {}))
        backend=service.backend('ibm_fez')
        if getattr(backend,'simulator',False) or backend.num_qubits<32:
            raise RuntimeError('No physical Fez target or insufficient native width')
        r['backend_reported_qubits']=int(backend.num_qubits)
        r['status']='NATIVE_CPU_COMPILING'
        save()

        for seed in SEEDS:
            pm=generate_preset_pass_manager(backend=backend,
                 optimization_level=1,seed_transpiler=seed)
            compiled={name:compile_native_cpu(pm,circuits[name])
              for name in ('original','one_cx_or','demorgan_zero_cx')}
            cand=compiled['demorgan_zero_cx']
            deltas={f'demorgan_minus_{ref}':dict(
                cz=cand['cz']-compiled[ref]['cz'],
                depth=cand['depth']-compiled[ref]['depth'])
                for ref in ('original','one_cx_or')}
            row=dict(seed=seed,circuits=compiled,deltas=deltas,
                candidate_better_than_one_cx_both=(
                  deltas['demorgan_minus_one_cx_or']['cz']<0 and
                  deltas['demorgan_minus_one_cx_or']['depth']<0),
                candidate_better_than_original_both=(
                  deltas['demorgan_minus_original']['cz']<0 and
                  deltas['demorgan_minus_original']['depth']<0),
                device_feasibility={name:(c['cz']<=800 and c['depth']<=2000)
                    for name,c in compiled.items()})
            r['seed_triple_metrics'].append(row)
            save()
            print('N35 DEMORGAN 3-ARM CPU FEZ MATCHED',base,seed,
              'ORIG',compiled['original']['cz'],compiled['original']['depth'],
              'ONECX',compiled['one_cx_or']['cz'],compiled['one_cx_or']['depth'],
              'DEMORGAN',cand['cz'],cand['depth'],
              'DELTA VS ONECX',deltas['demorgan_minus_one_cx_or'],
              'JOINT',row['candidate_better_than_one_cx_both'],
              'NO QPU',flush=True)

        summaries={reference:comparison_summary(r['seed_triple_metrics'],reference)
                   for reference in ('one_cx_or','original')}
        anchor=next(x for x in r['seed_triple_metrics'] if x['seed']==8776)
        historical=HISTORICAL[base]
        anchor_match=all(
            anchor['circuits'][name]['cz']==historical[name]['cz'] and
            anchor['circuits'][name]['depth']==historical[name]['depth']
            for name in ('original','one_cx_or'))
        summaries['all_previous_8776_anchors_exactly_reproduced']=anchor_match
        summaries['primary_robust_this_base_pass']=bool(
            anchor_match and
            summaries['one_cx_or']['six_of_eight_joint_rule_pass'] and
            summaries['one_cx_or']['paired_medians_both_negative'])
        summaries['secondary_robust_vs_original_pass']=bool(
            anchor_match and
            summaries['original']['six_of_eight_joint_rule_pass'] and
            summaries['original']['paired_medians_both_negative'])
        summaries['all_24_arms_fail_device_gate']=all(
            not accepted for row in r['seed_triple_metrics']
            for accepted in row['device_feasibility'].values())
        summaries['no_postselected_seeds']=True
        r.update(status='COMPILE_SUCCESS',success=True,
            all_eight_seed_triples_compiled=True,
            native_summary=summaries,real_qpu_jobs=0)
        save()
        print('N35 DEMORGAN EIGHT-SEED NATIVE SUMMARY',base,
              json.dumps(summaries,sort_keys=True),'ZERO QPU',flush=True)
        return 0
    except Exception as e:
        r.update(status='FAIL',success=False,
            failure_type=type(e).__name__,failure_message=str(e)[:2000],
            failure_trace=traceback.format_exc()[-3000:],
            real_qpu_jobs=0,used_free_quantum_runtime=False,
            used_paid_quantum_runtime=False)
        save()
        print('N35 DEMORGAN PHASE_OR_COMPILER_FAIL',base,
              type(e).__name__,str(e)[:900],
              traceback.format_exc()[-1400:],'ZERO QPU',flush=True)
        return 1


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--base',required=True,type=int,choices=BASES)
    raise SystemExit(main(p.parse_args().base))
