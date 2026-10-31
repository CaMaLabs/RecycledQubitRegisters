#!/usr/bin/env python3
"""Bit-exact host checks of a pinned independent GPU arithmetic header.

Tests the existing templated core at K=33 without changing or executing the
upstream GPU launcher, which explicitly rejects RSA-2048-sized inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile

COMMIT = '22e7470a0b9b3b5d0e696032e0208ae8bb2b010f'


def run(upstream,output):
    root = Path(upstream).resolve()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()!=COMMIT:
        raise ValueError('Unpinned CADO fork')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():
        raise ValueError('Modified CADO source')
    header = root/'misc/gpu_prefactor/gpu_ecm_mp.cuh'
    bridge = Path(__file__).with_name('cado_montgomery_host_bridge.cpp')
    rng = random.Random(67331603)
    tests = []
    mask = (1<<64)-1
    for k,bits in ((2,126),(4,254),(8,510),(16,1022),(33,2048)):
        for i in range(512):
            n = rng.getrandbits(bits-1)|(1<<(bits-1))|1
            a = (0,1,n-1,n-2)[i] if i<4 else rng.randrange(n)
            b = n-1 if i<4 else rng.randrange(n)
            assert n < 1<<(64*k-2)
            np = -pow(n&mask,-1,1<<64)&mask
            def limbs(v):
                return ' '.join(format(v>>(64*j)&mask,'x') for j in range(k))
            line = f'{k} {np:x} {limbs(n)} {limbs(a)} {limbs(b)}'
            expected = a*b*pow(1<<(64*k),-1,n)%n
            tests.append((k,bits,line,(expected,expected,(a+b)%n,(a-b)%n)))
    with tempfile.TemporaryDirectory(prefix='qrr-cado-core-') as temporary:
        binary = Path(temporary)/'bridge'
        command = ['g++','-O2','-std=c++17','-I',str(header.parent),str(bridge),'-o',str(binary)]
        subprocess.run(command,check=True,capture_output=True,text=True,timeout=90)
        answer = subprocess.run([str(binary)],input='\n'.join(t[2] for t in tests)+'\n',
                                capture_output=True,text=True,check=True,timeout=60)
    lines = answer.stdout.splitlines()
    assert len(lines)==len(tests)
    for (k,bits,_,expected),line in zip(tests,lines):
        words = [int(v,16) for v in line.split()]
        assert len(words)==4*k
        actual = tuple(sum(words[c*k+j]<<(64*j) for j in range(k)) for c in range(4))
        assert actual==expected,(k,bits,actual,expected)
    result = dict(status='PASS',upstream='https://github.com/doublegate/cado-nfs-modern',commit=COMMIT,
        header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        bridge_sha256=hashlib.sha256(bridge.read_bytes()).hexdigest(),
        modulus_cases=len(tests),primitive_comparisons=4*len(tests),
        cases_2048_bits=sum(t[1]==2048 for t in tests),
        operations=['Montgomery multiply','aliased Montgomery multiply','modular add','modular subtract'],
        compiled_for='CPU host path of the shared header',gpu_execution=False,
        upstream_launcher_max_bits=1022,core_2048_test_limbs=33,
        nvcc_available=shutil.which('nvcc') is not None,nvidia_smi_available=shutil.which('nvidia-smi') is not None,
        factorization_attempted=False,RSA2048_break=False,external_spend=0)
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',required=True)
    p.add_argument('--output',default='results/indie_diamond_20261030/cado_core.json')
    a=p.parse_args()
    run(a.upstream,a.output)
