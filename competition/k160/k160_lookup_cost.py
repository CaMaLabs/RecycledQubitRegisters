#!/usr/bin/env python3
"""K160 exact ANF lookup cost comparison; interpolation intentionally unpriced."""
import argparse,collections,hashlib,json
from pathlib import Path
import numpy as np
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
def anf(values):
 n=(len(values)-1).bit_length();assert len(values)==1<<n
 width=max(map(int.bit_length,values));result=[]
 for bit in range(width):
  coef=[(int(v)>>bit)&1 for v in values]
  for k in range(n):
   for m in range(1<<n):
    if (m>>k)&1:coef[m]^=coef[m^(1<<k)]
  result.append([m for m,v in enumerate(coef) if v])
 return result,n,width
def mcx(c,t,s):
 if not c:return [('X',t)]
 if len(c)==1:return [('CX',c[0],t)]
 if len(c)==2:return [('CCX',*c,t)]
 chain=[('CCX',c[0],c[1],s[0])]
 for i in range(2,len(c)-1):chain.append(('CCX',s[i-2],c[i],s[i-1]))
 return chain+[('CCX',s[len(c)-3],c[-1],t)]+list(reversed(chain))
def run(v,ops):
 for op,*q in ops:
  if op=='X':v^=1<<q[0]
  elif op=='CX':v^=((v>>q[0])&1)<<q[1]
  else:v^=(((v>>q[0])&1)&((v>>q[1])&1))<<q[2]
 return v
def evaluate(name,values):
 mon,n,w=anf(values);s=list(range(n+w,n+w+max(0,n-2)));g=[]
 for b,terms in enumerate(mon):
  for m in terms:g+=mcx([j for j in range(n) if (m>>j)&1],n+b,s)
 mask=(1<<w)-1
 for selector in range(1<<n):
  for z in (0,mask,0x55aa&mask):
   v=selector|(z<<n);want=selector|((z^int(values[selector]))<<n)
   assert run(v,g)==want,(name,selector,z)
   assert run(want,reversed(g))==v,(name,selector,z,'reverse')
 c=collections.Counter(op for op,*_ in g)
 return {'name':name,'selector_bits':n,'output_bits':w,'entries':len(values),
  'CCX':c['CCX'],'CX':c['CX'],'X':c['X'],'clean_ancilla':len(s),
  'total_wires':n+w+len(s),'test_states':3*(1<<n),
  'scratch_clean':True,'ANF_monomials':sum(map(len,mon))}
def coefficient_values():
 S=1<<14;out=[]
 for j in range(8):
  if j<4:m0=1+j/4;m1=1+(j+1)/4
  else:m0=2+2*(j-4)/4;m1=2+2*(j-3)/4
  slope=(1/np.sqrt(m0)-1/np.sqrt(m1))/(m1-m0)
  out.append((round(S/np.sqrt(m0)),round(S*slope),round(S*m0)))
 return out
def execute():
 a=np.arange(32,dtype=float);m=np.r_[1+(a+.5)/32,2+2*(a+.5)/32]
 ref=np.rint((1<<14)/np.sqrt(m)).astype(np.int64).tolist()
 c=coefficient_values()
 return [evaluate('K149_64_seed',ref),evaluate('K159_intercept',[v[0] for v in c]),
         evaluate('K159_slope',[v[1] for v in c]),
         evaluate('K159_origin',[v[2] for v in c])]
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k160/results/lookup_anf.json'))
 p.add_argument('--selftest',action='store_true')
 a=p.parse_args();cases=execute()
 assert [c['CCX'] for c in cases]==[1365,56,37,4]
 print('K160_SELFTEST PASS reversible lookup ANF, arbitrary target, clean scratch',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 for c in cases:print('K160_ORACLE',json.dumps(c),flush=True)
 report={'status':'EXACT_LOOKUP_ONLY_INTERPOLATION_UNPRICED','pinned_sha256':sha,
         'cases':cases,'K149_lookup_CCX':1365,'K159_coeff_lookup_CCX':93,
         'K159_origin_lookup_CCX':4,
         'limitations':['Only exact gate-level ANF lookup networks compared, not optimized global synthesis.',
          'K159 still needs coherent selected-slope multiplication, subtraction, rounding and cleanup.',
          'K149 selector normalization and both designs Newton iterations unpriced here.',
          'No full 62-qubit datapath, Kickmix circuit or official score.']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+'\n')
 print('K160_RESULT',json.dumps({'K149_lookup_CCX':1365,
  'K159_coeff_lookup_CCX':93,'K159_origin_CCX':4,
  'interpolation_priced':False,'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
