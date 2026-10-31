#!/usr/bin/env python3
"""Frozen small-key post-processing comparison; ideal sampler, zero QPU/spend."""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import math
import platform
from pathlib import Path
import random
import statistics
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integrations.darkstar_hybrid import quaspy_public_postprocess as public


def private_case(rng,bits):
    """Synthetic oracle setup. The solver never receives p, q, or r."""
    from sympy import nextprime, factorint
    def prime(k):
        while True:
            p = int(nextprime(rng.getrandbits(k-1)|(1<<(k-1))|1))
            if p.bit_length()==k:
                return p
    while True:
        p,q = prime(bits//2),prime(bits-bits//2)
        n = p*q
        if p!=q and n.bit_length()==bits:
            break
    while True:
        a = rng.randrange(2,n-1)
        if math.gcd(a,n)==1:
            break
    def order_at(p):
        order = p-1
        for f in factorint(order):
            while order%int(f)==0 and pow(a,order//int(f),p)==1:
                order //= int(f)
        return order
    r = math.lcm(order_at(p),order_at(q))
    assert pow(a,r,n)==1
    return n,a,r


def head_bins(r,z,bits,radius=64):
    """Subnormalized exact-QPE kernel near a peak, computed from exact residues.

    No tail renormalization. Missing probability is explicitly a failed trial.
    Exact integer residues avoid cancellation when phase_bits exceeds 53.
    """
    Q = 1<<bits
    quotient,remainder = divmod(z*Q,r)
    center = (quotient+(2*remainder>=r))%Q
    values = range(Q) if Q<=2*radius+1 else [(center+d)%Q for d in range(-radius,radius+1)]
    bins = []
    for y in values:
        v = (y*r-z*Q)%(Q*r)
        if 2*v>Q*r:
            v -= Q*r
        if v==0:
            probability = 1.0
        else:
            x = v/r
            probability = (math.sin(math.pi*x)/(Q*math.sin(math.pi*x/Q)))**2
        bins.append((y,probability))
    assert sum(p for _,p in bins)<=1+1e-12
    return bins


def draw_head(r,z,bits,u):
    bins = head_bins(r,z,bits)
    mass = sum(p for _,p in bins)
    cumulative = 0.0
    for y,p in bins:
        cumulative += p
        if u<cumulative:
            return y,mass
    return None,mass


def summarize(rows,cases,plan):
    result = []
    for cohort in plan['cohorts']:
        subset = [r for r in rows if r['cohort']==cohort]
        for width in plan['bits']+[None]:
            relevant = [r for r in subset if width is None or r['bits']==width]
            for arm in ('cf_full','cf_short','ekera_full','ekera_short','zero_frequency','uniform_frequency'):
                group = [r for r in relevant if r['arm']==arm]
                successes = sum(bool(r['result']['factors']) for r in group)
                precision = statistics.mean(r['phase_bits'] for r in group)
                result.append(dict(cohort=cohort,bits=width,arm=arm,trials=len(group),
                    verified_factors=successes,verified_exponents=sum(r['result']['candidate_exponent'] is not None for r in group),
                    factor_rate=successes/len(group),tail_censored=sum(r['frequency'] is None for r in group),
                    mean_head_mass=statistics.mean(r['head_mass'] for r in group),
                    median_seconds=statistics.median(r['result']['ledger']['seconds'] for r in group),
                    mean_pow_calls=statistics.mean(r['result']['ledger']['pow_calls'] for r in group),
                    mean_binary_mul_estimate=statistics.mean(r['result']['ledger']['binary_mul_estimate'] for r in group),
                    phase_round_proxy_per_factor=(precision*len(group)/successes if successes and arm not in ('zero_frequency','uniform_frequency') else None)))
    clusters = defaultdict(lambda:defaultdict(int))
    for row in rows:
        if row['cohort']=='holdout' and row['arm'] in ('cf_full','ekera_short'):
            clusters[row['case']][row['arm']] += bool(row['result']['factors'])
    wins = sum(g['ekera_short']>g['cf_full'] for g in clusters.values())
    losses = sum(g['ekera_short']<g['cf_full'] for g in clusters.values())
    discordant = wins+losses
    p = sum(math.comb(discordant,i) for i in range(wins,discordant+1))/2**discordant if discordant else 1.
    pooled = {r['arm']:r for r in result if r['cohort']=='holdout' and r['bits'] is None}
    uplift = pooled['ekera_short']['factor_rate']-pooled['cf_full']['factor_rate']
    ratio = pooled['ekera_short']['phase_round_proxy_per_factor']/pooled['cf_full']['phase_round_proxy_per_factor']
    primary = dict(cluster_wins=wins,cluster_losses=losses,one_sided_sign_p=p,
                   factor_success_uplift=uplift,phase_round_proxy_ratio=ratio,
                   uniform_null_factor_rate=pooled['uniform_frequency']['factor_rate'],
                   passed=p<=.01 and uplift>=.15 and ratio<1 and pooled['uniform_frequency']['factor_rate']<=.05)
    return result,primary


def run(upstream,output,plan_path):
    import gmpy2
    import sympy
    plan = json.loads(Path(plan_path).read_text())
    out = Path(output)
    out.mkdir(parents=True,exist_ok=True)
    result = dict(status='STARTED',plan=plan,plan_sha256=hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
                  upstream_sha256=public.load_upstream(upstream),public_cases=[],rows=[],qpu_jobs=0,external_spend=0,RSA2048_break=False,
                  environment=dict(python=platform.python_version(),gmpy2=gmpy2.version(),sympy=sympy.__version__))
    start = time.perf_counter()
    def save():
        result['elapsed_seconds'] = time.perf_counter()-start
        raw = (json.dumps(result,indent=2)+'\n').encode()
        (out/'audit.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    for cohort,seed in plan['cohorts'].items():
        rng = random.Random(seed)
        for bits in plan['bits']:
            for index in range(plan['cases_per_width_per_cohort']):
                n,a,r = private_case(rng,bits)
                case = f'{cohort}-{bits}-{index}'
                result['public_cases'].append(dict(case=case,cohort=cohort,N=str(n),base=str(a),bits=bits))
                for shot in range(plan['shots_per_case']):
                    z = rng.randrange(r)
                    u = rng.random()
                    full,mass_full = draw_head(r,z,2*bits,u)
                    short,mass_short = draw_head(r,z,2*bits-4,u)
                    uniform = rng.randrange(1<<(2*bits-4))
                    for arm,precision,y,mass in (
                        ('cf_full',2*bits,full,mass_full),('cf_short',2*bits-4,short,mass_short),
                        ('ekera_full',2*bits,full,mass_full),('ekera_short',2*bits-4,short,mass_short),
                        ('zero_frequency',2*bits-4,0,1.),('uniform_frequency',2*bits-4,uniform,1.)):
                        if arm=='zero_frequency' and shot:
                            continue
                        if y is None:
                            answer = dict(status='TAIL_CENSORED',candidate_exponent=None,factors=None,
                                          ledger=dict(seconds=0.,pow_calls=0,binary_mul_estimate=0))
                        else:
                            answer = public.recover(n,a,precision,y,'cf' if arm.startswith('cf_') else 'ekera')
                        if answer['candidate_exponent'] is not None:
                            assert answer['candidate_exponent']%r==0
                        if answer['factors']:
                            assert math.prod(answer['factors'])==n
                        result['rows'].append(dict(case=case,cohort=cohort,bits=bits,shot=shot,
                            arm=arm,phase_bits=precision,frequency=y,head_mass=mass,result=answer))
            print(f'{cohort} bits={bits}: complete',flush=True)
            save()
    result['summary'],result['primary_gate'] = summarize(result['rows'],result['public_cases'],plan)
    result['status'] = 'COMPLETE'
    save()
    (out/'summary.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ('rows','upstream_sha256')},indent=2)+'\n')
    print(json.dumps(result['primary_gate'],indent=2),flush=True)
    return result


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',required=True)
    p.add_argument('--output',default='results/indie_diamond_20261030')
    p.add_argument('--plan',default='results/indie_diamond_20261030/audit_plan.json')
    args = p.parse_args()
    run(args.upstream,args.output,args.plan)
