#!/usr/bin/env python3
"""Enforce a public-evidence gate before another PTP distance/scheduler sweep.

Historical experiments remain reproducible. This new entry point defaults to
the existing strong Brent arm, optionally its fixed eight-step Fermat precheck.
Residue signatures cannot authorize a factor-distance horizon.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def certified_horizon(n,lower_bound,budget=10000):
    """Actually exclude all divisors below L; never trust a supplied p>=L label.

    This public certificate is intentionally expensive and fully charged.
    It is not a new factorization theorem or a shortcut around trial division.
    """
    if not isinstance(n,int) or n<9 or n%2==0:raise ValueError('odd composite candidate required')
    if not 2<=lower_bound<=math.isqrt(n):raise ValueError('L outside valid range')
    if lower_bound-2>budget:
        return dict(status='CERTIFICATE_BUDGET_CENSORED',checked_divisors=0)
    checks=0
    for divisor in range(2,lower_bound):
        checks+=1
        if n%divisor==0:
            return dict(status='CLASSICAL_FACTOR_FOUND',factors=[divisor,n//divisor],checked_divisors=checks)
    start=math.isqrt(n)+(math.isqrt(n)**2<n)
    upper=(lower_bound*lower_bound+n)//(2*lower_bound)
    return dict(status='PUBLIC_LOWER_BOUND_CERTIFIED',lower_bound=lower_bound,
                midpoint_offset_upper_bound=max(0,upper-start),checked_divisors=checks,
                semiprime_assumption_required=True)


def select_policy(n,fermat_precheck=False,residue_signature=None):
    if n<9:raise ValueError('N too small')
    return dict(arm='F' if fermat_precheck else 'B',only_public_N=True,
                residue_distance_authorized=False,
                residue_signature_ignored=residue_signature is not None,
                reason='N34 anytime merit gates failed; residue-only proximity was falsified.',
                quantum_jobs=0)


def run(n,fermat_precheck=False):
    from integrations.darkstar_hybrid.darkstar_n34_anytime_scheduler import factor_public
    if not isinstance(n,int) or not 9<=n<2**40:
        raise ValueError('This bounded reference accepts 9 <= N < 2**40')
    selection=select_policy(n,fermat_precheck)
    return dict(selection=selection,result=factor_public(n,selection['arm']))


def self_test():
    close,far=922551607,537116557
    assert close % 255255==far % 255255
    for n in (close,far):
        assert select_policy(n,residue_signature=n % 255255)['arm']=='B'
        assert not select_policy(n,residue_signature=n % 255255)['residue_distance_authorized']
    assert certified_horizon(35,5)['status']=='PUBLIC_LOWER_BOUND_CERTIFIED'
    assert certified_horizon(35,5)['midpoint_offset_upper_bound']==0
    assert certified_horizon(35,5)['checked_divisors']==3
    assert certified_horizon(77,8)['factors']==[7,11]
    assert certified_horizon(101*103,100,budget=1)['status']=='CERTIFICATE_BUDGET_CENSORED'
    actual=[]
    for n in (35,209,713,781):
        row=run(n);assert math.prod(row['result']['factors'])==n
        actual.append(row)
    return dict(status='PASS',default_arm='B',residue_signature_never_authorizes_horizon=True,
                certificate_checks_charged=True,classical_checks=actual,quantum_jobs=0)


if __name__=='__main__':
    p=argparse.ArgumentParser();group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--N',type=int)
    p.add_argument('--fermat-precheck',action='store_true')
    group.add_argument('--self-test',action='store_true')
    p.add_argument('--output',default='results/literature_20261030/darkstar_gate.json')
    a=p.parse_args()
    result=self_test() if a.self_test else run(a.N,a.fermat_precheck)
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
