#!/usr/bin/env python3
"""K134: PTP fixed-increment periodicity falsification for Helios phase.

Tests a NEW mechanism, not fixed phase bucketing (K116): for x=r+kM,
ask whether theta(x+M)-theta(x) can be represented by ONE residue-based
increment independent of k, within verifier phase tolerance.

If impossible for any residue, a simple PTP residue-indexed *increment*
table cannot replace exact inverse-square-root arithmetic. This does not
exclude a quotient-dependent or hybrid interpolation circuit.
"""
import argparse, json, math
from pathlib import Path
MAX_X=3133452
TOL=2**-24

def phase(x):return 1/math.sqrt(x)
def phase_tolerance(x):return TOL/math.sqrt(x)
def increment(x,m):return phase(x+m)-phase(x)
def compatible(x,y,m):
    # Each increment is the difference between two phases, so the
    # cumulative permissible discrepancy is the sum of four tolerances.
    a=increment(x,m);b=increment(y,m)
    separation=abs((a-b+0.5)%1-0.5)
    budget=sum(phase_tolerance(v) for v in (x,x+m,y,y+m))
    return separation<=budget,separation,budget

def unit_input_count(m):
    # Inclusion-exclusion, avoiding an O(N) full-domain gcd scan.
    factors=[];k=m;p=2
    while p*p<=k:
        if k%p==0:
            factors.append(p)
            while k%p==0:k//=p
        p+=1
    if k>1:factors.append(k)
    count=0
    for mask in range(1<<len(factors)):
        prod=1;sign=1
        for i,f in enumerate(factors):
            if (mask>>i)&1:prod*=f;sign=-sign
        count+=sign*(MAX_X//prod)
    return count

def screen(m):
    x,y=1,1+m
    if y+m>MAX_X:return {'modulus':m,'status':'INSUFFICIENT_DOMAIN'}
    possible,sep,budget=compatible(x,y,m)
    units=sum(math.gcd(r,m)==1 for r in range(m))
    valid=unit_input_count(m)
    return {'modulus':m,'phi':units,'unit_fraction':units/m,
      'nonunit_fraction':1-units/m,'valid_unit_inputs':valid,
      'all_inputs_required':MAX_X,'witness_x':[x,y,y+m],
      'first_increment_turns':increment(x,m),
      'second_increment_turns':increment(y,m),
      'increment_modular_separation_turns':sep,
      'allowed_interval_overlap_budget_turns':budget,
      'separation_to_budget_ratio':sep/budget,
      'same_residue_fixed_increment_feasible':possible,
      'status':'NOT_REFUTED_BY_THIS_WITNESS' if possible else 'REFUTED_FIXED_INCREMENT'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--moduli',default='30,210,2310,30030')
    p.add_argument('--out',type=Path,default=Path('competition/k134/results/ptp_phase_periodicity.json'))
    args=p.parse_args();ms=[int(z.strip()) for z in args.moduli.split(',')]
    if not ms or any(m<=1 or m>MAX_X//2 for m in ms):p.error('bad moduli')
    rows=[screen(m) for m in ms]
    for row in rows:print('K134_MODULUS',json.dumps(row),flush=True)
    result={'experiment':'K134','status':'SCREEN_ONLY',
      'hypothesis':'PTP residue-indexed constant phase increments for x=r+kM',
      'rows':rows,
      'assumption':'Float calculations are reliable for these witnesses because every rejection gap vastly exceeds rounding noise.',
      'result_scope':'An incompatible pair of increments refutes a global constant-increment model for that modulus.',
      'not_tested':['Quotient-dependent increment table','Periodic corrections to an existing approximate circuit','An executable Kickmix candidate','Official score or verifier']}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print('K134_RESULT',json.dumps({'status':result['status'],'out':str(args.out)}),flush=True)
if __name__=='__main__':main()
