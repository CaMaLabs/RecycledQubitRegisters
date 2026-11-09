#!/usr/bin/env python3
"""K078: cache coherent two-bit ANF predicates across ALL K077 coefficient loads.

Uses the exact K076 circuit builder and K077 128-segment quadratic model.
Only transformation: compute each required two-bit address AND once, share it
across all coefficient lookups/loads/unloads, then uncompute at the end.
All higher-degree AND chains remain individually reversible.
No changes to arithmetic, phase encoding, input normalization, or verifier.

This is an A/B experiment and NOT a full-domain validated candidate.
"""
from __future__ import annotations
import argparse,hashlib,inspect,json,sys,textwrap,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load():
 import importlib.util
 p=ROOT/'competition/k076/k076_range_reduced_circuit.py'
 if not p.is_file():raise SystemExit('Missing '+str(p))
 s=importlib.util.spec_from_file_location('k076_k078',p)
 m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
 m.SEG_BITS=7;m.SEGMENTS=128;m.DEG=2
 m.TB=m.FRAC-m.SEG_BITS;m.PW=m.W+m.TB
 return m
def replace_once(src,old,new):
 n=src.count(old)
 if n!=1:raise RuntimeError('Source contract drift: expected one, found '+str(n)+' for '+repr(old[:90]))
 return src.replace(old,new)
def optimized_build(m):
 src=textwrap.dedent(inspect.getsource(m.build))
 marker=' # XOR coefficient lookup by algebraic normal form, with transient\n'
 shared=''' # Shared low-pair predicates of the 8-bit coefficient address.
 # Each is computed once, is coherent (not measured), and stays live
 # until the final coefficient unload. Compute only pairs actually used.
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
 stats["shared_two_bit_predicates"]=len(pair_masks)
'''
 src=replace_once(src,marker,shared+marker)
 old='''   control=bits[0]
   for src in bits[1:]:
    a=and_bit(builder,control,src);chain.append((control,src,a));control=a[0]
'''
 new='''   if len(bits)>=2:
    key=pair_of(mask)
    control=pair_cache[key][0]
    remaining=bits[2:]
   else:
    control=bits[0]
    remaining=[]
   for src in remaining:
    a=and_bit(builder,control,src);chain.append((control,src,a));control=a[0]
'''
 src=replace_once(src,old,new)
 cleanup_old=''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 toggle_normalized();builder.free(q)
'''
 cleanup_new=''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 for mask in reversed(pair_masks):
  inds=[j for j in range(SEG_BITS+1) if mask & (1<<j)]
  unand_bit(builder,addr[inds[0]],addr[inds[1]],pair_cache[mask])
 toggle_normalized();builder.free(q)
'''
 src=replace_once(src,cleanup_old,cleanup_new)
 ns={}
 exec(compile(src,'<k078 patched k076 build>','exec'),vars(m),ns)
 return ns['build'],{'shared_predicate_source_sha256':hashlib.sha256(src.encode()).hexdigest(),
                     'original_builder_sha256':hashlib.sha256(inspect.getsource(m.build).encode()).hexdigest()}
def test_source(m):
 f,meta=optimized_build(m)
 t=m.coefficients()
 a=m.anf_words(t)
 def pair_of(v):
  lo=v & -v
  return lo | ((v^lo) & -(v^lo))
 pairs={pair_of(mask) for coeff in a for mask,word in enumerate(coeff)
        if word and mask.bit_count()>=2}
 assert all(p.bit_count()==2 for p in pairs)
 assert len(pairs)<=28
 # Algebraic identity: product of the same two controls can replace
 # the first two terms of each AND chain for arbitrary binary address.
 for x in range(256):
  for mask in range(256):
   if mask.bit_count()<2:continue
   p=pair_of(mask)
   direct=int((x&mask)==mask)
   cached=int((x&p)==p)
   rest=int((x&(mask^p))==(mask^p))
   assert direct==cached*rest
 print('K078_SELFTEST PASS source patch, 65,536 coherent Boolean identities',
       json.dumps({'cached_pairs':len(pairs),**meta},sort_keys=True),flush=True)
 return f,meta,len(pairs)
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--self-test',action='store_true')
 p.add_argument('--prefix',type=int,default=15)
 p.add_argument('--timeout',type=int,default=600)
 p.add_argument('--full',action='store_true')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k078/results')
 a=p.parse_args()
 m=load()
 builder,metadata,pairs=test_source(m)
 if a.self_test:return
 table=m.coefficients()
 print('K078_MODEL',json.dumps({'samples':m.validate_model(table),'segments':128,
     'degree':2,'shared_pairs':pairs}),flush=True)
 a.out.mkdir(parents=True,exist_ok=True)
 report={'status':'NOT_BUILT','shared_pairs':pairs,'metadata':metadata,
   'baseline_k077_prefix_score':8867753.681795787,
   'baseline_k077_max_toffoli':23084,
   'baseline_k077_qubits':381,'official_full_domain':False}
 path=a.out/'shared_pair_candidate.kmb'
 try:
  start=time.monotonic()
  info=builder(path,table)
  print('K078_BUILD',json.dumps(info,sort_keys=True),flush=True)
  results=m.official(path,a.prefix,a.timeout,a.full)
  report['build']=info;report['verification']=results
  report['elapsed_s']=round(time.monotonic()-start,2)
  prefix=results.get('prefix',{})
  valid=prefix.get('status')=='PASS' and prefix.get('exit_code')==0
  if a.full:valid=valid and all(
    results.get(k,{}).get('status')=='PASS' and
    results.get(k,{}).get('exit_code')==0 for k in ('full_seed_12345','full_seed_23456'))
  report['status']=('PASS_FULL' if a.full else 'PASS_PREFIX_ONLY') if valid else 'FAIL'
  report['official_full_domain']=bool(valid and a.full)
  if prefix.get('score') is not None:
   report['score_delta_vs_k077_prefix']=prefix['score']-report['baseline_k077_prefix_score']
   report['toffoli_delta_vs_k077']=prefix.get('max_toffoli_count',0)-23084
   print('K078_DELTA',json.dumps({
     'score_delta':report['score_delta_vs_k077_prefix'],
     'max_toffoli_delta':report['toffoli_delta_vs_k077'],
     'qubit_delta':info['num_qubits']-381},sort_keys=True),flush=True)
 except Exception as ex:
  report['status']='BUILD_OR_VERIFY_ERROR';report['error']=repr(ex)
  print('K078_ERROR',json.dumps({'error':repr(ex)}),flush=True)
 (a.out/'report.json').write_text(json.dumps(report,indent=2,default=str))
 print('K078_RESULT',json.dumps({'status':report['status'],
   'prefix_score':report.get('verification',{}).get('prefix',{}).get('score'),
   'qubits':report.get('build',{}).get('num_qubits'),
   'delta':report.get('score_delta_vs_k077_prefix'),'error':report.get('error'),
   'full_domain_verified':report['official_full_domain']},sort_keys=True),flush=True)
 print('SAVED',a.out/'report.json',flush=True)
if __name__=='__main__':main()
