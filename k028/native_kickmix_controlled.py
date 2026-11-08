#!/usr/bin/env python3
"""K028-D: Direct controlled-add replacement of reference _multiply_m.

Identical fixed-point index mapping, but uses Kickmix's quantum-controlled
iadd/isub directly instead of init_and/row scratch or CCX Wallace workspaces.
Outputs official-source A/B KMB artifacts; verify them independently.
"""
import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
VERIFIERS=ROOT/"competition/k001/private/official/verifiers"
sys.path.insert(0,str(VERIFIERS))
import kickmix as km

def controlled_m(builder,inverse,x,square,z,scratch):
    width,wsq,wz=len(x),len(square),len(z)-2
    n=len(z)
    # Each reference _add_row adds exactly one controlled, shifted
    # fragment of square. Truncate negative offsets and high overflow.
    for i in (reversed(range(width)) if inverse else range(width)):
        e=wz-wsq+i-width+2
        jlo=max(0,-e)
        jhi=min(wsq,n-e)
        if jlo >= jhi:
            continue
        lo=jlo+e
        offset=square[jlo:jhi]
        target=z[lo:n]
        if inverse:
            builder.isub(offset,target=target,control=x[i])
        else:
            builder.iadd(offset,target=target,control=x[i])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",default=str(ROOT/"competition/k028d/results"))
    p.add_argument("--reference-only",action="store_true")
    a=p.parse_args()
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    ref=importlib.import_module("invsqrt.nr_reference_circuit")
    prec=ref.Precision(coef_bits=17,delta_bits=12,product_bits=27,result_bits=28,square_bits=27)
    ref_c=ref.build_nr_circuit(10,prec=prec)
    control=out/"control.kmb"
    ref_c.to_file(str(control),format="kmb")
    print(json.dumps({"control_bytes":control.stat().st_size}),flush=True)
    if a.reference_only:return
    old=ref._multiply_m
    calls=[0,0]
    def replace(builder,inverse,x,square,z,scratch):
        calls[int(bool(inverse))]+=1
        return controlled_m(builder,inverse,x,square,z,scratch)
    ref._multiply_m=replace
    try:
        exp=ref.build_nr_circuit(10,prec=prec)
    finally:
        ref._multiply_m=old
    variant=out/"controlled_m.kmb"
    exp.to_file(str(variant),format="kmb")
    if calls!=[1,1]:
        raise RuntimeError("Expected one forward and one reverse call: "+str(calls))
    print(json.dumps({"controlled_bytes":variant.stat().st_size,
                      "calls":calls,"status":"BUILT_REQUIRES_OFFICIAL_VERIFY"}),flush=True)

if __name__=="__main__":main()
