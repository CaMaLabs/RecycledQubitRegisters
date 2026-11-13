#!/usr/bin/env python3
"""K144: bounded joint two-site phase-headroom experiments on PINNED Helios KMX.

New test vs K098: opposite absolute angle perturbations on *two* q28 phase
sites, not isolated per-site scaling. This has NO guaranteed phase cancellation
because intervening gates change q28. It must pass the official verifier.

Safety: never modifies immutable source, never submits, one seed prefix
screen, bounded 2-seed full verification ONLY upon optional --full and a
strictly improving prefix SCORE vs the same-source prefix baseline.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, itertools, json, re, sys
from decimal import Decimal, localcontext
from pathlib import Path

PIN='e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183'
REF_SCORE=95369.00696815242
PAT=re.compile(r'^(\s*Z_POW\s+q28\s+)([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(\s*(?:#.*)?\n?)$')

def sites(lines):
    result=[]
    for i,line in enumerate(lines):
        m=PAT.fullmatch(line)
        if m: result.append((i,Decimal(m.group(2))))
    return result

def mutate(lines,first,second,delta):
    result=list(lines)
    with localcontext() as ctx:
        ctx.prec=110
        for idx,d in [(first,delta),(second,-delta)]:
            match=PAT.fullmatch(lines[idx]); assert match
            angle=Decimal(match.group(2))+d
            if not Decimal(0)<angle<Decimal(2):raise ValueError('phase outside (0,2)')
            result[idx]=match.group(1)+format(angle,'f')+match.group(3)
    return result

def pairs(s):
    # Two recorded q28 ladders separated by the source's phase spacing.
    clusters=[]
    for item in s:
        if not clusters or item[0]-clusters[-1][-1][0]>200:clusters.append([])
        clusters[-1].append(item)
    result=[]
    for group in clusters:
        if len(group)<2:continue
        # Adjacent in phase order; plus two pairs bridging the cluster ends.
        for i,j in zip(group,group[1:]): result.append((i[0],j[0]))
        result.append((group[0][0],group[-1][0]))
        if len(group)>=4:result.append((group[1][0],group[-2][0]))
    return list(dict.fromkeys(result)),[len(g) for g in clusters]

def official_verifier(root):
    p=root/'competition/k031/k031_full_domain_repair.py'
    if not p.is_file():raise SystemExit(f'Need existing official verifier wrapper: {p}')
    spec=importlib.util.spec_from_file_location('k144_k031',p)
    module=importlib.util.module_from_spec(spec)
    # K031 imports its own deps; retain same working environment as historical runs.
    spec.loader.exec_module(module)
    return module

def compile_kmb(kmx,kmb):
    import kickmix as km
    circuit=km.Circuit.from_file(str(kmx),format='kmx')
    circuit.to_file(str(kmb),format='kmb')
    return circuit.num_qubits

def metric(v,key):
    x=v.get(key)
    return x if isinstance(x,(int,float)) else None

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--baseline',type=Path,default=Path('competition/k098/results/helios_immutable.kmx'))
    a.add_argument('--out',type=Path,default=Path('competition/k144/results'))
    a.add_argument('--max-candidates',type=int,default=24)
    a.add_argument('--prefix-x',type=int,default=4095)
    a.add_argument('--full',action='store_true',help='Two-seed full domain only for a strict prefix score win')
    a.add_argument('--max-full',type=int,default=2)
    a.add_argument('--seed',type=int,default=12345)
    a.add_argument('--timeout',type=int,default=600)
    a.add_argument('--dry-run',action='store_true')
    args=a.parse_args()
    if args.max_candidates<1 or args.max_full<0 or not 161<=args.prefix_x<=3133452:
        a.error('bad bounds')
    raw=args.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=PIN:raise SystemExit('PIN mismatch '+sha)
    original=raw.decode('utf-8').splitlines(keepends=True)
    ss=sites(original); pp,clusters=pairs(ss)
    if len(ss)!=42 or len(clusters)!=2 or len(pp)==0:
        raise SystemExit(f'Expected 42 q28 sites in two ladders, got {len(ss)} sites and {clusters} clusters')
    # Spread candidates across both ladders AND magnitudes; avoid early-pair bias.
    representatives=[]
    for segment in (pp[:18],pp[18:]):
        if segment:
            representatives.extend([segment[0],segment[len(segment)//2],segment[-1]])
    representatives=list(dict.fromkeys(representatives))
    jobs=[]
    for pow2 in [40,36,44,32,48]:
        for i,j in representatives:
            for sign in (1,-1):
                jobs.append((i,j,sign*Decimal(1)/(Decimal(2)**pow2),pow2,sign))
    jobs=jobs[:args.max_candidates]
    if args.dry_run:
        print('K144_PLAN',json.dumps({'status':'PINNED_DRY_RUN','source_sha256':sha,
             'phase_sites':len(ss),'clusters':clusters,'candidate_count':len(jobs),
             'first_jobs':[{'line_a':i+1,'line_b':j+1,'delta_power':p,'sign':sign}
                           for i,j,delta,p,sign in jobs[:10]]}))
        return
    args.out.mkdir(parents=True,exist_ok=True)
    vr=official_verifier(Path.cwd())
    bkmx=args.out/'baseline.kmx';bkmx.write_bytes(raw)
    bkmb=args.out/'baseline.kmb'; q=compile_kmb(bkmx,bkmb)
    if q!=62:raise SystemExit(f'Unexpected width {q}')
    baseline=vr.verify(bkmb,args.prefix_x,args.seed,args.timeout)
    if baseline.get('status')!='PASS' or baseline.get('exit_code')!=0 or metric(baseline,'score') is None:
        raise SystemExit('Baseline prefix verification failed: '+json.dumps(baseline)[:800])
    print('K144_BASE',json.dumps({'score':baseline['score'],'q':q,'prefix_x':args.prefix_x,'seed':args.seed}),flush=True)
    rows=[]; full_count=0;winner=None
    for n,(i,j,delta,power,sign) in enumerate(jobs):
        label=f'pair{n:03d}_L{i+1}_{j+1}_p{power}_s{sign:+d}'
        kmx=args.out/(label+'.kmx');kmb=args.out/(label+'.kmb')
        row={'id':label,'line_a':i+1,'line_b':j+1,'delta':str(delta),'prefix_x':args.prefix_x}
        try:
            kmx.write_text(''.join(mutate(original,i,j,delta)))
            row['q']=compile_kmb(kmx,kmb)
            if row['q']!=62:raise ValueError('Unexpected width')
            row['kmb_sha256']=hashlib.sha256(kmb.read_bytes()).hexdigest()
            if row['kmb_sha256']==hashlib.sha256(bkmb.read_bytes()).hexdigest():
                raise ValueError('Same compiled binary as baseline; perturbation below representation precision')
            row['prefix']=vr.verify(kmb,args.prefix_x,args.seed,args.timeout)
            v=row['prefix'];score=metric(v,'score')
            row['prefix_improves']=v.get('status')=='PASS' and v.get('exit_code')==0 and score is not None and score < baseline['score']-1e-9
            if row['prefix_improves'] and args.full and full_count<args.max_full:
                full_count+=1
                first=vr.verify(kmb,3133452,12345,args.timeout)
                row['full_12345']=first
                if first.get('status')=='PASS' and first.get('exit_code')==0 and metric(first,'score') is not None and first['score']<REF_SCORE:
                    second=vr.verify(kmb,3133452,23456,args.timeout)
                    row['full_23456']=second
                    if second.get('status')=='PASS' and second.get('exit_code')==0 and second.get('score',1e99)<REF_SCORE:
                        row['status']='FULL_TWO_SEED_BEATS_REFERENCE'
                        winner=label
                if not winner: row['status']='FULL_NO_WIN'
            else:row['status']='PREFIX_WIN_ONLY' if row['prefix_improves'] else 'NO_PREFIX_WIN'
        except Exception as exc:row.update(status='ERROR',error=repr(exc))
        rows.append(row)
        print('K144_CASE',json.dumps({'id':label,'status':row['status'],'prefix_score':row.get('prefix',{}).get('score'),
          'full_score':row.get('full_12345',{}).get('score')}),flush=True)
        (args.out/'summary.json').write_text(json.dumps({'status':'RUNNING' if n+1<len(jobs) else 'FINISHED',
          'objective':'strictly below 95369.00696815242 FULL two-seed',
          'source_sha256':sha,'baseline_prefix':baseline,'winner':winner,'cases':rows},indent=2)+'\n')
        if winner:break
    print('K144_RESULT',json.dumps({'tested':len(rows),'prefix_wins':sum(x.get('prefix_improves',False) for x in rows),
      'full_checked':full_count,'winner':winner,'summary':str(args.out/'summary.json')}),flush=True)

if __name__=='__main__':main()