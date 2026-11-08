#!/usr/bin/env python3
"""K035: selective direct controlled-add arithmetic transplant into K034.

Preserves K034 row-local scratch for all unsupported/sparse product rows.
When _add_row terms cover contiguous source bits, replace the AND-register,
ordinary add, uncompute sequence with exact quantum-controlled iadd/isub.
Screen on official 64-input verifier; full-domain test both seeds only on
strict official prefix-score reductions. No inferred correctness promotions.
"""
from __future__ import annotations
import argparse
import importlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def load(local_name,file):
    spec=importlib.util.spec_from_file_location(local_name,file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

k031=load("k031",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=load("k034",ROOT/"competition/k034/k034_row_local_scratch.py")
PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=28)
BASE=1933697.432675161
STAGES=("horner","square","multiply_m","multiply_y0")
# Single stage or combinations: only score-promising candidates get full validation.
MODES=tuple(STAGES)+("square+multiply_y0","horner+square",
                     "horner+multiply_y0","all")

def make_row(selected,stats):
    fallback=k034.local_row("compact",stats["fallback"])
    def row(builder,inverse,control,terms,target,scratch,subtract=False):
        caller=sys._getframe(1).f_code.co_name.lstrip("_")
        positions=[i for _,i in terms]
        if not positions:
            return fallback(builder,inverse,control,terms,target,scratch,
                            subtract=subtract)
        lo=min(positions)
        # Must preserve the original index -> bit map, no reordered/sparse bits.
        ordered=sorted(terms,key=lambda pair:pair[1])
        indices=[j for _,j in ordered]
        stage_enabled=caller in selected
        contiguous=indices==list(range(lo,lo+len(indices)))
        if stage_enabled and contiguous:
            src=km.array([q for q,_ in ordered])
            suffix=target[lo:]
            if subtract != inverse:
                builder.isub(src,target=suffix,control=control)
            else:
                builder.iadd(src,target=suffix,control=control)
            stats["direct_by_stage"][caller]=stats["direct_by_stage"].get(caller,0)+1
            return
        key="sparse" if stage_enabled else "unselected"
        stats["fallback_reasons"][key]=stats["fallback_reasons"].get(key,0)+1
        return fallback(builder,inverse,control,terms,target,scratch,
                        subtract=subtract)
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k035/results"))
    ap.add_argument("--timeout",type=int,default=300)
    ap.add_argument("--modes",default=",".join(MODES))
    ap.add_argument("--prefix",type=int,default=64)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    saved=out/"receipts.jsonl";old=k031.read_receipts(saved)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    build0,row0=ref.build_nr_circuit,ref._add_row
    k034_file=ROOT/"competition/k034/results/row_local_full.kmb"
    if not k034_file.exists():
        raise SystemExit("K034 control artifact absent: "+str(k034_file))
    baseline=k031.verify(k034_file,args.prefix,12345,args.timeout)
    if baseline.get("status")!="PASS" or baseline.get("exit_code")!=0:
        raise SystemExit("K034 prefix control failed "+str(baseline))
    base_score=baseline["score"]
    print("K034_PREFIX_CONTROL",json.dumps({"score":base_score,"qubits":baseline.get("num_qubits"),
              "toffoli":baseline.get("toffoli_count")}),flush=True)
    verified=[]
    try:
        for mode in args.modes.split(","):
            mode=mode.strip()
            if mode=="all":selected=set(STAGES)
            else:
                selected=set(mode.split("+"))
                if not selected.issubset(set(STAGES)):raise ValueError(mode)
            ident="direct_"+mode.replace("+","_")
            filename=out/(ident+".kmb")
            if ident in old:
                print("CACHED",ident,old[ident].get("status"),flush=True)
                if old[ident].get("status")=="PASS_FULL":verified.append(old[ident])
                continue
            stats={"fallback":{"rows":0,"allocated_sum":0,"max_row_width":0},
                   "direct_by_stage":{},"fallback_reasons":{}}
            try:
                ref.build_nr_circuit=k034.no_persistent_scratch(build0)
                ref._add_row=make_row(selected,stats)
                build=k031.build(ref,PREC,1,filename)
                direct=sum(stats["direct_by_stage"].values())
                if not direct:raise RuntimeError("No contiguous product rows substituted")
                screen=k031.verify(filename,args.prefix,12345,args.timeout)
                screen_ok=screen.get("status")=="PASS" and screen.get("exit_code")==0
                less=screen_ok and screen["score"]<base_score-1e-7
                print("SCREEN",json.dumps({"id":ident,"direct":direct,
                      "qubits":build["num_qubits"],"score":screen.get("score"),
                      "base_score":base_score,"status":screen.get("status"),
                      "eligible_full":less}),flush=True)
                first=k031.verify(filename,k031.FULL_X,12345,args.timeout) if less else None
                first_ok=bool(first and first.get("status")=="PASS" and first.get("exit_code")==0)
                second=k031.verify(filename,k031.FULL_X,23456,args.timeout) if first_ok else None
                full=bool(first_ok and second and second.get("status")=="PASS" and second.get("exit_code")==0)
                row={"id":ident,"mode":mode,"status":"PASS_FULL" if full else
                     ("NOT_CHEAPER_PREFIX" if screen_ok and not less else "FAIL"),
                     "build":build,"stats":stats,"screen":screen,"first":first,"second":second}
                if full:
                    row["score"]=first["score"];row["delta"]=first["score"]-BASE
                    verified.append(row)
            except Exception as exc:
                row={"id":ident,"mode":mode,"status":"BUILD_ERROR",
                     "error":repr(exc),"stats":stats}
            finally:
                ref.build_nr_circuit=build0
                ref._add_row=row0
            k031.append(saved,old,row)
    finally:
        ref.build_nr_circuit=build0
        ref._add_row=row0
    ranking=sorted([
        {"id":r["id"],"score":r["score"],"delta":r["delta"],
         "qubits":r["build"]["num_qubits"],"path":str(out/(r["id"]+".kmb"))}
        for r in verified],key=lambda v:v["score"])
    (out/"frontier.json").write_text(json.dumps({"control_score":BASE,
                                              "verified":ranking},indent=2))
    print("K035_FULL_DOMAIN_VERIFIED",json.dumps(ranking),flush=True)
    print("BEST_CONTROL_SCORE",BASE,flush=True)

if __name__=="__main__":main()
