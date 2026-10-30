#!/usr/bin/env python3
"""Bounded sparse-state reference for arXiv:2610.06733, Sections 2/3.

Executes masked traveling states and controlled modular multiplication, rather
than injecting eigenphases. This is an exponential tiny-N reference, not a
gate-efficient implementation or a full Regev lattice decoder. ZERO QPU.
"""
from __future__ import annotations
import argparse
import cmath
import hashlib
import itertools
import json
import math
from pathlib import Path
import numpy as np


def fibonacci(count):
    a, b = 0, 1
    result = []
    for _ in range(count):
        result.append(a)
        a, b = b, a + b
    return result


def permute(state, function):
    out = {}
    for key, amplitude in state.items():
        dest = function(key)
        out[dest] = out.get(dest, 0j) + amplitude
    assert abs(sum(abs(a)**2 for a in out.values()) - 1) < 1e-10
    return out


def backward(state, modulus):
    # Inverse of (x,y) -> (y,xy); all x are units on this subspace.
    return permute(state, lambda xy: (xy[1]*pow(xy[0], -1, modulus) % modulus, xy[0]))


def probe_branches(state, multiplier, modulus, angle):
    """Explicit H-controlled-U-phase-H measurement Kraus branches."""
    moved = permute(state, lambda xy: (xy[0], xy[1]*multiplier % modulus))
    result = []
    for outcome in (0, 1):
        factor = (-1)**outcome * cmath.exp(1j*angle)
        raw = {key: (state.get(key, 0j)+factor*moved.get(key, 0j))/2
               for key in state.keys() | moved.keys()}
        probability = sum(abs(a)**2 for a in raw.values())
        child = {k: a/math.sqrt(probability) for k, a in raw.items()
                 if abs(a) > 1e-15} if probability > 1e-14 else {}
        result.append((probability, child))
    assert abs(sum(p for p, _ in result)-1) < 1e-10
    return result


def initial_state(modulus, mask):
    units = [x for x in range(modulus) if math.gcd(x, modulus) == 1]
    # Unit mask enumerates public gcds and is deliberately charged as classical
    # reference work. It is NOT the paper's efficient approximate preparation.
    values = units if mask == 'units' else [1]
    return {(x, 1): 1/math.sqrt(len(values)) for x in values}


def exact_transcripts(modulus, generators, levels, masked=True, mask='units'):
    assert 3 <= modulus <= 209 and 2 <= levels <= 9
    assert 1 <= len(generators) <= 2 and levels*len(generators) <= 12
    assert all(math.gcd(a, modulus) == 1 for a in generators)
    fib = fibonacci(levels+2)
    branches = {(): (1., initial_state(modulus, mask))}
    for k in range(2, levels+2):
        if masked:
            branches = {h: (p, backward(s, modulus)) for h, (p, s) in branches.items()}
        for coordinate, a in enumerate(generators):
            children = {}
            for history, (weight, state) in branches.items():
                # Public deterministic adaptive angle; no true phase/order.
                angle = math.pi/4 + math.pi/7*(sum(history) % 3)
                multiplier = a if masked else pow(a, fib[k], modulus)
                for bit, (p, child) in enumerate(probe_branches(state, multiplier, modulus, angle)):
                    if p > 1e-14:
                        children[history+(bit,)] = (weight*p, child)
            branches = children
    distribution = {''.join(map(str, h)): p for h, (p, _) in branches.items()}
    assert abs(sum(distribution.values())-1) < 1e-9
    return distribution


def grid_phase_probe(phase, powers, shots, seed, grid=2048):
    """Finite-grid scalar Bayesian diagnostic, not scalable paper estimator.

    The synthetic phase is used ONLY by the measurement source. The posterior
    sees outcomes, exponents, and adaptive angles. No order enters decoding.
    """
    rng = np.random.default_rng(seed)
    theta = np.arange(grid)/grid
    posterior = np.full(grid, 1/grid)
    transcript = []
    for exponent in powers:
        for _ in range(shots):
            # Pick between two quadratures by posterior outcome entropy.
            angles = (0., math.pi/2)
            predictions = [float(posterior @ ((1+np.cos(2*math.pi*exponent*theta+a))/2))
                           for a in angles]
            index = min(range(2), key=lambda i: abs(predictions[i]-.5))
            angle = angles[index]
            p0 = (1+math.cos(2*math.pi*exponent*phase+angle))/2
            bit = int(rng.random() >= p0)
            likelihood = (1+(-1)**bit*np.cos(2*math.pi*exponent*theta+angle))/2
            posterior *= np.maximum(likelihood, 1e-300)
            posterior /= posterior.sum()
            transcript.append([exponent, angle, bit])
    estimate = float(theta[int(posterior.argmax())])
    distance = abs((estimate-phase+.5) % 1-.5)
    return dict(estimate=estimate, circular_error=distance,
                correct_grid_cell=distance <= 1.5/grid,
                map_mass=float(posterior.max()), probes=len(transcript),
                power_sum=sum(x[0] for x in transcript), grid_points=grid)


def run():
    rows = []
    for modulus, generators in ((15, [4]), (21, [4]), (35, [4, 9])):
        levels = 4
        actual = exact_transcripts(modulus, generators, levels)
        reference = exact_transcripts(modulus, generators, levels, masked=False)
        keys = actual.keys() | reference.keys()
        tv = sum(abs(actual.get(k, 0)-reference.get(k, 0)) for k in keys)/2
        assert tv < 1e-9, (modulus, tv)
        broken = exact_transcripts(modulus, generators, levels, mask='singleton')
        negative_tv = sum(abs(broken.get(k, 0)-reference.get(k, 0)) for k in keys | broken.keys())/2
        assert negative_tv > 1e-3, 'negative mask control did not expose lost coherence'
        rows.append(dict(N=modulus, generators=generators, levels=levels,
                         transcript_outcomes=len(keys), masked_reference_tv=tv,
                         singleton_mask_negative_tv=negative_tv,
                         exact_mask_enumeration_gcd_tests=modulus,
                         transcript_sha256=hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()))
    fib = fibonacci(16)[2:]
    grid_rows = []
    for case in range(12):
        phase = float(np.random.default_rng(20261030+case).random())
        for family, powers in (('fibonacci', fib), ('binary', [1 << i for i in range(len(fib))])):
            grid_rows.append(dict(case=case, family=family,
                                  **grid_phase_probe(phase, powers, 6, 6000+case)))
    return dict(status='REFERENCE_SEMANTICS_PASS', qpu_jobs=0,
                masked_state_tests=rows, finite_grid_diagnostics=grid_rows,
                full_regev_factoring_implemented=False,
                scalable_adaptive_cell_estimator_implemented=False,
                source='https://arxiv.org/abs/2610.06733',
                limitations=['Sparse permutations and exact unit mask are exponential reference operations.',
                             'Finite posterior grid is a diagnostic; never extrapolate its memory to RSA.',
                             'Binary/fibonacci equal-probe results have unequal unitary-power costs.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/literature_20261030/masked_fibonacci.json')
    args = parser.parse_args()
    result = run()
    dest = Path(args.output); dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'qpu_jobs', 'masked_state_tests')}, indent=2))
