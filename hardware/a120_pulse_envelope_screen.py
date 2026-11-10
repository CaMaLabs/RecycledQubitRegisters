#!/usr/bin/env python3
"""A120: raised-cosine envelope screen under A119's spectral model.

Equal maximum addressed transition amplitude. Smoothing increases duration
to maintain pi-pulse area. No hardware claim; logical mapping and diagonal
phase corrections are ideal and free. Run alongside a119_spectral_spin_control.py.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.linalg import expm
sys.path.insert(0,str(Path(__file__).resolve().parent))
import a119_spectral_spin_control as a119

N=8

def env(x,r):
    if r==0:return 1.
    if x<r:return .5*(1-np.cos(np.pi*x/r))
    if x>1-r:return .5*(1-np.cos(np.pi*(1-x)/r))
    return 1.

def time_of(edges,r,scale):
    return max(np.pi/(2*scale*a119.c(k)) for k in edges)/(1-r)

def shaped_step(edges,r,scale,spacing,steps):
    T=time_of(edges,r,scale)
    dt=T/steps
    freq=np.arange(N-1)*spacing
    delta=freq[:,None]-freq[list(edges)][None,:]
    tones=np.array([np.pi/(2*T*(1-r)*a119.c(k)) for k in edges])
    coeff=np.array([a119.c(k) for k in range(N-1)])
    h=np.zeros((N,N),dtype=complex)
    u=np.eye(N,dtype=complex)
    for j in range(steps):
        t=(j+.5)*dt
        g=coeff*(np.exp(1j*delta*t)@tones)*env((j+.5)/steps,r)
        for k in range(N-1):
            h[k,k+1]=g[k]
            h[k+1,k]=np.conj(g[k])
        u=expm(-1j*h*dt)@u
    return u

def measure(groups,r,scale,spacing,steps,t2):
    # Ideal on-resonance matching layers commute within themselves, and
    # pulse area is exactly pi/2 per selected edge for every shape.
    B,C,order=a119.calibrate(groups,scale)
    u=np.eye(N,dtype=complex)
    T=0.
    for edges in groups:
        u=shaped_step(edges,r,scale,spacing,steps)@u
        T+=time_of(edges,r,scale)
    effective=C@B.conj().T@u@B
    return {'fidelity':a119.avg_fidelity(effective,a119.X8(),T,t2),
            'coherent_fidelity':a119.avg_fidelity(effective,a119.X8(),T,float('inf')),
            'duration':T,'encoding':order,
            'unitarity_error':float(np.max(abs(effective.conj().T@effective-np.eye(N))))}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--spacings',type=float,nargs='+',default=[10.,20.,40.])
    p.add_argument('--ramps',type=float,nargs='+',default=[0.,.25,.4,.5])
    p.add_argument('--steps',type=int,default=240)
    p.add_argument('--scale',type=float,default=1.)
    p.add_argument('--t2',type=float,default=100.)
    p.add_argument('--out',type=Path,default=Path('results/a120_pulse_envelope_screen.json'))
    a=p.parse_args()
    if a.steps<8 or a.scale<=0 or a.t2<=0 or any(r<0 or r>.5 for r in a.ramps) or any(s<0 for s in a.spacings):p.error('Invalid settings')
    points=[]
    for s in a.spacings:
        for r in a.ramps:
            seq=measure(a119.SEQ,r,a.scale,s,a.steps,a.t2)
            par=measure(a119.PAR,r,a.scale,s,a.steps,a.t2)
            point={'spacing':s,'ramp':r,'sequential':seq,'parallel':par}
            points.append(point)
            print('A120_POINT',json.dumps({'spacing':s,'ramp':r,
                'sequential_fidelity':seq['fidelity'],
                'parallel_fidelity':par['fidelity'],
                'parallel_duration':par['duration']}),flush=True)
    report={'status':'PASS_SIMPLIFIED_PULSE_SCREEN','steps':a.steps,
      't2_proxy':a.t2,'points':points,'method':'Sinusoidal raised-cosine ramps preserve pulse area and peak coupling cap by increasing duration by 1/(1-ramp).',
      'limitations':['Ideal phase correction and free logical basis reordering',
       'Equal transition frequency spacing and simplified RWA controls',
       'No calibrated spin Hamiltonian, pulse bandwidth constraints, leakage, or full decoherence channel',
       'Gate fidelity is an approximate end-gate T2 proxy; this is not a real-device speedup']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('A120_RESULT',json.dumps({'status':report['status'],'points':len(points),'output':str(a.out)}),flush=True)

if __name__=='__main__':main()
