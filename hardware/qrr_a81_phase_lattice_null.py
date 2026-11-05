#!/usr/bin/env python3
"""A81: strict QPE phase-lattice enrichment vs exact uniform-frequency null.

The multiplicative order is computed classically for *diagnostic labeling only*;
it is not supplied to circuit construction or factor postprocessing. A phase
bin is a hit when <= tolerance integer frequency bins from some s/r (mod 1).
Reports exact null probability by scanning all possible readout frequencies.
Two shots cannot establish reliable QPE distribution agreement.
"""
import argparse,json,math,time
from pathlib import Path

def order_mod(n,base,limit):
 value=1
 for r in range(1,limit+1):
  value=(value*base)%n
  if value==1:return r
 raise ValueError("Order exceeds supplied safe diagnostic bound")

def distance_to_lattice(freq,scale,r):
 # |freq/scale - k/r| on the circle, expressed in frequency bins;
 # exact integer numerator avoids float rounding near a peak.
 t=(freq*r)%scale
 numerator=min(t,scale-t)
 return numerator/r

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--n",type=int,required=True)
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--bits",type=int,default=16)
 p.add_argument("--frequencies",nargs="+",type=int,required=True)
 p.add_argument("--tolerance-bins",type=float,default=1.0)
 p.add_argument("--output",required=True)
 a=p.parse_args()
 if not 1<=a.bits<=20 or not 0<=a.tolerance_bins<=10:p.error("bits 1..20; tolerance bins 0..10")
 if math.gcd(a.n,a.base)!=1:p.error("base must be coprime to N")
 scale=1<<a.bits
 if any(f<0 or f>=scale for f in a.frequencies):p.error("frequency out of range")
 start=time.perf_counter()
 r=order_mod(a.n,a.base,a.n)
 distance=lambda f:distance_to_lattice(f,scale,r)
 null_hits=sum(distance(f)<=a.tolerance_bins for f in range(scale))
 observed=[{"frequency":f,"distance_bins":distance(f),
            "phase_lattice_hit":distance(f)<=a.tolerance_bins} for f in a.frequencies]
 hits=sum(v["phase_lattice_hit"] for v in observed)
 rate=null_hits/scale
 d={"experiment":"A81_PHASE_LATTICE_DIAGNOSTIC",
    "n":a.n,"base":a.base,"bits":a.bits,"diagnostic_order":r,
    "order_source":"classical repeated multiplication for evaluation only; not an oracle in QPE",
    "tolerance_bins":a.tolerance_bins,
    "uniform_null_hits":null_hits,"uniform_null_count":scale,"uniform_null_rate":rate,
    "observations":observed,"observed_hits":hits,"observed_shots":len(observed),
    "independent_uniform_null_probability_all_hits":rate**len(observed) if hits==len(observed) else None,
    "status":"PASS_EXACT_PHASE_LATTICE_NULL",
    "caveats":["Null model is uniformly random classical bits, not a hardware noise model",
       "Shots may be correlated by circuit/simulator sampling",
       "Phase lattice can show strong enrichment even when continued fractions cannot recover factors",
       "This test alone does not establish quantum speedup or general purpose factoring"],
    "elapsed_seconds":round(time.perf_counter()-start,3)}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(d,indent=2)+"\n")
 print(f"A81 N={a.n} order={r} null={null_hits}/{scale} ({rate:.6%}) measured_hits={hits}/{len(observed)}",flush=True)
 for row in observed:print("A81 FREQUENCY",row,flush=True)
 print("A81 STATUS",d["status"],flush=True)
if __name__=="__main__":main()
