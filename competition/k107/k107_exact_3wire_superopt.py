#!/usr/bin/env python3
"""K107: exact 3-wire reversible superoptimization (X/CX/CCX).

Enumerates all 3-bit reversible permutations (up to 8!=40320) using
lexicographic Dijkstra (CCX count first, then total gate count). Scans
bounded contiguous X/CX/CCX regions of the immutable Helios baseline
for precisely 3 active qubits. Emits a candidate ONLY when an isolated
3-wire window can be replaced by an equivalent circuit with fewer CCX
gates; it may then remove extra X/CX as a secondary criterion.

All gates are purely classical reversible permutations: their action is
exact on arbitrary superpositions, with no additional relative phases.
No unsupported instruction is crossed; all replacement qubits remain
within the window's original wire set. Official Kickmix validation needed.
"""
from __future__ import annotations
import argparse,hashlib,heapq,json,re,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
PAT=re.compile(r'^(X|CX|CCX)\s+((?:q\d+\s*)+)$')
EXPECTED={'X':1,'CX':2,'CCX':3}
ID=tuple(range(8))

def decode(s):
    m=PAT.fullmatch(s.strip())
    if m is None:return None
    op=m.group(1)
    qs=tuple(map(lambda x:int(x[1:]),m.group(2).split()))
    if len(qs)!=EXPECTED[op] or len(set(qs))!=len(qs):return None
    return op,qs

def gate_table(op,args):
    output=[]
    for state in range(8):
        bits=[(state>>j)&1 for j in range(3)]
        if op=='X':
            bits[args[0]]^=1
        elif op=='CX':
            bits[args[1]]^=bits[args[0]]
        elif op=='CCX':
            bits[args[2]]^=bits[args[0]]&bits[args[1]]
        output.append(sum(v<<j for j,v in enumerate(bits)))
    return tuple(output)

def gate_set():
    gates=[]
    for t in range(3):gates.append(('X',(t,),gate_table('X',(t,)),0))
    for c in range(3):
        for t in range(3):
            if c!=t:gates.append(('CX',(c,t),gate_table('CX',(c,t)),0))
    for t in range(3):
        c=[k for k in range(3) if k!=t]
        gates.append(('CCX',(c[0],c[1],t),gate_table('CCX',(c[0],c[1],t)),1))
    return gates

def compose(current,gate):
    # Gate is applied AFTER current permutation.
    return tuple(gate[v] for v in current)

def synth():
    gates=gate_set()
    # Track (CCX count, total gate count) lexicographically.
    costs={ID:(0,0)}
    previous={}
    pq=[(0,0,ID)]
    while pq:
        ccx,length,state=heapq.heappop(pq)
        if (ccx,length)!=costs[state]:continue
        for k,(op,qs,g,penalty) in enumerate(gates):
            nxt=compose(state,g)
            v=(ccx+penalty,length+1)
            if v<costs.get(nxt,(10**9,10**9)):
                costs[nxt]=v
                previous[nxt]=(state,k)
                heapq.heappush(pq,(*v,nxt))
    return costs,previous,gates

def window_perm(ops,wire_order):
    lookup={q:i for i,q in enumerate(wire_order)}
    out=ID
    for op,qs in ops:
        local=tuple(lookup[q] for q in qs)
        out=compose(out,gate_table(op,local))
    return out

def reconstruct(state,previous,gates,wires):
    result=[]
    while state!=ID:
        state,k=previous[state]
        op,qs,_,_=gates[k]
        result.append(f'{op} '+' '.join(f'q{wires[i]}' for i in qs)+'\n')
    result.reverse()
    return result

def candidates(lines,max_window,costs,previous,gates):
    ops=[decode(x) for x in lines]
    found=[]
    # Every contiguous X/CX/CCX sequence is a safe region. Consider windows
    # up to max_window gates and no more than 3 involved physical qubits.
    for start,item in enumerate(ops):
        if item is None:continue
        used=set()
        cur=[]
        ccx=0
        for stop in range(start,min(start+max_window,len(lines))):
            gate=ops[stop]
            if gate is None:break
            new=used|set(gate[1])
            if len(new)>3:break
            used=new
            cur.append(gate)
            ccx+=gate[0]=='CCX'
            if len(used)<3 or ccx<1:continue
            wires=tuple(sorted(used))
            permutation=window_perm(cur,wires)
            best=costs[permutation]
            old=(ccx,len(cur))
            # Conservative: only promote strictly smaller CCX count.
            if best[0]>=old[0]:continue
            replacement=reconstruct(permutation,previous,gates,wires)
            found.append({'start':start,'end':stop+1,
                'original_ccx':ccx,'original_length':len(cur),
                'replacement_ccx':best[0],'replacement_length':best[1],
                'ccx_saved':ccx-best[0],'wires':wires,'replacement':replacement,
                'original':[line.rstrip() for line in lines[start:stop+1]]})
    return found

def selftest(costs,previous,gates):
    assert len(costs)==40320, f'Expected 40320 reversible 3-bit permutations; got {len(costs)}'
    tests=[
        [('CCX',(0,1,2)),('CCX',(1,0,2))],
        [('CCX',(0,1,2)),('X',(2,)),('CCX',(0,1,2))],
        [('CCX',(0,1,2)),('CX',(0,2)),('CCX',(0,1,2))],
    ]
    for ops in tests:
        original=window_perm(ops,(0,1,2))
        out=reconstruct(original,previous,gates,(0,1,2))
        assert window_perm([decode(x) for x in out],(0,1,2))==original
        assert costs[original][0]<=sum(op=='CCX' for op,_ in ops)
    print('K107_SELFTEST PASS full permutation coverage and 3 witness circuits',flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k107/results/helios_3wire_synth.kmx')
    p.add_argument('--window',type=int,default=48)
    p.add_argument('--max-rewrites',type=int,default=25)
    a=p.parse_args()
    if a.window<2 or a.max_rewrites<1:p.error('Invalid window/max-rewrites')
    start_time=time.monotonic()
    raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit(f'Baseline digest mismatch {sha}')
    costs,prev,gates=synth()
    selftest(costs,prev,gates)
    lines=raw.decode('utf-8').splitlines(keepends=True)
    found=candidates(lines,a.window,costs,prev,gates)
    found.sort(key=lambda x:(-x['ccx_saved'],x['replacement_length'],x['start']))
    selected=[]
    for proposal in found:
        if any(not (proposal['end']<=x['start'] or proposal['start']>=x['end']) for x in selected):
            continue
        selected.append(proposal)
        if len(selected)>=a.max_rewrites:break
    out=list(lines)
    for item in sorted(selected,key=lambda x:x['start'],reverse=True):
        out[item['start']:item['end']]=item['replacement']
    new=''.join(out).encode('utf8')
    report={'status':'UNVERIFIED_CANDIDATE' if selected else 'NO_CHEAPER_3WIRE_WINDOWS',
        'baseline_sha256':sha,'candidate_sha256':hashlib.sha256(new).hexdigest(),
        'permutations_synthesized':len(costs),'windows_with_potential_savings':len(found),
        'rewrites_applied':len(selected),'source_ccx_saved':sum(x['ccx_saved'] for x in selected),
        'total_lines_before':len(lines),'total_lines_after':len(out),
        'selected':selected,'runtime_seconds':round(time.monotonic()-start_time,3),
        'warning':'Three-wire logical equivalence does not establish Kickmix validity or an executed score improvement. Run official verifier.'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if selected:a.out.write_bytes(new)
    print('K107_RESULT',json.dumps({k:v for k,v in report.items() if k!='selected'}),flush=True)
    print('K107_EXAMPLES',json.dumps([{
        'start_line':x['start']+1,'end_line':x['end'],'wires':x['wires'],
        'original_ccx':x['original_ccx'],'replacement_ccx':x['replacement_ccx'],
        'old_length':x['original_length'],'new_length':x['replacement_length'],
        'replacement':[x.strip() for x in x['replacement']]
    } for x in selected[:8]]),flush=True)
if __name__=='__main__':main()
