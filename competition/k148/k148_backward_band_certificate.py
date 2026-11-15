#!/usr/bin/env python3
"""K148: certified three-point no-go test for uniform piecewise-linear invsqrt.
Distinct from K117-123 numerical fits: analytical LOWER BOUND, no coefficients.
A failed necessary condition proves no real-valued affine fit can pass, even
before rounding, lookup, reversible arithmetic, or quantum resource costs.
"""
import argparse,hashlib,json
from decimal import Decimal,localcontext
from pathlib import Path
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
REF_SCORE=95369.00696815242
def bound(n,epsilon,exponent=20):
    # x0=2^e, x1=2^e+2^e/(2n), x2=2^e+2^e/n
    # Exactly representable integers for n | 2^(e-1).
    assert (1<<exponent)%(2*n)==0
    with localcontext() as c:
        c.prec=95
        one=Decimal(1)
        f=lambda x:one/x.sqrt()
        m0=one;m1=one+one/Decimal(2*n);m2=one+one/Decimal(n)
        f0,f1,f2=(f(m) for m in (m0,m1,m2))
        # For affine L, L(mid)=(L(left)+L(right))/2.
        # D= (f0+f2)/2 - f1 > 0 (strict convexity).
        # If |L_i-f_i|<=eps*f_i at all three points, then
        # D<=eps*(f1+(f0+f2)/2). Strict violation proves impossible.
        d=(f0+f2)/2-f1
        cap=f1+(f0+f2)/2
        minimum_epsilon=d/cap
        return {"uniform_regions":n,
           "integer_witness_x":[1<<exponent,(1<<exponent)+(1<<exponent)//(2*n),(1<<exponent)+(1<<exponent)//n],
           "three_point_relative_error_lower_bound":str(minimum_epsilon),
           "minimum_error_to_tolerance_ratio":float(minimum_epsilon/epsilon),
           "necessary_condition":"FAIL" if minimum_epsilon>epsilon else "NOT_RULED_OUT",
           "proof":"No affine function can meet all three relative-error bands when D > eps*(f1+(f0+f2)/2)."}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k148/results/backward_band_no_go.json"))
 p.add_argument("--max-x",type=int,default=3133452)
 p.add_argument("--regions",default="128,256,512,1024,2048")
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 with localcontext() as c:
  c.prec=95;eps=Decimal(2)**-24
  test=bound(128,eps)
  assert test["necessary_condition"]=="FAIL"
  assert 47<float(test["minimum_error_to_tolerance_ratio"])<49
  assert bound(2048,eps)["necessary_condition"]=="NOT_RULED_OUT"
 print("K148_SELFTEST PASS exact decimal curvature lower bounds",flush=True)
 if a.selftest:return
 raw=a.baseline.read_bytes();sha=hashlib.sha256(raw).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 ns=sorted(set(int(z) for z in a.regions.split(",")))
 if not ns or any(n<1 or n>2**19 or (n&(n-1)) for n in ns):p.error("regions must be powers of two <= 2^19")
 if a.max_x<2**20+2**20//min(ns):p.error("witness integer x exceeds domain")
 rows=[bound(n,eps) for n in ns]
 for r in rows:print("K148_BOUND",json.dumps(r),flush=True)
 report={"status":"PROVEN_NECESSARY_CONDITION_FOR_UNIFORM_AFFINE_PIECES",
         "baseline_sha256":sha,"reference_score":REF_SCORE,
         "nominal_relative_tolerance":str(eps),"domain":[1,a.max_x],
         "function":"x^(-1/2), normalized to m in [1,2)",
         "rows":rows,
         "limitations":["Only uniform affine piece fits are ruled out, not adaptive spacing, higher-degree polynomials, or a completely different function circuit.",
           "Three-point certificate is a necessary condition, not proof that NOT_RULED_OUT designs succeed.",
           "Assumes the K117/K120 nominal 2^-24 relative-error surrogate; the official Helios verifier must be checked separately for a synthesized circuit.",
           "No phase synthesis, coefficient quantization, reversible lookup, qubit cost, or official score computed.",
           "No KMX candidate generated."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(report,indent=2)+"\n")
 print("K148_RESULT",json.dumps({"impossible_uniform_regions":[r["uniform_regions"] for r in rows if r["necessary_condition"]=="FAIL"],
 "not_ruled_out":[r["uniform_regions"] for r in rows if r["necessary_condition"]!="FAIL"],
 "out":str(a.out)}),flush=True)
if __name__=="__main__":main()
