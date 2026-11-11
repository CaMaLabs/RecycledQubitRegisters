#!/usr/bin/env python3
"""K113: exact Toffoli common-factor extraction on pinned Helios.

CCX(c,a,t) CCX(c,b,t) ==
CX(a,b) CCX(c,b,t) CX(a,b), for distinct c,a,b,t.

The second CCX may be moved beside the first only if it commutes with
EVERY intervening operation. XOR-update gates commute when neither
writes a control of the other. Unknown lines and all non-XOR gates are
barriers, so conditional/phase operations are never crossed.

Every proposal is checked by exhaustive truth-table equivalence on
its affected wires, including intervening gates. Candidate generation
is NOT official Kickmix verification.
"""
from __future__ import annotations
import argparse,hashlib,json,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
PAT=re.compile(r'^(X|CX|CCX)\s+((?:q\d+\s*)+)$')
ARITY={'X':1,'CX':2,'CCX':3}

def parse(line):
    m=PAT.fullmatch(line.strip())
    if not m:return None
    op=m.group(1)
    q=tuple(int(x[1:]) for x in m.group(2).split())
    if len(q)!=ARITY[op] or len(q)!=len(set(q)):return None
    return op,q

def commute(g,h):
    # Both gates update their final wire with a Boolean function of controls.
    # Neither target may be among the other's controls.
    return g[1][-1] not in h[1][:-1] and h[1][-1] not in g[1][:-1]

def replacement(g,h):
    if g[0]!='CCX' or h[0]!='CCX' or g[1][2]!=h[1][2]:return None
    a=set(g[1][:2]);b=set(h[1][:2])
    if len(a&b)!=1:return None
    c=next(iter(a&b));u=next(iter(a-b));v=next(iter(b-a))
    t=g[1][2]
    return [('CX',(u,v)),('CCX',(c,v,t)),('CX',(u,v))]

def execute(gates,wires):
    idx={w:i for i,w in enumerate(wires)}
    answers=[]
    for n in range(1<<len(wires)):
        x=n
        for op,qs in gates:
            q=tuple(idx[w] for w in qs)
            if op=='X':x^=1<<q[0]
            elif op=='CX':x^=((x>>q[0])&1)<<q[1]
            else:x^=(((x>>q[0])&1)&((x>>q[1])&1))<<q[2]
        answers.append(x)
    return answers

def exhaustive_proof(original,after,max_wires=12):
    wires=sorted(set(w for g in original for w in g[1]))
    assert set(w for g in after for w in g[1])<=set(wires)
    if len(wires)>max_wires:return False, len(wires)
    return execute(original,wires)==execute(after,wires),len(wires)

def selftest():
    g=('CCX',(0,1,3));h=('CCX',(0,2,3))
    repl=replacement(g,h)
    assert repl is not None
    assert exhaustive_proof([g,h],repl)[0]
    between=('CX',(4,3))
    assert commute(h,between)
    assert exhaustive_proof([g,between,h],repl+[between])[0]
    blocking=('CX',(3,4))
    assert not commute(h,blocking)
    for c in range(4):
        for a in range(4):
            for b in range(4):
                t=4
                if len({c,a,b})!=3:continue
                g=('CCX',(c,a,t));h=('CCX',(c,b,t))
                r=replacement(g,h)
                assert r and exhaustive_proof([g,h],r)[0]
    print('K113_SELFTEST PASS factored identity for all distinct 4-wire assignments; commutation checks',flush=True)

def scan(lines,span,max_rewrites,max_proof_wires):
    ops=[parse(line) for line in lines]
    found=[];reasons=collections.Counter()
    for j,h in enumerate(ops):
        if h is None or h[0]!='CCX':continue
        for i in range(j-1,max(-1,j-span-1),-1):
            g=ops[i]
            if g is None:
                reasons['barrier']+=1
                break
            r=replacement(g,h)
            if r is not None:
                original=ops[i:j+1]
                proposed=r+ops[i+1:j]
                passed,width=exhaustive_proof(original,proposed,max_proof_wires)
                if passed:
                    found.append({'start':i,'end':j,'distance':j-i,
                       'wires':sorted(set(w for op,qs in original for w in qs)),
                       'truth_table_width':width,'replacement':r,
                       'original_ccx':sum(op=='CCX' for op,qs in original),
                       'replacement_ccx':sum(op=='CCX' for op,qs in proposed)})
                    reasons['exact_factorings']+=1
                else:reasons['too_wide_or_failed_proof']+=1
            if not commute(h,g):
                reasons['noncommuting_boundary']+=1
                break
    found.sort(key=lambda r:(r['distance'],r['start']))
    chosen=[]
    for item in found:
        if any(item['start']<=old['end'] and old['start']<=item['end'] for old in chosen):
            continue
        chosen.append(item)
        if len(chosen)>=max_rewrites:break
    output=list(lines)
    for entry in sorted(chosen,key=lambda r:r['start'],reverse=True):
        i,j=entry['start'],entry['end']
        convert=lambda g:g[0]+' '+' '.join('q'+str(x) for x in g[1])+'\n'
        output[j:j+1]=[]
        output[i:i+1]=[convert(g) for g in entry['replacement']]
    return output,chosen,found,reasons

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k113/results/helios_ccx_factored.kmx')
    p.add_argument('--span',type=int,default=256)
    p.add_argument('--max-rewrites',type=int,default=64)
    p.add_argument('--max-proof-wires',type=int,default=12)
    a=p.parse_args()
    if a.span<1 or a.max_rewrites<1 or not (4<=a.max_proof_wires<=16):p.error('Invalid bounds')
    selftest()
    raw=a.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Baseline digest mismatch')
    lines=raw.decode('utf8').splitlines(keepends=True)
    changed,selected,all_found,reasons=scan(lines,a.span,a.max_rewrites,a.max_proof_wires)
    output=''.join(changed).encode()
    report={'status':'UNVERIFIED_CANDIDATE' if selected else 'NO_EXACT_FACTORINGS',
        'baseline_sha256':sha,'candidate_sha256':hashlib.sha256(output).hexdigest(),
        'factorable_windows':len(all_found),'selected_rewrites':len(selected),
        'source_ccx_saved':len(selected),'source_cx_added':2*len(selected),
        'search_reasons':dict(reasons),
        'events':[{'start_line':x['start']+1,'end_line':x['end']+1,
                   'distance':x['distance'],'truth_table_width':x['truth_table_width'],
                   'wires':x['wires']} for x in selected],
        'note':'Every selected replacement has an exhaustive local proof. Official Kickmix checks and score improvement still required.'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if selected:a.out.write_bytes(output)
    print('K113_COUNTS',json.dumps({k:report[k] for k in (
        'factorable_windows','selected_rewrites','source_ccx_saved','source_cx_added','search_reasons')}),flush=True)
    print('K113_EXAMPLES',json.dumps(report['events'][:12]),flush=True)
    print('K113_RESULT',json.dumps({'status':report['status'],
       'candidate':str(a.out) if selected else None,
       'audit':str(a.out.with_suffix('.audit.json'))}),flush=True)
if __name__=='__main__':main()
