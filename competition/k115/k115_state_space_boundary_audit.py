#!/usr/bin/env python3
"""K115: Kickmix reset/measurement and register-role reconnaissance.

Read-only structural audit pinned to the immutable Helios circuit.
Recognizes R, HMR, BIT_STORE0/1, conditions and 22-qubit input register;
reports operation neighborhoods and per-wire roles. NO claim that an
R/HMR instruction proves a wire separable, clean, or compressible.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
OPER=re.compile(r'^\s*([A-Za-z][A-Za-z0-9_]*)\b')
WIRE=re.compile(r'\bq(\d+)\b')
REG=re.compile(r'^APPEND_TO_REGISTER\s+q(\d+)\s+r(\d+)\s*$')
REG_NAME=re.compile(r'^REGISTER\s+r(\d+)\s+"([^"]+)"\s*$')
EVENTS={'R','HMR','BIT_STORE0','BIT_STORE1','PUSH_CONDITION','POP_CONDITION',
        'BIT_INVERT','NEG','Z_POW'}
COST={'CCX','CCZ','CSWAP','Z_POW'}

def inspect(lines,context):
    operation_counts=collections.Counter()
    per_wire=collections.defaultdict(collections.Counter)
    positions=collections.defaultdict(lambda:collections.defaultdict(list))
    regs=collections.defaultdict(list)
    names={}
    events=[]
    conditioning=0
    condition_max=0
    condition_errors=[]
    for idx,source in enumerate(lines):
        lineno=idx+1
        stripped=source.strip()
        m=OPER.match(source)
        op=m.group(1).upper() if m else 'UNKNOWN'
        operation_counts[op]+=1
        wires=tuple(int(n) for n in WIRE.findall(stripped))
        for wire in set(wires):
            per_wire[wire][op]+=1
            positions[wire][op].append(lineno)
        reg=REG.fullmatch(stripped)
        if reg:regs[int(reg.group(2))].append(int(reg.group(1)))
        name=REG_NAME.fullmatch(stripped)
        if name:names[int(name.group(1))]=name.group(2)
        if op=='PUSH_CONDITION':
            conditioning+=1;condition_max=max(conditioning,condition_max)
        if op=='POP_CONDITION':
            conditioning-=1
            if conditioning<0:condition_errors.append(lineno);conditioning=0
        if op in EVENTS:
            a=max(0,idx-context)
            b=min(len(lines),idx+context+1)
            events.append({'line':lineno,'op':op,'text':stripped,
                'qubits':wires,
                'nearby':[{'line':j+1,'text':lines[j].strip()} for j in range(a,b)]})
    if conditioning:condition_errors.append('Unclosed blocks: '+str(conditioning))
    wire_roles=[]
    for wire in sorted(per_wire):
        c=per_wire[wire]
        appearances=sum(c.values())
        wire_roles.append({
            'wire':wire,'touches':appearances,
            'first':min(p[0] for p in positions[wire].values()),
            'last':max(p[-1] for p in positions[wire].values()),
            'R':c['R'],'HMR':c['HMR'],
            'CCX':c['CCX'],'CCZ':c['CCZ'],
            'CSWAP':c['CSWAP'],
            'CX':c['CX'],'CZ':c['CZ'],
            'Z_POW':c['Z_POW'],
            'measurement_or_reset_sites':sorted(positions[wire]['R']+positions[wire]['HMR']),
            'high_cost_occurrences':sum(c[k] for k in COST),
        })
    return {
        'operations':dict(operation_counts),
        'registers':[{'id':r,'name':names.get(r),'qubits':w,
                      'width':len(w)} for r,w in sorted(regs.items())],
        'wire_roles':wire_roles,
        'block_max_nesting':condition_max,
        'condition_balance_errors':condition_errors,
        'event_counts':dict(collections.Counter(e['op'] for e in events)),
        'events':events,
    }

def selftest():
    lines=[
        'APPEND_TO_REGISTER q0 r0','REGISTER r0 "x"','R q2',
        'HMR q3 b0','PUSH_CONDITION b0','CCX q0 q2 q4',
        'POP_CONDITION','BIT_STORE1 b2'
    ]
    v=inspect(lines,0)
    assert v['registers']==[{'id':0,'name':'x','qubits':[0],'width':1}]
    assert v['event_counts']['R']==1
    assert v['event_counts']['HMR']==1
    assert not v['condition_balance_errors']
    assert v['wire_roles'][2]['R']==1
    print('K115_SELFTEST PASS register and event parser',flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k115/results/state_space_boundaries.json')
    p.add_argument('--context',type=int,default=3)
    p.add_argument('--show',type=int,default=16)
    a=p.parse_args()
    if a.context<0 or a.show<0:p.error('context and show must be nonnegative')
    selftest()
    raw=a.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Pinned baseline SHA mismatch')
    lines=raw.decode('utf-8').splitlines()
    analysis=inspect(lines,a.context)
    inputs={q for r in analysis['registers'] if r['name']=='x' for q in r['qubits']}
    others=[v for v in analysis['wire_roles'] if v['wire'] not in inputs]
    ranked=sorted(others,key=lambda x:(-x['high_cost_occurrences'],-x['touches'],x['wire']))
    report={'status':'READ_ONLY','baseline_sha256':sha,
        **analysis,'input_wires':sorted(inputs),
        'noninput_wires':[w['wire'] for w in others],
        'noninput_wires_ranked_by_expensive_gates':ranked,
        'caveats':[
            'R and HMR semantics require checking Kickmix definitions; this is structural only.',
            'A reset or measurement does not establish that a register is compressible.',
            'Input values are classical, but their number implies a 22-bit minimum for direct reversible encoding.',
            'Three qubits hold eight orthogonal basis states; eight independent qubits hold 256.',
            'No reachable-subspace dimension, quantum entropy, or exact rewrite proved.',
            'No score improvement established.'
        ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K115_REGISTERS',json.dumps(analysis['registers']),flush=True)
    print('K115_COUNTS',json.dumps({
        'total_qubits':len(analysis['wire_roles']),
        'input_wire_count':len(inputs),
        'noninput_wire_count':len(others),
        'events':analysis['event_counts'],
        'max_condition_depth':analysis['block_max_nesting'],
        'condition_errors':analysis['condition_balance_errors']
    }),flush=True)
    print('K115_HOT_WIRES',json.dumps([{
        k:w[k] for k in ('wire','touches','high_cost_occurrences','R','HMR','CCX','CCZ','CSWAP')}
        for w in ranked[:a.show]]),flush=True)
    for op in ('R','HMR','BIT_STORE0','BIT_STORE1','PUSH_CONDITION'):
        sample=next((e for e in analysis['events'] if e['op']==op),None)
        if sample:print('K115_EVENT',json.dumps(sample),flush=True)
    print('K115_RESULT',json.dumps({'status':'READ_ONLY','out':str(a.out)}),flush=True)

if __name__=='__main__':
    main()
