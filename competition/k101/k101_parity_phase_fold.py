#!/usr/bin/env python3
"""K101: exact phase-parity folding through a CNOT network.

A Z_POW on a wire applies phase to a Boolean parity of the segment input
bits. Track the affine linear parity through unconditional CX gates; when
two rotations use the same parity, their angles may combine at the earlier
site without altering the rest of the circuit. All other instructions,
including X, measurements, declarations and conditional gates, end the
segment. Original baseline is pinned; no score claim until full verification.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE_PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
CX=re.compile(r'^CX\s+q(\d+)\s+q(\d+)\s*$',re.I)
ZP=re.compile(r'^Z_POW\s+q(\d+)\s+([^\s]+)\s*$',re.I)
QB=re.compile(r'\bq(\d+)\b')
def digest(buf):return hashlib.sha256(buf).hexdigest()

def fold(lines):
    out=list(lines)
    signatures={}
    # Map current wire value to parity of the segment's starting wires.
    parity={}
    merges=[]
    allowed=0
    for idx,line in enumerate(lines):
        text=line.strip()
        m=CX.fullmatch(text)
        z=ZP.fullmatch(text)
        if m:
            c,t=map(int,m.groups())
            if c==t:
                signatures.clear();parity.clear();continue
            if c not in parity:parity[c]=1<<c
            if t not in parity:parity[t]=1<<t
            parity[t]^=parity[c]
            allowed+=1
            continue
        if z:
            q=int(z.group(1))
            try: angle=Decimal(z.group(2))
            except Exception:
                signatures.clear();parity.clear();continue
            mask=parity.setdefault(q,1<<q)
            if mask in signatures:
                prev,prev_angle=signatures[mask]
                combined=prev_angle+angle
                if combined==0:
                    out[prev]=''
                    signatures.pop(mask)
                else:
                    out[prev]=f'Z_POW q{int(ZP.fullmatch(lines[prev].strip()).group(1))} {format(combined,"f")}\n'
                    signatures[mask]=(prev,combined)
                out[idx]=''
                merges.append({'first_line':prev+1,'second_line':idx+1,'parity_mask_hex':hex(mask),
                               'angles':[str(prev_angle),str(angle)],'combined':str(combined)})
            else:
                signatures[mask]=(idx,angle)
            allowed+=1
            continue
        # Every other operation is a barrier; do not cross control flow
        # or other arithmetic / state preparation / measurement instructions.
        signatures.clear()
        parity.clear()
    return out,merges,allowed

def selftest():
    cases=[
      (['Z_POW q0 0.125\n','CX q0 q1\n','CX q0 q1\n','Z_POW q0 0.25\n'],1),
      (['Z_POW q1 0.125\n','CX q0 q1\n','Z_POW q1 0.25\n'],0),
      (['CX q0 q1\n','Z_POW q1 0.125\n','CX q0 q1\n','Z_POW q1 0.25\n'],0),
      (['Z_POW q0 0.125\n','HMR q2 b0\n','Z_POW q0 0.25\n'],0),
      (['Z_POW q0 0.125\n','Z_POW q0 -0.125\n'],1),
      (['Z_POW q0 0.125\n','CX q0 q1 if b1\n','Z_POW q0 0.25\n'],0),
    ]
    for lines,n in cases:
        out,events,_=fold(lines)
        assert len(events)==n,(lines,events)
        assert len(out)==len(lines)
    print('K101_SELFTEST PASS 6 safe parity folding cases',flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',type=Path,default=ROOT/'competition/k098/results/helios_immutable.kmx')
    p.add_argument('--out',type=Path,default=ROOT/'competition/k101/results/helios_parity_fold.kmx')
    a=p.parse_args()
    selftest()
    raw=a.baseline.read_bytes()
    if digest(raw)!=BASE_PIN:raise SystemExit('Baseline SHA-256 mismatch; refusing')
    lines=raw.decode('utf-8').splitlines(keepends=True)
    transformed,events,allowed=fold(lines)
    summary={'status':'UNVERIFIED_CANDIDATE' if events else 'NO_FOLDS',
      'source_sha256':digest(raw),'candidate_sha256':digest(''.join(transformed).encode()),
      'total_source_lines':len(lines),'cnot_and_rotation_instructions_scanned':allowed,
      'folded_rotation_pairs':len(events),
      'removed_rotation_instructions':len(events),
      'events':events}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    audit=a.out.with_suffix('.json')
    audit.write_text(json.dumps(summary,indent=2)+'\n')
    if events:
        a.out.write_text(''.join(transformed))
    print('K101_RESULT',json.dumps({k:v for k,v in summary.items() if k!='events'}),flush=True)
    print('K101_EXAMPLES',json.dumps(events[:10]),flush=True)
    print('K101_NOTE does not establish executed rotation savings or verification',flush=True)
if __name__=='__main__':main()
