#!/usr/bin/env python3
"""K028-E: Schedule experiments for symmetric squaring in Kickmix.

Reuses reference _add_row (init_and, iadd/isub, del_and) and the diagonal
CX logic. Each candidate is an independently built KMB, verified using
the official inverse-square-root verifier. No source file is mutated.
"""
from __future__ import annotations
import argparse
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VERIFIERS=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VERIFIERS))
import kickmix as km

PRECISION=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=27)

def schedule_indices(wc, mode):
    indices=list(range(1,wc+1))
    if mode=="reverse":
        return indices[::-1]
    if mode=="even_odd":
        return indices[::2]+indices[1::2]
    if mode=="odd_even":
        return indices[1::2]+indices[::2]
    if mode=="outside_in":
        out=[]
        lo,hi=0,len(indices)-1
        while lo<=hi:
            out.append(indices[lo])
            if lo!=hi:out.append(indices[hi])
            lo+=1;hi-=1
        return out
    if mode=="inside_out":
        return list(reversed(schedule_indices(wc,"outside_in")))
    if mode=="reference":
        return indices
    raise ValueError(mode)

def alternative_square(ref,mode):
    def build_square(builder,inverse,y0,square,scratch):
        wc,wsq=len(y0),len(square)
        y={k:y0[wc-k] for k in range(1,wc+1)}
        diagonal=[k for k in range(1,wc+1) if 2*k<=wsq]
        controls=km.array([y[k] for k in diagonal])
        targets=km.array([square[wsq-2*k] for k in diagonal])
        if not inverse:
            builder.cx(controls,targets)
        for k in schedule_indices(wc,mode):
            terms=[(y[l],wsq-(k+l-1))
                   for l in range(k+1,wc+1) if k+l-1<=wsq]
            if terms:
                ref._add_row(builder,inverse,y[k],terms,square,scratch)
        if inverse:
            builder.cx(controls,targets)
    return build_square

def verify(path,level,seed,timeout):
    cmd=[sys.executable,
         str(VERIFIERS/"invsqrt/verify_submission_invsqrt.py"),
         str(path),"--format","kmb","--max-x",str(level),
         "--shots-per-x","1",
         "--batch-size",str(min(256,level)),
         "--max-workers","1","--seed",str(seed)]
    began=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=VERIFIERS,capture_output=True,text=True,
                         timeout=timeout)
    except subprocess.TimeoutExpired:
        return dict(status="TIMEOUT",elapsed=round(time.monotonic()-began,3))
    try:
        d=json.loads(p.stdout)
    except json.JSONDecodeError:
        d=dict(status="NON_JSON",error=p.stdout[-600:])
    return dict(status=d.get("status"),exit=p.returncode,score=d.get("score"),
                error_ratio=d.get("worst_error_over_tolerance"),
                error=d.get("error"),stderr=p.stderr[-500:],
                elapsed=round(time.monotonic()-began,3))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default=str(ROOT/"competition/k028e/results"))
    ap.add_argument("--levels",default="64,512,4096,65536")
    ap.add_argument("--seeds",default="12345,23456")
    ap.add_argument("--timeout",type=int,default=300)
    ap.add_argument("--modes",default="reference,reverse,even_odd,odd_even,outside_in,inside_out")
    args=ap.parse_args()
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    prec=ref.Precision(**PRECISION)
    levels=[int(v) for v in args.levels.split(",")]
    seeds=[int(v) for v in args.seeds.split(",")]
    modes=[v.strip() for v in args.modes.split(",")]
    original=ref._square
    results=[]
    try:
        for mode in modes:
            ref._square=original if mode=="reference" else alternative_square(ref,mode)
            print("BUILD",mode,flush=True)
            try:
                circuit=ref.build_nr_circuit(10,prec=prec)
                file=out/f"square_{mode}.kmb"
                circuit.to_file(str(file),format="kmb")
            except Exception as ex:
                result=dict(mode=mode,status="BUILD_FAIL",error=repr(ex))
                results.append(result)
                print(json.dumps(result),flush=True)
                continue
            for level in levels:
                for seed in seeds:
                    data=verify(file,level,seed,args.timeout)
                    result=dict(mode=mode,level=level,seed=seed,
                                file_bytes=file.stat().st_size,**data)
                    results.append(result)
                    print(json.dumps(result,sort_keys=True),flush=True)
                    if result["status"]!="PASS" or result["exit"]!=0:
                        break
                else:
                    continue
                break
    finally:
        ref._square=original
        (out/"official_ab.json").write_text(json.dumps(results,indent=2))
    full=max(levels)
    eligible=[]
    for mode in modes:
        tests=[r for r in results if r.get("mode")==mode and "level" in r]
        if len(tests)==len(levels)*len(seeds) and all(r.get("status")=="PASS" and r.get("exit")==0 for r in tests):
            high=[r for r in tests if r["level"]==full]
            eligible.append((sum(r["score"] for r in high)/len(high),mode))
    if eligible:
        eligible.sort()
        print("PASSING_FRONTIER",json.dumps(eligible),flush=True)
    else:
        print("NO_ALL_LEVELS_PASSING_CANDIDATE",flush=True)
    print("RESULTS",out/"official_ab.json",flush=True)

if __name__=="__main__":
    main()
