#!/usr/bin/env python3
"""Phase-exact relative-phase Toffoli clean control chains for N35.

Research lead: Chase Lunsford / CaMaLabs.
ONE change to the proven public N35 prefix-carry+shortened-ripple kernel:
RCCX/RCCX inverse instead of CCX for temporary conjunction compute and
uncompute inside reversible multi-X. Final target gate is exact CCX.

Importantly, RCCX alone has nontrivial phases. Verify the ACTUAL source
operators with a monomial-complex-amplitude interpreter on all relevant
basis states, requiring output PHASE +1 and every helper bit cleaned.
CPU-only IBM Fez TARGET read. Absolutely no QPU runtime/submissions.
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
REV = "qrr-n35-clean-vchain-relative-phase-v1-20261017"
ROOT = Path("results/ibm_shor35_relative_phase_vchain")
BASELINES = {
    2: dict(cz=12517, depth=32312, primitive=1817, logical=32),
    8: dict(cz=12680, depth=33138, primitive=1883, logical=32),
}
EPS = 1e-8


def relative_phase_clean_multi_x(qc, ctrl, target, chain):
    """Exact multi-controlled X by U-compute, TRUE CCX target, U-dagger.

    Every temporary conjunction uses relative-phase RCCX and its exact
    adjoint; all other source register operations remain unchanged.
    The scratch chain MUST be initialized clean and fully uncomputed.
    """
    controls = list(ctrl)
    chain = list(chain)
    if target in controls:
        raise AssertionError("Target included in own controls")
    if len(set(controls)) != len(controls):
        raise AssertionError("Duplicate controls")
    n = len(controls)
    if n == 0:
        qc.x(target)
        return
    if n == 1:
        qc.cx(controls[0], target)
        return
    if n == 2:
        qc.ccx(controls[0], controls[1], target)
        return
    need = n - 2
    if len(chain) < need:
        raise AssertionError(f"Need {need} clean scratch qubits")
    if any(q in controls or q == target for q in chain[:need]):
        raise AssertionError("Overlapping control/target/temporary chain")
    compute = RCCXGate()
    uncompute = compute.inverse()
    triples = [(controls[0], controls[1], chain[0])]
    for i in range(2, n - 1):
        triples.append((chain[i-2], controls[i], chain[i-1]))
    if len(triples) != need:
        raise AssertionError("Wrong number of conjunction chain steps")
    for operands in triples:
        qc.append(compute, operands)
    qc.ccx(chain[need-1], controls[-1], target)
    for operands in reversed(triples):
        qc.append(uncompute, operands)


# This is the ONLY patched arithmetic dependency: prior best predicate,
# prefix-carry constant add, modular correction and whole multiplier are
# unmodified and dynamically resolve primitive.multi_x.
primitive.multi_x = relative_phase_clean_multi_x


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


def exhaustive_local_clean_chain():
    total = 0
    count_rccx = 0
    count_inverse = 0
    gate_sizes = {}
    for n in range(9):
        control = QuantumRegister(n, "control") if n else None
        target = QuantumRegister(1, "target")
        scratch = QuantumRegister(BITS + 3, "scratch")
        registers = [target, scratch] if control is None else [control, target, scratch]
        qc = QuantumCircuit(*registers)
        controls = list(control) if control is not None else []
        relative_phase_clean_multi_x(qc, controls, target[0], scratch)
        idx, instr, counts = actual_complex_instructions(qc)
        if n >= 3:
            assert counts.get("rccx",0) == n - 2
            assert counts.get("rccx_dg",0) == n - 2
            assert counts.get("ccx",0) == 1
        else:
            assert counts.get("rccx",0) == 0 and counts.get("rccx_dg",0) == 0
        count_rccx += counts.get("rccx",0)
        count_inverse += counts.get("rccx_dg",0)
        positions = [idx[q] for q in controls]
        target_pos = idx[target[0]]
        aux_pos = [idx[q] for q in scratch]
        gate_sizes[str(n)] = counts
        for control_bits in range(1 << n):
            for target_initial in (0,1):
                initial = target_initial << target_pos
                for i,p in enumerate(positions):
                    initial |= ((control_bits >> i)&1) << p
                actual, phase = evolve_basis(instr, initial)
                expected_target = target_initial ^ int(control_bits == (1 << n) - 1)
                if ((actual >> target_pos)&1) != expected_target:
                    raise AssertionError(f"Local target wrong n={n} bits={control_bits} tgt={target_initial}")
                if any((actual >> p)&1 for p in aux_pos):
                    raise AssertionError(f"Local scratch dirty n={n} bits={control_bits}")
                if any(((actual >> p)&1) != ((control_bits >> i)&1)
                       for i,p in enumerate(positions)):
                    raise AssertionError("Local control was modified")
                check_exact_phase(phase,
                    f"Local n={n} controls={control_bits} target={target_initial}")
                total += 1
    assert total == 1022
    assert count_rccx > 0 and count_inverse == count_rccx
    return dict(pass_all=True, direct_gate_basis_cases=total,
        all_control_sizes_0_through_8=True, all_scratch_clean=True,
        exact_complex_output_phase_plus_one=True,
        local_source_counts=gate_sizes,
        relative_toffolis_observed=count_rccx,
        inverse_relative_toffolis_observed=count_inverse)


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
        preregistration='docs/QRR_N35_RELATIVE_PHASE_CLEAN_VCHAIN_PREREG.md',
        N=N,base=base,kind='one public full-residue controlled modular multiplier',
        original_compiled_baseline=BASELINES[base],
        frozen_transpiler_optimization_level=1,
        frozen_transpiler_seed=8776,
        read_only_target='ibm_fez',
        native_cz_device_limit=800,native_depth_device_limit=2000,
        relative_phase_rccx_only_inside_clean_v_chain=True,
        actual_instruction_complex_phase_proof_required=True,
        true_multiplicative_order_not_injected=True,
        orbit_not_precomputed=True,
        qpu_jobs_submitted=0,paid_runtime_used=False,
        no_quantum_runtime_submission=True,
        success=False,status='STARTED')
    def save():target.write_text(json.dumps(receipt,indent=2,default=str)+'\n')
    save()
    try:
        receipt['local_clean_chain_proof']=exhaustive_local_clean_chain()
        save()
        print("LOCAL PHASE-SENSITIVE V-CHAIN GATE PROOFS",base,
            receipt['local_clean_chain_proof']['direct_gate_basis_cases'],
            "exact +1 PHASE all scratch CLEAN",flush=True)
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
        print("RELATIVE_PHASE N35 KERNEL BASE",base,
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
        print("RELATIVE_PHASE N35 PHASE_GATE_OR_COMPILER_FAIL",
            base,type(exc).__name__,str(exc)[:750],
            traceback.format_exc()[-1900:],"ZERO QPU",flush=True)
        return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=int,required=True,choices=[2,8])
    raise SystemExit(main(parser.parse_args().base))
