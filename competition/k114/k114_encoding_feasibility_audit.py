#!/usr/bin/env python3
"""K114: state-space compression feasibility reconnaissance for Helios.

This is a READ-ONLY audit, not a proof of compressibility. For an arbitrary
eight-qubit input, an invertible circuit preserves a 256-dimensional space;
compression to 3 qubits requires an evidenced <=8-dimensional reachable
subspace and a reversible encoding/decoding plan.

Catalog nonunitary boundaries, input preparation, classical controls,
wire usage and 8-wire groups. Do not infer reachability from sampling or
from static periods of apparent inactivity.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
Q=re.compile(r'\bq(\d+)\b')
OP=re.compile(r'^\s*([A-Za-z][A-Za-z0-9_]*)\b')
REV={'X','CX','CCX','CCZ','CSWAP','SWAP'}
CLASSICAL_HINT=('MEAS','RESET','DISCARD','INIT','ALLOC','DEALLOC','FREE','IF','ELSE','COND','BIT','INPUT','OUTPUT','ASSERT','REPEAT','WHILE')
def analyze(lines):
    op_counts=collections.Counter()
    touch=collections.defaultdict(list)
    control=collections.Counter()
    suspects=[]
    for i,line in enumerate(lines,1):
        s=line.strip()
        m=OP.match(line)
        op=m.group(1).upper() if m else 'BLANK_OR_PUNCT'
        op_counts[op]+=1
        wires=[int(x) for x in Q.findall(s)]
        for q in set(wires):touch[q].append(i)
        if op in ('CX','CCX','CSWAP') and wires:
            for q in wires[:-1]:control[q]+=1
        if any(k in op for k in CLASSICAL_HINT) or op not in REV:
            suspects.append({'line':i,'op':op,'text':s[:200],'wires':wires})
    return op_counts,touch,control,suspects

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k114/results/encoding_feasibility.json')
    p.add_argument('--show',type=int,default=45)
    a=p.parse_args()
    raw=a.baseline.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('Immutable baseline hash mismatch')
    lines=raw.decode('utf8').splitlines()
    counts,touch,controls,suspects=analyze(lines)
    wire_rows=[]
    for q,locations in touch.items():
        wire_rows.append({'wire':q,'first':locations[0],'last':locations[-1],
            'touches':len(locations),'control_uses':controls[q]})
    wire_rows.sort(key=lambda x:x['wire'])
    untouched=[q for q in range(max(touch)+1) if q not in touch] if touch else []
    nonunitary=[r for r in suspects if any(w in r['op'] for w in
        ('MEAS','RESET','DISCARD','INIT','DEALLOC','FREE','ALLOC'))]
    near_start=[r for r in suspects if r['line']<=300]
    output={'status':'INSPECTION_ONLY','baseline_sha256':sha,'lines':len(lines),
        'operation_counts':dict(counts),'referenced_wire_count':len(touch),
        'max_referenced_wire':max(touch) if touch else None,
        'untouched_wire_indices':untouched,
        'wire_usage':wire_rows,
        'nonreversible_or_unrecognized_lines':len(suspects),
        'candidate_preparation_or_disposal_ops':nonunitary[:150],
        'first_300_nonreversible_lines':near_start[:100],
        'first_80_source_lines':[{'line':i,'text':s} for i,s in enumerate(lines[:80],1)],
        'warning':[
            'This scan does NOT establish low-dimensional reachable states.',
            '8 independent qubits require 256 basis dimensions, not 8.',
            'A proposed compression needs a specified input subspace, invariant proof, reversible decoder, and verifier tests.',
            'Conditional gates and phase operations may be hidden behind syntax not recognized here.',
            'No candidate circuit generated or competition score measured.'
        ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(output,indent=2)+'\n')
    print('K114_COUNTS',json.dumps({'referenced_wires':len(touch),
        'highest_wire':output['max_referenced_wire'],
        'unused_wire_indices':untouched,
        'nonreversible_or_unknown_lines':len(suspects),
        'candidate_preparation_or_disposal_ops':len(nonunitary)}),flush=True)
    print('K114_OPERATIONS',json.dumps(counts.most_common(24)),flush=True)
    print('K114_FIRST_LINES',json.dumps(output['first_80_source_lines'][:a.show]),flush=True)
    print('K114_BOUNDARIES',json.dumps(nonunitary[:a.show]),flush=True)
    print('K114_RESULT',json.dumps({'status':'INSPECTION_ONLY','out':str(a.out)}),flush=True)
if __name__=='__main__':main()
