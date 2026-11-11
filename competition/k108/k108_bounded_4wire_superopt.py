#!/usr/bin/env python3
"""K108 bounded four-wire reversible synthesis for pinned Helios.

Constructs exact 4-bit permutations for short X/CX/CCX circuits using a
state-capped breadth-first expansion. It then searches contiguous windows
with exactly four (or fewer) physical wires. Candidate replacements must
strictly reduce CCX count. Reversible permutations are exact on all
superpositions because these gates introduce no relative phases.

This is a bounded search, NOT an exhaustive 16! optimization.
"""
from __future__ import annotations
import argparse,hashlib,heapq,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
PAT=re.compile(r'^(X|CX|CCX)\s+((?:q\d+\s*)+)$')
NUM={'X':1,'CX':2,'CCX':3}
IDENTITY=bytes(range(16))
def parse(line):
    m=PAT.fullmatch(line.strip())
    if not m:return None
    qs=tuple(int(word[1:]) for word in m.group(2).split())
    if len(qs)!=NUM[m.group(1)] or len(set(qs))!=len(qs):return None
    return m.group(1),qs

def gates():
    result=[]
    for t in range(4):result.append(('X',(t,),0))
    for c in range(4):
        for t in range(4):
            if c!=t:result.append(('CX',(c,t),0))
    for t in range(4):
        for c in range(4):
            for d in range(c+1,4):
                if t not in (c,d):result.append(('CCX',(c,d,t),1))
    return [(op,qs,penalty,table(op,qs)) for op,qs,penalty in result]

def table(op,qs):
    v=[]
    for x in range(16):
        y=x
        if op=='X':y^=1<<qs[0]
        elif op=='CX':y^=((x>>qs[0])&1)<<qs[1]
        else:y^=(((x>>qs[0])&1)&((x>>qs[1])&1))<<qs[2]
        v.append(y)
    return bytes(v)

def compose(state,gate):
    return bytes(gate[x] for x in state)

def synth(max_depth,max_states):
    library=gates()
    best={IDENTITY:(0,0)}
    predecessor={}
    # Priority order Toffoli count, then length. Cap search exploration.
    pq=[(0,0,IDENTITY)]
    expanded=0
    while pq and expanded<max_states:
        ccx,depth,state=heapq.heappop(pq)
        if best[state]!=(ccx,depth):continue
        expanded+=1
        if depth>=max_depth:continue
        for k,(_,_,weight,permutation) in enumerate(library):
            nxt=compose(state,permutation)
            cost=(ccx+weight,depth+1)
            if cost < best.get(nxt,(10**9,10**9)):
                best[nxt]=cost
                predecessor[nxt]=(state,k)
                heapq.heappush(pq,(*cost,nxt))
    return best,predecessor,library,expanded

def reconstruct(state,predecessor,library,wires):
    out=[]
    while state!=IDENTITY:
        state,k=predecessor[state]
        op,qs,_,_=library[k]
        out.append(f'{op} '+' '.join(f'q{wires[i]}' for i in qs)+'\n')
    return list(reversed(out))

def window_scan(lines,best,predecessor,library,max_window):
    parsed=[parse(x) for x in lines]
    hits=[]
    candidates=[]
    eligible=0
    counts={'contiguous_windows_with_2plus_ccx_on_4_or_fewer_wires':0,
            'candidate_permutation_in_library':0}
    for start,op in enumerate(parsed):
        if op is None:continue
        used=set();sequence=[];ccx=0
        for end in range(start,min(len(parsed),start+max_window)):
            current=parsed[end]
            if current is None:break
            new=used|set(current[1])
            if len(new)>4:break
            used=new
            sequence.append(current)
            ccx+=current[0]=='CCX'
            if len(used)!=4 or ccx<2:continue
            counts['contiguous_windows_with_2plus_ccx_on_4_or_fewer_wires']+=1
            wires=tuple(sorted(used))
            map_wire={q:i for i,q in enumerate(wires)}
            perm=IDENTITY
            for kind,qs in sequence:
                local=tuple(map_wire[q] for q in qs)
                perm=compose(perm,table(kind,local))
            hit=best.get(perm)
            if hit is None:continue
            counts['candidate_permutation_in_library']+=1
            if hit[0]>=ccx:continue
            candidate={'start':start,'end':end+1,'wires':list(wires),
                'source_ccx':ccx,'source_gates':len(sequence),
                'replacement_ccx':hit[0],'replacement_gates':hit[1],
                'saved_ccx':ccx-hit[0],
                'replacement':reconstruct(perm,predecessor,library,wires)}
            candidates.append(candidate)
    candidates.sort(key=lambda r:(-r['saved_ccx'],r['replacement_gates'],r['start']))
    return candidates,counts

def selftest(best,predecessor,library):
    for op,qs,_,perm in library:
        assert perm in best
    for state in list(best.keys())[:100]:
        code=reconstruct(state,predecessor,library,tuple(range(4)))
        got=IDENTITY
        for line in code:
            op,qs=parse(line)
            got=compose(got,table(op,qs))
        assert got==state
    print('K108_SELFTEST PASS 100 reconstruction witnesses',flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k108/results/helios_4wire_bounded.kmx')
    p.add_argument('--depth',type=int,default=4)
    p.add_argument('--max-states',type=int,default=120000)
    p.add_argument('--window',type=int,default=36)
    p.add_argument('--max-rewrites',type=int,default=12)
    a=p.parse_args()
    if not (1<=a.depth<=8) or a.max_states<100 or a.window<3 or a.max_rewrites<1:p.error('Invalid limits')
    t0=time.monotonic()
    raw=a.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Baseline SHA-256 mismatch')
    best,predecessor,library,expanded=synth(a.depth,a.max_states)
    selftest(best,predecessor,library)
    lines=raw.decode('utf-8').splitlines(keepends=True)
    candidates,counts=window_scan(lines,best,predecessor,library,a.window)
    selected=[]
    for x in candidates:
        if any(x['start']<y['end'] and y['start']<x['end'] for y in selected):continue
        selected.append(x)
        if len(selected)>=a.max_rewrites:break
    rewritten=list(lines)
    for x in sorted(selected,key=lambda y:y['start'],reverse=True):
        rewritten[x['start']:x['end']]=x['replacement']
    output=''.join(rewritten).encode('utf-8')
    report={'status':'UNVERIFIED_CANDIDATE' if selected else 'NO_BOUNDED_4WIRE_REWRITES',
        'baseline_sha256':sha,'candidate_sha256':hashlib.sha256(output).hexdigest(),
        'library_states':len(best),'expanded_states':expanded,
        'library_depth_limit':a.depth,'library_state_limit':a.max_states,
        'windows':counts,'candidate_windows':len(candidates),'selected_rewrites':len(selected),
        'source_ccx_saved':sum(x['saved_ccx'] for x in selected),'examples':selected[:10],
        'elapsed_seconds':round(time.monotonic()-t0,3),
        'limitations':['Only X/CX/CCX contiguous four-wire windows.',
                       'State-capped search is not exhaustive nor proof of optimality.',
                       'Unverified full-circuit candidate; use Kickmix verifier before score claims.']}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if selected:a.out.write_bytes(output)
    print('K108_RESULT',json.dumps({k:v for k,v in report.items() if k not in ('examples','limitations')}),flush=True)
    print('K108_EXAMPLES',json.dumps([{'first_line':x['start']+1,'last_line':x['end'],
          'saved_ccx':x['saved_ccx'],'wires':x['wires']} for x in selected[:10]]),flush=True)

if __name__=='__main__':main()
