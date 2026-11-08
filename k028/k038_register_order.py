#!/usr/bin/env python3
"""K038: reversible register allocation-order ablation around full-domain K034.

Retains exact equations, precision, phase cut, row-local AND add/uncompute.
Only changes the initial order of register allocations, potentially reducing
Kickmix allocator high-water fragmentation. Exact official scores are checked
at prefix and full-domain, and no candidate promoted without both full passes.
"""
from __future__ import annotations
import argparse, ast, importlib, importlib.util, inspect, itertools, json, sys, textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

k031=load("k031",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=load("k034",ROOT/"competition/k034/k034_row_local_scratch.py")

PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,
          result_bits=28,square_bits=28)
CONTROL_SCORE=1933697.432675161

# Explicit allocations including x total 199. x remains first because the
# official input register must retain its exact name and interface.
TEMPLATES={
    "y1":"y1 = alloc(out_bits, 'y1')",
    "flags":"flags = alloc(n_p, 'flags')",
    "selectors":"selectors = alloc(3, 'selectors')",
    "coefs":"coefs = [alloc(prec.coef_bits, f'c{j}') for j in range(4)]",
    "square":"square = alloc(prec.square_bits, 'square')",
    "z":"z = alloc(prec.product_bits + 2, 'z')",
    "scratch":"scratch = km.array([])",
}
ORIGINAL=("y1","flags","selectors","coefs","square","z")
ORDERS=[
    ORIGINAL,
    tuple(reversed(ORIGINAL)),
    ("coefs","square","z","y1","flags","selectors"),
    ("square","z","coefs","flags","selectors","y1"),
    ("z","square","coefs","selectors","flags","y1"),
    ("flags","selectors","coefs","square","z","y1"),
    ("y1","coefs","z","square","flags","selectors"),
    ("y1","flags","selectors","z","square","coefs"),
    ("coefs","y1","flags","selectors","square","z"),
    ("z","y1","coefs","square","selectors","flags"),
    ("flags","selectors","y1","coefs","square","z"),
    ("coefs","flags","selectors","square","z","y1"),
]

def make_builder(original,order):
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    fn=next(n for n in tree.body
        if isinstance(n,ast.FunctionDef) and n.name=="build_nr_circuit")
    # AST rewrite only the contiguous register-definition block, preserving
    # the immutable x register, all equations, calls and cleanup semantics.
    def targets(node):
        if not isinstance(node,ast.Assign):return set()
        names=set()
        for t in node.targets:
            for child in ast.walk(t):
                if isinstance(child,ast.Name):names.add(child.id)
        return names
    groups=[]
    for i,n in enumerate(fn.body):
        names=targets(n)
        if names & set(TEMPLATES):
            if not names.issubset(set(TEMPLATES)):
                raise AssertionError("Unexpected register assignment "+str(names))
            groups.append(i)
    if len(groups)!=4 or groups!=list(range(groups[0],groups[0]+4)):
        raise AssertionError("Unexpected original allocation block "+str(groups))
    start,end=groups[0],groups[-1]+1
    replacement=[]
    for name in (*order,"scratch"):
        replacement.extend(ast.parse(TEMPLATES[name]).body)
    fn.body[start:end]=replacement
    ast.fix_missing_locations(tree)
    ns=original.__globals__.copy()
    exec(compile(tree,inspect.getsourcefile(original) or "<K038>","exec"),ns,ns)
    return ns["build_nr_circuit"]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",default=str(ROOT/"competition/k038/results"))
    p.add_argument("--timeout",type=int,default=300)
    p.add_argument("--prefix",type=int,default=64)
    p.add_argument("--max-orders",type=int,default=len(ORDERS))
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    receipts=out/"receipts.jsonl";old=k031.read_receipts(receipts)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    orig_build,orig_row=ref.build_nr_circuit,ref._add_row
    control=ROOT/"competition/k034/results/row_local_full.kmb"
    if not control.exists():raise SystemExit("Missing K034 full-domain control")
    base=k031.verify(control,a.prefix,12345,a.timeout)
    if base.get("status")!="PASS" or base.get("exit_code")!=0:
        raise SystemExit("Control screen failed "+str(base))
    print("CONTROL",json.dumps({"score":base["score"],
        "num_qubits":base.get("num_qubits"),
        "toffoli_count":base.get("toffoli_count")}),flush=True)
    ranked=[]
    for i,order in enumerate(ORDERS[:a.max_orders]):
        key=f"order_{i:02d}"
        path=out/(key+".kmb")
        if key in old:
            row=old[key]
            print("CACHED",key,row.get("status"),flush=True)
            if row.get("status")=="PASS_FULL":ranked.append(row)
            continue
        print("BUILD",key," ".join(order),flush=True)
        counts={"rows":0,"allocated_sum":0,"max_row_width":0}
        try:
            ref.build_nr_circuit=make_builder(orig_build,order)
            ref._add_row=k034.local_row("compact",counts)
            built=k031.build(ref,PREC,1,path)
            scan=k031.verify(path,a.prefix,12345,a.timeout)
            screen_ok=scan.get("status")=="PASS" and scan.get("exit_code")==0
            improvement=screen_ok and scan["score"]<base["score"]-1e-8
            if screen_ok:
                print("SCREEN",key,"qubits",built["num_qubits"],
                    "score",scan["score"],"delta",scan["score"]-base["score"],
                    flush=True)
            first=k031.verify(path,k031.FULL_X,12345,a.timeout) if improvement else None
            first_ok=bool(first and first.get("status")=="PASS" and
                         first.get("exit_code")==0)
            second=k031.verify(path,k031.FULL_X,23456,a.timeout) if first_ok else None
            full_ok=bool(first_ok and second and second.get("status")=="PASS" and
                         second.get("exit_code")==0)
            row={"id":key,"order":order,"build":built,"row_counts":counts,
                 "screen":scan,"first":first,"second":second,
                 "status":("PASS_FULL" if full_ok else
                           "NOT_CHEAPER_PREFIX" if screen_ok and not improvement
                           else "FAIL")}
            if full_ok:
                row["score"]=first["score"]
                row["delta"]=row["score"]-CONTROL_SCORE
                ranked.append(row)
        except Exception as exc:
            row={"id":key,"order":order,"status":"ERROR","error":repr(exc)}
        finally:
            ref.build_nr_circuit=orig_build
            ref._add_row=orig_row
        k031.append(receipts,old,row)
    frontier=sorted([
        {"id":x["id"],"score":x["score"],"delta":x["delta"],
         "qubits":x["build"]["num_qubits"],
         "order":x["order"],"path":str(out/(x["id"]+".kmb"))}
        for x in ranked],key=lambda x:x["score"])
    (out/"frontier.json").write_text(json.dumps(
        {"control_score":CONTROL_SCORE,"full_domain_candidates":frontier},indent=2))
    print("K038_FULL_DOMAIN_FRONTIER",json.dumps(frontier),flush=True)
    print("CONTROL_SCORE",CONTROL_SCORE,flush=True)

if __name__=="__main__":main()
