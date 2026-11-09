#!/usr/bin/env python3
"""A114 construction transfer: separate exact 7-T ledger from Kaggle metric.
Static upper-bound accounting only; conditioned gates may not execute on every
shot. Rotation synthesis is kept separate, not silently charged as 7-T CCX.
No replacement circuit is emitted because Kaggle scores its native operations.
"""
import argparse,json,collections
from pathlib import Path
from fractions import Fraction
p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);a=p.parse_args();records=json.loads((a.results/'matrix.json').read_text());out=[]
for r in records:
 if not r.get('tag'):continue
 c=collections.Counter();z=collections.Counter()
 for line in (a.results/(r['tag']+'.kmx')).read_text().splitlines():
  s=line.split()
  if not s:continue
  c[s[0]]+=1
  if s[0]=='Z_POW':
   f=Fraction(s[2])%2
   if (f*2).denominator==1:z['clifford']+=1
   elif (f*4).denominator==1:z['t']+=1
   else:z['rotation']+=1
 nonlinear=sum(c[k] for k in ('CCX','CCZ','CSWAP'))
 out.append({'tag':r['tag'],'source_chain':r['chain'],'qubits':r['resources']['qubits'],'static_nonlinear_instances':nonlinear,'exact_7t_construction_t_upper_bound':7*nonlinear+z['t'],'rotation_instructions':z['rotation'],'static_cx_construction_upper_bound':c['CX']+6*nonlinear+2*c['CSWAP'],'additional_clean_ancillas':0,'warning':'Not Kaggle scoring; conditional instruction maxima, not shot averages. No constructive T-depth proof claimed.'})
(a.results/'constructive_t_ledger.json').write_text(json.dumps(out,indent=2));print('K096_A114_LEDGER',len(out),'circuits','T-upper-bound range',min(r['exact_7t_construction_t_upper_bound'] for r in out),max(r['exact_7t_construction_t_upper_bound'] for r in out))
