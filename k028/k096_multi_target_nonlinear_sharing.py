#!/usr/bin/env python3
"""K096: exact multi-output GF(2) nonlinear-product sharing on Helios.

A shared quadratic product applied to multiple targets can be computed by
one CCX and two CX gates per extra target:
 CCX(a,b,t0); CCX(a,b,t1)
    == CX(t0,t1); CCX(a,b,t0); CX(t0,t1)
The ANF pass generalizes this beyond literal matching by retaining an affine
network, deriving every output's nonlinear residual, and sharing quadratic
terms across targets. It works only where residual terms depend on clean
control outputs. Strictly barriers on measurements, conditions, phase gates.
Every accepted replacement is exhaustively verified as a reversible map
for ALL 2^k basis states (therefore valid for coherent superpositions).
Helios remains a credited third-party baseline. Full-domain acceptance
requires both official seeds and an improved score.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,re,sys,time,random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PIN='1c5b1ee282904faf4c1a09d2a440577de1866c47462ff7df9714768f9ed2a56a'
BASE_SCORE=95369.00696815242
PAT=re.compile(r'^(X|CX|CCX)\s+(q\d+)(?:\s+(q\d+))?(?:\s+(q\d+))?\s*$',re.I)
SWAP=re.compile(r'^CSWAP\s+q(\d+)\s+q(\d+)\s+q(\d+)\s*$',re.I)
ARITY={'X':1,'CX':2,'CCX':3}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p)
 if spec is None or spec.loader is None:raise FileNotFoundError(str(p))
 mod=importlib.util.module_from_spec(spec)
 sys.modules[name]=mod
 spec.loader.exec_module(mod)
 return mod
def parse(line):
 m=PAT.fullmatch(line.strip())
 if m is None:return None
 op=m.group(1).upper()
 qs=tuple(int(x[1:]) for x in m.groups()[1:] if x is not None)
 return (op,qs) if len(qs)==ARITY[op] and len(set(qs))==len(qs) else None
def fmt(g):return g[0]+' '+' '.join('q'+str(k) for k in g[1])+'\n'
def add(a,b):return a.symmetric_difference(b)
def multiply(a,b):
 out=set()
 for p in a:
  for q in b:
   term=p|q   # Boolean idempotence x*x=x
   if term.bit_count()>2:raise ValueError('Degree beyond quadratic')
   if term in out:out.remove(term)
   else:out.add(term)
 return out
def apply_poly(poly,gate,idx,nonlinear=True):
 op,qs=gate;t=idx[qs[-1]]
 if op=='X':poly[t]=add(poly[t],{0})
 elif op=='CX':poly[t]=add(poly[t],poly[idx[qs[0]]])
 elif nonlinear:
  a,b,_=qs
  poly[t]=add(poly[t],multiply(poly[idx[a]],poly[idx[b]]))
def affine_inverse(baseline):
 n=len(baseline);mat=[]
 for j,p in enumerate(baseline):
  if any(term.bit_count()>1 for term in p):raise ValueError('Nonlinear baseline')
  coeff=0
  for term in p:
   if term:coeff^=term
  mat.append([coeff,1<<j,int(0 in p)])
 for col in range(n):
  pivot=next((j for j in range(col,n) if mat[j][0]&(1<<col)),None)
  if pivot is None:raise ValueError('Noninvertible affine baseline')
  mat[col],mat[pivot]=mat[pivot],mat[col]
  for row in range(n):
   if row!=col and mat[row][0]&(1<<col):
    mat[row]=[x^y for x,y in zip(mat[row],mat[col])]
 return [({0} if mat[i][2] else set())|
         {1<<j for j in range(n) if (mat[i][1]>>j)&1}
         for i in range(n)]
def substitute(poly,subs):
 out=set()
 for term in poly:
  product={0}
  for j in range(len(subs)):
   if term&(1<<j):product=multiply(product,subs[j])
  out=add(out,product)
 return out
def characterize(block):
 wires=tuple(sorted({q for _,qs in block for q in qs}))
 idx={q:i for i,q in enumerate(wires)}
 n=len(wires)
 actual=[{1<<j} for j in range(n)]
 affine=[{1<<j} for j in range(n)]
 linear=[]
 try:
  for g in block:
   apply_poly(actual,g,idx)
   if g[0]!='CCX':
    apply_poly(affine,g,idx)
    linear.append(g)
  inverse=affine_inverse(affine)
  residual=[substitute(add(a,b),inverse) for a,b in zip(actual,affine)]
 except ValueError:return None
 clean={j for j,p in enumerate(residual) if not p}
 dirty=set(range(n))-clean
 if not dirty:return None
 # Corrections may use only wires without nonlinear residuals as controls.
 if any(any(term & ~sum(1<<j for j in clean) for term in p)
        for p in residual):return None
 return {'wires':wires,'affine':linear,'residual':residual,
         'clean':clean,'dirty':dirty}

def synthesize(block):
 desc=characterize(block)
 if desc is None:return None
 wires=desc['wires'];res=desc['residual'];clean=desc['clean']
 quad=collections.defaultdict(list);out=list(desc['affine'])
 for t,p in enumerate(res):
  for term in p:
   if term.bit_count()==2:quad[term].append(t)
 for term,targets in sorted(quad.items()):
  a=(term&-term).bit_length()-1
  b=(term^(1<<a)).bit_length()-1
  if a not in clean or b not in clean:return None
  anchor=targets[0]
  for other in targets[1:]:out.append(('CX',(wires[anchor],wires[other])))
  out.append(('CCX',(wires[a],wires[b],wires[anchor])))
  for other in reversed(targets[1:]):out.append(('CX',(wires[anchor],wires[other])))
 for t,p in enumerate(res):
  if 0 in p:out.append(('X',(wires[t],)))
  for term in sorted(p):
   if term and term.bit_count()==1:
    c=term.bit_length()-1
    if c not in clean:return None
    out.append(('CX',(wires[c],wires[t])))
 return out

def eval_circuit(gates,wires,v):
 index={q:i for i,q in enumerate(wires)}
 for op,qs in gates:
  t=index[qs[-1]]
  if op=='X':v^=1<<t
  elif op=='CX':v^=((v>>index[qs[0]])&1)<<t
  else:v^=(((v>>index[qs[0]])&1)&((v>>index[qs[1]])&1))<<t
 return v
def exact(before,after,wires):
 return all(eval_circuit(before,wires,x)==eval_circuit(after,wires,x)
            for x in range(1<<len(wires)))
def try_block(block,max_wires):
 wires=tuple(sorted({q for _,qs in block for q in qs}))
 if len(wires)>max_wires:return None
 old=sum(g[0]=='CCX' for g in block)
 if old<2:return None
 proposed=synthesize(block)
 if proposed is None:return None
 new=sum(g[0]=='CCX' for g in proposed)
 if new>=old:return None
 if not exact(block,proposed,wires):
  raise AssertionError('K096 ANF local equivalence failure')
 return {'gates':proposed,'ccx_saved':old-new,'old_ccx':old,'new_ccx':new,
         'wires':wires,'old_length':len(block),'new_length':len(proposed)}

def sweep(lines,max_wires,max_span,max_ccx_window):
 parsed=[parse(s) for s in lines]
 trials=0;hits=[];i=0
 while i<len(lines):
  if parsed[i] is None:i+=1;continue
  j=i+1
  while j<len(lines) and parsed[j] is not None:j+=1
  pivots=[p for p in range(i,j) if parsed[p][0]=='CCX']
  for a,p in enumerate(pivots):
   for b in range(a+1,min(len(pivots),a+max_ccx_window)):
    last=pivots[b]
    if last-p+1>max_span:break
    block=parsed[p:last+1]
    if len({q for _,qs in block for q in qs})>max_wires:break
    trials+=1
    candidate=try_block(block,max_wires)
    if candidate:
     candidate.update(start=p,end=last+1,algorithm='anf_multi_target')
     hits.append(candidate)
  i=j
 return hits,trials

def direct_pairs(lines,distance):
 # Independent two-target sharing, including unrelated intervening gates.
 parsed=[parse(s) for s in lines]
 hits=[];trials=0
 for i,g in enumerate(parsed):
  if g is None or g[0]!='CCX':continue
  a,b,t1=g[1];control=frozenset((a,b))
  for j in range(i+1,min(len(lines),i+distance+1)):
   q=parsed[j]
   if q is None:break
   trials+=1
   if q[0]=='CCX' and frozenset(q[1][:2])==control and q[1][2]!=t1:
    t2=q[1][2]
    footprint={a,b,t1,t2}
    if all(not (set(parsed[k][1])&footprint)
           for k in range(i+1,j)):
     replacement=[('CX',(t1,t2)),g,('CX',(t1,t2))]
     # Noncontiguous rewrite is legal because the intervening gates commute
     # with every gate in the replacement on disjoint wires.
     affected=tuple(sorted(footprint))
     assert exact([g,q],replacement,affected)
     hits.append({'start':i,'end':j+1,'replacement':replacement,
      'remove':j,'ccx_saved':1,'old_ccx':2,'new_ccx':1,
      'wires':affected,'algorithm':'independent_pair',
      'old_length':j-i+1,'new_length':j-i+2})
    break
   if set(q[1])&set((a,b,t1)):break
 return hits,trials

def choose(lines,hits):
 # Take nonoverlapping, highest-yield local transformations.
 ordered=sorted(hits,key=lambda x:(-x['ccx_saved'],x['new_length']-x['old_length'],x['start']))
 selected=[]
 for h in ordered:
  if any(h['start']<z['end'] and z['start']<h['end'] for z in selected):continue
  selected.append(h)
 selected.sort(key=lambda x:x['start'])
 out=[];cursor=0
 for h in selected:
  out.extend(lines[cursor:h['start']])
  if h['algorithm']=='independent_pair':
   for k in range(h['start'],h['end']):
    if k==h['start']:out.extend(fmt(g) for g in h['replacement'])
    elif k!=h['remove']:out.append(lines[k])
  else:out.extend(fmt(g) for g in h['gates'])
  cursor=h['end']
 out.extend(lines[cursor:])
 return out,selected

def expand(lines,mode):
 if mode=='original':return list(lines),0
 out=[];count=0;orientation=1 if mode.endswith('o1') else 0
 for s in lines:
  m=SWAP.fullmatch(s.strip())
  if m:
   c,a,b=map(int,m.groups())
   if orientation:a,b=b,a
   out.extend((f'CX q{a} q{b}\n',f'CCX q{c} q{b} q{a}\n',
               f'CX q{a} q{b}\n'))
   count+=1
  else:out.append(s)
 return out,count

def selftest():
 # Same product on three independent targets: 3 CCX -> 1.
 g=[('CCX',(0,1,4)),('CCX',(0,1,5)),('CCX',(0,1,6))]
 r=try_block(g,8)
 assert r is not None and r['ccx_saved']==2,r
 # Nontrivial target mixing and affine control preprocessing.
 g=[('CX',(2,1)),('CCX',(0,1,4)),('CX',(4,5)),
    ('CCX',(0,1,5)),('X',(0,)),('CCX',(0,1,6))]
 r=try_block(g,8)
 if r is not None:assert exact(g,r['gates'],r['wires'])
 lines=['CCX q0 q1 q4\n','X q7\n','CCX q0 q1 q5\n','HMR q3 b0\n']
 hits,trials=direct_pairs(lines,12)
 assert hits and hits[0]['ccx_saved']==1
 out,selected=choose(lines,hits)
 assert len(selected)==1 and out[-1]=='HMR q3 b0\n'
 for s in ('HMR q8 b1\n','CZ q8 q9\n','CX q0 q7\n'):
  modified=list(lines);modified[1]=s
  assert not direct_pairs(modified,12)[0]
 # Diverse random circuits, exact local check if savings found.
 rng=random.Random(96096)
 for _ in range(250):
  qubits=list(range(7));gs=[]
  for j in range(rng.randint(5,28)):
   op=rng.choice(('X','CX','CX','CCX','CCX','CCX'))
   gs.append((op,tuple(rng.sample(qubits,ARITY[op]))))
  try_block(gs,9)
 print('K096_SELFTEST PASS multi-target ANF, affine propagation, direct sharing, barriers, randomized exhaustive equivalence',flush=True)

def good(x):return x.get('status')=='PASS' and x.get('exit_code')==0
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--base',type=Path,default=ROOT/'competition/k058/results/dataset/invsqrt.kmb')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k096/results')
 ap.add_argument('--variants',nargs='+',choices=['original','all_o0','all_o1'],
     default=['original','all_o0','all_o1'])
 ap.add_argument('--max-wires',type=int,default=9)
 ap.add_argument('--max-span',type=int,default=180)
 ap.add_argument('--max-ccx-window',type=int,default=12)
 ap.add_argument('--pair-distance',type=int,default=150)
 ap.add_argument('--prefix',type=int,default=4095)
 ap.add_argument('--timeout',type=int,default=1200)
 ap.add_argument('--full',action='store_true')
 ap.add_argument('--self-test',action='store_true')
 args=ap.parse_args()
 selftest()
 if args.self_test:return
 if not 3<=args.max_wires<=12:raise ValueError('max-wires should be 3..12')
 if sha(args.base)!=PIN:raise RuntimeError('Pinned original Helios SHA-256 mismatch')
 ver=load('k031_k096',ROOT/'competition/k031/k031_full_domain_repair.py')
 sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
 import kickmix as km
 args.out.mkdir(parents=True,exist_ok=True)
 original=km.Circuit.from_file(str(args.base),format='kmb')
 text=args.out/'original_helios.kmx';original.to_file(str(text),format='kmx')
 lines=text.read_text().splitlines(keepends=True)
 report={'baseline_sha256':PIN,'baseline_score':BASE_SCORE,'qubits':original.num_qubits,
         'attribution':'Helios public third-party circuit; K096 experimental transforms',
         'variants':[]}
 print('K096_BASE',json.dumps({'qubits':original.num_qubits,'source_sha256':PIN,
   'nonlinear_units':sum(s.lstrip().startswith(('CCX ','CCZ ','CSWAP ')) for s in lines)}),flush=True)
 for name in args.variants:
  start=time.monotonic()
  record={'variant':name,'status':'NOT_RUN','full_domain_verified':False}
  try:
   source,expanded=expand(lines,name)
   anf,trials=sweep(source,args.max_wires,args.max_span,args.max_ccx_window)
   direct,pair_trials=direct_pairs(source,args.pair_distance)
   result,selected=choose(source,anf+direct)
   saved=sum(x['ccx_saved'] for x in selected)
   record.update(expanded_cswaps=expanded,anf_windows_tested=trials,
      pair_checks=pair_trials,anf_candidates=len(anf),direct_candidates=len(direct),
      selected=len(selected),ccx_saved=saved,
      examples=[{k:v for k,v in x.items() if k not in ('gates','replacement','wires')}
                for x in selected[:12]])
   print('K096_SCAN',json.dumps({'variant':name,'expanded_cswaps':expanded,
      'anf_windows_tested':trials,'pair_checks':pair_trials,
      'anf_candidates':len(anf),'direct_candidates':len(direct),
      'ccx_saved':saved,'selected':len(selected)},sort_keys=True),flush=True)
   if not saved:record['status']='NO_NONLINEAR_SAVINGS'
   else:
    kmx=args.out/(name+'.kmx');kmx.write_text(''.join(result))
    candidate=km.Circuit.from_file(str(kmx),format='kmx')
    binary=args.out/(name+'.kmb');candidate.to_file(str(binary),format='kmb')
    record.update(qubits=candidate.num_qubits,candidate_sha256=sha(binary))
    official={'prefix':ver.verify(binary,args.prefix,12345,args.timeout)}
    if args.full and good(official['prefix']):
     official['full_12345']=ver.verify(binary,ver.FULL_X,12345,args.timeout)
     if good(official['full_12345']):
      official['full_23456']=ver.verify(binary,ver.FULL_X,23456,args.timeout)
    record['official']=official
    if not good(official['prefix']):record['status']='FAIL_PREFIX'
    elif args.full and good(official.get('full_12345',{})) and good(official.get('full_23456',{})):
     record.update(status='PASS_FULL',full_domain_verified=True,
          score=official['full_12345']['score'])
     record['score_delta']=record['score']-BASE_SCORE
    elif args.full:record['status']='FAIL_FULL'
    else:
     record.update(status='PASS_PREFIX_ONLY',
                   prefix_score=official['prefix'].get('score'))
   record['elapsed_s']=round(time.monotonic()-start,3)
  except Exception as e:record.update(status='ERROR',error=repr(e))
  report['variants'].append(record)
  (args.out/(name+'.json')).write_text(json.dumps(record,indent=2,default=str))
  print('K096_CASE',json.dumps({k:record.get(k) for k in
      ('variant','status','ccx_saved','score','score_delta','qubits','error')},
      sort_keys=True),flush=True)
 winners=[r for r in report['variants'] if r.get('status')=='PASS_FULL']
 best=min(winners,key=lambda x:x['score']) if winners else None
 report['best_full']={'variant':best['variant'],'score':best['score'],
      'score_delta':best['score_delta']} if best else None
 (args.out/'summary.json').write_text(json.dumps(report,indent=2,default=str))
 print('K096_RESULT',json.dumps({'best_full':report['best_full'],
   'cases':[(r['variant'],r['status'],r.get('ccx_saved')) for r in report['variants']]},
    sort_keys=True),flush=True)
 print('SAVED',args.out/'summary.json',flush=True)
if __name__=='__main__':main()
