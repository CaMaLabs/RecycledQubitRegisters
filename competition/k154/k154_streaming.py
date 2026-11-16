#!/usr/bin/env python3
"""K154 reversible 4-bit signed streamed product-and-round, and 14-bit Cuccaro adder.
Bounded arithmetic only. NOT a full-domain Helios candidate.
"""
import argparse,collections,hashlib,json,random
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def maj(c,b,a):return [('CX',a,b),('CX',a,c),('CCX',c,b,a)]
def uma(c,b,a):return [('CCX',c,b,a),('CX',a,c),('CX',c,b)]
def add(a,b,carry):
 assert len(a)==len(b) and not(set(a)&set(b)) and carry not in a+b
 g=[]
 for i in range(len(a)):g+=maj(carry if i==0 else a[i-1],b[i],a[i])
 for i in reversed(range(len(a))):g+=uma(carry if i==0 else a[i-1],b[i],a[i])
 return g
def controlled_x(controls,target,anc):
 n=len(controls)
 if n==0:return [('X',target)]
 if n==1:return [('CX',controls[0],target)]
 if n==2:return [('CCX',*controls,target)]
 if len(anc)<n-2:raise ValueError('insufficient clean ancillas')
 chain=[('CCX',controls[0],controls[1],anc[0])]
 for j in range(2,n-1):chain.append(('CCX',anc[j-2],controls[j],anc[j-1]))
 return chain+[('CCX',anc[n-3],controls[-1],target)]+list(reversed(chain))
def run(v,g):
 for op,*a in g:
  if op=='X':v^=1<<a[0]
  elif op=='CX':v^=((v>>a[0])&1)<<a[1]
  elif op=='CCX':v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
  else:raise AssertionError(op)
 return v
def make4():
 # r=q0..3 signed, y=q4..7 unsigned, output=q8..11
 # product=q12..19, operand=q20..27, carry=q28
 r=list(range(4));y=list(range(4,8));out=list(range(8,12))
 product=list(range(12,20));operand=list(range(20,28));carry=28
 rows=[]
 for i in range(4):
  prep=[('CCX',y[i],r[min(j-i,3)],operand[j]) for j in range(i,8)]
  rows+=prep+add(operand,product,carry)+list(reversed(prep))
 bias=[]
 for j in range(7,4,-1):
  bias+=controlled_x(product[4:j],product[j],operand)
 bias.append(('X',product[4]))
 write=[('CX',product[5],out[0]),('CX',product[6],out[1]),
        ('CX',product[7],out[2]),('CX',product[7],out[3])]
 return rows+bias+write+list(reversed(bias))+list(reversed(rows))
def signed4(v):return v-16 if v&8 else v
def verify4(g):
 rng=random.Random(154);tests=0
 for r in range(16):
  for y in range(16):
   answer=((signed4(r)*y+16)//32)&15
   for d in (0,15,rng.randrange(16)):
    before=r|(y<<4)|(d<<8)
    after=run(before,g)
    assert after==r|(y<<4)|((d^answer)<<8),(r,y,d)
    assert run(after,g)==before,(r,y,d,'not involution')
    tests+=1
 return tests
def verify_add(n):
 A=list(range(n));B=list(range(n,2*n));c=2*n;g=add(A,B,c)
 tests=(1<<n)**2 if n<=4 else 500
 rng=random.Random(n)
 for t in range(tests):
  a,b=(t//(1<<n),t%(1<<n)) if n<=4 else (rng.randrange(1<<n),rng.randrange(1<<n))
  before=a|(b<<n);after=run(before,g)
  assert after==a|(((a+b)&((1<<n)-1))<<n)
  assert run(after,reversed(g))==before
 return {'width':n,'cases':tests,'CCX':2*n,'CX':4*n,'clean_carry':True}
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k154/results/streaming.json'))
 p.add_argument('--selftest',action='store_true')
 a=p.parse_args()
 for n in (1,2,3,4):verify_add(n)
 g=make4();cases=verify4(g)
 print('K154_SELFTEST PASS 4-bit signed streaming, exact rounding, arbitrary XOR target and clean scratch',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 c=collections.Counter(op for op,*_ in g)
 resource={'data_bits':12,'scratch_bits':17,'total_declared_qubits':29,
   'product_scratch':8,'operand_scratch':8,'carry_scratch':1,
   'helio_compact_50_plus_stream_scratch':67,'helios_budget':62}
 report={'status':'BOUNDED_GATE_LEVEL_STREAMING_PROTOTYPE_NOT_HELIOS',
  'source_sha256':sha,'signed_r_bits':4,'unsigned_y_bits':4,
  'rounding':'delta=floor((signed_r*y+16)/32) mod 16',
  'basis_cases':cases,'counts':dict(c),'resource':resource,
  'adder_width14':verify_add(14),
  'warnings':['NOT the K153 16-bit residual multiplied by Q14 estimate',
    'The bounded demo uses 17 scratch vs 12 nominal free in K151',
    'No full input-domain implementation or official score check',
    'Cuccaro adder improves K153 reference; complete multiplication/cleanup dominates']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+'\n')
 print('K154_RESULT',json.dumps({'ccx':c['CCX'],'cx':c['CX'],
  'scratch':resource['scratch_bits'],'basis_cases':cases,
  'cuccaro_14bit_CCX':28,'cuccaro_14bit_CX':56,
  'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
