#!/usr/bin/env python3
"""LWE-style basis rotation on chemistry copy/factor columns.
Rotate columns of w and H2_I together. Sum_c X_c tensor X_c,
sum_c W_c X_c and sum_c W_c^2 are invariant. Thus fixed angle circuits,
Hamiltonian residuals and SOS energy remain unchanged mathematically,
while the L1-based LCU normalization can improve.
Exact 2D coordinate minimization tests every abs-value breakpoint and
stationary point on each smooth piece, not just a local gradient step.
"""
import argparse,json,time
from pathlib import Path
import numpy as np

def objective(A,B,angles):
 angles=np.atleast_1d(angles);c=np.cos(angles);s=np.sin(angles)
 return np.square(np.abs(A[:,None]*c+B[:,None]*s).sum(axis=0))+np.square(np.abs(B[:,None]*c-A[:,None]*s).sum(axis=0))

def best_angle(A,B):
 period=np.pi/2;active=(abs(A)+abs(B))>1e-15
 breaks=np.unique(np.r_[0.,np.mod(np.arctan2(-A[active],B[active]),period),period]);mid=(breaks[:-1]+breaks[1:])/2;c=np.cos(mid);s=np.sin(mid)
 sx=np.sign(A[:,None]*c+B[:,None]*s);sy=np.sign(B[:,None]*c-A[:,None]*s)
 aa=np.einsum('i,ij->j',A,sx);bb=np.einsum('i,ij->j',B,sx);dd=np.einsum('i,ij->j',B,sy);ee=-np.einsum('i,ij->j',A,sy)
 q=.5*(aa*aa+dd*dd-bb*bb-ee*ee);r=aa*bb+dd*ee;theta=np.mod(.5*(np.arctan2(r,q)+np.pi),np.pi);inside=(theta>breaks[:-1]+1e-14)&(theta<breaks[1:]-1e-14)
 angles=np.r_[breaks[:-1],theta[inside]];scores=objective(A,B,angles);j=int(scores.argmin());return float(angles[j]),float(scores[j])

def selftest():
 rng=np.random.default_rng(980980)
 for _ in range(12):
  A=rng.normal(size=19);B=rng.normal(size=19);A[rng.random(19)<.2]=0;B[rng.random(19)<.2]=0;angle,cost=best_angle(A,B);grid=objective(A,B,np.linspace(0,np.pi/2,10001)).min();assert cost<=grid+1e-8,(cost,grid)
  z=np.c_[A,B];c=np.cos(angle);s=np.sin(angle);rot=np.array([[c,-s],[s,c]]);changed=z@rot;assert np.allclose(changed@changed.T,z@z.T,atol=1e-12)
 return {'piecewise_minimizer_cases':12,'grid_points_per_case':10001,'Gram_invariance':'PASS'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--passes',type=int,default=8);p.add_argument('--seed',type=int,default=98098);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);print('K098_GAUGE_SELFTEST',json.dumps(selftest()),flush=True)
 data={k:np.array(x) for k,x in np.load(a.source).items()};w=data['W'];y=data['H2_I'];R,B,C=w.shape;aug=np.concatenate((w,y[:,None,:]),axis=1);initial=aug.copy();start=time.monotonic();history=[];events=[];rng=np.random.default_rng(a.seed)
 before=float(np.square(np.abs(aug).sum(axis=1)).sum()/4)
 for sweep in range(a.passes):
  gain=0.;count=0;pairs=[(r,i,j) for r in range(R) for i in range(C) for j in range(i+1,C)];rng.shuffle(pairs)
  for r,i,j in pairs:
   A=aug[r,:,i].copy();Bcol=aug[r,:,j].copy();old=float(objective(A,Bcol,0.)[0]);theta,new=best_angle(A,Bcol)
   if old-new<=max(1e-12,old*1e-12):continue
   c=np.cos(theta);s=np.sin(theta);aug[r,:,i]=c*A+s*Bcol;aug[r,:,j]=c*Bcol-s*A;delta=(old-new)/4;gain+=delta;count+=1;events.append({'pass':sweep,'group':r,'col_a':i,'col_b':j,'theta':theta,'lambda_h2_saved':delta})
  current=float(np.square(np.abs(aug).sum(axis=1)).sum()/4);row={'pass':sweep,'accepted':count,'lambda_h2':current,'pass_saved':gain,'total_saved':before-current,'elapsed_s':time.monotonic()-start};history.append(row);print('K098_GAUGE_PASS',json.dumps(row),flush=True)
  (a.out/'gauge_history.json').write_text(json.dumps(history,indent=2))
  if not count:break
 data['W']=aug[:,:-1,:];data['H2_I']=aug[:,-1,:];data['offset_W']=data['H2_I']-data['W'].sum(axis=1);np.savez(a.out/'submission.npz',**data)
 gram_before=np.einsum('rbc,rdc->rbd',initial,initial);gram_after=np.einsum('rbc,rdc->rbd',aug,aug);drift=float(np.max(np.abs(gram_after-gram_before)));summary={'status':'NUMERICAL_GAUGE_CANDIDATE_ONLY','initial_lambda_h2':before,'final_lambda_h2':float(np.square(np.abs(aug).sum(axis=1)).sum()/4),'rotations':len(events),'max_augmented_Gram_drift':drift,'elapsed_s':time.monotonic()-start,'history':history,'warning':'Require untouched verifier and exact full resource score before promotion.'};(a.out/'gauge_summary.json').write_text(json.dumps(summary,indent=2));(a.out/'rotations.json').write_text(json.dumps(events,indent=2));print('K098_GAUGE_RESULT',json.dumps(summary),flush=True)
