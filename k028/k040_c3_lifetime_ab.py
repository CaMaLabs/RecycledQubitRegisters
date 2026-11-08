#!/usr/bin/env python3
"""K040: isolate K039 cleanup failure using only c3 coefficient lifetime.

Modes:
  late_keep: allocate/load c3 just before forward Horner; keep until original
             final inverse coefficient unload, then free once.
  recycle:   allocate/load c3 before each Horner, clean/free after each.
Both retain exact reference Horner rows and K034 row-local AND workspace.
Score and official validity are required before promotion.
"""
from __future__ import annotations
import argparse,ast,importlib,importlib.util,inspect,json,sys,textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def module(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
k031=module("k031",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=module("k034",ROOT/"competition/k034/k034_row_local_scratch.py")
PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=28)
CONTROL=1933697.432675161

def patch_build(original):
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)
            and n.name=="build_nr_circuit")
    matches=[n for n in ast.walk(fn) if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id=="coefs" for t in n.targets)]
    if len(matches)!=1:raise AssertionError("Cannot isolate coefficient allocation")
    matches[0].value=ast.parse(
        "[alloc(prec.coef_bits, f'c{j}') for j in range(3)] + [km.array([])]",
        mode="eval").body
    for n in ast.walk(fn):
        if (isinstance(n,ast.For) and isinstance(n.target,ast.Name)
            and n.target.id=="reg" and isinstance(n.iter,ast.Tuple)
            and any(isinstance(e,ast.Starred)
                    and isinstance(e.value,ast.Name)
                    and e.value.id=="coefs" for e in n.iter.elts)):
            # c3 will have been freed inside the last loader, not at end.
            replacement=[]
            for e in n.iter.elts:
                if (isinstance(e,ast.Starred) and isinstance(e.value,ast.Name)
                    and e.value.id=="coefs"):
                    replacement.append(ast.Starred(value=ast.Subscript(
                        value=ast.Name(id="coefs",ctx=ast.Load()),
                        slice=ast.Slice(lower=None,upper=ast.Constant(value=3)),
                        ctx=ast.Load()),ctx=ast.Load()))
                else:replacement.append(e)
            n.iter.elts=replacement
    # Preserve K034's row-local scratch design.
    sm=[n for n in ast.walk(fn) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=="scratch" for t in n.targets)]
    if len(sm)!=1:raise AssertionError("Scratch allocation AST mismatch")
    sm[0].value=ast.parse("km.array([])",mode="eval").body
    ast.fix_missing_locations(tree)
    globals_=original.__globals__
    exec(compile(tree,"<K040_build>","exec"),globals_,globals_)
    return globals_["build_nr_circuit"]

def hooks(ref,mode,stats):
    old_horner=ref._horner
    old_load=ref._load_coefficients
    def toggle(builder,prec,x,selectors,reg,j):
        top,t_a,t_b=x[len(x)-1],selectors[0],selectors[1]
        tab=prec.coefficient_table()
        for ctl,value in ((True,tab[0][j]),
                         (top,tab[0][j]^tab[2][j]),
                         (t_a,tab[0][j]^tab[1][j]),
                         (t_b,tab[2][j]^tab[3][j])):
            builder.gf2_iadd(value,target=reg,control=ctl)
    def open_c3(builder,prec,x,selectors,coefs):
        assert len(coefs[3])==0
        coefs[3]=builder.alloc_qubits(prec.coef_bits)
        toggle(builder,prec,x,selectors,coefs[3],3)
        stats["open"]+=1
    def close_c3(builder,prec,x,selectors,coefs):
        assert len(coefs[3])==prec.coef_bits
        toggle(builder,prec,x,selectors,coefs[3],3)
        builder.free(coefs[3])
        coefs[3]=km.array([])
        stats["close"]+=1
    def loader(builder,prec,x,selectors,coefs):
        # Initially load c0/c1/c2 as in reference, and unload after reverse.
        for j in range(3):
            toggle(builder,prec,x,selectors,coefs[j],j)
        stats["loader"]+=1
        if mode=="late_keep" and stats["loader"]==2:
            # Cleanup c3 after reverse Horner, ahead of final register frees.
            close_c3(builder,prec,x,selectors,coefs)
    def horner(builder,inverse,prec,x,selectors,coefs,scratch):
        if not inverse or mode=="recycle":open_c3(builder,prec,x,selectors,coefs)
        old_horner(builder,inverse,prec,x,selectors,coefs,scratch)
        if mode=="recycle":close_c3(builder,prec,x,selectors,coefs)
        stats["horner"]+=1
    return loader,horner

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k040/results"))
    ap.add_argument("--timeout",type=int,default=300)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    original_build=ref.build_nr_circuit;original_load=ref._load_coefficients
    original_horner=ref._horner;original_row=ref._add_row
    control=ROOT/"competition/k034/results/row_local_full.kmb"
    baseline=k031.verify(control,64,12345,a.timeout)
    if baseline.get("status")!="PASS":raise RuntimeError("K034 control failed")
    results=[]
    for mode in ("late_keep","recycle"):
        stats={"open":0,"close":0,"loader":0,"horner":0}
        file=out/f"{mode}.kmb"
        try:
            ref._add_row=k034.local_row("compact",
                {"rows":0,"allocated_sum":0,"max_row_width":0})
            ref._load_coefficients,ref._horner=hooks(ref,mode,stats)
            ref.build_nr_circuit=patch_build(original_build)
            build=k031.build(ref,PREC,1,file)
            screen=k031.verify(file,64,12345,a.timeout)
            eligible=(screen.get("status")=="PASS" and screen.get("exit_code")==0
                      and screen["score"]<baseline["score"]-1e-8)
            first=k031.verify(file,k031.FULL_X,12345,a.timeout) if eligible else None
            second=(k031.verify(file,k031.FULL_X,23456,a.timeout)
                    if first and first.get("status")=="PASS"
                    and first.get("exit_code")==0 else None)
            full=bool(second and second.get("status")=="PASS"
                      and second.get("exit_code")==0)
            row={"mode":mode,"stats":stats,"build":build,"screen":screen,
                 "full_first":first,"full_second":second,
                 "status":"PASS_FULL" if full else "NOT_VERIFIED"}
            if full:row["score"]=first["score"];row["delta"]=row["score"]-CONTROL
        except Exception as ex:
            row={"mode":mode,"stats":stats,"status":"BUILD_ERROR","error":repr(ex)}
        finally:
            ref.build_nr_circuit=original_build
            ref._load_coefficients=original_load
            ref._horner=original_horner
            ref._add_row=original_row
        results.append(row)
        print("K040",json.dumps(row,sort_keys=True,default=str),flush=True)
    (out/"results.json").write_text(json.dumps(results,indent=2,default=str))
    print("SAVED",out/"results.json",flush=True)

if __name__=="__main__":main()
