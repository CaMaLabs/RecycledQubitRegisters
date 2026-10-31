#!/usr/bin/env python3
"""Local-only, phase-sensitive Gidney-adder and whole N35 resource audit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap

import qrr_gidney_mbu_adder as adder

SAMPLE_CONSTANTS = (1, 2, 3, 5, 17, 23, 29, 35, 43, 63)


@contextmanager
def patch_adders(src, replacement):
    old = src.oldsel.old
    best = src.oldsel.best
    saved = old.one_bit_bypass_constant_add, best.constant_add_from_prefix_carry
    # Both references matter: the positive branch caches the original function.
    old.one_bit_bypass_constant_add = replacement
    best.constant_add_from_prefix_carry = replacement
    try:
        yield
    finally:
        old.one_bit_bypass_constant_add, best.constant_add_from_prefix_carry = saved


def constant_add(qc, target, value, controls, carry, chain):
    adder.append_adder(qc, target, value, controls, carry[:3])


def composition_proof(src):
    """Check clean-entry contracts and collapsed ideal adders in actual powers.

    Standalone exhaustive Kraus checks establish each replacement channel.
    Here all 768 control/work inputs verify their preconditions at actual call
    boundaries; full branch enumeration of hundreds of MBU bits is not claimed.
    """
    results = []
    for power in (2, 4, 8, 11, 16, 29):
        calls = []
        original = src.oldsel.old.one_bit_bypass_constant_add

        def record(qc, target, value, controls, carry, chain):
            start = len(qc.data)
            original(qc, target, value, controls, carry, chain)
            calls.append((start, len(qc.data), list(target), value, list(controls), list(carry)))

        with patch_adders(src, record):
            qc, regs, _ = src.source_registers()
            src.oldsel.primitive.predicate(qc, regs['work'], 35, regs['valid'][0],
                                        regs['carry'], regs['scratch'], geq=False)
            src.emit_public_controlled_power(qc, regs, power)
            src.oldsel.primitive.predicate(qc, regs['work'], 35, regs['valid'][0],
                                        regs['carry'], regs['scratch'], geq=False)
        idx, instructions, counts = src.previous.actual_complex_instructions(qc)
        calls = {start:(end, [idx[q] for q in t], v, [idx[q] for q in c],
                       [idx[q] for q in clean]) for start,end,t,v,c,clean in calls}
        contracts = 0
        for enabled in (0, 1):
            for y in range(64):
                state = enabled << idx[regs['phase'][0]]
                state |= sum((y >> i & 1) << idx[q] for i,q in enumerate(regs['work']))
                expected, expected_phase = src.previous.evolve_basis(instructions, state)
                phase = 1+0j
                cursor = 0
                while cursor < len(instructions):
                    if cursor in calls:
                        end, target, value, controls, clean = calls[cursor]
                        assert all(not (state >> p & 1) for p in clean)
                        before = sum((state >> p & 1) << i for i,p in enumerate(target))
                        after = (before + (value if all(state >> p & 1 for p in controls) else 0)) % (1 << len(target))
                        for i,p in enumerate(target):
                            state = (state & ~(1 << p)) | ((after >> i & 1) << p)
                        cursor = end
                        contracts += 1
                    else:
                        positions, table = instructions[cursor]
                        local = sum((state >> p & 1) << i for i,p in enumerate(positions))
                        after, factor = table[local]
                        phase *= factor
                        for i,p in enumerate(positions):
                            state ^= ((local ^ after) >> i & 1) << p
                        cursor += 1
                assert state == expected and abs(phase - expected_phase) < 1e-12
                wanted = power*y % 35 if enabled and y < 35 else y
                got = sum((state >> idx[q] & 1) << i for i,q in enumerate(regs['work']))
                assert got == wanted and abs(phase-1) < 1e-12
                aux = [q for name,qs in regs.items() if name not in ('phase','work') for q in qs]
                assert all(not (state >> idx[q] & 1) for q in aux)
        results.append(dict(power=power, inputs=128, add_calls=len(calls),
                            clean_entry_contract_checks=contracts, exact_phase=True,
                            whole_instrument_equivalence_by_composition=True))
    return results


def coherent_qiskit_checks():
    rows = []
    for k in SAMPLE_CONSTANTS:
        qc = QuantumCircuit(10)
        m = adder.append_adder(qc, list(range(6)), k, [6], list(range(7,10)))
        initial = {x:(1j**x.bit_count()) / math.sqrt(128) for x in range(128)}
        expected = {(x & ~63) | (((x & 63)+k*(x >> 6 & 1)) % 64): a/math.sqrt(1 << m)
                    for x,a in initial.items()}
        worst = 0.0
        for transcript in range(1 << m):
            actual, measurements = adder.sparse_qiskit_branch(qc, initial, transcript)
            assert measurements == m and actual.keys() == expected.keys()
            overlap = sum(expected[x].conjugate()*actual[x] for x in expected)
            phase = overlap/abs(overlap)
            error = max(abs(actual[x]-phase*expected[x]) for x in expected)
            assert error < 1e-12
            worst = max(worst, error)
        rows.append(dict(n=6, value=k, branches=1 << m, max_amplitude_error=worst))
    return rows


def recursive_counts(qc):
    counts = Counter()
    for ins in qc.data:
        if ins.operation.name == 'if_else':
            counts['if_else'] += 1
            branches = [recursive_counts(b) for b in ins.operation.blocks if b is not None]
            for name in set().union(*(b.keys() for b in branches)):
                counts[name] += max(b.get(name, 0) for b in branches)
        else:
            counts[ins.operation.name] += 1
    return dict(sorted(counts.items()))


def structural_depth(qc):
    """Longest dependency path, recursively charging each classical branch.

    Unit instruction weights and one extra step per decision. This is a
    structural metric, not scheduled wall time or a measurement-latency model.
    """
    clock = {b:0 for b in list(qc.qubits) + list(qc.clbits)}
    for ins in qc.data:
        operands = list(ins.qubits) + list(ins.clbits)
        weight = 1
        if ins.operation.name == 'if_else':
            weight += max(structural_depth(b) for b in ins.operation.blocks if b is not None)
        end = max((clock[b] for b in operands), default=0) + weight
        for b in operands:
            clock[b] = end
    return max(clock.values(), default=0)


def prune_idle(qc):
    scratch = next(r for r in qc.qregs if r.name == 'scratch')
    assert not any(q in scratch for ins in qc.data for q in ins.qubits)
    result = QuantumCircuit(*(r for r in qc.qregs if r.name != 'scratch'), *qc.cregs)
    for ins in qc.data:
        result.append(ins.operation, ins.qubits, ins.clbits)
    assert result.num_qubits == 23 and result.num_clbits == qc.num_clbits
    assert list(result.data) == list(qc.data)
    return result


def scaling():
    rows = []
    for n in (6, 16, 64, 256, 1024, 2048):
        patterns = dict(one=1, alternating=sum(1 << i for i in range(0,n,2)),
                        all_ones=(1 << n)-1)
        for pattern,k in patterns.items():
            for variant in ('clean3','dirty2'):
                for controlled in (False,True):
                    circuit, t, c, dirty, ctrl = adder.make_adder(n,k,controlled,variant)
                    lower = adder.lower_ops(circuit)
                    tofs = sum(op.kind in ('X','ZIF') and
                               sum(bool(p.qubits) for p in op.controls)+(op.kind=='X') == 3
                               for op in lower)
                    rows.append(dict(n=n, pattern=pattern, variant=variant, controlled=controlled,
                        clean_workspace=len(c), dirty_workspace=len(dirty), control_qubits=len(ctrl),
                        upstream_toffoli_style=circuit.count_tofs(), lowered_toffoli_style=tofs,
                        lowered_ops=len(lower), measurement_reset_pairs=sum(op.kind=='MX' for op in lower),
                        not_RSA_or_modular_multiply_resource_estimate=True))
    return rows


def run(root, out, compile_requested, plan_path=None):
    start = time.perf_counter()
    out = Path(out)
    out.mkdir(parents=True,exist_ok=True)
    plan = Path(plan_path) if plan_path is not None else out / 'audit_plan.json'
    result = dict(status='STARTED', external_spend=0, qpu_jobs=0,
                  hosted_ci_requested=False, rsa2048_broken=False,
                  upstream=adder.load_upstream(root),
                  plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
                  environment=dict(python=platform.python_version(), qiskit=qiskit.__version__),
                  branch_proofs=[], compile_requested=compile_requested)
    def checkpoint():
        result['elapsed_seconds'] = time.perf_counter()-start
        (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    for variant,widths in (('clean3',range(1,7)),('dirty2',range(1,5))):
        for n in widths:
            for k in range(1 << n):
                result['branch_proofs'].append(adder.exact_branch_proof(n,k,variant))
            print(f'branch proof {variant} n={n} complete', flush=True)
            checkpoint()
    for k in SAMPLE_CONSTANTS:
        result['branch_proofs'].append(adder.exact_branch_proof(6,k,'dirty2'))
    try:
        adder.exact_branch_proof(6,23,omit_phase=True)
    except AssertionError:
        result['missing_phase_correction_mutation_rejected'] = True
    else:
        raise AssertionError('Proof did not detect missing phase correction')
    result['coherent_qiskit'] = coherent_qiskit_checks()
    print('coherent Qiskit branch checks complete', flush=True)
    result['scaling'] = scaling()
    import qrr_n35_true_recycled_phase_feedforward as src
    src.configure_original_public_arithmetic()
    result['composition'] = composition_proof(src)
    print('whole power composition proofs complete', flush=True)
    result['whole_circuit'] = []
    checkpoint()
    for base in (2,8):
        circuits = {}
        for arm in ('baseline','mbu'):
            if arm == 'mbu':
                with patch_adders(src, constant_add):
                    full = src.build_dynamic_source(base,4)[0]
            else:
                full = src.build_dynamic_source(base,4)[0]
            circuits[arm] = prune_idle(full)
        row = dict(base=base, phase_bits=4,
            source={arm:dict(qubits=q.num_qubits, classical_bits=q.num_clbits,
                            recursive_worst_branch_ops=recursive_counts(q),
                            structural_depth=structural_depth(q)) for arm,q in circuits.items()}, paired=[])
        result['whole_circuit'].append(row)
        if compile_requested:
            for seed in (509,1223,4093,8776):
                pair = dict(seed=seed)
                for arm,q in circuits.items():
                    isa = transpile(q, basis_gates=['x','sx','rz','cz','id'],
                        coupling_map=CouplingMap.from_line(23), initial_layout=list(range(23)),
                        optimization_level=1, seed_transpiler=seed)
                    ops = recursive_counts(isa)
                    pair[arm] = dict(cz=ops.get('cz',0), structural_depth=structural_depth(isa),
                                    recursive_worst_branch_ops=ops, qubits=isa.num_qubits)
                pair['win_both'] = all(pair['mbu'][k] < pair['baseline'][k]
                                       for k in ('cz','structural_depth'))
                row['paired'].append(pair)
                print(f'compile base={base} seed={seed}: {pair["baseline"]["cz"]} -> {pair["mbu"]["cz"]} CZ; win={pair["win_both"]}',flush=True)
                checkpoint()
    pairs = [p for row in result['whole_circuit'] for p in row['paired']]
    result['primary_gate_passed'] = len(pairs)==8 and all(p['win_both'] for p in pairs)
    result['status'] = 'COMPLETE'
    checkpoint()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',required=True)
    parser.add_argument('--out',default='results/gidney_mbu_20261031')
    parser.add_argument('--plan',default='results/gidney_mbu_20261031/audit_plan.json')
    parser.add_argument('--compile',action='store_true')
    args = parser.parse_args()
    run(args.upstream,args.out,args.compile,args.plan)
