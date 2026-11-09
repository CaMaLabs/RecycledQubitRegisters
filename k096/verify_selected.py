#!/usr/bin/env python3
"""Matched full-domain checks for representative combined transfer candidates."""
import argparse,json
from pathlib import Path
from run_transfer_matrix import test_circuit
p=argparse.ArgumentParser();p.add_argument('--verifiers',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--tags',nargs='+',required=True);a=p.parse_args()
for tag in a.tags:
 r={}
 for seed in (12345,23456):
  r[str(seed)]=test_circuit(a.verifiers/'invsqrt/verify_submission_invsqrt.py',a.results/(tag+'.kmb'),3133452,2,seed,1200)
  (a.results/(tag+'_full.json')).write_text(json.dumps(r,indent=2));print(tag,seed,r[str(seed)].get('status'),r[str(seed)].get('score'),flush=True)
