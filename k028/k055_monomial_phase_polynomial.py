#!/usr/bin/env python3
"""K055 — Boolean monomial polynomial phase oracle (REAL Kickmix circuit).

This is a circuit-level alternative to K053's dense Walsh representation:
    f(x) = sum_{nonzero bit masks S} a[S] * product_{j in S} x[j].
The a[S] are the subset Möbius transform of the K051 integer-Horner
phase table, not arbitrary decimal fits. Every monomial is a reversible
AND chain -> Z_POW(2*a) -> inverse AND chain, with all ancillas freed.

A greedy full bounded-domain numerical check removes small monomials while
preserving error < --margin times the official tolerance at ALL x in range.
Then the untouched official verifier checks the actual circuit, including
Z_POW quantization, x preservation and scratch cleanup.

No claim this implements the intended *arithmetic* Horner evaluator or the
full 22-bit domain. The goal is to test whether polynomial basis sparsity
gives a cheaper, physically valid bounded oracle than K053.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,sys
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km
def load(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
k031=load("k031_k055",ROOT/"competition/k031/k031_full_domain_repair.py")
k053=load("k053_k055",ROOT/"competition/k053/k053_walsh_direct_phase.py")
def coefficients(bits):
    values=np.array(k053.phase_lookup(bits),dtype=np.float64)
    a=values.copy()
    n=1<<bits
    # In-place Boolean subset Möbius transform.
    for bit in range(bits):
        stride=1<<bit
        for mask in range(n):
            if mask&stride:
                a[mask]-=a[mask^stride]
    return a,values
def prune(bits,margin):
    co,values=coefficients(bits)
    xs=np.arange(1,1<<bits,dtype=np.int64)
    tol=2**-24/np.sqrt(xs.astype(np.float64))
    expected=1/np.sqrt(xs.astype(np.float64))
    reconstructed=np.zeros(xs.size,dtype=np.float64)
    # Reconstruct the polynomial and establish the floating error floor.
    for mask in range(1,len(co)):
        reconstructed+=co[mask]*((xs&mask)==mask)
    residual=reconstructed-expected
    baseline=float(np.max(np.abs(residual)/tol))
    selected=np.ones(len(co),dtype=np.bool_)
    selected[0]=False
    removed=[]
    for mask in sorted(range(1,len(co)),key=lambda i:abs(co[i])):
        membership=(xs&mask)==mask
        candidate=residual-co[mask]*membership
        if np.max(np.abs(candidate)/tol)<margin:
            residual=candidate
            selected[mask]=False
            removed.append(mask)
    kept=[(i,float(co[i])) for i in range(1,len(co)) if selected[i]]
    summary={"all_terms":len(co)-1,"kept_terms":len(kept),
             "removed_terms":len(removed),
             "max_error_original":baseline,
             "max_error_pruned":float(np.max(np.abs(residual)/tol)),
             "relative_margin":margin,
             "order_distribution":{str(k):sum(m.bit_count()==k for m,_ in kept)
                                   for k in range(1,bits+1)}}
    return kept,summary
def compile_terms(bits,terms,path):
    builder=km.CircuitBuilder()
    x=builder.create_quantum_register(22,name="x")
    # Reusable explicit AND-chain workspace; never infer circuit cost.
    workspace=builder.alloc_qubits(bits-1)
    and_count=0
    rotations=0
    for mask,coef in terms:
        active=[i for i in range(bits) if mask>>i&1]
        for k in range(1,len(active)):
            ctl=x[active[0]] if k==1 else workspace[k-2]
            builder.init_and(ctl,km.array([x[active[k]]]),
                             km.array([workspace[k-1]]))
            and_count+=1
        target=x[active[0]] if len(active)==1 else workspace[len(active)-2]
        exponent=Fraction(round(2*coef*(1<<52)),1<<52)
        if exponent:
            builder.z_pow(target,exponent)
            rotations+=1
        for k in range(len(active)-1,0,-1):
            ctl=x[active[0]] if k==1 else workspace[k-2]
            builder.del_and(ctl,km.array([x[active[k]]]),
                            km.array([workspace[k-1]]))
    builder.free(workspace)
    circuit=builder.finish_circuit()
    circuit.to_file(str(path),format="kmb")
    return {"num_qubits":circuit.num_qubits,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes":path.stat().st_size,"rotations_requested":rotations,
            "and_chains":and_count,"terms":len(terms)}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bits",nargs="+",type=int,default=[8,10])
    ap.add_argument("--margin",type=float,default=0.85)
    ap.add_argument("--timeout",type=int,default=300)
    ap.add_argument("--out",type=Path,default=ROOT/"competition/k055/results")
    args=ap.parse_args()
    if not 0<args.margin<1:raise SystemExit("Invalid --margin")
    args.out.mkdir(parents=True,exist_ok=True)
    report=[]
    for bits in args.bits:
        if not 2<=bits<=10:raise SystemExit("Bits must be 2..10")
        case={"bits":bits}
        try:
            terms,stats=prune(bits,args.margin)
            case["prune"]=stats
            print("K055_PRUNE",json.dumps({"bits":bits,**stats},sort_keys=True),flush=True)
            candidate=args.out/f"monomial_{bits}bit.kmb"
            built=compile_terms(bits,terms,candidate)
            case["build"]=built
            verified=k031.verify(candidate,(1<<bits)-1,12345,args.timeout)
            case["official"]=verified
            case["status"]="PASS_BOUNDED" if verified.get("status")=="PASS" and verified.get("exit_code")==0 else "FAIL_BOUNDED"
            # Ground comparison in a freshly generated and checked K053 circuit.
            control=args.out/f"walsh_{bits}bit.kmb"
            walsh_build=k053.build(bits,0.0,control)
            walsh_verify=k031.verify(control,(1<<bits)-1,12345,args.timeout)
            case["walsh"]={"build":walsh_build,"official":walsh_verify}
            if case["status"]=="PASS_BOUNDED" and walsh_verify.get("status")=="PASS" and walsh_verify.get("exit_code")==0:
                case["score_delta_vs_walsh"]=verified["score"]-walsh_verify["score"]
            print("K055_COMPARE",json.dumps({
                "bits":bits,"status":case["status"],
                "polynomial_qubits":built["num_qubits"],
                "polynomial_rotations":verified.get("rotation_count"),
                "polynomial_toffolis":verified.get("toffoli_count"),
                "polynomial_score":verified.get("score"),
                "walsh_score":walsh_verify.get("score"),
                "score_delta":case.get("score_delta_vs_walsh"),
                "error":verified.get("error")},sort_keys=True),flush=True)
        except Exception as ex:
            case["status"]="ERROR";case["error"]=repr(ex)
            print("K055_ERROR",json.dumps(case,sort_keys=True),flush=True)
        report.append(case)
    (args.out/"result.json").write_text(json.dumps({
        "status":"BOUNDED_MONOMIAL_POLYNOMIAL_EXPERIMENT",
        "full_domain_verified":False,"cases":report},indent=2,default=str))
    print("K055_RESULT",json.dumps([{"bits":r["bits"],"status":r["status"],
        "kept":r.get("prune",{}).get("kept_terms"),
        "score":r.get("official",{}).get("score"),
        "delta_vs_walsh":r.get("score_delta_vs_walsh")}
        for r in report],sort_keys=True),flush=True)
    print("SAVED",args.out/"result.json",flush=True)
if __name__=="__main__":main()
