#!/usr/bin/env python3
"""K110: backward causal-cone profiling of Helios Toffoli-rich regions.

Read-only. For each CCX target, propagate its dependency set backward through
pure reversible gate runs. This is NOT an exact isolated subcircuit extraction:
out-of-cone operations are ignored for dependency analysis only, and cannot
automatically be discarded from a circuit replacement.

The output finds potential bounded function-extraction tasks and their widths.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
ARITY={'X':1,'CX':2,'CCX':3,'SWAP':2,'CSWAP':3}
LINE=re.compile(r'^([A-Z][A-Z0-9_]*)\s+(.*)$')
WIRE=re.compile(r'^q(\d+)$')
def parse(line):
    m=LINE.fullmatch(line.strip())
    if not m:return None
    op=m.group(1)
    if op not in ARITY:return None
    args=m.group(2).split()
    if len(args)!=ARITY[op] or any(WIRE.fullmatch(q) is None for q in args):
        return None
    wires=tuple(int(q[1:]) for q in args)
    if len(wires)!=len(set(wires)):return None
    return (op,wires)

def backward_update(deps,op,wires):
    """Conservative classical backward dependency through reversible gates."""
    if op=='X':return deps
    if op in ('CX','CCX'):
        if wires[-1] in deps:return deps|set(wires[:-1])
        return deps
    if op=='SWAP':
        a,b=wires
        if (a in deps)!=(b in deps):
            return (deps-{a,b})|({b} if a in deps else {a})
        return deps
    if op=='CSWAP':
        c,a,b=wires
        if a in deps or b in deps:return deps|{c,a,b}
        return deps
    raise ValueError(op)

def profile(records,lookback,top,targets):
    # Each CCX line is a seed; use only consecutive parseable reversible gates.
    seeds=[i for i,g in enumerate(records) if g and g[0]=='CCX']
    summaries=[]
    for seed in seeds:
        initial=records[seed][1][-1]
        deps={initial}
        counts=collections.Counter()
        max_width=1
        included_indices=[]
        reached_boundary=False
        start=max(0,seed-lookback)
        for idx in range(seed,start-1,-1):
            g=records[idx]
            if g is None:
                reached_boundary=True
                break
            op,wires=g
            before=deps.copy()
            deps=backward_update(deps,op,wires)
            # A gate affects the output cone if it updates a depended-on
            # target, or exchanges a depended-on wire.
            affected=(wires[-1] in before if op in ('X','CX','CCX')
                      else bool(set(wires)&before))
            if affected:
                counts[op]+=1
                included_indices.append(idx)
            max_width=max(max_width,len(deps))
        if len(included_indices)<2:continue
        summaries.append({
            'seed_line':seed+1,'seed_target':initial,
            'first_reached_line':(included_indices[-1]+1 if included_indices else seed+1),
            'span_lines':seed-(included_indices[-1] if included_indices else seed)+1,
            'dependency_width':len(deps),'max_dependency_width':max_width,
            'dependency_qubits':sorted(deps),
            'cone_gate_counts':dict(counts),
            'cone_cost_gate_count':counts['CCX']+counts['CSWAP'],
            'hit_unknown_barrier':reached_boundary,
            'lookback_limit':lookback
        })
    widths=collections.Counter()
    eligible=collections.Counter()
    for s in summaries:
        bucket=str(s['dependency_width']) if s['dependency_width']<=16 else '17+'
        widths[bucket]+=1
        for cutoff in targets:
            if s['dependency_width']<=cutoff and s['cone_cost_gate_count']>=2:
                eligible[str(cutoff)]+=1
    # Prefer dense, tractable cones with multiple costly gates.
    rank=sorted(summaries,key=lambda r:(
       -(r['cone_cost_gate_count']/max(r['dependency_width'],1)),
       -r['cone_cost_gate_count'],r['dependency_width'],r['seed_line']))
    return {'seed_count':len(seeds),'nontrivial_cones':len(summaries),
      'width_histogram':dict(widths),'cones_with_multiple_expensive_gates_at_width':dict(eligible),
      'top_cones':rank[:top]}

def selftest():
    lines=['CX q0 q1','CCX q1 q2 q3','CX q3 q4','CCX q4 q5 q6']
    records=[parse(x) for x in lines]
    assert backward_update({6},'CCX',(4,5,6))=={4,5,6}
    assert backward_update({4},'CX',(3,4))=={3,4}
    assert backward_update({3},'CCX',(1,2,3))=={1,2,3}
    assert backward_update({1},'CX',(0,1))=={0,1}
    result=profile(records,16,10,(4,8))
    assert result['seed_count']==2
    assert any(c['dependency_width']>=6 for c in result['top_cones'])
    print('K110_SELFTEST PASS four-gate causal-chain tracing',flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    ap.add_argument('--lookback',type=int,default=256)
    ap.add_argument('--top',type=int,default=30)
    ap.add_argument('--out',type=Path,default=ROOT/'competition/k110/results/dependency_cones.json')
    args=ap.parse_args()
    if args.lookback<2 or args.top<1:ap.error('Invalid limits')
    selftest()
    raw=args.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Pinned baseline digest mismatch')
    lines=raw.decode('utf-8').splitlines()
    parsed=[parse(x) for x in lines]
    opcounts=collections.Counter((x[0] if x else 'BARRIER') for x in parsed)
    result=profile(parsed,args.lookback,args.top,(4,6,8,10,12,16))
    report={'status':'AUDIT_ONLY','source_sha256':sha,
        'line_count':len(lines),'lookback':args.lookback,
        'parsed_operation_counts':dict(opcounts),**result,
        'limitations':[
            'Backward dependency width is not the count of wires in an independently replaceable unitary.',
            'Non-cone operations may require preservation when synthesizing a replacement.',
            'Stops at any unsupported line including control flow and phase operations.',
            'Only models the Boolean wire dependencies of X/CX/CCX/SWAP/CSWAP.',
            'No circuit modified or Kaggle score evaluated.'
        ]}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K110_COUNTS',json.dumps({'seeds':result['seed_count'],
        'nontrivial_cones':result['nontrivial_cones'],
        'multiple_cost_cones_by_width':result['cones_with_multiple_expensive_gates_at_width'],
        'width_histogram':result['width_histogram']}),flush=True)
    for item in result['top_cones'][:10]:
        print('K110_CONE',json.dumps(item),flush=True)
    print('K110_RESULT',json.dumps({'status':'AUDIT_ONLY','out':str(args.out)}),flush=True)
if __name__=='__main__':main()
