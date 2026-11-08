#!/usr/bin/env python3
"""K034 — QRR clean-workspace allocation experiment for Kickmix inverse sqrt.

Replace persistent scratch allocation with row-local, compute/consume/uncompute/free.
Modes:
  full    row-local scratch using original reference indexing
  compact row-local scratch using relative indexing; identical modular arithmetic
Use K031 Cut-1 precision and phase, compare against immutable verified control.
Never promote without official full-domain PASS with two seeds.
"""
from __future__ import annotations
import argparse
import ast
import importlib
import importlib.util
import inspect
import json
import sys
import textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km
K031=ROOT/"competition/k031/k031_full_domain_repair.py"
sp=importlib.util.spec_from_file_location("k031",K031)
k031=importlib.util.module_from_spec(sp);sp.loader.exec_module(k031)

PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,
          result_bits=28,square_bits=28)
CONTROL_SCORE=1940431.2299939874

def no_persistent_scratch(original):
    src=textwrap.dedent(inspect.getsource(original))
    tree=ast.parse(src)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=="build_nr_circuit")
    matches=[n for n in ast.walk(fn)
             if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=="scratch" for t in n.targets)]
    if len(matches)!=1:raise AssertionError("Unexpected scratch assignments: "+str(len(matches)))
    matches[0].value=ast.Call(
        func=ast.Attribute(value=ast.Name(id="km",ctx=ast.Load()),
                           attr="array",ctx=ast.Load()),
        args=[ast.List(elts=[],ctx=ast.Load())],keywords=[])
    ast.fix_missing_locations(tree)
    globals_=original.__globals__.copy()
    exec(compile(tree,inspect.getsourcefile(original) or "<k034>","exec"),globals_,globals_)
    return globals_["build_nr_circuit"]

def local_row(mode,counts):
    def row(builder,inverse,control,terms,target,scratch,subtract=False):
        if not terms:raise AssertionError("Empty row")
        indices=[i for _,i in terms]
        low=min(indices)
        high=max(indices)
        if low<0 or high>=len(target):
            raise ValueError("Invalid partial-product support "+repr((low,high,len(target))))
        n=(len(target) if mode=="full" else len(target)-low)
        tmp=builder.alloc_qubits(n)
        counts["rows"]+=1
        counts["allocated_sum"]+=n
        counts["max_row_width"]=max(n,counts["max_row_width"])
        src=km.array([q for q,_ in terms])
        prod=km.array([tmp[i if mode=="full" else i-low] for _,i in terms])
        builder.init_and(control,src,prod)
        if mode=="full":
            operand=tmp[low:len(target)]
        else:
            operand=tmp[:len(target)-low]
        dest=target[low:len(target)]
        if subtract != inverse:
            builder.isub(operand,target=dest)
        else:
            builder.iadd(operand,target=dest)
        builder.del_and(control,src,prod)
        builder.free(tmp)
    return row

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--out",default=str(ROOT/"competition/k034/results"))
    pa.add_argument("--timeout",type=int,default=300)
    pa.add_argument("--prefix",type=int,default=65536)
    a=pa.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    history=out/"receipts.jsonl"; old=k031.read_receipts(history)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    original_build,original_row=ref.build_nr_circuit,ref._add_row
    control=ROOT/"competition/k031/results/precision_003_cut_1.kmb"
    if not control.exists():raise SystemExit("Missing K031 verified control "+str(control))
    candidate_results=[]
    try:
        for mode in ("full","compact"):
            ident="row_local_"+mode
            path=out/(ident+".kmb")
            if ident in old:
                result=old[ident]
                print("CACHED",ident,result.get("status"),flush=True)
                if result.get("status")=="PASS_FULL":candidate_results.append(result)
                continue
            stats={"rows":0,"allocated_sum":0,"max_row_width":0}
            print("BUILD",ident,flush=True)
            try:
                ref.build_nr_circuit=no_persistent_scratch(original_build)
                ref._add_row=local_row(mode,stats)
                info=k031.build(ref,PREC,1,path)
                if not stats["rows"]:raise AssertionError("No row calls intercepted")
                short=k031.verify(path,a.prefix,12345,a.timeout)
                prefix_ok=(short.get("status")=="PASS" and short.get("exit_code")==0)
                first=k031.verify(path,k031.FULL_X,12345,a.timeout) if prefix_ok else None
                full_ok=bool(first and first.get("status")=="PASS" and first.get("exit_code")==0)
                second=k031.verify(path,k031.FULL_X,23456,a.timeout) if full_ok else None
                full_ok=bool(full_ok and second and second.get("status")=="PASS" and second.get("exit_code")==0)
                row={"id":ident,"status":"PASS_FULL" if full_ok else "FAIL",
                     "build":info,"stage":stats,"prefix":short,"first":first,
                     "second":second}
                if full_ok:
                    row["score"]=first["score"]
                    row["delta_vs_control"]=row["score"]-CONTROL_SCORE
                    candidate_results.append(row)
            except Exception as exc:
                row={"id":ident,"status":"BUILD_ERROR","error":repr(exc),"stage":stats}
            finally:
                ref.build_nr_circuit=original_build
                ref._add_row=original_row
            k031.append(history,old,row)
            if row.get("score") is not None:
                print("FULL_VERIFIED_SCORE",ident,row["score"],
                      "DELTA",row["delta_vs_control"],flush=True)
    finally:
        ref.build_nr_circuit=original_build
        ref._add_row=original_row
    ordered=sorted(
        [{"id":x["id"],"score":x["score"],"delta":x["delta_vs_control"],
          "num_qubits":x["build"]["num_qubits"],
          "path":str(out/(x["id"]+".kmb"))} for x in candidate_results],
        key=lambda x:x["score"])
    (out/"frontier.json").write_text(json.dumps(
        {"verified_control_score":CONTROL_SCORE,"candidates":ordered},indent=2))
    print("K034_FRONTIER",json.dumps(ordered),flush=True)
    if not ordered or ordered[0]["score"]>=CONTROL_SCORE:
        print("NO_VERIFIED_SCORE_IMPROVEMENT",flush=True)
    else:
        print("NEW_FULL_DOMAIN_WINNER",json.dumps(ordered[0]),flush=True)

if __name__=="__main__":main()
