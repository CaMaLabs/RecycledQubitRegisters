#!/usr/bin/env python3
"""KMX reversible-block optimization engine. Exact truth-table validation; original source never modified."""
import argparse,hashlib,json,os,random,subprocess,sys,time
from pathlib import Path
from collections import Counter
ARITY={'X':1,'CX':2,'CCX':3,'SWAP':2}
def parse(line):
    try:t=line.decode('ascii').strip().split()
    except UnicodeDecodeError:return None
    if not t or t[0] not in ARITY or len(t)!=ARITY[t[0]]+1:return None
    if not all(x.startswith('q') and x[1:].isdigit() for x in t[1:]):return None
    q=tuple(int(x[1:]) for x in t[1:])
    return (t[0],q) if len(set(q))==len(q) else None
def encode(op,nl):return (op[0]+' '+' '.join('q'+str(x) for x in op[1])).encode()+nl
def cost(ops):
    c=Counter(g for g,_ in ops)
    return (c['CCX'],c['CX']+3*c['SWAP'],c['X'],len(ops))
def truth(ops,wires):
    n=len(wires);size=1<<n;mask=(1<<size)-1
    s={w:sum(((v>>i)&1)<<v for v in range(size)) for i,w in enumerate(wires)}
    for g,q in ops:
        if g=='X':s[q[0]]^=mask
        elif g=='CX':s[q[1]]^=s[q[0]]
        elif g=='CCX':s[q[2]]^=s[q[0]]&s[q[1]]
        elif g=='SWAP':s[q[0]],s[q[1]]=s[q[1]],s[q[0]]
    return tuple(s[w] for w in wires)
def windows(parsed,max_wires,max_span,min_ccx,max_ccx):
    for start,op in enumerate(parsed):
        if op is None:continue
        wires=set();ccx=0
        for end in range(start,min(len(parsed),start+max_span)):
            item=parsed[end]
            if item is None:break
            wires.update(item[1]);ccx+=item[0]=='CCX'
            if len(wires)>max_wires or ccx>max_ccx:break
            if ccx>=min_ccx and end>start and (item[0]=='CCX' or end-start+1==max_span):
                yield start,end,tuple(sorted(wires)),ccx
def neighborhood(ops,wires,rng,cap=24):
    n=len(ops);seen=set();out=[]
    def add(candidate,tag):
        key=tuple(candidate)
        if key!=tuple(ops) and key not in seen:
            seen.add(key);out.append((candidate,tag))
    for i in range(n):add(ops[:i]+ops[i+1:],'delete')
    for i in range(n):
        for j in range(i+1,min(n,i+cap)):
            if ops[i][0]==ops[j][0]:add(ops[:i]+ops[i+1:j]+ops[j+1:],'delete_pair')
    for i,(g,q) in enumerate(ops):
        if g=='CCX':
            for t in wires:
                for a in wires:
                    for b in wires:
                        if a>=b or t in (a,b):continue
                        if (a,b,t)!=q:add(ops[:i]+[('CCX',(a,b,t))]+ops[i+1:],'ccx_substitute')
            for a in wires:
                for b in wires:
                    if a!=b:
                        c=('CX',(a,b))
                        add(ops[:i]+[c,ops[i],c]+ops[i+1:],'affine_conjugate')
        elif g=='CX':
            for a in wires:
                for b in wires:
                    if a!=b and (a,b)!=q:add(ops[:i]+[('CX',(a,b))]+ops[i+1:],'cx_substitute')
    for i,(g,q) in enumerate(ops):
        if g!='CCX':continue
        for j in range(i+1,n):
            h,r=ops[j]
            if h!='CCX' or q[2]!=r[2]:continue
            shared=set(q[:2])&set(r[:2])
            if len(shared)!=1:continue
            common=next(iter(shared));a=next(iter(set(q[:2])-shared));b=next(iter(set(r[:2])-shared))
            for src,dst in ((a,b),(b,a)):
                rep=[('CX',(src,dst)),('CCX',(common,dst,q[2])),('CX',(src,dst))]
                add(ops[:i]+rep+ops[i+1:j]+ops[j+1:],'factor')
    rng.shuffle(out)
    return out
def optimize(original,wires,rng,beam,depth,seconds):
    reference=truth(original,wires);baseline=cost(original)
    frontier=[original];seen={tuple(original)};best=None;tagbest=None;attempts=0;start=time.monotonic()
    for level in range(1,depth+1):
        choices=[]
        for state in frontier:
            for cand,tag in neighborhood(state,wires,rng):
                if time.monotonic()-start>=seconds:return best,tagbest,attempts,level
                key=tuple(cand)
                if key in seen:continue
                seen.add(key)
                if len(cand)>len(original)+4 or cost(cand)[0]>baseline[0]:continue
                attempts+=1
                if truth(cand,wires)!=reference:continue
                cc=cost(cand)
                if cc<baseline and (best is None or cc<cost(best)):best=cand;tagbest=tag
                choices.append((cc,rng.random(),cand))
        if not choices:break
        choices.sort(key=lambda x:(x[0],x[1]))
        frontier=[x[2] for x in choices[:beam]]
    return best,tagbest,attempts,level
def atomic(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2));os.replace(tmp,path)
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='competition/k191/results/helios_k191.kmx')
    p.add_argument('--expected-sha',default='d7da8646fc6bef7a08f62f8039829fdc3a2669c9572aabf7936596d3ea6560e8')
    p.add_argument('--out',default='competition/optimizer/results')
    p.add_argument('--max-wires',type=int,default=7)
    p.add_argument('--max-span',type=int,default=32)
    p.add_argument('--min-ccx',type=int,default=2)
    p.add_argument('--max-ccx',type=int,default=6)
    p.add_argument('--max-blocks',type=int,default=150)
    p.add_argument('--beam',type=int,default=12)
    p.add_argument('--depth',type=int,default=3)
    p.add_argument('--seconds-per-block',type=float,default=2.)
    p.add_argument('--seed',type=int,default=12345)
    p.add_argument('--verify',action='store_true')
    p.add_argument('--verifier',default='competition/k001/private/official/verifiers/invsqrt/verify_submission_invsqrt.py')
    p.add_argument('--resume',action='store_true')
    a=p.parse_args()
    if not 3<=a.max_wires<=10:raise SystemExit('max-wires must be 3..10')
    if min(a.max_blocks,a.depth,a.beam)<1:raise SystemExit('invalid search limits')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    raw=Path(a.source).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=a.expected_sha:raise SystemExit('BASELINE_SHA_MISMATCH '+sha)
    lines=raw.splitlines(keepends=True);parsed=[parse(line) for line in lines]
    cfg={k:v for k,v in vars(a).items() if k not in ('verify','resume')}
    cfgsha=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()
    checkpoint=out/'checkpoint.json';done=set();winner=None
    if a.resume and checkpoint.exists():
        saved=json.loads(checkpoint.read_text())
        if saved['configuration_hash']!=cfgsha:raise SystemExit('CHECKPOINT_CONFIGURATION_MISMATCH')
        done=set(saved['done'])
    stats=Counter();count=0
    print('ENGINE_START',json.dumps({'source_sha':sha,'configuration_hash':cfgsha}),flush=True)
    for start,end,wires,_ in windows(parsed,a.max_wires,a.max_span,a.min_ccx,a.max_ccx):
        key=f'{start}:{end}'
        if key in done:continue
        if count>=a.max_blocks:break
        count+=1;original=parsed[start:end+1]
        rng=random.Random(a.seed*1000003+start*1009+end)
        candidate,tag,attempts,level=optimize(original,wires,rng,a.beam,a.depth,a.seconds_per_block)
        stats['blocks']+=1;stats['attempts']+=attempts;done.add(key)
        if candidate is not None:
            stats['local_improvements']+=1
            if winner is None or cost(candidate)<cost(winner['candidate']):
                winner={'start':start,'end':end,'candidate':candidate}
                nl=b'\r\n' if lines[start].endswith(b'\r\n') else b'\n'
                dest=out/'candidate.kmx'
                dest.write_bytes(b''.join(lines[:start]+[encode(g,nl) for g in candidate]+lines[end+1:]))
                report={'status':'LOCAL_EXACT_IMPROVEMENT','lines':[start+1,end+1],'original_cost':cost(original),'replacement_cost':cost(candidate),'method':tag,'candidate_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'official_status':'NOT_RUN'}
                atomic(out/'candidate.json',report)
                print('ENGINE_CANDIDATE',json.dumps(report),flush=True)
        if count%10==0 or candidate is not None:
            atomic(checkpoint,{'configuration_hash':cfgsha,'done':sorted(done),'stats':dict(stats)})
            print('ENGINE_PROGRESS',json.dumps({'blocks':count,'attempts':stats['attempts'],'improvements':stats['local_improvements']}),flush=True)
    atomic(checkpoint,{'configuration_hash':cfgsha,'done':sorted(done),'stats':dict(stats)})
    if winner is None:
        print('ENGINE_NO_NEW_CANDIDATE',json.dumps(dict(stats)),flush=True);return
    if a.verify:
        cmd=[sys.executable,a.verifier,str(out/'candidate.kmx'),'--format','kmx','--seed',str(a.seed),'--max-workers','2']
        print('ENGINE_VERIFY_START',flush=True)
        with (out/'verify.log').open('w') as log:proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=False)
        result={'verifier_returncode':proc.returncode,'official_status':'REVIEW_LOG','log':str(out/'verify.log')}
        atomic(out/'verification.json',result)
        print('ENGINE_VERIFY_FINISHED',json.dumps(result),flush=True)
    print('ENGINE_COMPLETE',flush=True)
if __name__=='__main__':main()
