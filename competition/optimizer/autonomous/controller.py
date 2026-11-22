"""Adaptive bounded region search, durable exact branches, official-only promotion."""
import concurrent.futures
from collections import Counter
from dataclasses import asdict
import fcntl
import heapq
import json
import math
import multiprocessing
import platform
import importlib.metadata
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import time
from .core import DIAG, gate_from_record, canonical, census, cost, parse, sha, signature
from .conditional import parse_guarded, parse_region, render_region
from .passes import PLUGINS
from .store import Store
from .structured import PHASE_REGION
from .phase_precision import PHASE_OPS
from .verification import better, run_process, validate_contract, verify

PIN='d7da8646fc6bef7a08f62f8039829fdc3a2669c9572aabf7936596d3ea6560e8'
REFERENCE=95368.85909206404


def regions(lines, budget, method, max_regions):
    guarded = method == 'conditional_phase'
    parsed = [parse_guarded(line) if guarded else parse(line) for line in lines]
    def generate():
        for start,g in enumerate(parsed):
            if g is None: continue
            guard = g[1] if guarded else None
            wires=set(); block=[]
            for end in range(start,min(len(parsed),start+budget['span'])):
                h=parsed[end]
                if h is None: break
                if guarded:
                    h, condition = h
                    if condition != guard or (h.op not in DIAG and h.op != 'Z_POW'):
                        break
                if method in {'mitm','smt','factor','stochastic','arithmetic','workspace_reuse','affine_smt'} and h.op not in {'X','CX','CCX','SWAP','CSWAP'}: break
                if method=='affine' and h.op not in {'X','CX','SWAP'}: break
                if method=='parity_spectrum' and h.op not in PHASE_REGION: break
                if method=='phase_function' and (h.op not in PHASE_OPS or
                                                h.op in {'CZ','CCZ'}): break
                wires.update(h.q)
                if len(wires)>min(budget['wires'],3 if method=='mitm' else 4 if method=='smt' else 6 if method=='affine_smt' else 8 if method=='arithmetic' else 10): break
                block.append(h)
            if len(block)>=2:
                if method in {'arithmetic', 'workspace_reuse', 'affine_smt'} and cost(block)[0]<2:
                    continue
                if method == 'workspace_reuse':
                    ccx = Counter(g for g in block if g.op == 'CCX')
                    receivers = {g.q[0] for g in block if g.op == 'CX'}
                    if not any(n >= 2 and g.q[-1] in receivers for g,n in ccx.items()):
                        continue
                # Scored regions first; free affine cleanup can expose later work.
                rank=cost(block)[0]*1000+cost(block)[1]*100+len(block)
                if method in {'phase_function','phase_predicate'}:
                    sites = sum(g.op in {'Z_POW','T','T_DAG','S','S_DAG','Z'} for g in block)
                    if sites < 2:
                        continue
                    rank = sites * 1000 + cost(block)[1] * 100 + len(block)
                yield rank,-start,start,start+len(block),block,guard
    return [(a,b,g,guard) for _,__,a,b,g,guard in heapq.nlargest(max_regions,generate())]


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
       SUM(CASE WHEN status='LOCAL_IMPROVEMENT' AND (json_extract(detail,'$.before_cost[0]') > json_extract(detail,'$.after_cost[0]') OR json_extract(detail,'$.before_cost[1]') > json_extract(detail,'$.after_cost[1]')) THEN 1 ELSE 0 END) AS wins,
       SUM(seconds) AS seconds FROM experiments WHERE status NOT IN ('PENDING','COMPOSED') GROUP BY method''')}
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
            for start,end,gates,guard in regions(lines,budget,method,config['max_regions']):
                trial=dict(budget,priority=cost(gates)[0]*100+cost(gates)[1])
                if guard is not None:
                    trial['guard'] = guard
                if method in {'smt','affine_smt'}:
                    try: trial['solver_version']=importlib.metadata.version('z3-solver')
                    except importlib.metadata.PackageNotFoundError: trial['solver_version']=None
                store.add(parent,method,trial,[start,end],canonical(gates),config['seed'],commit=False)
    store.db.commit()


def synthesis_key(gates, budget, seed, method="affine_smt"):
    """Order-preserving wire canonicalization of exact Boolean behavior."""
    wires = sorted({q for gate in gates for q in gate.q})
    settings = {key: value for key, value in budget.items() if key != "priority"}
    mapping = [output for output, _ in signature(gates, wires)]
    key = sha(json.dumps([method, mapping, cost(gates), settings, seed], sort_keys=True))
    return key, wires


def run(args, config, export=None):
    for field in ('cpus','concurrency','memory_mb','max_jobs','max_regions','levels','width','span','depth','max_states'):
        if type(config[field]) is not int or config[field]<1: raise ValueError(field+' must be a positive integer')
    if config['width']>10 or config['span']>128 or config['levels']>8 or config['max_regions']>5000:
        raise ValueError('Hard limits: width<=10, span<=128, levels<=8, max_regions<=5000')
    if config['concurrency']>config['cpus']: raise ValueError('concurrency cannot exceed CPUs')
    if config['hours']<=0 or config['seconds_per_job']<=0 or config['verifier_timeout']<=0:
        raise ValueError('time limits must be positive')
    if config['memory_mb']<128*config['concurrency']: raise ValueError('Allow >=128 MiB per concurrent worker')
    if not set(config['methods']).issubset(PLUGINS) or not config['methods']: raise ValueError('Unknown/empty plugin selection')
    verify_every = getattr(args, 'verify_every', 20)
    if verify_every < 0:
        raise ValueError('--verify-every must be nonnegative')
    source=Path(args.source).resolve()
    raw=source.read_bytes(); digest=sha(raw)
    if digest!=args.expected_sha: raise ValueError('BASELINE_SHA_MISMATCH '+digest)
    out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=True)
    if source.is_relative_to(out): raise ValueError('Keep the immutable source outside the output directory')
    lock=(out/'controller.lock').open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise ValueError('Another controller owns this campaign')
    contract=json.loads(Path(args.contract).read_text()) if args.contract else None
    store=Store(out/'experiments.sqlite3')
    saved_identity = store.get('identity')
    if saved_identity and getattr(args, 'resume', False):
        if not args.contract:
            contract = saved_identity['contract']
        if not getattr(args, 'reference_explicit', args.reference_score is not None):
            args.reference_score = saved_identity['reference']
    if contract:
        validate_contract(contract)
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
                'platform':platform.platform(),'source_sha256':digest,'started_unix':time.time(),
                'requested_checkpoint':getattr(args, 'start_from', None),'verify_every':verify_every}
    store.set('run_'+str(time.time_ns()),run_record)
    started=time.monotonic(); deadline=started+config['hours']*3600
    def remaining(): return max(0,deadline-time.monotonic())
    base_path=out/(digest+'.kmx')
    if not base_path.exists(): base_path.write_bytes(raw)
    if sha(base_path.read_bytes())!=digest: raise ValueError('Stored baseline was modified')
    store.candidate(digest,None,base_path,{'status':'SOURCE','official_score_reference':args.reference_score})
    current=store.get('current',digest)
    requested = getattr(args, 'start_from', None)
    if requested:
        from competition.optimizer.replay_candidate import replay
        if store.db.execute('SELECT 1 FROM candidates WHERE sha=?', (requested,)).fetchone() is None:
            raise ValueError('Unknown archived candidate: ' + requested)
        checkpoint = out / (requested + '.kmx')
        with TemporaryDirectory(dir=out) as temporary:
            reconstructed = Path(temporary) / 'checkpoint.kmx'
            replay(out/'experiments.sqlite3', source, requested, reconstructed)
            if checkpoint.exists():
                if sha(checkpoint.read_bytes()) != requested:
                    raise ValueError('Archived candidate digest mismatch')
            else:
                reconstructed.replace(checkpoint)
        current = requested
        store.set('current', current)
        print('CHECKPOINT_SELECTED', current, flush=True)
    started_from = current
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
        verified_this_run = set()

        def drain_verification_queue():
            nonlocal best
            if not contract:
                return
            for row in store.pending_verifications():
                child = row['sha']
                if child in verified_this_run or remaining() <= 0:
                    continue
                path = out / (child + '.kmx')
                if not path.exists():
                    from competition.optimizer.replay_candidate import replay
                    replay(out/'experiments.sqlite3', source, child, path)
                if sha(path.read_bytes()) != child:
                    raise ValueError('Pending verifier candidate digest mismatch')
                verified_this_run.add(child)
                receipt = verify(path,out/'verify'/child,contract,config['verifier_timeout'],
                                 config['memory_mb'],config['cpus'],remaining())
                store.receipt(child,receipt)
                if (receipt['status']=='PASS_FULL'
                        and better(receipt['score'],best['score'],contract['direction'])):
                    best={'sha':child,'score':receipt['score'],'path':str(path)}
                    store.set('best',best)
                    print('OFFICIAL_PROMOTION',json.dumps(best),flush=True)

        if contract and requested and verify_every and current != digest:
            store.queue_verification(current, 0)
        drain_verification_queue()
        enqueue(store,current,working.decode('ascii').splitlines(keepends=True),config)
        count=0
        since_checkpoint=0
        context=multiprocessing.get_context('spawn')
        with concurrent.futures.ProcessPoolExecutor(max_workers=config['concurrency'],mp_context=context) as pool:
            while remaining()>0 and count<config['max_jobs']:
                lines=working.decode('ascii').splitlines(keepends=True)
                batch=[]
                for _ in range(min(config['concurrency'],config['max_jobs']-count)):
                    row=choose(store,current,config['methods'])
                    if row is None: break
                    start,end=json.loads(row['region']); budget=json.loads(row['config'])
                    gates=parse_region(lines[start:end], budget.get('guard'))
                    if any(g is None for g in gates) or canonical(gates)!=row['canonical']:
                        store.finish(row['key'],'STALE','Parent/region no longer matches'); continue
                    store.db.execute("UPDATE experiments SET status='RUNNING' WHERE key=?",(row['key'],)); store.db.commit()
                    task_dir=out/'tasks'/row['key']; task_dir.mkdir(parents=True,exist_ok=True)
                    task=task_dir/'task.json'; result_path=task_dir/'result.json'
                    payload = {'method':row['method'],'budget':budget,'seed':row['seed'],
                               'gates':[asdict(g) for g in gates]}
                    semantic = None
                    if row['method'] in {'affine_smt','mitm'}:
                        key, wires = synthesis_key(gates, budget, row['seed'], row['method'])
                        semantic = key, wires
                        cached = store.cached_synthesis(key)
                        if cached:
                            payload['cached'] = cached
                            payload['wire_order'] = wires
                    task.write_text(json.dumps(payload))
                    future=pool.submit(execute_worker,task,result_path,task_dir/'worker.log',
                        min(remaining(),budget['seconds']+2),config['memory_mb']//config['concurrency'],1)
                    batch.append((dict(row),future,semantic)); count+=1
                if not batch: break
                children = []

                def retain(parent, source_lines, interval, row, result):
                    start, end = interval
                    guard = json.loads(row['config']).get('guard')
                    replacement = render_region([gate_from_record(g) for g in result['gates']], guard)
                    candidate = ''.join(source_lines[:start]+replacement+source_lines[end:]).encode('ascii')
                    child = sha(candidate)
                    path = out/(child+'.kmx')
                    if not path.exists():
                        path.write_bytes(candidate)
                    proof = {'local':result['proof'], 'region':[start,end], 'parent':parent,
                             'task':row['key'], 'detail':result.get('detail')}
                    store.candidate(child,parent,path,proof)
                    return child, candidate, path

                for row, future, semantic in batch:
                    result, elapsed = future.result()
                    if semantic and result['status'] in {'LOCAL_IMPROVEMENT','UNSAT'}:
                        key, wires = semantic
                        normalized = [
                            {**gate, 'q': [wires.index(q) for q in gate['q']]}
                            for gate in result.get('gates', [])
                        ]
                        store.remember_synthesis(key, {'status':result['status'],
                            'gates':normalized, 'detail':result.get('detail',{})})
                    child = None
                    if result['status'] == 'LOCAL_IMPROVEMENT':
                        region = json.loads(row['region'])
                        child, candidate, path = retain(current, lines, region, row, result)
                        gain = tuple(x-y for x,y in zip(result['before_cost'],result['after_cost']))
                        children.append((gain, child, candidate, path, region, row, result))
                    store.finish(row['key'],result['status'],result.get('reason',''),elapsed,
                                 result.get('proof'),child,result)
                    print('EXPERIMENT',json.dumps({'method':row['method'],'status':result['status'],
                        'seconds':round(elapsed,3),'candidate':child}),flush=True)

                if not children:
                    continue
                children.sort(key=lambda child:(child[0],child[1]),reverse=True)
                total_gain,current,working,current_path,region,_,first_result = children[0]
                applied = [(region, len(first_result['gates'])-(region[1]-region[0]))]
                for gain,_,__,___,region,row,result in children[1:]:
                    start,end = region
                    if any(start < prior_end and end > prior_start
                           for (prior_start,prior_end),_ in applied):
                        continue
                    offset = sum(delta for (_,prior_end),delta in applied if prior_end <= start)
                    relocated = [start+offset,end+offset]
                    composition_config = dict(json.loads(row['config']), composed_from=row['key'])
                    new_key = store.add(current,row['method'],composition_config,relocated,
                                        row['canonical'],row['seed'])
                    combined_row = {**row,'key':new_key}
                    current,working,current_path = retain(
                        current, working.decode('ascii').splitlines(keepends=True),
                        relocated, combined_row, result)
                    store.finish(new_key,'COMPOSED','Disjoint edits with independent exact proofs',
                                 equivalence=result['proof'],candidate=current,detail=result)
                    applied.append((region,len(result['gates'])-(end-start)))
                    total_gain = tuple(a+b for a,b in zip(total_gain,gain))

                store.set('current',current)
                since_checkpoint += len(applied)
                if contract:
                    if verify_every and since_checkpoint >= verify_every:
                        store.queue_verification(current, 0)
                        since_checkpoint = 0
                    for gain, child, _, _, *_ in children:
                        if gain[:2] > (0,0):
                            store.queue_verification(child, gain[0]*1000+gain[1])
                    if total_gain[:2] > (0,0):
                        store.queue_verification(current, total_gain[0]*1000+total_gain[1])
                    drain_verification_queue()
                enqueue(store,current,working.decode('ascii').splitlines(keepends=True),config)
        if contract and verify_every and current != digest:
            store.queue_verification(current, 0)
            drain_verification_queue()
        baseline_score = store.db.execute('SELECT score FROM candidates WHERE sha=?',(digest,)).fetchone()[0]
        reference_score = args.reference_score if args.reference_score is not None else baseline_score
        summary={'source_sha256':digest,'reference_score':reference_score,
                 'reference_status':('USER_REPORTED' if args.reference_score is not None else 'RECHECKED' if contract else 'NONE'),
                 'measured_baseline_score':baseline_score,'started_from':started_from,
                 'objective':contract['direction'] if contract else 'MINIMIZE_STATIC_GATE_COST',
                 'jobs_this_run':count,'elapsed_seconds':time.monotonic()-started,
                 'best_official':best,'current_exact_candidate':current,'output_circuit':str(out/(current+'.kmx')),'output_format':'kmx',
                 'success':bool(best and best['sha'] != digest and baseline_score is not None and better(best['score'],baseline_score,contract['direction'])),
                 'beats_reference':bool(best and reference_score is not None and better(best['score'],reference_score,contract['direction'])),
                 'archived_candidate_count':store.db.execute('SELECT count(*) FROM candidates').fetchone()[0],
                 'census':census(working.decode('ascii').splitlines()),
                 'experiment_counts':dict(store.db.execute('SELECT status,COUNT(*) FROM experiments GROUP BY status'))}
        if export is not None:
            summary.update(export(working, out))
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print('CAMPAIGN_RESULT',json.dumps(summary),flush=True)
        return summary
    finally:
        store.export(out/'registry.json'); store.close(); lock.close()
