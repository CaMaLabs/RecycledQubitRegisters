#!/usr/bin/env python3
"""K076 experimental FULL-INPUT-WIDTH coherent Kickmix implementation of K075.

The K075 16-segment quartic integer Horner model is reproduced structurally:
  22-bit input -> one-hot leading-bit flags -> 24-bit normalized mantissa
  -> 5-bit coherent coefficient QROM -> signed 40x20-bit Horner arithmetic
  -> exponent-conditioned right shift -> phase -> reverse all scratch.

WARNING: Experimental. Source code is not evidence of circuit correctness.
The official verifier is required, first at x<=15 and then full-domain.
Likely resource-heavy, NOT an asserted competitor to the Helios reference.

Relies on the existing trusted K034 local row implementation. No modifications
to K031 verifier, K075 coefficients, or original third-party benchmark.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/'competition/k001/private/official/verifiers'
sys.path.insert(0,str(VER))
import kickmix as km
import numpy as np
NB=22;FRAC=24;SEG_BITS=4;TB=FRAC-SEG_BITS
COEF_BITS=38;W=40;PW=W+TB;DEG=4;SEGMENTS=1<<SEG_BITS
WORDMASK=(1<<W)-1

def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def coefficients():
 # Exactly the coefficient construction of K075, not a refitted table.
 t=np.linspace(0,1,DEG+12)
 table=[]
 for parity in (0,1):
  bank=[]
  for seg in range(SEGMENTS):
   xx=1+(seg+t)/SEGMENTS
   fit=np.polynomial.polynomial.Polynomial.fit(
    t, (2**(-parity/2))/np.sqrt(xx), DEG,domain=[0,1]).convert().coef
   bank.append([int(round(float(c)*(1<<COEF_BITS))) for c in fit])
  table.append(bank)
 return table

def anf_words(table):
 out=[]
 for j in range(DEG+1):
  vals=[0]*(SEGMENTS*2)
  for p in (0,1):
   for s in range(SEGMENTS):vals[s|(p<<SEG_BITS)]=table[p][s][j]&WORDMASK
  for b in range(SEG_BITS+1):
   for m in range(len(vals)):
    if m&(1<<b):vals[m]^=vals[m^(1<<b)]
  out.append(vals)
 return out

def model(x,table):
 if x==0:return 0
 e=x.bit_length()-1
 low=x-(1<<e)
 q=(low<<FRAC)//(1<<e)
 seg=q>>(FRAC-SEG_BITS)
 t=q&((1<<TB)-1)
 v=table[e&1][seg][DEG]
 for j in range(DEG-1,-1,-1):
  v=table[e&1][seg][j]+((v*t)>>TB)
 return v>>(e//2)

def validate_model(table):
 samples=list(range(1,65537))
 samples += [(1<<i)+d for i in range(1,NB) for d in (-1,0,1) if (1<<i)+d>0]
 for x in samples:
  if x>(1<<NB)-1:continue
  approx=model(x,table)/(1<<COEF_BITS)
  truth=x**-0.5
  ratio=abs(approx-truth)/(truth*2**-24)
  if ratio>=0.5:raise AssertionError((x,ratio))
 return len(samples)

def and_bit(b,c,t):
 q=b.alloc_qubits(1)
 b.init_and(c,km.array([t]),km.array([q[0]]))
 return q

def unand_bit(b,c,t,q):
 b.del_and(c,km.array([t]),km.array([q[0]]));b.free(q)

def toggled_ccx(b,c,a,target):
 t=and_bit(b,c,a);b.cx(t[0],target);unand_bit(b,c,a,t)

def build(out,table):
 k034=load_module('k034_k076',ROOT/'competition/k034/k034_row_local_scratch.py')
 stats={'rows':0,'allocated_sum':0,'max_row_width':0}
 row=k034.local_row('compact',stats)
 anf=anf_words(table)
 builder=km.CircuitBuilder()
 x=builder.create_quantum_register(NB,name='x')
 # Keep the original input unchanged on completion; invert for zero-prefix.
 for i in range(NB):builder.x(x[i])
 z=[None]*(NB+1);z[NB]=builder.alloc_qubits(1);builder.x(z[NB][0])
 hot=[None]*NB
 for i in reversed(range(NB)):
  hot[i]=builder.alloc_qubits(1)
  builder.x(x[i])  # original bit 1
  builder.init_and(z[i+1][0],km.array([x[i]]),km.array([hot[i][0]]))
  builder.x(x[i])  # back to complemented bit
  z[i]=and_bit(builder,z[i+1][0],x[i])
 for i in range(NB):builder.x(x[i])  # input back to original, leave prefix controls live
 # Coherently extract exponent parity and nonzero flag from one-hot exponent.
 parity=builder.alloc_qubits(1)
 for i in range(1,NB,2):builder.cx(hot[i][0],parity[0])
 # Normalize mantissa: q=floor((x-2^e)*2^24/2^e).
 q=builder.alloc_qubits(FRAC)
 def toggle_normalized():
  for i in range(NB):
   for j in range(i):
    pos=FRAC-i+j
    toggled_ccx(builder,hot[i][0],x[j],q[pos])
 toggle_normalized()
 addr=[q[TB+j] for j in range(SEG_BITS)]+[parity[0]]
 # XOR coefficient lookup by algebraic normal form, with transient
 # coherent AND terms uncomputed in reverse.
 def toggle_coefficient(register,degree):
  for mask,value in enumerate(anf[degree]):
   if not value:continue
   bits=[addr[k] for k in range(SEG_BITS+1) if mask&(1<<k)]
   chain=[]
   if not bits:
    for k in range(W):
     if value&(1<<k):builder.x(register[k])
    continue
   control=bits[0]
   for src in bits[1:]:
    a=and_bit(builder,control,src);chain.append((control,src,a));control=a[0]
   for k in range(W):
    if value&(1<<k):builder.cx(control,register[k])
   for c,s,a in reversed(chain):unand_bit(builder,c,s,a)
 # Signed fixed-width multiplication into a *large* transient product,
 # using the K034 reversible row-adder contract. Positive lower bits,
 # negative top bit (two's complement).
 t=q[:TB]
 def mul(source,product,inverse):
  operations=[]
  for j in range(TB):
   operations.append((t[j],[(source[i],i+j) for i in range(W-1)],False))
   operations.append((t[j],[(source[W-1],W-1+j)],True))
  for c,terms,sub in (reversed(operations) if inverse else operations):
   row(builder,inverse,c,terms,product,km.array([]),subtract=sub)
 acc=[builder.alloc_qubits(W)]
 toggle_coefficient(acc[0],DEG)
 def forward(source,j):
  product=builder.alloc_qubits(PW);mul(source,product,False)
  dest=builder.alloc_qubits(W)
  for k in range(W):builder.cx(product[TB+k],dest[k])
  coef=builder.alloc_qubits(W);toggle_coefficient(coef,j)
  builder.iadd(coef,target=dest)
  toggle_coefficient(coef,j);builder.free(coef)
  mul(source,product,True);builder.free(product)
  return dest
 def backward(source,dest,j):
  product=builder.alloc_qubits(PW);mul(source,product,False)
  coef=builder.alloc_qubits(W);toggle_coefficient(coef,j)
  builder.isub(coef,target=dest)
  toggle_coefficient(coef,j);builder.free(coef)
  for k in reversed(range(W)):builder.cx(product[TB+k],dest[k])
  mul(source,product,True);builder.free(product);builder.free(dest)
 for j in reversed(range(DEG)):acc.append(forward(acc[-1],j))
 # qout = floor(acc_final/2**floor(exponent/2)).
 shifted=builder.alloc_qubits(W)
 def toggle_shifted():
  for i in range(NB):
   shift=i//2
   for k in range(shift,W):
    toggled_ccx(builder,hot[i][0],acc[-1][k],shifted[k-shift])
 toggle_shifted()
 # Z_POW exponent is twice the desired phase in turns.
 # Only the 38 fractional bits contribute modulo a full turn.
 for k in range(COEF_BITS):
  builder.z_pow(shifted[k],2.0**(k+1-COEF_BITS))
 toggle_shifted();builder.free(shifted)
 for j in range(DEG):
  backward(acc[-2],acc[-1],j);acc.pop()
 toggle_coefficient(acc[0],DEG);builder.free(acc[0])
 toggle_normalized();builder.free(q)
 for i in reversed(range(1,NB,2)):builder.cx(hot[i][0],parity[0])
 builder.free(parity)
 # Reconstruct original complemented x for prefix cleanup.
 for i in range(NB):builder.x(x[i])
 for i in range(NB):
  unand_bit(builder,z[i+1][0],x[i],z[i])
  builder.x(x[i])
  builder.del_and(z[i+1][0],km.array([x[i]]),km.array([hot[i][0]]))
  builder.x(x[i]);builder.free(hot[i])
 builder.x(z[NB][0]);builder.free(z[NB])
 for i in range(NB):builder.x(x[i])
 circ=builder.finish_circuit()
 circ.to_file(str(out),format='kmb')
 return {'num_qubits':circ.num_qubits,'file_bytes':out.stat().st_size,
  'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'row_stats':stats,
  'degree':DEG,'segments':SEGMENTS,'frac_bits':FRAC,'coeff_bits':COEF_BITS}

def official(out,prefix,timeout,full):
 k031=load_module('k031_k076',ROOT/'competition/k031/k031_full_domain_repair.py')
 results={}
 for label,n,seed in [('prefix',prefix,12345)]+(
  [('full_seed_12345',k031.FULL_X,12345),
   ('full_seed_23456',k031.FULL_X,23456)] if full else []):
  result=k031.verify(out,n,seed,timeout)
  results[label]=result
  print('K076_VERIFY',json.dumps({'label':label,'result':result},sort_keys=True),flush=True)
  if result.get('status')!='PASS' or result.get('exit_code')!=0:break
 return results

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--self-test',action='store_true')
 ap.add_argument('--build',action='store_true')
 ap.add_argument('--full',action='store_true')
 ap.add_argument('--prefix',type=int,default=15)
 ap.add_argument('--timeout',type=int,default=600)
 ap.add_argument('--out',type=Path,default=ROOT/'competition/k076/results')
 a=ap.parse_args()
 table=coefficients();n=validate_model(table)
 print('K076_MODEL_SELFTEST',json.dumps({'status':'PASS','sample_inputs':n,
   'scope':'classical fixed-point, not Kickmix verification'}),flush=True)
 if a.self_test:return
 a.out.mkdir(parents=True,exist_ok=True)
 report={'model':'K075 16 segment quartic','numeric_sample_inputs':n,
         'full_domain_official':False,'status':'MODEL_ONLY'}
 if a.build:
  path=a.out/'range_reduced_candidate.kmb'
  try:
   start=time.monotonic()
   info=build(path,table)
   print('K076_BUILD',json.dumps(info,sort_keys=True),flush=True)
   verification=official(path,a.prefix,a.timeout,a.full)
   report.update(status='BUILT',build=info,official=verification,
                 elapsed_build_s=round(time.monotonic()-start,2))
   if a.full and all(k in verification and verification[k].get('status')=='PASS' and
                     verification[k].get('exit_code')==0 for k in ('prefix','full_seed_12345','full_seed_23456')):
    report['full_domain_official']=True;report['status']='PASS_FULL'
   elif verification.get('prefix',{}).get('status')=='PASS':
    report['status']='PASS_PREFIX_ONLY'
   else:report['status']='FAIL_PREFIX'
  except Exception as ex:
   report['status']='BUILD_OR_VERIFY_ERROR';report['error']=repr(ex)
   print('K076_ERROR',json.dumps({'error':repr(ex)}),flush=True)
 (a.out/'report.json').write_text(json.dumps(report,indent=2,default=str))
 print('K076_RESULT',json.dumps({'status':report['status'],
  'num_qubits':report.get('build',{}).get('num_qubits'),
  'prefix_score':report.get('official',{}).get('prefix',{}).get('score'),
  'error':report.get('error'),'full_domain_official':report['full_domain_official']},sort_keys=True),flush=True)
 print('SAVED',a.out/'report.json',flush=True)
if __name__=='__main__':main()
