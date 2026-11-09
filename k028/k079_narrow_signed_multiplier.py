#!/usr/bin/env python3
"""K079: exact signed-source-width specialization of the K078 Kickmix circuit.

K077/078 multiply polynomial intermediates as 40-bit signed values even though
the first Horner multiplier's source fits 24 signed bits and the second fits 32.
K079 uses rigorous coefficient magnitude bounds (including truncation safety)
to reduce *source* bitwidth, NOT truncate low product columns. Exact low-column
carries are retained by the unchanged K034 reversible row-adder.

Keeps K078 coherent shared 2-bit ANF predicates and all other circuit logic.
Bounded prefix official verifier first; --full only after a prefix PASS.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,inspect,json,sys,textwrap,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None:raise RuntimeError('Cannot import '+str(path))
 obj=importlib.util.module_from_spec(spec)
 sys.modules[name]=obj
 spec.loader.exec_module(obj)
 return obj

def get_base():
 m=load_module('k076_for_k079',ROOT/'competition/k076/k076_range_reduced_circuit.py')
 m.SEG_BITS=7;m.SEGMENTS=128;m.DEG=2
 m.TB=m.FRAC-m.SEG_BITS;m.PW=m.W+m.TB
 return m

def replace_once(text,old,new):
 if text.count(old)!=1:
  raise RuntimeError('K076 source changed: expected exactly one '+repr(old[:85])+
                     ', found '+str(text.count(old)))
 return text.replace(old,new)

def source_bounds(m,table):
 # For a Horner source starting at coefficient j, each multiply uses
 # 0<=t<1. floor(a*t) has absolute value <=abs(a)+1.
 # Therefore sum(abs(c[k]) for k>=j)+DEG+2 is a conservative bound
 # on each intermediate. A signed width w represents [-2^(w-1),2^(w-1)-1].
 bounds={}
 for j in range(1,m.DEG+1):
  limit=max(sum(abs(table[p][s][k]) for k in range(j,m.DEG+1))
            for p in (0,1) for s in range(m.SEGMENTS))+m.DEG+2
  width=max(2,limit.bit_length()+1)
  if width>m.W:raise ValueError('Bound exceeds accumulator width')
  bounds[j]={'max_magnitude_conservative':int(limit),'signed_width':width}
 return bounds

def validate_bounds(m,table,bounds):
 # Independent exact-integer endpoint and random within-segment tests;
 # conservative arithmetic above covers all remaining t.
 import random
 rng=random.Random(79079)
 for p in (0,1):
  for s in range(m.SEGMENTS):
   c=table[p][s]
   for t in (0,(1<<m.TB)-1,1<<max(0,m.TB-1),
             rng.randrange(1<<m.TB),rng.randrange(1<<m.TB)):
    a=c[m.DEG]
    for j in range(m.DEG,0,-1):
     w=bounds[j]['signed_width']
     if not (-(1<<(w-1))<=a<(1<<(w-1))):
      raise AssertionError((p,s,j,a,w))
     a=c[j-1]+((a*t)>>m.TB)
 return {'samples':2*m.SEGMENTS*5,'bound_method':'conservative signed interval'}

def optimized_builder(m,bounds):
 src=textwrap.dedent(inspect.getsource(m.build))

 # Retain K078's proven coherent reuse of pairwise QROM address controls.
 marker=' # XOR coefficient lookup by algebraic normal form, with transient\n'
 shared=''' # Cache each pair predicate once, preserving coherent quantum controls.
 def pair_of(mask):
  lo=mask & -mask
  rem=mask ^ lo
  return lo | (rem & -rem)
 pair_masks=sorted({pair_of(mask) for coeff in anf
                    for mask,value in enumerate(coeff)
                    if value and mask.bit_count()>=2})
 pair_cache={}
 for mask in pair_masks:
  inds=[j for j in range(SEG_BITS+1) if mask & (1<<j)]
  assert len(inds)==2
  pair_cache[mask]=and_bit(builder,addr[inds[0]],addr[inds[1]])
 stats['shared_two_bit_predicates']=len(pair_masks)
'''
 src=replace_once(src,marker,shared+marker)
 old='''   control=bits[0]
   for src in bits[1:]:
    a=and_bit(builder,control,src);chain.append((control,src,a));control=a[0]
'''
 new='''   if len(bits)>=2:
    control=pair_cache[pair_of(mask)][0]
    remaining=bits[2:]
   else:
    control=bits[0]
    remaining=[]
   for src in remaining:
    a=and_bit(builder,control,src);chain.append((control,src,a));control=a[0]
'''
 src=replace_once(src,old,new)
 src=replace_once(src,
 ''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 toggle_normalized();builder.free(q)
''',
 ''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 for mask in reversed(pair_masks):
  inds=[j for j in range(SEG_BITS+1) if mask & (1<<j)]
  unand_bit(builder,addr[inds[0]],addr[inds[1]],pair_cache[mask])
 toggle_normalized();builder.free(q)
''')

 # Narrow signed source inputs, but keep PW product bits and ALL low columns.
 src=replace_once(src,
 ''' def mul(source,product,inverse):
  operations=[]
  for j in range(TB):
   operations.append((t[j],[(source[i],i+j) for i in range(W-1)],False))
   operations.append((t[j],[(source[W-1],W-1+j)],True))
''',
 ''' def mul(source,product,inverse):
  width=source_widths[id(source)]
  assert width<=W
  operations=[]
  for j in range(TB):
   operations.append((t[j],[(source[i],i+j) for i in range(width-1)],False))
   operations.append((t[j],[(source[width-1],width-1+j)],True))
''')
 src=replace_once(src,
 ''' acc=[builder.alloc_qubits(W)]
 toggle_coefficient(acc[0],DEG)
''',
 ''' # These widths are conservative mathematical bounds from source
 # coefficient rows. Addresses remain coherent and unmeasured.
 source_widths={}
 width_by_stage=SIGNED_WIDTHS
 acc=[builder.alloc_qubits(W)]
 source_widths[id(acc[0])]=width_by_stage[DEG]
 toggle_coefficient(acc[0],DEG)
''')
 src=replace_once(src,
 '''  mul(source,product,True);builder.free(product)
  return dest
''',
 '''  mul(source,product,True);builder.free(product)
  source_widths[id(dest)]=width_by_stage[j]
  return dest
''')
 src=replace_once(src,
 '''  'degree':DEG,'segments':SEGMENTS,'frac_bits':FRAC,'coeff_bits':COEF_BITS}
''',
 '''  'degree':DEG,'segments':SEGMENTS,'frac_bits':FRAC,'coeff_bits':COEF_BITS,
  'source_widths':width_by_stage}
''')

 # Compile a source-transformed function in a constrained, known local module
 # namespace; this doesn't edit any installed verifier or reference circuit.
 namespace=dict(vars(m))
 namespace['SIGNED_WIDTHS']={k:v['signed_width'] for k,v in bounds.items()}
 local={}
 exec(compile(src,'<k079 audited K076 source rewrite>','exec'),namespace,local)
 return local['build'],{
  'base_builder_sha256':hashlib.sha256(inspect.getsource(m.build).encode()).hexdigest(),
  'transformed_builder_sha256':hashlib.sha256(src.encode()).hexdigest(),
  'source_widths':namespace['SIGNED_WIDTHS']}

def multiply_math_test(m,bounds):
 # Verify all signed source widths represent exactly the same modulo-PW
 # partial product as 40-bit sign-extended arithmetic.
 import random
 rng=random.Random(790790)
 mask=(1<<m.PW)-1
 for j,info in bounds.items():
  w=info['signed_width']
  for a in [-((1<<(w-1))-1),-1,0,1,(1<<(w-1))-1]+[
      rng.randrange(-(1<<(w-1))+1,(1<<(w-1))) for _ in range(200)]:
   a_full=a&((1<<m.W)-1)
   a_narrow=a&((1<<w)-1)
   for t in (0,1,(1<<m.TB)-1,rng.randrange(1<<m.TB)):
    original=(a_full*t-(int(a_full>>(m.W-1))<<m.W)*t)&mask
    specialized=(a_narrow*t-(int(a_narrow>>(w-1))<<w)*t)&mask
    assert original==specialized==(a*t)&mask
 return 'PASS'

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--self-test',action='store_true')
 p.add_argument('--prefix',type=int,default=15)
 p.add_argument('--timeout',type=int,default=600)
 p.add_argument('--full',action='store_true')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k079/results')
 a=p.parse_args()
 m=get_base()
 table=m.coefficients()
 bounds=source_bounds(m,table)
 checks=validate_bounds(m,table,bounds)
 assert multiply_math_test(m,bounds)=='PASS'
 builder,metadata=optimized_builder(m,bounds)
 print('K079_SELFTEST',json.dumps({
  'status':'PASS','source_bounds':bounds,'validation':checks,
  'signed_multiply_modular_test':'PASS',
  **metadata},sort_keys=True),flush=True)
 if a.self_test:return
 print('K079_MODEL',json.dumps({'sample_inputs':m.validate_model(table),
                              'segments':m.SEGMENTS,'degree':m.DEG}),flush=True)
 a.out.mkdir(parents=True,exist_ok=True)
 report={'status':'NOT_BUILT','model':'K077 128-segment quadratic with K078 ANF cache',
         'source_bounds':bounds,'transform':metadata,
         'baseline_score':8520674.115103614,'baseline_toffoli':20642,
         'baseline_qubits':409,'full_domain_verified':False}
 try:
  path=a.out/'narrow_signed_source.kmb'
  print('K079_BUILD_START',flush=True)
  start=time.monotonic()
  info=builder(path,table)
  report['build']=info
  print('K079_BUILD',json.dumps(info,sort_keys=True),flush=True)
  results=m.official(path,a.prefix,a.timeout,a.full)
  report['verification']=results
  report['elapsed_s']=round(time.monotonic()-start,2)
  prefix=results.get('prefix',{})
  good=prefix.get('status')=='PASS' and prefix.get('exit_code')==0
  fullgood=good and a.full and all(
   results.get(label,{}).get('status')=='PASS' and
   results.get(label,{}).get('exit_code')==0
   for label in ('full_seed_12345','full_seed_23456'))
  report['full_domain_verified']=bool(fullgood)
  report['status']='PASS_FULL' if fullgood else 'PASS_PREFIX_ONLY' if good else 'FAIL_PREFIX'
  if prefix.get('score') is not None:
   report['score_delta']=prefix['score']-report['baseline_score']
   report['toffoli_delta']=prefix['max_toffoli_count']-report['baseline_toffoli']
   report['qubit_delta']=info['num_qubits']-report['baseline_qubits']
   print('K079_DELTA',json.dumps({k:report[k] for k in (
    'score_delta','toffoli_delta','qubit_delta')},sort_keys=True),flush=True)
 except Exception as e:
  report['status']='BUILD_ERROR';report['error']=repr(e)
  print('K079_ERROR',json.dumps({'error':repr(e)}),flush=True)
 (a.out/'report.json').write_text(json.dumps(report,indent=2,default=str))
 print('K079_RESULT',json.dumps({
  'status':report['status'],'qubits':report.get('build',{}).get('num_qubits'),
  'prefix_score':report.get('verification',{}).get('prefix',{}).get('score'),
  'max_toffoli':report.get('verification',{}).get('prefix',{}).get('max_toffoli_count'),
  'error':report.get('error'),'full_domain_verified':report['full_domain_verified']},
  sort_keys=True),flush=True)
 print('SAVED',a.out/'report.json',flush=True)

if __name__=='__main__':main()
