#!/usr/bin/env python3
"""Recover the public K098 historical fixture, never substitute it for K191."""
import argparse,hashlib,subprocess
from pathlib import Path
REF='7d3c1909c2ac3c725d8c0450095877334de3fcfb'
PATH='competition/k131/results/candidate_domain_identity_prefix.kmx'
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'

def recover(output):
    raw=subprocess.check_output(['git','show',REF+':'+PATH])
    lines=raw.splitlines(keepends=True)
    restored=b''.join(lines[:23]+[b'R q22\n']+lines[23:])
    if hashlib.sha256(restored).hexdigest()!=PIN: raise ValueError('Recovered fixture digest mismatch')
    path=Path(output)
    if path.exists(): raise ValueError('Refusing to overwrite an existing file')
    path.write_bytes(restored)
    print(PIN,str(path))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    a=p.parse_args();recover(a.output)
