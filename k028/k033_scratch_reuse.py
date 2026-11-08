#!/usr/bin/env python3
"""K033: QRR-style clean-workspace search on the full-domain-valid K031 circuit.

The scratch register is returned to zero by the reference compute/uncompute
protocol. Probe its *allocated width* without changing any operation or
replacing exact arithmetic. Keep only full-domain official PASS outcomes.

Also records per-stage partial-product demand, a useful measurement for
future proven scratch/ancilla sharing. No shortened operand trick (K029-C
was a measured regression), no unsafe early free.
"""
from __future__ import annotations
import argparse
import ast
import collections
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
K031=ROOT/"competition/k031/k031_full_domain_repair.py"
spec=importlib.util.spec_from_file_location("k031",K031)
k031=importlib.util.module_from_spec(spec)
spec.loader.exec_module(k031)

PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,
          result_bits=28,square_bits=28)
WINNER_SCORE=1940431.2299939874

def rewrite_scratch(ref,trim):
    """AST rewrite exactly the scratch allocation's requested length."""
    original=ref.build_nr_circuit
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=="build_nr_circuit")
    assignments=[n for n in ast.walk(fn)
                 if isinstance(n,ast.Assign)
                 and any(isinstance(x,ast.Name) and x.id=="scratch"
                         for x in n.targets)]
    if len(assignments)!=1:raise AssertionError(
        "Expected one scratch allocation; got "+str(len(assignments)))
    node=assignments[0]
    if not isinstance(node.value,ast.Call) or not node.value.args:
        raise AssertionError("Unexpected scratch constructor")
    old=node.value.args[0]
    node.value.args[0]=ast.Call(
        func=ast.Name(id="max",ctx=ast.Load()),
        args=[ast.Constant(value=1),
              ast.BinOp(left=old,op=ast.Sub(),right=ast.Constant(value=trim))],
        keywords=[])
    ast.fix_missing_locations(tree)
    namespace=ref.__dict__.copy()
    exec(compile(tree,inspect.getsourcefile(original) or "<K033>", "exec"),
         namespace,namespace)
    return namespace["build_nr_circuit"]

def profiling_row(original,counters):
    def wrapped(builder,inverse,control,terms,target,scratch,subtract=False):
        caller=sys._getframe(1).f_code.co_name
        key=f"{caller}:{'inverse' if inverse else 'forward'}"
        bucket=counters.setdefault(key,{"rows":0,"terms":0,
                                         "max_scratch_index":-1,
                                         "max_target_width":0})
        bucket["rows"]+=1
        bucket["terms"]+=len(terms)
        bucket["max_target_width"]=max(bucket["max_target_width"],len(target))
        if terms:
            bucket["max_scratch_index"]=max(
                bucket["max_scratch_index"],max(i for _,i in terms))
        return original(builder,inverse,control,terms,target,scratch,
                        subtract=subtract)
    return wrapped

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default=str(ROOT/"competition/k033/results"))
    p.add_argument("--max-trim",type=int,default=8)
    p.add_argument("--timeout",type=int,default=300)
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    receipts=out/"receipts.jsonl"
    old=k031.read_receipts(receipts)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    original_build=ref.build_nr_circuit
    original_row=ref._add_row
    profile={}
    # The known full-domain winner is immutable as a reference on disk.
    winner=ROOT/"competition/k031/results/precision_003_cut_1.kmb"
    if not winner.exists():
        raise SystemExit("Missing full-domain K031 control: "+str(winner))
    try:
        for trim in range(args.max_trim+1):
            key=f"scratch_trim_{trim}"
            file=out/(key+".kmb")
            if key in old:
                print("CACHED",key,old[key]["status"],flush=True)
                continue
            profile_here={}
            ref._add_row=profiling_row(original_row,profile_here)
            ref.build_nr_circuit=(original_build if trim==0
                                   else rewrite_scratch(ref,trim))
            print("BUILD",key,flush=True)
            try:
                build=k031.build(ref,PREC,1,file)
                circuit=type("Stub",(),{})()
                # First check exact resource improvement before spending
                # time on expensive full-domain verification.
                metadata={"base_num_qubits":255,
                          "num_qubits":build["num_qubits"],
                          "source":"K031 full domain control"}
                if trim==0:
                    profile=profile_here
                    (out/"row_profile.json").write_text(
                        json.dumps(profile,indent=2,sort_keys=True))
                if trim>0 and build["num_qubits"]>=255:
                    row={"id":key,"trim":trim,"build":build,"metadata":metadata,
                         "status":"NO_QUBIT_REDUCTION"}
                else:
                    first=k031.verify(file,k031.FULL_X,12345,args.timeout)
                    good=(first.get("status")=="PASS" and
                          first.get("exit_code")==0)
                    second=(k031.verify(file,k031.FULL_X,23456,args.timeout)
                            if good else None)
                    good=(good and second.get("status")=="PASS"
                          and second.get("exit_code")==0)
                    row={"id":key,"trim":trim,"build":build,
                         "metadata":metadata,"first":first,"second":second,
                         "status":"PASS_FULL" if good else "FAIL_FULL"}
                    if good:row["score"]=first["score"]
            except Exception as exc:
                row={"id":key,"trim":trim,"status":"BUILD_ERROR",
                     "error":repr(exc)}
            finally:
                ref.build_nr_circuit=original_build
                ref._add_row=original_row
            k031.append(receipts,old,row)
    finally:
        ref.build_nr_circuit=original_build
        ref._add_row=original_row
    ranked=sorted([
        {"id":v["id"],"score":v["score"],
         "qubits":v["build"]["num_qubits"],
         "path":str(out/(v["id"]+".kmb"))}
        for v in old.values() if v.get("status")=="PASS_FULL"
    ],key=lambda x:x["score"])
    (out/"frontier.json").write_text(json.dumps(ranked,indent=2))
    print("CURRENT_VERIFIED_K031_SCORE",WINNER_SCORE,flush=True)
    print("K033_VERIFIED_FRONTIER",json.dumps(ranked),flush=True)
    print("STAGE_ROW_PROFILE",str(out/"row_profile.json"),flush=True)

if __name__=="__main__":main()
