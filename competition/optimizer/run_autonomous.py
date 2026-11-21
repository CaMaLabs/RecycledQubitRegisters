#!/usr/bin/env python3
"""Run as a script from any working directory; assets stay rooted in the repo."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from competition.optimizer.autonomous.controller import PIN, REFERENCE, run
from competition.optimizer.autonomous.verification import run_process


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',default='competition/k191/results/helios_k191.kmx')
    p.add_argument('--expected-sha',default=PIN)
    p.add_argument('--reference-score',type=float,default=REFERENCE)
    p.add_argument('--out',default='competition/optimizer/runs/autonomous')
    p.add_argument('--profile',choices=['quick','overnight','extended'],default='quick')
    p.add_argument('--config',help='JSON overrides of profile settings')
    p.add_argument('--verify',action='store_true',help='Inspect installed official defaults and verify every eligible candidate')
    p.add_argument('--score-direction',choices=['minimize','maximize'],help='Required with --verify: historical verifier score is a cost')
    p.add_argument('--official-script',default='competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py')
    p.add_argument('--contract',help='Inspected official verifier argv, SHA, metrics and full-domain contract')
    p.add_argument('--hours',type=float)
    p.add_argument('--max-jobs',type=int)
    p.add_argument('--resume',action='store_true',help='State always resumes; retained for explicit CLI intent')
    a=p.parse_args()
    # Resolve user paths BEFORE rooting subprocess module imports in this repo.
    for name in ('source','out','config','contract','official_script'):
        value=getattr(a,name)
        if value is not None: setattr(a,name,str(Path(value).expanduser().resolve()))
    config=json.loads((Path(__file__).parent/'profiles'/(a.profile+'.json')).read_text())
    if a.config: config.update(json.loads(Path(a.config).read_text()))
    if a.hours is not None: config['hours']=a.hours
    if a.max_jobs is not None: config['max_jobs']=a.max_jobs
    os.chdir(ROOT)
    if a.verify and not a.contract:
        if not a.score_direction: p.error('--verify requires an explicit --score-direction')
        out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
        a.contract=str(out/'official-contract.json')
        log=out/'official-inspection.log'
        result=run_process([sys.executable,'-m','competition.optimizer.autonomous.official_contract',
                '--script',a.official_script,'--output',a.contract,'--direction',a.score_direction],
                log,min(30,config['hours']*3600),config['memory_mb'],config['cpus'])
        if result.get('exit_code')!=0:
            p.exit(2,'Official asset inspection failed; see '+str(log)+'\n')
    try: run(a,config)
    except (ValueError,OSError,KeyError) as exc: p.exit(2,str(exc)+'\n')

if __name__=='__main__': main()
