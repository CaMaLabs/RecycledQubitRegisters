#!/usr/bin/env python3
"""Bounded public-input RSA attack, local compute only; never submits a job.

Primary target is the published RSA-2048 challenge. Controls are disposable
generated RSA keys with explicitly labeled weaknesses. Solvers receive only
N and e. A successful control is never a general RSA break.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

RSA2048 = int(''.join('''
251959084756578934940271832400483985714292821262040320277
771378360436620207075955562640185258807844069182906412495
150821892985591491761845028084891200728449926873928072877
767359714183472702618963750149718246911650776133798590957
000973304597488084284017974291006424586918171951187461215
151726546322822168699875491824224336372590851418654620435
767984233871847744479207399342365848238242811981638150106
748104516603773060562016196762561338441436038339044149526
344321901146575444541784240209246165157233507787077498171
257724679629263863563732899121548314381678998850404453640
23527381951378636564391212010397122822120720357
'''.split()))
SOURCE='https://dev.mysterytwister.org/media/challenges/pdf/mtc3-rsa-38-en.pdf'
PLAN=(('screen',2),('wiener',2),('odd_power_gcd',4),('pminus1',8),('brent',15),('ecm',30))


def factors_from_divisor(n,g):
    g=int(g)
    return sorted([g,n//g]) if 1<g<n and n % g==0 else None


def emit(**fields):
    print(json.dumps(fields,sort_keys=True),flush=True)


def screen(n):
    from sympy import primerange,perfect_power
    checks=0
    for p in primerange(2,10000):
        checks+=1
        if n % p==0:return factors_from_divisor(n,p),dict(trial_checks=checks)
    power=perfect_power(n)
    if power:return factors_from_divisor(n,int(power[0])),dict(perfect_power=True)
    x=math.isqrt(n);x+=x*x<n
    # Bounded Fermat, no residue-density proximity inference.
    for step in range(8192):
        y2=x*x-n;y=math.isqrt(y2)
        if y*y==y2:
            pair=factors_from_divisor(n,x-y)
            if pair:return pair,dict(trial_checks=checks,fermat_square_tests=step+1)
        x+=1
    return None,dict(trial_checks=checks,fermat_square_tests=8192)


def wiener(n,e):
    # Continued fractions e/N; every proposed phi and factor is checked exactly.
    numerator,denominator=e,n
    p0,p1,q0,q1=0,1,1,0;checked=0
    while denominator:
        a,numerator,denominator=numerator//denominator,denominator,numerator % denominator
        k,d=a*p1+p0,a*q1+q0
        p0,p1,q0,q1=p1,k,q1,d
        checked+=1
        if not k or (e*d-1) % k:continue
        phi=(e*d-1)//k;total=n-phi+1;discriminant=total*total-4*n
        if discriminant<0:continue
        root=math.isqrt(discriminant)
        if root*root==discriminant and (total+root) % 2==0:
            pair=factors_from_divisor(n,(total+root)//2)
            if pair:return pair,dict(convergents=checked,recovered_private_exponent=str(d))
    return None,dict(convergents=checked)


def odd_power_gcd(n):
    operations=0
    for base in (2,3,5,7,11,13,17,19):
        for odd in (1,3,5,7,105,1155,15015):
            value=pow(base,odd,n)
            for level in range(64):
                for sign in (-1,1):
                    pair=factors_from_divisor(n,math.gcd(value+sign,n))
                    if pair:return pair,dict(base=base,odd_power=odd,level=level,gcd_calls=operations+1,
                                              credit='classical public power/gcd, not quantum')
                    operations+=1
                value=value*value % n
    return None,dict(gcd_calls=operations,credit='classical only')


def brent(n):
    import gmpy2
    modulus=gmpy2.mpz(n);steps=0;gcds=0
    for constant,seed in ((1,2),(3,3),(5,7),(7,11)):
        y=gmpy2.mpz(seed);r=1;g=1
        while g==1 and steps<2_000_000:
            x=y
            for _ in range(r):y=(y*y+constant) % modulus;steps+=1
            k=0
            while k<r and g==1:
                saved=y;product=gmpy2.mpz(1)
                for _ in range(min(64,r-k)):
                    y=(y*y+constant) % modulus;steps+=1
                    product=product*abs(x-y) % modulus
                g=gmpy2.gcd(product,modulus);gcds+=1;k+=64
            r*=2
        if g==modulus:
            g=1
            while g==1 and steps<2_100_000:
                saved=(saved*saved+constant) % modulus;steps+=1
                g=gmpy2.gcd(abs(x-saved),modulus);gcds+=1
        pair=factors_from_divisor(n,g)
        if pair:return pair,dict(squarings=steps,gcd_calls=gcds)
    return None,dict(squarings=steps,gcd_calls=gcds)


def worker(method,budget):
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(math.ceil(budget)+1,math.ceil(budget)+2))
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    public=json.loads(sys.stdin.read(16384))
    if set(public)!={'N','e'}:raise ValueError('solver accepts only N/e')
    n,e=int(public['N']),int(public['e'])
    if not (9<=n and n.bit_length()<=4096 and 1<e<n):raise ValueError('unsupported input')
    start=time.perf_counter()
    if method=='screen':pair,detail=screen(n)
    elif method=='wiener':pair,detail=wiener(n,e)
    elif method=='odd_power_gcd':pair,detail=odd_power_gcd(n)
    elif method=='brent':pair,detail=brent(n)
    elif method=='pminus1':
        from sympy.ntheory import pollard_pm1
        g=pollard_pm1(n,B=100000,a=2,retries=0,seed=20261030)
        pair=factors_from_divisor(n,g or 1);detail=dict(B=100000,retries=0)
    elif method=='ecm':
        # Pinned SymPy 1.14.0 primitive returns one divisor rather than waiting
        # for recursive complete factorization and losing a partial success.
        import sympy
        if sympy.__version__!='1.14.0':raise RuntimeError('requires sympy==1.14.0')
        from sympy.ntheory.ecm import _ecm_one_factor
        g=_ecm_one_factor(n,B1=20000,B2=200000,max_curve=32,seed=20261030)
        pair=factors_from_divisor(n,g or 1);detail=dict(B1=20000,B2=200000,max_curves=32)
    else:raise ValueError('unknown method')
    emit(status='FACTOR_FOUND' if pair else 'NO_FACTOR_IN_COMPLETED_ARM',
         factors=[str(x) for x in pair] if pair else None,details=detail,
         seconds=time.perf_counter()-start)


def run_arm(n,e,method,budget):
    start=time.perf_counter()
    try:
        p=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',method,'--budget',str(budget)],
                         input=json.dumps({'N':str(n),'e':str(e)}),text=True,
                         capture_output=True,timeout=budget,
                         env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
    except subprocess.TimeoutExpired:
        return dict(method=method,status='TIMEOUT_CENSORED',wall_seconds=time.perf_counter()-start,budget_seconds=budget)
    if p.returncode:
        raise RuntimeError(method+' software failure: '+p.stderr[-1500:])
    result=json.loads(p.stdout.strip().splitlines()[-1])
    pair=result.get('factors')
    if pair and (len(pair)!=2 or math.prod(map(int,pair))!=n or not all(1<int(x)<n for x in pair)):
        raise AssertionError('invalid factor certificate')
    return dict(method=method,budget_seconds=budget,wall_seconds=time.perf_counter()-start,**result)


def validate_recovery(n,e,pair):
    from sympy import isprime
    p,q=map(int,pair)
    assert p*q==n and p!=q and isprime(p) and isprime(q)
    lam=math.lcm(p-1,q-1)
    if math.gcd(e,lam)!=1:return dict(factor_certificate_valid=True,rsa_private_exponent_available=False)
    d=pow(e,-1,lam)
    # Public fixed test messages; no hidden/control message passed to solver.
    messages=[0,1,2,42,p,q,n-1]
    assert all(pow(pow(message,e,n),d,n)==message for message in messages)
    return dict(factor_certificate_valid=True,rsa_private_exponent_available=True,
                private_exponent=str(d),public_roundtrip_checks=len(messages),
                warning='Disposable research/control key; do not use for real secrets')


def prime(bits):
    from sympy import nextprime
    while True:
        # Both top bits ensure two independently chosen equal-width primes
        # multiply to a full 2*bits-bit modulus with a factor ratio below 2.
        candidate=secrets.randbits(bits) | (3 << (bits-2)) | 1
        p=int(nextprime(candidate))
        if p.bit_length()==bits:return p


def controls():
    from sympy import nextprime
    rows=[]
    p=prime(1024);q=int(nextprime(p+2))
    while math.gcd(65537,(p-1)*(q-1))!=1:
        p=prime(1024);q=int(nextprime(p+2))
    rows.append(('weak_close_primes_2048',p*q,65537,'screen',2,'deliberately close factors'))
    p,q=prime(1024),prime(1024)
    while p==q:q=prime(1024)
    phi=(p-1)*(q-1);d=4294967311
    while math.gcd(d,phi)!=1:d=int(nextprime(d+1))
    e=pow(d,-1,phi)
    rows.append(('weak_small_d_2048',p*q,e,'wiener',2,'deliberately tiny private exponent'))
    p,q=prime(30),prime(34)
    while p==q or math.gcd(65537,(p-1)*(q-1))!=1:p,q=prime(30),prime(34)
    rows.append(('tiny_64bit_baseline',p*q,65537,'brent',8,'tiny modulus, not cryptographic security'))
    # The following solver loop sees only public N/e, not p,q or d.
    result=[]
    for label,n,e,method,budget,weakness in rows:
        row=run_arm(n,e,method,budget)
        row.update(label=label,N=str(n),e=str(e),bits=n.bit_length(),weakness=weakness,
                   credit='positive control only, not general RSA break')
        assert row['status']=='FACTOR_FOUND',(label,row)
        row['certificate']=validate_recovery(n,e,row['factors'])
        result.append(row)
        emit(event='control',label=label,status=row['status'],bits=row['bits'])
    return result


def quantum_gate(n):
    # Scope these numbers to the cited construction and archived experiment;
    # logical and noisy physical qubits must never be equated.
    bits=n.bit_length()
    return dict(status='NO_FEASIBLE_EXECUTION_PLAN',qpu_jobs=0,
                streamed_regev_4n_leading_logical_qubits=4*bits,
                lower_order_space_not_included=True,
                referenced_construction='https://arxiv.org/abs/2610.06733',
                repository_hardware_evidence='N15 five-logical-qubit Fez pilot only',
                prior_n35_ladder_full_circuit_paired_wins=0,
                approximate_fault_tolerant_reference='https://arxiv.org/abs/2505.15917',
                general_impossibility_claim=False,
                reason='No fault-tolerant execution plan; current sparse reference enumerates tiny groups, not RSA2048.')


def main(output,control_only=False):
    assert len(str(RSA2048))==617 and RSA2048.bit_length()==2048
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    manifest=dict(target='RSA-2048 challenge',N=str(RSA2048),
                  public_exponent=65537,exponent_note='Chosen for certificate checks; the challenge asks only for factors.',
                  source=SOURCE,arms=[dict(method=m,wall_cap_seconds=t) for m,t in PLAN],
                  budget_policy='Local subprocesses only; no API calls, hosted CI, cloud compute, or QPU submission',
                  algorithms='Established attacks and public odd-power GCD preprocessing; no new factoring theorem')
    # Freeze exact target and budget before generating controls or running arms.
    frozen=output.with_name(output.stem+'_public_manifest.json')
    frozen_text=json.dumps(manifest,sort_keys=True,indent=2)+'\n'
    if frozen.exists() and frozen.read_text()!=frozen_text:raise RuntimeError('refuse to replace different frozen manifest')
    frozen.write_text(frozen_text)
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),lead='Chase Lunsford / CaMaLabs',
                 manifest_sha256=hashlib.sha256(frozen_text.encode()).hexdigest(),
                 source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 versions={x:importlib.metadata.version(x) for x in ('sympy','gmpy2')},
                 controls=[],target=manifest,arms=[],quantum=quantum_gate(RSA2048),
                 external_compute_spend=0,qpu_jobs=0,hosted_ci_jobs_requested=0,
                 status='STARTED',general_RSA_break=False)
    def save():output.write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    try:
        receipt['controls']=controls();save()
        if control_only:
            receipt['status']='CONTROLS_PASS_TARGET_NOT_RUN';save();return
        for method,budget in PLAN:
            emit(event='target_arm_start',method=method,seconds=budget)
            arm=run_arm(RSA2048,65537,method,budget)
            receipt['arms'].append(arm);save()
            emit(event='target_arm_result',method=method,status=arm['status'])
            if arm.get('factors'):
                receipt['certificate']=validate_recovery(RSA2048,65537,arm['factors'])
                receipt['status']='PUBLISHED_RSA2048_FACTOR_FOUND';receipt['general_RSA_break']=False
                save();return
        receipt['status']='RSA2048_UNSOLVED_WITHIN_BUDGET';save()
        emit(event='final',status=receipt['status'],spent=0,qpu_jobs=0)
    except Exception as exc:
        receipt.update(status='SOFTWARE_FAILURE',error=repr(exc));save();raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--worker',choices=[m for m,_ in PLAN])
    p.add_argument('--budget',type=float,default=30)
    p.add_argument('--output',default='results/rsa_zero_cost_20261030/attempt.json')
    p.add_argument('--controls-only',action='store_true');args=p.parse_args()
    if args.worker:worker(args.worker,args.budget)
    else:main(args.output,args.controls_only)
