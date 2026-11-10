#!/usr/bin/env python3
"""A125: virtual-frame dressing restricted to adjacent physical spin levels.

A124 assumed any pair can be directly driven. Here physical spin levels
0..7 have adjacent single-quantum transitions only. Reversible X8 native
arithmetic is retained as a precompiled two-layer primitive (A117), while
two-level rotations are allowed only on physical neighbors. We also count
the routing swaps needed for arbitrary logical pairs, without claiming pulse
optimality or a hardware runtime advantage.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
D=8
ORDER=[0,2,4,6,7,5,3,1]
INV_ORDER={physical:logical for logical,physical in enumerate(ORDER)}
PHYSICAL_PHASE_CORRECTION=np.array([1,1j,1j,1j,1j,1j,1j,1],dtype=complex)
assert len(PHYSICAL_PHASE_CORRECTION)==D and sorted(ORDER)==list(range(D))
C=PHYSICAL_PHASE_CORRECTION[ORDER]
X=np.roll(np.eye(D,dtype=complex),1,axis=0)
V=np.diag(np.conj(C))@X
ADJACENT_LOGICAL_PAIRS=tuple((INV_ORDER[p],INV_ORDER[p+1]) for p in range(D-1))

def gate(a,b,theta,phi):
    u=np.eye(D,dtype=complex)
    v=np.cos(theta/2)
    w=np.sin(theta/2)
    u[a,a]=u[b,b]=v
    u[a,b]=-1j*w*np.exp(-1j*phi)
    u[b,a]=-1j*w*np.exp(1j*phi)
    return u

def route_cost(a,b):
    distance=abs(ORDER[a]-ORDER[b])
    return {'physical_distance':distance,
        'extra_swap_gates_if_routed_and_restored':2*(distance-1),
        'rotation_gates':1}

def run(trials,depth,seed):
    rng=np.random.default_rng(seed)
    max_error=0.
    counts={'increment':0,'decrement':0,'adjacent_rotation':0}
    adjusted=0
    for _ in range(trials):
        psi=rng.normal(size=D)+1j*rng.normal(size=D)
        psi/=np.linalg.norm(psi)
        logical=psi.copy()
        physical=psi.copy()
        frame=np.ones(D,dtype=complex)
        for __ in range(depth):
            action=int(rng.integers(0,3))
            if action==0:
                logical=X@logical
                physical=V@physical
                frame=np.conj(C)*np.roll(frame,1)
                counts['increment']+=1
            elif action==1:
                logical=X.conj().T@logical
                physical=V.conj().T@physical
                frame=np.roll(C*frame,-1)
                counts['decrement']+=1
            else:
                a,b=ADJACENT_LOGICAL_PAIRS[int(rng.integers(0,7))]
                theta=float(rng.uniform(-np.pi,np.pi))
                phi=float(rng.uniform(-np.pi,np.pi))
                # F G F^dag produces a phase-shifted physical-adjacent drive.
                shift=float(np.angle(frame[b])-np.angle(frame[a]))
                logical=gate(a,b,theta,phi)@logical
                physical=gate(a,b,theta,phi+shift)@physical
                if abs(np.angle(np.exp(1j*shift)))>1e-10:adjusted+=1
                counts['adjacent_rotation']+=1
            max_error=max(max_error,float(np.max(abs(physical-frame*logical))))
    routes=[]
    for a in range(D):
        for b in range(a+1,D):
            costs=route_cost(a,b)
            routes.append({'logical_levels':[a,b],**costs})
    hist={}
    for r in routes:
        n=r['physical_distance']
        hist[n]=hist.get(n,0)+1
    status='PASS_ADJACENT_FRAME_DRESSING' if max_error<1e-11 else 'FAIL'
    return {'status':status,'trials':trials,'depth':depth,
        'maximum_frame_aligned_error':max_error,'counts':counts,
        'nonzero_frame_adjustments':adjusted,
        'allowed_physical_edges':[[p,p+1] for p in range(D-1)],
        'corresponding_logical_edges':[list(x) for x in ADJACENT_LOGICAL_PAIRS],
        'physical_distance_histogram':hist,
        'mean_extra_swap_count_all_unordered_pairs':float(np.mean([r['extra_swap_gates_if_routed_and_restored'] for r in routes])),
        'max_extra_swap_count':max(r['extra_swap_gates_if_routed_and_restored'] for r in routes),
        'routing_examples':routes,
        'limits':[
          'Uses ideal native increment and inverse; physical two-layer pulse behavior is not re-simulated.',
          'Only adjacent spin-level rotations are exercised for exact phase-frame validation.',
          'Routing-swap cost is constructive, not a proven lower bound or hardware duration.',
          'SWAP phases and frame updates during routed non-adjacent gates are not implemented or verified.',
          'Hardware phase-control calibration, leakage, spectral crowding, decoherence, and dynamic errors are omitted.',
          'No Kaggle score improvement or physical-qudit speedup is claimed.']}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trials',type=int,default=10000)
    p.add_argument('--depth',type=int,default=24)
    p.add_argument('--seed',type=int,default=125)
    p.add_argument('--out',type=Path,default=Path('results/a125_adjacent_spin_frame.json'))
    a=p.parse_args()
    if a.trials<1 or a.depth<1:p.error('positive trials and depth required')
    r=run(a.trials,a.depth,a.seed)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print('A125_RESULT',json.dumps({k:r[k] for k in (
        'status','trials','depth','maximum_frame_aligned_error','counts',
        'nonzero_frame_adjustments','physical_distance_histogram',
        'mean_extra_swap_count_all_unordered_pairs','max_extra_swap_count')}),flush=True)
    if r['status']=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
