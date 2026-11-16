#!/usr/bin/env python3
"""K173: joint six-input ANF synthesis versus K171, 25/26-wire budgets.

Exact 64-entry Q14 ROM, XOR arbitrary 15-bit target, clean ancillas.
Candidate circuits use global six-variable ANF rather than segment blocks.
Gate costs and qubit-weighted proxy are measured, never presumed improved.
"""
import argparse, collections, json, random, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"k168"))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"k171"))
import k168_q14_cost as k168
import k171_shared_monomial as k171

def count(g):
    c=collections.Counter(x[0] for x in g)
    return {k:c[k] for k in ("CCX","CX","X")}

def global_anf(values):
    assert len(values)==64
    terms=collections.defaultdict(list)
    for bit in range(15):
        a=[(v>>bit)&1 for v in values]
        for k in range(6):
            for m in range(64):
                if m & (1<<k):
                    a[m]^=a[m^(1<<k)]
        for mask,v in enumerate(a):
            if v: terms[mask].append(bit)
    return dict(terms)

def build(ancillas,order="mask"):
    assert ancillas in (4,5)
    terms=global_anf(k168.lookup_values())
    keys=list(terms)
    if order=="weight":keys.sort(key=lambda m:(m.bit_count(),m))
    elif order=="mask":keys.sort()
    else:raise ValueError(order)
    g=[]
    for mask in keys:
        bits=[i for i in range(6) if mask>>i&1]
        targets=[6+b for b in terms[mask]]
        if not bits:
            g.extend(("X",t) for t in targets)
        elif len(bits)==1:
            g.extend(("CX",bits[0],t) for t in targets)
        else:
            # Compute k-control conjunction with k-1 scratch bits,
            # then fan it out with CX. If k-1 scratch is unavailable,
            # compute k-2 prefix bits and use direct CCX into each target.
            k=len(bits)
            if k-1<=ancillas:
                chain=[("CCX",bits[0],bits[1],21)]
                for i in range(2,k):
                    chain.append(("CCX",21+i-2,bits[i],21+i-1))
                source=21+k-2
                g+=chain
                g.extend(("CX",source,t) for t in targets)
                g+=chain[::-1]
            else:
                assert k==6 and ancillas==4
                chain=[("CCX",bits[0],bits[1],21)]
                for i in range(2,k-1):
                    chain.append(("CCX",21+i-2,bits[i],21+i-1))
                g+=chain
                g.extend(("CCX",24,bits[-1],t) for t in targets)
                g+=chain[::-1]
    return g,terms

def verify(g,ancillas,trials):
    rng=random.Random(173)
    ref=k168.lookup_values()
    n=0
    for address in range(64):
        for target in (0,32767,rng.randrange(32768)):
            before=address|(target<<6)
            expected=address|((target^ref[address])<<6)
            after=k168.execute(before,g)
            assert after==expected,(address,target,after,expected)
            assert k168.execute(after,reversed(g))==before
            n+=1
    for _ in range(trials):
        address=rng.randrange(64);target=rng.randrange(32768)
        before=address|(target<<6)
        assert k168.execute(before,g)==address|((target^ref[address])<<6)
        n+=1
    return n

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--trials",type=int,default=1000)
    p.add_argument("--out",type=Path,default=Path("competition/k173/results/joint_anf.json"))
    args=p.parse_args()
    baseline,_=k171.build()
    verify(baseline,4,args.trials)
    candidates=[]
    for scratch in (4,5):
        g,terms=build(scratch)
        tests=verify(g,scratch,args.trials)
        c=count(g)
        row={"method":"global_6bit_ANF","wires":21+scratch,"scratch":scratch,
             "counts":c,"cases":tests,"nonzero_monomials":len(terms),
             "proxy_qubits_times_CCX":(21+scratch)*c["CCX"]}
        candidates.append(row)
        print("K173_CANDIDATE",json.dumps(row,sort_keys=True),flush=True)
    base=count(baseline)
    best=min(candidates,key=lambda x:(x["proxy_qubits_times_CCX"],x["counts"]["CX"]))
    report={"k171":{"wires":25,"counts":base,"proxy_qubits_times_CCX":25*base["CCX"]},
            "candidates":candidates,"best_joint":best,
            "joint_beats_k171":best["proxy_qubits_times_CCX"]<25*base["CCX"],
            "recommended":"joint" if best["proxy_qubits_times_CCX"]<25*base["CCX"] else "K171",
            "all_verified":True,"affine_CSD_verified":False,"full_helios_candidate":False,
            "caveat":"Proxy excludes other Kaggle score terms. ANF synthesis is an exact reversible circuit, not a full Helios candidate."}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print("K173_RESULT",json.dumps({"k171":report["k171"],"best_joint":best,
          "joint_beats_k171":report["joint_beats_k171"],
          "recommended":report["recommended"],"all_verified":True},sort_keys=True),flush=True)
    print("K173_WRITTEN",args.out,flush=True)

if __name__=="__main__":main()
