#!/usr/bin/env python3
"""K124 phase-monomial expansion: structural screen, NOT a Kickmix submission."""
import argparse,json,math
from pathlib import Path
import numpy as np
from numpy.polynomial import Chebyshev,Polynomial
TOL=2**-24
def coefficients():
 t=np.cos(np.pi*(np.arange(64)+.5)/64);u=(t+1)/2
 return [list(Chebyshev.fit(u,1/np.sqrt(1+(s+u)/16),3,domain=[0,1]).convert(kind=Polynomial).coef) for s in range(16)]
def region_terms(e,c):
 n=max(0,e-4);w=[2.**(j-n) for j in range(n)];a,b,d,f=c;scale=2.**(-e/2)
 terms=[]
 for i,x in enumerate(w):terms.append(((i,),scale*(b*x+d*x*x+f*x**3)))
 for i in range(n):
  for j in range(i+1,n):
   x,y=w[i],w[j]
   terms.append(((i,j),scale*(2*d*x*y+3*f*(x*x*y+x*y*y))))
 for i in range(n):
  for j in range(i+1,n):
   for k in range(j+1,n):terms.append(((i,j,k),scale*6*f*w[i]*w[j]*w[k]))
 return scale*a,terms
def main():
 p=argparse.ArgumentParser();p.add_argument('--max-x',type=int,default=3133452)
 p.add_argument('--prune-fraction',type=float,default=.05)
 p.add_argument('--sample',type=int,default=20000)
 p.add_argument('--out',type=Path,default=Path('competition/k124/results/direct_phase_screen.json'))
 a=p.parse_args()
 if a.max_x<1 or a.max_x>3133452 or not 0<=a.prune_fraction<=.3:p.error('Invalid bounds')
 cs=coefficients();regions={};full=kept=0;summary=[]
 for e in range(a.max_x.bit_length()):
  for s in range(16):
   start=1<<e;lo=max(1,start+(s*start+15)//16)
   hi=min(a.max_x,start+((s+1)*start+15)//16-1)
   if lo>hi:continue
   base,terms=region_terms(e,cs[s]);floor=TOL/math.sqrt(hi)*a.prune_fraction
   omitted=set();error_bound=0.
   for subset,angle in sorted(terms,key=lambda z:abs(z[1])):
    if error_bound+abs(angle)>floor:break
    omitted.add(subset);error_bound+=abs(angle)
   retained=[(subset,angle) for subset,angle in terms if subset not in omitted]
   full+=len(terms);kept+=len(retained)
   regions[(e,s)]=(base,retained)
   summary.append({'exponent':e,'segment':s,'range':[lo,hi],
    'full_monomials':len(terms),'retained_monomials':len(retained),
    'pruned_error_fraction_of_tolerance':error_bound/(TOL/math.sqrt(hi))})
 counts={'regions':len(regions),'all_terms_including_constant':full+len(regions),
 'terms_retained_including_constant':kept+len(regions),
 'terms_pruned':full-kept}
 print('K124_COUNTS',json.dumps(counts),flush=True)
 rng=np.random.default_rng(124);xs=set(map(int,rng.integers(1,a.max_x+1,size=a.sample)))
 xs.update([1,a.max_x])
 for e in range(a.max_x.bit_length()):
  start=1<<e
  for s in range(16):
   x=start+(s*start+15)//16
   for z in (x-1,x,x+1):
    if 1<=z<=a.max_x:xs.add(z)
 worst=0.;worst_x=0;fail=0
 for x in xs:
  e=x.bit_length()-1;r=x-(1<<e);s=(r*16)>>e
  base,terms=regions[(e,s)];theta=base
  for subset,angle in terms:
   if all((r>>i)&1 for i in subset):theta+=angle
  relative=abs(theta-1/math.sqrt(x))*math.sqrt(x)
  if relative>worst:worst,worst_x=relative,x
  fail+=relative>=TOL
 checks={'sample_count':len(xs),'worst_x':worst_x,
  'worst_relative_error':worst,'tolerance_fraction':worst/TOL,'violations':fail}
 print('K124_SAMPLES',json.dumps(checks),flush=True)
 result={'status':'STRUCTURAL_REJECT_DIRECT_MONOMIALS','counts':counts,'sample_checks':checks,
  'regions':summary,'warning':['No full quantum circuit was synthesized.',
   'Source-like controlled phase terms do not equal verifier-executed rotations.',
   'Each term also needs exponent/segment control and possible cleanup.',
   'Floating-point sampled check is not exhaustive proof.',
   'Polynomial approximation and rotation synthesis errors also consume tolerance.']}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K124_RESULT',json.dumps({'status':result['status'],'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
