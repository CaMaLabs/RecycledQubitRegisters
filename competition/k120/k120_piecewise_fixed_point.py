#!/usr/bin/env python3
"""K120 offline piecewise fixed-point inverse-square-root arithmetic screening.
No Kickmix circuit is generated. All 22 input qubits must be preserved.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from numpy.polynomial import Chebyshev,Polynomial
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
TOL=2**-24
def coefficients(segments,degree,nodes=64):
    t=np.cos(np.pi*(np.arange(nodes)+0.5)/nodes);u=(t+1)/2
    return [tuple(float(z) for z in Chebyshev.fit(
        u,1/np.sqrt(1+(s+u)/segments),degree,domain=[0,1]
    ).convert(kind=Polynomial).coef) for s in range(segments)]
def check(xs,coef,segments,frac):
    coeffs=[[round(v*(1<<frac)) for v in row] for row in coef]
    maximum=0.;worst=None;violations=0;count=0
    for x in xs:
        x=int(x);count+=1;e=x.bit_length()-1
        rem=x-(1<<e)
        seg=min(segments-1,(rem*segments)>>e)
        u=(((rem*segments)-(seg<<e))<<frac)>>e
        c=coeffs[seg];v=c[-1]
        for a in reversed(c[:-1]):v=((v*u)>>frac)+a
        y=math.ldexp(v/(1<<frac),-(e//2))
        if e&1:y/=math.sqrt(2)
        ref=1/math.sqrt(x);error=abs(y-ref)/ref
        if error>maximum:maximum,worst=error,x
        violations+=error>=TOL
    return {'tested':count,'worst_relative_error':maximum,'worst_x':worst,
       'tolerance_fraction':maximum/TOL,'violations':violations}
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k120/results/piecewise_fixed_point.json')
    p.add_argument('--max-x',type=int,default=3133452)
    p.add_argument('--segments',default='8,16')
    p.add_argument('--degrees',default='2,3,4,5')
    p.add_argument('--fraction-bits',default='24,28,32,36')
    p.add_argument('--sample',type=int,default=22000)
    p.add_argument('--full-best',action='store_true')
    a=p.parse_args()
    if hashlib.sha256(a.baseline.read_bytes()).hexdigest()!=PIN:raise SystemExit('Pinned baseline hash mismatch')
    if a.max_x<1 or a.sample<100:p.error('Invalid bounds')
    ss=sorted(set(map(int,a.segments.split(','))))
    ds=sorted(set(map(int,a.degrees.split(','))))
    bs=sorted(set(map(int,a.fraction_bits.split(','))))
    if any(s<2 or s&(s-1) for s in ss):p.error('Segments must be powers of 2')
    if any(d<0 for d in ds) or any(b<8 for b in bs):p.error('Invalid degree/precision')
    xs=set(int(x) for x in np.linspace(1,a.max_x,a.sample))
    for e in range(a.max_x.bit_length()):
        origin=1<<e
        for s in range(max(ss)+1):
            edge=origin+(origin*s)//max(ss)
            for x in (edge-2,edge-1,edge,edge+1,edge+2):
                if 1<=x<=a.max_x:xs.add(x)
    xs=sorted(xs);rows=[];viable=[]
    for seg in ss:
        for degree in ds:
            co=coefficients(seg,degree)
            for f in bs:
                r=check(xs,co,seg,f)
                row={'segments':seg,'segment_bits':seg.bit_length()-1,
                   'degree':degree,'frac_bits':f,
                   'coefficient_count':seg*(degree+1),'multiply_stages':degree,**r}
                rows.append(row)
                print('K120_SCREEN',json.dumps(row),flush=True)
                if r['violations']==0 and r['tolerance_fraction']<.5:viable.append(row)
    viable.sort(key=lambda r:(r['degree'],r['frac_bits'],r['coefficient_count']))
    best=viable[0] if viable else None
    full=None
    if a.full_best and best:
        full=check(range(1,a.max_x+1),coefficients(best['segments'],best['degree']),best['segments'],best['frac_bits'])
        full.update({k:best[k] for k in ('segments','degree','frac_bits')})
        print('K120_FULL',json.dumps(full),flush=True)
    report={'status':'OFFLINE_ONLY','sample_count':len(xs),'rows':rows,
       'best_sample':best,'full_domain':full,
       'limitations':['No score improvement or Kickmix circuit demonstrated.',
         'Floating-point reference and fixed-point Horner surrogate, not a formal phase-error proof.',
         'Lookup, multiplication, reversible cleanup and phase synthesis resource costs are not measured.',
         'Input register must retain all required 22 qubits.']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K120_RESULT',json.dumps({'status':report['status'],'best_sample':best,'full_domain':full,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
