#!/usr/bin/env python3
"""K166 classical constant ROM, coherent small-word oracle, segmented full-domain
numerical comparison and independent K157 carry phase benchmark.
Not a combined KMX circuit or official Helios verifier result.
"""
import argparse,collections,hashlib,json,math,random
from pathlib import Path
import numpy as np
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
N=3133452

def coeff(q=14):
 s=1<<q;rows=[]
 for j in range(8):
  lo,hi=(1+j/4,1+(j+1)/4) if j<4 else (2+2*(j-4)/4,2+2*(j-3)/4)
  rows.append((round(s/math.sqrt(lo)),round(s*(1/math.sqrt(lo)-1/math.sqrt(hi))/(hi-lo))))
 return tuple(rows)

def refine(y,m,q):
 s=np.int64(1<<q)
 sq=(y*y+s//2)//s
 product=(m*sq+s//2)//s
 return (y*(3*s-product)+s)//(2*s)

def numerical(max_x,chunk):
 # Constants exist in Python, not registers. Quantum-coherent selection still costs gates.
 c=np.asarray(coeff(),dtype=np.int64)
 a=np.arange(32,dtype=float)
 mid=np.r_[1+(a+.5)/32,2+2*(a+.5)/32]
 lut=np.rint(16384/np.sqrt(mid)).astype(np.int64)
 stats=[dict(segment=j,count=0,affine_violations=0,lookup_violations=0,
              affine_worst_fraction=0.,lookup_worst_fraction=0.) for j in range(8)]
 for start in range(1,max_x+1,chunk):
  x=np.arange(start,min(start+chunk,max_x+1),dtype=np.int64)
  k=(np.frexp(x.astype(float))[1]-1)//2
  denom=np.left_shift(np.int64(1),2*k)
  m=(x<<14)//denom
  segment=np.where(m<32768,(m-16384)//4096,4+(m-32768)//8192)
  origin=np.where(segment<4,16384+segment*4096,32768+(segment-4)*8192)
  index=np.where(m<32768,((m-16384)*32)//16384,32+((m-32768)*32)//32768)
  seeds={'affine':c[segment,0]-((c[segment,1]*(m-origin)+8192)//16384),
         'lookup':lut[index]}
  truth=1/np.sqrt(x.astype(float))
  m26=(x<<26)//denom
  for name,y0 in seeds.items():
   y14=refine(y0,m,14)
   y26=refine(y14<<12,m26,26)
   pred=y26.astype(float)/float(1<<26)/np.left_shift(np.int64(1),k)
   error=np.abs(pred-truth)/truth/(2.**-24)
   for seg in range(8):
    mask=segment==seg
    if not mask.any():continue
    r=stats[seg]
    if name=='affine':r['count']+=int(mask.sum())
    r[name+'_violations']+=int(np.count_nonzero(error[mask]>=1))
    r[name+'_worst_fraction']=max(r[name+'_worst_fraction'],float(error[mask].max()))
 return stats

def oracle(q=4):
 # Share each ANF monomial among all output bits; ROM coefficients are Python constants.
 n=q+3;w=q+1;c=coeff(q)
 values=[(c[v&7][0]-((c[v&7][1]*(v>>3)+(1<<(q-1)))>>q))&((1<<w)-1)
         for v in range(1<<n)]
 terms=collections.defaultdict(list)
 for bit in range(w):
  f=[(v>>bit)&1 for v in values]
  for j in range(n):
   for mask in range(1<<n):
    if mask&(1<<j):f[mask]^=f[mask^(1<<j)]
  for mask,on in enumerate(f):
   if on:terms[mask].append(n+bit)
 scratch=list(range(n+w,n+w+n-1));g=[]
 for mask,outs in sorted(terms.items()):
  controls=[b for b in range(n) if mask&(1<<b)]
  if not controls:g += [('X',o) for o in outs]
  elif len(controls)==1:g += [('CX',controls[0],o) for o in outs]
  else:
   chain=[('CCX',controls[0],controls[1],scratch[0])]
   for j in range(2,len(controls)):
    chain.append(('CCX',scratch[j-2],controls[j],scratch[j-1]))
   g += chain+[('CX',scratch[len(controls)-2],o) for o in outs]+chain[::-1]
 return g,values,{'input_qubits':n,'output_qubits':w,'scratch_qubits':len(scratch),
                   'total_qubits':n+w+len(scratch),'coefficient_qubits':0,'product_qubits':0}

def run_gates(v,g):
 for op,*a in g:
  if op=='X':v^=1<<a[0]
  elif op=='CX':v^=((v>>a[0])&1)<<a[1]
  elif op=='CCX':v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
 return v

def verify():
 q=4;g,values,resources=oracle(q);rng=random.Random(170);cases=0
 for x,answer in enumerate(values):
  for z in (0,31,rng.randrange(32)):
   v=x|(z<<7);out=run_gates(v,g)
   assert out==x|((z^answer)<<7)
   assert run_gates(out,reversed(g))==v
   cases+=1
 ct=collections.Counter(op for op,*_ in g)
 assert (ct['CCX'],cases,resources['scratch_qubits'])==(440,384,6)
 return {'CCX':ct['CCX'],'CX':ct['CX'],'X':ct['X'],
         'cases':cases,'resources':resources,'clean_scratch':True}

def check_carry():
 # Verify existing K157 separately; no claimed integration into the affine oracle.
 import importlib.util
 path=Path('competition/k157/k157_recycled_carry.py')
 if not path.exists():return {'status':'NOT_RUN','reason':'K157 script not present locally'}
 spec=importlib.util.spec_from_file_location('k157',path)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 r=mod.test(4,True)
 assert r['CCX']==7 and r['carry_scratch']==2
 return {'status':'PASS_SEPARATE','CCX':7,'scratch':2,
         'measurement_branches':r['measurement_branches_tested'],
         'integrated_into_affine_oracle':False}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k166/results/hybrid.json'))
 p.add_argument('--max-x',type=int,default=N)
 p.add_argument('--chunk',type=int,default=100000)
 p.add_argument('--selftest',action='store_true')
 a=p.parse_args()
 oracle_report=verify();carry_report=check_carry()
 print('K166_SELFTEST PASS classical ROM constants, coherent XOR oracle, clean workspace',flush=True)
 print('K166_ORACLE',json.dumps(oracle_report),flush=True)
 print('K166_CARRY',json.dumps(carry_report),flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 if not 1<=a.max_x<=N or a.chunk<100:p.error('invalid numerical bounds')
 rows=numerical(a.max_x,a.chunk)
 for row in rows:print('K166_RANGE',json.dumps(row),flush=True)
 result={'status':'RANGE_PROFILE_AND_BOUNDED_CLASSICAL_ROM_NOT_KMX',
         'baseline_sha256':sha,'tested_inputs':a.max_x,'ranges':rows,
         'oracle':oracle_report,'K157_separate':carry_report,
         'caveats':['No live quantum input or selector measured in computational basis',
                    'Classical ROM storage is free; coherent access still costs gates',
                    'K157 carry phase verification is separate, not integrated',
                    'No full 62-qubit oracle or official verifier/score']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K166_RESULT',json.dumps({'inputs':a.max_x,
   'affine_all_pass':all(r['affine_violations']==0 for r in rows),
   'lookup_all_pass':all(r['lookup_violations']==0 for r in rows),
   'coefficient_qubits':0,'carry_integrated':False,
   'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
