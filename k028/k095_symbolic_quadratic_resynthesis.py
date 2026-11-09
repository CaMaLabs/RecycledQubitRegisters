#!/usr/bin/env python3
"""K095 exact GF(2) quadratic resynthesis across large affine-reversible windows.

For contiguous X/CX/CCX regions with a single nonlinear target, derive the
complete algebraic normal form (ANF) on the *final* control coordinates.
Factor quadratic terms using symplectic elimination. Each quadratic pivot
costs one CCX plus CX parity basis changes, and preserves all qubits.

Candidates are exhaustively checked on every local computational basis state
(no approximation, no restrictions on superpositions: both circuits are
permutation unitaries). Never cross HMR, condition/classical instructions,
phase operations, or unknown opcodes. Preserve third-party Helios provenance.

Only run official full-domain verification if real nonlinear gate savings exist.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASE_SCORE=95369.00696815242
PAT=re.compile(r'^(X|CX|CCX)\s+(q\d+)(?:\s+(q\d+))?(?:\s+(q\d+))?\s*$',re.I)
ARITY={'X':1,'CX':2,'CCX':3}
def parse(s):
 m=PAT.fullmatch(s.strip())
 if m is None:return None
 op=m[1].upper();qs=tuple(int(x[1:]) for x in m.groups()[1:] if x)
 return (op,qs) if len(qs)==ARITY[op] and len(qs)==len(set(qs)) else None
def fmt(g):return g[0]+' '+' '.join('q'+str(x) for x in g[1])+'\n'
def xor(s,monomial):
 if monomial in s:s.remove(monomial)
 else:s.add(monomial)
def form_product(a,b):
 # Affine polynomial encoding: bit0 constant; bit i+1 represents x_i.
 result=set()
 for ia in range(a.bit_length()):
  if not ((a>>ia)&1):continue
  for ib in range(b.bit_length()):
   if not ((b>>ib)&1):continue
   if ia==0:term=0 if ib==0 else 1<<(ib-1)
   elif ib==0:term=1<<(ia-1)
   elif ia==ib:term=1<<(ia-1)
   else:term=(1<<(ia-1))|(1<<(ib-1))
   xor(result,term)
 return result
def inverse_forms(rows,m):
 # Each row is affine current control wire expressed using initial x.
 # Build invertible linear transformation and obtain initial x_i in final y.
 mat=[]
 for k,row in enumerate(rows):
  coeff=row>>1
  if coeff >= (1<<m):raise ValueError('Malformed affine transform')
  mat.append([coeff,1<<k,(row&1)])
 for j in range(m):
  p=next((k for k in range(j,m) if mat[k][0]&(1<<j)),None)
  if p is None:raise ValueError('Non-invertible affine control mapping')
  mat[j],mat[p]=mat[p],mat[j]
  for k in range(m):
   if k!=j and (mat[k][0]&(1<<j)):
    mat[k]=[u^v for u,v in zip(mat[k],mat[j])]
 return [(mat[i][1]<<1)|mat[i][2] for i in range(m)]
def transform_poly(poly,subs):
 new=set()
 for mon in poly:
  if mon==0:terms={0}
  else:
   indexes=[i for i in range(len(subs)) if mon&(1<<i)]
   terms=form_product(subs[indexes[0]],subs[indexes[1]]) if len(indexes)==2 else {
      (0 if j==0 else 1<<(j-1)) for j in range(subs[indexes[0]].bit_length())
      if subs[indexes[0]]&(1<<j)}
  for term in terms:xor(new,term)
 return new
def extract(block):
 # All CCX targets must be identical; no gate may use target as control.
 non=[g for g in block if g[0]=='CCX']
 if len(non)<2:return None
 targets={g[1][-1] for g in non}
 if len(targets)!=1:return None
 target=next(iter(targets))
 wires=tuple(sorted({q for op,qs in block for q in qs}-{target}))
 m=len(wires);pos={q:i for i,q in enumerate(wires)}
 if m<2:return None
 forms={q:1<<(i+1) for i,q in enumerate(wires)}
 poly=set();control_gates=[]
 for op,qs in block:
  t=qs[-1]
  if target in qs[:-1]:return None
  if t==target:
   if op=='X':xor(poly,0)
   elif op=='CX':
    a=forms[qs[0]]
    for j in range(a.bit_length()):
     if (a>>j)&1:xor(poly,0 if j==0 else 1<<(j-1))
   elif op=='CCX':
    for mon in form_product(forms[qs[0]],forms[qs[1]]):xor(poly,mon)
  else:
   if op=='CCX':return None
   if op=='X':forms[t]^=1
   elif op=='CX':forms[t]^=forms[qs[0]]
   control_gates.append((op,qs))
 inv=inverse_forms([forms[q] for q in wires],m)
 finalpoly=transform_poly(poly,inv)
 return {'target':target,'wires':wires,'controls':control_gates,
         'polynomial':finalpoly,'old_ccx':len(non)}
def quadratic_synth(ex):
 target=ex['target'];wires=ex['wires']
 poly=ex['polynomial']
 linear=set();edges=set()
 for term in poly:
  if term==0:linear.add(0)
  elif term.bit_count()==1:linear.add(term.bit_length()-1)
  elif term.bit_count()==2:
   i=(term & -term).bit_length()-1
   j=(term^(1<<i)).bit_length()-1
   edges.add((i,j))
  else:raise ValueError('Degree >2')
 result=list(ex['controls'])
 for i in sorted(linear,key=lambda k:(k!=-1,k)):
  if i==0 and 0 in poly: # constant is represented as 0 in linear: handled below
   pass
 # Resolve constant and linear separately, avoiding bit 0 ambiguity.
 if 0 in poly:result.append(('X',(target,)))
 for term in sorted(v for v in poly if v and v.bit_count()==1):
  result.append(('CX',(wires[term.bit_length()-1],target)))
 steps=0
 while edges:
  # Highest-degree pivot often minimizes parity overhead.
  deg=collections.Counter(v for edge in edges for v in edge)
  i=max(deg,key=lambda k:(deg[k],-k))
  j=max((v for edge in edges for v in edge if i in edge and v!=i),
        key=lambda k:(deg[k],-k))
  if i>j:i,j=j,i
  a=sorted(k for edge in edges if i in edge for k in edge if k!=i and k!=j)
  b=sorted(k for edge in edges if j in edge for k in edge if k!=j and k!=i)
  for e in tuple(edges):
   if i in e or j in e:edges.remove(e)
  # (x_i XOR B)*(x_j XOR A) contributes A*B to the residual.
  for u in a:
   for v in b:
    if u==v:
     # x_u^2=x_u; add linear term later
     key=('CX',(wires[u],target))
     # Store parity in a separate output accumulator, not repeated now:
     linear.symmetric_difference_update({u})
    else:
     e=(min(u,v),max(u,v))
     if e in edges:edges.remove(e)
     else:edges.add(e)
  for u in b:result.append(('CX',(wires[u],wires[i])))
  for u in a:result.append(('CX',(wires[u],wires[j])))
  result.append(('CCX',(wires[i],wires[j],target)))
  for u in reversed(a):result.append(('CX',(wires[u],wires[j])))
  for u in reversed(b):result.append(('CX',(wires[u],wires[i])))
  steps+=1
 # Linear terms from A*B must be applied once, after all nonlinear gates.
 # The original linear terms above have already been emitted, so exclude those.
 added={k for k in linear if isinstance(k,int) and k>=0}
 initial={term.bit_length()-1 for term in poly if term and term.bit_count()==1}
 for k in sorted(added ^ initial):result.append(('CX',(wires[k],target)))
 return result,steps

def eval_block(gates,wires,v):
 pos={q:i for i,q in enumerate(wires)}
 for op,qs in gates:
  if op=='X':v^=1<<pos[qs[0]]
  elif op=='CX':v^=((v>>pos[qs[0]])&1)<<pos[qs[1]]
  else:v^=(((v>>pos[qs[0]])&1)&((v>>pos[qs[1]])&1))<<pos[qs[2]]
 return v
def exact_equal(before,after,wires):
 return all(eval_block(before,wires,x)==eval_block(after,wires,x)
           for x in range(1<<len(wires)))
def try_block(block,max_wires):
 allw=tuple(sorted({q for _,qs in block for q in qs}))
 if len(allw)>max_wires:return None
 ex=extract(block)
 if not ex:return None
 candidate,new_ccx=quadratic_synth(ex)
 savings=ex['old_ccx']-new_ccx
 if savings<=0:return None
 if not exact_equal(block,candidate,allw):
  raise AssertionError(f'Non-equivalent candidate: {block} -> {candidate}')
 return {'gates':candidate,'ccx_saved':savings,'ccx_before':ex['old_ccx'],
    'ccx_after':new_ccx,'wires':allw,'lines_before':len(block),
    'lines_after':len(candidate),'degree2_terms':sum(v.bit_count()==2
                                                       for v in ex['polynomial'])}

def candidates(lines,max_wires,max_span,max_ccx_per_window):
 parsed=[parse(s) for s in lines]
 hits=[];tested=0
 i=0
 while i<len(lines):
  if parsed[i] is None:i+=1;continue
  j=i+1
  while j<len(lines) and parsed[j] is not None:j+=1
  ccx=[k for k in range(i,j) if parsed[k][0]=='CCX']
  for a,pos in enumerate(ccx):
   end=max(a+2,min(len(ccx),a+max_ccx_per_window))
   for e in range(a+2,end):
    last=ccx[e]
    if last-pos+1>max_span:break
    part=parsed[pos:last+1]
    if len({q for _,qs in part for q in qs})>max_wires:break
    tested+=1
    ans=try_block(part,max_wires)
    if ans:
     ans.update(start=pos,end=last+1)
     hits.append(ans)
  i=j
 hits.sort(key=lambda x:(-x['ccx_saved'],x['lines_after']-x['lines_before'],x['start']))
 selected=[]
 for x in hits:
  if any(x['start']<z['end'] and z['start']<x['end'] for z in selected):continue
  selected.append(x)
 selected.sort(key=lambda x:x['start'])
 out=[];cursor=0
 for x in selected:
  out+=lines[cursor:x['start']]
  out+=list(map(fmt,x['gates']))
  cursor=x['end']
 out+=lines[cursor:]
 return out,selected,{'runs_tested':tested,'valid_candidates':len(hits),
                       'chosen':len(selected)}
def selftest():
 for n in range(2,7):
  old=[('CCX',(0,k,7)) for k in range(1,n+1)]
  ans=try_block(old,8)
  assert ans is not None and ans['ccx_saved']==n-1,(n,ans)
 old=[('CX',(0,1)),('CCX',(1,2,7)),('CX',(2,3)),
      ('CCX',(1,3,7)),('CCX',(1,4,7))]
 ans=try_block(old,8)
 assert ans and ans['ccx_saved']>=1,ans
 x=[fmt(g) for g in old]+['HMR q8 b1\n']
 out,ch,scan=candidates(x,8,80,8)
 assert ch and out[-1]=='HMR q8 b1\n'
 print('K095_SELFTEST PASS exhaustive affine polynomial factoring, noncommuting control transformation, barriers',flush=True)
def good(v):return v.get('status')=='PASS' and v.get('exit_code')==0
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--base',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 p.add_argument('--out',type=Path,default=ROOT/'competition/k095/results')
 p.add_argument('--max-wires',type=int,default=9)
 p.add_argument('--max-span',type=int,default=180)
 p.add_argument('--max-ccx-window',type=int,default=12)
 p.add_argument('--prefix',type=int,default=4095)
 p.add_argument('--timeout',type=int,default=1200)
 p.add_argument('--full',action='store_true')
 p.add_argument('--self-test',action='store_true')
 a=p.parse_args()
 selftest()
 if a.self_test:return
 if not 3<=a.max_wires<=12:raise ValueError('max-wires outside range')
 if sha(a.base)!=PIN:raise RuntimeError('Pinned original Helios reference hash mismatch')
 ver=load('k031_k095',ROOT/'competition/k031/k031_full_domain_repair.py')
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 a.out.mkdir(parents=True,exist_ok=True)
 orig=km.Circuit.from_file(str(a.base),format='kmb')
 original=a.out/'helios_immutable.kmx';orig.to_file(str(original),format='kmx')
 lines=original.read_text().splitlines(keepends=True)
 print('K095_BASE',json.dumps({'sha256':PIN,'qubits':orig.num_qubits,
   'ccx':sum(s.lstrip().startswith('CCX ') for s in lines)},sort_keys=True),flush=True)
 started=time.monotonic()
 transformed,chosen,stats=candidates(lines,a.max_wires,a.max_span,a.max_ccx_window)
 saved=sum(c['ccx_saved'] for c in chosen)
 print('K095_SCAN',json.dumps({'ccx_saved':saved,**stats,'elapsed_s':round(time.monotonic()-started,2),
   'examples':[{k:v for k,v in c.items() if k not in ('gates',)}
               for c in chosen[:10]]},sort_keys=True),flush=True)
 report={'attribution':'third-party Helios original, experimental CaMaLabs ANF resynthesis',
    'pinned_sha256':PIN,'ccx_saved':saved,'scan':stats,
    'chosen':[{k:v for k,v in c.items() if k!='gates'} for c in chosen],
    'status':'NOT_RUN'}
 if not saved:report['status']='NO_NONLINEAR_SAVINGS'
 else:
  try:
   text=a.out/'candidate.kmx';text.write_text(''.join(transformed))
   candidate=km.Circuit.from_file(str(text),format='kmx')
   binary=a.out/'candidate.kmb';candidate.to_file(str(binary),format='kmb')
   report.update(qubits=candidate.num_qubits,candidate_sha256=sha(binary))
   v={'prefix':ver.verify(binary,a.prefix,12345,a.timeout)}
   if a.full and good(v['prefix']):
    v['full_12345']=ver.verify(binary,ver.FULL_X,12345,a.timeout)
    if good(v['full_12345']):
     v['full_23456']=ver.verify(binary,ver.FULL_X,23456,a.timeout)
   report['official']=v
   if not good(v['prefix']):report['status']='FAIL_PREFIX'
   elif a.full and good(v.get('full_12345',{})) and good(v.get('full_23456',{})):
    report['status']='PASS_FULL'
    report['score']=v['full_12345']['score']
    report['score_delta']=report['score']-BASE_SCORE
   elif a.full:report['status']='FAIL_FULL'
   else:report['status']='PASS_PREFIX_ONLY'
  except Exception as ex:report.update(status='ERROR',error=repr(ex))
 (a.out/'summary.json').write_text(json.dumps(report,indent=2,default=str))
 print('K095_RESULT',json.dumps({k:report.get(k) for k in
   ('status','ccx_saved','qubits','score','score_delta','error')},sort_keys=True),flush=True)
 print('SAVED',a.out/'summary.json',flush=True)
if __name__=='__main__':main()
