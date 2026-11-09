#!/usr/bin/env python3
"""K081: multiplication-free phase oracle microbenchmark and numerical gate.

Architectural proposal: piecewise SECANT lookup. A segment indicator coherently
controls a base phase; residual mantissa bits select precomputed phase increments.
No output register, full-width multiplier or reversible accumulation is needed.

This standalone oracle is deliberately a phase function of (parity, segment,
residual) only. Full 22-bit inverse square root also requires reversible input
normalization and exponent-dependent phase scaling. Therefore this circuit is
NOT a full-domain contest submission, regardless of its microbenchmark cost.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,sys,time
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
F=24
BITS=38
MAX_X=(1<<22)-1

def coefficient_table(segments):
 assert segments>0 and segments & (segments-1)==0
 j=np.arange(segments+1,dtype=np.float64)
 rows=[]
 for p in (0,1):
  endpoints=np.rint((2**(-p/2))/np.sqrt(1+j/segments)*(1<<BITS)).astype(np.int64)
  rows.append(np.stack((endpoints[:-1],endpoints[1:]-endpoints[:-1]),axis=1))
 return np.stack(rows)

def numerical_screen(table,limit=MAX_X,chunk=131072):
 segments=table.shape[1]
 worst=0.0;worst_x=0;fails=0;half=0
 for start in range(1,limit+1,chunk):
  x=np.arange(start,min(limit+1,start+chunk),dtype=np.int64)
  e=np.floor(np.log2(x)).astype(np.int64)
  q=(x-(np.int64(1)<<e))<<(F-e)
  seg=(q*segments)>>F
  t=(q*segments)&((1<<F)-1)
  v=table[e&1,seg,0]+((table[e&1,seg,1]*t)>>F)
  y=(v>>(e//2)).astype(np.float64)/(1<<BITS)
  truth=1/np.sqrt(x.astype(np.float64))
  ratio=np.abs(y-truth)/(truth*(2**-24))
  index=int(np.argmax(ratio))
  if float(ratio[index])>worst:
   worst=float(ratio[index]);worst_x=int(x[index])
  fails+=int(np.count_nonzero(ratio>1))
  half+=int(np.count_nonzero(ratio>0.5))
 return {'tested':int(limit),'worst_error_over_tolerance':worst,
         'worst_x':worst_x,'tolerance_failures':fails,
         'above_half_tolerance':half,'margin_pass':half==0}

def selftest():
 for n in (2,4,8):
  table=coefficient_table(n)
  for p in (0,1):
   for s in range(n):
    b,d=map(int,table[p,s])
    for residual in range(16):
     assert b+((d*residual)>>4)==int(table[p,s,0])+((int(table[p,s,1])*residual)>>4)
 short=numerical_screen(coefficient_table(2048),2048)
 assert short['tolerance_failures']==0,short
 print('K081_SELFTEST PASS secant coefficient lookup, residual integer interpolation, short numerical screen',flush=True)

def circuit_builder(km,seg_bits=4,residual_bits=4,out=None):
 b=km.CircuitBuilder()
 parity=b.create_quantum_register(1,name='exponent_parity')
 segment=b.create_quantum_register(seg_bits,name='segment')
 frac=b.create_quantum_register(residual_bits,name='fraction')
 addr=list(segment)+[parity[0]]
 table=coefficient_table(1<<seg_bits)
 rotations=0;and_pairs=0
 for p in range(2):
  for s in range(1<<seg_bits):
   pattern=s|(p<<seg_bits)
   flips=[idx for idx in range(seg_bits+1) if not ((pattern>>idx)&1)]
   for idx in flips:b.x(addr[idx])
   nodes=[]
   c=addr[0]
   for idx in range(1,seg_bits+1):
    anc=b.alloc_qubits(1)
    b.init_and(c,km.array([addr[idx]]),km.array([anc[0]]))
    nodes.append((c,addr[idx],anc))
    c=anc[0]
   base,delta=(int(table[p,s,0]),int(table[p,s,1]))
   base%=1<<BITS
   if base:
    b.z_pow(c,Fraction(2*base,1<<BITS));rotations+=1
   for i in range(residual_bits):
    if not delta:continue
    anc=b.alloc_qubits(1)
    b.init_and(c,km.array([frac[i]]),km.array([anc[0]]))
    b.z_pow(anc[0],Fraction(2*delta*(1<<i),1<<(BITS+residual_bits)))
    b.del_and(c,km.array([frac[i]]),km.array([anc[0]]))
    b.free(anc)
    and_pairs+=1;rotations+=1
   for u,v,a in reversed(nodes):
    b.del_and(u,km.array([v]),km.array([a[0]]));b.free(a)
   for idx in reversed(flips):b.x(addr[idx])
 circ=b.finish_circuit()
 if out is not None:circ.to_file(str(out),format='kmx')
 return circ,{'phase_rotations_requested':rotations,'controlled_phase_ands':and_pairs,
              'address_rows':2*(1<<seg_bits),'segment_bits':seg_bits,
              'fraction_bits':residual_bits,'num_qubits':circ.num_qubits}

def kmx_counts(path):
 counts=collections.Counter()
 for line in path.open():
  s=line.strip()
  if s and not s.startswith('#'):counts[s.split()[0]]+=1
 return dict(total=sum(counts.values()),**{k:counts[k] for k in
  ('CCX','CCZ','CSWAP','CX','CZ','HMR','Z_POW','BIT_INVERT')})

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--self-test',action='store_true')
 ap.add_argument('--segments',type=int,nargs='+',default=[1024,2048,4096])
 ap.add_argument('--bench-address-bits',type=int,nargs='+',default=[3,4,5])
 ap.add_argument('--residual-bits',type=int,default=4)
 ap.add_argument('--numeric-only',action='store_true')
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k081/results')
 a=ap.parse_args();selftest()
 if a.self_test:return
 a.out.mkdir(parents=True,exist_ok=True)
 numeric=[]
 for n in a.segments:
  started=time.monotonic()
  r=numerical_screen(coefficient_table(n))
  r.update(segments=n,table_words=4*n,elapsed_s=round(time.monotonic()-started,3))
  numeric.append(r)
  print('K081_NUMERIC',json.dumps(r,sort_keys=True),flush=True)
 benches=[]
 if not a.numeric_only:
  sys.path.insert(0,str(ROOT/'competition/k001/private/official/verifiers'))
  import kickmix as km
  for bits in a.bench_address_bits:
   if not 1<=bits<=6:raise ValueError('microbenchmark address bits must be 1..6')
   target=a.out/f'phase_oracle_a{bits}_f{a.residual_bits}.kmx'
   try:
    circuit,stats=circuit_builder(km,bits,a.residual_bits,target)
    stats['compiled_counts']=kmx_counts(target)
    stats['file_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    stats['status']='COMPILED_MICROBENCHMARK_NOT_VERIFIED'
   except Exception as exc:
    stats={'segment_bits':bits,'status':'BUILD_ERROR','error':repr(exc)}
   benches.append(stats)
   print('K081_BENCH',json.dumps(stats,sort_keys=True),flush=True)
 report={'status':'NUMERIC_AND_RESOURCE_SCREEN','numerical':numeric,
         'microbenchmarks':benches,'is_full_domain_competition_candidate':False,
         'interpretation':'Standalone coherent phase oracle on parity,segment,fraction. No normalization/exponent scaling; gate counts are not an official score. Linear phase has fractional coefficient interpolation, while integer screen rounds per x.'}
 (a.out/'report.json').write_text(json.dumps(report,indent=2))
 print('K081_RESULT',json.dumps({'status':report['status'],
        'margin_models':[v['segments'] for v in numeric if v['margin_pass']],
        'benchmarks':[{'bits':v['segment_bits'],'status':v['status'],
         'qubits':v.get('num_qubits'),'counts':v.get('compiled_counts')} for v in benches]},sort_keys=True),flush=True)
 print('SAVED',a.out/'report.json',flush=True)
if __name__=='__main__':main()
