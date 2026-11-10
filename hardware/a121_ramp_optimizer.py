#!/usr/bin/env python3
"""A121: ramp optimization + numerical convergence for A120's spin-7/2 model.

Uses a deterministic, dimensionless RWA model. Only the single raised-cosine
ramp parameter is optimized; no claim of global pulse-shape optimality.
Cost of ideal diagonal correction, relabeling, hardware control and noise not
included. Objective is fidelity with an optional normalized-duration budget.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
import a120_pulse_envelope_screen as a120
import a119_spectral_spin_control as a119

def eval_ramp(spacing, ramp, steps, t2, scale):
    r=float(ramp)
    result=a120.measure(a119.PAR,r,scale,spacing,steps,t2)
    return {'ramp':r,'fidelity':float(result['fidelity']),
            'coherent_fidelity':float(result['coherent_fidelity']),
            'duration':float(result['duration']),
            'unitarity_error':float(result['unitarity_error'])}

def optimize(spacing, max_ramp, steps, t2, scale, grid_count):
    # Explicit grid ensures the optimizer is not trusted if objective is oscillatory.
    grid=np.linspace(0,max_ramp,grid_count)
    samples=[eval_ramp(spacing,r,steps,t2,scale) for r in grid]
    top=max(samples,key=lambda x:x['fidelity'])
    dr=max_ramp/(grid_count-1)
    lower=max(0.,top['ramp']-dr)
    upper=min(max_ramp,top['ramp']+dr)
    if upper>lower:
        opt=minimize_scalar(lambda r:-eval_ramp(spacing,r,steps,t2,scale)['fidelity'],
                            bounds=(lower,upper),method='bounded',
                            options={'xatol':1e-5,'maxiter':30})
        refined=eval_ramp(spacing,opt.x,steps,t2,scale)
    else:refined=top
    best=max([top,refined],key=lambda x:x['fidelity'])
    return best,samples

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--spacings',type=float,nargs='+',default=[10.,20.,40.])
    p.add_argument('--grid-count',type=int,default=9)
    p.add_argument('--max-ramp',type=float,default=.5)
    p.add_argument('--steps',type=int,default=240)
    p.add_argument('--check-steps',type=int,nargs='+',default=[120,480])
    p.add_argument('--scale',type=float,default=1.)
    p.add_argument('--t2',type=float,default=100.)
    p.add_argument('--out',type=Path,default=Path('results/a121_ramp_optimization.json'))
    a=p.parse_args()
    if (a.steps<16 or a.grid_count<3 or not 0<a.max_ramp<=.5
        or a.scale<=0 or a.t2<=0 or any(x<=0 for x in a.spacings)
        or any(n<16 for n in a.check_steps)):
        p.error('Invalid parameters')
    records=[]
    for spacing in a.spacings:
        best,samples=optimize(spacing,a.max_ramp,a.steps,a.t2,a.scale,a.grid_count)
        independent=[eval_ramp(spacing,best['ramp'],n,a.t2,a.scale)
                     | {'steps':n} for n in sorted(set(a.check_steps+[a.steps]))]
        delta=max(x['fidelity'] for x in independent)-min(x['fidelity'] for x in independent)
        base=eval_ramp(spacing,0.,a.steps,a.t2,a.scale)
        record={'spacing':spacing,'baseline_square':base,'best':best,
                'fidelity_gain':best['fidelity']-base['fidelity'],
                'numerical_check':independent,
                'max_fidelity_spread_across_steps':delta,
                'grid':samples}
        records.append(record)
        print('A121_POINT',json.dumps({'spacing':spacing,
            'best_ramp':best['ramp'],'best_fidelity':best['fidelity'],
            'best_duration':best['duration'],
            'square_fidelity':base['fidelity'],
            'numerical_spread':delta}),flush=True)
    report={'status':'PASS_PARAMETER_SEARCH','method':'Grid plus bounded local refinement of one envelope parameter',
            'integration_steps':a.steps,'t2_proxy':a.t2,'scale':a.scale,
            'records':records,
            'limitations':['Optimizes only the raised-cosine ramp, not arbitrary waveforms',
                'Convergence checks are not experimental validation',
                'End-of-gate T2 proxy, ideal phase correction, and free logical relabeling',
                'No realistic spectral calibration, leakage, Lindblad evolution, or hardware electronics',
                'Results do not establish superior physical spin-qudit computing or Kaggle improvement']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('A121_RESULT',json.dumps({'status':report['status'],'points':len(records),
        'out':str(a.out)}),flush=True)

if __name__=='__main__':main()
