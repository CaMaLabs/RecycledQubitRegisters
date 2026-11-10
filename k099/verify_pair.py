#!/usr/bin/env python3
"""Matched DQI Monte Carlo check, with explicit problem size and draw settings.
Default 4096 shots is a smoke test, not the competition's 102400-shot run.
No source/failure sampling, scorer changes or score-based seed selection.
"""
import argparse,json,subprocess,sys,time,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--verifiers',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--shots',type=int,default=4096);p.add_argument('--seed',type=int,default=12345);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);results={}
for name,path in [('baseline',a.baseline),('candidate',a.candidate)]:
 command=[sys.executable,str(a.verifiers/'dqi/verify_submission_dqi.py'),str(path),'--num-shots',str(a.shots),'--batch-size','256','--max-workers','1','--seed',str(a.seed)];start=time.monotonic();r=subprocess.run(command,capture_output=True,text=True,timeout=1800)
 try:report=json.loads(r.stdout)
 except Exception:report={'status':'NON_JSON','stdout_tail':r.stdout[-2000:]}
 report['exit_code']=r.returncode;report['elapsed_s']=time.monotonic()-start;report['command']=command
 if r.stderr:report['stderr_tail']=r.stderr[-2000:]
 results[name]=report;(a.out/(name+'.json')).write_text(json.dumps(report,indent=2));print('K099_VERIFY',name,report.get('status'),report.get('score'),report['elapsed_s'],flush=True)
fields=['status','num_qubits','toffoli_count','value_errors','phase_errors','score'];comparison={key:{name:r.get(key) for name,r in results.items()} for key in fields};summary={'settings':{'shots':a.shots,'seed':a.seed,'batch_size':256,'workers':1,'m':4095,'n':70,'degree':12},'default_shot_count':102400,'default_configuration_run':a.shots==102400,'comparison':comparison,'elapsed_ratio_candidate_over_baseline':results['candidate']['elapsed_s']/results['baseline']['elapsed_s'],'scored_resource_gain':False,'note':'Exact Clifford cancellation leaves width and nonlinear gates unchanged; runtime is an implementation metric.'};(a.out/'comparison.json').write_text(json.dumps(summary,indent=2));print('K099_PAIR_RESULT',json.dumps(summary),flush=True)
