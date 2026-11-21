#!/usr/bin/env python3
"""K168 exact Q14 K149 lookup and Q14 affine CSD schedule cost screen.

The Q14 64-entry lookup is an exact reversible X/CX/CCX XOR oracle with
coherent segment control and no coefficient registers. Affine multiplication,
normalization, Newton updates, and K157 measurement cleanup are NOT integrated.
"""
import argparse, collections, hashlib, json, math, random
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"

def lookup_values():
    return ([round(16384/math.sqrt(1+(j+.5)/32)) for j in range(32)]
           +[round(16384/math.sqrt(2+2*(j+.5)/32)) for j in range(32)])

def coefficients():
    out=[]
    for j in range(8):
        m0,m1=((1+j/4,1+(j+1)/4) if j<4
               else (2+2*(j-4)/4,2+2*(j-3)/4))
        out.append((round(16384/math.sqrt(m0)),
                    round(16384*(1/math.sqrt(m0)-1/math.sqrt(m1))/(m1-m0))))
    return out

def csd(v):
    out=[];i=0
    while v:
        if v&1:
            digit=2-(v&3);out.append([i,digit]);v-=digit
        v//=2;i+=1
    return out

def anf(values):
    assert len(values)==8
    terms=collections.defaultdict(list)
    for bit in range(15):
        a=[(v>>bit)&1 for v in values]
        for k in range(3):
            for m in range(8):
                if m&(1<<k):a[m]^=a[m^(1<<k)]
        for m,yes in enumerate(a):
            if yes:terms[m].append(bit)
    return terms

def circuit():
    # q0..2 local address; q3..5 segment; q6..20 XOR output.
    # q21..24 are reusable work: intermediate segment, match, monomial and final.
    addr=list(range(3));seg=list(range(3,6));out=list(range(6,21))
    intermediate,match,aux,final=21,22,23,24
    ref=lookup_values();g=[];segments=[]
    for j in range(8):
        tables=ref[8*j:8*(j+1)]
        poly=anf(tables)
        neg=[('X',seg[i]) for i in range(3) if not ((j>>i)&1)]
        prefix=(neg+[('CCX',seg[0],seg[1],intermediate),
                     ('CCX',intermediate,seg[2],match),
                     ('CCX',seg[0],seg[1],intermediate)]+neg[::-1])
        block=prefix[:]
        for mask,targets in sorted(poly.items()):
            if mask==0:
                block += [('CX',match,out[b]) for b in targets]
            else:
                controls=[addr[k] for k in range(3) if(mask>>k)&1]
                if len(controls)==1:
                    c=controls[0]
                    block += ([('CCX',match,c,intermediate)]
                         +[('CX',intermediate,out[b]) for b in targets]
                         +[('CCX',match,c,intermediate)])
                elif len(controls)==2:
                    a,b=controls
                    chain=[('CCX',a,b,intermediate),
                           ('CCX',match,intermediate,aux)]
                    block+=chain+[('CX',aux,out[b]) for b in targets]+chain[::-1]
                else:
                    a,b,c=controls
                    chain=[('CCX',a,b,intermediate),
                           ('CCX',intermediate,c,aux),
                           ('CCX',match,aux,final)]
                    block+=chain+[('CX',final,out[b]) for b in targets]+chain[::-1]
        block+=prefix[::-1]
        count=collections.Counter(op for op,*_ in block)
        segments.append({'segment':j,'CCX':count['CCX'],'CX':count['CX'],
                         'X':count['X'],'monomials':len(poly),'table':tables})
        g+=block
    return g,segments,{'index_bits':3,'segment_bits':3,'output_bits':15,
                        'scratch':4,'total_wires':25}

def execute(state,gates):
    for op,*a in gates:
        if op=='X':state^=1<<a[0]
        elif op=='CX':state^=((state>>a[0])&1)<<a[1]
        elif op=='CCX':state^=(((state>>a[0])&1)&((state>>a[1])&1))<<a[2]
        else:raise ValueError(op)
    return state

def verify():
    gates,segments,resource=circuit()
    lookup=lookup_values();rng=random.Random(168);tested=0
    for segment in range(8):
        for j in range(8):
            value=lookup[8*segment+j]
            for target in (0,32767,rng.randrange(32768)):
                initial=j|(segment<<3)|(target<<6)
                expected=j|(segment<<3)|((target^value)<<6)
                after=execute(initial,gates)
                assert after==expected,(segment,j,target,after^expected)
                assert execute(after,reversed(gates))==initial
                tested+=1
    c=collections.Counter(op for op,*_ in gates)
    assert (tested,c['CCX'],resource['scratch'])==(192,240,4)
    return {'CCX':c['CCX'],'CX':c['CX'],'X':c['X'],
            'cases':tested,'per_segment':segments,'resources':resource}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,
        default=Path('competition/k098/results/helios_immutable.kmx'))
    p.add_argument('--out',type=Path,
        default=Path('competition/k168/results/q14_cost.json'))
    p.add_argument('--selftest',action='store_true')
    a=p.parse_args()
    lookup=verify()
    slopes=[{'segment':i,'intercept':y,'slope':s,
             'signed_shifts':csd(s),'CSD_terms':len(csd(s))}
            for i,(y,s) in enumerate(coefficients())]
    print('K168_SELFTEST PASS exact Q14 lookup ROM, coherent selector, arbitrary targets, scratch clean',flush=True)
    print('K168_LOOKUP',json.dumps({k:v for k,v in lookup.items() if k!='per_segment'}),flush=True)
    for seg in lookup['per_segment']:
        print('K168_SEGMENT',json.dumps({'segment':seg['segment'],
          'lookup_CCX':seg['CCX'],'lookup_CX':seg['CX'],
          'affine_CSD_terms':slopes[seg['segment']]['CSD_terms']}),flush=True)
    if a.selftest:return
    sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
    report={'status':'EXACT_Q14_LOOKUP_ONLY_AFFINE_INTERPOLATION_UNPRICED',
      'baseline_sha256':sha,'lookup':lookup,'affine_CSD_schedule':slopes,
      'limitations':['Q14 exact table read uses K149 constants and 6-bit coherent address.',
       'Real Q14 affine interpolation and full Newton arithmetic remain unimplemented.',
       'Per-segment CCX is static cost of a complete conditional block, not expected dynamic execution.',
       'No costed hybrid routing, complete 62-qubit schedule, or official Kickmix verification.',
       'K157 measurement-assisted cleanup remains a separate, active experiment.']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K168_RESULT',json.dumps({'Q14_lookup_CCX':lookup['CCX'],
      'scratch':lookup['resources']['scratch'],'affine_full_cost_known':False,
      'hybrid_routing_verified':False,'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
