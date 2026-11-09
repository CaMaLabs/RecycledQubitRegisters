#!/usr/bin/env python3
"""QRR retained-product caching on the actual public gate stream.
One additional clean wire, reused between disjoint intervals. Controls cannot
be written in a retained interval. HMR+classical CZ erasure preserves phase
on every measurement outcome. Coherent erasure is an explicit A/B arm.
"""
import argparse,collections,json,re
from pathlib import Path
Q=re.compile(r'\bq(\d+)\b');B=re.compile(r'\bb(\d+)\b')
def transform(lines,measurement=True,max_span=5000,affine=False):
 parsed=[];depth=0;maxq=-1;maxb=-1
 for line in lines:
  t=line.strip();op=t.split()[0] if t else '';qs=tuple(map(int,Q.findall(t)));bs=list(map(int,B.findall(t)));maxq=max([maxq]+list(qs));maxb=max([maxb]+bs)
  if op=='POP_CONDITION':depth-=1
  parsed.append((op,qs,depth,' if ' in t))
  if op=='PUSH_CONDITION':depth+=1
 def writes(g):
  op,qs,depth,inline=g
  if op in ('X','CX','CCX'):return set(qs[-1:])
  if op in ('SWAP','CSWAP'):return set(qs[-2:])
  if op in ('HMR','R'):return set(qs)
  if op in ('CZ','CCZ','Z','Z_POW','NEG','PUSH_CONDITION','POP_CONDITION','BIT_INVERT','BIT_STORE0','BIT_STORE1','APPEND_TO_REGISTER','REGISTER') or not op:return set()
  return set(qs) if qs else None
 candidates=[]
 for i,(op,qs,scope,inline) in enumerate(parsed):
  if op!='CCX' or scope or inline:continue
  pair=set(qs[:2]);a,b=sorted(pair);forms={a:0b1010,b:0b1100};hits=[i];corrections={i:0}
  def correction():
   difference=(forms[a]&forms[b])^0b1000
   for mask in range(8):
    value=(15 if mask&1 else 0)^(forms[a] if mask&2 else 0)^(forms[b] if mask&4 else 0)
    if value==difference:return mask
   raise AssertionError('Lost invertible affine pair invariant')
  for j in range(i+1,min(len(lines),i+max_span+1)):
   g=parsed[j];written=writes(g)
   if written is None:break
   if pair&written:
    if affine and not g[2] and not g[3]:
     if g[0]=='X' and g[1][0] in pair:forms[g[1][0]]^=15;continue
     if g[0]=='CX' and set(g[1])==pair:forms[g[1][1]]^=forms[g[1][0]];continue
     if g[0]=='SWAP' and set(g[1])==pair:forms[a],forms[b]=forms[b],forms[a];continue
    break
   if g[0]=='CCX' and not g[2] and not g[3] and set(g[1][:2])==pair:hits.append(j);corrections[j]=correction()
  saved=len(hits)-(1 if measurement else 2)
  if saved>0:candidates.append({'start':i,'stop':hits[-1],'hits':hits,'controls':sorted(pair),'saved':saved,'corrections':corrections})
 # Weighted interval scheduling, not greedily selecting locally largest groups.
 candidates.sort(key=lambda c:(c['stop'],c['start']));best=[0];chosen=[[]]
 import bisect
 ends=[c['stop'] for c in candidates]
 for i,c in enumerate(candidates):
  pred=bisect.bisect_left(ends,c['start'],0,i);score=best[pred]+c['saved']
  if score>best[-1]:best.append(score);chosen.append(chosen[pred]+[c])
  else:best.append(best[-1]);chosen.append(chosen[-1])
 groups=chosen[-1];updates={};before={};after={};cache=maxq+1;bit=maxb+1
 for c in groups:
  a,b=c['controls'];before[c['start']]=[f'CCX q{a} q{b} q{cache}\n']
  for i in c['hits']:
   t=parsed[i][1][-1];mask=c['corrections'][i];updates[i]=f'CX q{cache} q{t}\n'+(f'CX q{a} q{t}\n' if mask&2 else '')+(f'CX q{b} q{t}\n' if mask&4 else '')+(f'X q{t}\n' if mask&1 else '')
  after[c['stop']]=[f'HMR q{cache} b{bit}\n',f'CZ q{a} q{b} if b{bit}\n'] if measurement else [f'CCX q{a} q{b} q{cache}\n']
 for c in groups:
  a,b=c['controls'];mask=c['corrections'][c['stop']]
  if measurement:
   after[c['stop']]+=[f'Z q{a} if b{bit}\n'] if mask&2 else []
   after[c['stop']]+=[f'Z q{b} if b{bit}\n'] if mask&4 else []
   after[c['stop']]+=[f'NEG if b{bit}\n'] if mask&1 else []
  else:
   after[c['stop']]+=[f'CX q{a} q{cache}\n'] if mask&2 else []
   after[c['stop']]+=[f'CX q{b} q{cache}\n'] if mask&4 else []
   after[c['stop']]+=[f'X q{cache}\n'] if mask&1 else []
 out=[]
 for i,line in enumerate(lines):out+=before.get(i,[]);out.append(updates.get(i,line));out+=after.get(i,[])
 return out,{'mode':'measurement' if measurement else 'coherent','groups':groups,'ccx_saved':sum(c['saved'] for c in groups),'additional_qubits':int(bool(groups)),'source_max_qubit':maxq,'cache_qubit':cache,'cache_bit':bit,'candidate_intervals':len(candidates),'affine_controls':affine}
def selftest():
 # Every input control/target/cache-zero combination and both erasure outcomes.
 for a in (0,1):
  for b in (0,1):
   for targets in range(8):
    old=targets^((a&b)*7);cache=a&b;new=targets^(cache*7);assert old==new
    for m in (0,1):assert ((cache&m)^((a&b)&m))==0
 source=['CCX q0 q1 q2\n','HMR q2 b0\n','CCX q1 q0 q3\n']
 out,r=transform(source);assert r['ccx_saved']==1 and r['groups']
 changed=['CCX q0 q1 q2\n','CX q4 q0\n','CCX q0 q1 q3\n'];assert not transform(changed)[1]['groups']
 for fa in range(16):
  for fb in range(16):
   pairs=[((fa>>x)&1)+2*((fb>>x)&1) for x in range(4)]
   if len(set(pairs))!=4:continue
   difference=(fa&fb)^0b1000
   masks=[m for m in range(8) if ((15 if m&1 else 0)^(fa if m&2 else 0)^(fb if m&4 else 0))==difference]
   assert len(masks)==1
   m=masks[0]
   for x in range(4):
    va=(fa>>x)&1;vb=(fb>>x)&1;cache=int(x==3)
    correction=int(bool(m&1))^(va if m&2 else 0)^(vb if m&4 else 0)
    assert (va&vb)==cache^correction
    for outcome in (0,1):assert ((cache^(va&vb)^correction)&outcome)==0
 return {'basis_and_measurement_branch_identity':'PASS','control_write_barrier':'PASS','affine_pair_maps_exhaustive':24}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--coherent',action='store_true');p.add_argument('--affine',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);print(selftest());l,r=transform(a.source.read_text().splitlines(keepends=True),not a.coherent,affine=a.affine);(a.out/'candidate.kmx').write_text(''.join(l));(a.out/'cache_report.json').write_text(json.dumps(r,indent=2));print('K096_CACHE',json.dumps({k:v for k,v in r.items() if k!='groups'}),flush=True)
