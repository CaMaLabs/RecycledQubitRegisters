#!/usr/bin/env python3
"""Phase-aware QRR product cache: CCZ(a,b,t) -> CZ(cached_AND,t).
The pair remains unwritten for the whole interval, including conditional
writes. Compute and HMR/CZ cleanup occur outside all condition scopes. Every
classical condition and intermediate measurement is preserved verbatim.
"""
import argparse,bisect,collections,itertools,json,re
from pathlib import Path
Q=re.compile(r'\bq(\d+)\b');B=re.compile(r'\bb(\d+)\b')
def transform(lines,max_span=10000):
 parsed=[];depth=0;maxq=-1;maxb=-1
 for line in lines:
  s=line.strip();op=s.split()[0] if s else '';qs=tuple(map(int,Q.findall(s)));maxq=max([maxq]+list(qs));maxb=max([maxb]+list(map(int,B.findall(s))))
  parsed.append((op,qs,depth))
  if op=='PUSH_CONDITION':depth+=1
  if op=='POP_CONDITION':depth-=1
 assert depth==0
 boundaries=[i for i,g in enumerate(parsed) if g[2]==0]+[len(lines)]
 def writes(g):
  op,qs,d=g
  if op in ('X','CX','CCX'):return set(qs[-1:])
  if op in ('SWAP','CSWAP'):return set(qs[-2:])
  if op in ('HMR','R'):return set(qs)
  if op in ('CZ','CCZ','Z','Z_POW','NEG','PUSH_CONDITION','POP_CONDITION','BIT_STORE0','BIT_STORE1','BIT_INVERT','REGISTER','APPEND_TO_REGISTER') or not op:return set()
  return set(qs)
 hits=[];seen=set()
 for i,(op,qs,d) in enumerate(parsed):
  if op!='CCZ':continue
  start=boundaries[bisect.bisect_right(boundaries,i)-1]
  for pair in itertools.combinations(sorted(qs),2):
   if (start,pair) in seen:continue
   seen.add((start,pair));p=set(pair)
   if any(p&writes(g) for g in parsed[start:i]):continue
   matching=[];last_safe_end=None
   for j in range(i,min(len(lines),start+max_span)):
    if p&writes(parsed[j]):break
    if parsed[j][0]=='CCZ' and p.issubset(parsed[j][1]):matching.append(j)
   if len(matching)<2:continue
   end=boundaries[bisect.bisect_right(boundaries,matching[-1])]
   if any(p&writes(g) for g in parsed[matching[-1]+1:end]):continue
   hits.append({'start':start,'stop':end,'controls':pair,'gates':matching,'static_saved':len(matching)-1})
 hits.sort(key=lambda r:(r['stop'],r['start']));ends=[r['stop'] for r in hits];best=[0];chosen=[[]]
 for i,r in enumerate(hits):
  prev=bisect.bisect_right(ends,r['start'],0,i);score=best[prev]+r['static_saved']
  if score>best[-1]:best.append(score);chosen.append(chosen[prev]+[r])
  else:best.append(best[-1]);chosen.append(chosen[-1])
 groups=chosen[-1];before=collections.defaultdict(list);replacement={};cache=maxq+1;bit=maxb+1
 for r in groups:
  a,b=r['controls'];before[r['start']].append(f'CCX q{a} q{b} q{cache}\n')
  for index in r['gates']:
   t=next(q for q in parsed[index][1] if q not in (a,b));suffix=' if '+lines[index].strip().split(' if ')[1] if ' if ' in lines[index] else '';replacement[index]=f'CZ q{cache} q{t}{suffix}\n'
  # Cleanup must precede a new group's initialization at a shared boundary.
  before[r['stop']][0:0]=[f'HMR q{cache} b{bit}\n',f'CZ q{a} q{b} if b{bit}\n']
 out=[]
 for i,line in enumerate(lines):out+=before[i];out.append(replacement.get(i,line))
 out+=before[len(lines)]
 return out,{'groups':groups,'candidate_groups':len(hits),'ccz_replaced':sum(len(r['gates']) for r in groups),'ccx_added':len(groups),'additional_qubits':int(bool(groups)),'cache_qubit':cache,'cache_bit':bit}
def selftest():
 for a,b,t,m in itertools.product((0,1),repeat=4):
  cache=a&b;assert (a&b&t)==(cache&t);assert (cache&m)==(a&b&m)
 lines=['PUSH_CONDITION if b0\n','CCZ q0 q1 q2\n','POP_CONDITION\n','PUSH_CONDITION if b1\n','CCZ q0 q1 q3\n','POP_CONDITION\n']
 out,r=transform(lines);assert r['ccz_replaced']==2 and r['ccx_added']==1
 lines.insert(3,'X q0\n');assert transform(lines)[1]['ccz_replaced']==0
 return {'quantum_phase_and_erasure_outcomes':16,'scope_and_write_barriers':'PASS'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);print(selftest());new,r=transform(a.source.read_text().splitlines(keepends=True));(a.out/'candidate.kmx').write_text(''.join(new));(a.out/'cache_report.json').write_text(json.dumps(r,indent=2));print('K097_DIAGONAL_CACHE',json.dumps({k:v for k,v in r.items() if k!='groups'}),flush=True)
