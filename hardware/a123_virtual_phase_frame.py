#!/usr/bin/env python3
"""A123: exact virtual-phase-frame tracking of eight-level spin arithmetic.

Tracks a diagonal phase frame through native multitone increment/inverse
and arbitrary *diagonal logical* phase gates. This shows when physically
applying A122's diagonal correction can be deferred, not eliminated.
All states and operators are ideal; physical pulse cost is not measured.
"""
import argparse,json
from pathlib import Path
import numpy as np

D=8
X=np.roll(np.eye(D,dtype=complex),1,axis=0)
# A122's correction is physical-order; permute to the two-layer logical order.
ORDER=[0,2,4,6,7,5,3,1]
PHYSICAL=np.array([1,1j,1j,1j,1j,1j,1j,1],dtype=complex)
LOGICAL_CORRECTION=PHYSICAL[ORDER]
C=np.diag(LOGICAL_CORRECTION)
# A117 actual native unitary is C^dag X.
V=C.conj().T@X

def simulate(trials,steps,seed):
    rng=np.random.default_rng(seed)
    max_aligned=0.
    max_prob=0.
    max_frame_nonunitarity=0.
    max_uncorrected=0.
    frame_nontrivial=0
    for _ in range(trials):
        psi=rng.normal(size=D)+1j*rng.normal(size=D)
        psi/=np.linalg.norm(psi)
        logical=psi.copy()
        physical=psi.copy()
        frame=np.ones(D,dtype=complex)
        for _ in range(steps):
            action=int(rng.integers(0,3))
            if action==0:
                # Desired logical X; actual hardware applies V = C^dag X.
                logical=X@logical
                physical=V@physical
                # X diag(f) X^dag permutes frame entries by +1.
                frame=np.conj(LOGICAL_CORRECTION)*np.roll(frame,1)
            elif action==1:
                # Desired X^dag; actual is the reversed pulse sequence V^dag.
                logical=X.conj().T@logical
                physical=V.conj().T@physical
                # V^dag diag(f) X = X^dag C diag(f) X.
                frame=np.roll(LOGICAL_CORRECTION*frame,-1)
            else:
                # Diagonal phase gates commute with any diagonal frame;
                # implementing these physical phases is a separate cost.
                angles=rng.uniform(-np.pi,np.pi,D)
                phases=np.exp(1j*angles)
                logical=phases*logical
                physical=phases*physical
            max_aligned=max(max_aligned,float(np.max(abs(physical-frame*logical))))
            max_prob=max(max_prob,float(np.max(abs(abs(physical)**2-abs(logical)**2))))
            max_frame_nonunitarity=max(max_frame_nonunitarity,float(np.max(abs(abs(frame)-1))))
            max_uncorrected=max(max_uncorrected,float(np.max(abs(physical-logical))))
            if np.max(abs(frame-frame[0]))>1e-10:frame_nontrivial+=1
    return {'status':'PASS_VIRTUAL_PHASE_FRAME' if max(max_aligned,max_prob,max_frame_nonunitarity)<1e-11 else 'FAIL',
       'trials':trials,'steps_per_trial':steps,'max_frame_aligned_amplitude_error':max_aligned,
       'max_computational_basis_probability_error':max_prob,
       'max_frame_modulus_error':max_frame_nonunitarity,
       'max_raw_amplitude_difference_without_frame_correction':max_uncorrected,
       'nontrivial_frame_steps':frame_nontrivial,
       'phase_correction_for_native_increment':[
           {'re':float(z.real),'im':float(z.imag)} for z in LOGICAL_CORRECTION],
       'limits':[
        'Applies to X8/X8 inverse and logical diagonal phase operations; not arbitrary gates.',
        'Computational-basis measurement probabilities remain correct, but phase-sensitive readout does not.',
        'A subsequent non-diagonal gate must be compiled in the current frame or the correction implemented.',
        'Requires reliable phase reference and calibrated transition-drive phases.',
        'Deferred frame accounting removes no demonstrated physical pulse or error cost.',
        'No hardware fidelity, duration, or Kaggle improvement is demonstrated.']}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trials',type=int,default=10000)
    p.add_argument('--steps',type=int,default=24)
    p.add_argument('--seed',type=int,default=123)
    p.add_argument('--out',type=Path,default=Path('results/a123_virtual_phase_frame.json'))
    a=p.parse_args()
    if a.trials<1 or a.steps<1:p.error('positive trials and steps required')
    result=simulate(a.trials,a.steps,a.seed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A123_RESULT',json.dumps({k:v for k,v in result.items() if k not in ('limits','phase_correction_for_native_increment')}),flush=True)
    if result['status']=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
