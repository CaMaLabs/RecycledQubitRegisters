#!/usr/bin/env python3
"""K099: conservative exact, commutation-aware self-inverse gate cancellation.

Unknown instructions, conditions and declarations are hard barriers.
The baseline is SHA-256 pinned and never overwritten.
Outputs an unverified candidate, not a leaderboard win.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

GATE_ARITY = {'X':1,'Y':1,'Z':1,'CX':2,'CZ':2,'CCX':3,'CCZ':3,'SWAP':2,'CSWAP':3,'Z_POW':1,'S':1,'S_DAG':1,'T':1,'T_DAG':1}
SELF_INVERSE = {'X','Y','Z','CX','CZ','CCX','CCZ','SWAP','CSWAP'}
DIAGONAL = {'Z','CZ','CCZ','Z_POW','S','S_DAG','T','T_DAG'}
BIT_FLIP = {'X','CX','CCX'}
PATTERN = re.compile(r'^([A-Z_]+)\s+((?:q\d+\s*)+)(?:\s+([^\s]+))?$', re.ASCII)

def parse(line):
    s = line.strip()
    if not s or s.startswith(('#','//')) or ' if ' in s.lower():
        return None
    m = PATTERN.fullmatch(s)
    if not m or m.group(1) not in GATE_ARITY:
        return None
    op = m.group(1)
    q = tuple(int(n) for n in re.findall(r'q(\d+)', m.group(2)))
    if len(q) != GATE_ARITY[op] or len(set(q)) != len(q):
        return None
    angle = m.group(3)
    if (op == 'Z_POW') != (angle is not None):
        return None
    return (op,q,angle)

def commute(a,b):
    if a is None or b is None:
        return False
    oa,qa,_ = a
    ob,qb,_ = b
    if set(qa).isdisjoint(qb):
        return True
    if oa in DIAGONAL and ob in DIAGONAL:
        return True
    if oa in BIT_FLIP and ob in BIT_FLIP:
        return qa[-1] not in qb[:-1] and qb[-1] not in qa[:-1]
    return False

def cancel(lines, window):
    if window < 1:
        raise ValueError('window must be positive')
    live = [(i,line,parse(line)) for i,line in enumerate(lines)]
    events = []
    passes = 0
    while True:
        removed = False
        for j in range(len(live)):
            orig_j,_,gj = live[j]
            if gj is None or gj[0] not in SELF_INVERSE:
                continue
            for i in range(j-1,max(-1,j-window-1),-1):
                orig_i,_,gi = live[i]
                if gi == gj:
                    events.append({'gate':gj[0], 'source_lines':[orig_i+1,orig_j+1], 'qubits':list(gj[1]), 'intervening':j-i-1})
                    del live[j]
                    del live[i]
                    removed = True
                    break
                if not commute(gi,gj):
                    break
            if removed:
                break
        if not removed:
            break
        passes += 1
    return [entry[1] for entry in live],events,passes

def selftest():
    tests = [
        (['CX q0 q1\n','CX q0 q2\n','CX q0 q1\n'],1),
        (['CCX q0 q1 q2\n','CX q0 q3\n','CCX q0 q1 q2\n'],1),
        (['CX q0 q1\n','CX q1 q2\n','CX q0 q1\n'],0),
        (['CCX q0 q1 q2\n','CCX q2 q3 q4\n','CCX q0 q1 q2\n'],0),
        (['CZ q0 q1\n','Z_POW q0 0.25\n','CZ q0 q1\n'],1),
        (['CX q0 q1\n','HMR q2 b0\n','CX q0 q1\n'],0),
        (['X q0\n','X q0 if b1\n','X q0\n'],0),
        (['CX q0 q1\n','CX q0 q1\n'],1),
    ]
    for inp,expected in tests:
        _,events,_ = cancel(inp,30)
        assert len(events) == expected,(inp,events)
    print('K099_SELFTEST PASS 8 exact-commutation cases',flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline',default='competition/k098/results/helios_immutable.kmx')
    ap.add_argument('--out',default='competition/k099/results/helios_exact_cancel.kmx')
    ap.add_argument('--window',type=int,default=256)
    ap.add_argument('--pin',default='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a')
    args = ap.parse_args()
    selftest()
    src = Path(args.baseline)
    raw = src.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != args.pin:
        raise SystemExit(f'Baseline SHA mismatch: {digest}; expected {args.pin}; refusing to edit')
    lines = raw.decode('utf-8').splitlines(keepends=True)
    print('K099_BASE',json.dumps({'sha256':digest,'lines':len(lines),'bytes':len(raw)}),flush=True)
    new,events,passes = cancel(lines,args.window)
    output = Path(args.out)
    output.parent.mkdir(parents=True,exist_ok=True)
    if not events:
        print('K099_RESULT ZERO_CANCELLATIONS; no candidate emitted',flush=True)
        return
    output.write_text(''.join(new),encoding='utf-8',newline='')
    counts = dict(Counter(e['gate'] for e in events))
    report = {'status':'UNVERIFIED_CANDIDATE','baseline_sha256':digest,
        'candidate_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
        'candidate':str(output),'removed_gates':2*len(events),
        'cancellation_pairs':len(events),'by_gate':counts,
        'passes':passes,'events':events}
    output.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('K099_RESULT',json.dumps({k:v for k,v in report.items() if k!='events'}),flush=True)
    print('K099_EXAMPLES',json.dumps(events[:12]),flush=True)
    print('K099_NOTE candidate requires official full-domain verification; no score claimed',flush=True)

if __name__ == '__main__':
    main()
