#!/usr/bin/env python3
"""K159 integer-linearized logarithmic seed versus K149's 64-entry lookup.
Normalizes x=2^(2k)*m; m in [1,4); fits piecewise affine seed of invsqrt(m).
This is logarithmic-style initial-guess bit arithmetic, NOT an IEEE float bitcast.
Exact int64 Newton updates and complete numerical domain test; no circuit built.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
PIN="e7eb4386faaa1d27be1cd23ab6d8c577d9d33b9e25d6c47e6a8d7eabbbd04183"
N=3133452;EPS=2.0**-24
def lookup(q):
 a=np.arange(32,dtype=np.float64)
 m=np.r_[1+(a+.5)/32,2+2*(a+.5)/32]
 return np.rint((1<<q)/np.sqrt(m)).astype(np.int64)
def line_coeff(q,segments,style):
 """Half of segments on m 1..2, half on m 2..4. All constants frozen."""
 assert segments>=2 and segments&(segments-1)==0
 half=segments//2;S=1<<q;data=[]
 for j in range(segments):
  if j<half:
   m0=1+j/half;m1=1+(j+1)/half
  else:
   m0=2+2*(j-half)/half;m1=2+2*(j-half+1)/half
  f0=1/np.sqrt(m0);f1=1/np.sqrt(m1)
  fmid=1/np.sqrt((m0+m1)/2)
  slope=(f0-f1)/(m1-m0)
  if style=="chord": intercept=f0
  elif style=="midpoint":intercept=f0+(fmid-(f0+f1)/2)
  else:raise ValueError(style)
  # Store intercept Q14 and slope Q14; derivative is fixed per interval.
  data.append((round(intercept*S),round(slope*S),round(m0*S)))
 return data
def refine(y,m,q):
 s=np.int64(1<<q)
 sq=(y*y+s//2)//s
 prod=(m*sq+s//2)//s
 return (y*(3*s-prod)+s)//(2*s)
def screen(xs,first_q,last_q,segments,style,chunk):
 S=1<<first_q;coef=line_coeff(first_q,segments,style)
 mid=segments//2
 worst=0.;at=0;bad=0;seed_worst=0.;seed_at=0
 for start in range(0,len(xs),chunk):
  x=xs[start:start+chunk]
  e=np.frexp(x.astype(float))[1]-1;k=e//2
  m=(x<<first_q)//np.left_shift(np.int64(1),2*k)
  ix=np.where(m<2*S,((m-S)*mid)//S,
               mid+((m-2*S)*mid)//(2*S))
  if np.any(ix<0) or np.any(ix>=segments):raise AssertionError("seed address")
  inter=np.asarray([c[0] for c in coef],dtype=np.int64)
  slope=np.asarray([c[1] for c in coef],dtype=np.int64)
  origin=np.asarray([c[2] for c in coef],dtype=np.int64)
  y0=inter[ix]-((slope[ix]*(m-origin[ix])+S//2)//S)
  if np.any(y0<0) or np.any(y0>S):raise AssertionError("seed outside legal range")
  target=1/np.sqrt(x.astype(float))
  seed_y=y0.astype(float)/S/np.left_shift(np.int64(1),k)
  se=np.abs(seed_y-target)/target
  j=int(np.argmax(se))
  if se[j]>seed_worst:seed_worst=float(se[j]);seed_at=int(x[j])
  y1=refine(y0,m,first_q)
  shifted=y1<<(last_q-first_q)
  m2=(x<<last_q)//np.left_shift(np.int64(1),2*k)
  y2=refine(shifted,m2,last_q)
  actual=y2.astype(float)/(1<<last_q)/np.left_shift(np.int64(1),k)
  err=np.abs(actual-target)/target
  j=int(np.argmax(err))
  if err[j]>worst:worst=float(err[j]);at=int(x[j])
  bad+=int(np.count_nonzero(err>=EPS))
 return {"segments":segments,"style":style,"coefficient_constants":2*segments,
         "nominal_selector_bits":(segments-1).bit_length(),
         "fixed_constant_multiply_stages":1,
         "Newton_variable_multiply_stages":6,
         "seed_worst_relative_error":seed_worst,"seed_worst_x":seed_at,
         "final_worst_relative_error":worst,"final_tolerance_fraction":worst/EPS,
         "worst_x":at,"violations":bad}
def lut_baseline(xs,first_q,last_q,chunk):
 l=lookup(first_q);s=1<<first_q
 worst=0.;bad=0
 for start in range(0,len(xs),chunk):
  x=xs[start:start+chunk]
  e=np.frexp(x.astype(float))[1]-1;k=e//2
  m=(x<<first_q)//np.left_shift(np.int64(1),2*k)
  ix=np.where(m<2*s,((m-s)*32)//s,32+((m-2*s)*32)//(2*s))
  y1=refine(l[ix],m,first_q)
  y2=refine(y1<<(last_q-first_q),(x<<last_q)//np.left_shift(np.int64(1),2*k),last_q)
  ref=1/np.sqrt(x.astype(float))
  err=np.abs(y2.astype(float)/(1<<last_q)/np.left_shift(np.int64(1),k)-ref)/ref
  worst=max(worst,float(err.max()));bad+=int(np.count_nonzero(err>=EPS))
 return {"seed_table_entries":64,"first_q":first_q,"last_q":last_q,
         "violations":bad,"worst_tolerance_fraction":worst/EPS}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--baseline",type=Path,default=Path("competition/k098/results/helios_immutable.kmx"))
 p.add_argument("--out",type=Path,default=Path("competition/k159/results/log_seed.json"))
 p.add_argument("--max-x",type=int,default=N)
 p.add_argument("--first-q",type=int,default=14)
 p.add_argument("--last-q",type=int,default=26)
 p.add_argument("--segments",default="2,4,8,16")
 p.add_argument("--styles",default="chord,midpoint")
 p.add_argument("--chunk",type=int,default=100000)
 p.add_argument("--selftest",action="store_true")
 a=p.parse_args()
 if not(1<=a.max_x<=N and 10<=a.first_q<=a.last_q<=30 and a.chunk>=100):p.error("bad bounds")
 # Rounded Q14 coefficient lines; no floating point arithmetic in the quantum-side model.
 xs0=np.arange(1,2000,dtype=np.int64)
 ref=lut_baseline(xs0,14,26,2000)
 assert ref["violations"]==0
 assert all(len(line_coeff(14,n,"chord"))==n for n in (2,4,8))
 print("K159_SELFTEST PASS affine coefficient generation and integer Newton stages",flush=True)
 if a.selftest:return
 sha=hashlib.sha256(a.baseline.read_bytes()).hexdigest()
 if sha!=PIN:raise SystemExit("PINNED_BASELINE_MISMATCH "+sha)
 ns=sorted(set(map(int,a.segments.split(","))))
 styles=sorted(set(s.strip() for s in a.styles.split(",")))
 if any(n<2 or n&(n-1) or n>256 for n in ns) or any(x not in ("chord","midpoint") for x in styles):p.error("invalid segments/styles")
 xs=np.arange(1,a.max_x+1,dtype=np.int64)
 baseline=lut_baseline(xs,a.first_q,a.last_q,a.chunk)
 rows=[]
 for n in ns:
  for style in styles:
   row=screen(xs,a.first_q,a.last_q,n,style,a.chunk);rows.append(row)
   print("K159_CASE",json.dumps(row),flush=True)
 wins=[r for r in rows if r["violations"]==0]
 result={"status":"NUMERIC_LOG_LINEAR_SEED_ONLY_NOT_REVERSIBLE_CIRCUIT",
         "pinned_sha256":sha,"tested_input_count":a.max_x,
         "reference_K149_Q14_LUT64":baseline,"rows":rows,
         "lowest_coefficients_numerical_pass":min(wins,key=lambda r:r["coefficient_constants"]) if wins else None,
         "warnings":["Piecewise affine seed requires a SELECTOR, two constant lookups and a variable-by-constant multiply.",
           "Not the original IEEE-754 magic constant and not a full log2 hardware circuit.",
           "A smaller coefficient table is NOT automatically cheaper than a 64-value lookup; interpolation has arithmetic cost.",
           "Floating oracle for tolerance; fixed-point integer candidate; no quantum compute/uncompute or official verifier.",
           "Prior K117–K123 tried polynomial approximate methods; this isolates linearized seed only."]}
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+"\n")
 print("K159_RESULT",json.dumps({"cases":len(rows),"passes":len(wins),
    "reference":baseline,
    "best":{"segments":wins[0]["segments"],"style":wins[0]["style"],
      "worst_fraction":wins[0]["final_tolerance_fraction"]} if wins else None,
    "out":str(a.out)}),flush=True)
if __name__=="__main__":main()
