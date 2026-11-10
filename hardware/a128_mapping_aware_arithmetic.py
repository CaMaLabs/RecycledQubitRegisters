#!/usr/bin/env python3
"""A128: compare restore-and-native vs mapping-aware adjacent-swap arithmetic.

The native two-layer X8 pulse is only assumed valid at the canonical
logical-to-physical mapping. For a changed mapping, alternative arithmetic
uses an exact permutation synthesized from adjacent physical SWAPs, preserving
the current mapping. Both methods are simulated state-vector exactly.

Costs are *models*, not calibrated gates. Generic arithmetic SWAPs are
implemented as ideal level permutations in this simulation, not physical
pi-pulses; their phase corrections, leakage, and fidelity are not simulated.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
D=8
L2P=(0,2,4,6,7,5,3,1)
CANON=tuple(L2P.index(p) for p in range(D))
C=np.array([1,1j,1j,1j,1j,1j,1j,1],complex)[list(L2P)]
X=np.roll(np.eye(D,dtype=complex),1,axis=0)
NATIVE=np.diag(np.conj(C))@X

def gate(p,q,angle,phase):
    g=np.eye(D,dtype=complex)
    a=np.cos(angle/2);b=np.sin(angle/2)
    g[p,p]=g[q,q]=a
    g[p,q]=-1j*b*np.exp(-1j*phase)
    g[q,p]=-1j*b*np.exp(1j*phase)
    return g

def swap(state,frame,mapping,k,move_map=True):
    state[k],state[k+1]=state[k+1],state[k]
    frame[k],frame[k+1]=frame[k+1],frame[k]
    if move_map:mapping[k],mapping[k+1]=mapping[k+1],mapping[k]

def permute_slots(state,frame,mapping,target_map):
    n=0
    for p,label in enumerate(target_map):
        q=mapping.index(label)
        while q>p:
            swap(state,frame,mapping,q-1)
            n+=1;q-=1
    return n

def generic_increment(state,frame,mapping,direction):
    # desired physical destination index p gets previous input amplitude
    # from position of logical label mapping[p]-direction (mod 8).
    sources=[mapping.index((label-direction)%D) for label in mapping]
    # Adjacent-swap sort current position tokens [0..7] to target source order.
    tokens=list(range(D))
    count=0
    for p,target in enumerate(sources):
        q=tokens.index(target)
        while q>p:
            swap(state,frame,mapping,q-1,move_map=False)
            tokens[q-1],tokens[q]=tokens[q],tokens[q-1]
            q-=1;count+=1
    return count

def physical_native(state,frame,mapping,direction):
    v=np.asarray([state[mapping.index(k)] for k in range(D)])
    f=np.asarray([frame[mapping.index(k)] for k in range(D)])
    if direction==1:
        v=NATIVE@v
        f=np.conj(C)*np.roll(f,1)
    else:
        v=NATIVE.conj().T@v
        f=np.roll(C*f,-1)
    for k in range(D):
        p=mapping.index(k)
        state[p]=v[k];frame[p]=f[k]

def simulate(ops,psi,phase,policy):
    mapping=list(CANON)
    frame=np.array([phase[k] for k in mapping],complex)
    state=frame*np.array([psi[k] for k in mapping])
    ideal=psi.copy()
    routing_swaps=arith_swaps=restoration_swaps=native_calls=rotations=0
    worst=0.
    for op in ops:
        if op[0]=='rot':
            _,a,b,angle,phi=op
            ideal=gate(a,b,angle,phi)@ideal
            p,q=mapping.index(a),mapping.index(b)
            path=(list(range(q-1,p,-1)) if q>p+1 else
                  list(range(q,p-1)) if q<p-1 else [])
            for k in path:swap(state,frame,mapping,k)
            routing_swaps+=len(path)
            p,q=mapping.index(a),mapping.index(b)
            phi_eff=phi+np.angle(frame[q])-np.angle(frame[p])
            state=gate(p,q,angle,phi_eff)@state
            rotations+=1
        else:
            direction=1 if op[0]=='inc' else -1
            ideal=(X if direction==1 else X.conj().T)@ideal
            if policy=='reset':
                restoration_swaps+=permute_slots(state,frame,mapping,CANON)
                physical_native(state,frame,mapping,direction)
                native_calls+=1
            elif policy=='generic':
                arith_swaps+=generic_increment(state,frame,mapping,direction)
            elif policy=='hybrid':
                # Greedy choose control-cost proxy, including immediate map
                # restoration if native is chosen. Conservative: does not
                # exploit potential future mapping changes.
                test=list(mapping)
                restoration_distance=0
                for p,label in enumerate(CANON):
                    q=test.index(label)
                    while q>p:
                        test[q],test[q-1]=test[q-1],test[q]
                        q-=1;restoration_distance+=1
                sources=[mapping.index((label-direction)%D) for label in mapping]
                arith_distance=sum(sources[i]>sources[j]
                                   for i in range(D) for j in range(i+1,D))
                if restoration_distance*simulate.swap_cost+simulate.native_cost < arith_distance*simulate.swap_cost:
                    restoration_swaps+=permute_slots(state,frame,mapping,CANON)
                    physical_native(state,frame,mapping,direction)
                    native_calls+=1
                else:
                    arith_swaps+=generic_increment(state,frame,mapping,direction)
            else:raise ValueError(policy)
        worst=max(worst,float(np.max(abs(state-frame*np.asarray([ideal[k] for k in mapping])))))
    restoration_swaps+=permute_slots(state,frame,mapping,CANON)
    return {'routing_swaps':routing_swaps,'arith_swaps':arith_swaps,
            'restoration_swaps':restoration_swaps,'native_calls':native_calls,
            'rotations':rotations,'max_error':worst}

def sample(rng,depth,fraction):
    out=[]
    for _ in range(depth):
        if rng.random()<fraction:
            out.append(('inc' if rng.random()<.5 else 'dec',))
        else:
            a,b=map(int,rng.choice(D,2,replace=False))
            out.append(('rot',a,b,float(rng.uniform(-np.pi,np.pi)),
                        float(rng.uniform(-np.pi,np.pi))))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--trials',type=int,default=200)
    ap.add_argument('--depth',type=int,default=64)
    ap.add_argument('--seed',type=int,default=128)
    ap.add_argument('--swap-cost',type=float,default=0.9423)
    ap.add_argument('--native-cost',type=float,default=2.4666)
    ap.add_argument('--fractions',nargs='+',type=float,default=[.1,.25,.5,.75])
    ap.add_argument('--out',type=Path,default=Path('results/a128_mapping_aware_arithmetic.json'))
    a=ap.parse_args()
    if a.trials<1 or a.depth<1 or a.swap_cost<=0 or a.native_cost<=0 or any(not 0<=f<=1 for f in a.fractions):
        ap.error('invalid arguments')
    simulate.swap_cost=a.swap_cost;simulate.native_cost=a.native_cost
    rng=np.random.default_rng(a.seed)
    report=[]
    for fraction in a.fractions:
        stats={name:dict(routing_swaps=0,arith_swaps=0,restoration_swaps=0,native_calls=0,rotations=0,max_error=0.) for name in ('reset','generic','hybrid')}
        for _ in range(a.trials):
            z=rng.normal(size=D)+1j*rng.normal(size=D);z/=np.linalg.norm(z)
            phase=np.exp(1j*rng.uniform(-np.pi,np.pi,D))
            ops=sample(rng,a.depth,fraction)
            for policy in stats:
                r=simulate(ops,z,phase,policy)
                for k in r:
                    if k=='max_error':stats[policy][k]=max(stats[policy][k],r[k])
                    else:stats[policy][k]+=r[k]
        summary={}
        for policy,r in stats.items():
            swaps=r['routing_swaps']+r['arith_swaps']+r['restoration_swaps']
            duration_proxy=swaps*a.swap_cost +r['native_calls']*a.native_cost
            summary[policy]={**r,'total_swaps':swaps,'duration_proxy':duration_proxy}
        row={'arithmetic_fraction':fraction,'methods':summary}
        report.append(row)
        print('A128_POINT',json.dumps({'fraction':fraction,
            'costs':{k:round(v['duration_proxy'],3) for k,v in summary.items()},
            'max_errors':{k:v['max_error'] for k,v in summary.items()}}),flush=True)
    status='PASS_MAPPING_AWARE_ARITHMETIC' if all(
        v['max_error']<1e-11 for row in report for v in row['methods'].values()) else 'FAIL'
    result={'status':status,'swap_cost_proxy':a.swap_cost,'native_cost_proxy':a.native_cost,
      'results':report,'limitations':[
        'Generic adjacent SWAPs are ideal permutations, not physical pi-pulse simulations.',
        'Swap cost 0.9423 and native arithmetic cost 2.4666 are illustrative A116/A121-derived normalized proxies, not hardware-calibrated.',
        'Both native and arbitrary-mapping generic arithmetic are fully phase-frame aligned mathematically.',
        'The hybrid choice is myopic and not globally optimal.',
        'No noise, gate calibration, Qiskit hardware execution or Kickmix improvement is implied.'
      ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A128_RESULT',json.dumps({'status':status,'output':str(a.out),'points':len(report)}),flush=True)
    if status=='FAIL':raise SystemExit(1)
if __name__=='__main__':main()
