#!/usr/bin/env python3
"""A117: two-layer multitone arithmetic on an ideal spin-7/2 ladder.

Two parallel nearest-neighbor matchings implement modulo-8 increment after
relabeling the logical basis. Includes explicit 8x8 Hamiltonian evolution.
Phase correction is ideal and not included in the control-time comparison.
No crosstalk, decoherence, leakage or off-resonant excitation is modeled.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
from scipy.linalg import expm

DIM=8
SPIN=3.5
EVEN=(0,2,4,6)
ODD=(1,3,5)

def coupling(edge):
    m=edge-SPIN
    return float(np.sqrt(SPIN*(SPIN+1)-m*(m+1))/2)

def layer(edges):
    duration=max(np.pi/(2*coupling(k)) for k in edges)
    h=np.zeros((DIM,DIM),dtype=complex)
    for k in edges:
        g=np.pi/(2*duration)
        assert g<=coupling(k)+1e-14
        h[k,k+1]=h[k+1,k]=g
    return expm(-1j*h*duration), duration

def shift():
    x=np.zeros((DIM,DIM),dtype=complex)
    for j in range(DIM):x[(j+1)%DIM,j]=1
    return x

def implied_permutation(u):
    idx=np.argmax(np.abs(u),axis=0)
    if len(set(map(int,idx)))!=DIM:
        raise AssertionError('Not a monomial unitary')
    err=np.max(np.abs(np.abs(u)-np.eye(DIM)[idx].T))
    if err>1e-12:raise AssertionError(f'Not monomial: {err}')
    return [int(x) for x in idx]

def cycle_order(perm):
    order=[0]
    while True:
        nxt=perm[order[-1]]
        if nxt==order[0]:break
        if nxt in order:raise AssertionError('Not a single 8-cycle')
        order.append(nxt)
    if len(order)!=DIM:raise AssertionError('Cycle does not cover all levels')
    return order

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--trials',type=int,default=10000)
    ap.add_argument('--out',type=Path,default=Path('results/a117_multitone_gray_cycle.json'))
    args=ap.parse_args()
    if args.trials<1:ap.error('trials must be positive')
    ue,te=layer(EVEN)
    uo,to=layer(ODD)
    raw=uo@ue
    perm=implied_permutation(raw)
    order=cycle_order(perm)
    B=np.eye(DIM,dtype=complex)[:,order]
    raw_logical=B.conj().T@raw@B
    expected=shift()
    phases=np.array([raw_logical[(j+1)%DIM,j] for j in range(DIM)])
    D=np.diag(np.conj(np.roll(phases,1)))
    corrected=D@raw_logical
    matrix_error=float(np.max(np.abs(corrected-expected)))
    rng=np.random.default_rng(117)
    worst_state=worst_inverse=0.
    for _ in range(args.trials):
        psi=rng.normal(size=DIM)+1j*rng.normal(size=DIM)
        psi/=np.linalg.norm(psi)
        worst_state=max(worst_state,float(np.max(np.abs(corrected@psi-expected@psi))))
        worst_inverse=max(worst_inverse,float(np.max(np.abs(corrected.conj().T@corrected@psi-psi))))
    sequential=sum(np.pi/(2*coupling(k)) for k in range(DIM-1))
    total=te+to
    report={
        'status':'PASS_IDEAL_TWO_LAYER_MATCHING' if max(matrix_error,worst_state,worst_inverse)<1e-12 else 'FAIL',
        'spin':'7/2','dimension':DIM,'trials':args.trials,
        'transition_group_1':list(EVEN),'transition_group_2':list(ODD),
        'permutation_in_physical_order':perm,
        'logical_to_physical_level':order,
        'diagonal_phase_correction_required':True,
        'phase_correction_diagonal':[{'re':float(z.real),'im':float(z.imag)} for z in np.diag(D)],
        'layer_duration_inverse_drive_units':[te,to],
        'total_two_layer_duration_inverse_drive_units':total,
        'seven_sequential_duration_inverse_drive_units':sequential,
        'idealized_duration_ratio_two_layer_over_sequential':total/sequential,
        'max_matrix_error':matrix_error,'max_random_state_error':worst_state,
        'max_inverse_error':worst_inverse,
        'hardware_assumptions':[
            'Independently selective nearest-neighbor drives; rotating-wave approximation.',
            'Transitions in a matching are simultaneous and independently calibrated.',
            'No off-resonant excitation, cross-talk, decoherence, leakage or noise.',
            'Amplitude per transition bounded by its spin ladder matrix element times a common scale.',
            'Ideal phase correction is free and un-timed; real implementation cost unknown.',
            'Logical levels are permuted relative to the native spin projection ordering.',
            'Comparison is to seven sequential transitions in the same ideal model, not a three-qubit processor.',
            'No Kaggle score improvement or increased information capacity is claimed.'
        ]
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('A117_RESULT',json.dumps({k:report[k] for k in (
        'status','logical_to_physical_level','total_two_layer_duration_inverse_drive_units',
        'seven_sequential_duration_inverse_drive_units','idealized_duration_ratio_two_layer_over_sequential',
        'max_matrix_error','max_random_state_error','max_inverse_error')}),flush=True)
    if report['status']=='FAIL':raise SystemExit(1)

if __name__=='__main__':main()
