#!/usr/bin/env python3
"""K028: gate-level 27-bit benchmark (not official kickmix cost)."""
from __future__ import annotations
import argparse
import json
import random
from native_arithmetic import Circuit

def run(width: int, cases: int) -> dict:
    rng=random.Random(280027+width)
    vectors=[(0,0),(0,(1<<width)-1),(1,(1<<width)-1),
             ((1<<width)-1,(1<<width)-1),
             ((1<<(width-1)),(1<<(width-1))),
             ((1<<width)-1,1)]
    vectors.extend((rng.randrange(1<<width),rng.randrange(1<<width)) for _ in range(cases))
    records={}
    for alg in ('schoolbook','carry_save'):
        c=Circuit()
        a=c.reg('a',width)
        b=c.reg('b',width)
        computed=c.mul(a,b,width,alg)
        output=c.clean_output(computed)
        protected=set(a+b+output)
        for x,y in vectors:
            q=c.evaluate({'a':x,'b':y})
            z=sum(q[w]<<i for i,w in enumerate(output))
            assert z==((x*y)&((1<<width)-1)), f'{alg}: {x=} {y=} {z=}'
            assert sum(q[w]<<i for i,w in enumerate(a))==x
            assert sum(q[w]<<i for i,w in enumerate(b))==y
            assert not any(q[i] for i in range(c.n) if i not in protected), f'{alg}: uncomputed scratch'
        records[alg]={'metrics':c.metrics(),'sha256':c.digest(),'verified_pairs':len(vectors)}
    s=records['schoolbook']['metrics'];c=records['carry_save']['metrics']
    reduction={k:round(100*(s[k]-c[k])/s[k],3) if s[k] else None for k in ('gates','ccx','cx','qubits','depth')}
    return {'width':width,'status':'PASS','results':records,
            'carry_save_percent_reduction_positive_is_better':reduction,
            'warning':'Logical reversible Boolean gate prototype only; not kickmix format, score or full inverse-square-root validation.'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--widths',default='8,12,16,27')
    p.add_argument('--random-pairs',type=int,default=20)
    a=p.parse_args()
    for width in [int(x) for x in a.widths.split(',')]:
        if not 2<=width<=64: p.error('width must be 2..64')
        print(json.dumps(run(width,a.random_pairs),sort_keys=True),flush=True)
