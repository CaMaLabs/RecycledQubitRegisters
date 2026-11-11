#!/usr/bin/env python3
"""K102: read-only arithmetic-region discovery for Helios Kickmix.

Search pinned baseline for reversible runs containing Toffoli-class gates.
Extract *structural* candidate windows for controlled arithmetic rewrites.
Never mutate baseline; no unproved rewrites or leaderboard claims.

K099 proved source CX cancellation does not lower the leaderboard score:
this audit prioritizes CCX/CCZ/CSWAP and Z_POW instead.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
Q=re.compile(r'\bq(\d+)\b')
OP=re.compile(r'^([A-Z][A-Z0-9_]*)\b')
REV={'X','CX','CCX','CCZ','CSWAP','SWAP'}
COST={'CCX','CCZ','CSWAP','Z_POW','T','T_DAG'}
CARRY={'CX','CCX','X'}

def parse(raw):
    records=[]
    for lineno,line in enumerate(raw.decode().splitlines(),1):
        s=line.strip()
        m=OP.match(s)
        op=m.group(1) if m else ''
        qs=tuple(int(x) for x in Q.findall(s))
        records.append((lineno,op,qs,s))
    return records

def regions(records):
    regions=[]
    current=[]
    for item in records:
        if item[1] in REV:
            current.append(item)
        else:
            if current:regions.append(current);current=[]
    if current:regions.append(current)
    return regions

def score(region):
    counts=collections.Counter(r[1] for r in region)
    return 100*(counts['CCX']+counts['CCZ']+counts['CSWAP'])+counts['CX']

def analyze(reg):
    cnt=collections.Counter(r[1] for r in reg)
    active=sorted(set(q for _,_,qs,_ in reg for q in qs))
    triple=collections.Counter((op,qs) for _,op,qs,_ in reg if op in {'CCX','CCZ','CSWAP'})
    targets=collections.Counter(qs[-1] for _,op,qs,_ in reg if op=='CCX' and qs)
    # A ladder is a run with at least two CCX and shared target,
    # or a repeated CCX control pair on different targets.
    ctrls=collections.defaultdict(set)
    for _,op,qs,_ in reg:
        if op=='CCX' and len(qs)==3:ctrls[tuple(sorted(qs[:2]))].add(qs[2])
    shared_ctrls=[{'controls':list(k),'targets':sorted(v)} for k,v in ctrls.items() if len(v)>1]
    return {'start_line':reg[0][0],'end_line':reg[-1][0],
       'length':len(reg),'weighted_priority':score(reg),
       'counts':dict(cnt),'qubits':active,'width':len(active),
       'target_hotspots':[{'qubit':t,'count':n} for t,n in targets.most_common(8)],
       'shared_control_fanouts':shared_ctrls[:12],
       'repeated_toffoli_triplets':sum(n>1 for n in triple.values()),
       'preview':[r[3] for r in reg[:12]],
       'note':'Structural candidate only; may not be arithmetic or reducible.'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--max-regions',type=int,default=25)
    p.add_argument('--out',type=Path,default=ROOT/'competition/k102/results/helios_arithmetic_regions.json')
    a=p.parse_args()
    raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit(f'Baseline hash mismatch: {sha}')
    records=parse(raw)
    runs=regions(records)
    selected=[analyze(r) for r in runs if sum(x[1] in {'CCX','CCZ','CSWAP'} for x in r)>=2]
    selected.sort(key=lambda x:(x['weighted_priority'],x['length']),reverse=True)
    gate_counts=collections.Counter(r[1] for r in records if r[1])
    report={'status':'AUDIT_ONLY','source_sha256':sha,
      'baseline_lines':len(records),'reversible_regions_total':len(runs),
      'reversible_regions_with_2plus_cost_gates':len(selected),
      'counts_of_interest':{x:gate_counts[x] for x in sorted(COST|REV)},
      'top_regions':selected[:max(0,a.max_regions)],
      'method':'Contiguous X/CX/CCX/CCZ/CSWAP/SWAP runs; split on every other line, including Z_POW, comments, control flow and classical instructions.',
      'limitations':[
        'No behavior or algebraic equivalence established for these candidate regions.',
        'Source gate counts are not dynamic executed Toffoli costs.',
        'Broad arithmetic networks interrupted by phase instructions or classical controls are split.',
        'This is read-only. No candidate binary or Kaggle score improvement produced.'
      ]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K102_COUNTS',json.dumps({'total_regions':len(runs),'expensive_regions':len(selected),
       'gates':report['counts_of_interest']}),flush=True)
    for r in report['top_regions'][:10]:
        print('K102_REGION',json.dumps({k:r[k] for k in ('start_line','end_line','length','width',
           'weighted_priority','counts','shared_control_fanouts','target_hotspots')}),flush=True)
    print('K102_RESULT',json.dumps({'status':'AUDIT_ONLY','out':str(a.out),'top_regions':len(report['top_regions'])}),flush=True)

if __name__=='__main__':main()
