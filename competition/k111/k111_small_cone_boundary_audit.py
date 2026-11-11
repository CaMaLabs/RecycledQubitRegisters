#!/usr/bin/env python3
"""K111: rank small K110 causal cones and audit their replacement boundaries.

Read only. Reconstruct each candidate's original reversible run, identify
its input support, backward cone, touched-but-untracked outputs, and whether
the cone can be extracted without crossing a non-disjoint operation.
K110 backward cones are NOT independently replaceable circuits.
"""
from __future__ import annotations
import argparse,hashlib,json,collections,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
ARITY={'X':1,'CX':2,'CCX':3,'SWAP':2,'CSWAP':3}
P=re.compile(r'^([A-Z][A-Z0-9_]*)\s+(.*)$')
Q=re.compile(r'^q(\d+)$')
def parse(line):
    m=P.fullmatch(line.strip())
    if not m or m.group(1) not in ARITY:return None
    op=m.group(1);w=m.group(2).split()
    if len(w)!=ARITY[op] or any(Q.fullmatch(t) is None for t in w):return None
    qs=tuple(int(t[1:]) for t in w)
    if len(qs)!=len(set(qs)):return None
    return op,qs
def back(deps,gate):
    op,w=gate
    deps=set(deps)
    if op in ('CX','CCX'):
        if w[-1] in deps:deps|=set(w[:-1])
    elif op=='SWAP':
        a,b=w
        if (a in deps)!=(b in deps):
            deps.difference_update({a,b})
            deps.add(b if a in deps else a)
    elif op=='CSWAP' and (w[1] in deps or w[2] in deps):
        deps|=set(w)
    return deps
def trace(records,seed,lookback):
    # Mirrors K110's stop-on-barrier semantics.
    deps={records[seed][1][-1]}
    changed=[]
    barrier=False
    for index in range(seed,max(-1,seed-lookback-1),-1):
        gate=records[index]
        if gate is None:
            barrier=True
            break
        before=set(deps)
        op,w=gate
        deps=back(deps,gate)
        affect=(w[-1] in before if op in ('X','CX','CCX') else bool(set(w)&before))
        if affect:changed.append(index)
    return deps,sorted(changed),barrier
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--lookback',type=int,default=256)
    p.add_argument('--max-width',type=int,default=8)
    p.add_argument('--min-ccx',type=int,default=2)
    p.add_argument('--top',type=int,default=25)
    p.add_argument('--out',type=Path,default=ROOT/'competition/k111/results/small_cone_boundary_audit.json')
    a=p.parse_args()
    raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Baseline hash mismatch')
    lines=raw.decode().splitlines()
    parsed=[parse(x) for x in lines]
    candidates=[]
    for seed,gate in enumerate(parsed):
        if gate is None or gate[0]!='CCX':continue
        deps,changed,hit_barrier=trace(parsed,seed,a.lookback)
        ccx=sum(parsed[i][0]=='CCX' for i in changed)
        if len(deps)>a.max_width or ccx<a.min_ccx:continue
        first=changed[0];last=seed
        touched=set()
        interleaved=[]
        fringe=set()
        for i in range(first,last+1):
            opw=parsed[i]
            if opw is None:continue
            op,qs=opw
            touched.update(qs)
            if i not in changed and set(qs)&deps:
                interleaved.append(i+1)
            if set(qs)&deps:fringe.update(set(qs)-deps)
        # A subcircuit cannot be replaced as a unit if the other gates
        # read or write its wires unless an exact multi-output proof is made.
        unique=set(changed)
        outside_touched=[i+1 for i in range(first,last+1)
            if i not in unique and parsed[i] is not None and
            not set(parsed[i][1]).isdisjoint(touched)]
        row={'seed_line':seed+1,'start_line':first+1,'last_line':last+1,
           'dependency_width':len(deps),'input_dependency_wires':sorted(deps),
           'touched_wires':sorted(touched),'touched_width':len(touched),
           'cone_gate_count':len(changed),'cone_ccx':ccx,
           'interleaved_on_cone_inputs':interleaved[:20],
           'outside_gate_interactions':outside_touched[:20],
           'outside_interaction_count':len(outside_touched),
           'hit_unknown_barrier':hit_barrier,
           'preview':[{'line':i+1,'instruction':lines[i]} for i in changed[:18]],
           'eligible_for_direct_subcircuit_replacement':len(outside_touched)==0 and len(touched)<=a.max_width}
        candidates.append(row)
    candidates.sort(key=lambda x:(
        not x['eligible_for_direct_subcircuit_replacement'],
        x['outside_interaction_count'],
        -x['cone_ccx'],x['touched_width'],x['cone_gate_count']))
    report={'status':'AUDIT_ONLY','sha256':sha,
      'filters':{'max_width':a.max_width,'min_ccx':a.min_ccx,'lookback':a.lookback},
      'candidate_cones':len(candidates),
      'direct_replacement_candidates':sum(x['eligible_for_direct_subcircuit_replacement'] for x in candidates),
      'top':candidates[:a.top],
      'note':'Cones are output dependencies, not independently replaceable unitaries. Direct eligibility is necessary screening only, not a proof.'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K111_COUNTS',json.dumps({'candidate_cones':report['candidate_cones'],
       'direct_replacement_candidates':report['direct_replacement_candidates'],
       'max_width':a.max_width,'min_ccx':a.min_ccx}),flush=True)
    for row in report['top'][:10]:
        print('K111_CONE',json.dumps({k:row[k] for k in ('seed_line','start_line','last_line',
           'dependency_width','touched_width','cone_ccx','outside_interaction_count',
           'eligible_for_direct_subcircuit_replacement')}),flush=True)
    print('K111_RESULT',json.dumps({'status':'AUDIT_ONLY','out':str(a.out)}),flush=True)
if __name__=='__main__':main()
