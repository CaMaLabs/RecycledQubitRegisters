#!/usr/bin/env python3
"""K103: exact cancellation of cost-class involutions across disjoint gates.

A pair of identical CCX, CCZ, or CSWAP unitaries cancels when every
intervening instruction acts on disjoint qubits. Conservative proof:
U^2=I and operators on disjoint supports commute. Break at every
unsupported instruction, classical control, or shared qubit operation.

This is a source-level candidate scan. The actual Kickmix score depends
on executed gates; FULL official verification required for any claim.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
INV={'X':1,'CX':2,'CCX':3,'CCZ':3,'CSWAP':3,'SWAP':2}
COST={'CCX','CCZ','CSWAP'}
PAT=re.compile(r'^([A-Z][A-Z0-9_]*)\s+((?:q\d+\s*)+)$')
Q=re.compile(r'^q(\d+)$')

def parse(s):
    m=PAT.fullmatch(s.strip())
    if not m:return None
    op=m.group(1)
    if op not in INV:return None
    words=m.group(2).split()
    if len(words)!=INV[op]:return None
    qs=[]
    for word in words:
        q=Q.fullmatch(word)
        if not q:return None
        qs.append(int(q.group(1)))
    if len(set(qs))!=len(qs):return None
    if op=='CCX':key=(op,*sorted(qs[:2]),qs[2])
    elif op=='CCZ':key=(op,*sorted(qs))
    elif op=='CSWAP':key=(op,qs[0],*sorted(qs[1:]))
    elif op=='SWAP':key=(op,*sorted(qs))
    else:key=(op,*qs)
    return (op,frozenset(qs),key)

def scan(lines,max_lookback):
    # Keep original line indices in active; removed gates are excluded.
    output=list(lines)
    active=[]
    pairs=[]
    for idx,line in enumerate(lines):
        gate=parse(line)
        if gate is None:
            # No commuting past comments, condition boundaries,
            # phase gates or unsupported source syntax.
            active.clear()
            continue
        op,support,key=gate
        found=None
        if op in COST:
            passed=0
            for prev in reversed(active):
                passed+=1
                if passed>max_lookback:break
                older=parse(lines[prev])
                if older is None:break
                if older[2]==key:
                    found=prev
                    break
                if older[1]&support:
                    break
        if found is not None:
            pairs.append({'gate':op,'first_line':found+1,'second_line':idx+1,
                          'crossed_active_gates':passed-1,
                          'support':sorted(support)})
            output[found]=''
            output[idx]=''
            active.remove(found)
        else:
            active.append(idx)
        # Cap memory to a generous neighborhood. This cannot affect
        # correctness, only completeness of opportunity discovery.
        if len(active)>max_lookback*2:
            active=active[-max_lookback*2:]
    return output,pairs

def selftest():
    cases=[
      (['CCX q0 q1 q2\n','CX q3 q4\n','CCX q1 q0 q2\n'],1),
      (['CCX q0 q1 q2\n','CX q2 q3\n','CCX q0 q1 q2\n'],0),
      (['CCZ q0 q1 q2\n','X q4\n','CCZ q2 q0 q1\n'],1),
      (['CSWAP q0 q1 q2\n','X q3\n','CSWAP q0 q2 q1\n'],1),
      (['CCX q0 q1 q2\n','PUSH_CONDITION b0\n','CCX q0 q1 q2\n'],0),
      (['CCX q0 q1 q2\n','Z_POW q3 0.2\n','CCX q0 q1 q2\n'],0),
      (['CCX q0 q1 q2\n','CCX q0 q1 q2\n'],1),
      (['CCX q0 q1 q2\n','CX q3 q4 if b0\n','CCX q0 q1 q2\n'],0),
    ]
    for lines,num in cases:
        result,pairs=scan(lines,100)
        assert len(pairs)==num,(lines,pairs)
    print('K103_SELFTEST PASS 8 structural cancellation tests',flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k103/results/helios_cost_involution_cancel.kmx')
    p.add_argument('--max-lookback',type=int,default=2048)
    a=p.parse_args()
    if a.max_lookback<1:p.error('max-lookback >=1')
    selftest()
    raw=a.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Immutable baseline SHA mismatch')
    lines=raw.decode('utf-8').splitlines(keepends=True)
    output,pairs=scan(lines,a.max_lookback)
    new=''.join(output).encode()
    counts={k:sum(p['gate']==k for p in pairs) for k in COST}
    report={'status':'UNVERIFIED_CANDIDATE' if pairs else 'NO_COST_CANCELLATIONS',
      'baseline_sha256':sha,'candidate_sha256':hashlib.sha256(new).hexdigest(),
      'lines':len(lines),'cancellation_pairs':len(pairs),
      'removed_cost_gates':2*len(pairs),
      'pair_counts':counts,'events':pairs,
      'proof':'Each pair is the same self-inverse gate; intermediate gates act only on disjoint qubits. All unsupported instructions are barriers.',
      'note':'No dynamic score or candidate validity established. Run staged official verifier if candidate produced.'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if pairs:a.out.write_bytes(new)
    print('K103_RESULT',json.dumps({k:v for k,v in report.items() if k not in ('events','proof')}),flush=True)
    print('K103_EXAMPLES',json.dumps(pairs[:12]),flush=True)
if __name__=='__main__':main()
