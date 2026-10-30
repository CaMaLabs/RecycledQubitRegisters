#!/usr/bin/env python3
"""Falsifiable audit of Bayesian Fibonacci refinement; local CPU, ZERO QPU.

Uses inspected upstream simulator as an external research dependency, not
vendored code. Tests global full-transcript midpoint reweighting against its
birth-local cell splitting. Neither finite quadrature is an exact posterior.
Includes a Cassini obstruction to cheap neighboring-accumulator alias checks.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
from mpmath import mp

UPSTREAM_SHA256='1baf81d1e8ff0c822ac5656f608e018ed4f6c2be50e9f1eecafc5e6397292306'
UPSTREAM_COMMIT='b4fee3bf08373bf759beec539d5a3ec78b63416f'
UPSTREAM_URL='https://github.com/katherinevankirk/streaming-regev'


def load_upstream(path):
    path=Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=UPSTREAM_SHA256:
        raise ValueError('upstream source differs from inspected snapshot')
    spec=importlib.util.spec_from_file_location('qrr_external_fibonacci_simulator',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def global_class(u):
    class GlobalPosterior(u.Posterior):
        """At every split, use width*L(entire transcript) at each child.

        log_evidence keeps all existing normalized cell weights on the same
        absolute scale. No true phase, factor, or order enters these methods.
        """
        def __init__(self,Q):
            self.log_evidence=0.
            super().__init__(Q)

        def normalise(self):
            w=self.log_weight[:self.count]
            correction=u.log_sum_exp(w)
            w-=correction
            self.log_evidence+=float(correction)

        def split(self,index,transcript):
            quarter=self.Q >> (7+int(self.depth[index]))
            children=(self.mid[index]-quarter,self.mid[index]+quarter)
            depth=int(self.depth[index])+1;new=self.count
            if new>=u.MAX_CELLS:raise ValueError('cell budget exceeded')
            self.mid[index]=children[0];self.mid.append(children[1])
            self.depth[index]=self.depth[new]=depth
            self.birth[index]=self.birth[new]=len(transcript)
            for slot,mid in ((index,children[0]),(new,children[1])):
                self.log_weight[slot]=(self.log_likelihood(mid,transcript)
                    -(5+depth)*math.log(2)-self.log_evidence)
            self.normalise()
    return GlobalPosterior


def full_weights(u,p,history):
    logw=np.array([p.log_likelihood(mid,history)-(5+int(depth))*math.log(2)
                   for mid,depth in zip(p.mid,p.depth[:p.count])])
    return np.exp(logw-u.log_sum_exp(logw))


def setup(u,n):
    # Match the authors' published parameter formulas, not our earlier coarse
    # uniform-grid diagnostic. P includes 24 numerical guard bits.
    mp.prec=64+math.ceil(3*math.sqrt(n))
    threshold=mp.mpf(2)**(3*mp.sqrt(n)-mp.mpf(5)/2)
    fib=u.fibonacci_numbers(2)
    while fib[-1]<=threshold:fib.append(fib[-1]+fib[-2])
    for _ in range(3):fib.append(fib[-1]+fib[-2])
    K=len(fib)-1
    P=max(16,fib[K].bit_length()+math.ceil(math.log2(u.MAX_CELLS))+24)
    mp.prec=P+32
    diameter=mp.mpf(2)**(P+mp.mpf(1)/2-3*mp.sqrt(n))
    return fib,K,P,1<<P,int(mp.floor(diameter))


def dense_reference(u,p,history,points=65536):
    """Independent uniform-grid likelihood quadrature, small frequencies only.

    Reports cell-mass errors, not a certified bound on the continuous posterior.
    Cell boundaries must be resolvable by this external diagnostic grid.
    """
    assert max(F for F,_,_ in history)<1000
    if int(p.depth[:p.count].max())+5>int(math.log2(points)):
        return dict(status='DENSE_GRID_TOO_COARSE')
    theta=(np.arange(points)+.5)/points;logw=np.zeros(points)
    for F,angle,bit in history:
        phase=(F*theta+angle/p.Q) % 1
        logw+=np.log(np.maximum((1+(-1)**bit*np.cos(2*math.pi*phase))/2,np.finfo(float).tiny))
    weights=np.exp(logw-logw.max());weights/=weights.sum()
    cumulative=np.concatenate(([0.],np.cumsum(weights)))
    masses=[]
    for i,mid in enumerate(p.mid):
        half=p.Q >> (6+int(p.depth[i]))
        lo=((mid-half)*points)//p.Q;hi=((mid+half)*points)//p.Q
        masses.append(cumulative[hi]-cumulative[lo])
    return dict(status='COMPLETE',points=points,
                birth_local_tv=float(abs(np.array(masses)-p.masses()).sum()/2),
                full_reweighted_tv=float(abs(np.array(masses)-full_weights(u,p,history)).sum()/2))


def score(u,p,diameter,theta,certified):
    mass,estimate=u.heaviest_arc(p,diameter)
    error=(estimate-2*theta) % (2*p.Q);error=min(error,2*p.Q-error)
    return dict(certified=bool(certified),accurate=bool(error<=diameter),
                accurate_and_certified=bool(certified and error<=diameter),
                falsely_certified=bool(certified and error>diameter),
                error_over_target=float(error/diameter),arc_mass=float(mass))


def trial(u,n,seed,global_splits):
    fib,K,P,Q,diameter=setup(u,n)
    rng=np.random.default_rng(seed)
    theta=int.from_bytes(rng.bytes((P+7)//8),'big') & ((1<<P)-1)
    p=global_class(u)(Q) if global_splits else u.Posterior(Q)
    history=[];shots={2:0};begin=time.perf_counter()
    reason=u.climb_ladder(p,history,shots,fib,K,theta,rng)
    if reason is None:
        _,certified,reason=u.certify_at_top(p,history,shots,fib,K,theta,diameter,rng)
    else:certified=False
    original=score(u,p,diameter,theta,certified)
    normalized=full_weights(u,p,history)
    discrepancy=float(abs(normalized-p.masses()).sum()/2)
    diagnostic=(dense_reference(u,p,history) if n==4 else None)
    # A separate no-extra-probe arm: globally reweight the final ORIGINAL
    # partition, without refitting the measurement sequence or adding cells.
    p_post=copy.deepcopy(p)
    p_post.log_weight[:p_post.count]=np.log(np.maximum(normalized,np.finfo(float).tiny))
    post_mass,_=u.heaviest_arc(p_post,diameter)
    posthoc=score(u,p_post,diameter,theta,post_mass>=1-u.DELTA_FINAL)
    if global_splits:assert discrepancy<1e-10
    return dict(n=n,seed=seed,K=K,arm='global_splits' if global_splits else 'upstream',
                result=original,posthoc_reweight=posthoc,probes=sum(shots.values()),
                cells=p.count,stop_reason=reason,full_transcript_midpoint_tv=discrepancy,
                dense_reference=diagnostic,seconds=time.perf_counter()-begin)


def cassini_obstruction():
    fib=[0,1]
    for _ in range(200):fib.append(fib[-1]+fib[-2])
    rows=[]
    for k in (8,20,197):
        f,g=fib[k],fib[k-1]
        residual=g*g % f
        assert min(residual,f-residual)==1
        # Distinct phases separated by g/f have identical F_k phase, and the
        # companion frequency differs only by +/-1/F_k modulo one.
        maximum_coefficient=8
        for a in range(-maximum_coefficient,maximum_coefficient+1):
            for b in range(-maximum_coefficient,maximum_coefficient+1):
                residue=((a*f+b*g)*g) % f
                assert residue==(b*residual) % f
        rows.append(dict(k=k,F_k=str(f),F_previous=str(g),
            exact_right_phase_difference_mod_one='0',
            companion_difference_numerator=min(residual,f-residual),denominator=str(f),
            independent_probe_transcript_TV_upper_bound_48_probes=float(min(1,48*math.pi/f))))
    return dict(status='EXACT_ALGEBRA_PASS',scope='fixed cheap linear combinations of the two current accumulator phases',rows=rows,
                general_factoring_lower_bound=False,
                consequence='Adjacent-accumulator checks cannot universally remove all global aliases at constant probe cost.')


def summarize(rows):
    out=[]
    for cohort in sorted({r['cohort'] for r in rows}):
        for n in sorted({r['n'] for r in rows}):
            for arm in ('upstream','global_splits'):
                block=[r for r in rows if r['cohort']==cohort and r['n']==n and r['arm']==arm]
                if not block:continue
                out.append(dict(cohort=cohort,n=n,arm=arm,trials=len(block),
                    false_certifications=sum(r['result']['falsely_certified'] for r in block),
                    successful=sum(r['result']['accurate_and_certified'] for r in block),
                    posthoc_false_certifications=sum(r['posthoc_reweight']['falsely_certified'] for r in block),
                    posthoc_successful=sum(r['posthoc_reweight']['accurate_and_certified'] for r in block),
                    mean_probes=float(np.mean([r['probes'] for r in block])),
                    mean_seconds=float(np.mean([r['seconds'] for r in block])),
                    median_midpoint_discrepancy=float(np.median([r['full_transcript_midpoint_tv'] for r in block]))))
    return out


def main(upstream,output):
    u=load_upstream(upstream)
    plan=dict(cohorts={'replication':20261031,'holdout':20271031},
              trials_per_cohort_by_n={'4':256,'64':64,'2048':4},
              hypothesis='Full-transcript refinement reduces false certification without >5% mean probe increase.',
              primary_gate='On holdout pooled across n: one-sided exact paired sign test p<=0.05 on false certifications and mean probe ratio<=1.05.',
              upstream=UPSTREAM_URL,upstream_commit=UPSTREAM_COMMIT,upstream_sha256=UPSTREAM_SHA256,
              measured_quantity='synthetic scalar phase estimation, not factoring',qpu_jobs=0)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    frozen=output.with_name(output.stem+'_plan.json');frozen.write_text(json.dumps(plan,indent=2)+'\n')
    result=dict(plan=plan,utc=datetime.now(timezone.utc).isoformat(),rows=[],
                cassini=cassini_obstruction(),status='STARTED',external_compute_spend=0)
    def save():output.write_text(json.dumps(result,indent=2)+'\n')
    save()
    for cohort,base_seed in plan['cohorts'].items():
        for n,count in ((4,256),(64,64),(2048,4)):
            for case in range(count):
                for full in (False,True):
                    row=trial(u,n,base_seed+n*1009+case,full)
                    row.update(cohort=cohort,case=case);result['rows'].append(row)
                if (case+1)%32==0 or case+1==count:
                    save();print(json.dumps(dict(cohort=cohort,n=n,completed=case+1)),flush=True)
    pairs={}
    for row in result['rows']:
        if row['cohort']=='holdout':pairs.setdefault((row['n'],row['case']),{})[row['arm']]=row
    wins=sum(p['upstream']['result']['falsely_certified'] and not p['global_splits']['result']['falsely_certified'] for p in pairs.values())
    losses=sum(p['global_splits']['result']['falsely_certified'] and not p['upstream']['result']['falsely_certified'] for p in pairs.values())
    discordant=wins+losses
    probability=sum(math.comb(discordant,j) for j in range(wins,discordant+1))/2**discordant if discordant else 1.
    ratio=sum(p['global_splits']['probes'] for p in pairs.values())/sum(p['upstream']['probes'] for p in pairs.values())
    result.update(status='COMPLETE',summary=summarize(result['rows']),
                  primary_gate=dict(wins=wins,losses=losses,one_sided_p=probability,mean_probe_ratio=ratio,
                                    passed=probability<=.05 and ratio<=1.05),
                  RSA_break=False)
    save();print(json.dumps(dict(primary_gate=result['primary_gate'],summary=result['summary']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--upstream-simulator',required=True)
    p.add_argument('--output',default='results/bayesian_refinement_20261030/audit.json')
    a=p.parse_args();main(a.upstream_simulator,a.output)
