#!/usr/bin/env python3
"""Reproducible limits of the ORIGINAL dense logical simulator.

Known-solution counts below are diagnostics only. The unknown-count schedule
chooses iterations from search-space size and failed measurements alone.
No simulator memory guard or quantum algorithm is changed by this benchmark.
"""
import os
# Avoid thread launch overhead in the many small/medium vector products.
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import math
from pathlib import Path
import time

from qudit_factor import Experiment


def trial_factor(n):
    for p in range(2, math.isqrt(n) + 1):
        if n % p == 0:
            return [p, n // p]
    return None


def dense_case(n, d, digits, hi, k):
    start = time.perf_counter()
    ex = Experiment(n, d, digits, hi)
    result = ex.run(k, shots=1000, seed=12345)
    elapsed = time.perf_counter() - start
    assert abs(result['success_history'][-1] - result['grover_prediction']) < 1e-10
    assert abs(result['scratch_zero_probability_before_readout'] - 1) < 1e-10
    for item in result['solution_weights']:
        assert item['p'] * item['q'] == n
    # One division sweep is a reference, not a quantum hardware timing comparison.
    cstart = time.perf_counter()
    classical = trial_factor(n)
    classical_seconds = time.perf_counter() - cstart
    return {
        'N': n, 'd': d, 'digits': digits, 'max_factor': hi,
        'iterations': k, 'seconds': elapsed,
        'amplitudes': ex.initial.size, 'single_state_bytes': ex.initial.nbytes,
        'baseline_probability': result['success_history'][0],
        'final_probability': result['success_history'][-1],
        'accepted_shots': result['accepted_shots'],
        'accepted_counts': result['accepted_counts'],
        'classical_factor_diagnostic': classical,
        'classical_trial_division_seconds': classical_seconds,
    }


def unknown_count(n, d, digits, hi, seed, budget=400):
    """BBHT-style randomized schedule, finite budget; no solution count input."""
    import numpy as np
    rng = np.random.default_rng(seed)
    ex = Experiment(n, d, digits, hi)
    space = len(ex.candidates) ** 2
    window, used, attempts = 1.0, 0, []
    start = time.perf_counter()
    for _ in range(120):
        k = int(rng.integers(0, max(1, math.ceil(window))))
        if used + k > budget:
            break
        result = ex.run(k, shots=1, seed=int(rng.integers(0, 2**32)))
        used += k
        accepted = bool(result['accepted_shots'])
        attempts.append({'k': k, 'accepted': accepted})
        if accepted:
            pair = next(iter(result['accepted_counts']))
            p, q = map(int, pair.split('*'))
            assert p*q == n
            return {'N': n, 'seed': seed, 'status': 'FOUND', 'pair': [p,q],
                    'oracle_uses': used, 'verification_runs': len(attempts),
                    'multiplication_permutations': 2*used + len(attempts),
                    'seconds': time.perf_counter()-start, 'attempts': attempts}
        window = min(1.2*window, math.sqrt(space))
    return {'N': n, 'seed': seed, 'status': 'BUDGET_EXHAUSTED_NOT_PRIMALITY_PROOF',
            'oracle_uses': used, 'verification_runs': len(attempts),
            'seconds': time.perf_counter()-start, 'attempts': attempts}


def main():
    cases = [
        (35, 2, 3, 7, 2), (35, 3, 2, 7, 2),
        (529, 3, 3, 26, 19),
        (899, 2, 5, 31, 16), (899, 37, 1, 31, 16),
        (961, 2, 5, 31, 23),
        (1296, 37, 1, 36, 27),
        (74, 37, 1, 36, 2),
    ]
    dense = []
    for case in cases:
        row = dense_case(*case)
        dense.append(row)
        print(json.dumps({'dense_case': row}), flush=True)
    assert abs(dense[0]['final_probability'] - dense[1]['final_probability']) < 1e-12
    assert abs(dense[3]['final_probability'] - dense[4]['final_probability']) < 1e-12
    rejections = []
    for d, m in [(3,4), (2,6), (38,1)]:
        try:
            Experiment(35, d, m)
        except ValueError as err:
            rejections.append({'d': d, 'digits': m, 'error': str(err),
                               'required_amplitudes': d**(4*m)})
        else:
            raise AssertionError('Memory guard did not reject oversized state')
    unknown = []
    for seed in [12345, 23456, 34567]:
        row = unknown_count(899, 2, 5, 31, seed)
        unknown.append(row)
        print(json.dumps({'unknown_count': row}), flush=True)
    # Exact classical support enumeration diagnoses range coverage only.
    coverage = {}
    for bound in [8,26,31,36]:
        first_miss = None
        supported = []
        semiprimes = []
        for n in range(4, bound*bound+1):
            pairs = [(p,q) for p in range(2,bound+1)
                     for q in range(p,bound+1) if p*q == n]
            if pairs:
                supported.append(n)
                if any(trial_factor(p) is None and trial_factor(q) is None
                       for p,q in pairs):
                    semiprimes.append(n)
            elif first_miss is None and trial_factor(n) is not None:
                first_miss = n
        coverage[str(bound)] = {
            'first_composite_outside_pair_coverage': first_miss,
            'largest_supported_product': max(supported),
            'largest_supported_semiprime': max(semiprimes),
            'supported_composites': len(supported),
        }
    # Balanced distinct semiprime asymptotic projection; NOT actual executions.
    scaling = []
    for bits in [16,32,64,128,256,2048]:
        log2iters = bits/2 + math.log2(math.pi/(4*math.sqrt(2)))
        scaling.append({'target_bits': bits,
                        'approx_log2_best_iteration_count': log2iters,
                        'assumption': 'balanced semiprime; B~sqrt(N), K~N, S=2'})
    report = {'scope': 'original code unchanged; ideal classical simulation only',
              'dense_cases': dense, 'memory_guard_rejections': rejections,
              'unknown_count_schedule': unknown, 'coverage_diagnostic': coverage,
              'asymptotic_projections_not_runs': scaling,
              'unknown_count_reference': 'https://arxiv.org/abs/quant-ph/9605034'}
    Path('limits_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'PASS','coverage':coverage,'rejections':rejections}), flush=True)


if __name__ == '__main__':
    main()
