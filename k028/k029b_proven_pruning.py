#!/usr/bin/env python3
"""K029-B: exact static partial-product pruning in Kickmix's NR circuit.

A term at bit offset >= len(target) contributes 0 mod 2**len(target).
A term below the window must NOT be removed: it can carry into retained bits.
Do not assume amplitude-distribution or selector correlations.

This intentionally conservative pass reports all inspected rows, produces
native A/B circuits and runs the official verifier. If no provable
reductions exist, it explicitly reports NO_PROVABLE_PRUNING.
"""
from __future__ import annotations
import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VERIFIERS=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VERIFIERS))
import kickmix as km

P=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=27)

def verify(path, level, seed):
    cmd=[sys.executable,str(VERIFIERS/"invsqrt/verify_submission_invsqrt.py"),str(path),
         "--format","kmb","--max-x",str(level),"--shots-per-x","1",
         "--batch-size",str(min(level,256)),"--max-workers","1","--seed",str(seed)]
    try:
        p=subprocess.run(cmd,cwd=VERIFIERS,capture_output=True,text=True,timeout=300)
        d=json.loads(p.stdout)
        return {"status":d.get("status"),"code":p.returncode,"score":d.get("score"),
                "error_ratio":d.get("worst_error_over_tolerance"),
                "error":d.get("error"),"stderr":p.stderr[-400:]}
    except Exception as e:
        return {"status":"EXCEPTION","error":repr(e)}

def build(ref,prec,path):
    c=ref.build_nr_circuit(10,prec=prec)
    c.to_file(str(path),format="kmb")
    return path.stat().st_size

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k029b/results"))
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    prec=ref.Precision(**P)
    original=ref._add_row
    audit={"rows":0,"terms_examined":0,"terms_pruned":0,"rows_eliminated":0,
           "invalid_negative_offsets":0,"proof":"2**offset == 0 mod 2**target_width iff offset >= target_width"}
    control=out/"control.kmb"
    baseline_bytes=build(ref,prec,control)

    def guarded_add(builder,inverse,control,terms,target,scratch,subtract=False):
        audit["rows"]+=1
        audit["terms_examined"]+=len(terms)
        width=len(target)
        kept=[(q,i) for q,i in terms if i<width]
        audit["terms_pruned"]+=len(terms)-len(kept)
        # Negative offsets describe fractional bits and require rounding or
        # a special window treatment. Refuse rather than silently truncate.
        if any(i<0 for _,i in kept):
            audit["invalid_negative_offsets"]+=1
            raise ValueError("Negative weighted partial product: no pruning permitted")
        if not kept:
            audit["rows_eliminated"]+=1
            return
        return original(builder,inverse,control,kept,target,scratch,subtract=subtract)

    candidate=out/"pruned.kmb"
    ref._add_row=guarded_add
    try:
        candidate_bytes=build(ref,prec,candidate)
    finally:
        ref._add_row=original
    print(json.dumps({"audit":audit,"control_bytes":baseline_bytes,
                      "candidate_bytes":candidate_bytes},sort_keys=True),flush=True)
    if audit["terms_pruned"]==0:
        print("NO_PROVABLE_PRUNING: all generated partial-product offsets are already in range.",flush=True)
    else:
        print("PROVABLE_PRUNING_FOUND",audit["terms_pruned"],flush=True)

    results=[]
    for level in (64,512,4096,65536):
        for name,path in (("control",control),("pruned",candidate)):
            for seed in (12345,23456):
                row={"circuit":name,"level":level,"seed":seed,**verify(path,level,seed)}
                results.append(row);print(json.dumps(row),flush=True)
                if row["status"]!="PASS" or row["code"]!=0:
                    print("STOP_ON_FAILURE",flush=True)
                    (out/"results.json").write_text(json.dumps({"audit":audit,"tests":results},indent=2))
                    return
    (out/"results.json").write_text(json.dumps({"audit":audit,"tests":results},indent=2))
    print("FINISHED: results.json; only compare scores when both circuits PASS",flush=True)

if __name__=="__main__":
    main()
