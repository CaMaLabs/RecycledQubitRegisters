#!/usr/bin/env python3
"""K032: targeted full-domain precision/phase tradeoff around K031 winner.

Exact official verifier, no changes to scoring logic. Saves receipts after each
candidate; prioritize combos that might afford more phase truncation.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
K031=ROOT/"competition/k031/k031_full_domain_repair.py"
spec=importlib.util.spec_from_file_location("k031_full_domain_repair",K031)
if not K031.exists():
    raise SystemExit("K031 script missing: "+str(K031))
k031=importlib.util.module_from_spec(spec)
spec.loader.exec_module(k031)

WINNER={"coef_bits":17,"delta_bits":12,"product_bits":27,"result_bits":28,"square_bits":28}

def designs():
    # A larger square register changes both numerical error and resource costs;
    # co-tune other widths selectively instead of a blind Cartesian sweep.
    yield WINNER.copy(), 1
    for square in (28,29,30,31,32):
        for more in ({}, {"delta_bits":13}, {"coef_bits":18},
                     {"result_bits":29}, {"product_bits":28}):
            p=dict(WINNER, square_bits=square,**more)
            for cut in (0,1,2,3,4):
                if p==WINNER and cut in (0,1):
                    continue
                yield p,cut

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k032/results"))
    ap.add_argument("--max-trials",type=int,default=125)
    ap.add_argument("--timeout",type=int,default=300)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    receipts=out/"receipts.jsonl"
    old=k031.read_receipts(receipts)
    k031.sys.path.insert(0,str(k031.VERIFIERS))
    ref=k031.importlib.import_module("invsqrt.nr_reference_circuit")
    ranked=[]
    for i,(prec,cut) in enumerate(designs()):
        if i>=args.max_trials:break
        key=f"trial_{i:03}"
        file=out/(key+".kmb")
        if key in old:
            r=old[key]
            if r["status"]=="PASS_FULL":
                ranked.append({"id":key,"precision":prec,"cut":cut,
                               "score":r["score"],"path":str(file)})
            continue
        print("TRY",key,json.dumps(prec,sort_keys=True),"cut",cut,flush=True)
        try:
            build=k031.build(ref,prec,cut,file)
            first=k031.verify(file,k031.FULL_X,12345,args.timeout)
            okay=first.get("status")=="PASS" and first.get("exit_code")==0
            second=k031.verify(file,k031.FULL_X,23456,args.timeout) if okay else None
            okay=okay and second.get("status")=="PASS" and second.get("exit_code")==0
            r={"id":key,"precision":prec,"cut":cut,"build":build,
               "first":first,"second":second,
               "status":"PASS_FULL" if okay else "FAIL_FULL"}
            if okay:
                r["score"]=first["score"]
                ranked.append({"id":key,"precision":prec,"cut":cut,
                               "score":first["score"],"path":str(file)})
        except Exception as e:
            r={"id":key,"precision":prec,"cut":cut,
               "status":"ERROR","error":repr(e)}
        k031.append(receipts,old,r)
        if len(ranked):
            best=min(ranked,key=lambda x:x["score"])
            (out/"best_full_domain.json").write_text(json.dumps(best,indent=2))
            print("CURRENT_BEST",json.dumps(best,sort_keys=True),flush=True)
    ranked.sort(key=lambda x:x["score"])
    (out/"verified_frontier.json").write_text(json.dumps(ranked,indent=2))
    print("FULL_DOMAIN_PASS_COUNT",len(ranked),flush=True)
    print("BEST",json.dumps(ranked[0] if ranked else None,sort_keys=True),flush=True)

if __name__=="__main__":main()
