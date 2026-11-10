#!/usr/bin/env python3
"""A124: compile non-diagonal two-level rotations in a virtual spin phase frame.

Exactly compares logical operations and frame-dressed physical transitions.
No hardware model, pulse-time benchmark, or Kaggle score claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

D=8
ORDER=[0,2,4,6,7,5,3,1]
PHYS_CORR=np.array([1,1j,1j,1j,1j,1j,1j,1],complex)
C=PHYS_CORR[ORDER]
X=np.roll(np.eye(D,dtype=complex),1,axis=0)
V=np.diag(np.conj(C))@X

def rot(a,b,theta,phi):
    """SU(2) equatorial rotation in logical levels a,b."""
    g=np.eye(D,dtype=complex)
    co=np.cos(theta/2)
    si=np.sin(theta/2)
    g[a,a]=g[b,b]=co
    g[a,b]=-1j*si*np.exp(-1j*phi)
    g[b,a]=-1j*si*np.exp(1j*phi)
    return g

def compile_dressed_rot(a,b,theta,phi,frame):
    """F G F^dag: drive phase shift arg(f_b)-arg(f_a)."""
    effective_phi=phi+np.angle(frame[b])-np.angle(frame[a])
    return rot(a,b,theta,effective_phi),effective_phi

def trial(rng,depth):
    psi=rng.normal(size=D)+1j*rng.normal(size=D)
    psi/=np.linalg.norm(psi)
    logical=psi.copy()
    physical=psi.copy()
    frame=np.ones(D,dtype=complex)
    errors=[]
    physical_ops={'native_inc':0,'native_dec':0,'dressed_rotation':0,'diag_phase':0}
    phase_updates=[]
    for _ in range(depth):
        op=int(rng.integers(0,4))
        if op==0:
            logical=X@logical
            physical=V@physical
            frame=np.conj(C)*np.roll(frame,1)
            physical_ops['native_inc']+=1
        elif op==1:
            logical=X.conj().T@logical
            physical=V.conj().T@physical
            frame=np.roll(C*frame,-1)
            physical_ops['native_dec']+=1
        elif op==2:
            # Compare F G F^dag with phase-adjusted resonant 2-level drive.
            a,b=rng.choice(D,size=2,replace=False)
            theta=float(rng.uniform(-np.pi,np.pi))
            phi=float(rng.uniform(-np.pi,np.pi))
            G=rot(a,b,theta,phi)
            U,shifted=compile_dressed_rot(a,b,theta,phi,frame)
            algebra=float(np.max(abs(U-(frame[:,None]*G)*np.conj(frame)[None,:])))
            errors.append(algebra)
            logical=G@logical
            physical=U@physical
            phase_updates.append(float(np.angle(np.exp(1j*(shifted-phi)))))
            physical_ops['dressed_rotation']+=1
        else:
            phases=np.exp(1j*rng.uniform(-np.pi,np.pi,size=D))
            logical=phases*logical
            physical=phases*physical
            physical_ops['diag_phase']+=1
        errors.append(float(np.max(abs(physical-frame*logical))))
    return max(errors,default=0.),physical_ops,phase_updates

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trials',type=int,default=10000)
    p.add_argument('--depth',type=int,default=24)
    p.add_argument('--seed',type=int,default=124)
    p.add_argument('--out',type=Path,default=Path('results/a124_dressed_transition_frame.json'))
    a=p.parse_args()
    if a.trials<1 or a.depth<1:p.error('positive trials/depth required')
    rng=np.random.default_rng(a.seed)
    worst=0.
    counts={'native_inc':0,'native_dec':0,'dressed_rotation':0,'diag_phase':0}
    nonzero=0
    for _ in range(a.trials):
        err,ops,shifts=trial(rng,a.depth)
        worst=max(worst,err)
        for k in counts:counts[k]+=ops[k]
        nonzero+=sum(abs(x)>1e-10 for x in shifts)
    result={
        'status':'PASS_IDEAL_FRAME_DRESSING' if worst<1e-11 else 'FAIL',
        'trials':a.trials,'depth':a.depth,'max_frame_aligned_error':worst,
        'operation_counts':counts,'nonzero_drive_phase_adjustments':nonzero,
        'assumptions':[
            'Arbitrary logical two-level rotations are assumed physically addressable.',
            'Phase adjustments are exact and costless in this ideal test.',
            'Non-adjacent transitions may require swaps or additional controls.',
            'This does not model actual multitone control, decoherence, leakage or constraints on phase shifts.',
            'No full algorithmic resource or Kaggle improvement demonstrated.'
        ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A124_RESULT',json.dumps({k:v for k,v in result.items() if k!='assumptions'}),flush=True)
    if result['status']=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
