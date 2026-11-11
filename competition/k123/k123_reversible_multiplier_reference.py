#!/usr/bin/env python3
"""K123 exact reversible truncated multiply-accumulate reference construction.

Implements |a,b,p,0> -> |a,b,(p+a*b) mod 2**n,0> with X/CX/CCX,
using conditional high-to-low bit increments. Every output basis state
is reversible, and all scratch bits finish clean. This is a deliberately
simple reference circuit, NOT an optimized quantum multiplier or a
lower bound on its cost. Large widths are counted, not simulated.

Kaggle Helios invsqrt total current resource baseline:
  Q=62, score=95369.00696815242, dynamic CCX ~1243.119
This reference multiplication is compared against an optimistic
Toffoli budget to inform whether further arithmetic development pays.
"""
from __future__ import annotations
import argparse, collections, json, random
from pathlib import Path
SCORE=95369.00696815242
Q=62
BASE_DYNAMIC=1243.118965920014
BASE_NON_TOFF_EQ=SCORE/Q-BASE_DYNAMIC

def mcx(controls,target,scratch):
    n=len(controls)
    if n==1:return [('CX',(controls[0],target))]
    if n==2:return [('CCX',(controls[0],controls[1],target))]
    assert n>=3 and len(scratch)>=n-2
    seq=[('CCX',(controls[0],controls[1],scratch[0]))]
    for i in range(2,n-1):
        seq.append(('CCX',(scratch[i-2],controls[i],scratch[i-1])))
    seq.append(('CCX',(scratch[n-3],controls[-1],target)))
    seq.extend(reversed(seq[:-1]))
    return seq

def build(width):
    if width<2:raise ValueError('width >= 2')
    a=list(range(width))
    b=list(range(width,2*width))
    p=list(range(2*width,3*width))
    scratch=list(range(3*width,4*width))
    gates=[]
    for i in range(width):
        for j in range(width-i):
            k=i+j
            # Update high bits first so increment's controls read old P.
            for bit in range(width-1,k-1,-1):
                controls=[a[j],b[i]]+p[k:bit]
                gates.extend(mcx(controls,p[bit],scratch))
    return gates

def execute(gates,value):
    for op,qs in gates:
        if op=='CX':
            value^=((value>>qs[0])&1)<<qs[1]
        elif op=='CCX':
            value^=(((value>>qs[0])&1)&((value>>qs[1])&1))<<qs[2]
        else:raise ValueError(op)
    return value

def validate(width,gates,random_tests,seed):
    rng=random.Random(seed)
    mask=(1<<width)-1
    exhaustive=width<=5
    if exhaustive:
        scenarios=((a,b,p) for a in range(1<<width)
                 for b in range(1<<width)
                 for p in (0,mask))
        total=2*(1<<width)**2
    else:
        scenarios=((rng.getrandbits(width),rng.getrandbits(width),
                    rng.getrandbits(width)) for _ in range(random_tests))
        total=random_tests
    for a,b,p in scenarios:
        init=a|(b<<width)|(p<<(2*width))
        output=execute(gates,init)
        expected=a|(b<<width)|(((p+a*b)&mask)<<(2*width))
        if output!=expected:
            raise AssertionError(f'Reversible multiply failed n={width}: a={a}, b={b}, p={p}')
    return total,exhaustive

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--widths',default='4,6,8,12,16,24,32')
    parser.add_argument('--tests',type=int,default=1000)
    parser.add_argument('--emit-width',type=int,default=4,
      help='Write a small exact gate fragment (0 to disable)')
    parser.add_argument('--out',type=Path,default=Path('competition/k123/results/reversible_mul_report.json'))
    a=parser.parse_args()
    if a.tests<1:parser.error('tests positive')
    widths=sorted(set(map(int,a.widths.split(','))))
    if min(widths)<2:parser.error('width >=2')
    rows=[]
    for n in widths:
        gates=build(n)
        counts=collections.Counter(op for op,_ in gates)
        tests,exhaustive=validate(n,gates,a.tests,123+n) if n<=8 else (0,False)
        row={'width':n,'declared_wires':4*n,'input_register_wires':3*n,
             'scratch_wires':n,'source_cx':counts['CX'],
             'source_ccx':counts['CCX'],
             'test_cases':tests,'test_mode':'EXHAUSTIVE_a_b_extreme_p' if exhaustive
                    else ('RANDOM' if tests else 'COUNT_ONLY'),
             'exceeds_entire_baseline_dynamic_ccx':counts['CCX']>BASE_DYNAMIC}
        rows.append(row)
        print('K123_MULT',json.dumps(row),flush=True)
        if a.emit_width==n:
            fragment=a.out.parent/f'reversible_mul_{n}bit.kmx'
            fragment.parent.mkdir(parents=True,exist_ok=True)
            fragment.write_text(''.join(op+' '+' '.join(f'q{w}' for w in qs)+'\n'
                                        for op,qs in gates))
            print('K123_FRAGMENT',str(fragment),flush=True)
    result={'status':'REFERENCE_ONLY','baseline':{'qubits':Q,'score':SCORE,
            'dynamic_toffoli_count':BASE_DYNAMIC,'non_toffoli_equivalent':BASE_NON_TOFF_EQ},
           'rows':rows,
           'warnings':[
             'Source CCX counts for this construction are not executed verifier counts.',
             'This is a simple, unoptimized fixed-width modular multiply-add; it is not a lower bound.',
             'Polynomial Horner may exploit short coefficients, truncated products or specialized circuits.',
             'A full invsqrt phase circuit, fixed-point signs, normalization, lookup cleanup, and quantum validity remain untested.',
             'No Kaggle score win has been established.']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('K123_RESULT',json.dumps({'status':result['status'],'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
