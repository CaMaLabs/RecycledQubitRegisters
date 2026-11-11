#!/usr/bin/env python3
"""K136: algebraic-degree lower-bound screen for K135 repeated motifs.

Read-only source proof, NOT a new generic synthesis/optimizer. Every isolated
X/CX/CCX motif is interpreted as a Boolean reversible mapping on independent
input wires. ANF degree of any output after k Toffolis <= 2**k, because
affine gates never raise degree and a Toffoli can at most double it.
Consequently ceil(log2(max_output_degree)) Toffolis are NECESSARY for any
exact X/CX/CCX implementation of the same full mapping. This proof does not
cover measurement-based circuits, altered work interfaces, native multi-qubit
gates or approximations.

A degree bound equal to original CCX count rules out an exact reduction for
that isolated template under this gate set, irrespective of periodic lookup.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
def parse(s):
 t=s.strip().split()
 if not t or t[0] not in ('X','CX','CCX') or len(t)!={'X':2,'CX':3,'CCX':4}[t[0]]:return None
 if any(not q.startswith('q') or not q[1:].isdigit() for q in t[1:]):return None
 wires=tuple(map(lambda q:int(q[1:]),t[1:]))
 if len(set(wires))!=len(wires):return None
 return t[0],wires
def pxor(a,b):return a^b
def pmul(a,b,limit):
 if len(a)*len(b)>limit*20:raise OverflowError('ANF expansion budget')
 out=set()
 for x in a:
  for y in b:
   m=x|y
   if m in out:out.remove(m)
   else:out.add(m)
   if len(out)>limit:raise OverflowError('ANF monomial budget')
 return out
def evaluate(lines,max_monomials):
 gs=[parse(s) for s in lines]
 if any(x is None for x in gs):raise ValueError('unsupported gate within motif')
 wires=sorted(set(q for _,qs in gs for q in qs))
 names={q:i for i,q in enumerate(wires)}
 # Each monomial is represented by a bitmask of input variable indices.
 state={q:{1<<names[q]} for q in wires}
 for op,qs in gs:
  if op=='X':state[qs[0]]^={0}
  elif op=='CX':state[qs[1]]=pxor(state[qs[1]],state[qs[0]])
  else:
   t=qs[2]
   state[t]=pxor(state[t],pmul(state[qs[0]],state[qs[1]],max_monomials))
 max_degree=max((m.bit_count() for poly in state.values() for m in poly),default=0)
 original=sum(op=='CCX' for op,_ in gs)
 lower=(max_degree-1).bit_length() if max_degree>1 else 0
 return {'actual_template_wire_count':len(wires),'original_ccx':original,
   'maximum_anf_degree':max_degree,'degree_based_ccx_lower_bound':lower,
   'degree_bound_matches_original_ccx':lower==original,
   'max_monomials_per_output':max(len(x) for x in state.values()),
   'remaining_ccx_saving_not_excluded_by_degree':original-lower}
def selftest():
 assert evaluate(['CCX q0 q1 q2'],1000)['degree_based_ccx_lower_bound']==1
 x=['CCX q0 q1 q2','CCX q2 q3 q4']
 assert evaluate(x,1000)['degree_based_ccx_lower_bound']==2
 assert evaluate(['CX q0 q1','CX q1 q2'],1000)['degree_based_ccx_lower_bound']==0
 print('K136_SELFTEST PASS ANF degree and necessary CCX gate bound',flush=True)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
 ap.add_argument('--k135',type=Path,default=Path('competition/k135/results/periodic_carry_motif_screen.json'))
 ap.add_argument('--out',type=Path,default=Path('competition/k136/results/motif_degree_lower_bounds.json'))
 ap.add_argument('--max-monomials',type=int,default=20000)
 a=ap.parse_args();selftest()
 raw=a.baseline.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PIN:raise SystemExit('baseline SHA mismatch')
 lines=raw.decode().splitlines()
 prior=json.loads(a.k135.read_text())
 if prior.get('baseline_sha256')!=PIN:raise SystemExit('K135 result baseline digest mismatch')
 families=prior['top_families']
 rows=[]
 for i,f in enumerate(families):
  where=f['locations'][0];start,end=where['start'],where['end']
  try:
   proof=evaluate(lines[start-1:end],a.max_monomials)
   row={'family_rank':i+1,'length':f['length'],
    'copies_nonoverlap':f['repeated_copies'],
    'start_line':start,'end_line':end,'source_ccx_across_copies':f['source_ccx_across_copies'],
    **proof}
  except (OverflowError,ValueError) as exc:
   row={'family_rank':i+1,'start_line':start,'status':'NOT_PROVED','reason':str(exc)}
  rows.append(row)
  print('K136_FAMILY',json.dumps(row),flush=True)
 proved=[r for r in rows if 'degree_based_ccx_lower_bound' in r]
 locked=[r for r in proved if r['degree_bound_matches_original_ccx']]
 result={'experiment':'K136','status':'ANF_LOWER_BOUND_SCREEN',
  'baseline_sha256':PIN,'families_from_k135':len(families),
  'families_proved':len(proved),'families_lower_bound_tight':len(locked),
  'rows':rows,
  'caveats':['Proof applies to full independent-wire Boolean mapping restricted to X/CX/CCX.',
   'The lower bound is necessary, not sufficient, and is often weak.',
   'No proof of a carry function or periodic table advantage was made.',
   'Overlapping families cannot have their source counts summed.',
   'Measurement-assisted or phase-based rewrites fall outside this proof.',
   'No official verifier or score improvement has been claimed.']}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+'\n')
 print('K136_RESULT',json.dumps({'status':result['status'],
 'families_proved':len(proved),'families_lower_bound_tight':len(locked),
 'out':str(a.out)}),flush=True)
if __name__=='__main__':main()
