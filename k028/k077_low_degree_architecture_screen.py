#!/usr/bin/env python3
"""K077: full-domain fixed-point inverse-sqrt approximation architecture screen.
Produces no quantum circuit; reports numeric error and rough cost proxies.
"""
import argparse,json,time,math
from pathlib import Path
import numpy as np
BITS=38; FRAC=24; DOMAIN=(1<<22)-1
def coefficients(segments,degree):
 t=np.linspace(0.,1.,degree+12)
 arr=np.empty((2,segments,degree+1),dtype=np.int64)
 for p in (0,1):
  for j in range(segments):
   xx=1+(j+t)/segments
   y=2**(-p/2)/np.sqrt(xx)
   arr[p,j]=np.rint(np.polynomial.polynomial.Polynomial.fit(t,y,degree,domain=[0,1]).convert().coef*(1<<BITS)).astype(np.int64)
 return arr
def probe(tab,nums):
 degree=tab.shape[-1]-1;segments=tab.shape[1]
 x=np.asarray(nums,dtype=np.int64)
 e=np.floor(np.log2(x)).astype(np.int64)
 low=x-(np.int64(1)<<e)
 q=np.where(e<=FRAC,low<<np.maximum(0,FRAC-e),low>>np.maximum(0,e-FRAC))
 seg=q*segments>>FRAC
 t=q*segments&((1<<FRAC)-1)
 acc=tab[e&1,seg,degree].copy()
 for j in range(degree-1,-1,-1):acc=tab[e&1,seg,j]+((acc*t)>>FRAC)
 res=acc>>(e//2)
 truth=1/np.sqrt(x.astype(float))
 ratio=np.abs(res/(1<<BITS)-truth)/(truth*2**-24)
 i=int(np.argmax(ratio))
 return {'worst_ratio':float(ratio[i]),'worst_x':int(x[i]),
         'fails':int(np.count_nonzero(ratio>1)),
         'beyond_margin':int(np.count_nonzero(ratio>0.5))}
def scan(tab,limit,chunk=131072):
 result={'worst_ratio':0.,'worst_x':0,'fails':0,'beyond_margin':0,'tested':0}
 for start in range(1,limit+1,chunk):
  end=min(start+chunk,limit+1)
  r=probe(tab,np.arange(start,end,dtype=np.int64))
  result['tested']+=end-start
  result['fails']+=r['fails'];result['beyond_margin']+=r['beyond_margin']
  if r['worst_ratio']>result['worst_ratio']:
   result['worst_ratio']=r['worst_ratio'];result['worst_x']=r['worst_x']
 result['margin_pass']=result['beyond_margin']==0
 return result
def cost(segments,degree):
 ab=int(math.log2(segments))+1
 words=2*segments*(degree+1)
 products=degree*40*(FRAC-int(math.log2(segments)))
 return {'qrom_words':words,'address_bits':ab,
         'generic_bitproducts_per_forward_horner':products,
         'symmetric_compute_uncompute_bitproducts':2*products,
         'low_bits_per_horner_term':FRAC-int(math.log2(segments))}
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--segments',nargs='+',type=int,default=[16,32,64,128,256,512,1024,2048,4096])
 p.add_argument('--degrees',nargs='+',type=int,default=[1,2,3])
 p.add_argument('--max-x',type=int,default=DOMAIN)
 p.add_argument('--out',type=Path,default=Path('competition/k077/results'))
 p.add_argument('--self-test',action='store_true')
 a=p.parse_args()
 t=scan(coefficients(16,4),2048)
 assert t['margin_pass'] and t['tested']==2048
 print('K077_SELFTEST PASS integer Horner and K075 16-segment quartic accuracy',flush=True)
 if a.self_test:return
 sample=np.unique(np.concatenate((np.arange(1,min(a.max_x,65536)+1),
    np.arange(max(1,a.max_x-131072),a.max_x+1,17),
    np.array([max(1,min(a.max_x,(1<<k)+d)) for k in range(22) for d in (-1,0,1)]))))
 results=[]
 for s in a.segments:
  if s<=0 or s&(s-1) or s>1<<FRAC:raise ValueError('segments must be a supported power of two')
  for d in a.degrees:
   begin=time.perf_counter();tab=coefficients(s,d);r=probe(tab,sample)
   detail={'segments':s,'degree':d,'sample_worst_ratio':r['worst_ratio'],
      'sample_failures':r['fails'],'cost_proxy':cost(s,d),'full':None}
   if r['worst_ratio']<=0.75:detail['full']=scan(tab,a.max_x)
   detail['elapsed_s']=round(time.perf_counter()-begin,2)
   results.append(detail)
   print('K077_MODEL',json.dumps({k:v for k,v in detail.items() if k!='cost_proxy'}),flush=True)
 accepted=[r for r in results if r['full'] and r['full']['margin_pass']]
 accepted.sort(key=lambda r:(r['cost_proxy']['symmetric_compute_uncompute_bitproducts'],
                             r['cost_proxy']['qrom_words']))
 report={'status':'NUMERIC_DESIGN_ONLY','domain_max_x':a.max_x,
  'full_domain_screened':a.max_x==DOMAIN,'official_verification':None,
  'models':results,'margin_models':[{'segments':r['segments'],'degree':r['degree'],
         'worst_ratio':r['full']['worst_ratio'],'cost_proxy':r['cost_proxy']} for r in accepted],
  'caveat':'No Kickmix circuit. Cost proxy omits QROM synthesis, carry propagation, phase rotations, and routing. Passing the classical error screen does not establish coherent circuit correctness.'}
 a.out.mkdir(parents=True,exist_ok=True)
 (a.out/'report.json').write_text(json.dumps(report,indent=2))
 print('K077_RESULT',json.dumps({'status':report['status'],'models_tested':len(results),
   'top_margin_models':report['margin_models'][:8]}),flush=True)
 print('SAVED',a.out/'report.json',flush=True)
if __name__=='__main__':main()
