#!/usr/bin/env python3
"""K052: FIRST REAL reversible direct-phase prototype (bounded-domain).

Architecture: K051 quantized piecewise polynomial -> classical phase table
-> reversible input equality predicate -> Z_POW -> clean uncompute.

Unlike K049-K051, this produces an actual .kmb and runs the UNMODIFIED
official verifier. Only x=1..(2**--bits-1) is covered. It is intentionally
NOT a valid full-domain submission and should never replace K040.

The table-driven implementation validates phase units, approximation
precision, AND-predicate construction, input restoration, and clean scratch.
It is NOT the intended scalable implementation. K053 will replace per-x
minterms with shared exponent/region selection and polynomial arithmetic.
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

def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m
k031=mod("k031_k052",ROOT/"competition/k031/k031_full_domain_repair.py")
k051=mod("k051_k052",ROOT/"competition/k051/k051_integer_horner_screen.py")

def model_phase(x,coef,coef_bits,t_bits):
    # Integer-only input normalization; all coordinates are exact dyadics.
    exp=x.bit_length()-1
    regions=len(coef)
    # m=x/2**exp, region=floor(regions*(m-1)).
    region=min(regions-1,((x-(1<<exp))*regions)//(1<<exp))
    # t=2*(regions*(x/2**exp-1)-region)-1.
    tq_num=2*(regions*(x-(1<<exp))-region*(1<<exp))-(1<<exp)
    tq=(tq_num*(1<<t_bits))//(1<<exp)
    acc=int(coef[region][-1])
    for c in reversed(coef[region][:-1]):
        acc=int(c)+((acc*tq)>>t_bits)
    normalized=acc/(2.0**coef_bits)
    return math.ldexp(normalized,-(exp//2)) * (
        1/math.sqrt(2) if exp%2 else 1.0)

def predicate(builder,x,workspace,value,bits,phase):
    # Compute [x_low_bits == value]. The high x bits are not read,
    # so correctness is guaranteed ONLY for 1 <= x < 2**bits.
    low=[j for j in range(bits) if not ((value>>j)&1)]
    for j in low:builder.x(x[j])
    # A chain of AND ancillas implements a multi-controlled predicate.
    for j in range(1,bits):
        ctl=x[0] if j==1 else workspace[j-2]
        builder.init_and(ctl,km.array([x[j]]),km.array([workspace[j-1]]))
    builder.z_pow(workspace[bits-2],phase)
    for j in range(bits-1,0,-1):
        ctl=x[0] if j==1 else workspace[j-2]
        builder.del_and(ctl,km.array([x[j]]),km.array([workspace[j-1]]))
    for j in reversed(low):builder.x(x[j])

def build(bits,out):
    if bits<2 or bits>10:raise ValueError("Prototype supports 2..10 input bits")
    regions,degree,cb,tb=8,4,28,20
    coefs=k051.offline_coefficients(regions,degree,cb)
    b=km.CircuitBuilder()
    x=b.create_quantum_register(22,name="x")
    temp=b.alloc_qubits(bits-1)
    examples=[]
    for n in range(1,1<<bits):
        value=model_phase(n,coefs,cb,tb)
        phase=Fraction(round(value*(1<<48)),1<<48)
        predicate(b,x,temp,n,bits,phase)
        examples.append({"x":n,"modeled_turns":value,
                         "exact_turns":1/math.sqrt(n),
                         "phase_turns":float(phase),
                         "absolute_error_turns":abs(float(phase)-1/math.sqrt(n)),
                         "allowed_absolute_turns":2**-24/math.sqrt(n)})
    b.free(temp)
    circuit=b.finish_circuit()
    circuit.to_file(str(out),format="kmb")
    return {"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
            "num_qubits":circuit.num_qubits,
            "bytes":out.stat().st_size,
            "max_error_ratio":max(v["absolute_error_turns"]/
                                  v["allowed_absolute_turns"] for v in examples),
            "worst":max(examples,key=lambda v:v["absolute_error_turns"]/
                        v["allowed_absolute_turns"]),
            "sample":examples[:5],
            "scope":"ONLY x=1..2**bits-1; high x bits are not decoded"}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--bits",type=int,default=4)
    a.add_argument("--out",type=Path,default=ROOT/"competition/k052/results")
    a.add_argument("--timeout",type=int,default=300)
    args=a.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    path=args.out/f"direct_phase_{args.bits}bit.kmb"
    info=build(args.bits,path)
    print("K052_BUILD",json.dumps(info,sort_keys=True),flush=True)
    domain=(1<<args.bits)-1
    screen=k031.verify(path,domain,12345,args.timeout)
    print("K052_VERIFY",json.dumps(screen,sort_keys=True),flush=True)
    report={"status":"PASS_BOUNDED_DOMAIN" if screen.get("status")=="PASS"
            and screen.get("exit_code")==0 else "FAIL_BOUNDED_DOMAIN",
            "build":info,"verification":screen,"domain":[1,domain],
            "official_full_domain_verified":False,
            "warning":"This is only a bounded-domain predicate QROM proof of concept; NOT a competition submission"}
    (args.out/"result.json").write_text(json.dumps(report,indent=2,default=str))
    print("K052_RESULT",json.dumps({"status":report["status"],
        "qubits":info["num_qubits"],"score_bounded":screen.get("score"),
        "max_error_ratio_model":info["max_error_ratio"],
        "official_full_domain_verified":False},sort_keys=True),flush=True)
    print("SAVED",args.out/"result.json",flush=True)
if __name__=="__main__":main()
