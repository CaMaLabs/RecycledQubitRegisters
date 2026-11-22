#!/usr/bin/env python3
"""Reconstruct retained candidates from proof records without intermediate KMXs."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from competition.optimizer.autonomous.core import gate_from_record, prove, sha
from competition.optimizer.autonomous.conditional import parse_region, render_region


def replay(database, source, candidate, output):
    db=sqlite3.connect(database);db.row_factory=sqlite3.Row
    chain=[];current=candidate;seen=set()
    while True:
        if current in seen: raise ValueError('Cyclic provenance')
        seen.add(current)
        row=db.execute('SELECT * FROM candidates WHERE sha=?',(current,)).fetchone()
        if not row: raise ValueError('Missing candidate provenance '+current)
        if row['parent'] is None:
            baseline=current;break
        chain.append(dict(row));current=row['parent']
    raw=Path(source).read_bytes()
    if sha(raw)!=baseline: raise ValueError('Baseline hash mismatch')
    for row in reversed(chain):
        proof=json.loads(row['proof']);experiment=db.execute('SELECT * FROM experiments WHERE key=?',(proof.get('task'),)).fetchone()
        if experiment is None or not experiment['detail']:
            raise ValueError('Missing replayable experiment for ' + row['sha'])
        detail=json.loads(experiment['detail']);replacement=[gate_from_record(g) for g in detail['gates']]
        lines=raw.decode('ascii').splitlines(keepends=True);start,end=proof['region']
        if not 0 <= start < end <= len(lines):
            raise ValueError('Invalid replay region')
        guard = proof.get('local', {}).get('guard')
        if guard != json.loads(experiment['config']).get('guard'):
            raise ValueError('Replay guard mismatch')
        before=parse_region(lines[start:end], guard)
        if any(g is None for g in before) or prove(before,replacement)['status']!='EXACT':
            raise ValueError('Replay proof failed')
        raw=''.join(lines[:start]+render_region(replacement, guard)+lines[end:]).encode('ascii')
        if sha(raw)!=row['sha']: raise ValueError('Replay digest mismatch')
    db.close()
    with Path(output).open('xb') as stream:
        stream.write(raw)
    return {'sha256':sha(raw),'exact_steps':len(chain),'official_status':'SEE_ORIGINAL_RECEIPTS'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('database','source','candidate','output'):p.add_argument('--'+key,required=True)
    a=p.parse_args();print(json.dumps(replay(a.database,a.source,a.candidate,a.output)))
