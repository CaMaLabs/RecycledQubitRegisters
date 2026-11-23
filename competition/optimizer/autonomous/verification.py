"""Verifier isolation and strict full-domain receipts.

The official CLI is invoked through a user-supplied argv contract, never a shell.
The local asset SHA, exact command, seeds, and output are retained. Exit code
alone, PASS in prose, a prefix PASS, or non-finite score can never promote.
"""
import hashlib
import json
import math
import os
import resource
import signal
import subprocess
import sys
from pathlib import Path


def limits(memory_mb, cpus):
    def apply():
        resource.setrlimit(resource.RLIMIT_AS,(memory_mb*1024**2,)*2)
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,)*2)
        if hasattr(os,'sched_getaffinity'):
            allowed=sorted(os.sched_getaffinity(0))[:cpus]
            os.sched_setaffinity(0,set(allowed))
    return apply


def run_process(argv, log, timeout, memory_mb=2048, cpus=1):
    """File-backed output, process-group timeout, no indefinite descendants."""
    env=os.environ.copy()
    env.update({x:str(cpus) for x in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')})
    with Path(log).open('wb') as stream:
        proc=subprocess.Popen(argv,stdout=stream,stderr=subprocess.STDOUT,
            start_new_session=True,preexec_fn=limits(memory_mb,cpus),env=env)
        try:
            code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL); proc.wait()
            return {'exit_code':None,'status':'TIMEOUT','log':str(log)}
        # No task may leave background solver children running.
        try: os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError: pass
    return {'exit_code':code,'status':'EXITED','log':str(log)}


def parse_receipt(text, exit_code, contract):
    decoder=json.JSONDecoder()
    records=[]
    # Verifier versions emit either a JSON object or banner + multiline JSON.
    # Only complete dictionaries with status qualify; strings mentioning PASS do not.
    offset=0
    while offset<len(text):
        i=text.find('{',offset)
        if i<0: break
        try:
            value,end=decoder.raw_decode(text,i)
            offset=end  # Nested status objects cannot override their parent.
            if isinstance(value,dict) and 'status' in value: records.append(value)
        except ValueError:
            offset=i+1
        if len(records)>100:
            return {'status':'UNPARSEABLE','reason':'Too many verifier documents'}
    if not records:
        return {'status':'UNPARSEABLE','reason':'No structured verifier result'}
    record=records[-1]
    score=record.get('score')
    if exit_code!=0 or record.get('status')!='PASS':
        return {'status':'FAIL','metrics':record,'reason':'Nonzero exit or no explicit PASS'}
    if isinstance(score,bool) or not isinstance(score,(int,float)) or not math.isfinite(score):
        return {'status':'INVALID_SCORE','metrics':record}
    expected=contract['full_shots']
    if record.get('verified_shots')!=expected:
        return {'status':'PARTIAL_OR_UNKNOWN_DOMAIN','metrics':record,
                'reason':f'Expected verified_shots={expected}'}
    # Required official metrics, with version-configurable exact field mapping.
    fields=contract['fields']
    missing=[name for name,field in fields.items() if field not in record]
    if missing:
        return {'status':'INCOMPLETE_METRICS','metrics':record,'reason':str(missing)}
    for name,field in fields.items():
        value=record[field]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            return {'status':'INVALID_METRICS','metrics':record,'reason':name}
    return {'status':'PASS_FULL','score':score,'metrics':record,
            'normalized_metrics':{name:record[field] for name,field in fields.items()}}


def verify(candidate, out, contract, timeout, memory_mb, cpus, remaining, *, python=None):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    candidate=Path(candidate).resolve()
    raw=candidate.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    script=Path(contract['script']).resolve()
    if not script.is_file():
        return {'status':'UNAVAILABLE','reason':f'Official verifier absent: {script}'}
    actual=hashlib.sha256(script.read_bytes()).hexdigest()
    if actual!=contract['script_sha256']:
        return {'status':'VERIFIER_SHA_MISMATCH','actual':actual}
    receipts=[]
    import time
    start=time.monotonic()
    for seed in contract['seeds']:
        budget=min(timeout,remaining-(time.monotonic()-start))
        if budget<=0:
            return {'status':'BUDGET_EXHAUSTED','runs':receipts}
        substitutions={'python':python or sys.executable,'script':str(script),'candidate':str(candidate),
                       'seed':str(seed),'workers':str(cpus),'binary':str(out/'candidate.kmb')}
        # Optional conversion uses an inspected local official interface/argv.
        if contract.get('prepare_argv'):
            argv=[token.format(**substitutions) for token in contract['prepare_argv']]
            prep=run_process(argv,out/f'prepare-{seed}.log',budget,memory_mb,cpus)
            if prep.get('exit_code')!=0:
                return {'status':'PREPARE_FAILED','runs':receipts,'prepare':prep}
        budget=min(timeout,remaining-(time.monotonic()-start))
        if budget<=0:
            return {'status':'BUDGET_EXHAUSTED','runs':receipts}
        argv=[token.format(**substitutions) for token in contract['argv']]
        log=out/f'verifier-{seed}.log'
        status=run_process(argv,log,budget,memory_mb,cpus)
        if status['status']=='TIMEOUT':
            result=status
        elif log.stat().st_size>8*1024**2:
            result={'status':'OUTPUT_TOO_LARGE','log':str(log)}
        else:
            result=parse_receipt(log.read_text(errors='replace'),status['exit_code'],contract)
        result.update({'argv':argv,'seed':seed,'verifier_sha256':actual,
                       'candidate_sha256':digest,'log':str(log)})
        receipts.append(result)
        (out/'receipt.json').write_text(json.dumps({'runs':receipts},indent=2)+'\n')
        if result['status']!='PASS_FULL':
            return {'status':result['status'],'runs':receipts}
    if hashlib.sha256(candidate.read_bytes()).hexdigest()!=digest:
        return {'status':'CANDIDATE_CHANGED','runs':receipts}
    # Conservative score across the configured seeds.
    scores=[r['score'] for r in receipts]
    return {'status':'PASS_FULL','score':min(scores) if contract['direction']=='maximize' else max(scores),
            'runs':receipts,'candidate_sha256':digest,'verifier_sha256':actual}


def validate_contract(contract):
    if contract['direction'] not in ('maximize','minimize'):
        raise ValueError('direction must be maximize or minimize')
    if not contract.get('seeds') or not all(type(s) is int for s in contract['seeds']):
        raise ValueError('nonempty integer seeds required')
    if type(contract.get('full_shots')) is not int or contract['full_shots']<=0:
        raise ValueError('official full_shots must be a positive integer')
    if not contract.get('fields') or not contract.get('argv'):
        raise ValueError('Inspected official argv and metric field mapping required')
    if len(contract.get('script_sha256',''))!=64:
        raise ValueError('Pin the official verifier SHA256')


def better(value, reference, direction):
    return value>reference if direction=='maximize' else value<reference
