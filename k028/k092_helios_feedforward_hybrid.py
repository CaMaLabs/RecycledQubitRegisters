#!/usr/bin/env python3
"""K092 Helios-preserving measurement-aware optimizer and targeted cost audit.

Four distinct interventions:
 - exact disjoint-gate cancellation (K091, tests previously skipped 88 CX)
 - conservative affine classical feed-forward constant propagation (K067)
 - in-block Z/CZ parity folding (K062)
 - combined classical -> phase -> unitary cancellation

Original third-party Helios KMB is immutable and SHA-pinned. Any candidate
must compile, pass official prefix, then BOTH full-domain seeds before
claiming a new verified score. No K076 polynomial arithmetic is introduced.

K064 and K060 inspections are read-only and report measurement-heavy hotspots.
This is an engineering experiment, not an assertion of performance improvement.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SHA='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASE=95369.00696815242
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path)
 if s is None or s.loader is None:raise FileNotFoundError(path)
 m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def count(lines):
 c=collections.Counter()
 for x in lines:
  s=x.strip()
  if s and not s.startswith(('#','//')):c[s.split()[0].upper()]+=1
 return c
def good(v):return v.get('status')=='PASS' and v.get('exit_code')==0
def mods():
 return {
  'k091':load('k091_k092',ROOT/'competition/k091/k091_helios_hybrid_exact.py'),
  'k063':load('k063_k092',ROOT/'competition/k063/k063_nonlinear_gate_cancellation.py'),
  'k062':load('k062_k092',ROOT/'competition/k062/k062_classical_parity_fold.py'),
  'k067':load('k067_k092',ROOT/'competition/k067/k067_coherence_aware_classical_compiler.py'),
  'k031':load('k031_k092',ROOT/'competition/k031/k031_full_domain_repair.py'),
  'k064':load('k064_k092',ROOT/'competition/k064/k064_nonlinear_block_atlas.py'),
  'k060':load('k060_k092',ROOT/'competition/k060/k060_measurement_feedforward_trace.py')}
def rewrite(name,source,m):
 out=source.copy()
 detail={}
 if name in ('classical','combined'):
  out,info=m['k067'].transform(out);detail['classical']=info
 if name in ('phase','combined'):
  # Keep original phase folding limited to truly contiguous diagonal blocks.
  # Conditional control scopes and classical writes remain hard barriers.
  out,info=m['k062'].transform(out)
  # K062 emits synthesized instructions without newline terminators.
  # Normalize every entry before the next pass or joining the KMX stream.
  out=[line.rstrip('\r\n')+'\n' for line in out]
  detail['phase']=info
 if name in ('cancel','combined'):
  out,info=m['k091'].cancel_involutions(out,m['k063'])
  detail['cancel']=info
 return out,detail
def audit(original,m):
 # Read-only source-level evidence for the next measurable subroutine.
 entries=m['k064'].load_from_memory if hasattr(m['k064'],'load_from_memory') else None
 # A standalone KMX filename is available, use K064's proven parser instead.
 return {}
def selftest(m):
 m['k067'].selftest()
 m['k091'].selftest({
  'k063':m['k063'],
  'k068':load('k068_k092',ROOT/'competition/k068/k068_nonlinear_xor_factor.py'),
  'k069':load('k069_k092',ROOT/'competition/k069/k069_block_anf_synth.py')})
 # Classical prefix propagation and phase fold preserve textual hard barriers.
 for sample in (['HMR q0 b0\n','CZ q1 q2 if b0\n'],
                ['BIT_STORE0 b0\n','HMR q0 b0\n','Z q1 if b0\n']):
  result,_=m['k067'].transform(sample)
  assert result==sample
 out,info=m['k062'].transform(['CZ q0 q1\n','CZ q1 q0\n','HMR q2 b0\n'])
 assert out==['HMR q2 b0\n'] and info['phase_gates_removed']==2
 for name in ('phase','combined'):
  inp=['CZ q0 q1 if b0\n','CZ q0 q1 if b1\n','HMR q2 b2\n']
  patched,_=rewrite(name,inp,m)
  assert all(x.endswith('\n') and x.count('\n')==1 for x in patched)
  assert any(x.startswith('BIT_STORE0') for x in patched)
 print('K092_SELFTEST PASS: conservative barriers and local rewrite contracts',flush=True)
def verification(m,path,prefix,timeout,full):
 out={'prefix':m['k031'].verify(path,prefix,12345,timeout)}
 if full and good(out['prefix']):
  out['full_12345']=m['k031'].verify(path,m['k031'].FULL_X,12345,timeout)
  if good(out['full_12345']):
   out['full_23456']=m['k031'].verify(path,m['k031'].FULL_X,23456,timeout)
 return out
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--base',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k092/results')
 ap.add_argument('--cases',nargs='+',choices=['cancel','classical','phase','combined'],
   default=['cancel','classical','phase','combined'])
 ap.add_argument('--prefix',type=int,default=4095)
 ap.add_argument('--timeout',type=int,default=1200)
 ap.add_argument('--full',action='store_true')
 ap.add_argument('--self-test',action='store_true')
 a=ap.parse_args()
 m=mods();selftest(m)
 if a.self_test:return
 if a.prefix<64 or a.prefix>m['k031'].FULL_X:raise ValueError('Invalid prefix')
 h=digest(a.base)
 if h!=SHA:raise RuntimeError('Refusing to transform an unpinned Helios KMB: '+h)
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 a.out.mkdir(parents=True,exist_ok=True)
 orig=km.Circuit.from_file(str(a.base),format='kmb')
 public=a.out/'public_helios_readonly.kmx';orig.to_file(str(public),format='kmx')
 lines=public.read_text().splitlines(keepends=True)
 before=count(lines)
 print('K092_BASE',json.dumps({'sha256':h,'qubits':orig.num_qubits,
       'CCX':before['CCX'],'CCZ':before['CCZ'],'CSWAP':before['CSWAP'],
       'CX':before['CX'],'CZ':before['CZ'],'HMR':before['HMR']},sort_keys=True),flush=True)
 # Independent hotspot diagnostics; never use heuristics to change source.
 try:
  atlas=m['k064'].investigate(m['k064'].load(public),600,80,8,24)
  trace=m['k060'].inspect(public,2,3,16)
  diagnostic={'expensive_windows':[
   {k:w[k] for k in ('start_line','end_line','score','CCX','CCZ','CSWAP','HMR')}
     for w in atlas['expensive_windows']],
   'condition_scope_lengths':trace['condition_scope_lengths'],
   'condition_scopes_total':trace['condition_scopes_total'],
   'hotspot_note':'Read-only characterization; no assumption that blocks are independently substitutable'}
  (a.out/'hotspots.json').write_text(json.dumps(diagnostic,indent=2))
  print('K092_HOTSPOTS',json.dumps(diagnostic,sort_keys=True),flush=True)
 except Exception as exc:
  print('K092_HOTSPOT_ERROR',repr(exc),flush=True)
 results=[];winner=None
 for name in dict.fromkeys(a.cases):
  r={'case':name,'status':'NOT_RUN','full_domain_verified':False}
  try:
   start=time.monotonic()
   rewritten,detail=rewrite(name,lines,m)
   after=count(rewritten)
   delta={g:after[g]-before[g] for g in ('CCX','CCZ','CSWAP','CX','CZ','HMR','Z_POW')}
   r.update(methods=detail,op_delta=delta)
   print('K092_SCAN',json.dumps({'case':name,'delta':delta,'details':detail},
       sort_keys=True),flush=True)
   if rewritten==lines:
    r['status']='NO_CHANGE'
   else:
    text=a.out/(name+'.kmx');text.write_text(''.join(rewritten))
    candidate=km.Circuit.from_file(str(text),format='kmx')
    binary=a.out/(name+'.kmb')
    candidate.to_file(str(binary),format='kmb')
    r.update(candidate_sha256=digest(binary),qubits=candidate.num_qubits)
    v=verification(m,binary,a.prefix,a.timeout,a.full);r['verification']=v
    if not good(v['prefix']):r['status']='FAIL_PREFIX'
    elif a.full:
     if good(v.get('full_12345',{})) and good(v.get('full_23456',{})):
      r['full_domain_verified']=True
      r['status']='PASS_FULL'
      r['score']=v['full_12345'].get('score')
      r['delta_vs_helios']=r['score']-BASE
      if winner is None or r['score']<winner['score']:winner=r
     else:r['status']='FAIL_FULL'
    else:
     r['status']='PASS_PREFIX_ONLY'
     r['prefix_score']=v['prefix'].get('score')
   r['elapsed_s']=round(time.monotonic()-start,3)
  except Exception as exc:
   r.update(status='ERROR',error=repr(exc))
  results.append(r)
  (a.out/(name+'.json')).write_text(json.dumps(r,indent=2,default=str))
  print('K092_CASE',json.dumps({
    'case':name,'status':r['status'],'qubits':r.get('qubits'),
    'op_delta':r.get('op_delta'),'score':r.get('score'),
    'prefix_score':r.get('prefix_score'),'error':r.get('error')},
    sort_keys=True),flush=True)
 summary={'status':'HELIOS_HYBRID_EXTENDED',
  'source_sha256':h,'attribution':'third-party Helios benchmark; adaptations are experiments',
  'original_score_full_seed_12345':BASE,
  'full_domain_winner':{'case':winner['case'],'score':winner['score'],
       'delta_vs_helios':winner['delta_vs_helios']} if winner else None,
  'cases':results}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2))
 print('K092_RESULT',json.dumps({
   'full_domain_winner':summary['full_domain_winner'],
   'cases':[{ 'case':r['case'],'status':r['status']} for r in results]},
   sort_keys=True),flush=True)
 print('SAVED',a.out/'summary.json',flush=True)
if __name__=='__main__':main()
