#!/usr/bin/env python3
"""Expanded base-d factor/product registers; exact structured simulation.

This retains P,Q,R, with digits,digits,2*digits carriers respectively.
The structured backend stores only occupied (p,q,r=p*q) or (p,q,r=0)
amplitudes. This is simulator sparsity, NOT removed physical product storage.
Arithmetic is an abstract block, not synthesized hardware pulses.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import numpy as np


class Layout:
    def __init__(self, levels, digits):
        if levels < 2 or digits < 1:
            raise ValueError('Require levels >= 2 and digits >= 1')
        self.levels, self.digits = levels, digits
        self.capacity = levels**digits

    def physical_digits(self, value):
        """Extend A117's [0,2,4,6,7,5,3,1] order for even dimensions.

        This is basis labeling only; no claim about pulse cost or phase fixing.
        Odd dimensions use identity labeling.
        """
        if not 0 <= value < self.capacity:
            raise ValueError('Value outside register')
        d = self.levels
        order = (list(range(0,d,2))+list(range(d-1,0,-2))
                 if d % 2 == 0 else list(range(d)))
        result = []
        for _ in range(self.digits):
            result.append(order[value % d])
            value //= d
        return result

    def decode(self, physical_digits):
        if len(physical_digits) != self.digits:
            raise ValueError('Wrong number of carrier digits')
        d = self.levels
        order = (list(range(0,d,2))+list(range(d-1,0,-2))
                 if d % 2 == 0 else list(range(d)))
        return sum(order.index(level)*d**j for j,level in enumerate(physical_digits))


class ExpandedRegisters:
    def __init__(self, n, levels=8, digits=2, max_factor=None,
                 max_stored_amplitudes=4_200_000):
        if n < 4 or levels < 2 or digits < 1 or max_stored_amplitudes < 1:
            raise ValueError('Invalid input or memory guard')
        if 2*digits*math.log2(levels) > math.log2(max_stored_amplitudes):
            raise ValueError('Structured state exceeds amplitude guard')
        self.n, self.layout = n, Layout(levels,digits)
        self.a = self.layout.capacity
        if n >= self.a**2:
            raise ValueError('Target exceeds product-register capacity')
        self.hi = min(self.a-1,n-1) if max_factor is None else max_factor
        if not 2 <= self.hi < min(self.a,n):
            raise ValueError('Invalid max-factor')
        self.width = self.hi-1
        start = time.perf_counter()
        indices = np.arange(self.a, dtype=np.int64)
        # Software compiles the multiplication/equality oracle by enumerating
        # the product table. This classical cost is reported, never hidden.
        self.products = indices[:,None]*indices[None,:]
        self.marked = self.products == n
        self.compilation_seconds = time.perf_counter()-start
        self.initial = np.zeros((self.a,self.a),complex)
        self.initial[2:self.hi+1,2:self.hi+1] = 1/self.width
        self.state = self.initial.copy()
        self.product_computed = False

    def reset(self):
        self.state = self.initial.copy()
        self.product_computed = False

    def multiply(self):
        if self.product_computed:
            raise ValueError('Structured multiply expects R=0')
        self.product_computed = True

    def uncompute(self):
        if not self.product_computed:
            raise ValueError('Uncompute expects R=p*q')
        self.product_computed = False

    def mark_product(self):
        if not self.product_computed:
            raise ValueError('Equality phase requires computed product')
        self.state[self.marked] *= -1

    def oracle(self):
        self.multiply()
        self.mark_product()
        self.uncompute()

    def diffuse(self):
        if self.product_computed:
            raise ValueError('Reflection requires clean product register')
        inner = self.state[2:self.hi+1,2:self.hi+1].sum()/self.width
        self.state *= -1
        self.state[2:self.hi+1,2:self.hi+1] += 2*inner/self.width

    def materialize(self, max_amplitudes=2_000_000):
        """For independent small-state verification only."""
        if self.a**4 > max_amplitudes:
            raise ValueError('Dense materialization exceeds guard')
        out = np.zeros((self.a,self.a,self.a**2),complex)
        p,q = np.indices((self.a,self.a))
        r = self.products if self.product_computed else np.zeros_like(p)
        out[p,q,r] = self.state
        return out

    def probability(self):
        return float(np.sum(np.abs(self.state[self.marked])**2))

    def run(self, iterations, shots=1000, seed=12345):
        if iterations < 0 or shots < 1:
            raise ValueError('Require iterations >= 0 and shots >= 1')
        start=time.perf_counter()
        self.reset()
        history=[self.probability()]
        for _ in range(iterations):
            self.oracle()
            self.diffuse()
            history.append(self.probability())
        norm=float(np.sum(np.abs(self.state)**2))
        assert abs(norm-1) < 1e-8
        # Sampling PQ before multiplying gives identical joint output statistics
        # because R is a deterministic computational-basis function of PQ.
        weights=np.abs(self.state.ravel())**2
        weights/=weights.sum()
        samples=np.random.default_rng(seed).choice(weights.size,size=shots,p=weights)
        accepted=Counter()
        for value in samples:
            p,q=divmod(int(value),self.a)
            if p*q == self.n:
                accepted[f'{p}*{q}']+=1
        theta=math.asin(math.sqrt(min(1,history[0])))
        prediction=math.sin((2*iterations+1)*theta)**2
        assert abs(history[-1]-prediction) < 1e-8
        d,m=self.layout.levels,self.layout.digits
        return {
            'N':self.n,'target_bits':self.n.bit_length(),
            'levels_per_qudit':d,'qudits_per_factor_register':m,
            'qudits_in_product_register':2*m,'total_physical_qudits_model':4*m,
            'factor_capacity':self.a,'candidate_range':[2,self.hi],
            'ordered_candidate_pairs':self.width**2,
            'product_capacity':self.a**2,
            'equivalent_binary_logical_qubits':4*m*math.log2(d),
            'iterations':iterations,'success_history':history,
            'accepted_shots':sum(accepted.values()),'shots':shots,
            'accepted_counts':dict(sorted(accepted.items())),
            'norm':norm,'product_register_clean':not self.product_computed,
            'statevector_amplitudes_stored':self.a**2,
            'statevector_bytes':self.state.nbytes,
            'dense_full_register_amplitudes':self.a**4,
            'dense_full_register_bytes':16*self.a**4,
            'simulator_oracle_compile_product_evaluations':self.a**2,
            'simulator_oracle_compile_seconds':self.compilation_seconds,
            'simulation_seconds':time.perf_counter()-start,
            'arithmetic_block_uses':2*iterations+1,
            'native_gate_count':None,
            'scope':'exact structured ideal simulation, retained logical P,Q,R',
            'coverage':'Both factors must fit; failure is not a primality proof.',
        }


def selftest():
    rng=np.random.default_rng(718)
    checks=0
    for d,m,n in [(2,3,35),(3,2,35),(4,2,143),(8,1,35),(16,1,143)]:
        ex=ExpandedRegisters(n,d,m)
        a=ex.a
        # A separate dense implementation establishes the arithmetic relation.
        ex.state=rng.normal(size=(a,a))+1j*rng.normal(size=(a,a))
        ex.state/=np.linalg.norm(ex.state)
        start=ex.materialize()
        ex.multiply()
        expected=np.zeros_like(start)
        for p in range(a):
            for q in range(a):
                expected[p,q]=np.roll(start[p,q],p*q)
        assert np.allclose(ex.materialize(),expected)
        ex.mark_product()
        expected[:,:,n]*=-1
        assert np.allclose(ex.materialize(),expected)
        ex.uncompute()
        back=np.empty_like(expected)
        for p in range(a):
            for q in range(a):
                back[p,q]=np.roll(expected[p,q],-p*q)
        assert np.allclose(ex.materialize(),back)
        dense_inner=np.vdot(ex.initial.ravel(),ex.state.ravel())
        expected_pq=2*dense_inner*ex.initial-ex.state
        ex.diffuse()
        assert np.allclose(ex.state,expected_pq)
        for p in range(a):
            assert ex.layout.decode(ex.layout.physical_digits(p)) == p
        for k in range(4):
            ex.run(k,100)
            checks+=1
    assert [Layout(8,1).physical_digits(j)[0] for j in range(8)] == [0,2,4,6,7,5,3,1]
    # Identical expanded capacity in different carrier groupings.
    results=[ExpandedRegisters(3599,d,m).run(34,100) for d,m in [(2,6),(4,3),(8,2),(64,1)]]
    assert all(np.allclose(x['success_history'],results[0]['success_history']) for x in results)
    return {'status':'PASS','grover_test_cases':checks,
            'dense_arithmetic_cross_checks':5,
            'matched_capacity_encodings':['24 qubits','12 four-level qudits',
                                          '8 eight-level qudits','4 64-level qudits'],
            'prior_eight_level_map_verified':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--N',type=int,default=3599)
    parser.add_argument('--levels',type=int,default=8)
    parser.add_argument('--digits',type=int,default=2)
    parser.add_argument('--max-factor',type=int)
    parser.add_argument('--iterations',type=int,default=34)
    parser.add_argument('--shots',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=12345)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--selftest',action='store_true')
    args=parser.parse_args()
    try:
        result=selftest() if args.selftest else ExpandedRegisters(
            args.N,args.levels,args.digits,args.max_factor).run(
                args.iterations,args.shots,args.seed)
    except ValueError as err:
        parser.error(str(err))
    rendered=json.dumps(result,indent=2)+'\n'
    if args.output:
        args.output.write_text(rendered)
    print(rendered)


if __name__=='__main__':
    main()
