#!/usr/bin/env python3
"""K041 — c2 checkpoint/recompute A/B on full-domain K040 c3-recycling control.

Test whether temporary uncompute/recompute of modified c2 can save *net*
resources. c2 is restored by EXACT inverse Horner c2 rows (using c3) before
clean free, then reconstructed before inverse Horner. Never XOR-unload an
arithmetic-modified coefficient. No change to official verifier or score.

Promote only if the official full-domain verifier PASSes for BOTH seeds and
the score strictly beats K040's verified winner.
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

def from_file(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m

k031=from_file("k031",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=from_file("k034",ROOT/"competition/k034/k034_row_local_scratch.py")
k040=from_file("k040",ROOT/"competition/k040/k040_c3_lifetime_ab.py")

PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,
          result_bits=28,square_bits=28)
BASE_SCORE=1803994.6591350352

def patch_build_c2(original):
    """Keep c0,c1 persistent; c2,c3 are clean, dynamically allocated."""
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=="build_nr_circuit")
    coefs=[n for n in ast.walk(fn)
           if isinstance(n,ast.Assign) and any(
               isinstance(t,ast.Name) and t.id=="coefs" for t in n.targets)]
    if len(coefs)!=1:raise AssertionError("Coefficient AST mismatch")
    coefs[0].value=ast.parse(
        "[alloc(prec.coef_bits,f'c{j}') for j in range(2)] + "
        "[km.array([]),km.array([])]",mode="eval").body
    scratch=[n for n in ast.walk(fn)
             if isinstance(n,ast.Assign) and any(
                 isinstance(t,ast.Name) and t.id=="scratch" for t in n.targets)]
    if len(scratch)!=1:raise AssertionError("Scratch AST mismatch")
    scratch[0].value=ast.parse("km.array([])",mode="eval").body
    endloops=0
    for n in ast.walk(fn):
        if (isinstance(n,ast.For) and isinstance(n.target,ast.Name)
            and n.target.id=="reg" and isinstance(n.iter,ast.Tuple)
            and any(isinstance(e,ast.Starred) and isinstance(e.value,ast.Name)
                    and e.value.id=="coefs" for e in n.iter.elts)):
            endloops+=1
            n.iter.elts=[
                ast.Starred(value=ast.Subscript(
                    value=ast.Name(id="coefs",ctx=ast.Load()),
                    slice=ast.Slice(lower=None,upper=ast.Constant(value=2)),
                    ctx=ast.Load()),ctx=ast.Load())
                if isinstance(e,ast.Starred) and isinstance(e.value,ast.Name)
                     and e.value.id=="coefs" else e for e in n.iter.elts]
    if endloops!=1:raise AssertionError("Final coefficient free loop mismatch")
    ast.fix_missing_locations(tree)
    g=original.__globals__
    exec(compile(tree,"<K041_build>","exec"),g,g)
    return g["build_nr_circuit"]

def hooks(ref,counts):
    old_horner=ref._horner
    table=PREC
    def toggle(builder,prec,x,selectors,reg,j):
        top,t_a,t_b=x[len(x)-1],selectors[0],selectors[1]
        vals=prec.coefficient_table()
        for ctl,v in ((True,vals[0][j]),
                      (top,vals[0][j]^vals[2][j]),
                      (t_a,vals[0][j]^vals[1][j]),
                      (t_b,vals[2][j]^vals[3][j])):
            builder.gf2_iadd(v,target=reg,control=ctl)
    def open_j(builder,prec,x,selectors,coefs,j):
        if len(coefs[j]):raise RuntimeError(f"c{j} already allocated")
        coefs[j]=builder.alloc_qubits(prec.coef_bits)
        toggle(builder,prec,x,selectors,coefs[j],j)
        counts[f"c{j}_open"]+=1
    def close_j(builder,prec,x,selectors,coefs,j):
        if len(coefs[j])!=prec.coef_bits:
            raise RuntimeError(f"c{j} not allocated")
        toggle(builder,prec,x,selectors,coefs[j],j)
        builder.free(coefs[j])
        coefs[j]=km.array([])
        counts[f"c{j}_close"]+=1
    def c2_rows(builder,inv,prec,x,selectors,coefs,scratch):
        """Exact c2 update from reference: c2 -= delta*c3."""
        width=len(x);wc=prec.coef_bits
        delta=[(selectors[2],1)]
        delta.extend((x[width-2-m],m) for m in
                     range(2,min(prec.delta_bits,width-2)+1))
        for control,m in delta:
            ref._add_row(builder,inv,control,
                [(coefs[3][i],i-m) for i in range(m,wc)],
                coefs[2],scratch,subtract=True)
        counts["c2_restore_rows" if inv else "c2_recompute_rows"]+=len(delta)
    def loader(builder,prec,x,selectors,coefs):
        for j in (0,1):
            toggle(builder,prec,x,selectors,coefs[j],j)
        counts["load_calls"]+=1
        if counts["load_calls"]==1:
            open_j(builder,prec,x,selectors,coefs,2)
    def horner(builder,inverse,prec,x,selectors,coefs,scratch):
        open_j(builder,prec,x,selectors,coefs,3)
        if inverse:
            # Restore the c2 value which existed after forward Horner,
            # so the reference inverse Horner's c1 and c0 undo matches.
            open_j(builder,prec,x,selectors,coefs,2)
            c2_rows(builder,False,prec,x,selectors,coefs,scratch)
        old_horner(builder,inverse,prec,x,selectors,coefs,scratch)
        if not inverse:
            # c2 has been modified by the first forward Horner step.
            # Undo THAT step before attempting to XOR-unload c2.
            c2_rows(builder,True,prec,x,selectors,coefs,scratch)
        close_j(builder,prec,x,selectors,coefs,2)
        close_j(builder,prec,x,selectors,coefs,3)
        counts["horner_calls"]+=1
    return loader,horner

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--out",default=str(ROOT/"competition/k041/results"))
    pa.add_argument("--timeout",type=int,default=300)
    pa.add_argument("--prefix",type=int,default=64)
    args=pa.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    orig=(ref.build_nr_circuit,ref._load_coefficients,ref._horner,ref._add_row)
    control=ROOT/"competition/k040/results/recycle.kmb"
    if not control.is_file():raise SystemExit("Missing validated K040 control: "+str(control))
    base=k031.verify(control,args.prefix,12345,args.timeout)
    if base.get("status")!="PASS" or base.get("exit_code")!=0:
        raise SystemExit("K040 control failed "+str(base))
    stats={k:0 for k in ("c2_open","c2_close","c3_open","c3_close",
                           "c2_restore_rows","c2_recompute_rows",
                           "load_calls","horner_calls")}
    path=out/"c2_checkpoint.kmb"
    try:
        ref._add_row=k034.local_row("compact",{
            "rows":0,"allocated_sum":0,"max_row_width":0})
        ref._load_coefficients,ref._horner=hooks(ref,stats)
        ref.build_nr_circuit=patch_build_c2(orig[0])
        build=k031.build(ref,PREC,1,path)
        # Counts are an exact-build sanity contract before score tests.
        if (stats["c2_open"],stats["c2_close"],
            stats["c3_open"],stats["c3_close"],
            stats["horner_calls"])!=(2,2,2,2,2):
            raise AssertionError("Unexpected coefficient lifecycle "+str(stats))
    except Exception as ex:
        report={"status":"BUILD_ERROR","error":repr(ex),"stats":stats}
        (out/"result.json").write_text(json.dumps(report,indent=2))
        print("K041",json.dumps(report),flush=True)
        return
    finally:
        ref.build_nr_circuit,ref._load_coefficients,ref._horner,ref._add_row=orig

    screen=k031.verify(path,args.prefix,12345,args.timeout)
    prefix_pass=screen.get("status")=="PASS" and screen.get("exit_code")==0
    cheaper=prefix_pass and screen["score"]<base["score"]-1e-7
    print("K041_SCREEN",json.dumps({
        "qubits":build["num_qubits"],"score":screen.get("score"),
        "base_prefix_score":base.get("score"),
        "status":screen.get("status"),"eligible_full":cheaper,"stats":stats
    },sort_keys=True),flush=True)
    first=k031.verify(path,k031.FULL_X,12345,args.timeout) if cheaper else None
    first_ok=bool(first and first.get("status")=="PASS"
                  and first.get("exit_code")==0)
    second=k031.verify(path,k031.FULL_X,23456,args.timeout) if first_ok else None
    valid=bool(second and second.get("status")=="PASS"
               and second.get("exit_code")==0)
    report={"status":"PASS_FULL" if valid else
            ("NOT_CHEAPER_PREFIX" if prefix_pass and not cheaper
             else "NOT_VERIFIED"),"candidate":str(path),"build":build,
            "stats":stats,"screen":screen,"full_first":first,"full_second":second}
    if valid:
        report["score"]=first["score"]
        report["delta_vs_K040"]=first["score"]-BASE_SCORE
    (out/"result.json").write_text(json.dumps(report,indent=2))
    print("K041_RESULT",json.dumps({
        "status":report["status"],"qubits":build["num_qubits"],
        "score":report.get("score"),"delta":report.get("delta_vs_K040"),
        "build_file":str(path)
    },sort_keys=True),flush=True)
    print("SAVED",out/"result.json",flush=True)

if __name__=="__main__":main()
