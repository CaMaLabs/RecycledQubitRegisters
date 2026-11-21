#!/usr/bin/env python3
"""Ideal logical qudit factoring experiment; NumPy only, no hardware execution.

P and Q each contain `digits` base-d qudits; R contains 2*digits.
U_mul: |p,q,r> -> |p,q,(r+p*q) mod d**(2*digits)>.
The flag is measured analytically from the product register, without allocating
an extra tensor axis. Arithmetic and reflections are logical block operations,
NOT decompositions into native one-/two-qudit gates. See README.md.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np


class Experiment:
    def __init__(self, target, d=3, digits=2, max_factor=None,
                 max_amplitudes=2_000_000):
        if target < 4 or d < 2 or digits < 1:
            raise ValueError('Require N >= 4, d >= 2, digits >= 1')
        self.n, self.d, self.digits = target, d, digits
        # Check size before calculating/allocating potentially huge dimensions.
        if max_amplitudes < 1:
            raise ValueError('max_amplitudes must be positive')
        if 4 * digits * math.log2(d) > math.log2(max_amplitudes):
            raise ValueError(f'Dense simulator limited to {max_amplitudes:,} amplitudes')
        self.a = d ** digits
        self.r = self.a ** 2
        if target >= self.r:
            raise ValueError('N does not fit the product register; increase digits')
        hi = min(self.a - 1, target - 1) if max_factor is None else max_factor
        if not 2 <= hi < min(self.a, target):
            raise ValueError('Require 2 <= max-factor < min(d**digits, N)')
        self.hi = hi
        self.candidates = list(range(2, hi + 1))
        self.initial = np.zeros((self.a, self.a, self.r), complex)
        for p in self.candidates:
            for q in self.candidates:
                self.initial[p, q, 0] = 1 / len(self.candidates)

    def multiply(self, state, inverse=False):
        """Permutation on the ENTIRE state, including arbitrary scratch values."""
        out = np.empty_like(state)
        sign = -1 if inverse else 1
        for p in range(self.a):
            for q in range(self.a):
                out[p, q] = np.roll(state[p, q], sign * p * q)
        return out

    def oracle(self, state):
        out = self.multiply(state)
        out[:, :, self.n] *= -1
        return self.multiply(out, inverse=True)

    def diffuse(self, state):
        """Reflection about prepared candidate state, on the full Hilbert space."""
        return 2 * np.vdot(self.initial, state) * self.initial - state

    def success_probability(self, state):
        computed = self.multiply(state)
        return float(np.sum(np.abs(computed[:, :, self.n]) ** 2))

    def run(self, iterations=0, shots=2000, seed=12345):
        if iterations < 0 or shots < 1:
            raise ValueError('Require iterations >= 0 and shots >= 1')
        rng = np.random.default_rng(seed)
        state = self.initial.copy()
        history = [self.success_probability(state)]
        for _ in range(iterations):
            state = self.diffuse(self.oracle(state))
            history.append(self.success_probability(state))
        computed = self.multiply(state)
        # Sample the full normalized output, INCLUDING all failed trials.
        probabilities = np.abs(computed.ravel()) ** 2
        probabilities /= probabilities.sum()
        indices = rng.choice(probabilities.size, size=shots, p=probabilities)
        pairs, failures = Counter(), 0
        for index in indices:
            p, q, product = np.unravel_index(index, computed.shape)
            if product == self.n:
                pairs[f'{p}*{q}'] += 1
            else:
                failures += 1
        exact_pairs = []
        for p in self.candidates:
            for q in self.candidates:
                probability = float(abs(computed[p, q, self.n]) ** 2)
                if probability > 1e-12:
                    exact_pairs.append({'p': p, 'q': q,
                                        'unconditional_probability': probability})
        baseline = history[0]
        theta = math.asin(math.sqrt(min(1, baseline)))
        predicted = math.sin((2 * iterations + 1) * theta) ** 2
        conditional = None
        if history[-1] > 1e-15:
            conditional = np.abs(computed[:, :, self.n]) ** 2 / history[-1]
        return {
            'N': self.n, 'dimension': self.d, 'digits_per_candidate': self.digits,
            'candidate_range': [2, self.hi], 'candidate_pairs': len(self.candidates)**2,
            'iterations': iterations, 'oracle_uses': iterations,
            'success_history': history, 'grover_prediction': predicted,
            'plain_expected_trials': 1 / baseline if baseline > 0 else None,
            'shots': shots, 'accepted_shots': shots-failures,
            'rejected_shots': failures, 'accepted_counts': dict(sorted(pairs.items())),
            'solution_weights': exact_pairs,
            'conditional_pair_probabilities': None if conditional is None else [
                {'p': item['p'], 'q': item['q'],
                 'probability': float(conditional[item['p'], item['q']])}
                for item in exact_pairs],
            'scratch_zero_probability_before_readout': float(
                np.sum(np.abs(state[:, :, 0])**2)),
            'resources': {
                'logical_d_level_qudits': 4 * self.digits,
                'optional_flag_qubit': 1,
                'binary_qubits_for_same_register_capacities':
                    2 * math.ceil(math.log2(self.a)) + math.ceil(math.log2(self.r)),
                'dense_state_amplitudes': int(state.size),
                'product_permutations_in_grover': 2 * iterations,
                'product_permutations_for_readout': 1,
                'native_gate_count': None,
            },
            'scope': 'ideal logical statevector simulation; no native gate compilation',
            'coverage': 'No success excludes factors only within the chosen candidate range.',
            'iteration_policy': 'Explicit iteration count; no solution count used to choose it.',
        }


def selftest():
    rng = np.random.default_rng(812)
    checks = 0
    for d, digits in [(2, 3), (3, 2), (4, 2)]:
        for n in [15, 21, 35, 49, 17]:
            ex = Experiment(n, d, digits, max_factor=7)
            # Check inverse on arbitrary nonzero product registers and phases.
            z = rng.normal(size=ex.initial.shape) + 1j*rng.normal(size=ex.initial.shape)
            z /= np.linalg.norm(z)
            assert np.allclose(ex.multiply(ex.multiply(z), True), z, atol=1e-12)
            assert np.allclose(ex.oracle(ex.oracle(z)), z, atol=1e-12)
            # Independent truth table validates oracle signs, not merely involution.
            expected = ex.initial.copy()
            solutions = 0
            for p in ex.candidates:
                for q in ex.candidates:
                    if p*q == n:
                        expected[p, q, 0] *= -1
                        solutions += 1
            assert np.allclose(ex.oracle(ex.initial), expected, atol=1e-12)
            assert np.isclose(ex.success_probability(ex.initial), solutions/36)
            for k in [0, 1, 2, 3]:
                result = ex.run(k, shots=100, seed=99)
                assert np.isclose(result['success_history'][-1], result['grover_prediction'])
                assert np.isclose(result['scratch_zero_probability_before_readout'], 1)
                assert result['accepted_shots'] + result['rejected_shots'] == 100
                for item in result['solution_weights']:
                    assert item['p']*item['q'] == n
                checks += 1
    # Fair radix comparison: identical candidate set and iteration count.
    results = [Experiment(35, d, m, 7).run(2, 300, 41)
               for d, m in [(2, 3), (3, 2), (4, 2)]]
    assert all(np.allclose(r['success_history'], results[0]['success_history'])
               for r in results)
    # Deliberate truncation must not be represented as a primality proof.
    assert Experiment(35, 3, 2, 4).run(1, 10)['accepted_shots'] == 0
    return {'status': 'PASS', 'grover_cases': checks,
            'also_checked': ['arbitrary-scratch multiplication inverse', 'oracle truth table',
                             'uncomputation', 'prime input', 'square input',
                             'fair radix comparison', 'truncated candidate coverage']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--N', type=int, default=35)
    parser.add_argument('--dimension', type=int, default=3)
    parser.add_argument('--digits', type=int, default=2)
    parser.add_argument('--max-factor', type=int)
    parser.add_argument('--max-amplitudes', type=int, default=2_000_000,
                        help='Dense state guard; several 16-byte arrays are needed')
    parser.add_argument('--iterations', type=int, default=2)
    parser.add_argument('--shots', type=int, default=2000)
    parser.add_argument('--seed', type=int, default=12345)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    try:
        result = selftest() if args.selftest else Experiment(
            args.N, args.dimension, args.digits, args.max_factor,
            args.max_amplitudes).run(
                args.iterations, args.shots, args.seed)
    except ValueError as error:
        parser.error(str(error))
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n')
    print(rendered)


if __name__ == '__main__':
    main()
