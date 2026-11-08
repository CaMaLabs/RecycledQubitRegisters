"""K028 experimental bit-level reversible arithmetic synthesis.

All gates represent Boolean reversible operations X, CX and CCX on mutable wires.
The source registers are retained; output is written into fresh result wires.
This is an experimental building block, NOT a kickmix-compatible circuit export.
"""
from __future__ import annotations
import dataclasses
import hashlib
import json
import random
from collections import Counter

@dataclasses.dataclass(frozen=True)
class Gate:
    op: str
    q: tuple[int, ...]

class Circuit:
    def __init__(self):
        self.n = 0
        self.gates: list[Gate] = []
        self.const1: set[int] = set()
        self.names: dict[str, list[int]] = {}
    def wire(self, one=False):
        i=self.n; self.n+=1
        if one: self.x(i); self.const1.add(i)
        return i
    def reg(self, name, width):
        r=[self.wire() for _ in range(width)]
        self.names[name]=r
        return r
    def x(self, t): self.gates.append(Gate('x',(t,)))
    def cx(self, c, t):
        if c==t: raise ValueError('CX aliases')
        self.gates.append(Gate('cx',(c,t)))
    def ccx(self, a, b, t):
        if len({a,b,t})<3: raise ValueError('CCX aliases')
        self.gates.append(Gate('ccx',(a,b,t)))
    def xor(self, a, b):
        out=self.wire(); self.cx(a,out); self.cx(b,out); return out
    def and_(self, a, b):
        out=self.wire(); self.ccx(a,b,out); return out
    def or_(self,a,b):
        out=self.xor(a,b); self.ccx(a,b,out); return out
    def half(self,a,b): return self.xor(a,b),self.and_(a,b)
    def full(self,a,b,c):
        # compute s = a xor b xor c; carry = ab xor c(a xor b)
        t=self.xor(a,b)
        s=self.xor(t,c)
        k=self.wire();self.ccx(a,b,k);self.ccx(t,c,k)
        return s,k
    def ripple(self,a,b,width):
        z=self.wire(); carry=z; out=[]
        for i in range(width):
            bit,carry=self.full(a[i],b[i],carry)
            out.append(bit)
        return out
    def mul(self,a,b,width,algorithm='schoolbook'):
        """Unsigned low-width product, exact mod 2**width.
        schoolbook repeatedly ripples partial rows;
        carry_save compresses each weight column before a final ripple.
        """
        zero=self.wire()
        rows=[]
        for i,ai in enumerate(a):
            row=[zero]*width
            for j,bj in enumerate(b):
                if i+j<width: row[i+j]=self.and_(ai,bj)
            rows.append(row)
        if algorithm=='schoolbook':
            acc=[zero]*width
            for row in rows: acc=self.ripple(acc,row,width)
            return acc
        if algorithm=='carry_save':
            cols=[[] for _ in range(width)]
            for row in rows:
                for j,q in enumerate(row):
                    if q != zero: cols[j].append(q)
            for k in range(width):
                while len(cols[k])>2:
                    a0=cols[k].pop();b0=cols[k].pop();c0=cols[k].pop()
                    s,carry=self.full(a0,b0,c0)
                    cols[k].append(s)
                    if k+1<width: cols[k+1].append(carry)
            r0=[(col[0] if col else zero) for col in cols]
            r1=[(col[1] if len(col)>1 else zero) for col in cols]
            return self.ripple(r0,r1,width)
        raise ValueError('Unsupported multiplication algorithm')
    def clean_output(self, result):
        """Bennett compute-copy-uncompute: clean every temporary work wire.

        Expects the circuit to contain only source registers and reversible
        computation gates before the call. Returns persistent output wires.
        """
        original=list(self.gates)
        outputs=[self.wire() for _ in result]
        for src,dst in zip(result,outputs): self.cx(src,dst)
        self.gates.extend(reversed(original))
        return outputs
    def evaluate(self,inputs):
        q=[0]*self.n
        for name,value in inputs.items():
            for k,w in enumerate(self.names[name]): q[w]=(int(value)>>k)&1
        for g in self.gates:
            if g.op=='x': q[g.q[0]]^=1
            elif g.op=='cx': q[g.q[1]]^=q[g.q[0]]
            else: q[g.q[2]]^=q[g.q[0]] & q[g.q[1]]
        return q
    def metrics(self):
        ctr=Counter(g.op for g in self.gates)
        d=[0]*self.n
        for g in self.gates:
            depth=max(d[q] for q in g.q)+1
            for q in g.q: d[q]=depth
        return {'qubits':self.n,'x':ctr['x'],'cx':ctr['cx'],'ccx':ctr['ccx'],
                'gates':len(self.gates),'depth':max(d,default=0)}
    def digest(self):
        payload=[(g.op,g.q) for g in self.gates]
        return hashlib.sha256(json.dumps(payload,separators=(',',':')).encode()).hexdigest()

def test(width=6,samples=1000):
    results={}
    for algorithm in ('schoolbook','carry_save'):
        c=Circuit();a=c.reg('a',width);b=c.reg('b',width)
        output=c.clean_output(c.mul(a,b,width,algorithm))
        rng=random.Random(280027)
        cases=[(x,y) for x in range(1<<width) for y in range(1<<width)] if width<=5 else [(rng.randrange(1<<width),rng.randrange(1<<width)) for _ in range(samples)]
        for x,y in cases:
            q=c.evaluate({'a':x,'b':y})
            got=sum(q[w]<<i for i,w in enumerate(output))
            assert got==(x*y)&((1<<width)-1), (algorithm,width,x,y,got)
            assert sum(q[w]<<i for i,w in enumerate(a))==x
            assert sum(q[w]<<i for i,w in enumerate(b))==y
            occupied=set(a+b+output)
            assert all(q[i]==0 for i in range(c.n) if i not in occupied), 'scratch not clean'
        results[algorithm]={'metrics':c.metrics(),'sha256':c.digest(),'cases':len(cases)}
    return results

if __name__=='__main__':
    for width in (3,4,5,6,8):
        print(json.dumps({'width':width,'results':test(width,512)}))
