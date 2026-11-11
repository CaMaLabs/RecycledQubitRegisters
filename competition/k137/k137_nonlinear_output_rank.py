#!/usr/bin/env python3
"""K137: multiplicative-complexity lower bound via nonlinear-output rank.

For an X/CX/CCX circuit acting on independent Boolean input wires, write each
output in algebraic normal form (ANF). Drop degree-0 and degree-1 monomials,
then calculate the GF(2) rank of the output vectors. An X/CX gate cannot
increase this rank. Each CCX introduces at most one new nonlinear polynomial
(the product of its two current controls), so the rank is a lower bound on
the number of CCX gates required to implement the full reversible mapping
using X/CX/CCX, even with clean initialized scratch that is restored.

This tightens K136's weaker max-degree bound on its existing 20 family
representatives. No synthesis, circuit rewrite or Kaggle verifier claim.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
def parse(source):
 t=source.strip().split()
 if not t or t[0] not in ('X','CX','CCX') or len(t)!=dict(X=2,CX=3,CCX=4)[t[0]]:
  raise ValueError('not an X/CX/CCX instruction: '+source.strip())
 if any(not x.startswith('q') or not x[1:].isdigit() for x in t[1:]):
  raise ValueError('bad qubit in '+source.strip())
 wires=tuple(int(x[1:]) for x in t[1:])
 if len(set(wires))!=len(wires):raise ValueError('repeated wire in '+source.strip())
 return t[0],wires

def prod(a,b,budget):
 if len(a)*len(b)>budget*32:raise OverflowError('ANF product too large')
 res=set()
 for x in a:
  for y in b:
   z=x|y
   if z in res:res.remove(z)
   else:res.add(z)
   if len(res)>budget:raise OverflowError('ANF output too large')
 return res
def rank(vectors):
 basis={}
 for vec in vectors:
  v=set(vec)
  while v:
   pivot=max(v)
   if pivot in basis:v^=basis[pivot]
   else:basis[pivot]=v;break
 return len(basis)
def evaluate(source,budget=20000):
 gates=[parse(line) for line in source]
 wires=sorted({x for _,qs in gates for x in qs})
 names={q:1<<i for i,q in enumerate(wires)}
 state={q:{names[q]} for q in wires}
 for op,qs in gates:
  if op=='X':state[qs[0]]^={0}
  elif op=='CX':state[qs[1]]^=state[qs[0]]
  elif op=='CCX':
   c=prod(state[qs[0]],state[qs[1]],budget)
   state[qs[2]]^=c
 nonlinear=[{v for v in state[q] if v.bit_count()>=2} for q in wires]
 output_rank=rank(nonlinear)
 ccx=sum(op=='CCX' for op,_ in gates)
 maxdeg=max((m.bit_count() for polynomial in state.values() for m in polynomial),default=0)
 degree_lb=(maxdeg-1).bit_length() if maxdeg>1 else 0
 bound=max(degree_lb,output_rank)
 return {'wire_count':len(wires),'original_ccx':ccx,
  'maximum_anf_degree':maxdeg,'degree_lower_bound':degree_lb,
  'nonlinear_output_rank_lower_bound':output_rank,
  'combined_ccx_lower_bound':bound,
  'remaining_ccx_gap':ccx-bound,
  'ccx_optimal_under_X_CX_CCX_if_tight':bound==ccx,
  'nonlinear_output_wires':sum(bool(poly) for poly in nonlinear),
  'nonlinear_output_monomials':len(set().union(*nonlinear))}
def selftest():
 a=evaluate(['CCX q0 q1 q2'])
 assert a['nonlinear_output_rank_lower_bound']==1
 b=evaluate(['CCX q0 q1 q2','CCX q2 q3 q4','CCX q4 q5 q6'])
 assert b['degree_lower_bound']==2 and b['nonlinear_output_rank_lower_bound']==3 and b['remaining_ccx_gap']==0
 c=evaluate(['CX q0 q1','CX q1 q2','X q3'])
 assert c['combined_ccx_lower_bound']==0
 # A product can be uncomputed and no nonlinear output remain; rank 0 is weak.
 d=evaluate(['CCX q0 q1 q2','CCX q0 q1 q2'])
 assert d['remaining_ccx_gap']==2
 print('K137_SELFTEST PASS nonlinear rank lower bound (chain degree gap tight)',flush=True)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 ap.add_argument('--k135',type=Path,default=Path('competition/k135/results/periodic_carry_motif_screen.json'))
 ap.add_argument('--out',type=Path,default=Path('competition/k137/results/nonlinear_rank_bounds.json'))
 ap.add_argument('--max-monomials',type=int,default=20000)
 a=ap.parse_args();selftest()
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit('pinned baseline digest mismatch: '+sha)
 data=json.loads(a.k135.read_text())
 if data.get('baseline_sha256')!=PIN:raise SystemExit('K135 input digest mismatch')
 lines=raw.decode().splitlines()
 rows=[]
 for idx,f in enumerate(data.get('top_families',[]),1):
  location=f['locations'][0];start,end=location['start'],location['end']
  try:
   proof=evaluate(lines[start-1:end],a.max_monomials)
   row={'family_rank':idx,'start_line':start,'end_line':end,
    'copies_nonoverlap':f['repeated_copies'],'source_ccx_across_copies':f['source_ccx_across_copies'],**proof}
  except (OverflowError,ValueError) as exc:
   row={'family_rank':idx,'start_line':start,'status':'INCONCLUSIVE','reason':str(exc)}
  rows.append(row)
  print('K137_FAMILY',json.dumps(row),flush=True)
 proved=[r for r in rows if 'remaining_ccx_gap' in r]
 tight=[r for r in proved if r['remaining_ccx_gap']==0]
 gaps=[r for r in proved if r['remaining_ccx_gap']>0]
 result={'experiment':'K137','status':'RANK_BOUND_COMPLETE',
  'baseline_sha256':PIN,'families_screened':len(rows),
  'families_proved':len(proved),'families_tight':len(tight),
  'families_with_unresolved_gap':len(gaps),'rows':rows,
  'method':'GF(2) rank of nonlinear ANF output components; combined with degree bound',
  'caveats':['Exact full independent-wire mapping only; not a general measurement-assisted lower bound.',
   'A nonzero gap is NOT proof that a better circuit exists.',
   'Physical sources and overlapping motif families are not additive resource savings.',
   'Does not infer a modulo-210 or binary-carry transition function.',
   'Official verifier and dynamic executed score are still required for any candidate.']}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K137_RESULT',json.dumps({k:result[k] for k in (
  'status','families_proved','families_tight','families_with_unresolved_gap')}),flush=True)
 print('K137_OUTPUT',str(a.out),flush=True)
if __name__=='__main__':main()
