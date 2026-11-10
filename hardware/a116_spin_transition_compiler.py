#!/usr/bin/env python3
"""A116: idealized transition-selective spin-7/2 arithmetic compiler.

Models resonant adjacent m<->m+1 transitions with spin ladder matrix elements.
No crosstalk, leakage, decoherence, or pulse hardware calibration.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
D=8
S=3.5
M=np.arange(-S,S+1)

def drive_pi(p):
    u=np.eye(D,dtype=complex)
    u[p,p]=u[p+1,p+1]=0
    u[p,p+1]=u[p+1,p]=-1j
    return u

def strength(p):
    m=M[p]
    return float(np.sqrt(S*(S+1)-m*(m+1))/2)

def x8():
    x=np.zeros((D,D),dtype=complex)
    for j in range(D): x[(j+1)%D,j]=1
    return x

def compile_increment():
    pulses=list(range(6,-1,-1))
    u=np.eye(D,dtype=complex)
    for p in pulses:u=drive_pi(p)@u
    phase=u@x8().conj().T
    diagonal=np.diag(phase)
    assert np.max(np.abs(phase-np.diag(diagonal)))<1e-12
    correction=np.diag(np.conj(diagonal))
    return pulses,correction,correction@u

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,default=Path('results/a116_spin_transition_compiler.json'))
    ap.add_argument('--trials',type=int,default=10000)
    ap.add_argument('--rabi-scale',type=float,default=1.,help='Arbitrary drive frequency scale, not calibrated physical Hz')
    args=ap.parse_args()
    if args.rabi_scale<=0:ap.error('rabi-scale must be positive')
    pulses,phase,unitary=compile_increment()
    ideal=x8()
    matrix_error=float(np.max(np.abs(unitary-ideal)))
    rng=np.random.default_rng(116)
    worst=0.
    inverse_worst=0.
    for _ in range(args.trials):
        psi=rng.normal(size=D)+1j*rng.normal(size=D)
        psi/=np.linalg.norm(psi)
        worst=max(worst,float(np.max(np.abs(unitary@psi-ideal@psi))))
        inverse_worst=max(inverse_worst,float(np.max(np.abs(unitary.conj().T@unitary@psi-psi))))
    durations=[float(np.pi/(2*args.rabi_scale*strength(p))) for p in pulses]
    status='PASS_IDEALIZED_TRANSITION_MODEL' if max(matrix_error,worst,inverse_worst)<1e-12 else 'FAIL'
    report={'status':status,'spin':S,'dimension':D,'random_trials':args.trials,
      'mode':'ideal transition-selective pi pulses plus ideal diagonal correction',
      'transition_pulses':len(pulses),'transition_indices':pulses,
      'relative_strengths':[strength(p) for p in pulses],
      'pulse_duration_inverse_scale_units':durations,'total_duration_inverse_scale_units':sum(durations),
      'phase_correction_required':True,
      'phase_correction':[{'real':float(z.real),'imag':float(z.imag)} for z in np.diag(phase)],
      'max_matrix_error':matrix_error,'max_state_error':worst,'max_inverse_error':inverse_worst,
      'three_qubit_ripple_reference':{'X':1,'CX':1,'CCX':1},
      'abstract_qudit_x8_reference':1,
      'limitations':[
        'Seven addressed transitions and a diagonal correction are not a single physical pulse.',
        'Phase correction implementation and cost have not been modeled.',
        'No crosstalk, leakage, decoherence, spectral crowding or noise are modeled.',
        'Pulse time units are arbitrary and are not hardware benchmarks.',
        'No platform-normalized performance comparison with three-qubit gates.',
        'Both encodings have Hilbert-space dimension eight; no increase in readable information.',
        'No Kickmix or Kaggle score improvement has been established.']}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('A116_RESULT',json.dumps({k:report[k] for k in ('status','transition_pulses','phase_correction_required','max_matrix_error','max_state_error','max_inverse_error','total_duration_inverse_scale_units')}),flush=True)
    if status=='FAIL':raise SystemExit(1)

if __name__=='__main__':main()
