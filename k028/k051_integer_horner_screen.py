#!/usr/bin/env python3
"""K051: full-domain integer-only fixed-point Horner screening for invsqrt.

The coefficient fit is computed offline in float64 (as in K050), and every
runtime Horner multiply/add is then evaluated in SIGNED INT64 fixed-point.

This is not a quantum circuit and is not the official phase verifier.
The goal is to determine actual operand precision needed for reversible
synthesis before committing expensive qubit registers.

For input x: x = 2**e * m, 1 <= m < 2, with region r=floor(R*(m-1)),
 t = 2*R*(m-1-r/R)-1, in [-1,1].
We represent t as integer t_q=round(t*2**TB), polynomial coefficient c_j
as integer c_jq=round(c_j*2**CB), and Horner step
 a_q <- c_jq + ((a_q*t_q) >> TB).
Negative signed products round down (arith right-shift), matching an
implementable reversible fixed-point truncation. The final normalized
approximation y=a_q/2**CB is evaluated against 1/sqrt(m).

Coefficient selection/lookup, exponent correction, phase encoding,
uncomputation, and the official verifier remain future work.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
FULL=3_133_452
TARGET=2.0**-24
# (regions, polynomial degree, coefficient fractional bits, t fractional bits).
CONFIGS=[
    (8,4,26,20),(8,4,26,24),(8,4,26,28),
    (8,4,28,20),(8,4,28,24),(8,4,28,28),
    (8,4,30,24),(8,4,30,28),
    (16,3,26,20),(16,3,26,24),(16,3,26,28),
    (16,3,28,24),(16,3,28,28),
    (16,4,28,24),(16,4,28,28),
    (16,4,30,24),(16,4,30,28),
    (8,5,28,24),(8,5,28,28),
    (16,5,28,24),(16,5,28,28)
]

def offline_coefficients(regions,degree,coef_bits):
    nodes=np.cos((np.arange(degree+1)+0.5)*np.pi/(degree+1))
    rows=[]
    for r in range(regions):
        xx=1.0+(r+(nodes+1)/2)/regions
        cheb=np.polynomial.chebyshev.chebfit(nodes,1/np.sqrt(xx),degree)
        power=np.polynomial.chebyshev.cheb2poly(cheb)
        rows.append(np.rint(power*(2.0**coef_bits)).astype(np.int64))
    return np.stack(rows)

def scalar_screen(cfg,max_x,batch_size,record_table):
    regions,degree,cb,tb=cfg
    coeff=offline_coefficients(regions,degree,cb)
    largest=int(np.max(np.abs(coeff)))
    if largest*(2**tb)>=2**61:
        raise OverflowError(f"Potential int64 product overflow for {cfg}")
    result={"regions":regions,"degree":degree,
            "coefficient_fractional_bits":cb,
            "t_fractional_bits":tb,
            "coefficient_words":regions*(degree+1),
            "coefficient_table_bits_lower_bound":regions*(degree+1)*(cb+1),
            "max_relative_error":0.0,"worst_x":None,"scalar_fail_count":0,
            "checked_x":0,"rounding":"signed arithmetic shift / floor"}
    for start in range(1,max_x+1,batch_size):
        xs=np.arange(start,min(start+batch_size,max_x+1),dtype=np.float64)
        mant,exp=np.frexp(xs)
        mant*=2.0
        exp-=1
        region=np.minimum(regions-1,np.floor((mant-1)*regions).astype(np.int64))
        t=((mant-1.0)*regions-region)*2.0-1.0
        t_q=np.rint(t*(2.0**tb)).astype(np.int64)
        # Overflow safety: all polynomials remain O(1); clamp against
        # unexpected coefficients/intermediates before every product.
        co=coeff[region]
        acc=co[:,-1].copy()
        for j in range(degree-1,-1,-1):
            max_prod=int(np.max(np.abs(acc)))*int(np.max(np.abs(t_q)))
            if max_prod>=2**62:
                raise OverflowError("Horner intermediate too large: "+repr(cfg))
            acc=co[:,j]+((acc*t_q)>>tb)
        normalized_approx=acc.astype(np.float64)/(2.0**cb)
        expected=1.0/np.sqrt(mant)
        err=np.abs(normalized_approx/expected-1)
        k=int(np.argmax(err))
        if float(err[k])>result["max_relative_error"]:
            result["max_relative_error"]=float(err[k])
            result["worst_x"]=int(xs[k])
        result["scalar_fail_count"]+=int(np.count_nonzero(err>=TARGET))
        result["checked_x"]+=len(xs)
    result["scalar_pass"]=result["scalar_fail_count"]==0
    if record_table:
        result["coefficient_table_signed_ints"]=coeff.tolist()
    return result

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--max-x",type=int,default=FULL)
    pa.add_argument("--batch",type=int,default=100000)
    pa.add_argument("--out",type=Path,default=ROOT/"competition/k051/results")
    args=pa.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if args.max_x<1 or args.max_x>FULL:raise SystemExit("Invalid domain bound")
    if args.batch<1:raise SystemExit("Batch must be positive")
    results=[]
    for cfg in CONFIGS:
        try:
            item=scalar_screen(cfg,args.max_x,args.batch,False)
        except Exception as exc:
            item={"configuration":cfg,"status":"ERROR","error":repr(exc),
                  "scalar_pass":False}
        results.append(item)
        print("K051_MODEL",json.dumps(item,sort_keys=True),flush=True)
    passing=sorted((v for v in results if v.get("scalar_pass")),
                    key=lambda r:(r["coefficient_words"]*
                                  (r["coefficient_fractional_bits"]+1),
                                  r["max_relative_error"]))
    best=[]
    for row in passing[:3]:
        cfg=(row["regions"],row["degree"],
             row["coefficient_fractional_bits"],row["t_fractional_bits"])
        # Export exact signed coefficient words to seed real synthesis.
        item=scalar_screen(cfg,args.max_x,args.batch,True)
        best.append(item)
    report={"status":"INTEGER_HORNER_SCALAR_SCREEN_ONLY",
            "domain_end":args.max_x,"scalar_relative_error_threshold":TARGET,
            "configurations":results,"best_with_coefficients":best,
            "caveat":"No phase circuit, reversible arithmetic, or official verification yet."}
    (args.out/"result.json").write_text(json.dumps(report,indent=2))
    print("K051_RESULT",json.dumps({"status":report["status"],
        "passing_models":len(passing),
        "best_models":[{k:v for k,v in r.items()
                        if k not in ("coefficient_table_signed_ints",)}
                        for r in best]},sort_keys=True),flush=True)
    print("SAVED",args.out/"result.json",flush=True)

if __name__=="__main__":main()
