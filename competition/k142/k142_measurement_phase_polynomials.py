#!/usr/bin/env python3
"""K142 read-only phase-polynomial audit of immediate HMR feedback networks.

Exact local correction: (-1)^(b*f(q)), f(q) = XOR of Z monomials
and CZ pair-products. Does not infer quantum channel equivalence or
scored Toffoli/rotation savings. Does not alter the circuit.
"""
import argparse, collections, hashlib, itertools, json, re
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
Q=re.compile(r'^q([0-9]+)$');B=re.compile(r'^b([0-9]+)$')
def parse(s):
 t=s.strip().split()
 return t if t and not t[0].startswith(('#','//')) else None
def qs(t):return [int(q[1:]) for q in t[1:] if Q.fullmatch(q)]
def guard(t):
 tlo=[z.lower() for z in t]
 if 'if' not in tlo:return None
 i=tlo.index('if')
 return t[i+1] if i+1<len(t) and B.fullmatch(t[i+1]) else 'INVALID'
def polynomial(seq):
 lin=set();pairs=set()
 for t in seq:
  q=qs(t);op=t[0].upper()
  if op=='Z' and len(q)==1:
   value=q[0];s=lin
  elif op=='CZ' and len(q)==2 and q[0]!=q[1]:
   value=tuple(sorted(q));s=pairs
  else:raise ValueError('unknown phase instruction '+str(t))
  if value in s:s.remove(value)
  else:s.add(value)
 return lin,pairs
def rank(rows):
 basis={}
 for r in rows:
  while r:
   i=r.bit_length()-1
   if i in basis:r^=basis[i]
   else:basis[i]=r;break
 return len(basis)
def canonical(lin,pairs,max_wires=7):
 w=sorted(set(lin)|{q for pair in pairs for q in pair})
 if len(w)>max_wires:return None
 best=None
 for perm in itertools.permutations(w):
  ix={x:i for i,x in enumerate(perm)}
  l=sum(1<<ix[x] for x in lin);p=0
  for x,y in pairs:
   a,b=sorted((ix[x],ix[y]))
   p|=1<<(b*(b-1)//2+a)
  key=(l,p)
  if best is None or key<best:best=key
 return (len(w),*best)
def stats(lin,pairs):
 w=sorted(set(lin)|{x for p in pairs for x in p});ix={x:i for i,x in enumerate(w)}
 rows=[0]*len(w)
 for a,b in pairs:
  u,v=ix[a],ix[b];rows[u]^=1<<v;rows[v]^=1<<u
 return {'wires':w,'quadratic_rank':rank(rows),'degrees':sorted([r.bit_count() for r in rows],reverse=True)}
def truth_check(seq,lin,pairs):
 w=sorted({x for t in seq for x in qs(t)})
 if len(w)>12:return None
 for bits in range(1<<len(w)):
  val={x:(bits>>i)&1 for i,x in enumerate(w)}
  direct=sum(val[qs(t)[0]] if t[0].upper()=='Z' else
    val[qs(t)[0]]*val[qs(t)[1]] for t in seq)&1
  reduced=(sum(val[x] for x in lin)+sum(val[x]*val[y] for x,y in pairs))&1
  if direct!=reduced:return False
 return True
def biclique(pairs):
 w=sorted({x for p in pairs for x in p})
 if len(w)>9:return None
 best=None
 for n in range(2,len(w)-1):
  for aa in itertools.combinations(w,n):
   a=set(aa);b={x for x in w if x not in a and all(tuple(sorted((x,y))) in pairs for y in a)}
   if len(b)<2:continue
   value=len(a)*len(b)
   if best is None or value>best['cross_edges']:
    best={'left':sorted(a),'right':sorted(b),'cross_edges':value,
      'other_quadratic_edges':len(pairs)-value}
 return best
def collect(lines):
 ops=[parse(s) for s in lines];out=[]
 for i,t in enumerate(ops):
  if not t or t[0].upper()!='HMR':continue
  bit=[x for x in t[1:] if B.fullmatch(x)]
  if len(bit)!=1:continue
  seq=[];j=i+1
  while j<len(ops):
   z=ops[j]
   if z is None:j+=1;continue
   if z[0].upper() not in ('Z','CZ') or guard(z)!=bit[0]:break
   seq.append(z);j+=1
  if not seq:continue
  lin,pairs=polynomial(seq)
  result={'hmr_line':i+1,'correction_start_line':i+2,
   'correction_end_line':j,'bit':bit[0],
   'source_z':sum(s[0].upper()=='Z' for s in seq),
   'source_cz':sum(s[0].upper()=='CZ' for s in seq),
   'net_z':len(lin),'net_cz':len(pairs),
   'linear_qubits':sorted(lin),'quadratic_pairs':[list(x) for x in sorted(pairs)],
   'truth_table_exact':truth_check(seq,lin,pairs),
   'canonical_phase_graph':canonical(lin,pairs),
   'biclique':biclique(pairs),**stats(lin,pairs)}
  out.append(result)
 return out
def selftest():
 seq=[['Z','q0'],['Z','q0'],['CZ','q0','q1'],['CZ','q1','q0'],['CZ','q1','q2']]
 l,p=polynomial(seq)
 assert l==set() and p=={(1,2)} and truth_check(seq,l,p)
 a,b=polynomial([['Z','q0'],['CZ','q0','q1'],['CZ','q0','q2']])
 c,d=polynomial([['Z','q8'],['CZ','q8','q9'],['CZ','q8','q10']])
 assert canonical(a,b)==canonical(c,d)
 assert stats(set(),{(0,1),(1,2)})['quadratic_rank']==2
 print('K142_SELFTEST PASS parity cancellation, truth table, renaming',flush=True)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 ap.add_argument('--out',type=Path,default=Path('competition/k142/results/correction_phase_polynomials.json'))
 ap.add_argument('--focus',default='21606,25612')
 ap.add_argument('--top',type=int,default=20)
 args=ap.parse_args();selftest()
 raw=args.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit('Pinned baseline SHA mismatch: '+sha)
 rows=collect(raw.decode().splitlines())
 shapes=collections.Counter((r['source_z'],r['source_cz']) for r in rows)
 graph_groups=collections.defaultdict(list)
 for r in rows:
  k=r['canonical_phase_graph']
  if k is not None:graph_groups[tuple(k)].append(r['hmr_line'])
 for r in rows:
  k=r['canonical_phase_graph']
  r['renamed_equivalent_hmr_lines']=graph_groups[tuple(k)][:30] if k is not None else []
 focus={int(x) for x in args.focus.split(',') if x.strip()}
 found=[r for r in rows if r['hmr_line'] in focus]
 ranked=sorted((r for r in rows if r['source_z']+r['source_cz']>=3),
  key=lambda r:(-r['source_cz'],-r['source_z'],r['hmr_line']))
 report={'experiment':'K142','status':'READ_ONLY_LOCAL_PHASE_POLYNOMIAL',
 'baseline_sha256':sha,'feedback_blocks':len(rows),
 'shapes':[{'z':z,'cz':c,'count':v} for (z,c),v in sorted(shapes.items())],
 'focused_blocks':found,'top_multiterm_blocks':ranked[:args.top],
 'source_clifford_cancellations':sum(r['source_z']+r['source_cz']-r['net_z']-r['net_cz'] for r in rows),
 'limitations':['Only contiguous same-measurement-bit Z/CZ feedback is included.',
 'Earlier HMR channel and full circuit phase are not modeled.',
 'Wire-isomorphic graphs do not imply hardware cost reduction.',
 'Z/CZ cancellations are not direct reductions in the Toffoli/rotation score.',
 'No modified circuit, official verifier or leaderboard result.']}
 args.out.parent.mkdir(parents=True,exist_ok=True)
 args.out.write_text(json.dumps(report,indent=2)+'\n')
 print('K142_SUMMARY',json.dumps({'blocks':len(rows),'multi_term':len(ranked),
 'clifford_cancellations':report['source_clifford_cancellations']}),flush=True)
 for r in found:print('K142_FOCUS',json.dumps(r),flush=True)
 for r in ranked[:args.top]:print('K142_RANKED',json.dumps({'hmr_line':r['hmr_line'],
 'net_z':r['net_z'],'net_cz':r['net_cz'],'quadratic_rank':r['quadratic_rank'],
 'biclique':r['biclique']}),flush=True)
 print('K142_RESULT',json.dumps({'status':report['status'],'out':str(args.out)}),flush=True)
if __name__=='__main__':main()
