#!/usr/bin/env python3
"""Reconstruct the tested NPZ candidate from its pinned public source and patch."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--patch',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();patch=json.loads(a.patch.read_text());assert hashlib.sha256(a.source.read_bytes()).hexdigest()==patch['source_sha256'],'source factorization version mismatch';data={k:np.array(v) for k,v in np.load(a.source).items()};offset=np.array(patch['H2_I'],dtype=np.float64);assert offset.shape==data['H2_I'].shape;data['H2_I']=offset;data['offset_W']=offset-data['W'].sum(axis=1);a.out.parent.mkdir(parents=True,exist_ok=True);np.savez(a.out,**data)
