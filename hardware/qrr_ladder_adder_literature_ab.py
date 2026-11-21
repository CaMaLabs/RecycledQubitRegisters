#!/usr/bin/env python3
"""Exact ladder-to-adder reduction (2610.34446 Lemma 3) in existing N35.

Uses the direct small-width ladder, as allowed by the paper, NOT its optimized
short-forest implementation. Includes a Pascal borrowed-register echo reference
for validating the endpoint algebra; no asymptotic optimality is claimed.
Default target is an explicitly synthetic 23-site line; no IBM account/QPU.
"""
from __future__ import annotations
import argparse
import json
import math
import statistics
from contextlib import contextmanager
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.transpiler import CouplingMap


def ladder_adder(qc, a, b):
    """Seven stages of Eq. (5); little-endian (a,b)->(a,a+b)."""
    n = len(a)
    assert n == len(b) and not set(a) & set(b)
    for i in range(n): qc.cx(a[i], b[i])
    for i in range(n-1, 0, -1): qc.cx(a[i-1], a[i])
    for i in range(1, n): qc.ccx(b[i-1], a[i-1], a[i])
    for i in range(n): qc.cx(a[i], b[i])
    for i in range(n-1, 0, -1):
        qc.x(b[i-1]); qc.ccx(b[i-1], a[i-1], a[i]); qc.x(b[i-1])
    for i in range(1, n): qc.cx(a[i-1], a[i])
    for i in range(n): qc.cx(a[i], b[i])


def pascal_echo(qc, endpoints, borrowed, control_blocks, which):
    """Eqs. (14)-(17), exact but deliberately naive control-product synthesis.

    Borrowed inputs may be arbitrary and entangled; four XOR additions restore
    them. Endpoints and borrowed must be disjoint. MCX cost is charged later.
    """
    m = len(endpoints)
    assert len(borrowed) == m and len(control_blocks) == m-1
    assert not set(endpoints) & set(borrowed)
    terms = []
    for i in range(1, m):
        for j in range(i):
            coefficient = (math.comb(i, j) if which == 0 else
                           (math.comb(i-1, j-1) if j else 0)) & 1
            if coefficient:
                controls = [z for block in control_blocks[j:i] for z in block]
                terms.append((i, j, controls))
    def add_A():
        for i, j, controls in terms: qc.mcx(controls+[borrowed[j]], endpoints[i])
    def add_DA():
        for i, j, controls in terms: qc.mcx(controls+[endpoints[j]], borrowed[i-1])
    add_A(); add_DA(); add_A(); add_DA()


def basis_permutation(qc, value):
    """Interpret emitted exact X/CX/CCX/MCX gates; all have amplitude +1."""
    for inst in qc.data:
        name = inst.operation.name
        if name not in ('x', 'cx', 'ccx', 'mcx', 'mcx_gray'):
            raise ValueError('Unexpected nonpermutation instruction: '+name)
        positions = [qc.find_bit(q).index for q in inst.qubits]
        if all(value >> p & 1 for p in positions[:-1]): value ^= 1 << positions[-1]
    return value


def self_tests():
    cases = 0
    for n in range(1, 7):
        qc = QuantumCircuit(2*n)
        ladder_adder(qc, list(range(n)), list(range(n, 2*n)))
        for a in range(1 << n):
            for b in range(1 << n):
                assert basis_permutation(qc, a+(b << n)) == a+(((a+b) % (1 << n)) << n)
                cases += 1
    echo_cases = 0
    # All dirty Z and control states, not just clean borrowed registers.
    m = 3
    for which in (0, 1):
        qc = QuantumCircuit(2*m+m-1)
        pascal_echo(qc, list(range(m)), list(range(m, 2*m)),
                    [[2*m+i] for i in range(m-1)], which)
        for value in range(1 << qc.num_qubits):
            controls = [(value >> (2*m+i)) & 1 for i in range(m-1)]
            x = [(value >> i) & 1 for i in range(m)]
            expected = value
            for i in range(1, m):
                delta = 0
                for j in range(i):
                    parity = (math.comb(i,j) if which == 0 else
                              (math.comb(i-1,j-1) if j else 0)) & 1
                    delta ^= parity*x[j]*math.prod(controls[j:i])
                expected ^= delta << i
            assert basis_permutation(qc, value) == expected
            echo_cases += 1
    return dict(adder_basis_cases=cases, dirty_echo_basis_cases=echo_cases,
                exact_phase_plus_one=True)


def constant_add(qc, target, value, controls, carry, chain):
    import qrr_n35_true_recycled_phase_feedforward as src
    const = int(value) % (1 << len(target))
    # carry is clean on entry: comparator cleanup precedes every add call.
    assert len(carry) == len(target)
    for i in range(len(target)):
        if const >> i & 1: src.oldsel.primitive.multi_x(qc, controls, carry[i], chain)
    ladder_adder(qc, carry, target)
    for i in range(len(target)):
        if const >> i & 1: src.oldsel.primitive.multi_x(qc, controls, carry[i], chain)


@contextmanager
def candidate_patch(src):
    # The frozen selected modadd calls old.one_bit_bypass_constant_add for both
    # positive and signed source arms. Restore it even after a failed proof.
    old = src.oldsel.old
    original = old.one_bit_bypass_constant_add
    old.one_bit_bypass_constant_add = constant_add
    try: yield
    finally: old.one_bit_bypass_constant_add = original


def run(compile_circuits=False, bits=(4,), seeds=(509, 1223, 4093, 8776)):
    import qrr_n35_true_recycled_phase_feedforward as src
    import qrr_n35_true_recycled_prune_idle_scratch as prune
    result = dict(status='STARTED', qpu_jobs=0, target='synthetic_bidirectional_line_23',
                  paper_optimal_forest_implemented=False, tests=self_tests(),
                  semantics=[], rows=[], compile_requested=compile_circuits)
    src.configure_original_public_arithmetic()
    # Exhaustive standalone controlled powers, including invalid work states,
    # actual complex source semantics, phase +1, and clean auxiliaries.
    for power in (2,4,8,11,16,29):
        with candidate_patch(src): proof = src.phase_exact_public_stage_proof(power)
        result['semantics'].append(dict(power=power, proof=proof))
    for base in (2, 8):
        for precision in bits:
            circuits = {}
            for arm in ('baseline', 'ladder'):
                if arm == 'ladder':
                    with candidate_patch(src): full = src.build_dynamic_source(base, precision)[0]
                else: full = src.build_dynamic_source(base, precision)[0]
                lean, identity = prune.reduction_with_exact_instruction_identity(full, precision)
                assert lean.num_qubits == 23
                circuits[arm] = lean
            row = dict(base=base, bits=precision,
                       source={k: dict(qubits=v.num_qubits, ops=dict(v.count_ops()))
                               for k,v in circuits.items()}, paired=[])
            if compile_circuits:
                for seed in seeds:
                    pair = dict(seed=seed)
                    for arm, circuit in circuits.items():
                        isa = transpile(circuit, basis_gates=['x','sx','rz','cz','id'],
                                        coupling_map=CouplingMap.from_line(23),
                                        initial_layout=list(range(23)),
                                        optimization_level=1, seed_transpiler=seed)
                        pair[arm] = dict(cz=int(isa.count_ops().get('cz',0)), depth=isa.depth())
                    pair['win_both'] = all(pair['ladder'][k] < pair['baseline'][k] for k in ('cz','depth'))
                    row['paired'].append(pair)
                row['wins'] = sum(p['win_both'] for p in row['paired'])
                row['robust_win'] = row['wins'] >= math.ceil(.75*len(seeds))
            result['rows'].append(row)
    result['status'] = 'COMPILE_COMPLETE' if compile_circuits else 'SOURCE_SEMANTICS_PASS'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compile', action='store_true')
    parser.add_argument('--bits', default='4')
    parser.add_argument('--output', default='results/literature_20261030/ladder_adder.json')
    args = parser.parse_args()
    bits = tuple(map(int, args.bits.split(','))); assert set(bits) <= {4,6,8}
    result = run(args.compile, bits)
    dest = Path(args.output); dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], tests=result['tests'],
                          rows=[{k:v for k,v in r.items() if k != 'source'} for r in result['rows']]), indent=2))
