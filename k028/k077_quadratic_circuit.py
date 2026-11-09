#!/usr/bin/env python3
"""K077 quadratic Kickmix build using K076's existing reversible circuit builder.
The alternative is 128 segments, degree 2 (instead of 16, degree 4).
This is a test candidate, never a claimed full-domain score until verified.
"""
import argparse,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load():
 path=ROOT/'competition/k076/k076_range_reduced_circuit.py'
 if not path.is_file():raise SystemExit('Missing '+str(path)+'; install K076 first')
 spec=importlib.util.spec_from_file_location('k076_for_k077',path)
 module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
 spec.loader.exec_module(module)
 return module
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--out',type=Path,default=ROOT/'competition/k077/results')
 p.add_argument('--prefix',type=int,default=15)
 p.add_argument('--timeout',type=int,default=600)
 p.add_argument('--full',action='store_true')
 p.add_argument('--self-test',action='store_true')
 a=p.parse_args()
 m=load()
 m.SEG_BITS=7;m.SEGMENTS=128;m.DEG=2
 m.TB=m.FRAC-m.SEG_BITS;m.PW=m.W+m.TB
 tab=m.coefficients()
 verified=m.validate_model(tab)
 print('K077_MODEL_SELFTEST',json.dumps({'status':'PASS','sample_inputs':verified,
  'segments':m.SEGMENTS,'degree':m.DEG,'low_fraction_bits':m.TB}),flush=True)
 if a.self_test:return
 a.out.mkdir(parents=True,exist_ok=True)
 report={'architecture':'128-segment quadratic K076 builder reuse',
  'official_full_domain':False,'status':'NOT_BUILT','numeric_samples':verified}
 try:
  path=a.out/'quadratic_128_candidate.kmb'
  print('K077_BUILD_START',json.dumps({'segments':128,'degree':2}),flush=True)
  start=time.monotonic()
  info=m.build(path,tab)
  print('K077_BUILD',json.dumps(info,sort_keys=True),flush=True)
  results=m.official(path,a.prefix,a.timeout,a.full)
  report['build']=info;report['verifications']=results
  report['elapsed_s']=round(time.monotonic()-start,2)
  pre=results.get('prefix',{})
  passed=pre.get('status')=='PASS' and pre.get('exit_code')==0
  if a.full:
   passed=passed and all(results.get(k,{}).get('status')=='PASS' and
     results.get(k,{}).get('exit_code')==0 for k in ('full_seed_12345','full_seed_23456'))
  report['status']='PASS_FULL' if passed and a.full else 'PASS_PREFIX_ONLY' if passed else 'FAIL'
  report['official_full_domain']=bool(passed and a.full)
 except Exception as ex:
  report['status']='BUILD_ERROR';report['error']=repr(ex)
 (a.out/'quadratic_build.json').write_text(json.dumps(report,indent=2,default=str))
 print('K077_RESULT',json.dumps({'status':report['status'],
   'num_qubits':report.get('build',{}).get('num_qubits'),
   'score':report.get('verifications',{}).get('prefix',{}).get('score'),
   'error':report.get('error')}),flush=True)
 print('SAVED',a.out/'quadratic_build.json',flush=True)
if __name__=='__main__':main()
