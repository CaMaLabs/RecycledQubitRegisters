#!/usr/bin/env python3
"""A29 controlled FOUR-ARM proxy, no claim of quantum speedup.

Pruning arm uses a transparent public-only residue filter of candidate
trial factors, NOT the original Fourier/NTT spectral pruning implementation.
Arithmetic arm uses A27 reversible repeated-increment logical MCX counts
versus the *ideal* A26 QFT-addition rotation count (incomparable units).
No end-to-end Shor, no QPU, no claimed gain.
"""
import json
import math
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
a24=load("a24",ROOT/"integrations/darkstar_hybrid/qrr_a24_n35_public_first_gate.py")
a27=load("a27",ROOT/"hardware/qrr_a27_reversible_fourier_comparison.py")
WHEEL=(2,3,5,7)
def residue_candidates(n):
    # For an odd semiprime whose primes exceed 7, potential divisors
    # between 11 and floor(sqrt(n)) must be coprime to 210.
    return [k for k in range(11,math.isqrt(n)+1) if math.gcd(k,210)==1]
def solve(n,use_pruning):
    calls=0
    if use_pruning:
        candidates=residue_candidates(n)
        for k in candidates:
            calls+=1
            if n%k==0:return (k,n//k),calls,len(candidates)
    else:
        for k in range(11,math.isqrt(n)+1):
            calls+=1
            if n%k==0:return (k,n//k),calls,None
    return None,calls,(len(candidates) if use_pruning else None)
def run():
    cases=(143,221,899,1763,2491)
    rows=[]
    for n in cases:
        assert all(n%p for p in WHEEL)
        initial=a24.public_preflight(n,2)
        assert initial["factors"] is None
        for pruning in (False,True):
            factors,tests,candidates=solve(n,pruning)
            assert factors is not None and math.prod(factors)==n
            for fourier in (False,True):
                # Identical fixed 4-bit arithmetic sanity cohort.
                x,a=n%16,2
                target,ops=a27.reversible_add(x,a,4)
                ideal=a27.mod.fourier_add_basis(x,a,4)
                error=max(abs(z-(1 if k==target else 0)) for k,z in enumerate(ideal))
                assert error < 1e-9 and target==(x+a)%16
                rows.append(dict(n=n,arm=("residue_" if pruning else "baseline_")+("fourier" if fourier else "binary"),
                    factors=list(factors),classical_divisibility_tests=tests,
                    residue_candidate_count=candidates,
                    logical_reversible_mcx_or_x=ops if not fourier else None,
                    ideal_fourier_rotations=16 if fourier else None,
                    arithmetic_error=error,actual_quantum_cost=None,
                    original_spectral_fourier_pruning=False))
    assert len(rows)==20
    return dict(experiment="A29_RESIDUE_X_ARITHMETIC_FOUR_ARM_PROXY",
        status="PASS_FOUR_ARM_PROXY_NOT_ORIGINAL_SPECTRAL_PRUNING",
        qpu_jobs=0,rows=rows,
        limitations="Residue wheel is genuine public classical filtering, but is NOT the original Fourier/NTT spectral method. All factors in this toy cohort are found classically. Binary logical MCX counts and Fourier abstract rotation counts are not equivalent physical costs; hybrid does NOT reduce Shor gates here. No quantum speedup or RSA projection.")
if __name__=="__main__":
    print(json.dumps(run(),indent=2))
