#!/usr/bin/env python3
"""QRR checkpoint/recompute: clear a reconstructible idle wire, restore later.
Recipes are exact XOR/AND functions, checked symbolically at both endpoints.
No sampled state or measurement erasure is used. Initial adapter selects only
non-overlapping global gaps so checkpoint recipes cannot read another omitted
wire. Costs include both clearing and restoration gates.
"""
import argparse,collections,json,re,time
from pathlib import Path
from branch_symbolic_lifetimes import Model,Q,ZERO,ONE

def find(lines,min_gap=8):
 m=Model();last={};definitions=collections.defaultdict(list);hits=[]
 def matches(q,recipe):
  value=ONE
  for c in recipe:value=m.mul(value,m.getq(c))
  return m.getq(q)==value
 for i,line in enumerate(lines):
  s=line.strip();op=s.split()[0] if s else '';qs=list(map(int,Q.findall(s)));pre={q:m.getq(q) for q in qs}
  if not m.stack:
   for q in set(qs):
    prev=last.get(q)
    if prev and i-prev['line']>=min_gap and matches(q,prev['recipe']):
     hits.append({'start':prev['line']+1,'stop':i,'target':q,'recipe':prev['recipe'],'span':i-prev['line']-1,'added_ccx':2 if len(prev['recipe'])==2 else 0})
  m.step(line)
  if not m.stack:
   if op in ('CX','CCX') and ' if ' not in s and pre[qs[-1]]==ZERO:
    recipe=tuple(qs[:-1])
    if recipe not in definitions[qs[-1]]:definitions[qs[-1]].append(recipe)
   for q in set(qs):
    last.pop(q,None)
    if m.getq(q)==ZERO:continue
    for recipe in reversed(definitions[q][-8:]):
     if matches(q,recipe):last[q]={'line':i,'recipe':recipe};break
  else:
   for q in set(qs):last.pop(q,None)
 return sorted(hits,key=lambda r:(r['added_ccx'],-r['span']))

def apply(lines,selected):
 boundaries=collections.defaultdict(list)
 for r in selected:
  g=('CX' if len(r['recipe'])==1 else 'CCX')+' '+' '.join('q'+str(q) for q in (*r['recipe'],r['target']))+'\n';boundaries[r['start']].append(g);boundaries[r['stop']].insert(0,g)
 out=[]
 for i,line in enumerate(lines):out+=boundaries[i];out.append(line)
 out+=boundaries[len(lines)];return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--max-added-ccx',type=int,default=0);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);lines=a.source.read_text().splitlines(keepends=True);t=time.monotonic();hits=find(lines);(a.out/'checkpoints.json').write_text(json.dumps({'candidates':hits,'elapsed_s':time.monotonic()-t},indent=2));print('K097_CHECKPOINTS',len(hits),hits[:10],flush=True)
 selected=[]
 for r in hits:
  if sum(x['added_ccx'] for x in selected)+r['added_ccx']<=a.max_added_ccx and not any(r['start']<x['stop'] and x['start']<r['stop'] for x in selected):selected.append(r)
 (a.out/'candidate.kmx').write_text(''.join(apply(lines,selected)));(a.out/'selected.json').write_text(json.dumps(selected,indent=2))
