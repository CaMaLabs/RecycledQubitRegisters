"""Adaptive bounded region search, durable exact branches, official-only promotion."""
import concurrent.futures
from dataclasses import asdict
import fcntl
import heapq
import json
import math
import multiprocessing
import platform
import importlib.metadata
from pathlib import Path
import sys
import time
from .core import Gate, canonical, census, cost, parse, sha
from .passes import PLUGINS
from .store import Store
from .verification import better, run_process, validate_contract, verify

PIN='d7da8646fc6bef7a08f62f8039829fdc3a2669c9572aabf7936596d3ea6560e8'
REFERENCE=95368.85909206404


def regions(lines, budget, method, max_regions):
    parsed=[parse(line) for line in lines]
    def generate():
        for start,g in enumerate(parsed):
            if g is None: continue
            wires=set(); block=[]
            for end in range(start,min(len(parsed),start+budget['span'])):
                h=parsed[end]
                if h is None: break
                if method in {'mitm','smt','factor','stochastic'} and h.op not in {'X','CX','CCX','SWAP','CSWAP'}: break
                if method=='affine' and h.op not in {'X','CX','SWAP'}: break
                wires.update(h.q)
                if len(wires)>min(budget['wires'],3 if method=='mitm' else 4 if method=='smt' else 10): break
                block.append(h)
            if len(block)>=2:
                # Scored regions first; free affine cleanup can expose later work.
                rank=cost(block)[0]*1000+cost(block)[1]*100+len(block)
                yield rank,-start,start,start+len(block),block
    return [(a,b,g) for _,__,a,b,g in heapq.nlargest(max_regions,generate())]


def execute_worker(task_path, result_path, log_path, timeout, memory_mb, cpus):
    started=time.monotonic()
    status=run_process([sys.executable,'-m','competition.optimizer.autonomous.worker',
                       str(task_path),str(result_path)],log_path,timeout,memory_mb,cpus)
    if status.get('exit_code')==0 and Path(result_path).is_file():
        result=json.loads(Path(result_path).read_text())
    else:
        result={'status':status['status'] if status['status']=='TIMEOUT' else 'WORKER_FAILED',
                'reason':json.dumps(status)}
    return result,time.monotonic()-started


def choose(store, parent, methods):
    pending=[r for r in store.db.execute("SELECT * FROM experiments WHERE parent=? AND status='PENDING'",(parent,)) if r['method'] in methods]
    if not pending: return None
    stats={r['method']:dict(r) for r in store.db.execute('''SELECT method, COUNT(*) AS n,
       SUM(CASE WHEN status='LOCAL_IMPROVEMENT' AND json_extract(detail,'$.before_cost[0]') > json_extract(detail,'$.after_cost[0]') THEN 1 ELSE 0 END) AS wins,
       SUM(seconds) AS seconds FROM experiments WHERE status NOT IN ('RUNNING','PENDING') GROUP BY method''')}
    total=max(1,sum(r['n'] for r in stats.values()))
    available={r['method'] for r in pending}
    def ucb(method):
        r=stats.get(method)
        if not r: return float('inf')
        # Count exact discoveries as provisional exploration reward. Actual
        # score rewards are only added after official verification below.
        verified=0  # No reward for a PASS that has not improved the objective.
        return (r['wins']+4*verified)/max(1,r['seconds'])+math.sqrt(2*math.log(total+1)/r['n'])
    method=max((m for m in methods if m in available),key=ucb)
    # Escalate effort only after cheaper budgets for this method have completed.
    options=[r for r in pending if r['method']==method]
    return min(options,key=lambda r:(json.loads(r['config'])['level'],-json.loads(r['config'])['priority'],r['key']))


def enqueue(store, parent, lines, config):
    for level in range(config['levels']):
        budget={'level':level,'wires':min(10,config['width']+level),
                'span':min(128,config['span']*(level+1)),
                'seconds':config['seconds_per_job']*(level+1),
                'depth':config['depth']+level*2,'max_states':min(100000,config['max_states']*(level+1)),
                'implementation_sha256':sha(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.rglob('*.py'))))}
        for method in config['methods']:
            for start,end,gates in regions(lines,budget,method,config['max_regions']):
                trial=dict(budget,priority=cost(gates)[0]*100+cost(gates)[1])
                if method=='smt':
                    try: trial['solver_version']=importlib.metadata.version('z3-solver')
                    except importlib.metadata.PackageNotFoundError: trial['solver_version']=None
                store.add(parent,method,trial,[start,end],canonical(gates),config['seed'],commit=False)
    store.db.commit()


def run(args, config):
    for field in ('cpus','concurrency','memory_mb','max_jobs','max_regions','levels','width','span','depth','max_states'):
        if type(config[field]) is not int or config[field]<1: raise ValueError(field+' must be a positive integer')
    if config['width']>10 or config['span']>128 or config['levels']>8 or config['max_regions']>5000:
        raise ValueError('Hard limits: width<=10, span<=128, levels<=8, max_regions<=5000')
    if config['concurrency']>config['cpus']: raise ValueError('concurrency cannot exceed CPUs')
    if config['hours']<=0 or config['seconds_per_job']<=0 or config['verifier_timeout']<=0:
        raise ValueError('time limits must be positive')
    if config['memory_mb']<128*config['concurrency']: raise ValueError('Allow >=128 MiB per concurrent worker')
    if not set(config['methods']).issubset(PLUGINS) or not config['methods']: raise ValueError('Unknown/empty plugin selection')
    source=Path(args.source).resolve()
    raw=source.read_bytes(); digest=sha(raw)
    if digest!=args.expected_sha: raise ValueError('BASELINE_SHA_MISMATCH '+digest)
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    if source.is_relative_to(out): raise ValueError('Keep the immutable source outside the output directory')
    lock=(out/'controller.lock').open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise ValueError('Another controller owns this campaign')
    contract=json.loads(Path(args.contract).read_text()) if args.contract else None
    if contract: validate_contract(contract)
    store=Store(out/'experiments.sqlite3')
    identity={'source_sha256':digest,'seed':config['seed'],'contract':contract,
              'reference':args.reference_score,'engine_version':1}
    if store.get('identity',identity)!=identity:
        store.close(); raise ValueError('Campaign source/seed/verification contract changed; use a new output directory')
    store.set('identity',identity); store.recover()
    engine_sha=sha(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.rglob('*.py'))))
    implementation_dir=out/'implementations'; implementation_dir.mkdir(exist_ok=True)
    snapshot={str(p.relative_to(Path(__file__).parent)):p.read_text() for p in sorted(Path(__file__).parent.rglob('*.py'))}
    (implementation_dir/(engine_sha+'.json')).write_text(json.dumps(snapshot,sort_keys=True))
    run_record={'engine_sha256':engine_sha,'config':config,'python':sys.version,
                'platform':platform.platform(),'source_sha256':digest,'started_unix':time.time()}
    store.set('run_'+str(time.time_ns()),run_record)
    started=time.monotonic(); deadline=started+config['hours']*3600
    def remaining(): return max(0,deadline-time.monotonic())
    base_path=out/(digest+'.kmx')
    if not base_path.exists(): base_path.write_bytes(raw)
    if sha(base_path.read_bytes())!=digest: raise ValueError('Stored baseline was modified')
    store.candidate(digest,None,base_path,{'status':'USER_SUPPLIED_REFERENCE','official_score_reference':args.reference_score})
    current=store.get('current',digest)
    current_row=store.db.execute('SELECT * FROM candidates WHERE sha=?',(current,)).fetchone()
    current_path=out/(current+'.kmx')
    if not current_path.exists():
        # A transferred SQLite campaign can reconstruct missing intermediate
        # files from its retained exact replacement records.
        from competition.optimizer.replay_candidate import replay
        replay(out/'experiments.sqlite3',source,current,current_path)
    working=current_path.read_bytes()
    store.db.execute('UPDATE candidates SET path=? WHERE sha=?',(str(base_path),digest))
    store.db.execute('UPDATE candidates SET path=? WHERE sha=?',(str(current_path),current))
    store.db.commit()
    if sha(working)!=current: raise ValueError('Checkpoint candidate digest mismatch')
    best=store.get('best')
    if best:
        best_path=out/(best['sha']+'.kmx')
        if not best_path.exists():
            from competition.optimizer.replay_candidate import replay
            replay(out/'experiments.sqlite3',source,best['sha'],best_path)
        if sha(best_path.read_bytes())!=best['sha']: raise ValueError('Official best digest mismatch')
        best['path']=str(best_path);store.set('best',best)
    try:
        # Never compare differently configured baseline/candidate score receipts.
        if contract and not best:
            result=verify(base_path,out/'verify'/digest,contract,config['verifier_timeout'],
                          config['memory_mb'],config['cpus'],remaining())
            store.receipt(digest,result)
            if result['status']!='PASS_FULL':
                raise ValueError('Baseline official verification failed: '+result['status'])
            best={'sha':digest,'score':result['score'],'path':str(base_path)}
            store.set('best',best)
        elif not contract:
            print('OFFICIAL_VERIFICATION_UNAVAILABLE: no inspected verifier contract; promotion disabled',flush=True)
        enqueue(store,current,working.decode('ascii').splitlines(keepends=True),config)
        count=0
        context=multiprocessing.get_context('spawn')
        with concurrent.futures.ProcessPoolExecutor(max_workers=config['concurrency'],mp_context=context) as pool:
            while remaining()>0 and count<config['max_jobs']:
                lines=working.decode('ascii').splitlines(keepends=True)
                batch=[]
                for _ in range(min(config['concurrency'],config['max_jobs']-count)):
                    row=choose(store,current,config['methods'])
                    if row is None: break
                    start,end=json.loads(row['region']); budget=json.loads(row['config'])
                    gates=[parse(x) for x in lines[start:end]]
                    if any(g is None for g in gates) or canonical(gates)!=row['canonical']:
                        store.finish(row['key'],'STALE','Parent/region no longer matches'); continue
                    store.db.execute("UPDATE experiments SET status='RUNNING' WHERE key=?",(row['key'],)); store.db.commit()
                    task_dir=out/'tasks'/row['key']; task_dir.mkdir(parents=True,exist_ok=True)
                    task=task_dir/'task.json'; result_path=task_dir/'result.json'
                    task.write_text(json.dumps({'method':row['method'],'budget':budget,'seed':row['seed'],
                                                'gates':[asdict(g) for g in gates]}))
                    future=pool.submit(execute_worker,task,result_path,task_dir/'worker.log',
                        min(remaining(),budget['seconds']+2),config['memory_mb']//config['concurrency'],1)
                    batch.append((dict(row),future)); count+=1
                if not batch: break
                # All edits in a batch use the same pinned parent. Retain every
                # child; advance the exact working branch using the best child.
                children=[]
                for row,future in batch:
                    result,elapsed=future.result()
                    child=None
                    if result['status']=='LOCAL_IMPROVEMENT':
                        start,end=json.loads(row['region'])
                        replacement=[Gate(g['op'],tuple(g['q'])).text() for g in result['gates']]
                        candidate=''.join(lines[:start]+replacement+lines[end:]).encode('ascii')
                        child=sha(candidate); path=out/(child+'.kmx')
                        if not path.exists(): path.write_bytes(candidate)
                        proof={'local':result['proof'],'region':[start,end],'parent':current,
                               'task':row['key'],'detail':result.get('detail')}
                        store.candidate(child,current,path,proof)
                        children.append((result['before_cost'][0]-result['after_cost'][0],
                                         result['before_cost'][2]-result['after_cost'][2],child,candidate,path))
                        # A free-gate rewrite is useful internally but has no
                        # positive direct score estimate; do not spend verifier time.
                        if contract and (result['after_cost'][:2]<result['before_cost'][:2]) and remaining()>0:
                            receipt=verify(path,out/'verify'/child,contract,config['verifier_timeout'],
                                           config['memory_mb'],config['cpus'],remaining())
                            store.receipt(child,receipt)
                            if receipt['status']=='PASS_FULL' and better(receipt['score'],best['score'],contract['direction']):
                                best={'sha':child,'score':receipt['score'],'path':str(path)}
                                store.set('best',best)
                                print('OFFICIAL_PROMOTION',json.dumps(best),flush=True)
                    store.finish(row['key'],result['status'],result.get('reason',''),elapsed,
                                 result.get('proof'),child,result)
                    print('EXPERIMENT',json.dumps({'method':row['method'],'status':result['status'],
                        'seconds':round(elapsed,3),'candidate':child}),flush=True)
                if children:
                    _,__,current,working,_=max(children,key=lambda x:(x[0],x[1],x[2]))
                    store.set('current',current)
                    # Retain siblings. Re-optimizing the chosen exact branch
                    # rediscovers applicable independent rewrites against its parent.
                    enqueue(store,current,working.decode('ascii').splitlines(keepends=True),config)
        summary={'source_sha256':digest,'reference_score':args.reference_score,
                 'reference_status':'USER_REPORTED' if not contract else 'RECHECKED',
                 'objective':contract['direction'] if contract else 'UNRESOLVED_NO_OFFICIAL_CONTRACT',
                 'jobs_this_run':count,'elapsed_seconds':time.monotonic()-started,
                 'best_official':best,'current_exact_candidate':current,
                 'success':bool(best and better(best['score'],args.reference_score,contract['direction'])),
                 'census':census(working.decode('ascii').splitlines()),
                 'experiment_counts':dict(store.db.execute('SELECT status,COUNT(*) FROM experiments GROUP BY status'))}
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print('CAMPAIGN_RESULT',json.dumps(summary),flush=True)
        return summary
    finally:
        store.export(out/'registry.json'); store.close(); lock.close()
