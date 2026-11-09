#!/usr/bin/env python3
"""K054: prune Walsh parity rotations under a full bounded-domain error test.

Uses the independently verified K053 Walsh circuit architecture. Removes
lowest-absolute-amplitude parity rotations greedily, but ONLY when the
resulting direct-phase error stays under a configurable fraction of the
official per-x tolerance for *every* x in the bounded domain. Rebuilds
full and sparse circuits, verifies both using the unmodified official
verifier, and compares actual scores. Not a 22-bit full-domain solution.

The K051 offline fit is evaluated in integer Horner arithmetic by K052.
Greedy screen uses float64 and direct phase errors; circuit verifies
the actual quantized phase rotations and ancilla/input contract.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,sys
from fractions import Fraction
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"competition/k001/private/official/verifiers"))
import kickmix as km

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj

k031=load("k031_k054",ROOT/"competition/k031/k031_full_domain_repair.py")
k053=load("k053_k054",ROOT/"competition/k053/k053_walsh_direct_phase.py")

def parity(mask,x):
    z=np.bitwise_and(x,mask)
    z=np.bitwise_xor(z,z >> 8)
    z=np.bitwise_xor(z,z >> 4)
    z=np.bitwise_xor(z,z >> 2)
    z=np.bitwise_xor(z,z >> 1)
    return np.bitwise_and(z,1).astype(np.float64)

def coefficients(bits):
    table=k053.phase_lookup(bits)
    transform=k053.fht(table)
    return [(mask,-2.0*transform[mask]/(1<<bits))
            for mask in range(1,1<<bits)],table

def select_terms(bits,margin):
    terms,table=coefficients(bits)
    xs=np.arange(1,1<<bits,dtype=np.int64)
    tolerance=(2.0**-24)/np.sqrt(xs.astype(np.float64))
    truth=1.0/np.sqrt(xs.astype(np.float64))
    # Full set is mathematically equivalent to K053, with f(0)=0.
    current=np.array(table[1:],dtype=np.float64)-truth
    selected={mask for mask,_ in terms}
    baseline=float(np.max(np.abs(current)/tolerance))
    dropped=[]
    for mask,alpha in sorted(terms,key=lambda item:abs(item[1])):
        vector=parity(mask,xs)
        candidate=current-alpha*vector
        risk=float(np.max(np.abs(candidate)/tolerance))
        if risk <= margin:
            current=candidate
            selected.remove(mask)
            dropped.append(mask)
    retained=[(mask,alpha) for mask,alpha in terms if mask in selected]
    return retained,{"original_terms":len(terms),"retained":len(retained),
                     "removed":len(dropped),"baseline_max_error_over_tolerance":baseline,
                     "pruned_max_error_over_tolerance":
                        float(np.max(np.abs(current)/tolerance)),
                     "margin":margin,
                     "retained_coefficient_l1":sum(abs(a) for _,a in retained),
                     "removed_coefficient_l1":sum(abs(a) for m,a in terms if m not in selected)}

def compile_circuit(bits,terms,path):
    builder=km.CircuitBuilder()
    x=builder.create_quantum_register(22,name="x")
    cnot=0
    rotations=0
    for mask,alpha in terms:
        active=[j for j in range(bits) if (mask>>j)&1]
        anchor=active[-1]
        others=active[:-1]
        for j in others:
            builder.cx(x[j],x[anchor])
            cnot+=1
        exponent=Fraction(round((2*alpha)*(1<<52)),1<<52)
        if exponent:
            builder.z_pow(x[anchor],exponent)
            rotations+=1
        for j in reversed(others):
            builder.cx(x[j],x[anchor])
            cnot+=1
    circ=builder.finish_circuit()
    circ.to_file(str(path),format="kmb")
    return {"num_qubits":circ.num_qubits,"rotations":rotations,
            "cnot":cnot,"bytes":path.stat().st_size,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--bits",type=int,nargs="+",default=[8,10])
    pa.add_argument("--margin",type=float,default=0.85)
    pa.add_argument("--timeout",type=int,default=300)
    pa.add_argument("--out",type=Path,
                    default=ROOT/"competition/k054/results")
    args=pa.parse_args()
    if not 0<args.margin<1:raise SystemExit("--margin must be in (0,1)")
    args.out.mkdir(parents=True,exist_ok=True)
    result=[]
    for bits in args.bits:
        if bits<2 or bits>10:
            raise SystemExit("K054 supports bounded test bits 2..10")
        all_terms,_=coefficients(bits)
        kept,screen=select_terms(bits,args.margin)
        row={"bits":bits,"numerical":screen}
        print("K054_PRUNE",json.dumps(row,sort_keys=True),flush=True)
        for mode,terms in (("full",all_terms),("sparse",kept)):
            target=args.out/f"{mode}_{bits}bit.kmb"
            try:
                build=compile_circuit(bits,terms,target)
                verify=k031.verify(target,(1<<bits)-1,12345,args.timeout)
                row[mode]={"build":build,"verification":verify,
                           "status":"PASS_BOUNDED" if (
                               verify.get("status")=="PASS" and verify.get("exit_code")==0
                           ) else "FAIL_BOUNDED"}
            except Exception as exc:
                row[mode]={"status":"ERROR","error":repr(exc)}
            print("K054_VERIFY",json.dumps({
                "bits":bits,"mode":mode,
                "status":row[mode]["status"],
                "qubits":row[mode].get("build",{}).get("num_qubits"),
                "rotations":row[mode].get("build",{}).get("rotations"),
                "score":row[mode].get("verification",{}).get("score"),
                "error":row[mode].get("verification",{}).get("error",
                        row[mode].get("error"))},sort_keys=True),flush=True)
        if (row["full"]["status"]=="PASS_BOUNDED"
            and row["sparse"]["status"]=="PASS_BOUNDED"):
            row["score_delta"]=(
                row["sparse"]["verification"]["score"]-
                row["full"]["verification"]["score"])
            row["better"]=row["score_delta"]<0
        result.append(row)
    (args.out/"result.json").write_text(json.dumps({
        "status":"K054_BOUNDED_WALSH_SPECTRAL_PRUNING",
        "warning":"No full-domain verification; no scalable synthesis claimed",
        "results":result},indent=2))
    print("K054_RESULT",json.dumps([{
        "bits":r["bits"],"removed":r["numerical"]["removed"],
        "full_score":r.get("full",{}).get("verification",{}).get("score"),
        "sparse_score":r.get("sparse",{}).get("verification",{}).get("score"),
        "score_delta":r.get("score_delta"),
        "improves":r.get("better",False)}
        for r in result],sort_keys=True),flush=True)
    print("SAVED",args.out/"result.json",flush=True)

if __name__=="__main__":main()
