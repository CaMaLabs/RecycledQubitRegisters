#!/usr/bin/env python3
"""K039: staged coefficient live-range recycling on K034 inverse sqrt.

No numerical approximations or changed coefficient table. Inverse row ordering\nexactly matches the reference. Original Horner rows
and original arithmetic remain intact; coefs are loaded just in time and
unloaded by the inverse sequence. Scratch remains K034 row-local, phase cut=1.

This is experimental: clean frees and the two-seed full-domain official
verifier are mandatory for any score claim.
"""
from __future__ import annotations
import argparse,ast,importlib,importlib.util,inspect,json,sys,textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj

k031=load("k031",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=load("k034",ROOT/"competition/k034/k034_row_local_scratch.py")
PREC=dict(coef_bits=17,delta_bits=12,product_bits=27,
          result_bits=28,square_bits=28)
BEST=1933697.432675161

def patched_compute_y1(original):
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)
            and x.name=="_compute_y1")
    first=next((i for i,x in enumerate(fn.body)
                if isinstance(x,ast.Assign)
                and any(isinstance(t,ast.Tuple) and any(isinstance(v,ast.Name) and v.id=="y0" for v in t.elts)
                        for t in x.targets)),None)
    if first is None:raise AssertionError("Cannot find y0,p prebinding")
    fn.body[first]=ast.parse("p = y1[:len(y1) - len(flags)]").body[0]
    class ResolveY0(ast.NodeTransformer):
        def visit_Name(self,node):
            if node.id=="y0" and isinstance(node.ctx,ast.Load):
                return ast.copy_location(ast.Subscript(
                    value=ast.Name(id="coefs",ctx=ast.Load()),
                    slice=ast.Constant(value=0),ctx=ast.Load()),node)
            return node
    tree=ResolveY0().visit(tree);ast.fix_missing_locations(tree)
    ns=original.__globals__
    # Bind to the live module dictionary to preserve K031 phase hooks.\n    exec(compile(tree,inspect.getsourcefile(original) or "<K039>","exec"),ns,ns)
    return ns["_compute_y1"]

def patched_build(original):
    tree=ast.parse(textwrap.dedent(inspect.getsource(original)))
    fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef)
            and x.name=="build_nr_circuit")
    class Replace(ast.NodeTransformer):
        def visit_Assign(self,node):
            if len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
                key=node.targets[0].id
                if key=="scratch":
                    return ast.copy_location(ast.parse("scratch = km.array([])").body[0],node)
                if key=="coefs":
                    return ast.copy_location(ast.parse(
                        "coefs = [km.array([]) for _ in range(4)]").body[0],node)
            return self.generic_visit(node)
        def visit_For(self,node):
            # Remove only the final extra frees, not the arithmetic loops.
            if (isinstance(node.target,ast.Name) and node.target.id=="reg"
                and isinstance(node.iter,ast.Tuple)
                and any(isinstance(v,ast.Starred) for v in node.iter.elts)):
                node.iter.elts=[v for v in node.iter.elts
                    if not (isinstance(v,ast.Starred)
                            and isinstance(v.value,ast.Name)
                            and v.value.id=="coefs")]
            return self.generic_visit(node)
    tree=Replace().visit(tree);ast.fix_missing_locations(tree)
    ns=original.__globals__
    exec(compile(tree,inspect.getsourcefile(original) or "<K039>","exec"),ns,ns)
    return ns["build_nr_circuit"]

def make_stage_hooks(ref,metrics):
    original_load=ref._load_coefficients
    original_horner=ref._horner
    def toggle_j(builder,prec,x,selectors,reg,j):
        top,t_a,t_b=x[len(x)-1],selectors[0],selectors[1]
        tab=prec.coefficient_table()
        for control,value in ((True,tab[0][j]),
            (top,tab[0][j]^tab[2][j]),
            (t_a,tab[0][j]^tab[1][j]),
            (t_b,tab[2][j]^tab[3][j])):
            builder.gf2_iadd(value,target=reg,control=control)
    def allocate_j(builder,prec,x,selectors,coefs,j):
        if len(coefs[j]):raise RuntimeError("Coefficient already live "+str(j))
        coefs[j]=builder.alloc_qubits(prec.coef_bits)
        toggle_j(builder,prec,x,selectors,coefs[j],j)
        metrics["allocated_coefficients"].append(j)
    def unload_j(builder,prec,x,selectors,coefs,j):
        if len(coefs[j])!=prec.coef_bits:
            raise RuntimeError("Coefficient not live "+str(j))
        toggle_j(builder,prec,x,selectors,coefs[j],j)
        builder.free(coefs[j])
        coefs[j]=km.array([])
        metrics["freed_coefficients"].append(j)
    def loader(builder,prec,x,selectors,coefs):
        # Forward load occurs before Horner; reverse load occurs after inverse
        # Horner. The Horner hook performs all exact coeff load/unload steps.
        # This hook is intentionally a no-op.
        metrics["loader_calls"]+=1
    def horner(builder,inverse,prec,x,selectors,coefs,scratch):
        width,wc=len(x),prec.coef_bits
        delta=[(selectors[2],1)]
        delta.extend((x[width-2-m],m)
                     for m in range(2,min(prec.delta_bits,width-2)+1))
        if not inverse:
            # Work from upper polynomial coefficient downwards. c3 can be
            # cleaned before allocating c1 and c0; peak coeffs = 2.
            allocate_j(builder,prec,x,selectors,coefs,3)
            allocate_j(builder,prec,x,selectors,coefs,2)
            steps=[(2,3),(1,2),(0,1)]
        else:
            # Reverse the Horner update. At this point c0,c1,c2 are live,
            # and c3 is clean/unallocated. c0 and c1 become their original
            # table values as soon as their inverse row completes.
            steps=[(0,1),(1,2),(2,3)]
        with builder.mark("horner"):
            with builder.mark("horner_step"):
                # This mark wraps all steps, unlike the reference's separate
                # stage markers; arithmetic operations are unchanged.
                for acc,mult in steps:
                    if not inverse and acc in (1,0):
                        allocate_j(builder,prec,x,selectors,coefs,acc)
                    if inverse and acc==2:
                        allocate_j(builder,prec,x,selectors,coefs,3)
                    # Match the reference: inverse reverses the Horner stages,
                    # NOT the order of delta-controlled rows within a stage.
                    for control,m in delta:
                        original_row=ref._add_row
                        original_row(builder,inverse,control,
                            [(coefs[mult][i],i-m) for i in range(m,wc)],
                            coefs[acc],scratch,subtract=True)
                    if not inverse and acc==2:
                        unload_j(builder,prec,x,selectors,coefs,3)
                    elif inverse:
                        unload_j(builder,prec,x,selectors,coefs,acc)
                if inverse:
                    unload_j(builder,prec,x,selectors,coefs,3)
    return loader,horner

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default=str(ROOT/"competition/k039/results"))
    ap.add_argument("--prefix",type=int,default=64)
    ap.add_argument("--timeout",type=int,default=300)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    old_build=ref.build_nr_circuit
    old_row=ref._add_row
    old_compute=ref._compute_y1
    old_load=ref._load_coefficients
    old_horner=ref._horner
    baseline=ROOT/"competition/k034/results/row_local_full.kmb"
    if not baseline.exists():raise SystemExit("Missing K034 baseline")
    base_screen=k031.verify(baseline,args.prefix,12345,args.timeout)
    if base_screen.get("status")!="PASS":raise SystemExit("K034 control failed")
    metrics={"allocated_coefficients":[],"freed_coefficients":[],"loader_calls":0}
    path=out/"staged_coeffs.kmb"
    try:
        # Dynamic compiled functions use a copied global namespace. Install
        # hooks BEFORE compiling each dependent function, so compiled globals
        # point to the stage-aware implementations rather than the original.
        ref._add_row=k034.local_row("compact",{"rows":0,"allocated_sum":0,"max_row_width":0})
        ref._load_coefficients,ref._horner=make_stage_hooks(ref,metrics)
        ref._compute_y1=patched_compute_y1(old_compute)
        ref.build_nr_circuit=patched_build(old_build)
        circuit=k031.build(ref,PREC,1,path)
    except Exception as e:
        (out/"error.json").write_text(json.dumps({"error":repr(e),"metrics":metrics},indent=2))
        raise
    finally:
        ref.build_nr_circuit=old_build
        ref._compute_y1=old_compute
        ref._add_row=old_row
        ref._load_coefficients=old_load
        ref._horner=old_horner
    screen=k031.verify(path,args.prefix,12345,args.timeout)
    print("SCREEN",json.dumps({"build":circuit,"metrics":metrics,
        "result":screen,"control_score":base_screen.get("score")},default=str),flush=True)
    cheaper=(screen.get("status")=="PASS" and screen.get("exit_code")==0
             and screen["score"]<base_screen["score"])
    first=k031.verify(path,k031.FULL_X,12345,args.timeout) if cheaper else None
    one=bool(first and first.get("status")=="PASS" and first.get("exit_code")==0)
    second=k031.verify(path,k031.FULL_X,23456,args.timeout) if one else None
    valid=bool(one and second and second.get("status")=="PASS" and second.get("exit_code")==0)
    report={"status":"PASS_FULL" if valid else "NO_VERIFIED_IMPROVEMENT",
        "candidate":str(path),"build":circuit,"metrics":metrics,
        "screen":screen,"full_seed_12345":first,"full_seed_23456":second}
    if valid:report["score"]=first["score"];report["delta_vs_K034"]=first["score"]-BEST
    (out/"result.json").write_text(json.dumps(report,indent=2,default=str))
    print("K039_RESULT",json.dumps({"status":report["status"],
        "score":report.get("score"),"delta":report.get("delta_vs_K034"),
        "qubits":circuit["num_qubits"]}),flush=True)
    print("SAVED",out/"result.json",flush=True)
if __name__=="__main__":main()
