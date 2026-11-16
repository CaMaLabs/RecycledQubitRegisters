#!/usr/bin/env python3
"""K164 exact carry-aware offset cofactor XOR oracle.
Offset split into upper and lower blocks. Carry/rounding is represented in
the cofactor truth tables, NOT a streamed arithmetic carry register.
Bounded Q3-Q6 verification only; NOT full Helios.
"""
import argparse, collections, hashlib, json, math, random
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def coefficients(q):
 S=1<<q; values=[]
 for s in range(8):
  if s<4: m0,m1=1+s/4,1+(s+1)/4
  else: m0,m1=2+2*(s-4)/4,2+2*(s-3)/4
  values.append((round(S/math.sqrt(m0)),round(S*(1/math.sqrt(m0)-1/math.sqrt(m1))/(m1-m0))))
 return values

def expected(q,s,offset,coeff):
 a,b=coeff[s]
 return (a-((b*offset+(1<<(q-1)))>>q))&((1<<(q+1))-1)

def mcx(controls,target,anc):
 n=len(controls)
 if n==0:return [('X',target)]
 if n==1:return [('CX',controls[0],target)]
 if n==2:return [('CCX',controls[0],controls[1],target)]
 assert len(anc)>=n-2 and not (set(controls)&(set(anc)|{target}))
 chain=[('CCX',controls[0],controls[1],anc[0])]
 for j in range(2,n-1):chain.append(('CCX',anc[j-2],controls[j],anc[j-1]))
 return chain+[('CCX',anc[n-3],controls[-1],target)]+chain[::-1]

def anf(words,width):
 terms=collections.defaultdict(list)
 for bit in range(max(words).bit_length()):
  values=[(v>>bit)&1 for v in words]
  for j in range(width):
   for m in range(1<<width):
    if m&(1<<j):values[m]^=values[m^(1<<j)]
  for m,present in enumerate(values):
   if present:terms[m].append(bit)
 return terms

def synth(q,low):
 assert 3<=q<=8 and 1<=low<q
 high=q-low+3;n=q+3;w=q+1
 input_bits=list(range(n));lowbits=input_bits[3:3+low]
 highbits=input_bits[:3]+input_bits[3+low:]
 assert len(highbits)==high
 outputs=list(range(n,n+w))
 anc=list(range(n+w,n+w+max(high-2,low-1,0)))
 highflag=n+w+len(anc);term=highflag+1
 c=coefficients(q);g=[];active_high=active_terms=0
 for upper in range(1<<high):
  segment=upper&7;upper_offset=upper>>3
  words=[expected(q,segment,(upper_offset<<low)|lo,c) for lo in range(1<<low)]
  polys=anf(words,low)
  if not polys:continue
  toggles=[('X',highbits[j]) for j in range(high) if not ((upper>>j)&1)]
  g+=toggles+mcx(highbits,highflag,anc)+toggles[::-1]
  active_high+=1
  for mask,bits in polys.items():
   controls=[lowbits[j] for j in range(low) if (mask>>j)&1]
   active_terms+=1
   if not controls:g += [('CX',highflag,outputs[b]) for b in bits]
   else:
    g+=mcx([highflag]+controls,term,anc)
    g += [('CX',term,outputs[b]) for b in bits]
    g+=mcx([highflag]+controls,term,anc)
  g+=toggles+mcx(highbits,highflag,anc)+toggles[::-1]
 return g,c,{'input_bits':n,'output_bits':w,'low_chunk_bits':low,
  'upper_conditional_bits':high,'scratch':len(anc)+2,
  'total_wires':term+1,'high_cofactors':active_high,
  'shared_low_terms':active_terms,
  'carry_semantics':'exact rounding/carry in cofactor truth tables (no carried arithmetic register)'}

def execute(v,g):
 for op,*a in g:
  if op=='X':v^=1<<a[0]
  elif op=='CX':v^=((v>>a[0])&1)<<a[1]
  elif op=='CCX':v^=(((v>>a[0])&1)&((v>>a[1])&1))<<a[2]
  else:raise ValueError(op)
 return v

def check(q,low):
 g,c,res=synth(q,low);rng=random.Random(164+q*10+low)
 n=q+3;mask=(1<<(q+1))-1;cases=0
 for seg in range(8):
  for off in range(1<<q):
   val=expected(q,seg,off,c)
   for z in (0,mask,rng.randrange(mask+1)):
    before=seg|(off<<3)|(z<<n)
    want=seg|(off<<3)|((z^val)<<n)
    after=execute(before,g)
    assert after==want,(q,low,seg,off,z,val,hex(after^want))
    assert execute(after,g)==before
    assert execute(after,reversed(g))==before
    cases+=1
 ct=collections.Counter(op for op,*_ in g)
 return {'q':q,'low':low,'CCX':ct['CCX'],'CX':ct['CX'],'X':ct['X'],
  'scratch':res['scratch'],'total_wires':res['total_wires'],
  'tested_cases':cases,'resources':res}

def main():
 p=argparse.ArgumentParser()
 p.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 p.add_argument('--out',type=Path,default=Path('competition/k164/results/cofactor.json'))
 p.add_argument('--selftest',action='store_true')
 p.add_argument('--scaling',action='store_true')
 a=p.parse_args()
 first=check(3,1)
 assert (first['CCX'],first['scratch'],first['tested_cases'])==(450,5,192)
 print('K164_SELFTEST PASS exact rounded cofactor, arbitrary XOR targets and clean scratch',flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit('PINNED_BASELINE_MISMATCH '+sha)
 widths=[(3,1),(4,2),(5,2),(6,3)] if a.scaling else [(4,2)]
 rows=[first if (q,lo)==(3,1) else check(q,lo) for q,lo in widths]
 for row in rows:print('K164_CASE',json.dumps(row),flush=True)
 result={'status':'BOUNDED_CARRY_AWARE_CHUNK_COFACTOR_NOT_STREAMING_MULTIPLIER',
  'pinned_sha256':sha,'rows':rows,
  'q14_estimate':{'low':7,'high_controls':10,'clean_scratch':10,
   'warning':'1024 high groups and 128 low inputs each: exponential gates; not synthesized'},
  'limitations':['Exact carry handled through cofactor truth tables, not physical carry propagation',
   'No 14-bit oracle or full Helios circuit',
   'K157 measurement-assisted carry cleanup not integrated',
   'No official verification or leaderboard score gain']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K164_RESULT',json.dumps({'tested_widths':[row['q'] for row in rows],
  'q14_scratch_projection':10,'full_helios_candidate':False,'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
