#!/usr/bin/env python3
"""K050: isolate interpolation vs coefficient-rounding error for direct invsqrt.

Numerically screens EVERY integer x in [1,3133452], with both
floating coefficients and quantized coefficients, using a shared uniform
piecewise Chebyshev-interpolation polynomial. All arithmetic in evaluation
is float64; this is NOT a fixed-point reversible circuit and NOT an
official phase-verifier pass.

Purposely test precision 26..34 rather than increasing polynomial degree
indiscriminately: the K049 24-bit floor was ~1e-7 even at degree 6.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
FULL_X=3_133_452
THRESHOLD=2**-24
# Keep number of full sweeps controlled, and include degree/region checks.
MODELS=((4,3),(8,3),(16,3),(8,4),(16,4),(32,3),(16,5),(32,4))
BITS=(26,28,30,32,34)

def coefficients(regions,degree):
    node=np.cos((np.arange(degree+1)+0.5)*np.pi/(degree+1))
    result=np.empty((regions,degree+1))
    for r in range(regions):
        left=1.0+r/regions
        xx=left+(node+1)/(2*regions)
        cheb=np.polynomial.chebyshev.chebfit(node,1/np.sqrt(xx),degree)
        result[r]=np.polynomial.chebyshev.cheb2poly(cheb)
    return result

def calc(c,t):
    val=c[:,-1]
    for j in range(c.shape[1]-2,-1,-1):val=val*t+c[:,j]
    return val

def test_model(regions,degree,max_x,batch):
    coef=coefficients(regions,degree)
    qcoefs={bits:np.rint(coef*2.0**bits)/2.0**bits for bits in BITS}
    cases={bits:{"max_rel":0.0,"worst_x":None,"fail_count":0} for bits in (0,)+BITS}
    for start in range(1,max_x+1,batch):
        xs=np.arange(start,min(start+batch,max_x+1),dtype=np.float64)
        mant,exp=np.frexp(xs)
        mant*=2
        exp-=1
        idx=np.minimum(regions-1, np.floor((mant-1)*regions).astype(np.int64))
        t=(mant-1.0-idx/regions)*(2*regions)-1.0
        # Relative error measured on normalized 1/sqrt(m); exponent cancels.
        target=1/np.sqrt(mant)
        for bits,ct in ((0,coef),)+tuple(qcoefs.items()):
            approx=calc(ct[idx],t)
            error=np.abs(approx/target-1.0)
            peak=int(np.argmax(error))
            candidate=float(error[peak])
            entry=cases[bits]
            if candidate>entry["max_rel"]:
                entry["max_rel"]=candidate
                entry["worst_x"]=int(xs[peak])
            entry["fail_count"]+=int(np.count_nonzero(error>=THRESHOLD))
    float_error=cases[0]["max_rel"]
    rows=[]
    for bits in BITS:
        item=cases[bits]
        rows.append({
            "regions":regions,"degree":degree,"coefficient_bits":bits,
            "coefficient_words":regions*(degree+1),
            "approx_only_max_relative_error":float_error,
            "approx_only_fail_count":cases[0]["fail_count"],
            "with_quantized_coefficients_max_relative_error":item["max_rel"],
            "quantization_additional_error_upper_bound_observed":
                max(0.0,item["max_rel"]-float_error),
            "worst_x":item["worst_x"],"scalar_fail_count":item["fail_count"],
            "scalar_pass":item["fail_count"]==0,
            "note":"This is a floating-arithmetic scalar screen, not reversible fixed-point or official phase verification."
        })
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--max-x",type=int,default=FULL_X)
    p.add_argument("--batch",type=int,default=150000)
    p.add_argument("--out",type=Path,default=ROOT/"competition/k050/results")
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    allrows=[]
    for regions,degree in MODELS:
        batch=test_model(regions,degree,a.max_x,a.batch)
        allrows.extend(batch)
        print("K050_MODEL",json.dumps({
            "regions":regions,"degree":degree,
            "approx_error":batch[0]["approx_only_max_relative_error"],
            "by_bits":[{"bits":r["coefficient_bits"],
                        "error":r["with_quantized_coefficients_max_relative_error"],
                        "fail_count":r["scalar_fail_count"]}
                       for r in batch]},sort_keys=True),flush=True)
    winners=sorted([r for r in allrows if r["scalar_pass"]],
                   key=lambda r:(r["coefficient_words"]*r["coefficient_bits"],
                                 r["degree"],r["regions"]))
    report={"status":"SCALAR_ONLY_NO_QUANTUM_CIRCUIT",
            "max_x":a.max_x,"threshold":THRESHOLD,
            "model_count":len(MODELS),"candidate_count":len(allrows),
            "results":allrows,"passing_models":winners}
    (a.out/"result.json").write_text(json.dumps(report,indent=2))
    print("K050_RESULT",json.dumps({"status":report["status"],
        "scalar_pass_count":len(winners),
        "most_compact":winners[0] if winners else None},sort_keys=True),flush=True)
    print("SAVED",a.out/"result.json",flush=True)
if __name__=="__main__":main()
