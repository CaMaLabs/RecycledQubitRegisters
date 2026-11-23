#!/usr/bin/env python3
"""Normalize available Git branches, source docs and optional historical ZIP.

Missing K IDs remain UNKNOWN. Archived PASS receipts remain historical evidence,
never new engine leaderboard entries. Never publish official/private assets.
"""
import argparse
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from competition.optimizer.autonomous.store import Store
from competition.optimizer.autonomous.model import calibrate


def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.DEVNULL)

def run(out, archive=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    sources=defaultdict(list); objects={}; receipts=[]; summaries=[]
    branches=git('for-each-ref','--format=%(refname)','refs/remotes/origin').decode().splitlines()
    for branch in branches:
        for entry in git('ls-tree','-r',branch).decode().splitlines():
            meta,path=entry.split('\t',1)
            match=re.match(r'competition/k(\d{3})/',path)
            if not match: continue
            number=int(match[1]); blob=meta.split()[2]
            if (path,blob) in objects: continue
            content=git('cat-file','blob',blob)
            objects[path,blob]=True
            item={'path':path,'ref':branch,'blob':blob,'sha256':hashlib.sha256(content).hexdigest()}
            if path.endswith('.py'):
                try: item['description']=ast.get_docstring(ast.parse(content))
                except (SyntaxError,UnicodeDecodeError): item['description']=None
            sources[number].append(item)
            if path.endswith('experiment_registry.json'):
                summaries.append(json.loads(content))
    if archive:
        with zipfile.ZipFile(archive) as z:
            archive_sha=hashlib.sha256(Path(archive).read_bytes()).hexdigest()
            for path in z.namelist():
                match=re.match(r'competition/k(\d{3})/',path)
                if not match: continue
                number=int(match[1]); content=z.read(path)
                item={'path':path,'archive_sha256':archive_sha,'sha256':hashlib.sha256(content).hexdigest()}
                if path.endswith('.py'):
                    try: item['description']=ast.get_docstring(ast.parse(content))
                    except (SyntaxError,UnicodeDecodeError): pass
                sources[number].append(item)
                if path.endswith('.json'):
                    try: data=json.loads(content)
                    except (ValueError,UnicodeDecodeError): continue
                    # Preserve bounded result/config fields with graded provenance.
                    def collect(value, trail=''):
                        if isinstance(value,dict):
                            if value.get('status')=='PASS' and isinstance(value.get('score'),(int,float)):
                                keep={k:value[k] for k in ('status','score','toffoli_count','rotation_count',
                                    'rotation_eps','reaction_depth','num_qubits','toffoli_equivalent',
                                    'verified_shots','worst_error_over_tolerance','circuit_sha256','exit_code') if k in value}
                                receipts.append({'id':f'K{number:03d}','source':item,'json_path':trail,
                                                 'metrics':keep,'evidence':'ARCHIVED_RECEIPT_NOT_REEXECUTED'})
                            for k,v in value.items(): collect(v,trail+'/'+k)
                        elif isinstance(value,list):
                            for i,v in enumerate(value): collect(v,trail+'/'+str(i))
                    collect(data)
    # Fetch the reconciled ledger explicitly; it is outside per-K directories.
    for branch in branches:
        try: content=git('show',branch+':competition/experiment_registry.json')
        except subprocess.CalledProcessError: continue
        summaries.append({'ref':branch,'data':json.loads(content)})
    records=[]
    for number in range(1,244):
        found=sources[number]
        records.append({'id':f'K{number:03d}','method':sorted({Path(x['path']).stem for x in found if x['path'].endswith('.py')}),
            'configuration':None,'candidate':None,'equivalence_status':'UNKNOWN_UNTIL_RESULT_INSPECTION',
            'verifier_result':'UNKNOWN','score':None,
            'coverage':'ARTIFACTS_AVAILABLE' if found else 'UNKNOWN_MISSING_FROM_ACCESSIBLE_SOURCES',
            'reason':'No per-ID failure/optimality conclusion inferred from filenames',
            'sources':found})
    data={'scope':'K001-K243','records':records,'archived_receipts':receipts,
          'reconciled_ledger':summaries,'coverage_limit':'No local Ubuntu checkout; K191 and K195-K243 unavailable.',
          'source_refs':{b:git('rev-parse',b).decode().strip() for b in branches}}
    (out/'history.json').write_text(json.dumps(data,indent=2)+'\n')
    store=Store(out/'history.sqlite3')
    for record in records:
        store.db.execute('INSERT OR REPLACE INTO history VALUES (?,?,?,?,?,?,?,?,?,?)',
            (record['id'],json.dumps(record['method']),None,None,record['equivalence_status'],
             record['verifier_result'],None,record['reason'],json.dumps(record['sources']),json.dumps(record)))
    for receipt in receipts:
        m=receipt['metrics']; key=hashlib.sha256(json.dumps(receipt,sort_keys=True).encode()).hexdigest()
        store.db.execute('INSERT OR REPLACE INTO history VALUES (?,?,?,?,?,?,?,?,?,?)',
            (key,receipt['id'],receipt['json_path'],m.get('circuit_sha256'),'NOT_REPROVED',
             'ARCHIVED_PASS',m['score'],'Archived receipt; scope is verified_shots, never inferred full correctness',
             json.dumps(receipt['source']),json.dumps(m)))
    for summary in summaries:
        for entry in summary.get('data',{}).get('experiments',[]):
            key='ledger:'+entry['id']
            store.db.execute('INSERT OR REPLACE INTO history VALUES (?,?,?,?,?,?,?,?,?,?)',
                (key,entry.get('technique'),None,None,'SEE_ARCHIVED_EVIDENCE',entry.get('verification_status'),
                 None,entry.get('actual_result'),summary.get('ref',''),json.dumps(entry)))
    store.db.commit();store.close()
    valid=[r['metrics'] for r in receipts if all(k in r['metrics'] for k in ('num_qubits','toffoli_equivalent','score'))]
    (out/'cost_calibration.json').write_text(json.dumps(calibrate(valid),indent=2)+'\n')
    result={'ids_with_artifacts':sum(bool(sources[i]) for i in range(1,244)),
            'ids_unknown':sum(not sources[i] for i in range(1,244)),
            'archived_pass_receipts':len(receipts),'historical_only':True}
    (out/'coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--archive')
    a=p.parse_args();run(a.out,a.archive)
