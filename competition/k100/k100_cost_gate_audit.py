#!/usr/bin/env python3
"""K100: score-driving gate census and structurally safe rewrite triage.

Read-only. Identifies CCX/CCZ/CSWAP hotspots, repeated patterns, and
live reversible gate boundaries. Does not claim an optimization.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
COST={'CCX','CCZ','CSWAP','Z_POW','T','T_DAG'}
Q=re.compile(r'\bq(\d+)\b')
OP=re.compile(r'^([A-Z][A-Z0-9_]*)\b')
CLASSICAL={'PUSH_CONDITION','POP_CONDITION','HMR','REGISTER','APPEND_TO_REGISTER','MEASURE','RESET'}

def scan(path):
    raw=path.read_bytes()
    lines=raw.decode('utf-8').splitlines()
    rows=[]
    for i,line in enumerate(lines,1):
        s=line.strip()
        m=OP.match(s)
        if not m:continue
        op=m.group(1)
        qs=tuple(map(int,Q.findall(s)))
        rows.append((i,op,qs,s))
    return hashlib.sha256(raw).hexdigest(),lines,rows

def blocks(rows):
    """Group nearby expensive operations, splitting at >64 intervening lines."""
    costly=[r for r in rows if r[1] in COST]
    groups=[]
    for r in costly:
        if not groups or r[0]-groups[-1][-1][0]>64:groups.append([])
        groups[-1].append(r)
    return sorted(groups,key=lambda g:sum(r[1] in {'CCX','CCZ','CSWAP'} for r in g),reverse=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    ap.add_argument('--candidate',type=Path,default=ROOT/'competition/k099/results/helios_exact_cancel.kmx')
    ap.add_argument('--out',type=Path,default=ROOT/'competition/k100/results/structural_audit.json')
    args=ap.parse_args()
    bh,bl,br=scan(args.baseline)
    if bh!=PIN:raise SystemExit(f'Unexpected baseline hash {bh}; refusing comparison')
    ch,cl,cr=scan(args.candidate)
    bc=collections.Counter(r[1] for r in br)
    cc=collections.Counter(r[1] for r in cr)
    ops=sorted(set(bc)|set(cc))
    differences={op:{'baseline':bc[op],'candidate':cc[op],'delta':cc[op]-bc[op]}
                 for op in ops if bc[op]!=cc[op]}
    gates=collections.Counter(r[1] for r in cr if r[1] in COST)
    qubits=collections.Counter(q for _,op,qs,_ in cr if op in {'CCX','CCZ','CSWAP'} for q in qs)
    targets=collections.Counter((op,qs[-1]) for _,op,qs,_ in cr
                                 if op in {'CCX','CSWAP'} and qs)
    triples=collections.Counter((op,qs) for _,op,qs,_ in cr if op in {'CCX','CCZ','CSWAP'})
    hotspot=[]
    for group in blocks(cr)[:20]:
        count=collections.Counter(r[1] for r in group)
        hotspot.append({'start_line':group[0][0],'end_line':group[-1][0],
                        'gates':dict(count),'cost_gates':sum(count[k] for k in ('CCX','CCZ','CSWAP'))})
    # Read-only windows of expensive gates; require proper symbolic proof before rewrites.
    repeated=[{'op':op,'qubits':list(qs),'occurrences':n} for (op,qs),n in triples.most_common(30) if n>1]
    report={'status':'AUDIT_ONLY','baseline_sha256':bh,'candidate_sha256':ch,
            'baseline_lines':len(bl),'candidate_lines':len(cl),
            'operation_changes':differences,'candidate_expensive_gates':dict(gates),
            'top_expensive_qubits':[{'qubit':q,'references':n} for q,n in qubits.most_common(20)],
            'top_ccx_cswap_targets':[{'op':op,'qubit':q,'count':n} for (op,q),n in targets.most_common(20)],
            'hotspots':hotspot,'repeated_cost_gates':repeated,
            'note':'Source gate census is not executed-gate score; optimizations need proof and full verification.'}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K100_CENSUS',json.dumps({'operation_changes':differences,
        'candidate_expensive_gates':dict(gates),'hotspots':hotspot[:5]}),flush=True)
    print('K100_RESULT',json.dumps({'status':'AUDIT_ONLY','report':str(args.out),
        'repeated_cost_gate_patterns':len(repeated),
        'cost_gate_changes':{k:v for k,v in differences.items() if k in COST}}),flush=True)

if __name__=='__main__':
    main()
