#!/usr/bin/env python3
"""A80 exact uniform-frequency null control for the A79 postprocessor.

Enumerates all phase-bit frequencies (up to 20 bits) using the SAME bounded
continued fraction + <=4 multiple recovery logic as A79. This does NOT
simulate a QPU or establish quantum advantage. Factors are used only to
validate the candidate product after recovery; they are not supplied as input.
"""
import argparse,json,math,time
from fractions import Fraction
from pathlib import Path

def recover(n,base,bits,freq,multiples):
 if freq==0:return None
 denominator=Fraction(freq,1<<bits).limit_denominator(n).denominator
 for multiple in range(1,multiples+1):
  order=multiple*denominator
  if order%2 or pow(base,order,n)!=1:continue
  half=pow(base,order//2,n)
  if half in (1,n-1):continue
  p,q=math.gcd(half-1,n),math.gcd(half+1,n)
  if 1<p<n and 1<q<n and p*q==n:return sorted((p,q))
 return None

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,default=247)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=16)
 p.add_argument("--multiples",type=int,default=4)
 p.add_argument("--observed",nargs="*",type=int,default=[32768,32768])
 p.add_argument("--output",default="results/a80_n247_random_control.json")
 a=p.parse_args()
 if not 1<=a.bits<=20:p.error("bits 1..20 for exact enumeration")
 if not 1<=a.multiples<=32:p.error("multiples 1..32")
 if math.gcd(a.n,a.base)!=1:p.error("coprime base required")
 if any(not 0<=v<1<<a.bits for v in a.observed):p.error("observed frequencies outside register")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 start=time.perf_counter();total=1<<a.bits
 wins=sum(recover(a.n,a.base,a.bits,f,a.multiples) is not None for f in range(total))
 observed=[{"frequency":f,"candidate_denominator":Fraction(f,total).limit_denominator(a.n).denominator if f else 1,
            "factors":recover(a.n,a.base,a.bits,f,a.multiples)} for f in a.observed]
 report={"experiment":"A80_EXACT_UNIFORM_FREQUENCY_NULL","n":a.n,"base":a.base,"bits":a.bits,
  "max_multiples":a.multiples,"null_frequency_count":total,"null_successes":wins,
  "null_success_rate":wins/total,"observed":observed,
  "observed_successes":sum(x["factors"] is not None for x in observed),
  "elapsed_seconds":round(time.perf_counter()-start,3),
  "status":"PASS_EXACT_NULL_CONTROL",
  "scope":"Exact uniform-frequency null for same postprocessing only. Not a physical noise model or a significance test of independent hardware samples."}
 out.write_text(json.dumps(report,indent=2)+"\n")
 print("A80",report["status"],"uniform",wins,"/",total,
   "rate",round(wins/total,6),"observed",report["observed_successes"],"/",len(observed),
   "seconds",report["elapsed_seconds"],flush=True)

if __name__=="__main__":main()
