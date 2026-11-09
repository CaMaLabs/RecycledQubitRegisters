#!/usr/bin/env python3
"""K049: independent numerical design space for direct invsqrt phase approximation.

This is an architecture *screen*, not a quantum circuit or Kaggle verifier pass.
Unlike K040's Newton correction, approximate 1/sqrt(x) via exponent
normalization, a small region index and fixed-point local polynomial:
    x = 2**e * m, m in [1,2)
    1/sqrt(x) = 2**(-e/2) * P_region(m).
Two exponent parities share the same coefficient table. We sweep region
counts, polynomial degrees, and coefficient fractional bits, screening
every integer x in the official 1..3,133,452 domain.

A candidate enters quantum synthesis ONLY if its scalar approximation error
is well below 2**-24 relative and its estimated Toffoli/ancilla budget
appears competitive. The official phase contract, fixed-point representation,
and synthesis/cleanup remain TO BE IMPLEMENTED and verified independently.
"""
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
try:
    import numpy as np
except ImportError as exc:
    raise SystemExit("K049 numerical screen requires numpy in the Kaggle venv") from exc

ROOT=Path(__file__).resolve().parents[2]
MAX_X=3_133_452
# This is ONLY a scalar relative-error screen; official tolerance concerns
# accumulated PHASE error and is verified independently by the official tool.
GOAL=2.0**-24
CONFIGS=((4,3,24),(8,3,24),(16,3,24),(32,3,24),
         (8,4,22),(16,4,22),(32,4,22),(64,4,22),
         (16,5,20),(32,5,20),(64,5,20),(128,5,20),
         (32,5,24),(64,5,24),(128,5,24),
         (64,6,24),(128,6,24),(256,6,24))

def polynomials(regions,degree,fractional_bits):
    # Fixed 1<=m<2 intervals; use Gauss-Chebyshev interpolation nodes.
    nodes=np.cos((np.arange(degree+1)+0.5)*np.pi/(degree+1))
    coeff=[]
    for j in range(regions):
        left=1.0+j/regions
        right=left+1.0/regions
        xx=(left+right)*0.5 + nodes*(right-left)*0.5
        yy=1.0/np.sqrt(xx)
        cheb=np.polynomial.chebyshev.chebfit(nodes,yy,degree)
        polynomial=np.polynomial.chebyshev.cheb2poly(cheb)
        fixed=np.rint(polynomial*(2.0**fractional_bits)).astype(np.int64)
        coeff.append(fixed)
    return np.array(coeff,dtype=np.int64)

def evaluate(config,full_domain,batch):
    regions,degree,bits=config
    poly=polynomials(*config)
    maximum_error=0.0
    worst_x=None
    failures=0
    checked=0
    for begin in range(1,full_domain+1,batch):
        xs=np.arange(begin,min(begin+batch,full_domain+1),dtype=np.float64)
        mant,exp=np.frexp(xs)
        mant=2*mant
        exp=exp-1
        region=np.minimum(regions-1,np.floor((mant-1.0)*regions).astype(np.int64))
        # Evaluate unrounded real polynomial representing quantized
        # constant words. Runtime arithmetic quantization is NOT modeled.
        t=(mant-(1.0+region/regions))*regions*2-1
        co=poly[region].astype(np.float64)/(2.0**bits)
        approx=co[:,-1]
        for k in range(degree-1,-1,-1):
            approx=approx*t+co[:,k]
        approx=np.ldexp(approx,-(exp//2))
        # For odd exponents the normalization contributes sqrt(1/2).
        approx=np.where((exp & 1)!=0,approx/math.sqrt(2),approx)
        exact=1.0/np.sqrt(xs)
        errors=np.abs(approx/exact-1.0)
        ix=int(np.argmax(errors))
        if errors[ix]>maximum_error:
            maximum_error=float(errors[ix]);worst_x=int(xs[ix])
        failures+=int(np.count_nonzero(errors>=GOAL))
        checked+=len(xs)
    return {"regions":regions,"degree":degree,"coef_fractional_bits":bits,
            "table_coefficients":regions*(degree+1),
            "table_data_bits":regions*(degree+1)*(bits+2),
            "scalar_max_relative_error":maximum_error,
            "worst_x":worst_x,
            "scalar_threshold":GOAL,"scalar_fail_count":failures,
            "scalar_screen_pass":failures==0,
            "checked_x":checked,
            "note":"Ignores reversible arithmetic rounding, phase encoding, rotation synthesis and ancilla cleanup; not a verified circuit."}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--max-x",type=int,default=MAX_X)
    ap.add_argument("--batch",type=int,default=100_000)
    ap.add_argument("--out",type=Path,default=ROOT/"competition/k049/results")
    args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for cfg in CONFIGS:
        result=evaluate(cfg,args.max_x,args.batch)
        rows.append(result)
        print("K049_CONFIG",json.dumps({k:v for k,v in result.items()
            if k not in ("note","scalar_threshold","checked_x")},sort_keys=True),flush=True)
    winners=sorted((r for r in rows if r["scalar_screen_pass"]),
                   key=lambda r:(r["table_data_bits"],r["degree"],r["regions"]))
    report={"status":"NUMERICAL_ARCHITECTURE_SCREEN_ONLY",
            "model":"regionwise normalized mantissa Chebyshev + quantized constant words",
            "reference_contract":"scalar relative tolerance only, not official phase verifier",
            "max_x":args.max_x,"target_scalar_relative_error":GOAL,
            "configs":rows,
            "scalar_passes":winners}
    (args.out/"result.json").write_text(json.dumps(report,indent=2))
    print("K049_RESULT",json.dumps({
        "status":report["status"],"passing_scalar_models":len(winners),
        "most_compact_scalar_pass":winners[0] if winners else None},sort_keys=True),flush=True)
    print("SAVED",args.out/"result.json",flush=True)
if __name__=="__main__":main()
