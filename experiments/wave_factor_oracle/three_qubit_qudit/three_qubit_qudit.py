#!/usr/bin/env python3
"""Exactly three qubits emulate one 8-level qudit. NumPy only.

The factor demonstration compiles an eight-entry divisibility oracle CLASSICALLY.
It is a gate-level Grover demonstration, not scalable quantum arithmetic or
a quantum factoring speedup. N and the cofactor are classical, not registers.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

ORDER = [0,2,4,6,7,5,3,1]  # logical candidate index -> physical 3-bit label
CANDIDATES = list(range(3,18,2))


def apply_gate(state, op):
    """Little-endian qubits; amplitude index is q2 q1 q0."""
    name, *qubits = op
    out=state.copy()
    if name == 'h':
        bit=1 << qubits[0]
        for j in range(8):
            if not j & bit:
                out[j]=(state[j]+state[j|bit])/math.sqrt(2)
                out[j|bit]=(state[j]-state[j|bit])/math.sqrt(2)
    elif name in ('x','cx','ccx'):
        controls,target=qubits[:-1],qubits[-1]
        for j in range(8):
            dest=j ^ (1 << target) if all(j & (1 << c) for c in controls) else j
            out[dest]=state[j]
    else:
        raise ValueError(f'Unsupported gate {name}')
    return out


def simulate(ops, initial=None):
    state=np.eye(8,dtype=complex)[:,0] if initial is None else initial.copy()
    for op in ops:
        state=apply_gate(state,op)
    return state


def phase_flip(label):
    """Flip exactly one computational basis state, using H, X, CCX."""
    zeros=[q for q in range(3) if not label & (1 << q)]
    return ([('x',q) for q in zeros]+[('h',2),('ccx',0,1,2),('h',2)]
            +[('x',q) for q in reversed(zeros)])


def diffusion():
    # H^3 (I-2|000><000|) H^3 = -(2|s><s|-I).
    # The minus sign is a physically irrelevant global phase per iteration.
    return [('h',q) for q in range(3)]+phase_flip(0)+[('h',q) for q in range(3)]


def oracle_ops(n):
    # Enumerating divisibility already identifies factors classically.
    # This is explicit simulator/circuit construction cost, NOT free arithmetic.
    marked=[j for j,p in enumerate(CANDIDATES) if p < n and n % p == 0]
    return [op for j in marked for op in phase_flip(ORDER[j])], marked


def circuit(n,k):
    if n < 4 or k < 0:
        raise ValueError('Require N >= 4 and iterations >= 0')
    oracle,marked=oracle_ops(n)
    ops=[('h',q) for q in range(3)]
    for _ in range(k):
        ops.extend(oracle)
        ops.extend(diffusion())
    return ops,marked


def qasm(ops):
    lines=['OPENQASM 2.0;','include "qelib1.inc";','qreg q[3];','creg c[3];']
    for name,*qubits in ops:
        lines.append(name+' '+','.join(f'q[{q}]' for q in qubits)+';')
    lines.append('measure q -> c;')
    return '\n'.join(lines)+'\n'


def run(n,k=2,shots=2000,seed=12345):
    if shots < 1:
        raise ValueError('shots must be positive')
    ops,marked=circuit(n,k)
    state=simulate(ops)
    # Independent qudit calculation; each operation is an 8-level reflection.
    logical=np.full(8,1/math.sqrt(8),complex)
    for _ in range(k):
        logical[marked]*=-1
        logical=2*logical.mean()-logical
    physical=np.empty(8,complex)
    physical[ORDER]=logical
    error=float(np.max(np.abs(state-((-1)**k)*physical)))
    assert error < 1e-12
    probs=np.abs(state)**2
    probs/=probs.sum()
    good_labels=[ORDER[j] for j in marked]
    probability=float(probs[good_labels].sum())
    theta=math.asin(math.sqrt(len(marked)/8))
    prediction=math.sin((2*k+1)*theta)**2
    assert abs(probability-prediction) < 1e-12
    observed=Counter(np.random.default_rng(seed).choice(8,shots,p=probs))
    counts={format(int(label),'03b'):int(count) for label,count in sorted(observed.items())}
    accepted=Counter()
    for label,count in observed.items():
        p=CANDIDATES[ORDER.index(int(label))]
        if p < n and n % p == 0:
            accepted[f'{p}*{n//p}']+=int(count)
    complete=n < 19**2
    return {
        'N':n,'qubits':3,'qudit_levels_emulated':8,
        'iterations':k,'candidate_divisors':CANDIDATES,
        'logical_to_physical_basis':ORDER,
        'success_probability':probability,'shots':shots,
        'accepted_shots':sum(accepted.values()),'accepted_factors':dict(accepted),
        'all_measurement_counts_q2q1q0':counts,
        'qubit_vs_qudit_max_state_error_after_global_phase':error,
        'gate_counts':dict(Counter(op[0] for op in ops)),
        'oracle_classical_divisibility_checks':8,
        'cofactor_computed_classically_after_measurement':True,
        'coverage':('Complete small-divisor coverage for this input (factor 2 checked classically).'
                    if complete else 'Truncated domain: absence of detections is inconclusive.'),
        'classical_factor_2_precheck':([2,n//2] if n % 2 == 0 else None),
        'scope':'Compiled truth-table oracle; not a reversible quantum divider.',
    },ops


def selftest():
    checks=0
    worst=0.
    for n in [15,35,74,77,143,221,289,323,331,361,899]:
        for k in range(5):
            r,_=run(n,k,100)
            worst=max(worst,r['qubit_vs_qudit_max_state_error_after_global_phase'])
            for pair in r['accepted_factors']:
                p,q=map(int,pair.split('*'))
                assert p*q == n
            checks+=1
    # Every selective phase must mark exactly its target, on every basis state.
    for label in range(8):
        for basis in range(8):
            initial=np.eye(8,dtype=complex)[:,basis]
            expected=initial*(-1 if label == basis else 1)
            assert np.allclose(simulate(phase_flip(label),initial),expected)
    # Reproduce A115 modulo-8 arithmetic using exactly three logical qubits.
    increment=[('ccx',0,1,2),('cx',0,1),('x',0)]
    for j in range(8):
        initial=np.eye(8,dtype=complex)[:,j]
        assert np.allclose(simulate(increment,initial),np.eye(8)[:,(j+1)%8])
    # Arbitrary complex superpositions preserve amplitudes and inverse exactly.
    rng=np.random.default_rng(115)
    for _ in range(100):
        psi=rng.normal(size=8)+1j*rng.normal(size=8)
        psi/=np.linalg.norm(psi)
        assert np.allclose(simulate(increment,psi),np.roll(psi,1))
        assert np.allclose(simulate(list(reversed(increment)),simulate(increment,psi)),psi)
    return {'status':'PASS','grover_cases':checks,'selective_phase_basis_cases':64,
            'random_increment_tests':100,'A115_modulo8_increment_verified':True,
            'max_qubit_qudit_state_error':worst}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--N',type=int,default=323)
    parser.add_argument('--iterations',type=int,default=2)
    parser.add_argument('--shots',type=int,default=2000)
    parser.add_argument('--seed',type=int,default=12345)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--qasm',type=Path)
    parser.add_argument('--selftest',action='store_true')
    args=parser.parse_args()
    try:
        if args.selftest:
            result=selftest()
        else:
            result,ops=run(args.N,args.iterations,args.shots,args.seed)
            if args.qasm:
                args.qasm.write_text(qasm(ops))
    except ValueError as err:
        parser.error(str(err))
    text=json.dumps(result,indent=2)+'\n'
    if args.output:
        args.output.write_text(text)
    print(text)


if __name__=='__main__':
    main()
