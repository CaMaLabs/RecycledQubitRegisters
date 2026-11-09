#!/usr/bin/env python3
"""Apply broader shared-product/shear synthesis to every distinct matrix result."""
import argparse,json
from pathlib import Path
import multioutput_anf as multi
import quadratic_windows as quadratic
from run_transfer_matrix import load,REPO
p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args();anf=load('extension_anf',REPO/'k028/k069_block_anf_synth.py');rows=[]
for r in json.loads((a.results/'matrix.json').read_text()):
 if not r.get('tag'):continue
 lines=(a.results/(r['tag']+'.kmx')).read_text().splitlines(keepends=True);candidate,st=multi.optimize(lines,anf,quadratic)
 rows.append({'tag':r['tag'],'source_chain':r['chain'],**st})
 if st['ccx_saved']:(a.results/(r['tag']+'_shear.kmx')).write_text(''.join(candidate))
(a.results/'multioutput_extension.json').write_text(json.dumps(rows,indent=2));print('K096_SHARED_PRODUCT',len(rows),'circuits',sum(r['ccx_saved'] for r in rows),'CCX saved')
