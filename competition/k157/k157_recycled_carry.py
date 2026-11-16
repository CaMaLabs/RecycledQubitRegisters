#!/usr/bin/env python3
"""K157 recycled first-carry workspace for 14-bit phase-correct measured adder.
A bounded/standalone exact-gate experiment, NOT a full Helios circuit.
"""
import argparse,collections,hashlib,json,random
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
def circuit(n):
 assert n>=4
 a=list(range(n));b=list(range(n,2*n));z=list(range(2*n,3*n))
 c=list(range(3*n,4*n-2))
 assert len(c)==n-2
 g=[('CCX',a[0],b[0],c[0])]
 for i in range(1,n-2):
  g += [('CCX',a[i],b[i],c[i]),('CX',a[i],b[i]),
        ('CCX',b[i],c[i-1],c[i]),('CX',a[i],b[i])]
 # Output bit1 before measuring/releasing first carry c1.
 g += [('CX',a[1],z[1]),('CX',b[1],z[1]),('CX',c[0],z[1]),
       ('HMR',c[0],'m1'),('CZ_IF',a[0],b[0],'m1')]
 # Reuse the clean physical c1 qubit for final carry c_(n-1).
 i=n-2
 g += [('CCX',a[i],b[i],c[0]),('CX',a[i],b[i]),
       ('CCX',b[i],c[i-1],c[0]),('CX',a[i],b[i])]
 for j in range(n):
  if j==1:continue
  g += [('CX',a[j],z[j]),('CX',b[j],z[j])]
  if j>=2:g.append(('CX',c[0] if j==n-1 else c[j-1],z[j]))
 # Descending X-measurement carry cleanup; predecessor remains coherent.
 for i in range(n-2,1,-1):
  q=c[0] if i==n-2 else c[i]
  bit='m'+str(i+1)
  g += [('HMR',q,bit),('CZ_IF',a[i],b[i],bit),
        ('CX_IF',a[i],b[i],bit),('CZ_IF',b[i],c[i-1],bit),
        ('CX_IF',a[i],b[i],bit)]
 # c1 was measured before reuse; recompute it to correct c2's phase,
 # then coherently uncompute it. Two additional CCX operations.
 g.append(('CCX',a[0],b[0],c[0]))
 g += [('HMR',c[1],'m2'),('CZ_IF',a[1],b[1],'m2'),
       ('CX_IF',a[1],b[1],'m2'),('CZ_IF',b[1],c[0],'m2'),
       ('CX_IF',a[1],b[1],'m2'),
       ('CCX',a[0],b[0],c[0])]
 return g

def run(v,ops,measurements):
 phase=0
 for op,*args in ops:
  if op=='CX':
   a,b=args;v^=((v>>a)&1)<<b
  elif op=='CCX':
   a,b,t=args;v^=(((v>>a)&1)&((v>>b)&1))<<t
  elif op=='HMR':
   q,name=args;phase^=measurements[name]&((v>>q)&1);v&=~(1<<q)
  elif op=='CZ_IF':
   a,b,name=args;phase^=measurements[name]&((v>>a)&1)&((v>>b)&1)
  elif op=='CX_IF':
   a,b,name=args
   if measurements[name]:v^=((v>>a)&1)<<b
  else:raise AssertionError(op)
 return v,phase

def test(n,exhaustive=False,random_count=500):
 ops=circuit(n);rng=random.Random(157+n);states=branches=0
 if exhaustive:
  states_iter=((a,b,z) for a in range(1<<n) for b in range(1<<n)
               for z in (0,(1<<n)-1))
 else:
  states_iter=((rng.randrange(1<<n),rng.randrange(1<<n),
                rng.randrange(1<<n)) for _ in range(random_count))
 for a,b,z in states_iter:
  initial=a|(b<<n)|(z<<(2*n))
  expect=a|(b<<n)|((z^((a+b)&((1<<n)-1)))<<(2*n))
  if exhaustive:branches_iter=range(1<<(n-1))
  else:branches_iter={0,(1<<(n-1))-1,
                      rng.randrange(1<<(n-1)),rng.randrange(1<<(n-1))}
  for bits in branches_iter:
   m={'m'+str(i):(bits>>(i-1))&1 for i in range(1,n)}
   value,phase=run(initial,ops,m)
   assert value==expect and phase==0,(n,a,b,z,bits,phase,value^expect)
   branches+=1
  states+=1
 gates=collections.Counter(g for g,*_ in ops)
 return {'width':n,'CCX':gates['CCX'],'CX':gates['CX'],
  'HMR':gates['HMR'],'conditional_CZ':gates['CZ_IF'],
  'conditional_CX':gates['CX_IF'],'carry_scratch':n-2,
  'standalone_width':4*n-2,'basis_states_tested':states,
  'measurement_branches_tested':branches,
  'proof':'EXACT_OUTPUT_AND_ZERO_PHASE_FOR_EACH_TESTED_BRANCH'}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,
                default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,
                default=Path('competition/k157/results/recycled_carry.json'))
 p.add_argument('--selftest',action='store_true')
 a=p.parse_args()
 small=[test(n,True) for n in (4,5,6)]
 for row in small:assert row['CCX']==2*row['width']-1
 print('K157_SELFTEST PASS exact arithmetic, X-branch phase and recycled-carry cleanup',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 large=test(14,False,500);rows=small+[large]
 for row in rows:print('K157_CASE',json.dumps(row),flush=True)
 report={'status':'EXACT_STANDALONE_RECYCLING_NOT_FULL_HELIOS',
         'pinned_sha256':sha,'rows':rows,'n14':large,
         'limits':['Only one standalone 14-bit XOR-adder, not the Newton multiplier.',
         'At n14 500 random input triples, at most 4 outcome branches each; not exhaustive.',
         'Conditional-CZ/CX Kickmix syntax and score not verified.',
         'The 12 free K151 registers cannot automatically be reassigned to a standalone 3-word adder.',
         'No full 22-bit Helios circuit/official verifier.']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+'\n')
 print('K157_RESULT',json.dumps({'n14_CCX':large['CCX'],
       'n14_carry_scratch':large['carry_scratch'],
       'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
