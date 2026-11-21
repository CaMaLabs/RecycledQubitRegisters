#!/usr/bin/env python3
"""Adaptive, resumable KMX optimization campaign.

Each stage runs the exact local-rewrite engine with a separate checkpoint.
Stages increase window width, depth and beam; every result is provenance-tracked.
This scheduler does not claim SAT/SMT, rotation or arithmetic synthesis support.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path

def save(path,data):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data,indent=2,sort_keys=True))
    os.replace(temp,path)

def stage_plan(args):
    # Favor nonlinear regions before spending time on wider, expensive searches.
    for wires,span,depth,beam,seconds,minimum in [
        (5,16,2,8,1.0,2),
        (6,24,3,12,2.0,2),
        (7,32,4,16,3.0,3),
        (8,48,5,20,5.0,3),
        (9,64,6,24,8.0,4),
    ]:
        if wires>args.max_wires:continue
        for seed in range(args.seeds):
            yield {'wires':wires,'span':span,'depth':depth,'beam':beam,
                   'seconds':seconds,'min_ccx':minimum,'seed':args.seed+seed}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='competition/k191/results/helios_k191.kmx')
    p.add_argument('--out',default='competition/optimizer/campaign')
    p.add_argument('--engine',default=str(Path(__file__).with_name('quantum_optimizer.py')))
    p.add_argument('--max-wires',type=int,default=8)
    p.add_argument('--max-blocks',type=int,default=150)
    p.add_argument('--seeds',type=int,default=2)
    p.add_argument('--seed',type=int,default=12345)
    p.add_argument('--hours',type=float,default=8)
    p.add_argument('--verify',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    if not 3<=a.max_wires<=10 or a.hours<=0 or a.seeds<1:raise SystemExit('invalid campaign parameters')
    source=Path(a.source)
    if not source.is_file():raise SystemExit('source not found: '+str(source))
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    manifest=out/'manifest.json'
    config={'source_sha':source_sha,'max_wires':a.max_wires,'max_blocks':a.max_blocks,'seeds':a.seeds,'seed':a.seed}
    config_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    if manifest.exists():
        state=json.loads(manifest.read_text())
        if state.get('config_hash')!=config_hash:raise SystemExit('CAMPAIGN_CONFIGURATION_CHANGED: choose another --out')
    else:
        state={'config_hash':config_hash,'source_sha':source_sha,'stages':{},'best':None}
        save(manifest,state)
    start=time.monotonic()
    stages=list(stage_plan(a))
    print('CAMPAIGN_START',json.dumps({'source_sha':source_sha,'stages':len(stages),'completed':sum(v.get('status')=='complete' for v in state['stages'].values())}),flush=True)
    for index,stage in enumerate(stages):
        name=f'stage_{index:03d}_w{stage["wires"]}_d{stage["depth"]}_s{stage["seed"]}'
        prior=state['stages'].get(name,{})
        if prior.get('status')=='complete':continue
        if time.monotonic()-start>=a.hours*3600:break
        stage_dir=out/name
        stage_dir.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,a.engine,'--source',str(source),'--expected-sha',source_sha,
             '--out',str(stage_dir),'--max-wires',str(stage['wires']),
             '--max-span',str(stage['span']),'--min-ccx',str(stage['min_ccx']),
             '--max-ccx','6','--max-blocks',str(a.max_blocks),
             '--beam',str(stage['beam']),'--depth',str(stage['depth']),
             '--seconds-per-block',str(stage['seconds']),'--seed',str(stage['seed'])]
        if prior.get('status')=='interrupted':cmd.append('--resume')
        if a.verify:cmd.append('--verify')
        print('CAMPAIGN_STAGE',name,json.dumps(stage),flush=True)
        if a.dry_run:
            print('CAMPAIGN_COMMAND',json.dumps(cmd),flush=True)
            continue
        with (stage_dir/'run.log').open('a') as log:
            log.write('COMMAND '+json.dumps(cmd)+'\n')
            log.flush()
            proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=False)
        candidate_file=stage_dir/'candidate.json'
        candidate=json.loads(candidate_file.read_text()) if candidate_file.exists() else None
        verification_file=stage_dir/'verification.json'
        verification=json.loads(verification_file.read_text()) if verification_file.exists() else None
        status='complete' if proc.returncode==0 else 'failed'
        state['stages'][name]={'status':status,'returncode':proc.returncode,
                               'candidate':candidate,'verification':verification}
        # Candidate is provisional: a successful process exit is NOT an official PASS.
        if candidate:
            print('CAMPAIGN_PROVISIONAL_CANDIDATE',name,json.dumps(candidate),flush=True)
            state['best_provisional']=name if not state.get('best_provisional') else state['best_provisional']
        save(manifest,state)
        print('CAMPAIGN_STAGE_END',name,'returncode',proc.returncode,flush=True)
        if proc.returncode:print('CAMPAIGN_STAGE_FAILED_LOG',str(stage_dir/'run.log'),flush=True)
    print('CAMPAIGN_COMPLETE',json.dumps({'complete':sum(v.get('status')=='complete' for v in state['stages'].values()),'total':len(stages),'manifest':str(manifest),'official_best':state['best']}),flush=True)
if __name__=='__main__':main()
