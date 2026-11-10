#!/usr/bin/env python3
"""Fixed-angle chemistry offset refit with analytic eigensystem derivatives.
This is a numerical candidate search, followed by the untouched full verifier.
The Hamiltonian, angle circuits, both residual gates, and gap floor are fixed.
The two-body weights are fixed, so error_2 is unchanged. Only H2_I offsets move.
"""
import argparse,json,sys,time,hashlib,shutil
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment,minimize
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--verifiers',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--iterations',type=int,default=300);p.add_argument('--radius',type=float,default=.02);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(a.verifiers))
from dfthcsos import verify as v
from dfthcsos.scoreinfra import dfthc_math as dm
from dfthcsos.scoreinfra.circuits import load_circuits,recover_words_from_circuits
start=time.monotonic();inp=v.load_inputs(a.source/'submission.npz');params={k:np.array(x) for k,x in np.load(a.source/'submission.npz').items()};edges=params['tree_edges'];brot=int(params['brot']);circs=load_circuits(a.source)
words,layout,toff=recover_words_from_circuits(circs,num_vectors=inp.num_vectors,num_angles=75,shots_per_address=2,seed=12345)
assert np.array_equal(words,params['angle_words']),'stored words differ from actually loaded words'
vec=dm.reconstruct_u_vectors(words.astype(float)/(2**(brot-1)),edges);vec/=np.linalg.norm(vec,axis=1,keepdims=True);one,u=dm.split_u_vectors(vec,inp.w);X=dm.reconstruct_x(u,inp.w);X=np.tril(X)+np.swapaxes(np.tril(X,-1),-1,-2);X=X.reshape(-1,76,76);sumw=inp.w.sum(axis=1).ravel();absw=np.abs(inp.w).sum(axis=1).ravel();offset0=np.array(params['H2_I']).ravel();fixed=inp.ref['h1_thc']-.5*inp.ref['electrons']*inp.S+inp.beta_1*np.eye(76);Xflat=X.reshape(len(X),-1);ec=inp.ref['ecore'];eta=inp.ref['electrons'];floor=v.E_GAP_FLOOR;baseline=v.evaluate_words(inp,words,edges,brot);(a.out/'baseline_metrics.json').write_text(json.dumps(baseline,indent=2));print('K098_BASE_METRICS',json.dumps(baseline),flush=True)
cache={};evaluations=0;history=[]
def evaluate(offset):
 global evaluations
 key=offset.tobytes()
 if key in cache:return cache[key]
 native=offset-sumw;H=fixed-(native@Xflat).reshape(76,76);lam,U=np.linalg.eigh(H);row,col=linear_sum_assignment(-np.abs(one@U));matched=np.empty(76);matched[row]=lam[col];R=(one.T*matched)@one-H;errsq=float(np.sum(R*R));labs=float(np.abs(lam).sum());Lambda=labs+.25*float(np.square(absw+np.abs(offset)).sum());gap=float(v.UPPER_ENERGY-ec+eta*inp.beta_1+labs-lam.sum()+.5*np.dot(native,native));eff=np.sqrt(max(gap*(2*Lambda-gap),1e-100))
 # d lambda_j / d offset_i = -u_j^T X_i u_j.
 dl=-np.einsum('pj,ipq,qj->ij',U,X,U,optimize=True);dlabs=dl@np.sign(lam);dLambda=dlabs+.5*(absw+np.abs(offset))*np.sign(offset);dgap=dlabs-dl.sum(axis=1)+native;deff=(gap*dLambda+(Lambda-gap)*dgap)/eff
 vRv=np.einsum('jp,pq,jq->j',one,R,one,optimize=True);weights=np.empty(76);weights[col]=vRv[row];derr=2*(dl@weights+Xflat@R.ravel());r={'objective':eff,'gradient':deff,'errsq':errsq,'err_gradient':derr,'gap':gap,'gap_gradient':dgap,'Lambda':Lambda,'Lambda_gradient':dLambda};cache.clear();cache[key]=r;evaluations+=1;return r
base=evaluate(offset0);print('K098_SMALL_EIGENVALUES',np.linalg.eigvalsh(fixed-((offset0-sumw)@Xflat).reshape(76,76))[:15].tolist(),flush=True);assert abs(base['objective']-baseline['lambda_eff'])<1e-7;assert abs(np.sqrt(base['errsq'])-baseline['error_1'])<1e-8
# Baseline has abs-value kinks near zero offsets. Check gradients at an
# independently perturbed point away from those kinks before optimization.
rng=np.random.default_rng(98098);checks=[]
probe=offset0+rng.normal(scale=1e-3,size=len(offset0));probe_base=evaluate(probe)
for _ in range(4):
 direction=rng.normal(size=len(offset0));direction/=np.linalg.norm(direction);step=1e-6;left=evaluate(probe-step*direction);right=evaluate(probe+step*direction)
 check={name:{'finite_difference':(right[name]-left[name])/(2*step),'analytic':float(np.dot(probe_base[grad],direction))} for name,grad in [('objective','gradient'),('gap','gap_gradient'),('errsq','err_gradient')]};checks.append(check)
 print('K098_GRADIENT_CHECK',check,flush=True)
 for name in check:
  aa=check[name];assert abs(aa['finite_difference']-aa['analytic'])<max(2e-5,abs(aa['analytic'])*.02),(name,aa)
(a.out/'gradient_checks.json').write_text(json.dumps(checks,indent=2));best=offset0.copy();best_val=base['objective'];iters=0
scale=baseline['lambda_eff'];limit=.020**2
constraints=[{'type':'ineq','fun':lambda z:(limit-evaluate(z)['errsq'])/limit,'jac':lambda z:-evaluate(z)['err_gradient']/limit},{'type':'ineq','fun':lambda z:evaluate(z)['gap']-floor-2e-10,'jac':lambda z:evaluate(z)['gap_gradient']},{'type':'ineq','fun':lambda z:evaluate(z)['Lambda']-v.LAMBDA_FLOOR-1e-8,'jac':lambda z:evaluate(z)['Lambda_gradient']}]
def callback(z):
 global best,best_val,iters
 iters+=1;r=evaluate(z);feasible=r['errsq']<=limit and r['gap']>floor and r['Lambda']>v.LAMBDA_FLOOR
 if feasible and r['objective']<best_val:best=z.copy();best_val=r['objective'];np.save(a.out/'best_offsets.npy',best)
 history.append({'iteration':iters,'lambda_eff':float(r['objective']),'error_1':float(np.sqrt(r['errsq'])),'gap':float(r['gap']),'feasible':bool(feasible),'best_lambda_eff':float(best_val)})
 (a.out/'history.json').write_text(json.dumps(history,indent=2))
 if iters%10==0:print('K098_REFIT',history[-1],flush=True)
res=minimize(lambda z:evaluate(z)['objective']/scale,offset0,jac=lambda z:evaluate(z)['gradient']/scale,method='SLSQP',bounds=[(x-a.radius,x+a.radius) for x in offset0],constraints=constraints,callback=callback,options={'maxiter':a.iterations,'ftol':1e-13,'disp':False})
callback(res.x);params['H2_I']=best.reshape(params['H2_I'].shape);params['offset_W']=params['H2_I']-params['W'].sum(axis=1);np.savez(a.out/'submission.npz',**params)
# Independently re-evaluate the candidate with the original official math.
newinp=v.load_inputs(a.out/'submission.npz');metrics=v.evaluate_words(newinp,words,edges,brot);summary={'status':'NUMERIC_CANDIDATE_ONLY','baseline':baseline,'candidate':metrics,'improvement_ratio':baseline['lambda_eff']/metrics['lambda_eff'],'all_accuracy_gates_pass':v.passes_accuracy(metrics),'iterations':iters,'evaluations':evaluations,'optimizer_success':bool(res.success),'optimizer_message':str(res.message),'elapsed_s':time.monotonic()-start,'limitation':'No candidate promoted until complete unchanged verifier passes at default shots.'};(a.out/'refit_summary.json').write_text(json.dumps(summary,indent=2));print('K098_REFIT_RESULT',json.dumps(summary),flush=True)
