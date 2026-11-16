#!/usr/bin/env python3
"""K172: exhaustive shared-pair cache selection for exact Q14 ROM, 25 wires.

Searches all three cached address pairs, tests full reversible circuits, and
reports measured counts. No unverified claim of <200 CCX.
"""
import argparse, collections, json, random, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"k168"))
import k168_q14_cost as k168

def counts(g):
    c=collections.Counter(x[0] for x in g)
    return {k:c[k] for k in ("CCX","CX","X")}

def build(pairmask):
    assert pairmask in (3,5,6)
    a=(0,1,2);s=(3,4,5);out=tuple(range(6,21))
    cache,match,work,tmp=21,22,23,24
    pair=[a[i] for i in range(3) if pairmask>>i&1]
    g=[("CCX",pair[0],pair[1],cache)]
    per=[]
    for j in range(8):
        start=len(g)
        neg=[("X",s[i]) for i in range(3) if not j>>i&1]
        prefix=neg+[("CCX",s[0],s[1],work),("CCX",work,s[2],match),
                    ("CCX",s[0],s[1],work)]+neg[::-1]
        g+=prefix
        for mask,targets in sorted(k168.anf(k168.lookup_values()[j*8:j*8+8]).items()):
            if mask==0:
                g.extend(("CX",match,out[b]) for b in targets)
                continue
            bits=[a[i] for i in range(3) if mask>>i&1]
            if len(bits)==1:
                compute=[("CCX",match,bits[0],tmp)]
            elif mask==pairmask:
                compute=[("CCX",match,cache,tmp)]
            elif mask==7:
                remaining=a[next(i for i in range(3) if not pairmask>>i&1)]
                compute=[("CCX",cache,remaining,work),("CCX",match,work,tmp)]
            else:
                compute=[("CCX",bits[0],bits[1],work),("CCX",match,work,tmp)]
            g+=compute
            g.extend(("CX",tmp,out[b]) for b in targets)
            g+=compute[::-1]
        g+=prefix[::-1]
        per.append({"segment":j,**counts(g[start:])})
    g.append(("CCX",pair[0],pair[1],cache))
    return g,per

def verify(g,trials):
    rng=random.Random(172)
    ref=k168.lookup_values()
    n=0
    for s in range(8):
        for i in range(8):
            for target in (0,32767,rng.randrange(32768)):
                before=i|(s<<3)|(target<<6)
                after=k168.execute(before,g)
                assert after==i|(s<<3)|((target^ref[8*s+i])<<6),(s,i,target)
                assert k168.execute(after,reversed(g))==before
                n+=1
    for _ in range(trials):
        s=rng.randrange(8);i=rng.randrange(8);target=rng.randrange(32768)
        before=i|(s<<3)|(target<<6)
        assert k168.execute(before,g)==i|(s<<3)|((target^ref[8*s+i])<<6)
        n+=1
    return n

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--trials",type=int,default=1000)
    p.add_argument("--out",type=Path,default=Path("competition/k172/results/cache_search.json"))
    args=p.parse_args()
    baseline,_,_=k168.circuit()
    rows=[]
    for mask in (3,5,6):
        gates,segments=build(mask)
        tests=verify(gates,args.trials)
        row={"pairmask":mask,"address_pair":[i for i in range(3) if mask>>i&1],
             "counts":counts(gates),"cases":tests,"segments":segments}
        rows.append(row)
        print("K172_CANDIDATE",json.dumps({k:row[k] for k in ("pairmask","address_pair","counts","cases")},sort_keys=True))
    best=min(rows,key=lambda r:(r["counts"]["CCX"],r["counts"]["CX"],r["counts"]["X"]))
    report={"baseline":counts(baseline),"k171_reference":{"CCX":210,"CX":388,"X":48},
            "best":best,"candidates":rows,"CCX_saved_vs_K168":240-best["counts"]["CCX"],
            "CCX_saved_vs_K171":210-best["counts"]["CCX"],
            "under_200_CCX":best["counts"]["CCX"]<200,
            "total_wires":25,"scratch":4,"all_candidates_exact_verified":True,
            "affine_CSD_verified":False,"full_helios_candidate":False,
            "next":"If no win, factor selector and output ANF jointly rather than repeating pair caching."}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print("K172_RESULT",json.dumps({k:report[k] for k in ("baseline","k171_reference","CCX_saved_vs_K168","CCX_saved_vs_K171","under_200_CCX","total_wires","all_candidates_exact_verified")}|{"best_pair":best["address_pair"],"best_counts":best["counts"]},sort_keys=True))
    print("K172_WRITTEN",args.out)

if __name__=="__main__":main()
