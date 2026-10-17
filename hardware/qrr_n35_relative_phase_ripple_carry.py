#!/usr/bin/env python3
"""Phase-exact RCCX temporary ripple-CARRY comparator for N35.

Research lead Chase Lunsford / CaMaLabs. One change to the verified best
public N35 source: temporary comparator carry-compute CCXs become RCCX,
uncompute uses exact inverse. Semantic flag control and all modular arithmetic,
shortened public thresholds, register controls and clean helpers unchanged.
Actual emitted operator-phase verification is MANDATORY before target reads.
IBM Fez native compilation on CPU only, ZERO QPU jobs/runtime.
"""
from __future__ import annotations
import argparse
import json
import os
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

import qrr_n35_single_modmul_ripple_toffoli as primitive
import qrr_n35_latched_controls_single_modmul as verified
import qrr_n35_public_prefix_carry_single_modmul as best

N = 35
BITS = 6
REV = "qrr-n35-relative-phase-ripple-carry-v1-20261017"
ROOT = Path("results/ibm_shor35_relative_phase_ripple")
BASELINES = {
    2: dict(cz=12517, depth=32312, primitive=1817, logical=32),
    8: dict(cz=12680, depth=33138, primitive=1883, logical=32),
}
EPS = 1e-8


def phase_aware_ripple_predicate(qc,x,threshold,flag,carry,chain,
                                  controls=(),geq=True):
    """Same public Boolean ripple compare; temporary CCXs use RCCX/adjoint.

    A reversible carry computation U, an unchanged semantic multi-X flag
    toggle using final carry, followed by exact U-dagger. Temporary carries
    and every intermediate control are unchanged between U and U-dagger
    except the geq=False NOT/NOT pair, which restores itself. This supports
    coherent superposition only if full phase checks return +1.
    """
    x=list(x)
    carry=list(carry)
    controls=list(controls)
    n=len(x)
    if len(carry)!=n or not (1<=threshold<(1<<n)):
        raise AssertionError("Bad threshold/width in phase ripple compare")
    const=(1<<n)-threshold
    rccx=RCCXGate()
    inverse=rccx.inverse()
    # Independently confirm actual inverse operator, irrespective of gate name.
    assert np.allclose(
        np.asarray(Operator(inverse).data) @ np.asarray(Operator(rccx).data),
        np.eye(8),atol=EPS)
    for i in range(n):
        b=(const>>i)&1
        if i==0:
            if b: qc.cx(x[i],carry[i])
        elif b==0:
            qc.append(rccx,[x[i],carry[i-1],carry[i]])
        else:
            qc.cx(x[i],carry[i])
            qc.cx(carry[i-1],carry[i])
            qc.append(rccx,[x[i],carry[i-1],carry[i]])
    if not geq:
        qc.x(carry[-1])
    # Source multi_x remains the VERIFIED original exact X/CX/CCX version.
    primitive.multi_x(qc,controls+[carry[-1]],flag,chain)
    if not geq:
        qc.x(carry[-1])
    for i in reversed(range(n)):
        b=(const>>i)&1
        if i==0:
            if b: qc.cx(x[i],carry[i])
        elif b==0:
            qc.append(inverse,[x[i],carry[i-1],carry[i]])
        else:
            qc.append(inverse,[x[i],carry[i-1],carry[i]])
            qc.cx(carry[i-1],carry[i])
            qc.cx(x[i],carry[i])


primitive.predicate = phase_aware_ripple_predicate


def _gate_table(gate, cache):
    """Extract EXACT monomial basis permutation + complex phase from Operator.

    Fail for unknown non-unitary or non-monomial gates. In particular, do not
    mistakenly interpret RCCX as an ordinary CCX with no phase.
    """
    key = gate.name
    if key in cache:
        return cache[key]
    if key not in {"x","cx","ccx","rccx","rccx_dg"}:
        raise AssertionError("Unrecognized gate type: "+key)
    matrix = np.asarray(Operator(gate).data, dtype=complex)
    n = gate.num_qubits
    if matrix.shape != (1 << n, 1 << n):
        raise AssertionError("Incorrect operator dimension")
    table = []
    for old_basis in range(1 << n):
        nonzero = np.flatnonzero(np.abs(matrix[:, old_basis]) > EPS)
        if len(nonzero) != 1:
            raise AssertionError(f"Non-monomial gate {key} column={old_basis}")
        new_basis = int(nonzero[0])
        amplitude = complex(matrix[new_basis, old_basis])
        if abs(abs(amplitude) - 1) > EPS:
            raise AssertionError("Gate is not a basis-state permutation phase")
        table.append((new_basis, amplitude))
    cache[key] = tuple(table)
    return cache[key]


def actual_complex_instructions(qc):
    ix = {bit: i for i, bit in enumerate(qc.qubits)}
    instructions = []
    gate_counts = {}
    cache = {}
    for item in qc.data:
        name = item.operation.name
        operands = tuple(ix[q] for q in item.qubits)
        if len(set(operands)) != len(operands):
            raise AssertionError("Overlapping gate operands: "+name)
        mapping = _gate_table(item.operation, cache)
        gate_counts[name] = gate_counts.get(name, 0) + 1
        instructions.append((operands, mapping))
    return ix, instructions, gate_counts


def evolve_basis(instructions, input_state):
    """Interpret the ACTUAL emitted gates on a basis input WITH complex phases."""
    state = int(input_state)
    phase = 1.0 + 0.0j
    for operands, table in instructions:
        local = sum(((state >> pos) & 1) << i for i, pos in enumerate(operands))
        local_new, factor = table[local]
        phase *= factor
        changes = local ^ local_new
        for i, pos in enumerate(operands):
            if (changes >> i) & 1:
                state ^= 1 << pos
    return state, phase


def check_exact_phase(phase, description):
    if abs(phase - (1.0 + 0.0j)) > EPS:
        raise AssertionError(description + f": nontrivial residual complex phase {phase!r}")


def exhaustive_comparator_phase_proof():
    """Actual source operators; 42,672 exact basis +1-phase checks."""
    count=0
    circuits=0
    gate_totals={}
    for n in range(1,BITS+1):
        for threshold in range(1,1<<n):
            for geq in (True,False):
                enable=QuantumRegister(1,'enable')
                values=QuantumRegister(n,'values')
                flag=QuantumRegister(1,'flag')
                carry=QuantumRegister(n,'carry')
                scratch=QuantumRegister(BITS+3,'scratch')
                qc=QuantumCircuit(enable,values,flag,carry,scratch)
                phase_aware_ripple_predicate(qc,values,threshold,
                    flag[0],carry,scratch,controls=[enable[0]],geq=geq)
                idx,inst,counts=actual_complex_instructions(qc)
                for name,num in counts.items():
                    gate_totals[name]=gate_totals.get(name,0)+num
                epos=idx[enable[0]]
                fpos=idx[flag[0]]
                vpos=[idx[q] for q in values]
                clean=[idx[q] for register in (carry,scratch) for q in register]
                circuits+=1
                for x in range(1<<n):
                    for enabled in (0,1):
                        for startflag in (0,1):
                            input_bits=(enabled<<epos)|(startflag<<fpos)
                            for i,p in enumerate(vpos):
                                input_bits|=((x>>i)&1)<<p
                            final,phase=evolve_basis(inst,input_bits)
                            wanted=startflag^int(bool(enabled) and (
                               x>=threshold if geq else x<threshold))
                            actual=(final>>fpos)&1
                            same_x=sum(((final>>p)&1)<<i for i,p in enumerate(vpos))
                            if actual!=wanted or same_x!=x or ((final>>epos)&1)!=enabled:
                                raise AssertionError(json.dumps(dict(
                                    stage='public comparator',n=n,threshold=threshold,
                                    geq=geq,x=x,enabled=enabled,startflag=startflag,
                                    expected_flag=wanted,actual_flag=actual,
                                    actual_input=same_x)))
                            if any((final>>p)&1 for p in clean):
                                raise AssertionError(
                                  f'Comparator dirty carry or scratch n={n} t={threshold} x={x}')
                            check_exact_phase(phase,
                               f'Compare n={n} t={threshold} x={x} geq={geq} enabled={enabled} flag={startflag}')
                            count+=1
    assert circuits==240 and count==42672,(circuits,count)
    assert gate_totals.get('rccx',0)>0,gate_totals
    return dict(pass_all=True,actual_gate_comparator_cases=count,
                comparator_source_circuits=circuits,
                rccx_inside_comparator_present=True,
                exact_complex_phase_plus_one=True,all_carry_scratch_clean=True,
                controls_inputs_and_flags_unchanged_except_expected_predicate=True,
                comparator_total_source_gate_distribution=gate_totals)


def exhaustive_modadd_phases(public_constants):
    per_constant=[]
    cases=0
    for k in sorted(public_constants):
        enable=QuantumRegister(1,'enable')
        target=QuantumRegister(BITS,'target')
        wrap=QuantumRegister(1,'wrap')
        carry=QuantumRegister(BITS,'carry')
        scratch=QuantumRegister(BITS+3,'scratch')
        qc=QuantumCircuit(enable,target,wrap,carry,scratch)
        best.optimized_modadd(qc,target,k,N,[enable[0]],wrap[0],carry,scratch)
        idx,inst,counts=actual_complex_instructions(qc)
        epos=idx[enable[0]]
        tpos=[idx[x] for x in target]
        aux=[idx[x] for reg in (wrap,carry,scratch) for x in reg]
        tested=0
        for enabled in (0,1):
            for x in range(64 if not enabled else N):
                initial=enabled << epos
                for b,pos in enumerate(tpos):
                    initial |= ((x>>b)&1)<<pos
                final,phase=evolve_basis(inst,initial)
                got=sum(((final>>pos)&1)<<b for b,pos in enumerate(tpos))
                expected=(x+k)%N if enabled else x
                if got!=expected or ((final>>epos)&1)!=enabled:
                    raise AssertionError(json.dumps(dict(stage='modadd',
                        k=k,enabled=enabled,x=x,got=got,expected=expected)))
                if any((final>>pos)&1 for pos in aux):
                    raise AssertionError(f"Modadd dirty auxiliary k={k} x={x} control={enabled}")
                check_exact_phase(phase,f"Modadd k={k} x={x} enabled={enabled}")
                cases+=1
                tested+=1
        if tested!=99:raise AssertionError("Wrong modular addition case count")
        per_constant.append(dict(public_constant=k,source_gates=counts,
            actual_gate_cases=tested,clean_aux=True,exact_phase=True))
    assert len(per_constant)==16 and cases==1584
    return dict(pass_all=True, source_gate_cases=cases,
        unique_constants=len(per_constant), per_constant=per_constant,
        clean_helpers=True, exact_complex_phase_plus_one=True,
        disabled_identity_full_six_bit_inputs=True)


def exhaustive_full_multiplier_phases(qc,regs,base):
    idx,inst,counts=actual_complex_instructions(qc)
    ctrl=idx[regs['phase'][0]]
    work=[idx[x] for x in regs['work']]
    aux=[idx[x] for name in ('acc','wrap','valid','carry','scratch','active','enable')
         for x in regs[name]]
    assert len(work)==6 and len(aux)==25
    assert len(qc.qubits)==32
    tested=0
    for c in (0,1):
        for y in range(64):
            state=c<<ctrl
            for b,p in enumerate(work):
                state |= ((y>>b)&1)<<p
            final,phase=evolve_basis(inst,state)
            got=sum(((final>>p)&1)<<b for b,p in enumerate(work))
            wanted=(base*y)%N if c and y<N else y
            if got!=wanted or ((final>>ctrl)&1)!=c:
                raise AssertionError(json.dumps(dict(stage='fullmul',
                    base=base,c=c,y=y,actual=got,expected=wanted)))
            if any((final>>p)&1 for p in aux):
                raise AssertionError(f"Full multiplier auxiliaries dirty base={base}, y={y}, c={c}")
            check_exact_phase(phase,f"Full mul base={base} y={y} c={c}")
            tested+=1
    assert tested==128
    return dict(pass_all=True,full_residue_control_basis_cases=tested,
        output_equals_public_modular_multiplication=True,
        all_25_auxiliaries_clean=True,control_unmodified=True,
        disabled_invalid_states_identity=True,
        exact_complex_output_phase_plus_one=True,
        quantum_source_gate_counts=counts,source_instruction_count=len(inst))


def source_constants():
    public=set()
    for base in (2,8):
        inv=pow(base,-1,N)
        for i in range(BITS):
            public.add((base*(1<<i))%N)
            public.add((-inv*(1<<i))%N)
    public.discard(0)
    return public


def main(base):
    assert base in (2,8)
    ROOT.mkdir(parents=True,exist_ok=True)
    target=ROOT/f"qrr_n35_relative_phase_clean_vchain_base{base}.json"
    receipt=dict(revision=REV,
        research_lead='Chase Lunsford / CaMaLabs',
        date_utc=datetime.now(timezone.utc).isoformat(),
        preregistration='docs/QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_PREREG.md',
        N=N,base=base,kind='one public full-residue controlled modular multiplier',
        original_compiled_baseline=BASELINES[base],
        frozen_transpiler_optimization_level=1,
        frozen_transpiler_seed=8776,
        read_only_target='ibm_fez',
        native_cz_device_limit=800,native_depth_device_limit=2000,
        relative_phase_rccx_only_inside_temporary_comparator_carries=True,
        actual_instruction_complex_phase_proof_required=True,
        true_multiplicative_order_not_injected=True,
        orbit_not_precomputed=True,
        qpu_jobs_submitted=0,paid_runtime_used=False,
        no_quantum_runtime_submission=True,
        success=False,status='STARTED')
    def save():target.write_text(json.dumps(receipt,indent=2,default=str)+'\n')
    save()
    try:
        receipt['comparator_phase_proof']=exhaustive_comparator_phase_proof()
        save()
        print("RIPPLE COMPARATOR PHASE-SENSITIVE OPERATOR PROOFS",base,
            receipt['comparator_phase_proof']['actual_gate_comparator_cases'],
            "exact +1 PHASE all carry/scratch CLEAN",flush=True)
        receipt['public_modadd_phase_proof']=exhaustive_modadd_phases(source_constants())
        save()
        print("PUBLIC MODADD PHASE-SENSITIVE ACTUAL GATE PROOFS",base,
            receipt['public_modadd_phase_proof']['source_gate_cases'],
            "all helpers CLEAN +1 PHASE",flush=True)
        qc,regs=verified.build(base)
        receipt['full_modmul_phase_proof']=exhaustive_full_multiplier_phases(qc,regs,base)
        receipt['source_logical_qubits']=qc.num_qubits
        receipt['status']='PHASE_CORRECT_AND_CLEAN'
        save()
        print("COMPLETE PUBLIC MULTIPLIER PHASE-SENSITIVE GATE PROOF",base,
            receipt['full_modmul_phase_proof']['full_residue_control_basis_cases'],
            "all 25 helpers CLEAN exact +1 PHASE",
            "source gate distribution",receipt['full_modmul_phase_proof']['quantum_source_gate_counts'],flush=True)
        token=os.environ.get('IBM_QUANTUM_API_KEY','').strip()
        service=QiskitRuntimeService(channel='ibm_quantum_platform',
            plans_preference=['open'],**({'token':token} if token else {}))
        backend=service.backend('ibm_fez')
        if getattr(backend,'simulator',False):
            raise RuntimeError('Not a physical target backend')
        if backend.num_qubits < qc.num_qubits:
            raise RuntimeError('Target too narrow for circuit')
        receipt['backend_qubits']=backend.num_qubits
        receipt['status']='COMPILING'
        save()
        pass_manager=generate_preset_pass_manager(
            backend=backend,optimization_level=1,seed_transpiler=8776)
        t0=time.perf_counter()
        native=pass_manager.run(qc)
        elapsed=time.perf_counter()-t0
        ops={str(k):int(v) for k,v in native.count_ops().items()}
        cz=ops.get('cz',0)
        depth=native.depth()
        receipt.update(success=True,status='COMPILE_SUCCESS',
            native_cz=cz,native_depth=depth,native_size=native.size(),
            compiled_device_width=native.num_qubits,
            compiled_native_ops=ops,compile_seconds=elapsed,
            engineering_both_costs_improve=(
                cz<BASELINES[base]['cz'] and depth<BASELINES[base]['depth']),
            device_feasibility_gate=(
                cz<=800 and depth<=2000),
            native_cz_delta=cz-BASELINES[base]['cz'],
            native_depth_delta=depth-BASELINES[base]['depth'])
        save()
        print("RELATIVE_PHASE RIPPLE N35 BASE",base,
              "CZ",cz,"DEPTH",depth,
              "COMPARED_CZ",BASELINES[base]['cz'],
              "COMPARED_DEPTH",BASELINES[base]['depth'],
              "ENGINEERING",receipt['engineering_both_costs_improve'],
              "HARDWARE",receipt['device_feasibility_gate'],
              "ZERO QPU",flush=True)
        return 0
    except Exception as exc:
        receipt.update(success=False,status='FAIL',
            error_type=type(exc).__name__,error_message=str(exc)[:1600],
            error_stack=traceback.format_exc()[-2800:],
            qpu_jobs_submitted=0)
        save()
        print("RELATIVE_PHASE RIPPLE PHASE_GATE_OR_COMPILER_FAIL",
            base,type(exc).__name__,str(exc)[:750],
            traceback.format_exc()[-1900:],"ZERO QPU",flush=True)
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=int,required=True,choices=[2,8])
    raise SystemExit(main(parser.parse_args().base))
