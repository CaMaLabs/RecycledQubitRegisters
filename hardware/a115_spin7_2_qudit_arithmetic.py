#!/usr/bin/env python3
"""A115: exact spin-7/2 (8-level) qudit vs three logical qubits.

Pure mathematical simulation; NOT a hardware pulse benchmark or Kaggle score.
Qudit X8 is one abstract unitary, not necessarily one physical pulse.
All comparisons use identical 8-dimensional Hilbert spaces.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np

D = 8
TWO_PI = 2 * np.pi

def basis(j):
    x = np.zeros(D, dtype=complex)
    x[j] = 1
    return x

def bit(j, k):
    return (j >> k) & 1

def permutation_from_map(fn):
    u = np.zeros((D, D), dtype=complex)
    for j in range(D):
        u[fn(j), j] = 1
    return u

def apply_x(j, target, controls=()):
    if all(bit(j, c) for c in controls):
        return j ^ (1 << target)
    return j

def three_qubit_ripple_increment():
    """Apply gates in this order: CCX(0,1 -> 2), CX(0 -> 1), X(0)."""
    u = np.eye(D, dtype=complex)
    gate_map = [
        lambda j: apply_x(j, 2, (0,1)),
        lambda j: apply_x(j, 1, (0,)),
        lambda j: apply_x(j, 0),
    ]
    for gate in gate_map:
        u = permutation_from_map(gate) @ u
    return u

def qudit_increment():
    return permutation_from_map(lambda j: (j + 1) % D)

def spin_phase(k=1):
    """Z8^k; phase is computational, not independently readable storage."""
    return np.diag(np.exp(1j * TWO_PI * k * np.arange(D) / D))

def qft8():
    j = np.arange(D)
    return np.exp(1j * TWO_PI * np.outer(j,j) / D) / np.sqrt(D)

def gray(j):
    return j ^ (j >> 1)

def test(atol=1e-12, random_trials=256, seed=115):
    x8 = qudit_increment()
    ripple = three_qubit_ripple_increment()
    z8 = spin_phase()
    f8 = qft8()
    identity = np.eye(D, dtype=complex)
    errors = {}
    errors['ripple_vs_qudit_matrix'] = float(np.max(np.abs(ripple-x8)))
    errors['increment_8_times_identity'] = float(np.max(np.abs(np.linalg.matrix_power(x8,8)-identity)))
    errors['unitary_increment'] = float(np.max(np.abs(x8.conj().T@x8-identity)))
    errors['unitary_fourier'] = float(np.max(np.abs(f8.conj().T@f8-identity)))
    errors['fourier_inverse'] = float(np.max(np.abs(f8.conj().T@f8-identity)))
    errors['fourier_diagonalizes_increment'] = float(np.max(np.abs(f8@x8@f8.conj().T-spin_phase(1))))
    errors['phase_order_8'] = float(np.max(np.abs(np.linalg.matrix_power(z8,8)-identity)))
    errors['conjugate_commutation'] = float(np.max(np.abs(z8@x8-np.exp(1j*TWO_PI/D)*x8@z8)))
    errors['all_basis_increment'] = max(float(np.max(np.abs(x8@basis(j)-basis((j+1)%D)))) for j in range(D))
    rng=np.random.default_rng(seed)
    worst_roundtrip=0.
    worst_ripple=0.
    worst_phase_uncompute=0.
    for _ in range(random_trials):
        psi=rng.normal(size=D)+1j*rng.normal(size=D)
        psi=psi/np.linalg.norm(psi)
        k=int(rng.integers(0,8))
        out=np.linalg.matrix_power(x8,k)@psi
        worst_roundtrip=max(worst_roundtrip,float(np.max(np.abs(np.linalg.matrix_power(x8,-k)@out-psi))))
        worst_ripple=max(worst_ripple,float(np.max(np.abs(ripple@psi-x8@psi))))
        encoded=z8@out
        worst_phase_uncompute=max(worst_phase_uncompute,float(np.max(np.abs(x8.conj().T@z8.conj().T@encoded-psi))) if k==1 else 0.)
    errors['random_increment_uncompute']=worst_roundtrip
    errors['random_ripple_vs_qudit']=worst_ripple
    errors['random_phase_uncompute']=worst_phase_uncompute
    errors['phase_uncompute_all_k']=max(float(np.max(np.abs(np.linalg.matrix_power(x8,-k)@z8.conj().T@z8@np.linalg.matrix_power(x8,k)-identity))) for k in range(8))
    all_ok=all(v <= atol for v in errors.values())
    if not all_ok:
        raise AssertionError('A115 numerical selftest failure: '+json.dumps(errors))
    binary_flips=sum((j ^ ((j+1)%8)).bit_count() for j in range(8))
    gray_flips=sum((gray(j)^gray((j+1)%8)).bit_count() for j in range(8))
    return {
        'status':'PASS_MATHEMATICAL_EQUIVALENCE',
        'dimension':8,'physical_spin_s':'7/2','logical_qubits_encoded':3,
        'independent_classical_bits_per_projective_measurement':3,
        'random_trials':random_trials,'tolerance':atol,'errors':errors,
        'arithmetic':{
            'operation':'increment modulo 8',
            'abstract_qudit_unitaries':1,
            'three_qubit_ripple_gate_counts':{'X':1,'CX':1,'CCX':1},
            'adjacent_level_transpositions_upper_construction':7,
            'binary_encoding_hamming_sum_8_cycle':binary_flips,
            'gray_encoding_hamming_sum_8_cycle':gray_flips,
            'note':'7 transpositions are a constructive upper bound, not a hardware pulse estimate'
        },
        'limits':[
            'Both encodings have exactly 8-dimensional Hilbert spaces; no information-capacity gain.',
            'A generic 8-level unitary may be costly to synthesize using allowed spin transitions.',
            'Spin populations, coherences and correlations are not independent readable classical registers.',
            'The experiment does not demonstrate hardware speedups, fidelity, error correction or competition score improvement.'
        ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,default=Path('results/a115_spin7_2_qudit_arithmetic.json'))
    p.add_argument('--trials',type=int,default=256)
    args=p.parse_args()
    report=test(random_trials=args.trials)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('A115_RESULT',json.dumps({'status':report['status'],
        'max_error':max(report['errors'].values()),
        'arithmetic':report['arithmetic'],'output':str(args.out)}),flush=True)

if __name__=='__main__':
    main()
