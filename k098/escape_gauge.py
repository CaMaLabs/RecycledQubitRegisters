#!/usr/bin/env python3
"""Coupled-copy gauge search: retain pairwise-negative rotations in combinations.
Random SO(k) kicks followed by exact pair-coordinate minimization on k=3/4
columns. Accept only verified direct L1-cost reductions. A final untouched
chemistry verifier is still required; no accuracy floor is altered.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from orthogonal_copy_gauge import best_angle
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--trials',type=int,default=1000);p.add_argument('--columns',type=int,default=3);p.add_argument('--starts',type=int,default=2);p.add_argument('--sweeps',type=int,default=8);p.add_argument('--seed',type=int,default=98198);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);data={k:np.array(v) for k,v in np.load(a.source).items()};aug=np.concatenate((data['W'],data['H2_I'][:,None,:]),axis=1);initial=aug.copy();R,M,C=aug.shape;rng=np.random.default_rng(a.seed);start=time.monotonic();records=[];accepted=[]
def cost(x):return float(np.square(np.abs(x).sum(axis=0)).sum()/4)
before=sum(cost(x) for x in aug);best_total=before
for trial in range(a.trials):
 r=int(rng.integers(R));first=int(rng.integers(C));norm=np.linalg.norm(aug[r],axis=0);similar=np.abs(aug[r].T@aug[r,:,first])/(norm*max(norm[first],1e-30)+1e-30);similar[first]=0;prob=similar+1e-3;prob[first]=0;cols=np.r_[first,rng.choice(C,size=a.columns-1,replace=False,p=prob/prob.sum())];cols=np.unique(cols)
 if len(cols)!=a.columns:continue
 base=aug[r][:,cols].copy();base_cost=cost(base);best=base;new_cost=base_cost
 for restart in range(a.starts):
  Q,_=np.linalg.qr(rng.normal(size=(a.columns,a.columns)));work=base@Q
  for sweep in range(a.sweeps):
   changed=0
   pairs=[(i,j) for i in range(a.columns) for j in range(i+1,a.columns)];rng.shuffle(pairs)
   for i,j in pairs:
    A=work[:,i].copy();B=work[:,j].copy();old=float(np.square(np.abs(A).sum())+np.square(np.abs(B).sum()));theta,new=best_angle(A,B)
    if old-new<=max(1e-13,old*1e-13):continue
    c=np.cos(theta);s=np.sin(theta);work[:,i]=c*A+s*B;work[:,j]=c*B-s*A;changed+=1
   if not changed:break
  candidate=cost(work)
  if candidate<new_cost:best=work.copy();new_cost=candidate
 if base_cost-new_cost>max(1e-10,base_cost*1e-10):
  aug[r][:,cols]=best;delta=base_cost-new_cost;best_total-=delta;accepted.append({'trial':trial,'group':r,'columns':cols.tolist(),'lambda_h2_saved':delta});print('K098_ESCAPE_ACCEPT',json.dumps(accepted[-1]),flush=True)
 if trial%100==0:
  row={'trial':trial,'accepted':len(accepted),'lambda_h2_saved':before-best_total,'elapsed_s':time.monotonic()-start};records.append(row);(a.out/'history.json').write_text(json.dumps(records,indent=2));print('K098_ESCAPE_PROGRESS',json.dumps(row),flush=True)
data['W']=aug[:,:-1,:];data['H2_I']=aug[:,-1,:];data['offset_W']=data['H2_I']-data['W'].sum(axis=1);np.savez(a.out/'submission.npz',**data);g0=np.einsum('rbc,rdc->rbd',initial,initial);g1=np.einsum('rbc,rdc->rbd',aug,aug);summary={'status':'NUMERIC_GAUGE_CANDIDATE_ONLY','trials':a.trials,'columns':a.columns,'starts':a.starts,'sweeps':a.sweeps,'seed':a.seed,'initial_lambda_h2':before,'final_lambda_h2':sum(cost(x) for x in aug),'max_Gram_drift':float(np.max(np.abs(g1-g0))),'accepted':accepted,'elapsed_s':time.monotonic()-start};(a.out/'escape_summary.json').write_text(json.dumps(summary,indent=2));print('K098_ESCAPE_RESULT',json.dumps(summary),flush=True)
