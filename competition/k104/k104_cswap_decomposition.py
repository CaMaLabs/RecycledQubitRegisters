#!/usr/bin/env python3
"""K104: exact controlled-SWAP decomposition candidate generator.

CSWAP(c,a,b) equals:
  CX a b; CCX c b a; CX a b
or
  CX b a; CCX c a b; CX b a

Creates candidate(s), never edits pinned baseline. Checks both identities
against all 8 basis states and random complex states using numpy.
Does not claim any Kickmix cost advantage. Full-domain validation required.

Avoid changing CSWAP instructions inside complex source syntax: only a
line that EXACTLY matches 'CSWAP qN qN qN' is touched.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
PAT=re.compile(r'^(\s*)CSWAP\s+q(\d+)\s+q(\d+)\s+q(\d+)\s*$',re.I)
STYLES=('a_to_b','b_to_a')

def cx(bits,c,t):bits[t]^=bits[c]
def ccx(bits,c1,c2,t):bits[t]^=bits[c1]&bits[c2]
def cswap(bits,c,a,b):
    if bits[c]:bits[a],bits[b]=bits[b],bits[a]

def logical(action,style):
    bits=list(action)
    if style=='native':
        cswap(bits,0,1,2)
    elif style=='a_to_b':
        cx(bits,1,2);ccx(bits,0,2,1);cx(bits,1,2)
    elif style=='b_to_a':
        cx(bits,2,1);ccx(bits,0,1,2);cx(bits,2,1)
    else:raise ValueError(style)
    return tuple(bits)

def selftest():
    # Permutations fix action on arbitrary complex states, not just bases.
    for n in range(8):
        bits=((n>>0)&1,(n>>1)&1,(n>>2)&1)
        for style in STYLES:
            assert logical(bits,style)==logical(bits,'native'),(n,style)
    rng=np.random.default_rng(104)
    for _ in range(100):
        state=rng.normal(size=8)+1j*rng.normal(size=8)
        state/=np.linalg.norm(state)
        def operated(style):
            out=np.empty_like(state)
            for n in range(8):
                bits=((n>>0)&1,(n>>1)&1,(n>>2)&1)
                result=logical(bits,style)
                target=sum(result[k]<<k for k in range(3))
                out[target]=state[n]
            return out
        ref=operated('native')
        for style in STYLES:
            assert np.max(abs(ref-operated(style)))==0
    print('K104_SELFTEST PASS 8 basis states; 100 complex-state samples; both orientations',flush=True)

def replacement(c,a,b,style,indent):
    if style=='a_to_b':
        return [f'{indent}CX q{a} q{b}\n',
                f'{indent}CCX q{c} q{b} q{a}\n',
                f'{indent}CX q{a} q{b}\n']
    return [f'{indent}CX q{b} q{a}\n',
            f'{indent}CCX q{c} q{a} q{b}\n',
            f'{indent}CX q{b} q{a}\n']

def build(lines,style,scope,line_min,line_max):
    out=[];count=0;locations=[]
    for i,line in enumerate(lines,1):
        m=PAT.fullmatch(line.strip()) # preserve only top-level matching syntax
        if m and line==line.strip()+'\n':
            # Regex captures empty indent for canonical one-line instructions.
            c,a,b=map(int,m.group(2,3,4))
            if len({c,a,b})==3 and (scope=='all' or line_min<=i<=line_max):
                out.extend(replacement(c,a,b,style,''));count+=1;locations.append(i)
                continue
        out.append(line)
    return out,count,locations

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out-dir',type=Path,default=ROOT/'competition/k104/results')
    p.add_argument('--scope',choices=['all','hotspot'],default='hotspot')
    p.add_argument('--line-min',type=int,default=53620)
    p.add_argument('--line-max',type=int,default=53700)
    a=p.parse_args()
    selftest()
    raw=a.baseline.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=PIN:raise SystemExit(f'Baseline fingerprint mismatch: {digest}')
    lines=raw.decode('utf-8').splitlines(keepends=True)
    summary=[]
    a.out_dir.mkdir(parents=True,exist_ok=True)
    for style in STYLES:
        candidate,count,locations=build(lines,style,a.scope,a.line_min,a.line_max)
        output=''.join(candidate).encode('utf-8')
        path=a.out_dir/f'helios_cswap_{a.scope}_{style}.kmx'
        audit_path=a.out_dir/f'helios_cswap_{a.scope}_{style}.audit.json'
        record={'status':'UNVERIFIED_CANDIDATE' if count else 'NO_MATCH',
                'scope':a.scope,'style':style,'baseline_sha256':digest,
                'candidate_sha256':hashlib.sha256(output).hexdigest(),
                'replaced_cswaps':count,'introduced_ccx':count,
                'introduced_cx':2*count,'candidate':str(path),
                'first_rewritten_lines':locations[:30],
                'line_range':[a.line_min,a.line_max],
                'warnings':[
                  'This rewrite is mathematically exact, not yet verified by Kickmix.',
                  'It may increase the executed-gate score; CSWAP and CCX costs must be measured.',
                  'Do not submit unless official full-domain verifier passes and score improves.']}
        audit_path.write_text(json.dumps(record,indent=2)+'\n')
        if count:path.write_bytes(output)
        summary.append(record)
        print('K104_CANDIDATE',json.dumps({k:record[k] for k in (
           'status','style','replaced_cswaps','introduced_ccx',
           'introduced_cx','candidate','candidate_sha256')}),flush=True)
    status='GENERATED_UNVERIFIED' if any(r['replaced_cswaps'] for r in summary) else 'NO_MATCH'
    print('K104_RESULT',json.dumps({'status':status,'candidates':len(summary),
       'scope':a.scope,'baseline_sha256':digest}),flush=True)

if __name__=='__main__':main()
