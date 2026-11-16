#!/usr/bin/env python3
"""K171: exact Q14 ROM with a shared address-pair monomial across segments.

All gates are reversible X/CX/CCX; all four scratch bits return to zero.
No affine interpolation or full Helios integration is claimed.
"""
import argparse
import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "k168"))
import k168_q14_cost as k168

def build():
    # q0..2 address, q3..5 segment, q6..20 output.
    # q21 cache=addr0&addr1, q22 selector, q23 selector work / local
    # pair, q24 output-control temporary.
    addr=(0,1,2); seg=(3,4,5); out=tuple(range(6,21))
    cache,match,work,tmp=21,22,23,24
    gates=[("CCX",addr[0],addr[1],cache)]
    per_segment=[]
    for j in range(8):
        start=len(gates)
        neg=[("X",seg[i]) for i in range(3) if not (j>>i)&1]
        prefix=(neg+[("CCX",seg[0],seg[1],work),
                     ("CCX",work,seg[2],match),
                     ("CCX",seg[0],seg[1],work)]+neg[::-1])
        gates.extend(prefix)
        poly=k168.anf(k168.lookup_values()[j*8:j*8+8])
        for mask,targets in sorted(poly.items()):
            if mask==0:
                gates.extend(("CX",match,out[b]) for b in targets)
                continue
            if mask in (1,2,4):
                compute=[("CCX",match,addr[{1:0,2:1,4:2}[mask]],tmp)]
            elif mask==3:
                compute=[("CCX",match,cache,tmp)]
            elif mask==7:
                compute=[("CCX",cache,addr[2],work),
                         ("CCX",match,work,tmp)]
            elif mask in (5,6):
                pair={5:(addr[0],addr[2]),6:(addr[1],addr[2])}[mask]
                compute=[("CCX",pair[0],pair[1],work),
                         ("CCX",match,work,tmp)]
            else:
                raise AssertionError(mask)
            gates.extend(compute)
            gates.extend(("CX",tmp,out[b]) for b in targets)
            gates.extend(reversed(compute))
        gates.extend(reversed(prefix))
        per_segment.append({"segment":j,**count(gates[start:])})
    gates.append(("CCX",addr[0],addr[1],cache))
    return gates,per_segment

def count(gates):
    c=collections.Counter(g[0] for g in gates)
    return {k:c[k] for k in ("CCX","CX","X")}

def verify(gates,trials):
    rng=random.Random(171)
    reference=k168.lookup_values()
    cases=0
    for s in range(8):
        for i in range(8):
            for target in (0,32767,rng.randrange(32768)):
                initial=i|(s<<3)|(target<<6)
                expected=i|(s<<3)|((target^reference[8*s+i])<<6)
                result=k168.execute(initial,gates)
                assert result==expected,(s,i,target,result,expected)
                assert k168.execute(result,reversed(gates))==initial
                cases+=1
    for _ in range(trials):
        s=rng.randrange(8);i=rng.randrange(8);target=rng.randrange(32768)
        initial=i|(s<<3)|(target<<6)
        expected=i|(s<<3)|((target^reference[8*s+i])<<6)
        assert k168.execute(initial,gates)==expected
        cases+=1
    return cases

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--trials",type=int,default=1000)
    ap.add_argument("--out",type=Path,default=Path("competition/k171/results/shared_monomial.json"))
    args=ap.parse_args()
    baseline,_,resources=k168.circuit()
    candidate,segments=build()
    tests=verify(candidate,args.trials)
    base=count(baseline); optimized=count(candidate)
    assert optimized["CCX"]<base["CCX"],(base,optimized)
    report={"baseline":base,"optimized":optimized,
            "CCX_saved":base["CCX"]-optimized["CCX"],
            "segments":segments,"cases":tests,
            "scratch":4,"total_wires":25,
            "exact_basis_and_arbitrary_target_verified":True,
            "coherent_unitary":"X/CX/CCX permutation, no measurements or input-dependent classical control",
            "affine_CSD_verified":False,"full_helios_candidate":False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print("K171_RESULT",json.dumps(report,sort_keys=True),flush=True)
    print("K171_WRITTEN",args.out,flush=True)

if __name__=="__main__":
    main()
