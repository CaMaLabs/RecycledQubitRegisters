#!/usr/bin/env python3
"""K170: synthesize and verify exact low-CCX selected lookup segments 2 and 3.
Uses a shared segment-match ancilla and cached local address monomials.
Not an affine-CSD multiplier: those approximate a different function.
"""
import argparse, collections, json, random
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'k168'))
import k168_q14_cost as k168

def segment_block(segment, optimized):
    addr=(0,1,2); seg=(3,4,5); out=list(range(6,21))
    match=22; work=21; mono=23; final=24
    table=k168.lookup_values()[segment*8:segment*8+8]
    poly=k168.anf(table)
    neg=[('X',seg[i]) for i in range(3) if not ((segment>>i)&1)]
    # compute/uncompute match using work; work remains clean
    prefix=neg+[('CCX',seg[0],seg[1],work),('CCX',work,seg[2],match),('CCX',seg[0],seg[1],work)]+neg[::-1]
    gates=prefix[:]
    if optimized:
        # Cache address pair monomials across all output bits. With the selector
        # match computed once, each monomial is combined once and fanned out.
        for mask,targets in sorted(poly.items()):
            if mask==0:
                gates += [('CX',match,out[b]) for b in targets]
                continue
            bits=[addr[i] for i in range(3) if (mask>>i)&1]
            if len(bits)==1:
                compute=[('CCX',match,bits[0],work)]; source=work
            elif len(bits)==2:
                compute=[('CCX',bits[0],bits[1],work),('CCX',match,work,mono)];source=mono
            else:
                compute=[('CCX',bits[0],bits[1],work),('CCX',work,bits[2],mono),('CCX',match,mono,final)];source=final
            gates+=compute+[('CX',source,out[b]) for b in targets]+compute[::-1]
    else:
        # Original per-segment block from K168
        all_g,info,_=k168.circuit()
        start=sum(x['CCX']*0 for x in info) # only for clarity
        # slice using selector block boundaries, reconstructed below
        return None
    gates+=prefix[::-1]
    return gates

def synthesize():
    baseline,info,res=k168.circuit()
    # Derive segment blocks by reconstructing exact original boundaries:
    # each block starts with the segment's negative-control X pattern
    # and has a known per-block X/CX/CCX count.
    offsets=[]; pos=0
    for item in info:
        length=item['CCX']+item['CX']+item['X']
        offsets.append((pos,pos+length));pos+=length
    assert pos==len(baseline)
    replacement={}
    for j in (2,3):
        alt=segment_block(j,True)
        assert alt is not None
        replacement[j]=alt
    hybrid=[]
    for j,(a,b) in enumerate(offsets):
        hybrid+=replacement.get(j,baseline[a:b])
    return baseline,hybrid,replacement,res

def verify(gates, reference, trials):
    rng=random.Random(170)
    cases=0
    for segment in range(8):
        for idx in range(8):
            for target in (0,32767,rng.randrange(32768)):
                before=idx|(segment<<3)|(target<<6)
                expected=idx|(segment<<3)|((target^reference[segment*8+idx])<<6)
                actual=k168.execute(before,gates)
                assert actual==expected,(segment,idx,target,actual,expected)
                assert k168.execute(actual,reversed(gates))==before
                cases+=1
    for _ in range(trials):
        segment=rng.randrange(8);idx=rng.randrange(8);target=rng.randrange(32768)
        before=idx|(segment<<3)|(target<<6)
        actual=k168.execute(before,gates)
        assert actual==idx|(segment<<3)|((target^reference[segment*8+idx])<<6)
    return cases+trials

def counts(gates):
    c=collections.Counter(g[0] for g in gates)
    return {k:c[k] for k in ('CCX','CX','X')}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--trials',type=int,default=1000)
    p.add_argument('--out',default='competition/k170/results/exact_synthesis.json')
    args=p.parse_args()
    baseline,hybrid,alts,res=synthesize()
    table=k168.lookup_values()
    checks=verify(hybrid,table,args.trials)
    base=counts(baseline); new=counts(hybrid)
    report={'baseline':base,'hybrid':new,'delta_CCX':base['CCX']-new['CCX'],
            'segment_alternatives':{str(j):counts(g) for j,g in alts.items()},
            'cases':checks,'resources':res,'coherent_basis_permutation':True,
            'coherent_phase_preservation':'inferred from exact X/CX/CCX permutation with no measurements',
            'affine_CSD_verified':False,'full_helios_candidate':False,
            'note':'Exact ANF monomial synthesis; affine interpolation CSD is not interchangeable with exact Q14 ROM.'}
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+'\n')
    print('K170_RESULT',json.dumps(report,sort_keys=True))
    print('K170_WRITTEN',path)
if __name__=='__main__':main()
