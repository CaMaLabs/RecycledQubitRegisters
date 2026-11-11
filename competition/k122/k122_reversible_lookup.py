#!/usr/bin/env python3
"""K122 reversible 16-way coefficient lookup. Source-level cost only.

Computes |selector>|target>|00> -> |selector>|target XOR coefficient[selector]>|00>.
Every selector is checked, including random nonzero target states. Output KMx
is a fragment, not a valid invsqrt submission. No score claim.
"""
import argparse,hashlib,json,random
from pathlib import Path
import numpy as np
from numpy.polynomial import Chebyshev,Polynomial
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def coefficients():
    t=np.cos(np.pi*(np.arange(64)+.5)/64);u=(t+1)/2
    rows=[]
    for s in range(16):
        c=Chebyshev.fit(u,1/np.sqrt(1+(s+u)/16),3,domain=[0,1]).convert(kind=Polynomial).coef
        rows.append([round(float(x)*2**32) for x in c])
    return rows

def width(x):
    return max(1,x.bit_length()+1 if x>=0 else (~x).bit_length()+1)

def lookup(values,w):
    mask=(1<<w)-1
    anf=[v&mask for v in values]
    for b in range(4):
        for s in range(16):
            if s&(1<<b):anf[s]^=anf[s^(1<<b)]
    a=4+w;b=a+1
    gates=[]
    def put(op,*q):gates.append((op,q))
    for s,bits in enumerate(anf):
        targets=[4+i for i in range(w) if bits&(1<<i)]
        controls=[i for i in range(4) if s&(1<<i)]
        if not targets:continue
        n=len(controls)
        if n==0:
            for t in targets:put('X',t)
        elif n==1:
            for t in targets:put('CX',controls[0],t)
        elif n==2:
            if len(targets)==1:put('CCX',*controls,targets[0])
            else:
                put('CCX',*controls,a)
                for t in targets:put('CX',a,t)
                put('CCX',*controls,a)
        elif n==3:
            put('CCX',controls[0],controls[1],a)
            put('CCX',a,controls[2],b)
            for t in targets:put('CX',b,t)
            put('CCX',a,controls[2],b)
            put('CCX',controls[0],controls[1],a)
        else:
            put('CCX',controls[0],controls[1],a)
            put('CCX',controls[2],a,b)
            for t in targets:put('CCX',b,controls[3],t)
            put('CCX',controls[2],a,b)
            put('CCX',controls[0],controls[1],a)
    return gates

def apply(gates,x):
    for op,q in gates:
        if op=='X':x^=1<<q[0]
        elif op=='CX':x^=((x>>q[0])&1)<<q[1]
        else:x^=(((x>>q[0])&1)&((x>>q[1])&1))<<q[2]
    return x

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out-dir',type=Path,default=ROOT/'competition/k122/results')
    a=p.parse_args()
    if hashlib.sha256(a.baseline.read_bytes()).hexdigest()!=PIN:raise SystemExit('Baseline hash mismatch')
    a.out_dir.mkdir(parents=True,exist_ok=True)
    rng=random.Random(122)
    rows=coefficients()
    output=[]
    for power in range(4):
        values=[row[power] for row in rows]
        w=max(map(width,values));mask=(1<<w)-1
        gates=lookup(values,w)
        for selector in range(16):
            for y in [0,mask]+[rng.getrandbits(w) for _ in range(10)]:
                inp=selector|(y<<4)
                actual=apply(gates,inp)
                expected=selector|((y^(values[selector]&mask))<<4)
                assert actual==expected,(power,selector,y)
        counts={op:sum(g[0]==op for g in gates) for op in ('X','CX','CCX')}
        path=a.out_dir/f'coefficient_power{power}.kmx'
        path.write_text(''.join(op+' '+' '.join(f'q{q}' for q in qs)+'\n' for op,qs in gates))
        row={'power':power,'selector_bits':4,'output_bits':w,'scratch_bits':2,
             'standalone_wire_count':4+w+2,'gates':counts,
             'tests':192,'fragment':str(path)}
        output.append(row)
        print('K122_LOOKUP',json.dumps(row),flush=True)
    report={'status':'LOOKUP_FRAGMENTS_ONLY','results':output,
       'total_source_ccx':sum(r['gates']['CCX'] for r in output),
       'limitations':['No complete Kickmix circuit generated or scored.',
          'All selector values verified with 12 output-register states each.',
          'Input preservation, reversible coefficient cleanup, signed Horner, phase and full circuit width remain untested.',
          'This is a gate-count baseline, not a proof of resource improvement.']}
    dst=a.out_dir/'report.json'
    dst.write_text(json.dumps(report,indent=2)+'\n')
    print('K122_RESULT',json.dumps({'status':report['status'],
        'total_source_ccx':report['total_source_ccx'],'out':str(dst)}),flush=True)
if __name__=='__main__':main()
