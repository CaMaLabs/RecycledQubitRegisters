#!/usr/bin/env python3
"""Extract full-domain features from a pinned, attributed public circuit. Requires numpy and kickmix."""
import kickmix as km,numpy as np,sys,time,json,argparse
from pathlib import Path
p=argparse.ArgumentParser(description='K095 full-domain phase-feature extraction; diagnostic circuit is NEVER a submission')
p.add_argument('--source',type=Path,required=True);p.add_argument('--verifiers',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--batch',type=int,default=6132)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
assert 3133452%a.batch==0, 'batch must divide full domain'
import hashlib
assert hashlib.sha256((a.verifiers/'invsqrt/verify_submission_invsqrt.py').read_bytes()).hexdigest()=='ddef520dec6b68d1cf0a6f328ddd36d79eb84570b9192cf3f7acaf073f06733a'
assert hashlib.sha256(a.source.read_bytes()).hexdigest()=='034c7c2a54d51e13aff6e62ec4c14997d3968b6c11122146c57290b1a1b8c7e2'
km.Circuit.from_file(str(a.source),format='kmb').to_file(str(a.out/'source.kmx'),format='kmx')
from fractions import Fraction
sys.path.insert(0,str(a.verifiers));from invsqrt.verify_submission_invsqrt import half_turns_to_units
lines=open(a.out/'source.kmx').readlines();new=[];columns=[]
for i,line in enumerate(lines):
 if line.startswith('Z_POW q28 '):
  diag=62+len(columns);columns.append({'line':i,'angle':line.split()[2]});new.append(f'CX q28 q{diag}\n')
 new.append(line)
open(a.out/'diagnostic.kmx','w').writelines(new)
c=km.Circuit.from_file(str(a.out/'diagnostic.kmx'),format='kmx');n=3133452;b=a.batch
A=np.lib.format.open_memmap(a.out/'features.npy',mode='w+',dtype='bool',shape=(n,len(columns)))
E=np.lib.format.open_memmap(a.out/'error.npy',mode='w+',dtype='float64',shape=(n,))
sim=km.Simulator(batch_size=b,seed=12345);sim.use_same_registers_as(c);xx=c.register_data['x'];t0=time.monotonic()
for start in range(0,n,b):
 xs=np.arange(start+1,start+b+1,dtype=np.uint64);sim.clear_for_shot();sim.write_across_shots(xx,((xs[None,:]>>np.arange(22,dtype=np.uint64)[:,None])&1).astype(bool));sim.do(c)
 A[start:start+b]=sim.read_across_shots(km.array([km.q(62+j) for j in range(len(columns))])).T
 theta=np.array([half_turns_to_units(sim.read_shot_phase(i)) for i in range(b)],dtype=np.uint64)
 target=np.array([int(np.rint((np.longdouble(1)/np.sqrt(np.longdouble(int(x))))*(2**64)))%(2**64) for x in xs],dtype=np.uint64)
 E[start:start+b]=(theta-target).view(np.int64).astype(np.float64)/(2**64)
 if start//b%50==0:print(start,round(time.monotonic()-t0,1),flush=True)
A.flush();E.flush();json.dump(columns,open(a.out/'columns.json','w'));print('DONE',len(columns),flush=True)
