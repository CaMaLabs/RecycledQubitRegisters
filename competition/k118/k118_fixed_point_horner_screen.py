#!/usr/bin/env python3
"""K118 offline normalized-invsqrt fixed-point Horner resource screening.
No Kickmix circuit or leaderboard improvement is claimed.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from numpy.polynomial import Chebyshev,Polynomial
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
TOL=2.0**-24
def coefficients(degree,nodes=128):
    t=np.cos(np.pi*(np.arange(nodes)+0.5)/nodes)
    c=np.polynomial.chebyshev.chebfit(t,1/np.sqrt((t+3)/2),degree)
    return [float(z) for z in Chebyshev(c,domain=[0,1]).convert(kind=Polynomial).coef]
def trial(xs,degree,frac):
    coeff=coefficients(degree)
    coeff_int=[round(c*(1<<frac)) for c in coeff]
    largest=0.;worst=None;violations=0;tested=0
    for x in xs:
        x=int(x);e=x.bit_length()-1
        u=((x-(1<<e))<<frac)//(1<<e)
        value=coeff_int[-1]
        for c in reversed(coeff_int[:-1]):
            value=((value*u)>>frac)+c
        y=math.ldexp(value/(1<<frac),-(e//2))
        if e&1:y/=math.sqrt(2)
        ref=1/math.sqrt(x)
        err=abs(y-ref)/ref
        if err>largest:largest,worst=err,x
        violations+=err>=TOL;tested+=1
    return dict(degree=degree,frac_bits=frac,tested=tested,
       worst_relative_error=largest,worst_x=worst,
       tolerance_fraction=largest/TOL,violations=violations)
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k118/results/fixed_point_screen.json')
    p.add_argument('--max-x',type=int,default=3133452)
    p.add_argument('--scan-points',type=int,default=25000)
    p.add_argument('--degrees',default='9,10')
    p.add_argument('--bits',default='24,28,32,36,40,44')
    p.add_argument('--full-best',action='store_true')
    a=p.parse_args()
    if hashlib.sha256(a.baseline.read_bytes()).hexdigest()!=PIN:raise SystemExit('Baseline hash mismatch')
    xs={1,2,3,a.max_x}
    xs.update(int(x) for x in np.linspace(1,a.max_x,a.scan_points))
    for e in range(a.max_x.bit_length()):
        for x in (2**e-2,2**e-1,2**e,2**e+1,2**e+2):
            if 1<=x<=a.max_x:xs.add(x)
    rows=[]
    for degree in sorted({int(z) for z in a.degrees.split(',')}):
        for bits in sorted({int(z) for z in a.bits.split(',')}):
            r=trial(sorted(xs),degree,bits)
            rows.append(r)
            print('K118_SCREEN',json.dumps(r),flush=True)
    viable=[r for r in rows if r['tolerance_fraction']<=0.5 and r['violations']==0]
    best=min(viable,key=lambda r:(r['degree']*r['frac_bits'],r['frac_bits'])) if viable else None
    full=trial(range(1,a.max_x+1),best['degree'],best['frac_bits']) if a.full_best and best else None
    if full:print('K118_FULL',json.dumps(full),flush=True)
    result={'status':'OFFLINE_ONLY','sample_count':len(xs),'rows':rows,
            'best_screen':best,'full_domain':full,
            'warnings':['Signed fixed-point Horner; no formal rounding proof.',
              'Fractional precision is NOT a claim of physical qubit count.',
              'Quantum reversible multiplication, cleanup and phase gates are not priced.',
              'Input x must remain unchanged. No legal Kickmix circuit generated.']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('K118_RESULT',json.dumps({'status':result['status'],'best_screen':best,
      'full_domain':full,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
