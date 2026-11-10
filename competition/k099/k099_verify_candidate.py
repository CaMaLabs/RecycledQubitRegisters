#!/usr/bin/env python3
"""K099 staged verification of an exact-cancellation candidate.

Runs the same k031 verifier and two full-domain seeds used by K098.
No winner is claimed without two full-domain passes and a lower score.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

BASE_KMX_SHA = 'e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
BASE_SCORE = 95369.00696815242
ROOT = Path(__file__).resolve().parents[2]

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def load(path: Path):
    spec = importlib.util.spec_from_file_location('k031_k099', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot import {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def passed(record):
    return record.get('status') == 'PASS' and record.get('exit_code') == 0

def compact(r):
    return {k:r.get(k) for k in (
        'status','score','toffoli_count','rotation_count','rotation_eps',
        'worst_x','worst_error_over_tolerance','num_qubits','t_count',
        'exit_code','error','reason','stderr_tail','stdout_tail')}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    ap.add_argument('--candidate',type=Path,default=ROOT/'competition/k099/results/helios_exact_cancel.kmx')
    ap.add_argument('--audit',type=Path,default=ROOT/'competition/k099/results/helios_exact_cancel.audit.json')
    ap.add_argument('--output',type=Path,default=ROOT/'competition/k099/results/verification.json')
    ap.add_argument('--screen',type=int,default=256)
    ap.add_argument('--prefix',type=int,default=4095)
    ap.add_argument('--timeout',type=int,default=1200)
    ap.add_argument('--full',action='store_true',help='Run both full-domain seed checks after passing the prefix')
    args = ap.parse_args()
    if not 161 <= args.screen <= args.prefix:
        ap.error('Require 161 <= screen <= prefix')
    if not args.candidate.is_file() or not args.baseline.is_file():
        ap.error('Baseline or candidate not found; run K099 optimizer first')
    bsha, csha = digest(args.baseline),digest(args.candidate)
    if bsha != BASE_KMX_SHA:
        raise SystemExit(f'Baseline digest mismatch: {bsha}; expected {BASE_KMX_SHA}')
    audit = json.loads(args.audit.read_text())
    if audit.get('baseline_sha256') != bsha or audit.get('candidate_sha256') != csha:
        raise SystemExit('Audit digest mismatch; candidate has changed or is not from this baseline')
    if not audit.get('cancellation_pairs'):
        raise SystemExit('Audit has no cancellation pairs')
    verifier_path=ROOT/'competition/k031/k031_full_domain_repair.py'
    if not verifier_path.is_file():
        raise SystemExit(f'Cannot locate {verifier_path}')
    ver=load(verifier_path)
    report={'baseline_sha256':bsha,'candidate_sha256':csha,
            'baseline_score_reference':BASE_SCORE,
            'cancellation_pairs':audit['cancellation_pairs'],
            'removed_gates':audit['removed_gates'],
            'full_requested':args.full,'started_at_unix':time.time(),'stages':{}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    stages=[('screen',args.screen,12345)]
    if args.prefix > args.screen:
        stages.append(('prefix',args.prefix,12345))
    if args.full:
        stages.extend([('full_12345',ver.FULL_X,12345),
                       ('full_23456',ver.FULL_X,23456)])
    for label,n,seed in stages:
        r=compact(ver.verify(str(args.candidate),n,seed,args.timeout))
        report['stages'][label]=r
        print('K099_VERIFY_STAGE',json.dumps({'stage':label,'x':n,'seed':seed,**r},default=str),flush=True)
        if not passed(r):
            break
    full_ok=args.full and all(passed(report['stages'].get(k,{}))
        for k in ('full_12345','full_23456'))
    values=[report['stages'][k]['score'] for k in ('full_12345','full_23456')
            if passed(report['stages'].get(k,{}))]
    report['full_passes']=sum(passed(report['stages'].get(k,{}))
        for k in ('full_12345','full_23456'))
    report['beats_baseline']=bool(full_ok and len(values)==2 and
        all(isinstance(x,(int,float)) and x<BASE_SCORE for x in values))
    report['status']='FULL_PASS' if full_ok else 'NOT_FULLY_VERIFIED'
    report['finished_at_unix']=time.time()
    args.output.write_text(json.dumps(report,indent=2,default=str)+'\n')
    print('K099_VERIFY_RESULT',json.dumps({
        'status':report['status'],'full_passes':report['full_passes'],
        'scores':values,'baseline_score':BASE_SCORE,
        'beats_baseline':report['beats_baseline'],
        'output':str(args.output)}),flush=True)

if __name__ == '__main__':
    main()
