#!/usr/bin/env python3
"""Preregistered public constant/carry XOR fusion, 8 matched native CPU seeds.

Research lead: Chase Lunsford / CaMaLabs. One intended arithmetic rewrite:
when a public bit of k and an incoming carry both toggle the target bit,
use just the controlled less-than carry predicate instead of two XOR flips.

The base N35 multiplier and exact RCCX temporary comparator carry are from
the original independently phase-proven kernel, unchanged. Directly interpret
each emitted Qiskit Operator monomial complex phase, including on all 8192
six-bit controlled additions BEFORE reading native IBM Fez TARGET metadata.
No QPU jobs/runtime, no full Shor factoring circuit, no seed postselection.
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

from qiskit import QuantumCircuit,QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService

import qrr_n35_relative_phase_ripple_carry as previous

# previous.best is the original verified constant-prefix adder module;
# previous.verified.build uses its modadd through primitive.modadd.
best=previous.best
verified=previous.verified

REV="qrr-n35-fused-public-bit-carry-matched-seeds-v1-20261017"
SEEDS=(11,37,101,409,8776,12011,20261,45673)
BASES=(2,8)
BITS=6
N=35
ROOT=Path("results/ibm_shor35_fused_constant_carry_multiseed")
HISTORICAL={
  2:dict(cz=9263,depth=21772,
         source=dict(cx=1033,rccx=596,x=28,ccx=160)),
  8:dict(cz=9426,depth=21933,
         source=dict(cx=1077,rccx=616,x=28,ccx=162))
}

# Original function reference is retained. Only the module-wide adder name
# is patched AFTER the original 32-qubit full circuit has been constructed.
ORIGINAL_ADDER=best.constant_add_from_prefix_carry


def fused_constant_add(qc,target,value,controls,carry,chain):
    """For public k_j=1 and carry predicate P: 1 XOR P is NOT P.

    Controlled 'k_j XOR carry_j' directly as one predicate of selected sign.
    Iterate MSB->LSB, so lower target bits remain original while queried.
    """
    target=list(target)
    controls=list(controls)
    n=len(target)
    k=int(value)%(1<<n)
    for j in range(n-1,-1,-1):
        low=k&((1<<j)-1)
        bit=(k>>j)&1
        if low:
            threshold=(1<<j)-low
            best.public_threshold_predicate(
                qc,target[:j],threshold,target[j],carry[:j],chain,
                controls=controls,geq=(bit==0))
            # If bit=1, comparator returns x_low < threshold directly;
            # old comparator >= threshold XOR controlled unconditional X.
        elif bit:
            # Carry is provably zero since all lower public k bits are 0.
            previous.primitive.multi_x(qc,controls,target[j],chain)


def check_source_gate_fusion(old_circuit,new_circuit,base):
    """Fail closed unless ONLY intended CX->2X polarity substitution occurs."""
    old=previous.actual_complex_instructions(old_circuit)[2]
    new=previous.actual_complex_instructions(new_circuit)[2]
    assert old==HISTORICAL[base]["source"],(base,old)
    assert new.get("rccx",0)==old.get("rccx",0),(old,new)
    assert new.get("ccx",0)==old.get("ccx",0),(old,new)
    assert new.get("cx",0)<old.get("cx",0),(old,new)
    saved=old["cx"]-new["cx"]
    # Each fused one-controlled constant XOR eliminates one source CX,
    # replaced by 2 reversible X toggles on the comparator's CLEAN carry.
    assert new.get("x",0)-old.get("x",0)==2*saved,(old,new,saved)
    assert new_circuit.num_qubits==old_circuit.num_qubits==32
    return dict(pass_all=True,old_source=old,new_source=new,
        removed_semantic_controlled_cx=saved,
        added_comparator_clean_x=2*saved,
        extra_rccx=0,extra_exact_ccx=0,
        unchanged_layout_32_logical_qubits=True)


def exhaustive_fused_six_bit_add_phase_proof():
    """All k,x in 0..63, enabled 0/1 = 8192 actual gate-unitary cases."""
    cases=0
    total_fused_terms=0
    witnessed_rccx=0
    per_constant=[]
    for k in range(64):
        enable=QuantumRegister(1,'enable')
        target=QuantumRegister(BITS,'target')
        carry=QuantumRegister(BITS,'carry')
        scratch=QuantumRegister(BITS+3,'scratch')
        qc=QuantumCircuit(enable,target,carry,scratch)
        fused_constant_add(qc,target,k,[enable[0]],carry,scratch)
        ix,instr,ops=previous.actual_complex_instructions(qc)
        control_pos=ix[enable[0]]
        target_pos=[ix[q] for q in target]
        aux_pos=[ix[q] for reg in (carry,scratch) for q in reg]
        fused_terms=sum(int(bool(k&(1<<j)) and bool(k&((1<<j)-1)))
                        for j in range(BITS))
        total_fused_terms+=fused_terms
        witnessed_rccx+=ops.get("rccx",0)
        for initial_enable in (0,1):
            for x in range(64):
                initial=initial_enable<<control_pos
                for j,pos in enumerate(target_pos):
                    initial|=((x>>j)&1)<<pos
                actual,phase=previous.evolve_basis(instr,initial)
                got=sum(((actual>>pos)&1)<<j
                        for j,pos in enumerate(target_pos))
                expected=((x+k)%64 if initial_enable else x)
                if got!=expected:
                    raise AssertionError(json.dumps(dict(
                       stage='fused_constant_add',k=k,x=x,
                       enable=initial_enable,actual=got,expected=expected)))
                if ((actual>>control_pos)&1)!=initial_enable:
                    raise AssertionError("Adder external enable mutated")
                if any((actual>>pos)&1 for pos in aux_pos):
                    raise AssertionError(json.dumps(dict(
                       stage='fused_constant_add',k=k,x=x,
                       enable=initial_enable,error='dirty carry or scratch')))
                previous.check_exact_phase(phase,
                     f'fused six-bit k={k} x={x} enable={initial_enable}')
                cases+=1
        per_constant.append(dict(public_constant=k,basis_cases=128,
             clean_carry_and_chain=True,complex_phase_exactly_plus_one=True,
             fused_carry_polarity_terms=fused_terms,
             actual_source_operation_counts=ops))
    assert cases==8192 and total_fused_terms>0 and witnessed_rccx>0
    return dict(pass_all=True,actual_emitted_source_complex_gate_cases=cases,
        all_64_public_constants=True,all_64_six_bit_work_inputs=True,
        both_external_enable_values=True,
        exact_complex_phase_plus_one=True,
        all_carry_and_scratch_clean=True,
        fused_polarity_bit_terms_across_64_constants=total_fused_terms,
        relative_phase_rccx_observed_in_comparator=witnessed_rccx,
        per_constant=per_constant)


def prove_sources_before_target(base):
    """Build old before replacing name in old module; full proofs both arms."""
    # Compare uses original old source gate instructions independent of future
    # adder replacement; source Qiskit circuit already materialized.
    best.constant_add_from_prefix_carry=ORIGINAL_ADDER
    old_qc,old_reg=verified.build(base)
    old_proof=previous.exhaustive_full_multiplier_phases(old_qc,old_reg,base)
    assert old_proof["pass_all"] and old_proof["exact_complex_output_phase_plus_one"]
    assert old_proof["all_25_auxiliaries_clean"]
    best.constant_add_from_prefix_carry=fused_constant_add

    standalone=exhaustive_fused_six_bit_add_phase_proof()
    print("FUSED SIX-BIT CONSTANT ADD ALL SOURCE PHASES",
          base,standalone["actual_emitted_source_complex_gate_cases"],
          "phase +1 all scratch CLEAN",flush=True)
    comparator=previous.exhaustive_comparator_phase_proof()
    assert comparator["pass_all"] and comparator["actual_gate_comparator_cases"]==42672
    assert comparator["exact_complex_phase_plus_one"]
    print("UNCHANGED PHASE-AWARE RIPPLE COMPARATOR",
          base,comparator["actual_gate_comparator_cases"],flush=True)
    modadd=previous.exhaustive_modadd_phases(previous.source_constants())
    assert modadd["pass_all"] and modadd["source_gate_cases"]==1584
    assert modadd["exact_complex_phase_plus_one"]
    print("FUSED MODULAR ADD FULL SOURCE COMPLEX CHECK",
          base,modadd["source_gate_cases"],flush=True)
    new_qc,new_reg=verified.build(base)
    candidate_proof=previous.exhaustive_full_multiplier_phases(
        new_qc,new_reg,base)
    for name,proof in (('original',old_proof),('fused',candidate_proof)):
        assert proof['pass_all'] and proof['full_residue_control_basis_cases']==128
        assert proof['all_25_auxiliaries_clean'] and proof['control_unmodified']
        assert proof['exact_complex_output_phase_plus_one']
        assert proof['disabled_invalid_states_identity']
    gate_change=check_source_gate_fusion(old_qc,new_qc,base)
    print("PHASE EXACT FULL SOURCE BOTH ARMS",base,
        "128+128 inputs 25 CLEAN, +1 PHASE, source removed",
        gate_change["removed_semantic_controlled_cx"],"CX, added",
        gate_change["added_comparator_clean_x"],"X",flush=True)
    return old_qc,new_qc,dict(pass_all=True,
        direct_gate_complex_phase_check_before_backend_read=True,
        old_full_proof=old_proof,new_full_proof=candidate_proof,
        six_bit_constant_add=standalone,
        comparator=comparator,
        modadd=modadd,
        source_change=gate_change,
        source_width_both_32=True,
        source_seed_independent=True)


def compile_isa_target(pm,circuit):
    start=time.perf_counter()
    native=pm.run(circuit)
    seconds=time.perf_counter()-start
    ops={str(k):int(v) for k,v in native.count_ops().items()}
    cz=int(ops.get("cz",0))
    depth=int(native.depth())
    if cz<=0 or depth<=0 or native.num_qubits<circuit.num_qubits:
        raise AssertionError("Invalid Fez native target resource measurement")
    return dict(cz=cz,depth=depth,
        native_ops=ops,compiled_device_width=int(native.num_qubits),
        compiled_gates=int(native.size()),compiler_seconds=seconds)


def aggregate(pairs):
    assert len(pairs)==len(SEEDS)
    deltas_cz=[p['difference_fused_minus_old']['cz'] for p in pairs]
    deltas_depth=[p['difference_fused_minus_old']['depth'] for p in pairs]
    wins=sum(p['paired_strict_improvement_both'] for p in pairs)
    median_cz=statistics.median(deltas_cz)
    median_depth=statistics.median(deltas_depth)
    return dict(matched_seed_pairs=len(pairs),
        both_metrics_strict_improvement_seed_count=wins,
        cz_improvement_seeds=sum(z<0 for z in deltas_cz),
        depth_improvement_seeds=sum(d<0 for d in deltas_depth),
        paired_cz_delta_median=median_cz,
        paired_depth_delta_median=median_depth,
        paired_cz_delta_min=min(deltas_cz),
        paired_cz_delta_max=max(deltas_cz),
        paired_depth_delta_min=min(deltas_depth),
        paired_depth_delta_max=max(deltas_depth),
        joint_wins_at_least_six_of_eight=(wins>=6),
        both_medians_negative=(median_cz<0 and median_depth<0),
        all_original_seed_rows_preserved=True)


def main(base):
    assert base in BASES
    ROOT.mkdir(parents=True,exist_ok=True)
    dest=ROOT/f"qrr_n35_fused_constant_carry_base{base}.json"
    receipt=dict(revision=REV,research_lead='Chase Lunsford / CaMaLabs',
       utc=datetime.now(timezone.utc).isoformat(),
       preregistration="docs/QRR_N35_FUSED_CONSTANT_CARRY_MULTISEED_PREREG.md",
       N=N,base=base,
       scope="one controlled full-six-bit modular multiplication with public N35",
       experiment="one-bit public-constant/carry XOR predicate fusion vs unchanged prior best, eight matched compiler seeds",
       old_baseline=HISTORICAL[base],
       seeds=list(SEEDS),optimization_level=1,target_backend="ibm_fez",
       exact_complex_source_gate_proofs_required=True,
       limit_native_cz=800,limit_native_depth=2000,
       true_order_not_used=True,private_factors_not_used=True,
       precalculated_orbits_not_used=True,
       qpu_jobs_submitted=0,
       quantum_runtime_used=False,paid_runtime_used=False,
       seed_pairs=[],success=False,status='STARTED')
    def save():
        dest.write_text(json.dumps(receipt,indent=2,default=str)+'\n')
    save()
    try:
        old_qc,new_qc,proof=prove_sources_before_target(base)
        receipt['all_source_unitary_proofs']=proof
        receipt['status']='ALL_SOURCE_COMPLEX_PHASES_PROVED_BEFORE_TARGET'
        save()
        token=os.environ.get('IBM_QUANTUM_API_KEY','').strip()
        service=QiskitRuntimeService(channel='ibm_quantum_platform',
            plans_preference=['open'],**({'token':token} if token else {}))
        backend=service.backend('ibm_fez')
        if getattr(backend,'simulator',False) or backend.num_qubits<32:
            raise RuntimeError('IBM Fez backend is not suitable for read-only native target compiling')
        receipt['backend_qubits']=int(backend.num_qubits)
        receipt['status']='COMPILING_8_MATCHED_CPU_ONLY'
        save()
        for seed in SEEDS:
            pm=generate_preset_pass_manager(
                backend=backend,optimization_level=1,
                seed_transpiler=seed)
            old=compile_isa_target(pm,old_qc)
            fused=compile_isa_target(pm,new_qc)
            diff=dict(cz=fused['cz']-old['cz'],
                      depth=fused['depth']-old['depth'])
            row=dict(seed=seed,old_neither=old,
                fused_constant=fused,
                difference_fused_minus_old=diff,
                paired_strict_improvement_both=(diff['cz']<0 and diff['depth']<0),
                device_feasible_old=(old['cz']<=800 and old['depth']<=2000),
                device_feasible_fused=(fused['cz']<=800 and fused['depth']<=2000))
            receipt['seed_pairs'].append(row)
            save()
            print('N35 PUBLIC CONSTANT FUSION MATCHED SEED',base,seed,
                'old CZ/depth',old['cz'],old['depth'],
                'new CZ/depth',fused['cz'],fused['depth'],
                'delta',diff['cz'],diff['depth'],
                'joint_win',row['paired_strict_improvement_both'],
                'physical_feasible',row['device_feasible_fused'],
                'ZERO QPU',flush=True)
        summary=aggregate(receipt['seed_pairs'])
        anchor=next(p for p in receipt['seed_pairs'] if p['seed']==8776)
        expected=HISTORICAL[base]
        exact_anchor=(anchor['old_neither']['cz']==expected['cz'] and
                      anchor['old_neither']['depth']==expected['depth'])
        summary['original_8776_anchor_exact_reproduction']=exact_anchor
        summary['backend_drift_inconclusive_if_anchor_changed']=not exact_anchor
        summary['robust_per_base_pass']=bool(
            exact_anchor and summary['joint_wins_at_least_six_of_eight']
            and summary['both_medians_negative'])
        summary['all_new_layouts_hardware_infeasible']=all(
            not p['device_feasible_fused'] for p in receipt['seed_pairs'])
        summary['all_old_layouts_hardware_infeasible']=all(
            not p['device_feasible_old'] for p in receipt['seed_pairs'])
        receipt.update(status='COMPILE_SUCCESS',success=True,
            full_eight_pair_seed_series_completed=True,summary=summary,
            qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print('N35 PUBLIC CONSTANT FUSION EIGHT MATCHED SEED SUMMARY',
            base,json.dumps(summary,sort_keys=True),'NO QPU',flush=True)
        return 0
    except Exception as exc:
        receipt.update(status='FAIL',success=False,
            error_type=type(exc).__name__,error_message=str(exc)[:1800],
            exception_trace=traceback.format_exc()[-2600:],
            qpu_jobs_submitted=0,quantum_runtime_used=False)
        save()
        print('N35 PUBLIC CONSTANT FUSION FAILED',base,
            type(exc).__name__,str(exc)[:800],
            traceback.format_exc()[-1200:],'NO QPU',flush=True)
        return 1


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',type=int,required=True,choices=BASES)
    args=ap.parse_args()
    raise SystemExit(main(args.base))
