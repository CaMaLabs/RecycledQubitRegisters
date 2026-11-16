#!/usr/bin/env python3
"""K163 dual exact reversible affine seed constructions.
WORD: segment-controlled word accumulator (no separate seed register);
SHARED: shared ANF monomials across output bits (no product register).
Both are bounded Q3/Q4 (SHARED also Q5), not Q14 or a full Helios circuit.
"""
import argparse, collections, hashlib, json, math, random
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"

def coefficients(q):
 S=1<<q; ans=[]
 for j in range(8):
  if j<4:m0,m1=1+j/4,1+(j+1)/4
  else:m0,m1=2+2*(j-4)/4,2+2*(j-3)/4
  ans.append((round(S/math.sqrt(m0)),
              round(S*(1/math.sqrt(m0)-1/math.sqrt(m1))/(m1-m0))))
 return ans

def seed(q,s,o,c):
 return (c[s][0]-((c[s][1]*o+(1<<(q-1)))>>q))&((1<<(q+1))-1)

def mcx(c,t,s):
 n=len(c)
 if n==0:return [('X',t)]
 if n==1:return [('CX',c[0],t)]
 if n==2:return [('CCX',c[0],c[1],t)]
 assert len(s)>=n-2 and t not in c
 chain=[('CCX',c[0],c[1],s[0])]
 for i in range(2,n-1):chain.append(('CCX',s[i-2],c[i],s[i-1]))
 return chain+[('CCX',s[n-3],c[-1],t)]+chain[::-1]

def power_add(c,word,at,negative,scratch):
 """Exact reversible controlled +/- 2^at modulo 2^len(word).
 High-to-low updates preserve lower-bit carry/borrow tests."""
 g=[]
 if at>=len(word):return g
 for j in reversed(range(at,len(word))):
  low=word[at:j]
  if negative:g.extend(('X',b) for b in low)
  g+=mcx(c+low,word[j],scratch)
  if negative:g.extend(('X',b) for b in reversed(low))
 return g

def word_circuit(q):
 """Segment multiplexed coefficient times offset into one product/seed accumulator.
 P=(intercept<<q)-slope*offset+2^(q-1)-1. XOR P>>q and uncompute P.
 Product scratch remains oversized; experiment is a NEGATIVE architecture screen.
 """
 S=1<<q;n=2*q+1
 sel=list(range(3));off=list(range(3,3+q))
 z=list(range(3+q,3+2*q+1))
 acc=list(range(z[-1]+1,z[-1]+1+n))
 scratch=list(range(acc[-1]+1,acc[-1]+1+n+2))
 c=coefficients(q);g=[]
 for s,(intercept,slope) in enumerate(c):
  neg=[('X',sel[i]) for i in range(3) if not(s>>i)&1]
  g+=neg
  for bit in range(q+1):
   if (intercept>>bit)&1:g+=power_add(sel,acc,q+bit,False,scratch)
  for j in range(q):
   for k in range(slope.bit_length()):
    if(slope>>k)&1:g+=power_add(sel+[off[j]],acc,j+k,True,scratch)
  g+=neg[::-1]
 for bit in range(q):
  if ((S//2-1)>>bit)&1:g+=power_add([],acc,bit,False,scratch)
 g=g+[('CX',acc[q+i],z[i]) for i in range(q+1)]+g[::-1]
 return g,{'scratch':len(acc)+len(scratch),
           'total_wires':len(sel)+len(off)+len(z)+len(acc)+len(scratch),
           'product_work':len(acc),'mcx_work':len(scratch)}

def shared_circuit(q):
 """Compute each Boolean monomial ONCE into clean scratch, fan out to all
 output bits, and uncompute. Shares all nonlinear terms across a full output WORD.
 This still has exponential ANF size and q+2 clean scratch.
 """
 n=q+3;w=q+1;c=coefficients(q)
 values=[seed(q,i&7,i>>3,c) for i in range(1<<n)]
 terms=collections.defaultdict(list)
 for j in range(w):
  a=[(v>>j)&1 for v in values]
  for k in range(n):
   for mask in range(1<<n):
    if (mask>>k)&1:a[mask]^=a[mask^(1<<k)]
  for mask,enabled in enumerate(a):
   if enabled:terms[mask].append(n+j)
 scratch=list(range(n+w,n+w+n-1));g=[]
 for mask,targets in sorted(terms.items()):
  controls=[bit for bit in range(n) if (mask>>bit)&1]
  if not controls:g += [('X',t) for t in targets]
  elif len(controls)==1:g += [('CX',controls[0],t) for t in targets]
  else:
   chain=[('CCX',controls[0],controls[1],scratch[0])]
   for k in range(2,len(controls)):
    chain.append(('CCX',scratch[k-2],controls[k],scratch[k-1]))
   g+=chain+[('CX',scratch[len(controls)-2],t) for t in targets]+chain[::-1]
 return g,{'scratch':len(scratch),'total_wires':n+w+len(scratch),
           'nonzero_monomials':len(terms),'term_fanouts':sum(map(len,terms.values())),
           'note':'full ANF still exponential in q; sharing only avoids repeated monomial compute'}

def play(v,g):
 for op,*a in g:
  if op=='X':v^=1<<a[0]
  elif op=='CX':v^=((v>>a[0])&1)<<a[1]
  elif op=='CCX':v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
  else:raise AssertionError(op)
 return v

def check(q,g):
 c=coefficients(q);rng=random.Random(163+q);cases=0
 for s in range(8):
  for off in range(1<<q):
   value=seed(q,s,off,c)
   for z in (0,(1<<(q+1))-1,rng.randrange(1<<(q+1))):
    v=s|(off<<3)|(z<<(3+q))
    want=s|(off<<3)|((z^value)<<(3+q))
    observed=play(v,g)
    assert observed==want,(q,s,off,z,value,hex(observed^want))
    assert play(observed,reversed(g))==v
    assert play(observed,g)==v
    cases+=1
 return cases

def test(q,method):
 g,r=(word_circuit(q) if method=='word' else shared_circuit(q))
 cases=check(q,g);counts=collections.Counter(op for op,*_ in g)
 return {'q':q,'method':method,'CCX':counts['CCX'],'CX':counts['CX'],
         'X':counts['X'],'scratch':r['scratch'],
         'total_wires':r['total_wires'],'tested_cases':cases,'details':r}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k163/results/word_vs_shared.json'))
 p.add_argument('--selftest',action='store_true')
 p.add_argument('--scaling',action='store_true')
 a=p.parse_args()
 base=[test(3,'word'),test(3,'shared')]
 assert base[0]['CCX']==3428 and base[1]['CCX']==154
 print('K163_SELFTEST PASS bounded word accumulation and shared-output oracle, exact XOR, arbitrary targets, scratch clean',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 rows=base+[test(4,'word'),test(4,'shared')]
 if a.scaling:rows.append(test(5,'shared'))
 assert next(r for r in rows if r['q']==4 and r['method']=='word')['CCX']==7860
 assert next(r for r in rows if r['q']==4 and r['method']=='shared')['CCX']==440
 for row in rows:print('K163_CASE',json.dumps(row),flush=True)
 result={'status':'EXACT_BOUNDED_WORD_VS_SHARED_ANF_NOT_FULL_HELIOS',
  'pinned_sha256':sha,'cases':rows,
  'K161_reference_q4':{'CCX':7208,'scratch':24},
  'K162_reference_q4':{'CCX':1024,'scratch':5},
  'Q14_extrapolation':{'word_scratch_at_least':4*14+4,
     'shared_scratch_unmodified':14+2,
     'K151_nominal_free_scratch':12,'fits_compact_Newton':False},
  'limitations':['Word-level full-product arithmetic still uses too much scratch.',
    'Shared-ANF is low scratch at bounded Q, but grows exponentially and needs 16 scratch at Q14.',
    'K157 measurement carry remains unintegrated; no mid-circuit measurement here.',
    'These are exact q3..q5 basis gate tests, not full Q14 quantum circuit or official score.',
    'K159 full domain numerical seed remains valid; optimization cost remains unsolved.']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K163_RESULT',json.dumps({'q4_word_CCX':7860,'q4_word_scratch':20,
  'q4_shared_CCX':440,'q4_shared_scratch':6,'q14_fits_12_scratch':False,
  'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
