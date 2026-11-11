#!/usr/bin/env python3
"""K117 offline exponent/mantissa range-reduction feasibility experiment.

This is a classical design experiment, NOT a legal standalone replacement
for Kickmix input loading. All x bits remain necessary. We fit Chebyshev
polynomials to inverse sqrt on normalized m=x/2**floor(log2(x)) in [1,2),
then estimate degree/error and validate candidates against every integer
x in [1, 3133452]. Exponent parity remains in a reversible implementation.

No quantum cost, register count, intermediate truncation, or Kickmix
verification is established by this floating-point screening.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
from numpy.polynomial.chebyshev import chebfit, chebval

ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
EPS=2**-24

def choose_coefficients(degree:int, nodes:int):
    k=np.arange(nodes,dtype=np.float64)
    t=np.cos(np.pi*(k+0.5)/nodes)
    m=(t+3.0)/2.0
    return chebfit(t,1.0/np.sqrt(m),degree)

def eval_interval(coeffs, samples):
    m=np.linspace(1.0,2.0,samples,dtype=np.float64)
    approx=chebval(2*m-3,coeffs)
    ref=1.0/np.sqrt(m)
    errors=np.abs(approx-ref)/ref
    i=int(np.argmax(errors))
    return float(errors[i]),float(m[i])

def full_integer_check(coeffs,n,batch):
    worst_rel=0.0
    worst_x=0
    failure_count=0
    max_abs_phase=0.0
    for start in range(1,n+1,batch):
        stop=min(n+1,start+batch)
        xs=np.arange(start,stop,dtype=np.float64)
        mant,exponents=np.frexp(xs)
        normalized=2.0*mant
        # y=x^-1/2 = 2^(-e/2)*m^-1/2 with m in [1,2).
        # np.ldexp handles even exponent and odd parity with sqrt(2) factor.
        e=exponents-1
        scale=np.ldexp(np.ones_like(xs),-(e//2))
        scale*=np.where(e%2==0,1.0,1/math.sqrt(2))
        approximation=chebval(2*normalized-3,coeffs)*scale
        exact=1/np.sqrt(xs)
        absolute=np.abs(approximation-exact)
        relative=absolute/exact
        ratio=relative/EPS
        idx=int(np.argmax(relative))
        if relative[idx]>worst_rel:
            worst_rel=float(relative[idx]);worst_x=int(xs[idx])
        failure_count+=int(np.count_nonzero(ratio>=1))
        max_abs_phase=max(max_abs_phase,float(np.max(absolute)))
    return {'worst_relative_error':worst_rel,
            'worst_input':worst_x,
            'relative_tolerance':EPS,
            'worst_error_fraction_of_tolerance':worst_rel/EPS,
            'surrogate_violations':failure_count,
            'maximum_absolute_phase_error_turns':max_abs_phase}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    ap.add_argument('--out',type=Path,default=ROOT/'competition/k117/results/range_reduction.json')
    ap.add_argument('--max-x',type=int,default=3133452)
    ap.add_argument('--degrees',default='4,6,8,9,10,11,12,14')
    ap.add_argument('--nodes',type=int,default=128)
    ap.add_argument('--grid',type=int,default=100001)
    ap.add_argument('--batch',type=int,default=262144)
    a=ap.parse_args()
    if a.max_x<1 or a.nodes<4 or a.grid<101 or a.batch<1:ap.error('Invalid bounds')
    sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit('Pinned Helios baseline hash mismatch')
    degrees=sorted(set(int(x.strip()) for x in a.degrees.split(',')))
    if any(d<0 or d>=a.nodes for d in degrees):ap.error('degree must be >=0 and < nodes')
    rows=[]
    best=None
    for degree in degrees:
        coefficients=choose_coefficients(degree,a.nodes)
        error,argmax=eval_interval(coefficients,a.grid)
        row={'degree':degree,'normalized_max_relative_error':error,
             'relative_error_as_fraction_of_allowed':error/EPS,
             'worst_normalized_mantissa':argmax,
             'passes_half_tolerance_on_grid':error<=EPS/2}
        rows.append(row)
        print('K117_DEGREE',json.dumps(row),flush=True)
        if best is None and row['passes_half_tolerance_on_grid']:
            best=(degree,coefficients)
    checked=None
    if best is not None:
        checked=full_integer_check(best[1],a.max_x,a.batch)
        checked['degree']=best[0]
        print('K117_FULL_INTEGER',json.dumps(checked),flush=True)
    else:print('K117_FULL_INTEGER',json.dumps({'status':'NO_DEGREE_MET_HALF_TOLERANCE'}),flush=True)
    report={'status':'OFFLINE_DESIGN_ONLY',
       'baseline_sha256':sha,'domain':[1,a.max_x],
       'relative_tolerance':EPS,'normalization':'x=2^e*m, 1<=m<2',
       'exponent_scaling':'2**(-floor(e/2)) * (1/sqrt(2) if e odd else 1)',
       'fit':'Chebyshev least-squares at Gauss nodes on [1,2]',
       'degrees':rows,'full_integer_validation':checked,
       'limitations':[
           'Double precision numerical screening is not a formal approximation-error certificate.',
           'No fixed-point rounding, coherent exponent extraction, phase rotation synthesis or scratch cleanup modeled.',
           'The original 22-qubit x register must be preserved exactly in Kickmix.',
           'External classical preprocessing cannot be injected into the official submitted circuit.',
           'Polynomial degree does not imply Toffoli cost or score reduction.',
           'Official phase-turn tolerance and score must be verified after implementing a circuit.'
       ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K117_RESULT',json.dumps({'status':report['status'],'preferred_degree':best[0] if best else None,
        'full_integer_violations':checked['surrogate_violations'] if checked else None,
        'out':str(a.out)}),flush=True)

if __name__=='__main__':main()
