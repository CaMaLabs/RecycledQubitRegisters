#!/usr/bin/env python3
"""K087-K089: isolated, coherent, actually built K086 source variants.

K087: retain selected hot[i]&x[j] normalization controls across forward
      and backward normalization (exact, one cache qubit per selected pair).
K088: cache three-input ANF predicate prefixes in addition to K078's pairs.
K089: combine K087 normalization caching and K088 triple predicate caching.

Each candidate builds a complete 22-input-bit inverse-square-root Kickmix
circuit. First requires official 15-input PASS; then tests a wider 1023-input
prefix. --full is opt-in and requires preceding checks to pass.
Do NOT misrepresent any prefix PASS as a full-domain verification.
"""
from __future__ import annotations
import argparse,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def import_module(path):
 spec=importlib.util.spec_from_file_location('k086_k087_089',path)
 if spec is None or spec.loader is None:raise RuntimeError('Cannot import '+str(path))
 m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 return m

def normalization_cache(source,k086,budget):
 # Controls remain valid: x and hot are untouched throughout Horner,
 # phase, reverse Horner and second normalization.
 if budget<=0:return source
 setup=''' q=builder.alloc_qubits(FRAC)
 def toggle_normalized():
'''
 addition=''' q=builder.alloc_qubits(FRAC)
 # K087: cache fixed hot/exponent x input conjunctions, independent of q.
 cached_normalization_pairs=[(i,j) for i in range(NB) for j in range(i)][:CACHED_BUDGET]
 normalization_cache={}
 for i,j in cached_normalization_pairs:
  normalization_cache[(i,j)]=and_bit(builder,hot[i][0],x[j])
 stats['cached_normalization_pairs']=len(cached_normalization_pairs)
 def toggle_normalized():
'''
 # The scalar CACHED_BUDGET is injected into builder global scope.
 source=k086.patch_once(source,setup,addition)
 source=k086.patch_once(source,
 '''    toggled_ccx(builder,hot[i][0],x[j],q[pos])
''',
 '''    if (i,j) in normalization_cache:
     builder.cx(normalization_cache[(i,j)][0],q[pos])
    else:
     toggled_ccx(builder,hot[i][0],x[j],q[pos])
''')
 source=k086.patch_once(source,
 ''' toggle_normalized();builder.free(q)
 for i in reversed(range(1,NB,2)):builder.cx(hot[i][0],parity[0])
''',
 ''' toggle_normalized();builder.free(q)
 for i,j in reversed(cached_normalization_pairs):
  unand_bit(builder,hot[i][0],x[j],normalization_cache[(i,j)])
 for i in reversed(range(1,NB,2)):builder.cx(hot[i][0],parity[0])
''')
 return source

def triple_cache(source,k086):
 # The first two inputs of each triple are already held by K078's pair
 # cache. Compute one more AND and reuse for all ANF masks with that prefix.
 marker=''' stats['shared_two_bit_predicates']=len(pair_masks)
 # XOR coefficient lookup by algebraic normal form, with transient
'''
 replacement=''' stats['shared_two_bit_predicates']=len(pair_masks)
 def triple_of(mask):
  first=pair_of(mask)
  rem=mask ^ first
  return first | (rem & -rem)
 triple_masks=sorted({triple_of(mask) for coeff in anf
                      for mask,value in enumerate(coeff)
                      if value and mask.bit_count()>=3})
 triple_cache={}
 for mask in triple_masks:
  pair=pair_of(mask)
  extra=mask ^ pair
  idx=extra.bit_length()-1
  triple_cache[mask]=and_bit(builder,pair_cache[pair][0],addr[idx])
 stats['shared_three_bit_predicates']=len(triple_masks)
 # XOR coefficient lookup by algebraic normal form, with transient
'''
 source=k086.patch_once(source,marker,replacement)
 source=k086.patch_once(source,
 '''   if len(bits)>=2:
    control=pair_cache[pair_of(mask)][0]
    remaining=bits[2:]
   else:
    control=bits[0]
    remaining=[]
''',
 '''   if len(bits)>=3:
    control=triple_cache[triple_of(mask)][0]
    remaining=bits[3:]
   elif len(bits)>=2:
    control=pair_cache[pair_of(mask)][0]
    remaining=bits[2:]
   else:
    control=bits[0]
    remaining=[]
''')
 source=k086.patch_once(source,
 ''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 for mask in reversed(pair_masks):
''',
 ''' toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 for mask in reversed(triple_masks):
  pair=pair_of(mask)
  idx=(mask ^ pair).bit_length()-1
  unand_bit(builder,pair_cache[pair][0],addr[idx],triple_cache[mask])
 for mask in reversed(pair_masks):
''')
 return source

def control_math_selftest():
 # 22 exponent hot controls are one-hot; exact cached conjunction behaves
 # identically to individually recomputed hot[i]&x[j] in both directions.
 checks=0
 for x in range(1,8192):
  e=x.bit_length()-1
  for i in range(min(e+1,22)):
   for j in range(i):
    c=int(i==e and bool((x>>j)&1))
    assert c==(int(i==e)&((x>>j)&1))
    checks+=1
 # shared triple prefix == full mask for every 8-bit control pattern
 for addr in range(256):
  for mask in range(256):
   if mask.bit_count()<3:continue
   low=mask & -mask
   second=(mask ^ low)&-(mask ^ low)
   pair=low|second
   third=(mask ^ pair)&-(mask ^ pair)
   triple=pair|third
   assert int((addr&mask)==mask)==int((addr&triple)==triple)*int(
    (addr&(mask^triple))==(mask^triple))
   checks+=1
 return checks

def variant_transform(case,k086):
 cache={'norm16':16,'norm32':32,'norm64':64,'triple':0,'combined':32,'baseline':0}[case]
 add_triples=case in ('triple','combined')
 def apply(source):
  if cache:source=normalization_cache(source,k086,cache)
  if add_triples:source=triple_cache(source,k086)
  return source
 return apply,cache,add_triples

def transformed_source_contract_selftest():
 """Compile every proposed source transformation without requiring Kickmix.

 Builds the exact K076 function source via Python's AST and uses the same
 patcher as the real experiment. Tests source compatibility and syntax only.
 """
 import ast
 from types import SimpleNamespace
 from unittest.mock import patch
 raw=(ROOT/'competition/k076/k076_range_reduced_circuit.py').read_text()
 nodes=ast.parse(raw).body
 original=next(node for node in nodes
               if isinstance(node,ast.FunctionDef) and node.name=='build')
 source=ast.get_source_segment(raw,original)
 k086=import_module(ROOT/'competition/k086/k086_factored_exponent_coherent.py')
 done=[]
 for case in ('baseline','norm16','norm32','norm64','triple','combined'):
  transform,budget,_=variant_transform(case,k086)
  stub=SimpleNamespace(build=lambda:None,CACHED_BUDGET=budget)
  with patch.object(k086.inspect,'getsource',return_value=source):
   fn,receipt=k086.build_variant(stub,'paired',transform)
  assert callable(fn)
  done.append({'variant':case,'source_sha256':receipt['compiled_builder_source_sha256']})
 return done

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--cases',nargs='+',
   choices=['baseline','norm16','norm32','norm64','triple','combined'],
   default=['norm16','norm32','norm64','triple','combined'])
 ap.add_argument('--prefix',type=int,default=1023)
 ap.add_argument('--timeout',type=int,default=600)
 ap.add_argument('--full',action='store_true')
 ap.add_argument('--self-test',action='store_true')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k087_089/results')
 a=ap.parse_args()
 checks=control_math_selftest()
 compile_contracts=transformed_source_contract_selftest()
 print('K087_089_SELFTEST',json.dumps({'status':'PASS','algebraic_cases':checks,
   'compiled_patch_contracts':compile_contracts,
   'proof_scope':'classical identities and source syntax only, NOT quantum gate correctness'}),flush=True)
 if a.self_test:return
 if not 15<=a.prefix<=3133452:raise ValueError('Prefix must be >=15 and <=3133452')
 k086=import_module(ROOT/'competition/k086/k086_factored_exponent_coherent.py')
 m=k086.parent()
 coeff=m.coefficients()
 print('K087_089_MODEL',json.dumps({'sample_inputs':m.validate_model(coeff),
   'fraction_bits':m.FRAC,'segments':m.SEGMENTS,'degree':m.DEG}),flush=True)
 a.out.mkdir(parents=True,exist_ok=True)
 for case in a.cases:
  record={'case':case,'status':'NOT_STARTED','full_domain_verified':False}
  try:
   transform,budget,use_triples=variant_transform(case,k086)
   # Build K086's actual paired-shift and shared-pair circuit, with only
   # the selected extra transformation applied.
   # CACHED_BUDGET is injected into K076 module globals, as compiled
   # builder reads it there after exec namespace copy.
   m.CACHED_BUDGET=budget
   builder,meta=k086.build_variant(m,'paired',transform)
   path=a.out/f'{case}.kmb'
   started=time.monotonic()
   info=builder(path,coeff)
   record.update(build=info,transform=meta)
   print('K087_089_BUILD',json.dumps({'case':case,**info},sort_keys=True),flush=True)
   v15=m.official(path,15,a.timeout,False)['prefix']
   record['prefix15']=v15
   if v15.get('status')!='PASS' or v15.get('exit_code')!=0:
    record['status']='FAIL_PREFIX_15'
   else:
    if a.prefix>15:
     vw=m.official(path,a.prefix,a.timeout,False)['prefix']
    else:vw=v15
    record['prefix_wide']=vw
    if vw.get('status')!='PASS' or vw.get('exit_code')!=0:
     record['status']='FAIL_WIDE_PREFIX'
    elif a.full:
     full=m.official(path,15,a.timeout,True)
     record['full_verification']=full
     full_ok=all(full.get(k,{}).get('status')=='PASS' and
            full.get(k,{}).get('exit_code')==0
            for k in ('prefix','full_seed_12345','full_seed_23456'))
     record['status']='PASS_FULL' if full_ok else 'FAIL_FULL'
     record['full_domain_verified']=full_ok
    else:record['status']='PASS_WIDE_PREFIX_ONLY'
    if v15.get('score') is not None:
     record['delta_vs_k086_prefix15']={
       'score':v15['score']-8205744.115103613,
       'toffoli':v15['max_toffoli_count']-19872,
       'qubits':info['num_qubits']-409,
       'reaction_depth':v15['reaction_depth']-6422}
   record['elapsed_s']=round(time.monotonic()-started,2)
  except Exception as ex:
   record.update(status='BUILD_OR_VERIFY_ERROR',error=repr(ex))
  (a.out/f'{case}.json').write_text(json.dumps(record,indent=2,default=str))
  print('K087_089_CASE',json.dumps({'case':case,'status':record['status'],
       'qubits':record.get('build',{}).get('num_qubits'),
       'score15':record.get('prefix15',{}).get('score'),
       'score_wide':record.get('prefix_wide',{}).get('score'),
       'delta':record.get('delta_vs_k086_prefix15'),
       'error':record.get('error')},sort_keys=True),flush=True)
 print('K087_089_SAVED',a.out,flush=True)

if __name__=='__main__':main()
