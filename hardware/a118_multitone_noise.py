#!/usr/bin/env python3
"""A118: coherent-error robustness of ideal spin-7/2 multitone arithmetic.

Compares the A116 seven sequential resonant transitions with the A117 two
parallel matchings at identical maximum resonant coupling scale.
Applies static, trial-wise amplitude calibration error, diagonal detuning,
and residual nearest-neighbor crosstalk. This is a dimensionless toy model,
NOT a measured device/noise model. No decoherence, leakage, spectrum, or
real phase-correction pulse is included.

The sequential implementation is physically equivalent to X8 up to a
calibrated diagonal correction; the parallel implementation uses an explicit
logical-to-physical permutation. Those fixed corrections are ideal and free.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.linalg import expm

D=8
S=3.5
EVEN=(0,2,4,6)
ODD=(1,3,5)

def coupling(edge):
    m=edge-S
    return float(np.sqrt(S*(S+1)-m*(m+1))/2)

def shift():
    u=np.zeros((D,D),complex)
    for j in range(D):u[(j+1)%D,j]=1
    return u

def nominal_step(edges, scale):
    """Disjoint selected transitions share a pi/2 area; each <= natural coupling."""
    duration=max(np.pi/(2*scale*coupling(k)) for k in edges)
    strengths={k:np.pi/(2*duration) for k in edges}
    return duration,strengths

def evolution(edges, scale, amp_error, detuning, crosstalk):
    t,gates=nominal_step(edges,scale)
    H=np.diag(detuning).astype(complex)
    for k in range(D-1):
        intended=gates.get(k,0.0)
        # Residual unintended nearest-neighbor coupling, measured relative
        # to each edge's nominal available Rabi matrix element.
        g=intended*(1+amp_error[k])+(
            crosstalk[k]*scale*coupling(k) if k not in gates else 0.
        )
        H[k,k+1]=H[k+1,k]=g
    return expm(-1j*H*t),t

def compile_layers(groups,scale=1.):
    u=np.eye(D,dtype=complex)
    total=0.
    for edges in groups:
        v,t=evolution(edges,scale,np.zeros(D-1),np.zeros(D),np.zeros(D-1))
        u=v@u
        total+=t
    return u,total

def find_order(u):
    ids=np.argmax(np.abs(u),axis=0)
    if len(set(map(int,ids))) != D:raise AssertionError('Not a permutation')
    path=[0]
    while True:
        j=int(ids[path[-1]])
        if j==path[0]:break
        if j in path:raise AssertionError('Not an eight-cycle')
        path.append(j)
    if len(path)!=D:raise AssertionError('Not an eight-cycle')
    return path

def canonicalize(u,order):
    B=np.eye(D,dtype=complex)[:,order]
    w=B.conj().T@u@B
    phases=np.asarray([w[(j+1)%D,j] for j in range(D)])
    correction=np.diag(np.conj(np.roll(phases,1)))
    corrected=correction@w
    if np.max(np.abs(corrected-shift()))>1e-12:
        raise AssertionError('Nominal correction does not reconstruct shift')
    return B,correction,corrected

def fidelity(u,target):
    # Average pure-state gate fidelity, unitary error only (d=8).
    tr=np.trace(target.conj().T@u)
    return float((abs(tr)**2+D)/(D*(D+1)))

def simulate(args):
    seven=[(k,) for k in range(6,-1,-1)]
    two=[EVEN,ODD]
    us,ts=compile_layers(seven,args.scale)
    up,tp=compile_layers(two,args.scale)
    bs,cs,_=canonicalize(us,find_order(us))
    bp,cp,_=canonicalize(up,find_order(up))
    # Input coding differs, but both are compared to identical logical X8.
    rng=np.random.default_rng(args.seed)
    curves=[]
    for error in args.errors:
        sequential=[]
        parallel=[]
        for trial in range(args.trials):
            # Common error distribution, independently sampled for each
            # strategy. Simulations are not hardware cross-correlations.
            values=[]
            for groups,B,C in ((seven,bs,cs),(two,bp,cp)):
                amp=rng.normal(0,error,size=D-1)
                det=rng.normal(0,error*args.scale,size=D)
                bleed=rng.normal(0,error*args.crosstalk_multiplier,size=D-1)
                u=np.eye(D,dtype=complex)
                for edges in groups:
                    v,_=evolution(edges,args.scale,amp,det,bleed)
                    u=v@u
                effective=C@B.conj().T@u@B
                values.append(fidelity(effective,shift()))
            sequential.append(values[0])
            parallel.append(values[1])
        a=np.asarray(sequential)
        b=np.asarray(parallel)
        curves.append({
            'error_fraction':error,
            'sequential_mean_fidelity':float(a.mean()),
            'parallel_mean_fidelity':float(b.mean()),
            'sequential_p05_fidelity':float(np.quantile(a,0.05)),
            'parallel_p05_fidelity':float(np.quantile(b,0.05)),
            'parallel_better_mean':bool(b.mean()>a.mean()),
            'parallel_better_p05':bool(np.quantile(b,0.05)>np.quantile(a,0.05))
        })
    return {'status':'PASS_SIMULATION','model':'static coherent dimensionless noise',
        'spin':'7/2','dimension':D,'trials_per_error_per_strategy':args.trials,
        'seed':args.seed,'normalized_drive_scale':args.scale,
        'crosstalk_multiplier':args.crosstalk_multiplier,
        'seven_step_ideal_duration':ts,'two_layer_ideal_duration':tp,
        'two_layer_time_ratio':tp/ts,
        'curves':curves,
        'assumptions':[
            'Gaussian relative amplitude calibration error per edge.',
            'Gaussian static diagonal energy detuning per level with std = error*drive_scale.',
            'Gaussian residual drive on off-target adjacent transitions, std = error*crosstalk_multiplier*available_coupling.',
            'Errors held constant through all sequential layers within each trial.',
            'Exact matrix exponentiation of an 8x8 rotating-frame Hamiltonian.',
            'Ideal uncharged basis relabeling and calibrated diagonal phase correction.',
            'No explicit level spacing, off-resonant spectral response, leakage, decoherence, or hardware drive calibration.',
            'Mean gate fidelities compare two simulated logical gates, not physical hardware.',
            'No direct Kaggle resource reduction is implied.'
        ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trials',type=int,default=300)
    p.add_argument('--seed',type=int,default=118)
    p.add_argument('--scale',type=float,default=1.)
    p.add_argument('--crosstalk-multiplier',type=float,default=0.25)
    p.add_argument('--errors',type=float,nargs='+',default=[0.,.001,.003,.01,.02,.05])
    p.add_argument('--out',type=Path,default=Path('results/a118_multitone_noise.json'))
    a=p.parse_args()
    if a.trials<1 or a.scale<=0 or a.crosstalk_multiplier<0 or any(x<0 for x in a.errors):p.error('Invalid arguments')
    result=simulate(a)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A118_RESULT',json.dumps({'status':result['status'],
        'two_layer_time_ratio':result['two_layer_time_ratio'],
        'curves':result['curves'],'output':str(a.out)}),flush=True)

if __name__=='__main__':main()
