#!/usr/bin/env python3
"""Try retained-product variants on every distinct compiler-matrix circuit.
Even variants losing alone are retained for combined cleanup/lifetime tests.
"""
import argparse,json,hashlib
from pathlib import Path
import kickmix as km
import retained_products as cache
import symbolic_state as symbolic
import clean_lifetimes as lifetime
import commuting_cancellation as commute
from run_transfer_matrix import load,test_circuit,resources,canon,REPO
p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--verifiers',type=Path,required=True);a=p.parse_args();m=load('cache_decode',REPO/'k028/k063_nonlinear_gate_cancellation.py');prior=json.loads((a.results/'matrix.json').read_text());out=[];unique={}
for r in prior:
 if not r.get('tag'):continue
 original=(a.results/(r['tag']+'.kmx')).read_text().splitlines(keepends=True)
 for measurement in (False,True):
  for affine in (False,True):
   lines,report=cache.transform(original,measurement,affine=affine)
   for cleanup in (False,True):
    item={'source_tag':r['tag'],'measurement':measurement,'affine':affine,'combined_cleanup':cleanup,'cache':{k:v for k,v in report.items() if k!='groups'}}
    working=lines
    if cleanup and report['groups']:
     working=commute.optimize(working,m.decode)[0];working=symbolic.transform(working)[0];working=lifetime.compact(working)[0]
    working=canon(working);key=hashlib.sha256(''.join(working).encode()).hexdigest();item['text_sha256']=key
    if key in unique:item.update(status='DUPLICATE',same_as=unique[key])
    elif not report['groups']:item['status']='NO_CACHE_GROUPS';unique[key]=r['tag']
    else:
     tag=f'cache_{len(out):03d}';item['tag']=tag;unique[key]=tag;p=a.results/(tag+'.kmx');p.write_text(''.join(working));c=km.Circuit.from_file(str(p),format='kmx');binary=a.results/(tag+'.kmb');c.to_file(str(binary),format='kmb');item['resources']=resources(c,working);v=test_circuit(a.verifiers/'invsqrt/verify_submission_invsqrt.py',binary,4095,2,12345,1200);item['prefix']=v;item['status']='PASS_PREFIX' if v.get('status')=='PASS' else 'FAIL_PREFIX';print('K096_CACHE_CASE',json.dumps({'tag':tag,'source':r['tag'],'measurement':measurement,'affine':affine,'cleanup':cleanup,'saved':report['ccx_saved'],'q':c.num_qubits,'status':item['status'],'score':v.get('score')}),flush=True)
    out.append(item)
    (a.results/'cache_extension.json').write_text(json.dumps(out,indent=2))
print('K096_CACHE_DONE',len(out),flush=True)
