#!/usr/bin/env python3
"""K086: actual K078-derived coherent invsqrt circuit with factored exponent shifts.

Combines:
 - K078 shared ANF pair predicate caching (K082-style common controls).
 - K083-motivated exponent-function factoring: e=2s or 2s+1 share s,
   so replace 22 separate exponent-controlled shifted-product XORs with
   eleven mutually exclusive parity-pair controls (no wide result encoding
   changes, no phase rotations added).
 - K084 remains a separate exact Qiskit operator audit; NO unproven RCCX
   substitution is made to Kickmix measurement-based init_and/del_and.

Official full 22-bit verification is required to promote any candidate.
Default prefix check is strictly 1..15, not full domain.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,inspect,json,random,sys,textwrap,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path)
 if sp is None or sp.loader is None:raise RuntimeError('Module not found: '+str(path))
 m=importlib.util.module_from_spec(sp);sys.modules[name]=m;sp.loader.exec_module(m);return m

def parent():
 m=load('k076_k086',ROOT/'competition/k076/k076_range_reduced_circuit.py')
 m.SEG_BITS=7;m.SEGMENTS=128;m.DEG=2;m.TB=m.FRAC-m.SEG_BITS;m.PW=m.W+m.TB
 return m

def patch_once(s,old,new):
 n=s.count(old)
 if n!=1:raise AssertionError('K076 builder contract drift: expected once, got '+str(n)+' for '+repr(old[:90]))
 return s.replace(old,new)

def build_variant(m,mode):
 src=textwrap.dedent(inspect.getsource(m.build))
 source_sha=hashlib.sha256(src.encode()).hexdigest()
 # Reproduce the exact tested K078 shared-ANF transformation.
 src=patch_once(src,
  ' # XOR coefficient lookup by algebraic normal form, with transient\n',
  ''' # Preserve K078's shared two-bit ANF controls.
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
''' + ' # XOR coefficient lookup by algebraic normal form, with transient\n')
 src=patch_once(src,
 '''   control=bits[0]
   for src in bits[1:]:
    a=and_bit(builder,control,src);chain.append((control,src,a));control=a[0]
''',
 '''   if len(bits)>=2:
    control=pair_cache[pair_of(mask)][0]
    remaining=bits[2:]
   else:
    control=bits[0]
    remaining=[]
   for src in remaining:
    a=and_bit(builder,control,src);chain.append((control,src,a));control=a[0]
''')
 src=patch_once(src,
 ''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 toggle_normalized();builder.free(q)
''',
 ''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 for mask in reversed(pair_masks):
  inds=[j for j in range(SEG_BITS+1) if mask & (1<<j)]
  unand_bit(builder,addr[inds[0]],addr[inds[1]],pair_cache[mask])
 toggle_normalized();builder.free(q)
''')
 if mode=='paired':
  src=patch_once(src,
 ''' def toggle_shifted():
  for i in range(NB):
   shift=i//2
   for k in range(shift,W):
    toggled_ccx(builder,hot[i][0],acc[-1][k],shifted[k-shift])
''',
 ''' def toggle_shifted():
  # The one-hot exponent flags are mutually exclusive for all x, including
  # x=0 (all flags zero). Pair the two exponents with identical e//2.
  # Compute/uncompute each pair using CX; one clean helper is recycled.
  for shift in range((NB+1)//2):
   control=builder.alloc_qubits(1)
   builder.cx(hot[2*shift][0],control[0])
   if 2*shift+1<NB:builder.cx(hot[2*shift+1][0],control[0])
   for k in range(shift,W):
    toggled_ccx(builder,control[0],acc[-1][k],shifted[k-shift])
   if 2*shift+1<NB:builder.cx(hot[2*shift+1][0],control[0])
   builder.cx(hot[2*shift][0],control[0])
   builder.free(control)
 stats['exponent_shift_controls']=((NB+1)//2)
''')
 else:
  src=patch_once(src,
 ' # qout = floor(acc_final/2**floor(exponent/2)).\n',
 " stats['exponent_shift_controls']=NB\n # qout = floor(acc_final/2**floor(exponent/2)).\n")
 namespace=dict(vars(m));loc={}
 exec(compile(src,'<k086 coherent integrated builder>','exec'),namespace,loc)
 return loc['build'],{'source_sha256':source_sha,
   'compiled_builder_source_sha256':hashlib.sha256(src.encode()).hexdigest(),
   'mode':mode}

def selftest():
 # Proof for all legal 22-bit exponent one-hots and zero; random x probes
 # additionally check the bit-level shifted output modulo 2^40.
 tests=0;r=random.Random(86086)
 for exp in [-1]+list(range(22)):
  flags=[int(i==exp) for i in range(22)]
  groups=[flags[2*i]^(flags[2*i+1] if 2*i+1<22 else 0) for i in range(11)]
  for _ in range(300):
   value=r.getrandbits(40)
   direct=0;paired=0
   for i in range(22):
    if flags[i]:direct^=value>>(i//2)
   for i in range(11):
    if groups[i]:paired^=value>>i
   assert direct==paired,(exp,value,direct,paired)
   tests+=1
 print('K086_SELFTEST',json.dumps({'status':'PASS','exact_onehot_or_zero_shift_cases':tests,
  'input_preservation_logic':'one-hot XOR factorization',
  'relative_phase_latch':'NOT integrated; independent K084 Qiskit proof only'}),flush=True)
 return tests

def verify_status(result):
 return result.get('status')=='PASS' and result.get('exit_code')==0

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--mode',choices=['paired','baseline'],default='paired')
 ap.add_argument('--prefix',type=int,default=15)
 ap.add_argument('--timeout',type=int,default=600)
 ap.add_argument('--full',action='store_true')
 ap.add_argument('--self-test',action='store_true')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k086/results')
 a=ap.parse_args()
 selftest()
 m=parent()
 build,metadata=build_variant(m,a.mode)
 print('K086_TRANSFORM',json.dumps(metadata,sort_keys=True),flush=True)
 if a.self_test:return
 if not 1<=a.prefix<=3133452:raise ValueError('Invalid prefix')
 table=m.coefficients();n=m.validate_model(table)
 print('K086_NUMERIC',json.dumps({'sample_inputs':n,'degree':2,'segments':128}),flush=True)
 a.out.mkdir(parents=True,exist_ok=True)
 report={'mode':a.mode,'status':'NOT_BUILT','full_domain_verified':False,
         'source':metadata,'baseline_k078':{'prefix_score':8520674.115103614,
          'max_toffoli':20642,'qubits':409,'reaction_depth':6422}}
 try:
  begin=time.monotonic()
  candidate=a.out/f'k086_{a.mode}.kmb'
  details=build(candidate,table)
  print('K086_BUILD',json.dumps(details,sort_keys=True),flush=True)
  verify=m.official(candidate,a.prefix,a.timeout,a.full)
  report.update(build=details,verification=verify,
                elapsed_s=round(time.monotonic()-begin,2))
  pref=verify.get('prefix',{})
  full_ok=a.full and all(verify_status(verify.get(k,{}))
          for k in ('prefix','full_seed_12345','full_seed_23456'))
  report['full_domain_verified']=bool(full_ok)
  report['status']='PASS_FULL' if full_ok else 'PASS_PREFIX_ONLY' if verify_status(pref) else 'FAIL_PREFIX'
  if pref.get('score') is not None:
   delta={'score':pref['score']-report['baseline_k078']['prefix_score'],
       'toffoli':pref['max_toffoli_count']-20642,
       'qubits':details['num_qubits']-409,
       'reaction_depth':pref['reaction_depth']-6422}
   report['delta_vs_recorded_k078_prefix']=delta
   print('K086_DELTA',json.dumps(delta,sort_keys=True),flush=True)
 except Exception as ex:
  report['status']='BUILD_OR_VERIFY_ERROR';report['error']=repr(ex)
  print('K086_ERROR',json.dumps({'error':repr(ex)},sort_keys=True),flush=True)
 (a.out/f'{a.mode}_report.json').write_text(json.dumps(report,indent=2,default=str))
 print('K086_RESULT',json.dumps({
  'status':report['status'],'mode':a.mode,'full_domain_verified':report['full_domain_verified'],
  'score':report.get('verification',{}).get('prefix',{}).get('score'),
  'qubits':report.get('build',{}).get('num_qubits'),
  'delta':report.get('delta_vs_recorded_k078_prefix'),
  'error':report.get('error')},sort_keys=True),flush=True)
 print('SAVED',a.out/f'{a.mode}_report.json',flush=True)

if __name__=='__main__':main()
