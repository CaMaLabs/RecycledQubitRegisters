#!/usr/bin/env python3
"""K056 — first actual reversible fixed-point Horner phase circuit.

The official bounded-domain verifier checks all x=1..15:
  x=1..7:  verified K052 equality-controlled phase fallback.
  x=8..15: NEW reversible integer Horner polynomial, using 2 coefficient
            regions selected by x[2], and t=(-1 + (x&3)/2).
  Inputs 16..2**22-1 are NOT supported. NOT a full-domain candidate.

The polynomial has degree 3 and is interpolated at the four exact dyadic
t values in each region, fitting the DIRECT TARGET 1/sqrt(x) turns.
Coefficient bits=36; signed accumulator=39 bits; t is Q6 signed 7-bit.
The quantum circuit performs:
  controlled coefficient XOR load -> signed schoolbook multiply ->
  fixed-point truncate -> reversible integer addition per Horner stage ->
  phase controlled by x[3] -> exact reverse computation -> free.

This experiment establishes genuine compute/phase/uncompute behavior. It is
a functional prototype, NOT a competitive resource optimization. All
reported resource numbers and accuracy come from the unmodified verifier.
"""
from __future__ import annotations
import argparse, hashlib, importlib, importlib.util, json, math, sys
from fractions import Fraction
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
VER=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VER))
import kickmix as km

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

k031=module("k031_k056",ROOT/"competition/k031/k031_full_domain_repair.py")
k034=module("k034_k056",ROOT/"competition/k034/k034_row_local_scratch.py")
k052=module("k052_k056",ROOT/"competition/k052/k052_bounded_direct_phase.py")

CB=36
TB=6
W=39
TW=7
PW=W+TW
POLY_DEGREE=3
PHASE_MIN_BIT=8
MASK=(1<<W)-1

def coeff_table():
    # Values of t: -1, -.5, 0, +.5 in each of two regions.
    t=np.array([-1.0,-0.5,0.0,0.5])
    out=[]
    for reg in (0,1):
        xx=np.array([8+4*reg+j for j in range(4)],dtype=np.float64)
        fit=np.polynomial.polynomial.polyfit(t,1/np.sqrt(xx),POLY_DEGREE)
        words=np.rint(fit*(2.0**CB)).astype(np.int64)
        out.append([int(v) for v in words])
    return out

def eval_fixed(x,table):
    reg=(x-8)//4
    t_q=((x-8)&3)*(1<<(TB-1))-(1<<TB)
    a=table[reg][POLY_DEGREE]
    for j in range(POLY_DEGREE-1,-1,-1):
        a=table[reg][j]+((a*t_q)>>TB)
    return a/(1<<CB)

def toggle_coeff(builder,x,reg,j,table):
    # XOR loading in two's-complement register. Unload by repeating.
    first=table[0][j]&MASK
    delta=(table[0][j]^table[1][j])&MASK
    builder.gf2_iadd(first,target=reg)
    builder.gf2_iadd(delta,target=reg,control=x[2])

def multiply(builder,row,a,t,product,inverse):
    # Signed product of W-bit a and TW-bit t into PW-bit product:
    # positive/negative sign comes from the two's-complement top bits.
    ops=[]
    for j in range(TW):
        positive=[(a[i],i+j) for i in range(W-1)]
        top=[(a[W-1],W-1+j)]
        ops.append((t[j],positive,j==TW-1))
        ops.append((t[j],top,j!=TW-1))
    for ctl,terms,neg in (reversed(ops) if inverse else ops):
        row(builder,inverse,ctl,terms,product,km.array([]),subtract=neg)

def build(path):
    table=coeff_table()
    errors=[{"x":n,"target":1/math.sqrt(n),"modeled":eval_fixed(n,table),
             "ratio":abs(eval_fixed(n,table)-1/math.sqrt(n))/
                       (2**-24/math.sqrt(n))}
            for n in range(8,16)]
    worst=max(errors,key=lambda r:r["ratio"])
    if worst["ratio"]>0.5:
        raise RuntimeError("Fixed-point model does not leave phase margin: "+str(worst))
    stats={"rows":0,"allocated_sum":0,"max_row_width":0}
    row=k034.local_row("compact",stats)
    b=km.CircuitBuilder()
    x=b.create_quantum_register(22,name="x")
    # Complement for 1..7 is from official PASS K052.
    fallback=b.alloc_qubits(3)
    for n in range(1,8):
        exact=1/math.sqrt(n)
        phase=Fraction(round(exact*(1<<50)),1<<50)
        k052.predicate(b,x,fallback,n,4,phase)
    b.free(fallback)

    # t_q: bits [TB-1,TB] = [x0, NOT x1] in signed TW-bit QTB.
    t=b.alloc_qubits(TW)
    b.cx(x[0],t[TB-1])
    b.cx(x[1],t[TB])
    b.x(t[TB])

    acc=[b.alloc_qubits(W)]
    toggle_coeff(b,x,acc[0],POLY_DEGREE,table)

    def forward_step(source,j):
        product=b.alloc_qubits(PW)
        multiply(b,row,source,t,product,False)
        dest=b.alloc_qubits(W)
        for k in range(W):
            b.cx(product[TB+k],dest[k])
        coef=b.alloc_qubits(W)
        toggle_coeff(b,x,coef,j,table)
        b.iadd(coef,target=dest)
        toggle_coeff(b,x,coef,j,table)
        b.free(coef)
        multiply(b,row,source,t,product,True)
        b.free(product)
        return dest

    def reverse_step(source,dest,j):
        product=b.alloc_qubits(PW)
        multiply(b,row,source,t,product,False)
        coef=b.alloc_qubits(W)
        toggle_coeff(b,x,coef,j,table)
        b.isub(coef,target=dest)
        toggle_coeff(b,x,coef,j,table)
        b.free(coef)
        for k in range(W-1,-1,-1):
            b.cx(product[TB+k],dest[k])
        multiply(b,row,source,t,product,True)
        b.free(product)
        b.free(dest)

    for j in reversed(range(POLY_DEGREE)):
        acc.append(forward_step(acc[-1],j))

    # y=acc[-1]/2**CB is the direct phase in turns. Modulo one turn,
    # two's-complement MSB has negative weight. Restrict phase to x[3]=1;
    # x=1..7 is handled by the previously verified fallback.
    target=acc[-1]
    gate=b.alloc_qubits(1)
    rotation_count=0
    for i in range(PHASE_MIN_BIT,W):
        signed_weight=-(1<<i) if i==W-1 else (1<<i)
        exponent=Fraction(2*signed_weight,1<<CB)
        b.init_and(x[3],km.array([target[i]]),km.array([gate[0]]))
        b.z_pow(gate[0],exponent)
        b.del_and(x[3],km.array([target[i]]),km.array([gate[0]]))
        rotation_count+=1
    b.free(gate)

    for j in range(POLY_DEGREE):
        reverse_step(acc[-2],acc[-1],j)
        acc.pop()
    toggle_coeff(b,x,acc[0],POLY_DEGREE,table)
    b.free(acc[0])
    b.x(t[TB])
    b.cx(x[1],t[TB])
    b.cx(x[0],t[TB-1])
    b.free(t)
    circ=b.finish_circuit()
    circ.to_file(str(path),format="kmb")
    return {"num_qubits":circ.num_qubits,
            "file_bytes":path.stat().st_size,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows":stats,"phase_rotations_requested":rotation_count,
            "coefficients":table,"worst_numerical":worst,
            "scope":"official x=1..15 only; polynomial x=8..15"}

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--out",type=Path,default=ROOT/"competition/k056/results")
    pa.add_argument("--timeout",type=int,default=300)
    a=pa.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    target=a.out/"fixed_point_horner_bounded.kmb"
    try:
        built=build(target)
        print("K056_BUILD",json.dumps({
            k:v for k,v in built.items() if k!="coefficients"
        },sort_keys=True),flush=True)
        official=k031.verify(target,15,12345,a.timeout)
        status="PASS_BOUNDED" if (
            official.get("status")=="PASS" and official.get("exit_code")==0
        ) else "FAIL_BOUNDED"
        report={"status":status,"build":built,"official":official,
                "full_domain_verified":False,
                "warning":"Not a valid full-domain submission"}
        print("K056_VERIFY",json.dumps(official,sort_keys=True),flush=True)
    except Exception as e:
        report={"status":"BUILD_ERROR","error":repr(e),"full_domain_verified":False}
        print("K056_ERROR",json.dumps(report,sort_keys=True),flush=True)
    (a.out/"result.json").write_text(json.dumps(report,indent=2,default=str))
    print("K056_RESULT",json.dumps({"status":report["status"],
        "num_qubits":report.get("build",{}).get("num_qubits"),
        "score_bounded":report.get("official",{}).get("score"),
        "error":report.get("official",{}).get("error",
                                           report.get("error"))},sort_keys=True),flush=True)
    print("SAVED",a.out/"result.json",flush=True)

if __name__=="__main__":main()
