#!/usr/bin/env python3
"""K150: mixed-precision, full-domain Newton feasibility + reversible resource gates.
This is NOT a synthesized reversible multiplier or an official Kickmix verification.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np

PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
N=3133452
EPS=2.0**-24
BASE_Q=62
BASE_SCORE=95369.00696815242

def seeds(q,bins):
    a=np.arange(bins,dtype=float)
    mids=np.r_[1+(a+.5)/bins,2+2*(a+.5)/bins]
    return np.rint((1<<q)/np.sqrt(mids)).astype(np.int64)

def newton(y,m,q):
    scale=np.int64(1<<q)
    square=(y*y+scale//2)//scale
    product=(m*square+scale//2)//scale
    return (y*(3*scale-product)+scale)//(2*scale)

def one_case(q1,q2,bins,max_x,chunk):
    if q2<q1:raise ValueError("q2 must be >=q1")
    lut=seeds(q1,bins)
    max1=max2=0
    worst=0.
    at=0
    fails=0
    for first in range(1,max_x+1,chunk):
        last=min(max_x+1,first+chunk)
        x=np.arange(first,last,dtype=np.int64)
        e=np.frexp(x.astype(np.float64))[1]-1
        k=e//2
        shifts=np.left_shift(np.int64(1),2*k)
        s1=np.int64(1<<q1)
        m1=(x<<q1)//shifts
        idx=np.where(m1>=2*s1,
                     bins+((m1-2*s1)*bins)//(2*s1),
                     ((m1-s1)*bins)//s1)
        if np.any((idx<0)|(idx>=2*bins)):raise AssertionError("bad lookup index")
        y1=newton(lut[idx],m1,q1)
        y1max=int(y1.max())
        max1=max(max1,y1max)
        m2=(x<<q2)//shifts
        y2=newton(y1<<(q2-q1),m2,q2)
        max2=max(max2,int(y2.max()))
        approximate=(y2.astype(float)/(1<<q2))/np.left_shift(np.int64(1),k)
        reference=1/np.sqrt(x.astype(float))
        errors=np.abs(approximate-reference)/reference
        j=int(np.argmax(errors))
        if float(errors[j])>worst:
            worst=float(errors[j]);at=int(x[j])
        fails+=int(np.count_nonzero(errors>=EPS))
    w1=max1.bit_length()
    w2=max2.bit_length()
    # Input x, the first-stage value, and the second-stage value all
    # coexist in a straightforward out-of-place Newton implementation.
    # This is NOT a universal quantum lower bound: constrained subspaces
    # or alternative reversible in-place constructions could avoid it.
    naive_live=22+w1+w2
    # K149's bit-product proxy for a middle/truncated schoolbook product.
    # NOT an exact gate count, lower bound, or the real width of operands.
    proxy=3*(q1*(q1+1)//2)+3*(q2*(q2+1)//2)
    return {
        "first_q":q1,"last_q":q2,"bins_per_octave":bins,
        "seed_entries":2*bins,"tested_inputs":max_x,
        "violations":fails,"worst_relative_error":worst,
        "tolerance_fraction":worst/EPS,"worst_x":at,
        "max_first_iteration_integer":max1,"first_register_bits":w1,
        "max_second_iteration_integer":max2,"second_register_bits":w2,
        "straightforward_live_bits_without_scratch":naive_live,
        "available_scratch_if_62q":BASE_Q-naive_live,
        "six_product_schoolbook_proxy":proxy,
        "vs_all_q26_proxy_percent":round(100*(1-proxy/(6*(26*27//2))),3),
        "passes_numerical_surrogate":fails==0
    }

def reversible_collision_witness():
    # Reversible classical circuits are injective on the full basis.
    # Fixed-m Newton y -> y' need not be injective; therefore erasing the
    # old estimate in place is not automatically a legal quantum mapping.
    q=8
    scale=1<<q
    m=np.array([3*scale//2],dtype=np.int64)
    seen={}
    for v in range(scale//2,scale+1):
        output=int(newton(np.array([v],dtype=np.int64),m,q)[0])
        if output in seen:
            return {"m_Q8":int(m[0]),"input_y_a":seen[output],
                    "input_y_b":v,"same_output_y":output,
                    "meaning":"Plain Newton map cannot overwrite an arbitrary y register reversibly without retaining distinguishing information."}
        seen[output]=v
    raise AssertionError("Expected finite-width collision")

def k123_gate_reference(n):
    # Reproduces the exact count obtained by the K123 original
    # high-to-low modular multiply-accumulate implementation.
    # This is NOT a construction of fixed-point middle-product Newton.
    return sum((k+1)*(n-k)**2 for k in range(n))

def selftest():
    w=reversible_collision_witness()
    assert w["input_y_a"]!=w["input_y_b"]
    assert k123_gate_reference(8)==540
    assert k123_gate_reference(16)==6936
    assert int(newton(np.array([100],dtype=np.int64),
                      np.array([384],dtype=np.int64),8)[0])>100
    print("K150_SELFTEST PASS reversible collision, K123 gate formula and Newton update",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
    p.add_argument("--out",type=Path,default=Path("competition/k150/results/mixed_precision.json"))
    p.add_argument("--max-x",type=int,default=N)
    p.add_argument("--chunk",type=int,default=100000)
    p.add_argument("--first-q",default="13,14,15,16,26")
    p.add_argument("--last-q",type=int,default=26)
    p.add_argument("--bins",default="32")
    p.add_argument("--selftest",action="store_true")
    args=p.parse_args()
    selftest()
    if args.selftest:return
    if not(1<=args.max_x<=N and args.chunk>=100 and 1<=args.last_q<=30):p.error("invalid bounds")
    sha=hashlib.sha256(args.baseline.read_bytes()).hexdigest()
    if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
    qs=sorted(set(int(v) for v in args.first_q.split(",")))
    bins=sorted(set(int(v) for v in args.bins.split(",")))
    if any(q<8 or q>args.last_q for q in qs) or any(b<1 or b&(b-1) for b in bins):
        p.error("bad first-q or bins")
    cases=[]
    for b in bins:
        for q in qs:
            case=one_case(q,args.last_q,b,args.max_x,args.chunk)
            cases.append(case)
            print("K150_CASE",json.dumps(case),flush=True)
    best=min((c for c in cases if c["passes_numerical_surrogate"]),
             key=lambda c:(c["six_product_schoolbook_proxy"],c["seed_entries"]),
             default=None)
    report={
        "status":"NUMERICAL_AND_RESOURCE_PROXY_ONLY_NO_REVERSIBLE_NEWTON_IMPLEMENTATION",
        "source_sha256":sha,"tested_x":args.max_x,"reference_score":BASE_SCORE,
        "cases":cases,"smallest_proxy_numerical_pass":best,
        "injectivity_counterexample":reversible_collision_witness(),
        "k123_naive_modular_reference_ccx_at_14":k123_gate_reference(14),
        "k123_naive_modular_reference_ccx_at_26":k123_gate_reference(26),
        "k123_six_products_3_each_reference_ccx":
            3*(k123_gate_reference(14)+k123_gate_reference(26)),
        "caveats":[
            "The original 22-bit x input must remain unchanged.",
            "No compressed in-place bijection or actual 62-qubit Newton circuit constructed.",
            "The local collision rules out naive arbitrary-state overwriting, not specialized reachable-subspace transformations.",
            "Straightforward peak liveness is NOT a mathematical minimum across all circuits.",
            "The schoolbook proxy is NOT a Toffoli count or proven lower bound.",
            "K123 gate counts are for a different full modular multiply-accumulate, not the exact fixed-point Newton middle product.",
            "No reversible lookup, cleanup, phase application, quantum phase-error proof or official verifier run.",
            "A numerically passing implementation is NOT a verified leaderboard solution."
        ]
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print("K150_RESULT",json.dumps({
        "configs":len(cases),
        "passing":sum(c["passes_numerical_surrogate"] for c in cases),
        "best_proxy":{k:best[k] for k in (
            "first_q","last_q","bins_per_octave","tolerance_fraction",
            "straightforward_live_bits_without_scratch",
            "six_product_schoolbook_proxy")} if best else None,
        "out":str(args.out)}),flush=True)

if __name__=="__main__":main()
