#!/usr/bin/env python3
"""A126: phase-aware lazy routing for spin-7/2 logical two-level gates.

Compares static SWAP-route-restore with lazy physical-level mapping, using
adjacent-level SWAPs and phase-dressed adjacent rotations. Physical states
are simulated explicitly. This is a gate-count experiment, NOT a calibrated
pulse-time or fidelity benchmark.

The arbitrary native X8 increment is not included: a changed mapping would
require recompiling that pulse sequence or resetting the map. This study
covers arbitrary logical two-level rotations and diagonal phase operations.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np

D=8
LOGICAL_TO_PHYSICAL=(0,2,4,6,7,5,3,1)
INITIAL_ORDER=tuple(LOGICAL_TO_PHYSICAL.index(p) for p in range(D))

def two_level(p,q,theta,phi):
    U=np.eye(D,dtype=complex)
    ct=np.cos(theta/2)
    st=np.sin(theta/2)
    U[p,p]=U[q,q]=ct
    U[p,q]=-1j*st*np.exp(-1j*phi)
    U[q,p]=-1j*st*np.exp(1j*phi)
    return U

def swap(vec,phase,positions,k):
    """Physical SWAP, update lazy physical->logical labels and phase frame."""
    vec[[k,k+1]]=vec[[k+1,k]]
    phase[[k,k+1]]=phase[[k+1,k]]
    positions[k],positions[k+1]=positions[k+1],positions[k]

def route(positions,vec,frame,a,b):
    p=positions.index(a)
    q=positions.index(b)
    path=[]
    if q>p+1:
        path=list(range(q-1,p,-1))
    elif q<p-1:
        path=list(range(q,p-1))
    for k in path:
        swap(vec,frame,positions,k)
    return path

def execute(operations,psi,initial_frame,restore):
    # positions[physical index] = logical label.
    positions=list(INITIAL_ORDER)
    logical=psi.copy()
    frame=initial_frame.copy()
    physical=frame*np.array([logical[j] for j in positions])
    swaps=0
    rotations=0
    frame_adjustments=0
    worst=0.
    for op in operations:
        if op[0]=='rot':
            _,a,b,theta,phi=op
            G=two_level(a,b,theta,phi)
            logical=G@logical
            path=route(positions,physical,frame,a,b)
            swaps+=len(path)
            p=positions.index(a)
            q=positions.index(b)
            if abs(p-q)!=1:raise AssertionError('Routing failed')
            shift=np.angle(frame[q])-np.angle(frame[p])
            if abs(np.angle(np.exp(1j*shift)))>1e-12:
                frame_adjustments+=1
            phys_gate=two_level(p,q,theta,phi+shift)
            physical=phys_gate@physical
            rotations+=1
            if restore:
                for k in reversed(path):
                    swap(physical,frame,positions,k)
                swaps+=len(path)
        elif op[0]=='diag':
            _,angles=op
            diag=np.exp(1j*np.asarray(angles))
            logical=diag*logical
            physical=np.asarray([diag[j] for j in positions])*physical
        else:
            raise AssertionError('Unknown operation')
        expected=frame*np.asarray([logical[j] for j in positions])
        worst=max(worst,float(np.max(np.abs(expected-physical))))
        if abs(np.linalg.norm(physical)-1)>1e-11:
            raise AssertionError('Lost normalization')
    return {'swaps':swaps,'rotations':rotations,
            'frame_adjustments':frame_adjustments,
            'max_state_error':worst,'final_mapping':positions}

def workload(rng,count,pattern):
    out=[]
    favorite=(0,7)
    for _ in range(count):
        if rng.random()<0.15:
            out.append(('diag',rng.uniform(-np.pi,np.pi,size=D).tolist()))
            continue
        if pattern=='hotspot' and rng.random()<0.8:
            a,b=favorite
        elif pattern=='local':
            k=int(rng.integers(0,D-1))
            a,b=INITIAL_ORDER[k:k+2]
        else:
            a,b=map(int,rng.choice(D,size=2,replace=False))
        theta=float(rng.uniform(-np.pi,np.pi))
        phi=float(rng.uniform(-np.pi,np.pi))
        out.append(('rot',a,b,theta,phi))
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trials',type=int,default=1000)
    p.add_argument('--depth',type=int,default=64)
    p.add_argument('--seed',type=int,default=126)
    p.add_argument('--out',type=Path,default=Path('results/a126_lazy_spin_routing.json'))
    a=p.parse_args()
    if a.trials<1 or a.depth<1:p.error('trials/depth must be positive')
    rng=np.random.default_rng(a.seed)
    records=[]
    for pattern in ('uniform','hotspot','local'):
        total_static=total_lazy=total_rot=0
        max_error=0.
        wins=ties=losses=0
        for trial in range(a.trials):
            psi=rng.normal(size=D)+1j*rng.normal(size=D)
            psi/=np.linalg.norm(psi)
            f=np.exp(1j*rng.uniform(-np.pi,np.pi,size=D))
            ops=workload(rng,a.depth,pattern)
            baseline=execute(ops,psi,f,True)
            lazy=execute(ops,psi,f,False)
            max_error=max(max_error,baseline['max_state_error'],lazy['max_state_error'])
            total_static+=baseline['swaps']
            total_lazy+=lazy['swaps']
            total_rot+=lazy['rotations']
            if lazy['swaps']<baseline['swaps']:wins+=1
            elif lazy['swaps']==baseline['swaps']:ties+=1
            else:losses+=1
        r={'workload':pattern,'trials':a.trials,'depth':a.depth,
           'static_swaps':total_static,'lazy_swaps':total_lazy,
           'two_level_rotations':total_rot,
           'swap_reduction_fraction':1-total_lazy/max(total_static,1),
           'lazy_wins':wins,'ties':ties,'lazy_loses':losses,
           'max_frame_aligned_state_error':max_error}
        records.append(r)
        print('A126_POINT',json.dumps(r),flush=True)
    result={'status':'PASS_LAZY_ROUTING' if all(r['max_frame_aligned_state_error']<1e-11 for r in records) else 'FAIL',
      'initial_logical_labels_in_physical_order':list(INITIAL_ORDER),
      'records':records,
      'limitations':[
        'Only logical two-level rotations and diagonal gates; native multitone X8 is not used under changed mapping.',
        'All physical swaps and adjacent rotations are exact and noiseless.',
        'Initial per-level frame is arbitrary and known; drive phase changes are assumed free.',
        'An additional cost to restore or recompile the mapping before other native operations is not included.',
        'Routing uses a simple local greedy rule and is not globally optimized.',
        'This is not a proof of a hardware runtime or Kickmix cost advantage.'
      ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A126_RESULT',json.dumps({'status':result['status'],
        'workloads':[{k:r[k] for k in ('workload','swap_reduction_fraction','max_frame_aligned_state_error')} for r in records],
        'output':str(a.out)}),flush=True)
    if result['status']=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
