#!/usr/bin/env python3
"""K116: classical input bucketing feasibility for invsqrt.

An OFFLINE design experiment, not a submission. Exact real-valued
relative-error interval intersection gives the minimum number of
contiguous value buckets for y(x)=1/sqrt(x), x=1..N, under each specified
relative tolerance. This is a SURROGATE and does not model the official
invsqrt phase-turn tolerance or quantum input restoration requirement.

Also prints relevant official verifier source lines for follow-up
phase-aware analysis. No Kickmix circuit is modified.
"""
from __future__ import annotations
import argparse,ast,hashlib,json,math,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OFFICIAL=ROOT/'competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py'
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def optimal_intervals(n,relative_error):
    if n<1 or not 0<relative_error<1:raise ValueError('Invalid bounds')
    # 1/sqrt(x) and its relative-error interval endpoints are strictly
    # decreasing in x. Scanning x=N..1 gives increasing intervals.
    # The greedy interval-stabbing algorithm chooses the smallest
    # available right endpoint for each group; this minimizes groups.
    count=0
    representative=None
    groups=[]
    first=n
    for x in range(n,0,-1):
        f=1/math.sqrt(x)
        lo=f*(1-relative_error)
        hi=f*(1+relative_error)
        if representative is None or lo>representative:
            if representative is not None:
                groups.append((x+1,first))
            count+=1
            representative=hi
            first=x
    groups.append((1,first))
    assert groups[0][0]==1 and groups[-1][1]==n
    assert all(groups[i][1]+1==groups[i+1][0] for i in range(len(groups)-1))
    return count,max(b-a+1 for a,b in groups),groups[:8],groups[-8:]

def source_inspection(path,limit=90):
    if not path.is_file():return {'available':False,'error':'Local official verifier file not found'}
    lines=path.read_text().splitlines()
    key=re.compile(r'(def\s+|\b(?:MAX_X|FULL_X|NUM_SHOTS|TOL|PHASE|SCALE|BITS|PRECISION|ERROR|TURN|MARGIN|invsqrt|inv_sqrt|sqrt)\b)',re.I)
    selected=[]
    for i,line in enumerate(lines,1):
        if key.search(line):
            # Short snippets only; user can paste the relevant definitions.
            if len(selected)>=limit:break
            selected.append({'line':i,'text':line[:180]})
    return {'available':True,'lines':len(lines),'candidates':selected}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--n',type=int,default=3133452)
    ap.add_argument('--tolerances',default='24,22,20,18,16,12')
    ap.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    ap.add_argument('--out',type=Path,default=ROOT/'competition/k116/results/input_bucketing_feasibility.json')
    args=ap.parse_args()
    if not args.baseline.is_file():raise SystemExit('Baseline not found')
    sha=hashlib.sha256(args.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit('Pinned baseline hash mismatch')
    reports=[]
    for bits in [int(s) for s in args.tolerances.split(',')]:
        if bits<1 or bits>52:ap.error('Accuracy bits must be 1..52')
        n,largest,first,last=optimal_intervals(args.n,2.0**(-bits))
        row={'relative_accuracy_bits':bits,'relative_epsilon':2.0**(-bits),
             'minimum_contiguous_buckets':n,
             'bits_for_bucket_index':(n-1).bit_length(),
             'largest_bucket':largest}
        reports.append(row)
        print('K116_BUCKETS',json.dumps(row),flush=True)
    source=source_inspection(OFFICIAL)
    print('K116_VERIFIER_SOURCE',json.dumps(source),flush=True)
    report={'status':'SURROGATE_ONLY','baseline_sha256':sha,'domain':[1,args.n],
        'model':'For every x, choose representative yhat with |yhat-1/sqrt(x)| <= epsilon/sqrt(x); contiguous buckets; greedy interval stabbing.',
        'results':reports,'verifier_inspection':source,
        'limitations':[
            'These are real-value relative-error buckets, NOT official phase-error buckets.',
            'Requires inspection of official phase modulo and tolerance calculations before conclusions about Kickmix validity.',
            'Classical input preprocessing is not an external runtime step in the submitted .kmx/.kmb circuit.',
            'Quantum input register must be preserved and correct phase applied for every allowed input.',
            'No candidate submitted and no score measured.']}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print('K116_RESULT',json.dumps({'status':report['status'],'out':str(args.out)}),flush=True)

if __name__=='__main__':main()
