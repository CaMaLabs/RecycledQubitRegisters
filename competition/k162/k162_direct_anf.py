#!/usr/bin/env python3
"""K162 direct reversible eight-segment affine seed XOR oracle.
No product, selected slope, or seed workspace registers.
Exact Boolean ANF synthesis; bounded Q3..Q6, NOT full Q14 Helios.
"""
import argparse,collections,hashlib,json,math,random
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def coefficients(q):
 S=1<<q; data=[]
 for j in range(8):
  if j<4:m0,m1=1+j/4,1+(j+1)/4
  else:m0,m1=2+2*(j-4)/4,2+2*(j-3)/4
  data.append((round(S/math.sqrt(m0)),
   round(S*(1/math.sqrt(m0)-1/math.sqrt(m1))/(m1-m0))))
 return data

def affine(q,segment,offset,c):
 intercept,slope=c[segment]
 return (intercept-((slope*offset+(1<<(q-1)))>>q))&((1<<(q+1))-1)

def mcx(controls,target,scratch):
 n=len(controls)
 if n==0:return [('X',target)]
 if n==1:return [('CX',controls[0],target)]
 if n==2:return [('CCX',controls[0],controls[1],target)]
 assert len(scratch)>=n-2
 chain=[('CCX',controls[0],controls[1],scratch[0])]
 for i in range(2,n-1):
  chain.append(('CCX',scratch[i-2],controls[i],scratch[i-1]))
 return chain+[('CCX',scratch[n-3],controls[-1],target)]+chain[::-1]

def generate(q):
 if not 3<=q<=6:raise ValueError('bounded exact ANF synthesis only q3..q6')
 n,w=q+3,q+1;c=coefficients(q)
 values=[affine(q,k&7,k>>3,c) for k in range(1<<n)]
 inputs=list(range(n));outputs=list(range(n,n+w))
 scratch=list(range(n+w,n+w+n-2))
 gates=[];degrees=collections.Counter()
 for outbit,target in enumerate(outputs):
  anf=[(v>>outbit)&1 for v in values]
  for bit in range(n):
   for mask in range(1<<n):
    if mask&(1<<bit):anf[mask]^=anf[mask^(1<<bit)]
  for mask,enabled in enumerate(anf):
   if enabled:
    controls=[inputs[b] for b in range(n) if mask&(1<<b)]
    degrees[len(controls)]+=1
    gates+=mcx(controls,target,scratch)
 resources={'input_bits':n,'output_bits':w,'clean_scratch':len(scratch),
  'total_wires':n+w+len(scratch),
  'monomial_degree_counts':dict(degrees),
  'exact_nonzero_monomials':sum(degrees.values()),
  'construction':'full affine-seed Boolean ANF; exponential in q'}
 return gates,c,resources

def execute(value,gates):
 for op,*w in gates:
  if op=='X':value^=1<<w[0]
  elif op=='CX':value^=((value>>w[0])&1)<<w[1]
  elif op=='CCX':value^=(((value>>w[0])&1)&((value>>w[1])&1))<<w[2]
  else:raise ValueError(op)
 return value

def test(q,gates,coeff):
 rng=random.Random(162+q);cases=0;n=q+3;mask=(1<<(q+1))-1
 for segment in range(8):
  for offset in range(1<<q):
   answer=affine(q,segment,offset,coeff)
   for target in (0,mask,rng.randrange(mask+1)):
    before=segment|(offset<<3)|(target<<n)
    expected=segment|(offset<<3)|((target^answer)<<n)
    actual=execute(before,gates)
    assert actual==expected,(q,segment,offset,target,answer,actual^expected)
    assert execute(actual,reversed(gates))==before
    assert execute(actual,gates)==before
    cases+=1
 return cases

def make_case(q):
 gates,c,resources=generate(q)
 cases=test(q,gates,c)
 counts=collections.Counter(op for op,*_ in gates)
 return {'q':q,'gate_count':dict(counts),
  'scratch':resources['clean_scratch'],
  'total_wires':resources['total_wires'],'cases':cases,
  'resources':resources}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--q',type=int,default=4,choices=(3,4,5,6))
 p.add_argument('--baseline',type=Path,
  default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,
  default=Path('competition/k162/results/direct_anf.json'))
 p.add_argument('--selftest',action='store_true')
 p.add_argument('--scaling',action='store_true')
 a=p.parse_args()
 small=make_case(3)
 assert small['gate_count']['CCX']==301 and small['scratch']==4
 print('K162_SELFTEST PASS exact reversible XOR seed, arbitrary targets, clean scratch',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 widths=sorted({3,4,5,a.q} if a.scaling else {a.q})
 rows=[small if q==3 else make_case(q) for q in widths]
 for row in rows:
  ct=row['gate_count']
  print('K162_CASE',json.dumps({'q':row['q'],'CCX':ct['CCX'],
   'CX':ct.get('CX',0),'X':ct.get('X',0),'scratch':row['scratch'],
   'total_wires':row['total_wires'],'tested_cases':row['cases']}),flush=True)
 result={'status':'BOUNDED_COHERENT_DIRECT_ANF_INTERPOLATION_NOT_HELIOS',
  'pinned_sha256':sha,'cases':rows,
  'compare_K161_q4':{'CCX':7208,'scratch':24,'total_wires':36},
  'warnings':['Correct for bounded piecewise-affine seed only, not Q14 Newton pipeline.',
   'ANF direct lookup has exponential size in selector+offset; q14 probably prohibitively costly.',
   'K157 mid-circuit measurement not needed: every MCX scratch chain uncomputed.',
   '12 scratch nominally available in K151 is not proof that all Newton operations fit 62.',
   'No optimized synthesis, Kickmix transpilation or official verification.']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+'\n')
 row=next(r for r in rows if r['q']==a.q)
 ct=row['gate_count']
 print('K162_RESULT',json.dumps({'q':a.q,'CCX':ct['CCX'],
  'CX':ct.get('CX',0),'scratch':row['scratch'],
  'total_wires':row['total_wires'],'tested_cases':row['cases'],
  'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
