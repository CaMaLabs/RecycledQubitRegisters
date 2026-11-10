#!/usr/bin/env python3
"""Monte Carlo basis-trajectory filter only; NEVER a correctness certificate.
Find rare/absent effects worth spending SAT budget on. Candidate modifications
must independently pass proof and official verification before promotion.
"""
import argparse,collections,json,re
from pathlib import Path
import numpy as np
Q=re.compile(r'\bq(\d+)\b');B=re.compile(r'\bb(\d+)\b')
def search(lines,samples=32768,seed=97097,layout="uniform_prefix"):
 rng=np.random.default_rng(seed);half=samples//2
 small=np.arange(1,half+1) if layout=="uniform_prefix" else np.resize(np.arange(1,min(512,half)+1),half)
 x=np.r_[small,rng.integers(1,3133453,samples-half)].astype(np.uint32);ones=(1<<samples)-1
 def pack(v):return int.from_bytes(np.packbits(v,bitorder='little').tobytes(),'little')&ones
 q={i:pack((x>>i)&1) for i in range(22)};b={};scope=ones;stack=[];hits=[];rare=[];hist=collections.Counter()
 for index,line in enumerate(lines):
  s=line.strip();op=s.split()[0] if s else '';qs=list(map(int,Q.findall(s)));bs=list(map(int,B.findall(s)));active=scope&b.get(bs[-1],0) if ' if ' in s else scope
  get=lambda v:q.get(v,0)
  if op=='PUSH_CONDITION':stack.append(scope);scope=active;continue
  if op=='POP_CONDITION':scope=stack.pop();continue
  if op in ('X','CX','CCX'):
   effect=active
   for v in qs[:-1]:effect&=get(v)
   if op=='CCX':
    if not effect:hits.append({'line':index+1,'kind':'zero','original':s})
    if not (active&(get(qs[0])^get(qs[1]))):hits.append({'line':index+1,'kind':'equal','original':s})
    rare.append({'line':index+1,'kind':'zero','effect_samples':effect.bit_count(),'original':s})
   q[qs[-1]]=get(qs[-1])^effect
  elif op in ('SWAP','CSWAP'):
   a,c=qs[-2:];effect=active&(get(a)^get(c))
   if op=='CSWAP':
    effect&=get(qs[0])
    if not effect:hits.append({'line':index+1,'kind':'zero','original':s})
    rare.append({'line':index+1,'kind':'zero','effect_samples':effect.bit_count(),'original':s})
   q[a]=get(a)^effect;q[c]=get(c)^effect
  elif op in ('CZ','CCZ','Z','Z_POW'):
   if op=='CCZ':
    effect=active
    for v in qs:effect&=get(v)
    if not effect:hits.append({'line':index+1,'kind':'zero','original':s})
    rare.append({'line':index+1,'kind':'zero','effect_samples':effect.bit_count(),'original':s})
  elif op in ('HMR','R'):
   q[qs[0]]=get(qs[0])&(ones^active)
   if op=='HMR':
    rnd=int.from_bytes(rng.bytes((samples+7)//8),'little')&ones;old=b.get(bs[0],0);b[bs[0]]=(old&(ones^active))|(rnd&active)
  elif op in ('BIT_STORE0','BIT_STORE1'):
   old=b.get(bs[0],0);b[bs[0]]=(old&(ones^active))|(active if op=='BIT_STORE1' else 0)
  elif op=='BIT_INVERT':b[bs[0]]=b.get(bs[0],0)^active
  elif op in ('NEG','REGISTER','APPEND_TO_REGISTER') or not op:pass
  else:raise ValueError(s)
 restored=all(q.get(i,0)==pack((x>>i)&1) for i in range(22))
 return {'input_restored':restored,'layout':layout,'samples':samples,'seed':seed,'candidates':hits,'rarest':sorted(rare,key=lambda r:r['effect_samples'])[:40],'warning':'Sampling only; no safe gate deletion implied'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--samples',type=int,default=32768);p.add_argument('--layout',choices=['uniform_prefix','repeat_small'],default='uniform_prefix');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);r=search(a.source.read_text().splitlines(keepends=True),a.samples,layout=a.layout);(a.out/'candidate_constraints.json').write_text(json.dumps(r,indent=2));print('K097_FILTER',r['samples'],'samples',len(r['candidates']),'candidate proofs',r['candidates'][:12],flush=True)
