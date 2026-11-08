#!/usr/bin/env python3
"""K029-A: Reuse QRR complement-conjugated addition in native Kickmix.

Exact n-bit identity: NOT(NOT(t) - u) == t + u (mod 2**n).
Likewise NOT(NOT(t) + u) == t - u (mod 2**n).

Retains the reference measurement-based init_and/del_and pair and every
partial-product position. A/B tests each multiplication stage separately.
This transplants an algebraic technique previously tested in QRR; it is
NOT a prediction that a variable-addend Kickmix score will improve.
"""
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

PRECISION=dict(coef_bits=17,delta_bits=12,product_bits=27,
               result_bits=28,square_bits=27)
MODES=("reference","square","horner","multiply_m","multiply_y0","all")

def make_row(original, mode, statistics):
    def patched(builder, inverse, control, terms, target, scratch, subtract=False):
        caller=sys._getframe(1).f_code.co_name
        selected=(mode=="all" or caller==("_"+mode))
        if not selected:
            return original(builder,inverse,control,terms,target,scratch,subtract=subtract)
        statistics[caller]=statistics.get(caller,0)+1
        sources=km.array([q for q,_ in terms])
        products=km.array([scratch[i] for _,i in terms])
        low=min(i for _,i in terms)
        if low<0 or low>=len(target):
            raise ValueError(f"Invalid row offset {low}")
        builder.init_and(control,sources,products)
        # Conjugate the exact little-endian modular accumulator, not the
        # source bits or clean-AND scratch; invert just the target suffix.
        suffix=target[low:]
        builder.x(suffix)
        if subtract != inverse:
            builder.iadd(scratch[low:len(target)],target=suffix)
        else:
            builder.isub(scratch[low:len(target)],target=suffix)
        builder.x(suffix)
        builder.del_and(control,sources,products)
    return patched

def verify(path,level,seed,timeout):
    cmd=[sys.executable,str(VERIFIERS/"invsqrt/verify_submission_invsqrt.py"),
         str(path),"--format","kmb","--max-x",str(level),
         "--shots-per-x","1","--batch-size",str(min(256,level)),
         "--max-workers","1","--seed",str(seed)]
    start=time.monotonic()
    try:
        p=subprocess.run(cmd,cwd=VERIFIERS,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        return dict(status="TIMEOUT",elapsed=round(time.monotonic()-start,3))
    try:
        d=json.loads(p.stdout)
    except json.JSONDecodeError:
        d=dict(status="NON_JSON",error=p.stdout[-900:])
    return dict(status=d.get("status"),exit=p.returncode,
                score=d.get("score"),error_ratio=d.get("worst_error_over_tolerance"),
                error=d.get("error"),stderr=p.stderr[-500:],
                elapsed=round(time.monotonic()-start,3))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default=str(ROOT/"competition/k029a/results"))
    ap.add_argument("--levels",default="64,512,4096,65536")
    ap.add_argument("--seeds",default="12345,23456")
    ap.add_argument("--timeout",type=int,default=300)
    ap.add_argument("--modes",default=",".join(MODES))
    a=ap.parse_args()
    out=Path(a.output_dir)
    out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    prec=ref.Precision(**PRECISION)
    original=ref._add_row
    levels=[int(x) for x in a.levels.split(",")]
    seeds=[int(x) for x in a.seeds.split(",")]
    modes=[x.strip() for x in a.modes.split(",")]
    records=[]
    try:
        for mode in modes:
            if mode not in MODES:raise ValueError(mode)
            stats={}
            ref._add_row=original if mode=="reference" else make_row(original,mode,stats)
            print("BUILD",mode,flush=True)
            try:
                circ=ref.build_nr_circuit(10,prec=prec)
                path=out/f"qrr_complement_{mode}.kmb"
                circ.to_file(str(path),format="kmb")
            except Exception as ex:
                row=dict(mode=mode,status="BUILD_FAIL",error=repr(ex))
                records.append(row);print(json.dumps(row),flush=True)
                continue
            if mode!="reference" and not stats:
                row=dict(mode=mode,status="NO_PATCHED_ROW",file_bytes=path.stat().st_size)
                records.append(row);print(json.dumps(row),flush=True)
                continue
            for level in levels:
                failed=False
                for seed in seeds:
                    result=dict(mode=mode,level=level,seed=seed,
                                file_bytes=path.stat().st_size,
                                patched_calls=stats,**verify(path,level,seed,a.timeout))
                    records.append(result)
                    print(json.dumps(result,sort_keys=True),flush=True)
                    if result.get("status")!="PASS" or result.get("exit")!=0:
                        failed=True;break
                if failed:break
    finally:
        ref._add_row=original
        (out/"official_ab.json").write_text(json.dumps(records,indent=2))
    for mode in modes:
        high=[r for r in records if r.get("mode")==mode and r.get("level")==max(levels)]
        if len(high)==len(seeds) and all(r.get("status")=="PASS" and r.get("exit")==0 for r in high):
            print("HIGH_LEVEL_PASS",mode,round(sum(r["score"] for r in high)/len(high),5),flush=True)
    print("SAVED",out/"official_ab.json",flush=True)

if __name__=="__main__":
    main()
