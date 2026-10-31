#!/usr/bin/env python3
"""Audit finite parameters of a new factoring claim without launching its engine.

This is an exact integer port of the pinned source's parameter formulas, not
an independent verification of its 36,000-line Lean proof or a factoring tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

UPSTREAM = 'https://github.com/IsaacRudich/SubexponentialDeterministicFactoring'
COMMIT = 'c91cc3f4947caca8977e81a5d14244f73b5ae2b1'


def parameters(n):
    if not isinstance(n,int) or n < 0:
        raise ValueError('Input length must be a nonnegative integer')
    # UniParams.lean: K0u=48, Kb(d+1)=9*Kb(d)^16,
    # ellStep increments iff Kb(ell+1)^40 <= n. Once stuck it stays stuck.
    bottom = group = 48
    levels = 0
    while levels < n:
        following = 9 * group**16
        if n < following**40:
            break
        group = following
        levels += 1
    # EngineTop.sOf: smallest s with n <= 2^(4s+2).
    s = 0
    while (1 << (4*s+2)) < n:
        s += 1
    # Transform.pA, pL, pm; MulNet.fw; Cluster.clP; EngineTop.Ltop.
    a = 1 << (s+1)
    message_width = 4*(1 << (2*s+1)) + 1
    grid = 3*group**8
    cluster_width = (7*(a//grid+2)*a*message_width +
                     3*(a*a//grid+2)*message_width)
    top_width = (group*(10*a*a*message_width)+grid*cluster_width)//group**3
    first_threshold = (9*bottom**16)**40
    return dict(input_bits=n, recursive_levels=levels, group=group, s=s,
                grid=grid, message_width=message_width, top_width=top_width,
                top_table_power_of_two_exponent=top_width*group,
                bottom_enumeration_iterations_log2=top_width*bottom**2 if levels==0 else None,
                first_level_input_bits_threshold=str(first_threshold),
                first_level_input_bits_threshold_decimal_digits=len(str(first_threshold)),
                first_level_input_bits_threshold_floor_log2=first_threshold.bit_length()-1)


def inspect(root, n=2048):
    root = Path(root).resolve()
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    if head != COMMIT:
        raise ValueError('Claim checkout differs from inspected snapshot')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():
        raise ValueError('Claim source checkout has modifications')
    files = ['README.md','Challenge.lean','Solution.lean', 'FactoringAux/UniParams.lean',
             'FactoringAux/EngineGroup.lean','FactoringAux/EngineTop.lean',
             'FactoringAux/Transform.lean','FactoringAux/MulNet.lean',
             'FactoringAux/Cluster.lean','FactoringAux/EngineDeepEx.lean',
             'FactoringAux/UniEngine.lean','lean-toolchain','lake-manifest.json']
    hashes = {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}
    p = parameters(n)
    return dict(upstream=UPSTREAM, commit=head, source_sha256=hashes,
                scope='Exact finite-parameter audit of pinned source; not proof verification',
                independently_kernel_checked=False, claimed_theorem='Deterministic N^{o(1)} factoring',
                stronger_sqrt_loglog_rate='Stated as conjecture, not proved',
                parameters=p, dense_table_budget_log2=60,
                dense_table_fits_budget=(p['top_table_power_of_two_exponent']<=60 and
                    p['group'] <= 1 << (60-p['top_table_power_of_two_exponent'])),
                factoring_engine_launched=False, rsa2048_broken=False,
                external_spend=0, qpu_jobs=0,
                caveat='Loop sizes apply to this written engine. They are not factoring lower bounds.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream',required=True)
    parser.add_argument('--bits',type=int,default=2048)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    result = inspect(args.upstream,args.bits)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result['parameters'][k] for k in (
        'input_bits','recursive_levels','top_table_power_of_two_exponent',
        'bottom_enumeration_iterations_log2','first_level_input_bits_threshold_decimal_digits')},indent=2))
