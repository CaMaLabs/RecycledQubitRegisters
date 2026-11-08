#!/usr/bin/env python3
"""K031: Search a FULL-DOMAIN valid Kickmix precision, then test phase cuts.

Uses the unmodified official invsqrt verifier and original NR circuit source.
Does not mistake prefix PASS for full-domain PASS. Resumable JSONL receipts.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import itertools
import json
import math
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VERIFIERS=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VERIFIERS))
import kickmix as km

BASE={"coef_bits":17,"delta_bits":12,"product_bits":27,
      "result_bits":28,"square_bits":27}
FULL_X=3133452
HARD_X=(270063,3127095)
KEYS=tuple(BASE)

def valid_batch(num):
    batch=min(256,num)
    while num%batch: batch-=1
    return batch

def verify(path,max_x,seed,timeout):
    cmd=[sys.executable,
         str(VERIFIERS/"invsqrt/verify_submission_invsqrt.py"),
         str(path),"--format","kmb","--max-x",str(max_x),
         "--shots-per-x","1","--batch-size",str(valid_batch(max_x)),
         "--max-workers","1","--seed",str(seed)]
    start=time.monotonic()
    try:
        proc=subprocess.run(cmd,cwd=VERIFIERS,capture_output=True,
                            text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status":"TIMEOUT","elapsed":round(time.monotonic()-start,2)}
    try:
        result=json.loads(proc.stdout)
    except ValueError:
        result={"status":"NON_JSON","stdout_tail":proc.stdout[-600:]}
    result["exit_code"]=proc.returncode
    result["elapsed"]=round(time.monotonic()-start,2)
    if proc.stderr:result["stderr_tail"]=proc.stderr[-1000:]
    return result

def rank_specs(limit):
    """Incremental local neighborhoods, avoiding blind wide Cartesian scans."""
    specs=[]
    seen=set()
    def add(delta):
        spec={k:BASE[k]+delta.get(k,0) for k in KEYS}
        key=tuple(spec[k] for k in KEYS)
        if key not in seen:
            seen.add(key)
            specs.append(spec)
    add({})
    # Widen likely numerical precision first, one coordinate at a time.
    for bump in (1,2,3,4,6,8):
        for k in ("delta_bits","coef_bits","square_bits","product_bits","result_bits"):
            add({k:bump})
    # Combined increases when independent changes cannot cure the error.
    for bump in (1,2,3,4):
        for count in (2,3,4,5):
            for subset in itertools.combinations(
                ("delta_bits","coef_bits","square_bits","product_bits","result_bits"),count
            ):
                add({k:bump for k in subset})
    # Final broad precision fallbacks.
    for bump in (6,8,10):
        add({k:bump for k in KEYS})
    return specs[:limit]

def make_phase(ref,cut):
    def phase(builder,y):
        size=len(y)
        with builder.mark("phase_by_bits"):
            for j in range(cut,size):
                builder.z_pow(y[j],Fraction(2)**(j-size+1))
    return phase

def build(ref,spec,cut,out):
    prec=ref.Precision(**spec)
    original=ref._phase_by_bits
    try:
        if cut:ref._phase_by_bits=make_phase(ref,cut)
        circ=ref.build_nr_circuit(10,prec=prec)
        circ.to_file(str(out),format="kmb")
        return {"num_qubits":circ.num_qubits,
                "output_bits":prec.output_bits(10),
                "file_bytes":out.stat().st_size,
                "sha256":hashlib.sha256(out.read_bytes()).hexdigest()}
    finally:
        ref._phase_by_bits=original

def read_receipts(path):
    entries={}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                row=json.loads(line)
                if "id" in row:entries[row["id"]]=row
            except ValueError:continue
    return entries

def append(path,entries,row):
    with path.open("a") as f:
        f.write(json.dumps(row,sort_keys=True,default=str)+"\n")
        f.flush()
    entries[row["id"]]=row
    headline={"id":row["id"],"status":row["status"]}
    if "score" in row: headline["score"]=row["score"]
    if "error" in row: headline["error"]=row["error"]
    print("RESULT",json.dumps(headline,sort_keys=True),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default=str(ROOT/"competition/k031/results"))
    p.add_argument("--max-specs",type=int,default=75)
    p.add_argument("--max-cut",type=int,default=6)
    p.add_argument("--timeout",type=int,default=300)
    p.add_argument("--seed",type=int,default=12345)
    p.add_argument("--second-seed",type=int,default=23456)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    receipts=out/"receipts.jsonl"
    existing=read_receipts(receipts)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    selected=None
    results=[]

    for index,spec in enumerate(rank_specs(args.max_specs)):
        key=f"precision_{index:03d}"
        if key in existing:
            row=existing[key]
            if row.get("status")=="PASS_FULL":
                selected=(key,spec,out/f"{key}.kmb",row)
                break
            continue
        candidate=out/f"{key}.kmb"
        print("PRECISION",key,json.dumps(spec,sort_keys=True),flush=True)
        try:
            info=build(ref,spec,0,candidate)
            # The official verifier, not a guessed numerical bound, is the gate.
            v=verify(candidate,FULL_X,args.seed,args.timeout)
            good=v.get("status")=="PASS" and v.get("exit_code")==0
            if good:
                other=verify(candidate,FULL_X,args.second_seed,args.timeout)
                good=other.get("status")=="PASS" and other.get("exit_code")==0
            else:
                other=None
            row={"id":key,"spec":spec,"build":info,"verification":v,
                 "second_seed_verification":other,
                 "status":"PASS_FULL" if good else "FAIL_FULL"}
            if good:
                row["score"]=v.get("score")
        except Exception as ex:
            row={"id":key,"spec":spec,"status":"BUILD_ERROR","error":repr(ex)}
        append(receipts,existing,row)
        if row["status"]=="PASS_FULL":
            selected=(key,spec,candidate,row)
            break

    if selected is None:
        print("NO_FULL_DOMAIN_PASS_IN_CURRENT_SEARCH. Resume with --max-specs 150, or broaden the precision strategy.",flush=True)
        return

    key,spec,baseline,baseline_row=selected
    print("FULL_DOMAIN_BASELINE",key,json.dumps(spec,sort_keys=True),
          "score",baseline_row.get("score"),flush=True)
    accepted=[{"cut":0,"score":baseline_row["score"],"path":str(baseline)}]
    for cut in range(1,args.max_cut+1):
        identity=f"{key}_cut_{cut}"
        if identity in existing:
            row=existing[identity]
            if row.get("status")=="PASS_FULL":
                accepted.append({"cut":cut,"score":row["score"],"path":str(out/f"{identity}.kmb")})
            continue
        variant=out/f"{identity}.kmb"
        try:
            info=build(ref,spec,cut,variant)
            f=info["output_bits"]
            max_omitted_radians=float(2*math.pi*sum(
                (Fraction(2)**(j-f+1) for j in range(cut)),Fraction(0)))
            v=verify(variant,FULL_X,args.seed,args.timeout)
            good=v.get("status")=="PASS" and v.get("exit_code")==0
            if good:
                other=verify(variant,FULL_X,args.second_seed,args.timeout)
                good=other.get("status")=="PASS" and other.get("exit_code")==0
            else:other=None
            row={"id":identity,"spec":spec,"cut":cut,"build":info,
                 "max_omitted_radians":max_omitted_radians,
                 "verification":v,"second_seed_verification":other,
                 "status":"PASS_FULL" if good else "FAIL_FULL"}
            if good:
                row["score"]=v.get("score")
                accepted.append({"cut":cut,"score":row["score"],"path":str(variant)})
        except Exception as ex:
            row={"id":identity,"spec":spec,"cut":cut,
                 "status":"BUILD_ERROR","error":repr(ex)}
        append(receipts,existing,row)

    accepted.sort(key=lambda x:x["score"])
    report={"baseline":baseline_row,"accepted_sorted":accepted,
            "full_max_x":FULL_X,"hard_x":HARD_X,
            "warning":"Full-domain verifier PASS is required for every promoted candidate."}
    (out/"frontier.json").write_text(json.dumps(report,indent=2,default=str))
    print("FULL_DOMAIN_VERIFIED_FRONTIER",json.dumps(accepted,sort_keys=True),flush=True)
    print("SAVED",out/"frontier.json",flush=True)

if __name__=="__main__":main()
