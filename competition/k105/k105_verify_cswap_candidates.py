#!/usr/bin/env python3
"""K105: cost-aware staged Kickmix verifier for K104 CSWAP alternatives.

Authenticates baseline and candidate audits, converts each KMx to KMb,
runs official k031 verification on screening domain, then optionally
prefix/full domain. Never treats a partial pass as a leaderboard win.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
SCORE=95369.00696815242

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def load(path):
    spec=importlib.util.spec_from_file_location('k031_k105',path)
    if spec is None or spec.loader is None:raise RuntimeError(f'Unable to load {path}')
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def succeeded(r):
    return r.get('status')=='PASS' and r.get('exit_code')==0

def brief(r):
    return {k:r.get(k) for k in (
        'status','exit_code','score','toffoli_count','rotation_count',
        'rotation_eps','worst_x','worst_error_over_tolerance',
        'error','reason','stderr_tail') if k in r}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--screen',type=int,default=256)
    p.add_argument('--prefix',type=int,default=4095)
    p.add_argument('--timeout',type=int,default=1200)
    p.add_argument('--full',action='store_true',
        help='Only full-check a candidate after a prefix PASS and observed score improvement')
    p.add_argument('--include-all',action='store_true',help='Include all-scope candidate files if present')
    p.add_argument('--output',type=Path,default=ROOT/'competition/k105/results/k104_screen.json')
    a=p.parse_args()
    if not 161<=a.screen<=a.prefix:p.error('Require 161 <= screen <= prefix')
    baseline=ROOT/'competition/k098/results/helios_immutable.kmx'
    if sha(baseline)!=PIN:raise SystemExit('Pinned baseline mismatch')
    sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
    try:import kickmix as km
    except ImportError as exc:raise SystemExit(f'Kickmix unavailable: {exc}')
    verifier=load(ROOT/'competition/k031/k031_full_domain_repair.py')
    root=ROOT/'competition/k104/results'
    scopes=('hotspot','all') if a.include_all else ('hotspot',)
    names=[(scope,style,root/f'helios_cswap_{scope}_{style}.kmx')
           for scope in scopes for style in ('a_to_b','b_to_a')]
    report={'baseline_sha256':PIN,'reference_score':SCORE,'full_requested':a.full,'candidates':[]}
    for scope,style,path in names:
        if not path.exists():continue
        audit_path=path.with_suffix('.audit.json')
        if not audit_path.exists():
            print('K105_SKIP',json.dumps({'candidate':str(path),'reason':'missing audit'}),flush=True)
            continue
        audit=json.loads(audit_path.read_text())
        candidate_hash=sha(path)
        if audit.get('baseline_sha256')!=PIN or audit.get('candidate_sha256')!=candidate_hash:
            raise SystemExit(f'Candidate audit mismatch: {path}')
        circuit=km.Circuit.from_file(str(path),format='kmx')
        binary=path.with_suffix('.kmb')
        circuit.to_file(str(binary),format='kmb')
        row={'scope':scope,'style':style,'candidate':str(path),
            'candidate_sha256':candidate_hash,'binary_sha256':sha(binary),
            'replaced_cswaps':audit.get('replaced_cswaps'),'stages':{}}
        print('K105_COMPILED',json.dumps({k:row[k] for k in (
            'scope','style','binary_sha256','replaced_cswaps')}),flush=True)
        stages=[('screen',a.screen,12345)]
        if a.prefix>a.screen:stages.append(('prefix',a.prefix,12345))
        for label,n,seed in stages:
            v=brief(verifier.verify(str(binary),n,seed,a.timeout))
            row['stages'][label]=v
            print('K105_STAGE',json.dumps({'scope':scope,'style':style,'stage':label,
                'x':n,'seed':seed,**v},default=str),flush=True)
            if not succeeded(v):break
            if label=='screen' and v.get('score') is not None and v['score']>=SCORE:
                row['reason']='screen_pass_but_score_not_improved'
                print('K105_EARLY_STOP',json.dumps({'scope':scope,'style':style,
                    'screen_score':v['score'],'baseline_score':SCORE}),flush=True)
                break
        screen=row['stages'].get('screen',{})
        prefix=row['stages'].get('prefix',{})
        if a.full and succeeded(prefix) and isinstance(prefix.get('score'),(int,float)) and prefix['score']<SCORE:
            for label,seed in [('full_12345',12345),('full_23456',23456)]:
                v=brief(verifier.verify(str(binary),verifier.FULL_X,seed,a.timeout))
                row['stages'][label]=v
                print('K105_STAGE',json.dumps({'scope':scope,'style':style,'stage':label,
                    'x':verifier.FULL_X,'seed':seed,**v},default=str),flush=True)
                if not succeeded(v):break
        fulls=[row['stages'].get(s,{}) for s in ('full_12345','full_23456')]
        row['beats_baseline']=all(succeeded(v) and isinstance(v.get('score'),(int,float)) and v['score']<SCORE for v in fulls)
        report['candidates'].append(row)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,default=str)+'\n')
    print('K105_RESULT',json.dumps({'status':'COMPLETE','candidates':len(report['candidates']),
        'verified_winners':sum(v['beats_baseline'] for v in report['candidates']),
        'output':str(a.output)}),flush=True)

if __name__=='__main__':main()
