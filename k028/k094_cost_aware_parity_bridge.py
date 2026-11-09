#!/usr/bin/env python3
"""K094: cost-aware affine-bridge factoring, exact Helios 62-qubit baseline.

Use original Helios or K093's exact CSWAP->CX/CCX/CX encoding.
Bridge identity (all four wires distinct):
  CCX(a,b,t); CX(b,c); CCX(a,c,t) == CCX(a,c,t); CX(b,c)
  CCX(a,c,t); CX(b,c); CCX(a,b,t) == CX(b,c); CCX(a,c,t)
All intervening gates must be unconditional known unitaries disjoint from
(a,b,c,t). Never cross measurements, classical writes, scope changes or
unknown operations. Optional K069 ANF synthesis and K091 involution cleanup.
Only report official scoring improvement after two full-domain PASS seeds.
Public third-party Helios circuit is kept immutable and attributed.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SHA='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASE=95369.00696815242
Q=re.compile(r'\bq(\d+)\b')
CSWAP=re.compile(r'^CSWAP\s+q(\d+)\s+q(\d+)\s+q(\d+)\s*$',re.I)
ARITY={'X':1,'Y':1,'Z':1,'H':1,'S':1,'S_DAG':1,'T':1,'T_DAG':1,
'Z_POW':1,'CX':2,'CZ':2,'SWAP':2,'CCX':3,'CCZ':3,'CSWAP':3}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p)
 if s is None or s.loader is None:raise FileNotFoundError(p)
 m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def parse(s):
 t=s.strip()
 if not t or ' if ' in t or t.startswith(('#','//')):return None
 op=t.split()[0].upper()
 if op not in ARITY:return None
 qs=tuple(map(int,Q.findall(t)))
 if len(qs)!=ARITY[op] or len(set(qs))!=len(qs):return None
 return op,qs
def relation(first,last,middle):
 if not(first and last and middle) or (first[0],middle[0],last[0])!=('CCX','CX','CCX'):return None
 a,b,t=first[1];x,y,u=last[1];src,dst=middle[1]
 if t!=u or t in (src,dst):return None
 shared=set((a,b))&set((x,y))
 if len(shared)!=1:return None
 common=next(iter(shared))
 if len({common,src,dst,t})!=4:return None
 e1=next(iter(set((a,b))-{common}))
 e2=next(iter(set((x,y))-{common}))
 if e1==src and e2==dst:return 'before',(common,dst,t)
 if e1==dst and e2==src:return 'after',(common,dst,t)
 return None
def bridge(lines,distance):
 parsed=[parse(s) for s in lines]
 for i,g in enumerate(parsed):
  if g is None or g[0]!='CCX':continue
  for j in range(i+1,min(len(lines),i+distance+1)):
   mid=parsed[j]
   if mid is None:break
   if mid[0]!='CX':
    if set(mid[1])&set(g[1]):break
    continue
   for k in range(j+1,min(len(lines),i+distance+1)):
    last=parsed[k]
    if last is None:break
    r=relation(g,last,mid)
    if r:
     mode,params=r;footprint=set(params)|{mid[1][0]}
     if all(parsed[z] is not None and not footprint.intersection(parsed[z][1])
            for z in range(i+1,k) if z!=j):
      return i,j,k,mode,params
    if set(last[1])&set(g[1]):break
 return None
def optimize(lines,distance,limit):
 events=[]
 for _ in range(limit):
  candidate=bridge(lines,distance)
  if candidate is None:break
  i,j,k,mode,(common,dst,t)=candidate
  new=f'CCX q{common} q{dst} q{t}\n'
  if mode=='before':
   lines[i]=new;del lines[k]
  else:
   del lines[i];lines[k-1]=new
  events.append({'start':i+1,'cx':j+1,'end':k+1,'mode':mode,'replacement':[common,dst,t]})
 return lines,events
def expand_swaps(lines,scope,orientation):
 out=[];n=0
 for i,s in enumerate(lines):
  m=CSWAP.fullmatch(s.strip())
  if m and (scope=='all' or 25200<=i<26400):
   c,a,b=map(int,m.groups())
   if orientation:a,b=b,a
   out.extend((f'CX q{a} q{b}\n',f'CCX q{c} q{b} q{a}\n',
               f'CX q{a} q{b}\n'))
   n+=1
  else:out.append(s)
 return out,n
def count(lines):
 c=collections.Counter()
 for s in lines:
  t=s.strip()
  if t and not t.startswith(('#','//')):c[t.split()[0].upper()]+=1
 return c
def evaluate(gates,value):
 for op,qs in gates:
  if op=='CCX':
   a,b,t=qs;value^=(((value>>a)&1)&((value>>b)&1))<<t
  elif op=='CX':
   a,t=qs;value^=((value>>a)&1)<<t
 return value
def selftest():
 for mode in ('before','after'):
  a=('CCX',(0,1 if mode=='before' else 2,3))
  b=('CX',(1,2))
  c=('CCX',(0,2 if mode=='before' else 1,3))
  assert relation(a,c,b)==(mode,(0,2,3))
  old=[a,b,c]
  new=[('CCX',(0,2,3)),b] if mode=='before' else [b,('CCX',(0,2,3))]
  assert all(evaluate(old,x)==evaluate(new,x) for x in range(16))
  src=[f'CCX q0 q{a[1][1]} q3\n','Z q7\n','CX q1 q2\n',
       'X q8\n',f'CCX q0 q{c[1][1]} q3\n']
  assert bridge(src,20) is not None
  for barrier in ('HMR q9 b0\n','CX q0 q7\n','CZ q3 q7\n'):
   altered=list(src);altered[1]=barrier
   assert bridge(altered,20) is None
 assert relation(('CCX',(0,1,3)),('CCX',(0,1,3)),('CX',(1,2))) is None
 print('K094_SELFTEST PASS exhaustive affine identities and control/measurement barriers',flush=True)
def good(x):return x.get('status')=='PASS' and x.get('exit_code')==0
def official(m,p,n,timeout,full):
 r={'prefix':m.verify(p,n,12345,timeout)}
 if full and good(r['prefix']):
  r['full_12345']=m.verify(p,m.FULL_X,12345,timeout)
  if good(r['full_12345']):r['full_23456']=m.verify(p,m.FULL_X,23456,timeout)
 return r
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--base',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k094/results')
 p.add_argument('--variants',nargs='+',choices=['original','all_o0','all_o1','phase_o0','phase_o1'],
  default=['original','all_o0','all_o1','phase_o0','phase_o1'])
 p.add_argument('--distance',type=int,default=96)
 p.add_argument('--max-rewrites',type=int,default=600)
 p.add_argument('--anf',action='store_true')
 p.add_argument('--anf-qubits',type=int,default=8)
 p.add_argument('--anf-gates',type=int,default=100)
 p.add_argument('--cancel',action='store_true')
 p.add_argument('--prefix',type=int,default=4095)
 p.add_argument('--timeout',type=int,default=1200)
 p.add_argument('--full',action='store_true')
 p.add_argument('--self-test',action='store_true')
 a=p.parse_args()
 selftest()
 if a.self_test:return
 if sha(a.base)!=SHA:raise RuntimeError('Pinned Helios reference SHA mismatch')
 ver=load('k031_k094',ROOT/'competition/k031/k031_full_domain_repair.py')
 if a.anf:anf=load('k069_k094',ROOT/'competition/k069/k069_block_anf_synth.py')
 if a.cancel:
  cancel=load('k091_k094',ROOT/'competition/k091/k091_helios_hybrid_exact.py')
  k063=load('k063_k094',ROOT/'competition/k063/k063_nonlinear_gate_cancellation.py')
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 a.out.mkdir(parents=True,exist_ok=True)
 baseline=km.Circuit.from_file(str(a.base),format='kmb')
 text=a.out/'immutable_helios.kmx';baseline.to_file(str(text),format='kmx')
 lines=text.read_text().splitlines(keepends=True)
 prior=count(lines);original_nl=prior['CCX']+prior['CCZ']+prior['CSWAP']
 print('K094_BASE',json.dumps({'qubits':baseline.num_qubits,'CCX':prior['CCX'],
   'CCZ':prior['CCZ'],'CSWAP':prior['CSWAP'],'nonlinear_units':original_nl},sort_keys=True),flush=True)
 records=[];best=None
 for name in a.variants:
  r={'variant':name,'status':'NOT_RUN','full_domain_verified':False}
  try:
   start=time.monotonic();expanded=0
   if name=='original':src=list(lines)
   else:
    scope='phase' if name.startswith('phase') else 'all'
    orient=1 if name.endswith('o1') else 0
    src,expanded=expand_swaps(lines,scope,orient)
   candidate,events=optimize(src,a.distance,a.max_rewrites)
   r.update(expanded_cswaps=expanded,bridge_rewrites=len(events),
    bridge_examples=events[:20])
   if a.anf:
    candidate,blocks,scan=anf.optimize(candidate,a.anf_qubits,a.anf_gates)
    r.update(anf_blocks=len(blocks),
             anf_ccx_saved=sum(x['CCX_saved'] for x in blocks),anf_scan=scan)
   if a.cancel:
    candidate,removed=cancel.cancel_involutions(candidate,k063)
    r['cancelled']=removed
   after=count(candidate)
   r['delta']={op:after[op]-prior[op] for op in
      ('CCX','CCZ','CSWAP','CX','CZ','HMR','Z_POW')}
   r['nonlinear_saved']=original_nl-(after['CCX']+after['CCZ']+after['CSWAP'])
   print('K094_SCAN',json.dumps({'variant':name,'expanded_cswaps':expanded,
    'bridge_rewrites':len(events),'nonlinear_saved':r['nonlinear_saved'],
    'deltas':r['delta'],'anf_blocks':r.get('anf_blocks')},sort_keys=True),flush=True)
   if r['nonlinear_saved']<=0:r['status']='NO_NONLINEAR_SAVINGS'
   else:
    kmx=a.out/(name+'.kmx');kmx.write_text(''.join(candidate))
    circ=km.Circuit.from_file(str(kmx),format='kmx')
    binary=a.out/(name+'.kmb');circ.to_file(str(binary),format='kmb')
    r.update(qubits=circ.num_qubits,candidate_sha=sha(binary))
    v=official(ver,binary,a.prefix,a.timeout,a.full)
    r['official']=v
    if not good(v['prefix']):r['status']='FAIL_PREFIX'
    elif a.full and good(v.get('full_12345',{})) and good(v.get('full_23456',{})):
     r.update(status='PASS_FULL',full_domain_verified=True,
              score=v['full_12345']['score'])
     r['score_delta']=r['score']-BASE
     if best is None or r['score']<best['score']:best=r
    elif a.full:r['status']='FAIL_FULL'
    else:r.update(status='PASS_PREFIX_ONLY',prefix_score=v['prefix'].get('score'))
   r['elapsed_s']=round(time.monotonic()-start,2)
  except Exception as exc:r.update(status='ERROR',error=repr(exc))
  records.append(r)
  (a.out/(name+'.json')).write_text(json.dumps(r,indent=2,default=str))
  print('K094_CASE',json.dumps({'variant':name,'status':r['status'],
    'nonlinear_saved':r.get('nonlinear_saved'),
    'bridge_rewrites':r.get('bridge_rewrites'),
    'score':r.get('score'),'qubits':r.get('qubits'),
    'error':r.get('error')},sort_keys=True),flush=True)
 summary={'source':'Helios third-party verified reference; CaMaLabs experimental adaptation',
  'baseline_score':BASE,'baseline_sha256':SHA,
  'best_full':{'variant':best['variant'],'score':best['score'],
    'score_delta':best['score_delta']} if best else None,'records':records}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2))
 print('K094_RESULT',json.dumps({'best_full':summary['best_full'],
  'cases':[{ 'variant':r['variant'],'status':r['status'],
   'nonlinear_saved':r.get('nonlinear_saved')} for r in records]},sort_keys=True),flush=True)
 print('SAVED',a.out/'summary.json',flush=True)
if __name__=='__main__':main()
