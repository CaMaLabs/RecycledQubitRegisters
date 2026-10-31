#!/usr/bin/env python3
"""Public-input Quaspy adapter; no sampler, factors, order oracle, or QPU API.

The external author implementation supplies order-recovery mathematics. This
adapter adds strict factor verification, a work ledger, and bounded execution.
"""
from __future__ import annotations

import hashlib
import math
from numbers import Integral
import subprocess
import sys
import time
from pathlib import Path

COMMIT = '8040affdf08814ef7d451d9797d28f7645856151'


def load_upstream(root):
    root = Path(root).resolve()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip() != COMMIT:
        raise ValueError('Unpinned Quaspy checkout')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():
        raise ValueError('Quaspy checkout has source modifications')
    existing = sys.modules.get('quaspy')
    if existing is not None and not Path(existing.__file__).resolve().is_relative_to(root):
        raise ValueError('Different quaspy module already imported')
    sys.path.insert(0,str(root/'src'))
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((root/'src/quaspy').rglob('*.py'))}


class WorkLimit(Exception):
    pass


class Ledger:
    def __init__(self, budget=100000, timeout=2):
        self.pow_calls = self.mul_calls = self.binary_mul_estimate = self.gcd_calls = self.inverse_calls = 0
        self.budget = budget
        self.start = time.perf_counter()
        self.deadline = self.start + timeout

    def charge(self, units):
        self.binary_mul_estimate += units
        if self.binary_mul_estimate > self.budget or time.perf_counter() > self.deadline:
            raise WorkLimit('public post-processing work limit')

    def power(self,a,e,n):
        e = int(e)
        self.pow_calls += 1
        if e < 0:
            # Lattice enumeration needs inverses; count them separately.
            self.inverse_calls += 1
            a = pow(int(a),-1,int(n))
            e = -e
        # Binary exponentiation work proxy, not a count of GMP internals.
        self.charge(max(0,e.bit_length()-1)+e.bit_count())
        return pow(int(a),e,int(n))

    def snapshot(self):
        return dict(pow_calls=self.pow_calls,mul_calls=self.mul_calls,
                    gcd_calls=self.gcd_calls,inverse_calls=self.inverse_calls,
                    binary_mul_estimate=self.binary_mul_estimate,
                    seconds=time.perf_counter()-self.start)


def group_element(a,n,ledger):
    from quaspy.math.groups import CyclicGroupElement
    class Counted(CyclicGroupElement):
        def __init__(self,value):
            self.value = int(value)%n
        def __pow__(self,e):
            return Counted(ledger.power(self.value,e,n))
        def __mul__(self,other):
            if not isinstance(other,Counted):
                return NotImplemented
            ledger.mul_calls += 1
            ledger.charge(1)
            return Counted(self.value*other.value%n)
        def __eq__(self,other):
            if isinstance(other,Integral):
                return other==1 and self.value==1
            return isinstance(other,Counted) and self.value==other.value
        def __hash__(self):
            return hash((n,self.value))
    return Counted(a)


def verified_pair(n,divisor):
    divisor = int(divisor)
    if 1 < divisor < n and n%divisor==0:
        return sorted((divisor,n//divisor))
    return None


def split_order(n,a,r,ledger):
    if r is None or r<=0 or r%2:
        return None
    root = ledger.power(a,r//2,n)
    for sign in (-1,1):
        ledger.gcd_calls += 1
        factors = verified_pair(n,math.gcd(root+sign,n))
        if factors:
            return factors
    return None


def convergents(j,Q):
    previous2,previous = 1,0
    while Q:
        quotient,remainder = divmod(j,Q)
        denominator = quotient*previous+previous2
        yield denominator
        previous2,previous = previous,denominator
        j,Q = Q,remainder


def recover(n,base,phase_bits,frequency,method='ekera',budget=100000,timeout=2):
    """Consumes only N, public base, measured frequency, and public precision."""
    if n<9 or n%2==0 or not 1<base<n or math.gcd(base,n)!=1:
        raise ValueError('Odd modulus and coprime public base required')
    if phase_bits<1 or not 0<=frequency<1<<phase_bits:
        raise ValueError('Invalid measurement')
    ledger = Ledger(budget,timeout)
    candidate = None
    factors = None
    status = 'NO_VERIFIED_ORDER'
    try:
        if method=='cf':
            for d in convergents(frequency,1<<phase_bits):
                if d>n:
                    break
                # Match the current Dark Star factor verifier's even denominators.
                if d>1 and d%2==0 and ledger.power(base,d,n)==1:
                    candidate = d if candidate is None else min(candidate,d)
                    factors = split_order(n,base,d,ledger)
                    if factors:
                        break
        elif method=='ekera':
            from quaspy.orderfinding.general.postprocessing.ekera import solve_j_for_r, SolutionMethods
            m = n.bit_length()  # Public upper bound: order < N < 2^m.
            l = phase_bits-m
            if not 1<=l<=m:
                raise ValueError('Quaspy requires m < phase_bits <= 2m')
            value = solve_j_for_r(frequency,m,l,group_element(base,n,ledger),c=1,B=4,
                accept_multiple=False,method=SolutionMethods.LATTICE_BASED_ENUMERATE,
                timeout=timeout,opt_speculative=True,opt_isolate_peak=False)
            if value is not None:
                value = int(value)
                if value>0 and ledger.power(base,value,n)==1:
                    candidate = value
                    factors = split_order(n,base,candidate,ledger)
        else:
            raise ValueError('Unknown postprocessor')
        if candidate is not None:
            status = 'VERIFIED_EXPONENT'
        if factors is not None:
            assert math.prod(factors)==n
            status = 'VERIFIED_FACTORS'
    except (WorkLimit,TimeoutError):
        status = 'WORK_LIMIT'
    return dict(status=status,candidate_exponent=candidate,factors=factors,
                public_only=True,ledger=ledger.snapshot())


def replay(payload):
    required = {'N','base','phase_bits','frequency'}
    if set(payload)!=required:
        raise ValueError('Replay accepts exactly N, base, phase_bits, frequency')
    return recover(int(payload['N']),int(payload['base']),int(payload['phase_bits']),
                   int(payload['frequency']))


if __name__=='__main__':
    import argparse
    import json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',required=True)
    parser.add_argument('--input',required=True,help='Public readout JSON with four fields')
    args=parser.parse_args()
    load_upstream(args.upstream)
    print(json.dumps(replay(json.loads(Path(args.input).read_text())),indent=2))
