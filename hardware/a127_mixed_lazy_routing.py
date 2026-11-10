#!/usr/bin/env python3
"""A127: phase-aware lazy routing with native arithmetic in mixed workloads.

The native 8-level increment is calibrated for the canonical spin-level
assignment. If lazy routing changed that assignment, restore the canonical
map before invoking it, and account for the required adjacent physical SWAPs.
All SWAPs, adjacent rotations, diagonal phases and native increments are
simulated as exact unitaries on 8-level statevectors, including phase frame.
This is NOT a physical pulse-fidelity/time or Kickmix-score experiment.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np

D=8
LOGICAL_TO_PHYSICAL=(0,2,4,6,7,5,3,1)
CANONICAL=tuple(LOGICAL_TO_PHYSICAL.index(p) for p in range(D))
PHYSICAL_PHASE=np.array([1,1j,1j,1j,1j,1j,1j,1],complex)
C=PHYSICAL_PHASE[list(LOGICAL_TO_PHYSICAL)]
X=np.roll(np.eye(D,dtype=complex),1,axis=0)
NATIVE=np.diag(np.conj(C))@X

def two_level(p,q,theta,phi):
    G=np.eye(D,dtype=complex)
    co=np.cos(theta/2)
    si=np.sin(theta/2)
    G[p,p]=G[q,q]=co
    G[p,q]=-1j*si*np.exp(-1j*phi)
    G[q,p]=-1j*si*np.exp(1j*phi)
    return G

def do_swap(state,frame,mapping,k):
    state[[k,k+1]]=state[[k+1,k]]
    frame[[k,k+1]]=frame[[k+1,k]]
    mapping[k],mapping[k+1]=mapping[k+1],mapping[k]

def restore(state,frame,mapping,target):
    swaps=0
    for p,label in enumerate(target):
        q=mapping.index(label)
        while q>p:
            do_swap(state,frame,mapping,q-1)
            swaps+=1
            q-=1
    assert tuple(mapping)==tuple(target)
    return swaps

def route_pair(state,frame,mapping,a,b):
    p=mapping.index(a)
    q=mapping.index(b)
    path=(list(range(q-1,p,-1)) if q>p+1 else
          list(range(q,p-1)) if q<p-1 else [])
    for k in path:do_swap(state,frame,mapping,k)
    assert abs(mapping.index(a)-mapping.index(b))==1
    return path

def simulate(ops,initial,phases,lazy):
    logical=initial.copy()
    mapping=list(CANONICAL)
    frame=np.array([phases[k] for k in mapping],complex)
    physical=frame*np.array([logical[k] for k in mapping],complex)
    swaps=rotations=arith=diag=phase_updates=0
    worst=0.
    for op in ops:
        if op[0]=='rot':
            _,a,b,theta,phi=op
            logical=two_level(a,b,theta,phi)@logical
            path=route_pair(physical,frame,mapping,a,b)
            swaps+=len(path)
            p,q=mapping.index(a),mapping.index(b)
            phi_eff=phi+np.angle(frame[q])-np.angle(frame[p])
            physical=two_level(p,q,theta,phi_eff)@physical
            phase_updates+=int(abs(np.angle(np.exp(1j*(phi_eff-phi))))>1e-10)
            rotations+=1
            if not lazy:
                for k in reversed(path):do_swap(physical,frame,mapping,k)
                swaps+=len(path)
        elif op[0]=='diag':
            _,angles=op
            gate=np.exp(1j*np.asarray(angles))
            logical=gate*logical
            physical=np.asarray([gate[k] for k in mapping])*physical
            diag+=1
        elif op[0] in ('inc','dec'):
            # Native two-layer pulse schedule is only calibrated for the
            # canonical physical order; charge the reconfiguration.
            swaps+=restore(physical,frame,mapping,CANONICAL)
            f=np.asarray([frame[mapping.index(k)] for k in range(D)])
            if op[0]=='inc':
                logical=X@logical
                # The native operator is C^dag X in logical order.
                v=np.asarray([physical[mapping.index(k)] for k in range(D)])
                v=NATIVE@v
                f=np.conj(C)*np.roll(f,1)
            else:
                logical=X.conj().T@logical
                v=np.asarray([physical[mapping.index(k)] for k in range(D)])
                v=NATIVE.conj().T@v
                f=np.roll(C*f,-1)
            for k in range(D):
                p=mapping.index(k)
                physical[p]=v[k]
                frame[p]=f[k]
            arith+=1
        else:raise ValueError(op)
        expected=frame*np.asarray([logical[k] for k in mapping])
        worst=max(worst,float(np.max(abs(expected-physical))))
    swaps+=restore(physical,frame,mapping,CANONICAL)
    final_error=float(np.max(abs(frame*np.asarray([logical[k] for k in mapping])-physical)))
    return {'swaps':swaps,'rotations':rotations,'native_arithmetic':arith,
            'diagonal_gates':diag,'drive_phase_adjustments':phase_updates,
            'max_frame_aligned_error':max(worst,final_error)}

def make_ops(rng,n,arithmetic_fraction):
    out=[]
    for _ in range(n):
        x=rng.random()
        if x<arithmetic_fraction:
            out.append(('inc' if rng.random()<.5 else 'dec',))
        elif x<arithmetic_fraction+.1:
            out.append(('diag',rng.uniform(-np.pi,np.pi,D).tolist()))
        else:
            a,b=map(int,rng.choice(D,2,replace=False))
            out.append(('rot',a,b,float(rng.uniform(-np.pi,np.pi)),
                        float(rng.uniform(-np.pi,np.pi))))
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trials',type=int,default=300)
    p.add_argument('--depth',type=int,default=64)
    p.add_argument('--seed',type=int,default=127)
    p.add_argument('--arithmetic-fractions',type=float,nargs='+',default=[0,.1,.25,.5,.75])
    p.add_argument('--out',type=Path,default=Path('results/a127_mixed_lazy_routing.json'))
    a=p.parse_args()
    if a.trials<1 or a.depth<1 or any(v<0 or v>.9 for v in a.arithmetic_fractions):
        p.error('Invalid arguments')
    rng=np.random.default_rng(a.seed)
    result=[]
    for fraction in a.arithmetic_fractions:
        old=new=0
        worst=0.
        wins=ties=losses=0
        for _ in range(a.trials):
            psi=rng.normal(size=D)+1j*rng.normal(size=D)
            psi/=np.linalg.norm(psi)
            phases=np.exp(1j*rng.uniform(-np.pi,np.pi,D))
            ops=make_ops(rng,a.depth,fraction)
            static=simulate(ops,psi,phases,False)
            lazy=simulate(ops,psi,phases,True)
            worst=max(worst,static['max_frame_aligned_error'],lazy['max_frame_aligned_error'])
            old+=static['swaps']
            new+=lazy['swaps']
            wins+=lazy['swaps']<static['swaps']
            ties+=lazy['swaps']==static['swaps']
            losses+=lazy['swaps']>static['swaps']
        row={'arithmetic_fraction':fraction,'static_swaps':old,'lazy_swaps':new,
             'reduction_fraction':(1-new/old) if old else None,
             'lazy_wins':wins,'ties':ties,'lazy_loses':losses,
             'max_state_error':worst}
        result.append(row)
        print('A127_POINT',json.dumps(row),flush=True)
    status='PASS_MIXED_EXACT_STATE' if all(r['max_state_error']<1e-11 for r in result) else 'FAIL'
    report={'status':status,'trials':a.trials,'depth':a.depth,
      'canonical_physical_to_logical':list(CANONICAL),
      'results':result,
      'limitations':[
        'Native increment is an ideal precompiled primitive; it is not physically simulated under noise.',
        'Native arithmetic resets mapping to canonical physical order and restoration SWAPs are charged.',
        'Adjacent SWAPs and rotations are noiseless and have equal abstract cost.',
        'Virtual phase updates and physical pulse phase settings are free.',
        'No decoherence, gate duration, bandwidth, or actual Qiskit hardware advantage inferred.',
        'Savings are workload-dependent and not directly translatable to the Kickmix score.'
      ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('A127_RESULT',json.dumps({'status':status,'output':str(a.out),'points':len(result)}),flush=True)
    if status=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
