#!/usr/bin/env python3
"""K121: coefficient-table and multiplier-structure audit for K120 candidates.

Computes actual quantized polynomial coefficients, signed bit widths,
NAF signed-digit sparsity, coefficient diversity, and simple table
bitplane statistics. All these are *structural opportunities*, NOT a
Kickmix gate-count prediction. No quantum circuit is modified.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
from numpy.polynomial import Chebyshev, Polynomial

ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def coefficients(segments,degree,nodes=64):
    t=np.cos(np.pi*(np.arange(nodes)+.5)/nodes)
    u=(t+1)/2
    rows=[]
    for s in range(segments):
        y=1/np.sqrt(1+(s+u)/segments)
        coef=Chebyshev.fit(u,y,degree,domain=[0,1]).convert(kind=Polynomial).coef
        rows.append([float(z) for z in coef])
    return rows

def naf(x):
    n=abs(int(x));out=[]
    while n:
        if n&1:
            digit=2-(n&3) if n>1 else 1
            out.append(digit);n-=digit
        else:out.append(0)
        n//=2
    return out

def signed_width(x):
    # Minimum signed two's-complement bit width.
    x=int(x)
    if x>=0:return max(1,x.bit_length()+1)
    return max(1,(~x).bit_length()+1)

def stage_summary(vals,frac):
    widths=[signed_width(v) for v in vals]
    nafs=[naf(v) for v in vals]
    pop=[sum(z!=0 for z in a) for a in nafs]
    # Count independently differing table bit planes (two's complement),
    # using sufficient common width. Constant planes need no lookup.
    width=max(widths)
    masks=[v&((1<<width)-1) for v in vals]
    varying=[]
    for i in range(width):
        bits={(v>>i)&1 for v in masks}
        if len(bits)>1:varying.append(i)
    return {
      'unique_coefficients':len(set(vals)),
      'min_coefficient':min(vals),'max_coefficient':max(vals),
      'signed_width_bits_min':min(widths),'signed_width_bits_max':max(widths),
      'max_absolute_magnitude_bits':max(abs(v).bit_length() for v in vals),
      'signed_digit_weight_min':min(pop),'signed_digit_weight_max':max(pop),
      'signed_digit_weight_mean':sum(pop)/len(pop),
      'varying_bitplanes':len(varying),
      'varying_bitplane_positions':varying,
      'constant_bitplanes':width-len(varying),
      'worst_case_additions_for_one_constant_if_naf':max(0,max(pop)-1)
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k121/results/coeff_structure.json')
    p.add_argument('--fraction-bits',type=int,default=32)
    p.add_argument('--configs',default='8:4,16:3,16:4')
    a=p.parse_args()
    if a.fraction_bits<1 or a.fraction_bits>100:p.error('invalid fraction-bits')
    sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit('Pinned baseline SHA mismatch')
    reports=[]
    for spec in a.configs.split(','):
        seg,degree=(int(q) for q in spec.split(':'))
        if seg<2 or seg&(seg-1) or degree<1:p.error('configs must be pow2 segments:degree')
        floating=coefficients(seg,degree)
        quantized=[[round(v*(1<<a.fraction_bits)) for v in row] for row in floating]
        columns=list(zip(*quantized))
        stages=[]
        for power,values in enumerate(columns):
            row={'power':power,
                 'evaluation_role':'constant_offset' if power==0 else ('linear_coefficient' if power==1 else 'nonlinear_coefficient'),
                 **stage_summary(values,a.fraction_bits)}
            stages.append(row)
        total_vary=sum(s['varying_bitplanes'] for s in stages)
        result={'segments':seg,'selection_bits':seg.bit_length()-1,
            'degree':degree,'fraction_bits':a.fraction_bits,
            'horner_multiplication_stages':degree,
            'quantized_coefficient_count':seg*(degree+1),
            'total_varying_bitplanes':total_vary,
            'stages':stages,
            'quantized_coefficients':quantized}
        reports.append(result)
        print('K121_CONFIG',json.dumps({k:result[k] for k in (
            'segments','selection_bits','degree','fraction_bits',
            'horner_multiplication_stages','quantized_coefficient_count',
            'total_varying_bitplanes')}),flush=True)
        for s in stages:
            print('K121_STAGE',json.dumps({'segments':seg,'degree':degree,**{
                k:s[k] for k in ('power','unique_coefficients',
                    'signed_width_bits_max','max_absolute_magnitude_bits',
                    'signed_digit_weight_mean','varying_bitplanes',
                    'worst_case_additions_for_one_constant_if_naf')}}),flush=True)
    report={'status':'STRUCTURAL_AUDIT_ONLY','baseline_sha256':sha,
        'configs':reports,'warnings':[
           'NAF sparsity helps only after conditioning on a coefficient; data-dependent table selection is not free.',
           'Bitplane count is not a Kickmix gate count or lower bound.',
           'Cubic Horner still requires three multiplications by variable u, not just by constants.',
           'Coefficient tables may require lookup, reversibility and uncomputation.',
           'No actual quantum circuit, width measurement, or verifier score.' ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K121_RESULT',json.dumps({'status':report['status'],'out':str(a.out)}),flush=True)

if __name__=='__main__':main()
