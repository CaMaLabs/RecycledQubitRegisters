#!/usr/bin/env python3
"""Eight matched seeds: phase-exact De Morgan comparator vs De Morgan+active_RCCX.

Original N35 controlled multiplier complete full 6bit residues, 32 logical
qubits/25 clean auxiliaries. Exactly the 2 active temporary control-latch
CCX are replaced by RCCX/actual inverse in candidate. Full ORIGINAL and
CANDIDATE source Operator complex phase proofs BEFORE target metadata.
Read-only ibm_fez CPU native compilation, NO REAL QPU/JOBS/RUNTIME.
Research lead: Chase Lunsford / CaMaLabs.
"""
from __future__ import annotations
import argparse,json,os,statistics,time,traceback
from datetime import datetime,timezone
from pathlib import Path
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
import qrr_n35_demorgan_zero_cx_or_multiseed as demorgan
import qrr_n35_relative_phase_latch_families as family

previous=demorgan.previous
primitive=demorgan.primitive
N=35
BASES=(2,8)
SEEDS=(11,37,101,409,8776,12011,20261,45673)
REV="qrr-n35-demorgan-active-only-eight-matched-v1-20261018"
ROOT=Path("results/ibm_shor35_demorgan_active_only")
HIST={
 2:dict(cz=7993,depth=18604,source=dict(cx=349,rccx=596,x=1738,ccx=160)),
 8:dict(cz=8758,depth=20575,source=dict(cx=357,rccx=616,x=1828,ccx=162))
}


def exact_gate_preflight(base):
    """Both complete source circuits independently gate-unitary verified."""
    original_identity=demorgan.boolean_and_inverse_operator_proof()
    local=family.shared.local_latch_unitary_test()
    assert original_identity['pass_all'] and original_identity['public_boolean_or_cases']==4
    assert original_identity['actual_rccx_inverse_operator_product_identity']
    assert local['pass_all'] and local['direct_actual_operator_cases']==8
    assert local['output_complex_phase_exactly_plus_one'] and local['final_latch_zero']
    cmp=demorgan.exhaustive_demorgan_comparator_phase_proof()
    assert cmp['pass_all'] and cmp['actual_emitted_gate_cases']==42672
    assert cmp['final_complex_phase_plus_one_every_case'] and cmp['zero_workspace_after_every_case']
    # This exact patch is the only comparator change relative to prior
    # source code; both old/candidate circuits share the same comparator.
    primitive.predicate=demorgan.demorgan_ripple_predicate
    modadd=previous.exhaustive_modadd_phases(previous.source_constants())
    assert modadd['pass_all'] and modadd['source_gate_cases']==1584
    assert modadd['exact_complex_phase_plus_one'] and modadd['clean_helpers']

    old,old_regs=previous.verified.build(base)
    candidate,candidate_regs=family.build_variant(base,"active_only")
    oldproof=previous.exhaustive_full_multiplier_phases(old,old_regs,base)
    newproof=previous.exhaustive_full_multiplier_phases(candidate,candidate_regs,base)
    for source,proof in ((old,oldproof),(candidate,newproof)):
        assert source.num_qubits==32
        assert proof['pass_all'] and proof['full_residue_control_basis_cases']==128
        assert proof['exact_complex_output_phase_plus_one']
        assert proof['all_25_auxiliaries_clean'] and proof['control_unmodified']
        assert proof['disabled_invalid_states_identity']

    actual_old=oldproof['quantum_source_gate_counts']
    actual_new=newproof['quantum_source_gate_counts']
    wanted=HIST[base]['source']
    assert actual_old==wanted,dict(actual_old=actual_old,wanted=wanted)
    assert actual_new==dict(
        cx=wanted['cx'],rccx=wanted['rccx']+2,
        x=wanted['x'],ccx=wanted['ccx']-2),dict(actual_new=actual_new)
    print('DEMORGAN+ACTIVE UNITARY SOURCE PASS base',base,
      '4 Boolean identity, 8 active phase, 42672 comparator, 1584 modadd,',
      '128 original + 128 active full, all25 clean, exact phase+1',
      'source original',actual_old,'active',actual_new,flush=True)
    return old,candidate,dict(pass_all=True,
       boolean_identity=original_identity,local_active=local,
       comparator=cmp,modadd=modadd,
       original_full=oldproof,candidate_full=newproof,
       source_old=actual_old,source_active=actual_new,
       exactly_two_active_rccx_replaced=True,
       both_source_32_qubits=True,all_25_helper_bits_clean=True,
       exact_quantum_output_phase_plus_one=True)


def compile_native(pm,qc):
    start=time.perf_counter()
    out=pm.run(qc)
    dur=time.perf_counter()-start
    ops={str(k):int(v) for k,v in out.count_ops().items()}
    result=dict(cz=int(ops.get('cz',0)),depth=int(out.depth()),
        native_count_ops=ops,native_total_ops=int(out.size()),
        compiled_device_width=int(out.num_qubits),
        seconds=dur)
    if not (result['cz']>0 and result['depth']>0 and result['compiled_device_width']>=qc.num_qubits):
        raise AssertionError("Invalid compiler metrics")
    return result


def stats(pairs):
    assert len(pairs)==8
    dc=[p['delta_active_minus_original']['cz'] for p in pairs]
    dd=[p['delta_active_minus_original']['depth'] for p in pairs]
    both=sum(z<0 and d<0 for z,d in zip(dc,dd))
    med_c=statistics.median(dc)
    med_d=statistics.median(dd)
    return dict(eight_matched_pairs_complete=True,
      paired_seed_count=len(pairs),joint_both_improve=both,
      cz_improve_count=sum(z<0 for z in dc),
      depth_improve_count=sum(d<0 for d in dd),
      median_paired_cz=med_c,median_paired_depth=med_d,
      min_paired_cz=min(dc),max_paired_cz=max(dc),
      min_paired_depth=min(dd),max_paired_depth=max(dd),
      six_of_eight_joint_rule=(both>=6),
      negative_both_medians=(med_c<0 and med_d<0))


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    path=ROOT/f'qrr_n35_demorgan_active_only_base{base}.json'
    row=dict(revision=REV,research_lead='Chase Lunsford / CaMaLabs',
        utc=datetime.now(timezone.utc).isoformat(),
        prereg='docs/QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_PREREG.md',
        modulus=35,base=base,
        scope='one controlled N35 full-six-bit public modular multiplier',
        seeds=list(SEEDS),hardware_target_read_only='ibm_fez',
        optimization_level=1,historical_original=HIST[base],
        physical_cz_limit=800,physical_depth_limit=2000,
        true_order_not_used=True,factors_not_used=True,
        multiplication_orbit_not_hardcoded=True,
        actual_qpu_jobs=0,free_runtime_used=False,paid_runtime_used=False,
        pairs=[],status='STARTED',success=False)
    def save():path.write_text(json.dumps(row,indent=2,default=str)+'\n')
    save()
    try:
        old,new,proof=exact_gate_preflight(base)
        row['complex_source_gate_proof']=proof
        row['status']='SOURCE_UNITARY_PROOF_PASSED'
        save()
        token=os.environ.get('IBM_QUANTUM_API_KEY','').strip()
        service=QiskitRuntimeService(channel='ibm_quantum_platform',
                 plans_preference=['open'],**({'token':token} if token else {}))
        backend=service.backend('ibm_fez')
        if getattr(backend,'simulator',False) or backend.num_qubits<32:
            raise RuntimeError('No valid physical Fez target for CPU compile')
        row['target_device_qubits']=backend.num_qubits
        row['status']='COMPILING_EIGHT_SEEDS_CPU_ONLY'
        save()
        for seed in SEEDS:
            pm=generate_preset_pass_manager(backend=backend,
                   optimization_level=1,seed_transpiler=seed)
            orig=compile_native(pm,old)
            active=compile_native(pm,new)
            dc=active['cz']-orig['cz']
            dd=active['depth']-orig['depth']
            p=dict(seed=seed,original=orig,active_only=active,
                delta_active_minus_original=dict(cz=dc,depth=dd),
                paired_both_improve=dc<0 and dd<0,
                physical_device_old=orig['cz']<=800 and orig['depth']<=2000,
                physical_device_active=active['cz']<=800 and active['depth']<=2000)
            row['pairs'].append(p)
            save()
            print('DEMORGAN ACTIVE MATCHED',base,seed,
                'original',orig['cz'],orig['depth'],
                'active',active['cz'],active['depth'],
                'delta',dc,dd,'both',p['paired_both_improve'],
                'QPU gate',p['physical_device_active'],'ZERO QPU',flush=True)
        summary=stats(row['pairs'])
        anchor=next(p for p in row['pairs'] if p['seed']==8776)['original']
        ok=(anchor['cz'],anchor['depth'])==(HIST[base]['cz'],HIST[base]['depth'])
        summary['frozen_original_seed_8776_exact']=ok
        summary['robust_gate_this_base_pass']=bool(
            ok and summary['six_of_eight_joint_rule'] and summary['negative_both_medians'])
        summary['every_seed_fails_device_gate']=all(
             not p['physical_device_active'] for p in row['pairs'])
        row.update(status='COMPILE_SUCCESS',success=True,
           all_8_pairs_completed=True,summary=summary,
           actual_qpu_jobs=0,free_runtime_used=False,paid_runtime_used=False)
        save()
        print('DEMORGAN ACTIVE EIGHT SEEDS SUMMARY base',base,
              json.dumps(summary,sort_keys=True),'NO QPU',flush=True)
        return 0
    except Exception as exc:
        row.update(status='FAIL',success=False,
             error_class=type(exc).__name__,error_message=str(exc)[:1800],
             trace=traceback.format_exc()[-3100:],
             actual_qpu_jobs=0,free_runtime_used=False,paid_runtime_used=False)
        save()
        print('DEMORGAN ACTIVE FAILED base',base,
              type(exc).__name__,str(exc)[:800],
              traceback.format_exc()[-1300:],'ZERO QPU',flush=True)
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=int,required=True,choices=BASES)
    raise SystemExit(main(parser.parse_args().base))
