#!/usr/bin/env python3
"""A119: spectral crowding and static noise in spin-7/2 arithmetic.

8-level interaction-picture, rotating-wave model. Each addressed tone drives
all adjacent levels with spin ladder strengths, including off-resonant terms.
A phase-damping T2 proxy is applied at end of gate. Ideal diagonal correction
and logical relabeling are free; no real-device advantage is claimed.
"""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.linalg import expm

N=8
S=3.5
SEQ=tuple((k,) for k in range(6,-1,-1))
PAR=((0,2,4,6),(1,3,5))
def c(k):
    m=k-S
    return float(np.sqrt(S*(S+1)-m*(m+1))/2)
def X8():
    a=np.zeros((N,N),complex)
    for i in range(N):a[(i+1)%N,i]=1
    return a
def duration(edges,scale):
    return max(np.pi/(2*scale*c(k)) for k in edges)
def nominal(groups,scale):
    u=np.eye(N,dtype=complex)
    for edges in groups:
        t=duration(edges,scale)
        h=np.zeros((N,N),complex)
        for k in edges:h[k,k+1]=h[k+1,k]=np.pi/(2*t)
        u=expm(-1j*h*t)@u
    return u
def calibrate(groups,scale):
    u=nominal(groups,scale)
    nxt=np.argmax(abs(u),axis=0)
    order=[0]
    while len(order)<N:
        j=int(nxt[order[-1]])
        if j in order:raise AssertionError('Not an 8-cycle')
        order.append(j)
    if nxt[order[-1]]!=0:raise AssertionError('Cycle closure failed')
    B=np.eye(N,dtype=complex)[:,order]
    w=B.conj().T@u@B
    phase=[w[(j+1)%N,j] for j in range(N)]
    C=np.diag(np.conj(np.roll(phase,1)))
    assert np.max(abs(C@w-X8()))<1e-12
    return B,C,order
def step(edges,scale,spacing,steps,noise):
    t=duration(edges,scale)
    dt=t/steps
    freqs=np.arange(N-1)*spacing
    carrier=freqs[list(edges)]
    drive=np.array([np.pi/(2*t*c(k)) for k in edges])
    gap=freqs[:,None]-carrier[None,:]
    ladd=np.array([c(k) for k in range(N-1)])
    h=np.diag(noise).astype(complex)
    u=np.eye(N,dtype=complex)
    for n in range(steps):
        now=(n+.5)*dt
        g=ladd*(np.exp(1j*gap*now)@drive)
        for k in range(N-1):
            h[k,k+1]=g[k]
            h[k+1,k]=np.conj(g[k])
        u=expm(-1j*h*dt)@u
    return u
def evolve(groups,scale,spacing,steps,noise):
    u=np.eye(N,dtype=complex)
    for edges in groups:u=step(edges,scale,spacing,steps,noise)@u
    return u
def avg_fidelity(actual,target,time,t2):
    w=target.conj().T@actual
    eta=float(np.exp(-time/t2)) if np.isfinite(t2) else 1.
    ent=(eta*abs(np.trace(w))**2+(1-eta)*sum(abs(np.diag(w))**2))/(N*N)
    return float((N*ent+1)/(N+1))
def run(a):
    configs={}
    for label,groups in [('sequential',SEQ),('two_layer',PAR)]:
        B,C,order=calibrate(groups,a.scale)
        configs[label]=(groups,B,C,order,sum(duration(e,a.scale) for e in groups))
    rng=np.random.default_rng(a.seed)
    points=[]
    for spacing in a.spacings:
        record={'spacing_in_drive_units':spacing}
        for label,(groups,B,C,order,total) in configs.items():
            nominal=C@B.conj().T@evolve(groups,a.scale,spacing,a.steps,np.zeros(N))@B
            vals=[]
            for _ in range(a.trials):
                noise=rng.normal(0,a.detuning_std,size=N)
                u=C@B.conj().T@evolve(groups,a.scale,spacing,a.steps,noise)@B
                vals.append(avg_fidelity(u,X8(),total,a.t2))
            record[label]={
                'duration_inverse_drive_units':total,
                'coherent_fidelity':avg_fidelity(nominal,X8(),total,float('inf')),
                't2_proxy_fidelity':avg_fidelity(nominal,X8(),total,a.t2),
                'drift_mean_fidelity':float(np.mean(vals)),
                'drift_p05_fidelity':float(np.quantile(vals,.05))}
        points.append(record)
        print('A119_POINT',json.dumps({'spacing':spacing,
            'sequential_fidelity':record['sequential']['t2_proxy_fidelity'],
            'two_layer_fidelity':record['two_layer']['t2_proxy_fidelity'],
            'sequential_drift_mean':record['sequential']['drift_mean_fidelity'],
            'two_layer_drift_mean':record['two_layer']['drift_mean_fidelity']}),flush=True)
    return {'status':'PASS_MODEL_SWEEP','spin':'7/2','dimension':N,
            'steps':a.steps,'trials':a.trials,'drive_scale':a.scale,
            'detuning_std':a.detuning_std,'t2_inverse_drive_units':a.t2,
            'sequential_encoding':configs['sequential'][3],
            'parallel_encoding':configs['two_layer'][3],'points':points,
            'limitations':[
                'Effective equally spaced spin transitions: not fitted to actual hardware.',
                'Off-target adjacent transition coupling included in rotating-wave approximation.',
                'No measured noise, explicit quadrupole Hamiltonian calibration, or carrier counter-rotating effects.',
                'Ideal free logical basis relabeling and diagonal phase correction.',
                'T2 is a final logical-basis dephasing proxy, not continuous Lindblad evolution.',
                'No leakage outside 8 levels, electronic bandwidth, or optimized pulse shaping.',
                'No physical speedup, increased information capacity or Kaggle gain demonstrated.']}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--spacings',type=float,nargs='+',default=[2,5,10,20,40])
    p.add_argument('--steps',type=int,default=120)
    p.add_argument('--trials',type=int,default=8)
    p.add_argument('--seed',type=int,default=119)
    p.add_argument('--scale',type=float,default=1.)
    p.add_argument('--detuning-std',type=float,default=.01)
    p.add_argument('--t2',type=float,default=100.)
    p.add_argument('--out',type=Path,default=Path('results/a119_spectral_spin_control.json'))
    a=p.parse_args()
    if a.steps<2 or a.trials<1 or a.scale<=0 or a.detuning_std<0 or a.t2<=0 or any(x<0 for x in a.spacings):p.error('Invalid arguments')
    result=run(a)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('A119_RESULT',json.dumps({'status':result['status'],'output':str(a.out),'points':len(result['points'])}),flush=True)
if __name__=='__main__':main()
