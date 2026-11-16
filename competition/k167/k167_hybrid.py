#!/usr/bin/env python3
"""K167 exact cost-selected coherent segment routing (bounded Q3-Q5).
The Q3..Q5 lookup is a rounded center-sample SURROGATE, not the Q14
K149 implementation. No full 62-qubit circuit or official verifier.
"""
import argparse,collections,hashlib,json,math,random
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
def coeff(q):
 S=1<<q; result=[]
 for j in range(8):
  a,b=(1+j/4,1+(j+1)/4) if j<4 else (2+2*(j-4)/4,2+2*(j-3)/4)
  result.append((round(S/math.sqrt(a)),round(S*(1/math.sqrt(a)-1/math.sqrt(b))/(b-a))))
 return result
def word(q,s,o,mode,c):
 if mode=='affine':
  a,b=c[s];return (a-((b*o+(1<<(q-1)))>>q))&((1<<(q+1))-1)
 if mode=='lookup':
  j=o*8>>q
  m=1+(s+(j+.5)/8)/4 if s<4 else 2+2*(s-4+(j+.5)/8)/4
  return round((1<<q)/math.sqrt(m))&((1<<(q+1))-1)
 raise ValueError(mode)
def local_anf(values,q):
 terms=collections.defaultdict(list)
 for bit in range(q+1):
  p=[(v>>bit)&1 for v in values]
  for k in range(q):
   for mask in range(1<<q):
    if mask&(1<<k):p[mask]^=p[mask^(1<<k)]
  for mask,one in enumerate(p):
   if one:terms[mask].append(bit)
 return terms
def mcx(c,t,s):
 n=len(c)
 assert t not in c
 if n==0:return [('X',t)]
 if n==1:return [('CX',c[0],t)]
 if n==2:return [('CCX',c[0],c[1],t)]
 assert len(s)>=n-2
 chain=[('CCX',c[0],c[1],s[0])]
 for i in range(2,n-1):chain.append(('CCX',s[i-2],c[i],s[i-1]))
 return chain+[('CCX',s[n-3],c[-1],t)]+chain[::-1]
def block(q,seg,mode,c,sel,off,out,flag,term,work):
 polys=local_anf([word(q,seg,o,mode,c) for o in range(1<<q)],q)
 if not polys:return [],{'CCX':0,'CX':0,'X':0,'terms':0}
 toggles=[('X',sel[i]) for i in range(3) if not ((seg>>i)&1)]
 prep=toggles+mcx(sel,flag,work)+toggles[::-1]
 core=[]
 for mask,bits in sorted(polys.items()):
  if mask==0:
   core.extend(('CX',flag,out[j]) for j in bits);continue
  controls=[flag]+[off[i] for i in range(q) if (mask>>i)&1]
  sub=mcx(controls,term,work)
  core+=sub+[('CX',term,out[j]) for j in bits]+sub[::-1]
 g=prep+core+prep[::-1]
 counts=collections.Counter(x for x,*_ in g)
 return g,{'CCX':counts['CCX'],'CX':counts['CX'],'X':counts['X'],'terms':len(polys)}
def construct(q,forced=None):
 assert 3<=q<=5
 sel=list(range(3));off=list(range(3,3+q));out=list(range(3+q,4+2*q))
 scratch=list(range(out[-1]+1,out[-1]+q));flag=scratch[-1]+1;term=flag+1
 c=coeff(q);g=[];choices=[];rank=[]
 for seg in range(8):
  choices_for_segment={mode:block(q,seg,mode,c,sel,off,out,flag,term,scratch) for mode in ('affine','lookup')}
  winner=forced[seg] if forced is not None else min(choices_for_segment,key=lambda mode:(choices_for_segment[mode][1]['CCX'],choices_for_segment[mode][1]['CX']))
  g+=choices_for_segment[winner][0];choices.append(winner)
  rank.append({'segment':seg,'selected':winner,'alternatives':{k:v[1] for k,v in choices_for_segment.items()}})
 return g,c,{'scratch':len(scratch)+2,'total_wires':term+1,'coefficient_qubits':0,'product_qubits':0,'choices':choices,'rank':rank}
def play(v,g):
 for op,*a in g:
  if op=='X':v^=1<<a[0]
  elif op=='CX':v^=((v>>a[0])&1)<<a[1]
  elif op=='CCX':v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
  else:raise ValueError(op)
 return v
def verify(q,g,choices,c):
 rng=random.Random(167+q);cases=0;w=q+1
 for seg in range(8):
  for off in range(1<<q):
   answer=word(q,seg,off,choices[seg],c)
   for z in (0,(1<<w)-1,rng.randrange(1<<w)):
    before=seg|(off<<3)|(z<<(q+3))
    expect=seg|(off<<3)|((z^answer)<<(q+3))
    after=play(before,g)
    assert after==expect,(q,seg,off,z,answer,after^expect)
    assert play(after,g)==before
    assert play(after,reversed(g))==before
    cases+=1
 return cases
def test(q):
 rows=[]
 for mode,forced in [('cost',None),('all_affine',['affine']*8),('all_lookup',['lookup']*8)]:
  g,c,res=construct(q,forced);cases=verify(q,g,res['choices'],c)
  ct=collections.Counter(x for x,*_ in g)
  rows.append({'mode':mode,'q':q,'CCX':ct['CCX'],'CX':ct['CX'],'X':ct['X'],
    'scratch':res['scratch'],'total_wires':res['total_wires'],'cases':cases,
    'choices':res['choices'],'segment_costs':res['rank']})
 return rows
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k167/results/cost_hybrid.json'))
 p.add_argument('--selftest',action='store_true');p.add_argument('--scaling',action='store_true')
 a=p.parse_args();small=test(3)
 assert [r['CCX'] for r in small]==[54,106,78]
 print('K167_SELFTEST PASS coherent cost routing, arbitrary XOR target, all scratch clean',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 rows=[r for q in ((3,4,5) if a.scaling else (4,)) for r in (small if q==3 else test(q))]
 for r in rows:
  print('K167_CASE',json.dumps({k:v for k,v in r.items() if k!='segment_costs'}),flush=True)
 result={'status':'EXACT_BOUNDED_COST_ROUTED_HYBRID_NOT_Q14_HELIOS',
  'baseline_sha256':sha,'cases':rows,
  'warnings':['Q3-Q5 lookup uses rounded center-sample SURROGATE, not verified full Q14 K149 lookup.',
   'Selection optimizes static CCX for bounded ROM, not total executed Helios gates.',
   'Both Q14 methods passed the K166 full-domain numerical screen independently, but their Q4 circuit costs do not establish a Q14 routing advantage.',
   'Coherent selector preserved; no live input measurement.',
   'K157 measurement carry not integrated in these seed oracles.',
   'No full 62-qubit circuit or official leaderboard score.']}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
 best=next(r for r in rows if r['q']==4 and r['mode']=='cost')
 assert (best['CCX'],best['scratch'])==(120,5)
 print('K167_RESULT',json.dumps({'q4_CCX':best['CCX'],'q4_scratch':best['scratch'],
  'selection':best['choices'],'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
