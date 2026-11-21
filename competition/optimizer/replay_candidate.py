#!/usr/bin/env python3
"""Reconstruct retained candidates from proof records without intermediate KMXs."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from competition.optimizer.autonomous.core import Gate,parse,prove,sha


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
        proof=json.loads(row['proof']);experiment=db.execute('SELECT * FROM experiments WHERE key=?',(proof['task'],)).fetchone()
        detail=json.loads(experiment['detail']);replacement=[Gate(g['op'],tuple(g['q'])) for g in detail['gates']]
        lines=raw.decode('ascii').splitlines(keepends=True);start,end=proof['region']
        before=[parse(x) for x in lines[start:end]]
        if any(g is None for g in before) or prove(before,replacement)['status']!='EXACT':
            raise ValueError('Replay proof failed')
        raw=''.join(lines[:start]+[g.text() for g in replacement]+lines[end:]).encode('ascii')
        if sha(raw)!=row['sha']: raise ValueError('Replay digest mismatch')
    output=Path(output)
    if output.exists(): raise ValueError('Refusing to overwrite existing output')
    output.write_bytes(raw)
    return {'sha256':sha(raw),'exact_steps':len(chain),'official_status':'SEE_ORIGINAL_RECEIPTS'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('database','source','candidate','output'):p.add_argument('--'+key,required=True)
    a=p.parse_args();print(json.dumps(replay(a.database,a.source,a.candidate,a.output)))
