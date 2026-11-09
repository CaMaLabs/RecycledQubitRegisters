#!/usr/bin/env python3
"""K075 numerical screen of range-reduced invsqrt over every nonzero 22-bit x.
NOT a Kickmix circuit and NOT an official verifier result.
"""
from __future__ import annotations
import argparse,json,math,time
from pathlib import Path
import numpy as np
FULL_X=3133452
MAX_X=(1<<22)-1
TOL=2**-24

def coeffs(bits,degree,segments):
 scale=1<<bits;tables=[]
 for par in (0,1):
  part=[]
  for j in range(segments):
   ts=np.linspace(0,1,degree+12)
   xx=1+(j+ts)/segments
   vv=np.polynomial.polynomial.Polynomial.fit(
    ts,(2**(-par/2))/np.sqrt(xx),degree,domain=[0,1]).convert().coef
   part.append(tuple(int(round(float(v)*scale)) for v in vv))
  tables.append(part)
 return tables

def eval_chunk(start,stop,bits,frac,segments,degree,table):
 x=np.arange(start,stop,dtype=np.int64)
 e=np.floor(np.log2(x)).astype(np.int64)
 e-=((np.int64(1)<<e)>x)
 low=x-(np.int64(1)<<e)
 q=np.empty_like(x)
 small=e<=frac
 q[small]=low[small]<<(frac-e[small])
 q[~small]=low[~small]>>(e[~small]-frac)
 seg=(q*segments)>>frac
 t=(q*segments)&((1<<frac)-1)
 qout=np.empty_like(x)
 for p in (0,1):
  maskp=(e&1)==p
  for j in range(segments):
   mask=maskp&(seg==j)
   if not mask.any():continue
   c=table[p][j]
   val=np.full(int(mask.sum()),c[-1],dtype=np.int64)
   tt=t[mask]
   for cc in reversed(c[:-1]):val=cc+((val*tt)>>frac)
   qout[mask]=val
 qout=qout>>(e//2)
 target=1/np.sqrt(x.astype(np.float64))
 err=np.abs(qout.astype(np.float64)/(1<<bits)-target)
 relative=err/(target*TOL)
 max_idx=int(np.argmax(relative))
 return {'tested':int(x.size),'worst_ratio':float(relative[max_idx]),
         'worst_x':int(x[max_idx]),'failures':int(np.count_nonzero(relative>1)),
         'above_half_margin':int(np.count_nonzero(relative>0.5)),
         'max_abs_error':float(err.max())}

def scan(bits=38,frac=24,segments=16,degree=4,limit=MAX_X,chunk=131072):
 assert segments>=2 and segments&(segments-1)==0
 assert 30<=bits<=39 and 20<=frac<=25 and bits+frac<=62
 assert degree>=1
 tab=coeffs(bits,degree,segments)
 report={'bits':bits,'frac':frac,'segments':segments,'degree':degree,
  'table_words':2*segments*(degree+1),'max_x':limit,
  'tested':0,'worst_ratio':0,'worst_x':0,'failures':0,
  'above_half_margin':0,'max_abs_error':0}
 for start in range(1,limit+1,chunk):
  result=eval_chunk(start,min(limit+1,start+chunk),bits,frac,segments,degree,tab)
  report['tested']+=result['tested']
  for key in ('failures','above_half_margin'):report[key]+=result[key]
  report['max_abs_error']=max(report['max_abs_error'],result['max_abs_error'])
  if result['worst_ratio']>report['worst_ratio']:
   report['worst_ratio']=result['worst_ratio']
   report['worst_x']=result['worst_x']
 report['margin_pass']=report['worst_ratio']<=0.5
 report['numeric_pass']=report['failures']==0
 return report

def selftest():
 t=coeffs(38,2,4)
 for x in range(1,513):
  r=eval_chunk(x,x+1,38,22,4,2,t)
  assert r['tested']==1 and r['worst_ratio']>=0
 assert scan(38,24,16,4,1024)['numeric_pass']
 print('K075_SELFTEST PASS integer Horner, exponent normalization, small-domain error gate',flush=True)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--out',type=Path,default=Path('competition/k075/results'))
 ap.add_argument('--max-x',type=int,default=MAX_X)
 ap.add_argument('--chunk',type=int,default=131072)
 ap.add_argument('--bits',type=int,default=38)
 ap.add_argument('--frac',type=int,default=24)
 ap.add_argument('--self-test',action='store_true')
 ap.add_argument('--segments',type=int,nargs='+',default=[16,32,64])
 ap.add_argument('--degrees',type=int,nargs='+',default=[3,4,5])
 a=ap.parse_args();selftest()
 if a.self_test:return
 a.out.mkdir(parents=True,exist_ok=True)
 results=[]
 for segments in a.segments:
  for degree in a.degrees:
   start=time.perf_counter()
   r=scan(a.bits,a.frac,segments,degree,a.max_x,a.chunk)
   r['elapsed_s']=round(time.perf_counter()-start,2)
   results.append(r)
   print('K075_MODEL',json.dumps(r,sort_keys=True),flush=True)
 valid=[r for r in results if r['margin_pass']]
 valid.sort(key=lambda r:(r['table_words'],r['degree'],r['worst_ratio']))
 selected=valid[0] if valid else None
 report={'status':'NUMERIC_MARGIN_FOUND' if selected else 'NO_NUMERIC_MARGIN',
  'selected':selected,'sweep':results,'not_a_quantum_circuit':True,
  'official_verification':None,
  'note':'Only a numeric model. A real circuit still needs reversible leading-one normalization, a coherent coefficient lookup, integer Horner, phase, and uncomputation.'}
 if selected:
  coefficients=coeffs(selected['bits'],selected['degree'],selected['segments'])
  coeff_export={'selected':selected,'scaling':'Q'+str(selected['bits']),
   'mantissa_t_fraction_bits':selected['frac'],
   'coefficient_rows_by_exponent_parity':coefficients,
   'address_description':'leading-one exponent, top mantissa bits and exponent parity',
   'status':'NUMERIC_DESIGN_ONLY'}
  (a.out/'coefficients.json').write_text(json.dumps(coeff_export,indent=2))
 (a.out/'screen.json').write_text(json.dumps(report,indent=2))
 print('K075_RESULT',json.dumps({'status':report['status'],'selected':selected,
       'full_domain_screened':a.max_x==MAX_X},sort_keys=True),flush=True)
 print('SAVED',a.out/'screen.json',flush=True)
if __name__=='__main__':main()
