#!/usr/bin/env python3
"""K053: direct-phase Walsh/parity synthesis against bounded K052 baseline.

A phase oracle can be written as f(x)=sum_{S!=empty} a_S parity_S(x)
when f(0)=0. The Walsh-Hadamard transform produces coefficients a_S.
Every parity is computed with CNOTs onto one of the EXISTING x bits,
Z_POW is applied, then the parity CNOTs are reversed. No ancillae and
no Toffoli gates are required for this bounded-domain construction.

The desired mathematical phase is in turns. Kickmix Z_POW(a) implements
a/2 turns on |1>, so we apply Z_POW(2*a_S).

Only bits [0,bits) are read; this circuit is NOT a full-domain
submission for the 22-bit inverse-square-root challenge. All candidates
are checked using the unmodified official local verifier. In particular,
do not compare bounded official scores with full-domain scores.
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

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj

k031=module("k031_k053",ROOT/"competition/k031/k031_full_domain_repair.py")
k051=module("k051_k053",ROOT/"competition/k051/k051_integer_horner_screen.py")
k052=module("k052_k053",ROOT/"competition/k052/k052_bounded_direct_phase.py")

def fht(v):
    """Forward unnormalized Walsh-Hadamard transform, len power of two."""
    out=list(v)
    step=1
    n=len(out)
    while step<n:
        for i in range(0,n,2*step):
            for j in range(i,i+step):
                a,b=out[j],out[j+step]
                out[j]=a+b
                out[j+step]=a-b
        step*=2
    return out

def phase_lookup(bits):
    coefs=k051.offline_coefficients(8,4,28)
    values=[0.0]* (1<<bits)
    for x in range(1,1<<bits):
        values[x]=k052.model_phase(x,coefs,28,20)
    return values

def build(bits,drop_threshold,out):
    values=phase_lookup(bits)
    n=1<<bits
    had=fht(values)
    # f(x)=sum_{mask!=0} (-2*had[mask]/n)*parity(mask,x);
    # exact algebra for f(0)=0, apart from fp coefficient rounding.
    coefficients=[(mask,-2*had[mask]/n)
                  for mask in range(1,n) if abs(-2*had[mask]/n)>drop_threshold]
    b=km.CircuitBuilder()
    x=b.create_quantum_register(22,name="x")
    rotations=0
    cnot=0
    for mask,a in coefficients:
        active=[j for j in range(bits) if (mask>>j)&1]
        anchor=active[-1]
        others=active[:-1]
        for j in others:
            b.cx(x[j],x[anchor])
            cnot+=1
        exponent=Fraction(round((2*a)*(1<<52)),1<<52)
        if exponent:
            b.z_pow(x[anchor],exponent)
            rotations+=1
        for j in reversed(others):
            b.cx(x[j],x[anchor])
            cnot+=1
    circ=b.finish_circuit()
    circ.to_file(str(out),format="kmb")
    approximate=[]
    for value in range(1,n):
        got=sum(a for mask,a in coefficients if (value & mask).bit_count()&1)
        expected=1/math.sqrt(value)
        # Phase is periodic modulo one turn; these targets are in (0,1].
        error=abs(got-expected)
        approximate.append((value,error/(2**-24/math.sqrt(value))))
    worst=max(approximate,key=lambda z:z[1])
    return {"num_qubits":circ.num_qubits,
            "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
            "file_bytes":out.stat().st_size,
            "rotation_count_requested":rotations,
            "cnot_count_requested":cnot,
            "terms_kept":len(coefficients),
            "terms_total":n-1,
            "max_model_error_over_tolerance":worst[1],
            "worst_model_x":worst[0],
            "domain":n-1,
            "phase_zero_reference":values[0],
            "coefficient_drop_threshold":drop_threshold}

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--bits",type=int,nargs="+",default=[4,6,8])
    pa.add_argument("--out",type=Path,
                    default=ROOT/"competition/k053/results")
    pa.add_argument("--timeout",type=int,default=300)
    a=pa.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for bits in a.bits:
        if bits<2 or bits>10:
            raise SystemExit("Supported bounded-domain widths: 2..10")
        out=a.out/f"walsh_{bits}bits.kmb"
        row={"bits":bits}
        try:
            info=build(bits,0.0,out)
            check=k031.verify(out,(1<<bits)-1,12345,a.timeout)
            row.update({"build":info,"official":check,
                        "status":"PASS_BOUNDED" if check.get("status")=="PASS"
                        and check.get("exit_code")==0 else "FAIL_BOUNDED"})
        except Exception as exc:
            row.update({"status":"ERROR","error":repr(exc)})
        rows.append(row)
        print("K053_CASE",json.dumps(row,sort_keys=True),flush=True)
    (a.out/"result.json").write_text(json.dumps({
        "status":"BOUNDED_DIRECT_PHASE_WALSH_COMPARISON",
        "not_full_domain":True,"cases":rows},indent=2))
    print("K053_RESULT",json.dumps([{
        "bits":r["bits"],"status":r["status"],
        "qubits":r.get("build",{}).get("num_qubits"),
        "toffolis":r.get("official",{}).get("toffoli_count"),
        "rotations":r.get("official",{}).get("rotation_count"),
        "score":r.get("official",{}).get("score")}
        for r in rows],sort_keys=True),flush=True)
    print("SAVED",a.out/"result.json",flush=True)
if __name__=="__main__":main()
