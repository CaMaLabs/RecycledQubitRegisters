#!/usr/bin/env python3
"""K106: exact cancellation of equal Toffolis across commuting XOR gates.

A target-XOR operation (X,CX,CCX) is a reversible update t^=f(controls).
Two such operations commute when neither writes any controls of the other.
Thus identical CCX gates can cancel even across shared-target operations.
All unsupported operations, phase gates, classical control, comments and
declarations are barriers. Candidate is NOT score-verified.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
OPS={'X':1,'CX':2,'CCX':3,'CCZ':3,'CSWAP':3,'SWAP':2}
P=re.compile(r'^([A-Z][A-Z0-9_]*)\s+((?:q\d+\s*)+)$')
def parse(s):
    m=P.fullmatch(s.strip())
    if not m or m.group(1) not in OPS:return None
    op=m.group(1);args=m.group(2).split()
    if len(args)!=OPS[op]:return None
    qs=[int(t[1:]) for t in args]
    if len(set(qs))!=len(qs):return None
    key=(op,*sorted(qs[:2]),qs[2]) if op=='CCX' else (op,*qs)
    return op,qs,key

def commute(toffoli,other):
    _,xs,_=toffoli;op,ys,_=other
    c=set(xs[:2]);t=xs[2]
    if not (set(xs)&set(ys)):return True
    if op in ('X','CX','CCX'):
        return ys[-1] not in c and t not in ys[:-1]
    return False

def scan(lines,lookback):
    parsed=[parse(s) for s in lines]
    removed=set();active=[];events=[]
    for i,g in enumerate(parsed):
        if g is None:
            active.clear();continue
        if g[0]=='CCX':
            for step,j in enumerate(reversed(active)):
                if step>=lookback:break
                prior=parsed[j]
                if prior[2]==g[2]:
                    removed.add(i);removed.add(j)
                    active.remove(j)
                    events.append({'first_line':j+1,'second_line':i+1,
                                   'crossed_gates':step,'controls':sorted(g[1][:2]),
                                   'target':g[1][2]})
                    break
                if not commute(g,prior):break
            if i not in removed:active.append(i)
        else:active.append(i)
        if len(active)>lookback*3:active=active[-lookback*3:]
    return [s for i,s in enumerate(lines) if i not in removed],events

def act(line,bits):
    op,qs,_=parse(line);b=list(bits)
    if op=='X':b[qs[0]]^=1
    elif op=='CX':b[qs[1]]^=b[qs[0]]
    elif op=='CCX':b[qs[2]]^=b[qs[0]]&b[qs[1]]
    else:raise ValueError(op)
    return tuple(b)

def equivalent(a,b):
    for x in range(32):
        initial=tuple((x>>i)&1 for i in range(5))
        result=[]
        for seq in (a,b):
            state=initial
            for line in seq:state=act(line,state)
            result.append(state)
        if result[0]!=result[1]:return False
    return True

def selftest():
    tests=[
      (['CCX q0 q1 q2','CX q3 q2','CCX q1 q0 q2'],1),
      (['CCX q0 q1 q2','X q2','CCX q1 q0 q2'],1),
      (['CCX q0 q1 q2','CCX q3 q4 q2','CCX q0 q1 q2'],1),
      (['CCX q0 q1 q2','CX q2 q3','CCX q0 q1 q2'],0),
      (['CCX q0 q1 q2','CX q3 q0','CCX q0 q1 q2'],0),
      (['CCX q0 q1 q2','CCX q2 q3 q4','CCX q0 q1 q2'],0),
      (['CCX q0 q1 q2','HMR q4 b1','CCX q0 q1 q2'],0),
      (['CCX q0 q1 q2','CCX q0 q1 q2'],1),
      (['CCX q0 q1 q2','CX q0 q3','CCX q0 q1 q2'],1)]
    for i,(case,count) in enumerate(tests):
        out,pairs=scan([x+'\n' for x in case],256)
        assert len(pairs)==count,(i,pairs)
        if all(parse(line) and parse(line)[0] in ('X','CX','CCX') for line in case):
            assert equivalent(case,out),f'Failed exact equivalence case {i}'
    print('K106_SELFTEST PASS 9 cases; exhaustive 5-bit equivalence',flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k106/results/helios_xor_cancel.kmx')
    p.add_argument('--lookback',type=int,default=4096)
    a=p.parse_args()
    if a.lookback<1:p.error('lookback >=1')
    selftest()
    raw=a.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Pinned baseline SHA-256 mismatch')
    lines=raw.decode('utf8').splitlines(keepends=True)
    out,events=scan(lines,a.lookback)
    candidate=''.join(out).encode('utf8')
    audit={'status':'UNVERIFIED_CANDIDATE' if events else 'NO_CANCELLATIONS',
      'baseline_sha256':sha,'candidate_sha256':hashlib.sha256(candidate).hexdigest(),
      'cancellation_pairs':len(events),'removed_ccx':2*len(events),
      'events':events,'warning':'Requires official Kickmix conversion and full-domain verification.'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.with_suffix('.audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    if events:a.out.write_bytes(candidate)
    print('K106_RESULT',json.dumps({k:v for k,v in audit.items() if k!='events'}),flush=True)
    print('K106_EXAMPLES',json.dumps(events[:12]),flush=True)
if __name__=='__main__':main()
