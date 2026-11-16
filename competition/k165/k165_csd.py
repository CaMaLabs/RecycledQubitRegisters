#!/usr/bin/env python3
"""K165 signed-digit segment slope vs binary shifted-add reversible seed.
Gate-level bounded Q3/Q4; Q14 constant-schedule screen only. Not a KMX submission.
"""
import argparse, collections, hashlib, json, math, random
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
def coeff(q):
 S=1<<q; ans=[]
 for j in range(8):
  if j<4: m0,m1=1+j/4,1+(j+1)/4
  else: m0,m1=2+2*(j-4)/4,2+2*(j-3)/4
  ans.append((round(S/math.sqrt(m0)),round(S*(1/math.sqrt(m0)-1/math.sqrt(m1))/(m1-m0))))
 return ans
def digits(v,mode):
 if mode=='binary':return [(i,1) for i in range(v.bit_length()) if (v>>i)&1]
 x=v;i=0;out=[]
 while x:
  if x&1:
   d=2-(x&3);out.append((i,d));x-=d
  x//=2;i+=1
 assert sum(d*(1<<i) for i,d in out)==v
 return out
def mcx(c,t,s):
 n=len(c)
 if n==0:return [('X',t)]
 if n==1:return [('CX',c[0],t)]
 if n==2:return [('CCX',c[0],c[1],t)]
 assert len(s)>=n-2 and t not in c
 chain=[('CCX',c[0],c[1],s[0])]
 for j in range(2,n-1):chain.append(('CCX',s[j-2],c[j],s[j-1]))
 return chain+[('CCX',s[n-3],c[-1],t)]+chain[::-1]
def power_add(c,word,pos,subtract,s):
 g=[]
 if pos>=len(word):return g
 for j in reversed(range(pos,len(word))):
  low=word[pos:j]
  if subtract:g.extend(('X',x) for x in low)
  g+=mcx(c+low,word[j],s)
  if subtract:g.extend(('X',x) for x in reversed(low))
 return g
def make(q,mode):
 assert mode in ('binary','csd')
 n=2*q+1; sel=list(range(3));off=list(range(3,3+q));out=list(range(3+q,4+2*q))
 product=list(range(out[-1]+1,out[-1]+1+n));scratch=list(range(product[-1]+1,product[-1]+1+n+2))
 g=[];c=coeff(q);terms=0
 for selector,(inter,slope) in enumerate(c):
  toggles=[('X',sel[i]) for i in range(3) if not ((selector>>i)&1)]
  g+=toggles
  for bit in range(q+1):
   if(inter>>bit)&1:g+=power_add(sel,product,q+bit,False,scratch)
  for offset_bit in range(q):
   for bit,sgn in digits(slope,mode):
    g+=power_add(sel+[off[offset_bit]],product,bit+offset_bit,sgn>0,scratch)
    terms+=1
  g+=toggles[::-1]
 for bit in range(q):
  if (((1<<(q-1))-1)>>bit)&1:g+=power_add([],product,bit,False,scratch)
 compute=g.copy()
 g+= [('CX',product[q+i],out[i]) for i in range(q+1)]
 g+=compute[::-1]
 return g,c,{'scratch':len(product)+len(scratch),'total_wires':scratch[-1]+1,'signed_shift_terms':terms}
def play(v,g):
 for op,*a in g:
  if op=='X':v^=1<<a[0]
  elif op=='CX':v^=((v>>a[0])&1)<<a[1]
  elif op=='CCX':v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
 return v
def run(q,mode):
 g,c,res=make(q,mode);rng=random.Random(165+q);mask=(1<<(q+1))-1
 cases=0
 for selector in range(8):
  for offset in range(1<<q):
   v=(c[selector][0]-((c[selector][1]*offset+(1<<(q-1)))>>q))&mask
   for d in (0,mask,rng.randrange(mask+1)):
    before=selector|(offset<<3)|(d<<(3+q))
    expected=selector|(offset<<3)|((d^v)<<(3+q))
    actual=play(before,g)
    assert actual==expected,(q,mode,selector,offset,d,actual^expected)
    assert play(actual,g)==before
    cases+=1
 counts=collections.Counter(t for t,*_ in g)
 return {'q':q,'mode':mode,'CCX':counts['CCX'],'CX':counts['CX'],'X':counts['X'],
         'scratch':res['scratch'],'total_wires':res['total_wires'],'tested_cases':cases,
         'shift_terms':res['signed_shift_terms']}
def q14_static():
 c=coeff(14)
 return [{'segment':j,'slope':b,'binary_digits':digits(b,'binary'),
          'csd_digits':digits(b,'csd'), 'binary_nonzero':len(digits(b,'binary')),
          'csd_nonzero':len(digits(b,'csd'))} for j,(_,b) in enumerate(c)]
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k165/results/csd_screen.json'))
 p.add_argument('--selftest',action='store_true');p.add_argument('--scaling',action='store_true')
 a=p.parse_args()
 for x in range(1,16384):
  assert sum(sign*(1<<bit) for bit,sign in digits(x,'csd'))==x
 test=run(3,'csd');assert test['tested_cases']==192
 print('K165_SELFTEST PASS CSD exact integers, reversible rounded XOR oracle, clean scratch',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 widths=(3,4) if a.scaling else (4,)
 cases=[run(q,mode) for q in widths for mode in ('binary','csd')]
 for row in cases:print('K165_CASE',json.dumps(row),flush=True)
 static=q14_static()
 print('K165_Q14_SLOPES',json.dumps([{'segment':x['segment'],'slope':x['slope'],
       'binary_nonzero':x['binary_nonzero'],'csd_nonzero':x['csd_nonzero']} for x in static]),flush=True)
 result={'status':'BOUNDED_CSD_REVERSIBLE_SHIFT_ADD_AND_Q14_STATIC_ONLY',
  'baseline_sha256':sha,'bounded_cases':cases,'q14_static':static,
  'limitations':['Q14 is constant-schedule screen, not gate-synthesized or verified',
   'A full product accumulator and MCX workspace exceed 12 scratch even at Q4',
   'CSD reduces terms but may not improve CCX if signed-borrow carries are expensive',
   'K157 measured carry not integrated and Kickmix conditional ops not verified',
   'No complete Helios circuit or official score claim']}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K165_RESULT',json.dumps({'cases':len(cases),'q14_binary_terms':sum(x['binary_nonzero'] for x in static),
  'q14_csd_terms':sum(x['csd_nonzero'] for x in static),'out':str(a.out),
  'full_helios_candidate':False}),flush=True)
if __name__=='__main__':main()
