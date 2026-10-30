#!/usr/bin/env python3
"""Dependency-free N35 Boolean screening; CPU only, no QPU or native compilation."""
import json,math,random,itertools
from fractions import Fraction
N=35; WIDTH=6
def fib_product_probability(n):
    a,b=0,1; z=1
    for _ in range(n):
        a,b=b,a+b; z*=a
    return Fraction(1,z)
def no_triangles(xs):
    s=sorted(xs)
    return all(s[i]+s[i+1]<=s[i+2] for i in range(len(s)-2))
def bit(y,i): return (y>>i)&1
def ge35_factored(y):
    return bit(y,5)&(bit(y,4)|bit(y,3)|bit(y,2)|(bit(y,1)&bit(y,0)))
def anf_coeff(truth,n=6):
    coefficients=list(truth)
    for i in range(n):
        for mask in range(1<<n):
            if mask&(1<<i): coefficients[mask]^=coefficients[mask^(1<<i)]
    return coefficients
def terms(anf): return [i for i,v in enumerate(anf) if v]
def eval_anf(m,y):
    return (sum(1 for term in m if (y&term)==term)&1)
def modadd_truth(y,k,enable):
    return ((y+k)%N if enable and y<N else y)
def test():
    rng=random.Random(20261030); mc=[]
    for n in (3,4,5,6):
        trials=100000
        hits=sum(no_triangles([rng.random() for _ in range(n)]) for _ in range(trials))
        p=float(fib_product_probability(n)); stderr=math.sqrt(p*(1-p)/trials)
        passed=abs(hits/trials-p)<=max(5*stderr,1/trials)
        mc.append(dict(n=n,exact=str(fib_product_probability(n)),hits=hits,trials=trials,estimated=hits/trials,pass_check=passed))
        assert passed
    assert all(ge35_factored(y)==int(y>=N) for y in range(64))
    valid_anf=terms(anf_coeff([int(y<N) for y in range(64)]))
    assert all(eval_anf(valid_anf,y)==int(y<N) for y in range(64))
    wrap=[]; evaluated=0
    for k in range(1,N):
        old=[int(y<N and y+k>=N) for y in range(64)]
        masks=terms(anf_coeff(old))
        assert all(eval_anf(masks,y)==old[y] for y in range(64))
        for en,y in itertools.product((0,1),range(64)):
            out=modadd_truth(y,k,en)
            assert out==(y if not en or y>=N else (y+k)%N)
            evaluated+=1
        wrap.append(dict(k=k,threshold=N-k,anf_monomials=len(masks),max_degree=max((x.bit_count() for x in masks),default=0)))
    for p in range(2,36):
        for q in range(2,36):
            if p*q==N: assert p in (5,7) and q in (5,7)
    return dict(success=True,scope='classical exact truth tables/ANF; no quantum gates',
        fibonacci_samples=mc,ge35_factored_all_64=True,valid_predicate_anf_masks=valid_anf,
        wrap_k_cases=34*64,controlled_modadd_cases=evaluated,wrap_anf_summaries=wrap,
        clean_or_dirty_ancilla_quantum_proof=False,source_gate_count_change_verified=False,
        native_fez_compiles=0,qpu_jobs=0,fibonacci_RSA_pruning_proven=False)
if __name__=='__main__':
    result=test()
    with open('qrr_n35_next_tests_results.json','w') as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
