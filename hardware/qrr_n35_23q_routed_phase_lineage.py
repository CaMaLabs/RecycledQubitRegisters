#!/usr/bin/env python3
"""Trace routed SWAP lineage of the genuine 23-source-qubit N35 dynamic phase.

Chase Lunsford / CaMaLabs, 2026-10-24. No source changes and ZERO real QPU jobs.
Qiskit CPU staged routing vs final native IBM Fez target:
  2 public bases x 3 precisions x 2 frozen compiler seeds.
Strictly separate source logical phase reuse, compiler routed SWAP-token
evidence, final native phase physical addresses, and untested device execution.
Fail INCONCLUSIVE on missing layout/mismatched event path; never invent a
fixed physical phase qubit or assert on-device timing.
"""
from __future__ import annotations
import argparse,json,os,traceback,time
from pathlib import Path
from datetime import datetime,timezone
from qiskit.transpiler import StagedPassManager
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_true_recycled_prune_idle_scratch as prune
import qrr_n35_native_dynamic_feedback_phase_audit as feedback

N=35
BASES=(2,8)
BITS=(4,6,8)
SEEDS=(509,8776)
REV="qrr-n35-true-23q-phase-routed-swap-lineage-v1-20261024"
ROOT=Path("results/ibm_shor35_true_recycled_phase_route_lineage")
OLD_PRUNED={
  2:{4:(29223,68106),6:(44313,102275),8:(59730,138953)},
  8:{4:(15036,34595),6:(15036,34597),8:(15036,34599)}
}

def _qi(circuit,q):
    return int(circuit.find_bit(q).index)

def _ci(circuit,c):
    return int(circuit.find_bit(c).index)

def _events(circuit):
    """Ordered events. This is a circuit structure comparison only, not proof."""
    events=[]
    for i,ins in enumerate(circuit.data):
        name=ins.operation.name
        if name not in ('measure','reset','if_else'):
            continue
        physical=[_qi(circuit,q) for q in ins.qubits]
        row=dict(index=i,name=name,physical=physical)
        if name=='measure':
            row["classical"]=[_ci(circuit,x) for x in ins.clbits]
        if name=='if_else':
            cond=getattr(ins.operation,'condition',None)
            if isinstance(cond,tuple) and len(cond)==2:
                try:
                    row['condition_bit']=_ci(circuit,cond[0])
                    row['condition_value']=int(cond[1])
                except Exception:
                    row['condition_unresolved']=str(cond)[:100]
            else:
                row['condition_unresolved']=str(cond)[:100]
        events.append(row)
    return events


def track_routed_stage(original,routed,bits):
    """Conservative, explicit logical phase token in the routed swap stage."""
    out=dict(status='STARTED',source_one_phase_wire=True,
       routed_qubit_width=int(routed.num_qubits),
       routed_instruction_count=len(routed.data),
       routed_operation_counts={str(k):int(v) for k,v in routed.count_ops().items()},
       raw_routed_phase_events=_events(routed),
       provenance='Qiskit CPU preset init+layout+routing stages ONLY',
       physically_fixed_single_phase_site_proven=False,
       phase_token_trace_certified=False,
       problems=[],phase_swaps=[],routed_phase_events=[])
    problem=out['problems']
    layout=getattr(routed,'layout',None)
    initial_layout=getattr(layout,'initial_layout',None) if layout is not None else None
    orig_phase=next((r[0] for r in original.qregs if r.name=='recycled_phase'),None)
    if orig_phase is None:
        raise AssertionError("Source does not expose one unique recycled_phase register")
    virtuals=initial_layout.get_virtual_bits() if initial_layout is not None else {}
    # Never infer a physical phase start position from an arbitrary observed
    # measurement: that would be circular when trying to prove the lineage.
    if orig_phase not in virtuals:
        problem.append('Original source phase qubit absent from initial_layout virtual map')
        out.update(status='INCONCLUSIVE_LAYOUT_MISSING',initial_layout_virtual_size=len(virtuals))
        return out
    token=int(virtuals[orig_phase])
    if token<0 or token>=routed.num_qubits:
        problem.append(f'Initial physical phase {token} out of routed circuit bounds')
        out.update(status='INCONCLUSIVE_LAYOUT_INVALID')
        return out
    out['original_source_phase_index']=_qi(original,orig_phase)
    out['initial_phase_physical_address']=token
    out['initial_layout_virtual_size']=len(virtuals)
    source_event_names=[z['name'] for z in _events(original)]
    swap_count=0
    phase_swap_count=0
    for i,ins in enumerate(routed.data):
        name=ins.operation.name
        physical=[_qi(routed,q) for q in ins.qubits]
        if name=='swap':
            if len(physical)!=2:
                problem.append('Unexpected nonbinary swap at instruction '+str(i))
                continue
            a,b=physical
            swap_count+=1
            if token==a or token==b:
                prior=token
                token=b if token==a else a
                phase_swap_count+=1
                out['phase_swaps'].append(dict(instruction=i,from_physical=prior,to_physical=token))
        elif name in ('measure','reset','if_else'):
            row=dict(index=i,name=name,token_physical_address=token,
                     observed_physical_addresses=physical,
                     phase_token_matches=(physical==[token]))
            if name=='measure':
                row['classical']=[_ci(routed,c) for c in ins.clbits]
            if name=='if_else':
                condition=getattr(ins.operation,'condition',None)
                if isinstance(condition,tuple) and len(condition)==2:
                    try:
                        row['condition_bit']=_ci(routed,condition[0])
                        row['condition_value']=int(condition[1])
                    except Exception:row['condition_unresolved']=str(condition)[:120]
                else:
                    row['condition_unresolved']=str(condition)[:120]
            if not row['phase_token_matches']:
                problem.append(f"Phase token unexpected at routed op {i} {name}: token physical {token}, observed {physical}")
            out['routed_phase_events'].append(row)
    out['total_explicit_routed_swap_ops']=swap_count
    out['phase_token_swap_ops']=phase_swap_count
    out['final_tracked_phase_address']=token
    routed_names=[e['name'] for e in out['routed_phase_events']]
    if routed_names!=source_event_names:
        problem.append(f'Routed dynamic event names/order differ source: {routed_names[:15]} vs {source_event_names[:15]}')
    expected=dict(measure=bits,reset=bits-1,if_else=bits*(bits-1)//2)
    counts={s:sum(e['name']==s for e in out['routed_phase_events']) for s in expected}
    if counts!=expected:
        problem.append(f'Routed dynamic event counts changed: {counts} vs {expected}')
    out['expected_dynamic_counts']=expected
    out['routed_dynamic_counts']=counts
    # Ensure every compiled conditional reads a previously measured classical
    # output before its own stage. Condition/order is additional to token check.
    earlier=set()
    for row in out['routed_phase_events']:
        if row['name']=='measure':
            if len(row.get('classical',[]))!=1:
                problem.append('Unexpected measurement classical width')
            else:
                earlier.add(row['classical'][0])
        elif row['name']=='if_else':
            if row.get('condition_bit') not in earlier or row.get('condition_value')!=1:
                problem.append('Conditional not a previously measured bit or condition not 1')
    all_matches=all(e['phase_token_matches'] for e in out['routed_phase_events'])
    out['phase_token_trace_certified']=bool(not problem and all_matches)
    out['status']='ROUTED_SWAP_TOKEN_PASS' if out['phase_token_trace_certified'] else 'ROUTED_LINEAGE_INCONCLUSIVE'
    out['physically_fixed_single_phase_site_proven']=bool(
        out['phase_token_trace_certified'] and
        len(set(e['observed_physical_addresses'][0] for e in out['routed_phase_events']))==1)
    return out


def compare_routed_and_native(routed_info,native,bits):
    final_events=_events(native)
    out=dict(final_native_phase_events=final_events,
       final_native_event_counts={x:sum(e['name']==x for e in final_events)
                                   for x in ('measure','reset','if_else')},
       native_event_order_and_physical_match_routed=False,
       source_phase_lineage_to_native_certified=False,
       physically_fixed_single_phase_site_proven=False,
       problems=[])
    exp=routed_info.get('routed_phase_events',[])
    if len(exp)!=len(final_events):
        out['problems'].append(f'Native {len(final_events)} dynamic vs routed {len(exp)}')
    for i,(r,n) in enumerate(zip(exp,final_events)):
        if r['name']!=n['name'] or r['observed_physical_addresses']!=n['physical']:
            out['problems'].append(
               f'Physical phase event {i}: routed {r["name"]}@{r["observed_physical_addresses"]} '
               f'vs native {n["name"]}@{n["physical"]}')
        if r['name']=='measure' and r.get('classical')!=n.get('classical'):
            out['problems'].append(f'Classical measure output mismatch at event {i}')
        if r['name']=='if_else' and (
            r.get('condition_bit')!=n.get('condition_bit') or
            r.get('condition_value')!=n.get('condition_value')):
            out['problems'].append(f'Native measured-bit condition differs at event {i}')
    if not out['problems'] and len(exp)==len(final_events):
        out['native_event_order_and_physical_match_routed']=True
    out['source_phase_lineage_to_native_certified']=bool(
        routed_info.get('phase_token_trace_certified') and
        out['native_event_order_and_physical_match_routed'])
    phaseaddresses=[e['physical'][0] for e in final_events
                    if len(e['physical'])==1]
    out['native_phase_event_unique_physical_addresses']=sorted(set(phaseaddresses))
    out['physically_fixed_single_phase_site_proven']=bool(
        out['source_phase_lineage_to_native_certified'] and len(set(phaseaddresses))==1)
    return out


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    resultpath=ROOT/f'qrr_n35_23q_routed_phase_lineage_base{base}.json'
    r=dict(revision=REV,research_lead="Chase Lunsford / CaMaLabs",
      utc=datetime.now(timezone.utc).isoformat(),
      preregistration="docs/QRR_N35_23Q_ROUTED_PHASE_LINEAGE_PREREG.md",
      public_base=base,N=N,bits_list=list(BITS),seed_list=list(SEEDS),
      qiskit_optimization_level=1,backend_target="ibm_fez",
      source_phase_qubits=1,source_quantum_width=23,
      old_original_32q_historical_anchors=prune.PREVIOUS_NATIVE[base],
      old_pruned_23q_seed8776_anchors=OLD_PRUNED[base],
      frozen_hardware_CZ_limit=800,frozen_hardware_depth_limit=2000,
      actual_qpu_jobs=0,IBM_free_or_paid_quantum_runtime_used=False,
      backend_run_never_invoked=True,
      results=[],status='STARTED',success=False)
    def save():resultpath.write_text(json.dumps(r,indent=2,default=str)+"\n")
    save()
    try:
        originals,orig_valid=prune.reference.original_structure_exact(base)
        r['previous_immutable_source_integrity']=orig_valid
        qcs={}
        sourceproof={}
        for bits in BITS:
            qc,detail=prune.reduction_with_exact_instruction_identity(originals[bits],bits)
            assert qc.num_qubits==23 and qc.num_clbits==bits
            assert detail['unchanged_conditional_body_and_previous_classical_control']
            assert detail['scratch_all_nine_actually_unused']
            qcs[bits]=qc
            sourceproof[str(bits)]=detail
        r['source_proofs']=sourceproof
        r['status']='SIX_ORIGINAL_SOURCE_EQUIVALENCE_PASS'
        save()
        print('Genuine 23q original quantum source EXACT unchanged (9 idle scratch removed)',base,flush=True)
        key=os.environ.get('IBM_QUANTUM_API_KEY','').strip()
        service=QiskitRuntimeService(channel='ibm_quantum_platform',
            plans_preference=['open'],**({'token':key} if key else {}))
        backend=service.backend('ibm_fez')
        assert not getattr(backend,'simulator',False) and backend.num_qubits>=32
        r['target_device_qubits']=int(backend.num_qubits)
        r['status']='CPU_STAGED_ROUTING_AND_NATIVE_AUDIT'
        save()
        oldreceipt=json.loads(Path(
          f"results/ibm_shor35_true_recycled_idle_scratch_pruning/"
          f"qrr_n35_prune_idle_scratch_base{base}.json").read_text())
        for bits in BITS:
            for seed in SEEDS:
                row=dict(bits=bits,seed=seed,status='STARTED')
                r['results'].append(row)
                save()
                try:
                    qc=qcs[bits]
                    pm=generate_preset_pass_manager(
                        backend=backend,optimization_level=1,seed_transpiler=seed)
                    # Qiskit public StagedPassManager API creates an actual
                    # routed pre-ISA snapshot WITHOUT translation/optimization.
                    pre=StagedPassManager(stages=['init','layout','routing'],
                        init=pm.init,layout=pm.layout,routing=pm.routing)
                    t=time.perf_counter()
                    routed=pre.run(qc)
                    routed_time=time.perf_counter()-t
                    route=track_routed_stage(qc,routed,bits)
                    t=time.perf_counter()
                    native=pm.run(qc)
                    native_time=time.perf_counter()-t
                    counts={str(k):int(v) for k,v in native.count_ops().items()}
                    branch=feedback.certify_branch_operators(native,bits)
                    required=bool(
                        branch['all_native_condition_body_operators_proved'] and
                        branch['fully_certified_prior_classical_measurement_conditions'] and
                        branch['emitted_compiled_if_else_count']==bits*(bits-1)//2 and
                        branch['measurement_classical_targets']==list(range(bits)) and
                        counts.get('measure')==bits and counts.get('reset')==bits-1)
                    if not required:
                        raise AssertionError('Compiled dynamic feedback operator / controls failed: '+str(branch.get('problems'))[:700])
                    physical=compare_routed_and_native(route,native,bits)
                    cz=int(counts.get('cz',0));depth=int(native.depth())
                    if cz<=0 or depth<=0:raise AssertionError('Bad native ISA metrics')
                    original_seed8776=next((x for x in oldreceipt['pairs']
                          if x['bits']==bits and x['seed']==8776),None)
                    if original_seed8776 is None:
                        raise AssertionError('Archived source-pruned seed8776 missing')
                    anchor_expected=OLD_PRUNED[base][bits]
                    assert (original_seed8776['pruned_23q']['compiled_native_cz'],
                       original_seed8776['pruned_23q']['compiled_native_depth'])==anchor_expected
                    same_anchor=(cz,depth)==anchor_expected if seed==8776 else None
                    row.update(status='STAGED_ROUTING_AND_FEZ_NATIVE_CPU_COMPLETE',
                        staged_routing=route,native_lineage_comparison=physical,
                        native_cz=cz,native_depth=depth,
                        native_count_ops=counts,
                        native_compiled_qubit_width=int(native.num_qubits),
                        compiler_routed_seconds=routed_time,
                        compiler_native_seconds=native_time,
                        conditional_operator_equivalence_pass=True,
                        native_conditional_comparison_count=branch['emitted_compiled_if_else_count'],
                        archived_23q_seed8776_cost_anchor_reproduced=same_anchor,
                        original_archived_8776_23q_costs=list(anchor_expected),
                        quantum_hardware_gate_pass=bool(cz<=800 and depth<=2000),
                        fixed_single_physical_phase_site_proven=physical['physically_fixed_single_phase_site_proven'],
                        routed_swap_lineage_pass=route.get('phase_token_trace_certified',False),
                        routed_to_native_lineage_pass=physical['source_phase_lineage_to_native_certified'])
                    print('ROUTED PHASE LINEAGE CPU base',base,'b',bits,'seed',seed,
                        'stage swaps',route.get('total_explicit_routed_swap_ops'),
                        'phase swaps',route.get('phase_token_swap_ops'),
                        'routed',row['routed_swap_lineage_pass'],
                        'final ISA',row['routed_to_native_lineage_pass'],
                        'native physical',physical['native_phase_event_unique_physical_addresses'],
                        'CZ',cz,'depth',depth,'anchor',same_anchor,
                        'NO QPU',flush=True)
                except Exception as exc:
                    row.update(status='INCOMPLETE_OR_ERROR',error_type=type(exc).__name__,
                        error_message=str(exc)[:1300],error_traceback=traceback.format_exc()[-1700:])
                    print('ROUTED PHASE LINEAGE FAILURE base',base,'b',bits,'seed',seed,
                        type(exc).__name__,str(exc)[:450],traceback.format_exc()[-900:],
                        'NO QPU',flush=True)
                save()
        full=[row for row in r['results'] if row['status']=='STAGED_ROUTING_AND_FEZ_NATIVE_CPU_COMPLETE']
        r['summary']=dict(
            experiments=len(r['results']),complete_native_audits=len(full),
            stage_phase_token_pass=sum(x['routed_swap_lineage_pass'] for x in full),
            source_phase_lineage_to_native_certified=sum(x['routed_to_native_lineage_pass'] for x in full),
            single_fixed_physical_phase_site_proven=sum(x['fixed_single_physical_phase_site_proven'] for x in full),
            all_original_pruned_seed8776_anchors_reproduced=all(
               x['archived_23q_seed8776_cost_anchor_reproduced'] is True for x in full if x['seed']==8776)
               if len([x for x in full if x['seed']==8776])==3 else False,
            native_feedback_phase_operator_checks=sum(x['native_conditional_comparison_count'] for x in full),
            hardware_feasible_count=sum(x['quantum_hardware_gate_pass'] for x in full),
            no_quantum_processor_execution=True,
            one_source_phase_qubit_not_a_claim_of_one_fixed_hardware_site=True,
            real_device_feedback_latency_NOT_TESTED=True,
            physical_qubit_lineage_fully_certified_for_all_cases=bool(
              len(full)==6 and all(x['routed_to_native_lineage_pass'] for x in full)))
        r['success']=len(full)==len(BITS)*len(SEEDS)
        r['status']='COMPLETE_ROUTE_AUDITS' if r['success'] else 'PARTIAL_ROUTE_AUDITS'
        save()
        print('ROUTED PHASE LINEAGE AUDIT FINAL',base,json.dumps(r['summary'],sort_keys=True),'ZERO QPU',flush=True)
        return 0 if r['success'] else 1
    except Exception as exc:
        r.update(status='FAIL',success=False,error_type=type(exc).__name__,
           error_message=str(exc)[:1500],error_traceback=traceback.format_exc()[-2800:],
           actual_qpu_jobs=0,IBM_free_or_paid_quantum_runtime_used=False)
        save()
        print('ROUTED PHASE LINEAGE GLOBAL FAILURE',base,type(exc).__name__,
            str(exc)[:850],traceback.format_exc()[-1600:],'ZERO QPU',flush=True)
        return 1

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--base',type=int,choices=BASES,required=True)
    raise SystemExit(main(p.parse_args().base))
