#!/usr/bin/env python3
"""Reuse already-live quantum products through branch-aware symbolic equality.
CCX(a,b,t) -> CX(p,t) if p==a*b and p is not t.
CCZ(a,b,t) -> CZ(p,t), or Z(t) when p==t. No extra wire,
measurement or assumption about a sampled input is introduced.
"""
import argparse,collections,itertools,json,re,time
from pathlib import Path
from branch_symbolic_lifetimes import Model,Q

def transform(lines):
 m=Model();out=[];events=[]
 for i,line in enumerate(lines):
  s=line.strip();op=s.split()[0] if s else '';qs=tuple(map(int,Q.findall(s)));new=line
  if op in ('CCX','CCZ'):
   pairs=[qs[:2]] if op=='CCX' else list(itertools.combinations(qs,2))
   values={}
   for q,p in m.q.items():
    if p:values.setdefault(p,[]).append(q)
   for pair in pairs:
    product=m.mul(m.getq(pair[0]),m.getq(pair[1]));candidates=values.get(product,[]) if product else []
    rest=next(q for q in qs if q not in pair) if op=='CCZ' else qs[-1]
    candidates=[q for q in candidates if op=='CCZ' or q!=rest]
    if not candidates:continue
    cache=min(candidates);suffix=' if '+s.split(' if ')[1] if ' if ' in s else ''
    new=(f'Z q{rest}' if op=='CCZ' and cache==rest else f'{"CZ" if op=="CCZ" else "CX"} q{cache} q{rest}')+suffix+'\n';events.append({'line':i+1,'original':s,'replacement':new.strip(),'product_controls':pair,'existing_wire':cache});break
  m.step(line);out.append(new)
 return out,{'replacements':events,'saved':len(events),'by_gate':dict(collections.Counter(e['original'].split()[0] for e in events))}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);t=time.monotonic();lines,r=transform(a.source.read_text().splitlines(keepends=True));r['elapsed_s']=time.monotonic()-t;(a.out/'candidate.kmx').write_text(''.join(lines));(a.out/'reuse_report.json').write_text(json.dumps(r,indent=2));print('K097_EXISTING_PRODUCT',json.dumps(r),flush=True)
