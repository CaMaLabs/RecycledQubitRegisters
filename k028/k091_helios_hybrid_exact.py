#!/usr/bin/env python3
"""K091: Helios-centered hybrid rewrite search. ZERO large polynomial evaluator.

Use the public, full-domain verified, third-party Helios invsqrt implementation
as the immutable reference. Transfer CaMaLabs' exact reversible compiler ideas:
  1. Involutory cancellation (X/CX/CZ/SWAP/CCX/CCZ/CSWAP), crossing strictly
     disjoint, unconditional unitary operations ONLY.
  2. K068 shared-control XOR factoring, with commuting-gate barriers.
  3. K069 small block truth-table / ANF synthesis (exhaustive equivalence).
  4. Combine the transformations, then run another cancellation pass.

DO NOT move gates over HMR/conditions/classical operations/unknown metadata.
DO NOT claim full-domain correctness from compiler cost or a prefix PASS.
Every promoted candidate must PASS BOTH official full-domain seeds.
No copying of K076/K086's 400+ qubit arithmetic, no reference mutation.
"""
from __future__ import annotations
import argparse, collections, hashlib, importlib.util, json, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/'competition/k001/private/official/verifiers'
EXPECTED_PUBLIC_SHA='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASELINE_SCORE=95369.00696815242

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None:raise RuntimeError('Missing module: '+str(path))
 obj=importlib.util.module_from_spec(spec);sys.modules[name]=obj;spec.loader.exec_module(obj)
 return obj

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def modules():
 return {
  'k063':load('k063_for_k091',ROOT/'competition/k063/k063_nonlinear_gate_cancellation.py'),
  'k068':load('k068_for_k091',ROOT/'competition/k068/k068_nonlinear_xor_factor.py'),
  'k069':load('k069_for_k091',ROOT/'competition/k069/k069_block_anf_synth.py'),
  'k031':load('k031_for_k091',ROOT/'competition/k031/k031_full_domain_repair.py')}

def simple_gate(gate):
 # Borrow existing K063 strict gate/arity parser. Preserve only unconditional,
 # unitary instructions and NO unknown syntax between cancellation endpoints.
 op,qs=gate
 if op not in {'X','CX','CZ','SWAP','CCX','CCZ','CSWAP'}:return None
 if len(set(qs))!=len(qs):return None
 if op in ('CZ','CCZ'):qs=tuple(sorted(qs))
 return op,qs

def cancel_involutions(lines,k063):
 removed_total=collections.Counter()
 # Iterative fixed point, never crosses a measurement, a condition,
 # or unknown instructions. K063.parse knows which operations are unitary.
 for round in range(10):
  parsed=[k063.decode(s) for s in lines]
  remove=set()
  for i,g in enumerate(parsed):
   if i in remove or g is None:continue
   key=simple_gate(g)
   if key is None:continue
   footprint=set(g[1])
   for j in range(i-1,-1,-1):
    if j in remove:continue
    other=parsed[j]
    if other is None:break
    if simple_gate(other)==key:
     remove.add(i);remove.add(j)
     removed_total[key[0]]+=2
     break
    if footprint.intersection(other[1]):break
  if not remove:break
  lines=[row for i,row in enumerate(lines) if i not in remove]
 return lines,dict(removed_total)

def apply(name,lines,mods,max_distance,max_qubits,max_gates):
 meta={}
 if name in ('cancel','hybrid'):
  lines,removed=cancel_involutions(lines,mods['k063'])
  meta['cancelled_before']=removed
 if name in ('xor','hybrid'):
  # The K068 change is an exact 4-qubit unitary identity, verified exhaustively.
  steps=[]
  for n in range(2):
   lines,pairs=mods['k068'].factor(lines,max_distance)
   steps+=pairs
   if not pairs:break
  meta['xor_pairs']=len(steps)
 if name in ('anf','hybrid'):
  lines,chosen,stats=mods['k069'].optimize(lines,max_qubits,max_gates)
  meta['anf_blocks']=len(chosen)
  meta['anf_ccx_saved']=sum(x['CCX_saved'] for x in chosen)
  meta['anf_scan']=stats
 if name=='hybrid':
  lines,removed=cancel_involutions(lines,mods['k063'])
  meta['cancelled_after']=removed
 return lines,meta

def opcount(lines):
 c=collections.Counter()
 for s in lines:
  if s.strip() and not s.lstrip().startswith(('#','//')):
   c[s.strip().split()[0].upper()]+=1
 return c

def expensive_delta(before,after):
 return {g:after[g]-before[g] for g in ('CCX','CCZ','CSWAP','HMR','Z_POW','CX','CZ')}

def gate_savings(before,after):
 # Only consider alternatives with fewer expensive non-Clifford resources.
 return sum(before[g]-after[g] for g in ('CCX','CCZ','CSWAP'))

def success(v):return v.get('status')=='PASS' and v.get('exit_code')==0

def official(m,path,n,timeout,full=False):
 d={'prefix':m.verify(path,n,12345,timeout)}
 if full and success(d['prefix']):
  d['full_12345']=m.verify(path,m.FULL_X,12345,timeout)
  if success(d['full_12345']):
   d['full_23456']=m.verify(path,m.FULL_X,23456,timeout)
 return d

def selftest(mods):
 # K068 and K069 already have their own exhaustive tests. Additionally
 # establish cancellation barriers for entangling/non-diagonal operations.
 test=[
  ['CX q0 q1\n','Z q7\n','CX q0 q1\n'],
  ['CCX q0 q1 q2\n','CZ q5 q6\n','CCX q0 q1 q2\n'],
  ['X q0\n','HMR q4 b0\n','X q0\n'],
  ['CX q0 q1\n','CX q2 q1\n','CX q0 q1\n'],
  ['CZ q0 q1\n','Z_POW q4 0.25\n','CZ q0 q1\n']]
 expected=[True,True,False,False,True]
 for lines,want in zip(test,expected):
  out,_=cancel_involutions(lines,mods['k063'])
  assert (len(out)<len(lines))==want,(lines,out,want)
 mods['k068'].exhaustive_test()
 mods['k069'].selftest()
 print('K091_SELFTEST PASS conservative quantum barriers, XOR factoring and ANF proofs',
       flush=True)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--source',type=Path,default=ROOT/'competition/k059/results/helios_public.kmx')
 ap.add_argument('--public-kmb',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k091/results')
 ap.add_argument('--cases',nargs='+',choices=['cancel','xor','anf','hybrid'],
                 default=['cancel','xor','anf','hybrid'])
 ap.add_argument('--max-distance',type=int,default=96)
 ap.add_argument('--max-qubits',type=int,default=6)
 ap.add_argument('--max-gates',type=int,default=60)
 ap.add_argument('--prefix',type=int,default=4095)
 ap.add_argument('--timeout',type=int,default=600)
 ap.add_argument('--full',action='store_true',help='Verify both complete official full-domain seeds for promising candidates')
 ap.add_argument('--self-test',action='store_true')
 ap.add_argument('--allow-other-source',action='store_true',
   help='Permit a different source than the SHA-pinned public Helios input for experimental inspection')
 args=ap.parse_args()
 mods=modules()
 selftest(mods)
 if args.self_test:return
 if not 64<=args.prefix<=mods['k031'].FULL_X:raise ValueError('Unsupported prefix')
 sys.path.insert(0,str(VER))
 import kickmix as km
 if not args.public_kmb.is_file() and not args.source.is_file():
  raise RuntimeError('Missing public Helios KMB and decoded KMX. Run K059 decode or extract the original K058 dataset first.')
 if args.public_kmb.is_file():
  h=digest(args.public_kmb)
  if h!=EXPECTED_PUBLIC_SHA and not args.allow_other_source:
   raise RuntimeError('Public KMB hash mismatched pinned third-party Helios: '+h)
  print('K091_PUBLIC_BASELINE',json.dumps({'kmb_sha256':h,'expected':EXPECTED_PUBLIC_SHA,
     'source_is_pinned':h==EXPECTED_PUBLIC_SHA,'reference':'third-party Helios'}),flush=True)
  # Regenerate KMX from verified KMB so there is no stale decoded stream.
  origin=km.Circuit.from_file(str(args.public_kmb),format='kmb')
  args.out.mkdir(parents=True,exist_ok=True)
  decode=args.out/'helios_immutable_decoded.kmx'
  origin.to_file(str(decode),format='kmx')
  source=decode
 else:
  if not args.allow_other_source:
   raise RuntimeError('For provenance verification, provide the original pinned KMB or explicitly --allow-other-source')
  source=args.source
 args.out.mkdir(parents=True,exist_ok=True)
 original=source.read_text().splitlines(keepends=True)
 before=opcount(original)
 print('K091_BASELINE_COUNTS',json.dumps({'source':str(source),
  'sha256':digest(source),'ops':len(original),'CCX':before['CCX'],
  'CCZ':before['CCZ'],'CSWAP':before['CSWAP'],'HMR':before['HMR']},
  sort_keys=True),flush=True)
 records=[]
 winner=None
 for name in dict.fromkeys(args.cases):
  r={'case':name,'status':'NOT_SCANNED',
     'attribution':'adaptation of third-party Helios public full-domain invsqrt reference',
     'full_domain_verified':False}
  try:
   started=time.monotonic()
   rewritten,meta=apply(name,original.copy(),mods,args.max_distance,args.max_qubits,args.max_gates)
   after=opcount(rewritten);savings=gate_savings(before,after)
   r.update(transform=meta,gate_deltas=expensive_delta(before,after),
       saved_expensive_gates=savings)
   print('K091_SCAN',json.dumps({'case':name,'saved_expensive_gates':savings,
       'gate_deltas':r['gate_deltas'],'transform':meta},sort_keys=True),flush=True)
   if savings<=0:
    r['status']='NO_EXPENSIVE_GATE_IMPROVEMENT'
   else:
    text=args.out/(name+'.kmx');text.write_text(''.join(rewritten))
    circ=km.Circuit.from_file(str(text),format='kmx')
    binary=args.out/(name+'.kmb');circ.to_file(str(binary),format='kmb')
    r.update(qubits=circ.num_qubits,binary_sha256=digest(binary))
    v=official(mods['k031'],binary,args.prefix,args.timeout,args.full)
    r['verification']=v
    if not success(v['prefix']):r['status']='FAIL_PREFIX'
    elif args.full:
     if success(v.get('full_12345',{})) and success(v.get('full_23456',{})):
      r['status']='PASS_FULL'
      r['full_domain_verified']=True
      r['score']=v['full_12345']['score']
     else:r['status']='FAIL_FULL'
    else:
     r['status']='PASS_PREFIX_ONLY'
     r['prefix_score']=v['prefix'].get('score')
    if r['full_domain_verified'] and (winner is None or r['score']<winner['score']):
     winner=r
   r['elapsed_s']=round(time.monotonic()-started,2)
  except Exception as ex:
   r['status']='ERROR';r['error']=repr(ex)
  records.append(r)
  (args.out/(name+'.json')).write_text(json.dumps(r,indent=2,default=str))
  print('K091_CASE',json.dumps({'case':name,'status':r['status'],
     'qubits':r.get('qubits'),'saved_expensive_gates':r.get('saved_expensive_gates'),
     'score':r.get('score'),'prefix_score':r.get('prefix_score'),
     'error':r.get('error')},sort_keys=True),flush=True)
 summary={'status':'HELIOS_HYBRID_ABLATION',
     'reference':'Helios third-party; retain attribution and source license',
     'baseline_full_seed_12345_score':BASELINE_SCORE,
     'baseline_full_verified_prior':True,
     'winner':{'case':winner['case'],'score':winner['score'],
       'delta_vs_helios':winner['score']-BASELINE_SCORE} if winner else None,
     'all_results':records}
 (args.out/'summary.json').write_text(json.dumps(summary,indent=2,default=str))
 print('K091_RESULT',json.dumps({'winner':summary['winner'],
    'cases':[{ 'case':x['case'],'status':x['status'],
      'saved_expensive_gates':x.get('saved_expensive_gates')}
      for x in records]},sort_keys=True),flush=True)
 print('SAVED',args.out/'summary.json',flush=True)

if __name__=='__main__':main()
