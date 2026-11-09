#!/usr/bin/env python3
"""K090 selective three-bit coherent ANF predicate caching.

Runs K086 with 0,2,4,8,12,16,24,32,48 or 56 retained triple prefixes.
Rank prefixes by weighted usage in all coefficient load/unload invocations,
then test actual official Kickmix score after building entire 22-bit circuit.

The 4095-input test is a PREFIX only, not full-domain verification.
"""
from __future__ import annotations
import argparse,collections,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None:raise RuntimeError('Cannot import '+str(path))
 m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def first_n_mask(mask,n):
 selected=0
 while n:
  bit=mask&-mask
  selected|=bit;mask^=bit;n-=1
 return selected

def rank_triples(m,coefficients):
 usage=collections.Counter()
 # DEG coefficient is loaded/unloaded once each; remaining DEG
 # coefficients are loaded/unloaded on forward and backward evaluation.
 words=m.anf_words(coefficients)
 for degree,values in enumerate(words):
  loads=2 if degree==m.DEG else 4
  for mask,value in enumerate(values):
   if value and mask.bit_count()>=3:
    usage[first_n_mask(mask,3)]+=loads
 return sorted(usage,key=lambda mask:(-usage[mask],mask.bit_count(),mask)),usage

def transform(selected,k086,k087):
 def apply(source):
  if not selected:return source
  source=k087.triple_cache(source,k086)
  source=k086.patch_once(source,
 ''' triple_masks=sorted({triple_of(mask) for coeff in anf
                      for mask,value in enumerate(coeff)
                      if value and mask.bit_count()>=3})
''',
 ''' triple_masks=sorted(SELECTED_TRIPLES)
''')
  source=k086.patch_once(source,
 '''   if len(bits)>=3:
    control=triple_cache[triple_of(mask)][0]
    remaining=bits[3:]
''',
 '''   if len(bits)>=3 and triple_of(mask) in triple_cache:
    control=triple_cache[triple_of(mask)][0]
    remaining=bits[3:]
''')
  return source
 return apply

def passed(r):return r.get('status')=='PASS' and r.get('exit_code')==0

def run():
 p=argparse.ArgumentParser()
 p.add_argument('--counts',type=int,nargs='+',default=[0,2,4,8,12,16,24,32,48,56])
 p.add_argument('--prefix',type=int,default=4095)
 p.add_argument('--timeout',type=int,default=600)
 p.add_argument('--full-best',action='store_true',
  help='After all cases, reverify the lowest-score wide-prefix PASS on two official full seeds')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k090/results')
 a=p.parse_args()
 if not 15<=a.prefix<=3133452:raise ValueError('prefix outside official limits')
 k086=load('k086_k090',ROOT/'competition/k086/k086_factored_exponent_coherent.py')
 k087=load('k087_k090',ROOT/'competition/k087_089/k087_k089_coherent_variants.py')
 m=k086.parent()
 coeffs=m.coefficients()
 ranking,usage=rank_triples(m,coeffs)
 print('K090_RANKING',json.dumps({
  'triples_available':len(ranking),
  'top_16':[{'mask':mask,'uses':usage[mask]} for mask in ranking[:16]],
  'model_tested':m.validate_model(coeffs)},sort_keys=True),flush=True)
 a.out.mkdir(parents=True,exist_ok=True)
 results=[]
 best=None
 for count in dict.fromkeys(a.counts):
  if count<0 or count>len(ranking):raise ValueError('invalid count '+str(count))
  selected=ranking[:count]
  report={'case':f'top{count}','selected_masks':selected,
          'status':'NOT_BUILT','full_domain_verified':False}
  try:
   m.SELECTED_TRIPLES=tuple(selected)
   builder,metadata=k086.build_variant(m,'paired',transform(selected,k086,k087))
   start=time.monotonic()
   circuit=a.out/f'top{count}.kmb'
   build=builder(circuit,coeffs)
   report.update(build=build,source=metadata)
   print('K090_BUILD',json.dumps({'case':report['case'],**build},
      sort_keys=True),flush=True)
   verification=m.official(circuit,15,a.timeout,False)['prefix']
   report['prefix15']=verification
   if not passed(verification):report['status']='FAIL_PREFIX15'
   else:
    wider=m.official(circuit,a.prefix,a.timeout,False)['prefix'] if a.prefix>15 else verification
    report['prefix_wide']=wider
    if passed(wider):
     report['status']='PASS_WIDE_PREFIX_ONLY'
     if best is None or wider['score']<best['prefix_wide']['score']:
      best=report
    else:report['status']='FAIL_WIDE_PREFIX'
   report['elapsed_s']=round(time.monotonic()-start,2)
  except Exception as exc:
   report.update(status='BUILD_OR_VERIFY_ERROR',error=repr(exc))
  results.append(report)
  (a.out/(report['case']+'.json')).write_text(json.dumps(report,indent=2,default=str))
  print('K090_CASE',json.dumps({
   'case':report['case'],'status':report['status'],
   'num_qubits':report.get('build',{}).get('num_qubits'),
   'toffoli':report.get('prefix_wide',{}).get('max_toffoli_count'),
   'score_wide':report.get('prefix_wide',{}).get('score'),
   'score_delta_vs_recorded_k086_4095':(
     report.get('prefix_wide',{}).get('score')-8213841.946497097
     if report.get('prefix_wide',{}).get('score') is not None else None),
   'error':report.get('error')},sort_keys=True),flush=True)
 if best and a.full_best:
  # No accidental promotion: the official verifier must pass all seeds.
  path=a.out/(best['case']+'.kmb')
  check=m.official(path,15,a.timeout,True)
  ok=all(passed(check.get(k,{})) for k in
         ('prefix','full_seed_12345','full_seed_23456'))
  best['full_verification']=check;best['full_domain_verified']=bool(ok)
  best['status']='PASS_FULL' if ok else 'FAIL_FULL'
  (a.out/(best['case']+'.json')).write_text(json.dumps(best,indent=2,default=str))
 final={'full_domain_verified':bool(best and best['full_domain_verified']),
        'status':'SELECTIVE_TRIPLE_PREFIX_SCREEN',
        'best_case':best['case'] if best else None,
        'best_prefix_score':best.get('prefix_wide',{}).get('score') if best else None,
        'winner_full_domain_pass':bool(best and best['full_domain_verified']),
        'scoring_domain':a.prefix,'cases':results}
 (a.out/'summary.json').write_text(json.dumps(final,indent=2,default=str))
 print('K090_RESULT',json.dumps({
  'status':final['status'],'best_case':final['best_case'],
  'best_prefix_score':final['best_prefix_score'],
  'full_domain_verified':final['full_domain_verified']},sort_keys=True),flush=True)
 print('SAVED',a.out/'summary.json',flush=True)
if __name__=='__main__':run()
