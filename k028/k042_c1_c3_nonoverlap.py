#!/usr/bin/env python3
"""K042: lifetime scheduling for c1 + c3 with NO extra Horner arithmetic.

Compared with full-domain PASS K040:
  Forward: open c3 -> update c2 -> close c3 -> open c1 -> update c1,c0.
  Reverse: undo c0,c1 -> close c1 -> open c3 -> undo c2 -> close c3.
c0,c2 remain persistent, with their reference table load/unload unchanged.
Every row of reference Horner is executed once in both directions, in exactly
the original order. All temporary coefficients are toggled back to zero
before free. Requires official full-domain two-seed PASS for promotion.
"""
from __future__ import annotations
import argparse, ast, importlib, importlib.util, inspect, json, sys, textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def mod(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

k031=mod("k031",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=mod("k034",ROOT/"competition/k034/k034_row_local_scratch.py")
P=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=28)
K040_SCORE=1803994.6591350352

def patch_build(original):
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=="build_nr_circuit")
    assignments={name:[n for n in ast.walk(fn)
        if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
        for name in ("coefs","scratch")}
    if any(len(v)!=1 for v in assignments.values()):
        raise RuntimeError("Unexpected reference source allocation AST")
    assignments["coefs"][0].value=ast.parse(
        "[alloc(prec.coef_bits,'c0'),km.array([]),"
        "alloc(prec.coef_bits,'c2'),km.array([])]",mode="eval").body
    assignments["scratch"][0].value=ast.parse("km.array([])",mode="eval").body
    loops=0
    for n in ast.walk(fn):
        if not isinstance(n,ast.For) or not isinstance(n.target,ast.Name) or n.target.id!="reg":
            continue
        if not isinstance(n.iter,ast.Tuple):continue
        for i,e in enumerate(n.iter.elts):
            if (isinstance(e,ast.Starred) and isinstance(e.value,ast.Name)
                and e.value.id=="coefs"):
                n.iter.elts[i]=ast.Starred(value=ast.Tuple(elts=[
                    ast.Subscript(value=ast.Name(id="coefs",ctx=ast.Load()),
                                  slice=ast.Constant(value=j),ctx=ast.Load())
                    for j in (0,2)],ctx=ast.Load()),ctx=ast.Load())
                loops+=1
    if loops!=1:raise RuntimeError("Expected one final free loop")
    ast.fix_missing_locations(tree)
    g=original.__globals__
    exec(compile(tree,"<K042_build>","exec"),g,g)
    return g["build_nr_circuit"]

def hooks(ref,stage):
    def toggle(builder,prec,x,selectors,reg,j):
        top,t_a,t_b=x[-1],selectors[0],selectors[1]
        tab=prec.coefficient_table()
        for ctl,val in ((True,tab[0][j]),
                        (top,tab[0][j]^tab[2][j]),
                        (t_a,tab[0][j]^tab[1][j]),
                        (t_b,tab[2][j]^tab[3][j])):
            builder.gf2_iadd(val,target=reg,control=ctl)
    def open_j(builder,prec,x,selectors,coefs,j):
        if len(coefs[j]):raise RuntimeError(f"c{j} already open")
        coefs[j]=builder.alloc_qubits(prec.coef_bits)
        toggle(builder,prec,x,selectors,coefs[j],j)
        stage["open"].append(j)
    def close_j(builder,prec,x,selectors,coefs,j):
        if len(coefs[j])!=prec.coef_bits:
            raise RuntimeError(f"c{j} missing before cleanup")
        toggle(builder,prec,x,selectors,coefs[j],j)
        builder.free(coefs[j])
        coefs[j]=km.array([])
        stage["close"].append(j)
    def loader(builder,prec,x,selectors,coefs):
        for j in (0,2):toggle(builder,prec,x,selectors,coefs[j],j)
        stage["load"]+=1
    def horner(builder,inverse,prec,x,selectors,coefs,scratch):
        width,wc=len(x),prec.coef_bits
        delta=[(selectors[2],1)]
        delta += [(x[width-2-m],m)
                  for m in range(2,min(prec.delta_bits,width-2)+1)]
        steps=((0,1),(1,2),(2,3)) if inverse else ((2,3),(1,2),(0,1))
        with builder.mark("horner"):
            marker=builder.mark("horner_step")
            for acc,mult in steps:
                # c1 and c3 never overlap in allocated lifetime.
                if not inverse:
                    if acc==2:open_j(builder,prec,x,selectors,coefs,3)
                    if acc==1:open_j(builder,prec,x,selectors,coefs,1)
                else:
                    if acc==2:open_j(builder,prec,x,selectors,coefs,3)
                with marker:
                    for ctl,m in delta:
                        ref._add_row(builder,inverse,ctl,
                            [(coefs[mult][i],i-m) for i in range(m,wc)],
                            coefs[acc],scratch,subtract=True)
                if not inverse and acc==2:
                    close_j(builder,prec,x,selectors,coefs,3)
                if inverse and acc==1:
                    close_j(builder,prec,x,selectors,coefs,1)
                if inverse and acc==2:
                    close_j(builder,prec,x,selectors,coefs,3)
        stage["horner"]+=1
    return loader,horner

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k042/results"))
    ap.add_argument("--timeout",type=int,default=300)
    ap.add_argument("--prefix",type=int,default=64)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    original=(ref.build_nr_circuit,ref._add_row,ref._load_coefficients,ref._horner)
    control=ROOT/"competition/k040/results/recycle.kmb"
    if not control.is_file():raise SystemExit("K040 verified control missing")
    baseline=k031.verify(control,a.prefix,12345,a.timeout)
    if baseline.get("status")!="PASS" or baseline.get("exit_code")!=0:
        raise SystemExit("K040 control prefix failed")
    stats={"open":[],"close":[],"load":0,"horner":0}
    file=out/"c1_c3_nonoverlap.kmb"
    try:
        ref._add_row=k034.local_row("compact",{"rows":0,"allocated_sum":0,"max_row_width":0})
        ref._load_coefficients,ref._horner=hooks(ref,stats)
        ref.build_nr_circuit=patch_build(original[0])
        build=k031.build(ref,P,1,file)
        if (stats["open"],stats["close"],stats["load"],stats["horner"])!=(
            [3,1,3],[3,1,3],2,2):
            raise AssertionError("Unexpected lifecycle "+repr(stats))
    except Exception as ex:
        error={"status":"BUILD_ERROR","reason":repr(ex),"stats":stats}
        (out/"result.json").write_text(json.dumps(error,indent=2))
        print("K042_RESULT",json.dumps(error),flush=True)
        return
    finally:
        ref.build_nr_circuit,ref._add_row,ref._load_coefficients,ref._horner=original
    screen=k031.verify(file,a.prefix,12345,a.timeout)
    eligible=(screen.get("status")=="PASS" and screen.get("exit_code")==0
              and screen.get("score",1e99)<baseline["score"]-1e-7)
    print("K042_SCREEN",json.dumps({"num_qubits":build["num_qubits"],
        "candidate_score":screen.get("score"),
        "control_score":baseline["score"],"status":screen.get("status"),
        "error":screen.get("error"),"full_domain_eligible":eligible,
        "lifecycle":stats},sort_keys=True),flush=True)
    first=k031.verify(file,k031.FULL_X,12345,a.timeout) if eligible else None
    good=bool(first and first.get("status")=="PASS" and first.get("exit_code")==0)
    second=k031.verify(file,k031.FULL_X,23456,a.timeout) if good else None
    valid=bool(second and second.get("status")=="PASS" and second.get("exit_code")==0)
    result={"status":"PASS_FULL" if valid else "NOT_PROMOTED",
            "build":build,"stats":stats,"screen":screen,
            "full_seed_12345":first,"full_seed_23456":second,
            "candidate":str(file)}
    if valid:
        result["score"]=first["score"]
        result["delta_vs_k040"]=first["score"]-K040_SCORE
    (out/"result.json").write_text(json.dumps(result,indent=2))
    print("K042_RESULT",json.dumps({"status":result["status"],
        "num_qubits":build["num_qubits"],"score":result.get("score"),
        "delta":result.get("delta_vs_k040")},sort_keys=True),flush=True)
    print("SAVED",out/"result.json",flush=True)

if __name__=="__main__":main()
