#!/usr/bin/env python3
"""CPU-only Fibonacci/borrowed-ancilla prerequisite tests. No QPU or native compilation."""
import itertools, json, math, random
from fractions import Fraction

def fibonacci(n):
    a,b=0,1
    for _ in range(n):
        a,b=b,a+b
        yield a

def triangle_free(seq):
    s=sorted(seq)
    return all(s[i]+s[i+1] <= s[i+2] for i in range(len(s)-2))

def exact(n):
    return Fraction(1, math.prod(fibonacci(n)))

def xor_into(s,i,j):
    s[j] ^= s[i]

def ccx_into(s,i,j,k):
    s[k] ^= s[i]&s[j]

def carry_test():
    # Wires a,b,c,t,carry; every operation self-inverse with phase +1.
    gates=[(xor_into,(0,3)), (xor_into,(1,3)),
           (ccx_into,(0,1,4)), (ccx_into,(2,3,4)),
           (xor_into,(2,3))]
    checked=0
    for a,b,c,d in itertools.product(range(2),repeat=4):
        s=[a,b,c,0,d]
        for f,idx in gates: f(s,*idx)
        assert s[:3]==[a,b,c]
        assert s[3]==a^b^c
        assert s[4]==d^((a&b)^(c&(a^b)))
        for f,idx in reversed(gates): f(s,*idx)
        assert s==[a,b,c,0,d]
        checked+=1
    return {'pass':True,'dirty_and_clean_cases':checked,
            'forward_gate_counts':{'cx':3,'ccx':2},
            'phase':'exact +1 by CX/CCX basis permutation',
            'scope':'one reversible carry cell, NOT controlled modular multiplication'}

def main():
    rng=random.Random(20261030)
    rows=[]
    for n in (3,4,5,6):
        trials=100000
        hits=sum(triangle_free([rng.random() for _ in range(n)]) for _ in range(trials))
        p=float(exact(n))
        sigma=math.sqrt(p*(1-p)/trials)
        assert abs(hits/trials-p)<=max(5*sigma,1/trials)
        rows.append({'n':n,'exact':str(exact(n)),'sample':hits/trials,
                     'trials':trials,'pass':True})
    # No valid implication from random-stick inequalities to factor candidates.
    assert 35%5==0 and not triangle_free([0.2,0.3,0.4])
    print(json.dumps({'success':True,'research_lead':'Chase Lunsford / CaMaLabs',
       'fibonacci':rows,'xor_carry':carry_test(),'rsa_pruning_certified':False,
       'n35_arithmetic_changed':False,'fez_native_compiles':0,'qpu_jobs':0},indent=2))

if __name__=='__main__': main()
