#!/usr/bin/env python3
"""Compare three reversible multiplier architectures, with scratch cleanup."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
from native_arithmetic import Circuit
from parallel_compressor import wallace_multiply

def run(width, random_pairs):
    rng = random.Random(280028 + width)
    mask = (1 << width) - 1
    cases = [
        (0, 0), (mask, mask), (1, mask), (mask, 1),
        (1 << (width-1), 1 << (width-1)), (mask, 0)
    ]
    if width <= 5:
        cases = [(a, b) for a in range(1 << width) for b in range(1 << width)]
    else:
        cases.extend(
            (rng.randrange(1 << width), rng.randrange(1 << width))
            for _ in range(random_pairs)
        )
    results = {}
    for method in ('schoolbook', 'carry_save', 'wallace'):
        c = Circuit()
        a = c.reg('a', width)
        b = c.reg('b', width)
        if method == 'wallace':
            raw, rounds = wallace_multiply(c, a, b, width)
        else:
            raw = c.mul(a, b, width, method)
            rounds = None
        result = c.clean_output(raw)
        protected = set(a + b + result)
        for x, y in cases:
            bits = c.evaluate({'a': x, 'b': y})
            observed = sum(bits[q] << i for i, q in enumerate(result))
            assert observed == ((x*y) & mask), (method, width, x, y, observed)
            assert sum(bits[q] << i for i, q in enumerate(a)) == x
            assert sum(bits[q] << i for i, q in enumerate(b)) == y
            assert all(bits[i] == 0 for i in range(c.n) if i not in protected), (
                method, width, 'dirty scratch'
            )
        results[method] = {
            'metrics': c.metrics(),
            'verified_pairs': len(cases),
            'compression_rounds': rounds
        }
    return {
        'width': width,
        'results': results,
        'status': 'PASS',
        'scope': 'Gate-level unsigned multiplication mod 2**width; not official Kickmix circuit'
    }

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--widths', default='4,5,8,12,16,27')
    p.add_argument('--random-pairs', type=int, default=40)
    a = p.parse_args()
    for width in map(int, a.widths.split(',')):
        print(json.dumps(run(width, a.random_pairs), sort_keys=True), flush=True)
