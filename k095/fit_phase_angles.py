#!/usr/bin/env python3
"""Joint full-domain angle fit. Requires numpy, scipy, kickmix. Credit original circuit authors; see README."""
import numpy as np,json,sys,argparse
from pathlib import Path
p=argparse.ArgumentParser(description='K095 full-domain phase minimax refit; does not establish verifier PASS')
p.add_argument('--work',type=Path,required=True);p.add_argument('--drop',type=int,default=None);a=p.parse_args()
from scipy.optimize import linprog
from fractions import Fraction
from decimal import Decimal,localcontext
A=np.load(a.work/'features.npy',mmap_mode='r');E=np.load(a.work/'error.npy',mmap_mode='r')*1e12;cols=json.load(open(a.work/'columns.json'));idx=[i for i,c in enumerate(cols) if Fraction(c['angle']).denominator>4];A=A[:,idx];n=len(E)
T=1e12*2**-24/np.sqrt(np.arange(1,n+1,dtype=float))
sel=np.unique(np.r_[np.arange(2048),np.linspace(0,n-1,4096,dtype=int),np.argsort(T-np.abs(E))[:4096]])
best=None
for it in range(15):
 aa=A[sel].astype(float);ee=E[sel];tt=T[sel];d=len(idx)
 r=linprog(np.r_[np.zeros(d),-1],A_ub=np.r_[np.c_[aa,np.ones(len(sel))],np.c_[-aa,np.ones(len(sel))]],b_ub=np.r_[tt-ee,tt+ee],bounds=[((-float(Fraction(cols[i]['angle']))*5e11,)*2 if i==a.drop else (-10000,10000)) for i in idx]+[(None,None)],method='highs')
 if not r.success:raise RuntimeError(r.message)
 delta=r.x[:-1];pred=E.copy()
 for j,x in enumerate(delta):pred+=A[:,j]*x
 slack=T-np.abs(pred);worst=np.argsort(slack)[:2048];print(it,'rows',len(sel),'lp',r.x[-1],'full_min',slack.min(),'worst_x',int(worst[0]+1),flush=True)
 best=delta
 if slack.min()>=r.x[-1]-1e-5:break
 sel=np.unique(np.r_[sel,worst])
lines=open(a.work/'source.kmx').readlines()
for i,v in zip(idx,best):
 c=cols[i];ang=Fraction(0) if i==a.drop else Fraction(c['angle'])+2*Fraction(float(v)*1e-12);lines[c['line']]=f"Z_POW q28 {Decimal(ang.numerator)/Decimal(ang.denominator):.50f}\n"
open(a.work/'refit.kmx','w').writelines(lines)
json.dump({'columns':idx,'delta_turns':(best*1e-12).tolist(),'min_slack_turns':float(slack.min()*1e-12),'lp_slack_turns':float(r.x[-1]*1e-12),'worst_x':int(worst[0]+1)},open(a.work/'fit.json','w'),indent=2)
import kickmix as km
c=km.Circuit.from_file(str(a.work/'refit.kmx'),format='kmx');c.to_file(str(a.work/'refit.kmb'),format='kmb')
