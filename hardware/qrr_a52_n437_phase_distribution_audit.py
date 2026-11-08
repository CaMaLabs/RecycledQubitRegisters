#!/usr/bin/env python3
"""A52 independent N437 phase-distribution check with reproducible null Monte Carlo.

Reads A51 actual Aer frequencies. Oracle true order is used ONLY for evaluation,
not factoring; no claim of physical QPU runs, quantum speedup, or statistical
independence of output shots. Rejects incorrectly registered frequency bit order
by reporting direct-vs-reversed geometry. Does not replace separate modular-gate
basis validation.
"""
import argparse,json,math,random,statistics
from pathlib import Path

def bitrev(v,bits):
 return int(f"{v:0{bits}b}"[::-1],2)

def nearest(v,Q,r):
 return min(abs(v-k*Q/r) for k in range(r+1))

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--aer",default="results/a51_n437_aer8.json")
 p.add_argument("--null",default="results/a49_phase_frequency_replication.json")
 p.add_argument("--draws",type=int,default=100000)
 p.add_argument("--seed",type=int,default=20261103)
 p.add_argument("--output",default="results/a52_n437_phase_distribution.json")
 a=p.parse_args()
 d=json.loads(Path(a.aer).read_text())
 if d.get("status")!="PASS_ACTUAL_AER_MEASUREMENTS_POSTPROCESSED" or not d.get("actual_Aer_measured_readouts"):
  raise SystemExit("A52 FAIL: no actual Aer memory in result")
 n,base,bits=d["n"],d["base"],d["bits"]
 if (n,base,bits)!=(437,8,18):raise SystemExit("A52 FAIL: unexpected circuit target")
 order=66;Q=1<<bits
 if pow(base,order,n)!=1 or any(pow(base,order//p,n)==1 for p in [2,3,11]):
  raise SystemExit("A52 FAIL: reference multiplicative order not verified")
 shots=d["readouts"]
 if len(shots)<8:raise SystemExit("A52 FAIL: fewer than eight measured shots")
 vals=[x["frequency"] for x in shots]
 for x in shots:
  if x["frequency"]!=int(x["measured_bitstring"].replace(" ",""),2):raise SystemExit("A52 FAIL: bitstring disagreement")
 def stats(values):
  ds=[nearest(x,Q,order) for x in values]
  return {"samples":len(values),"mean_peak_distance":statistics.mean(ds),
   "median_peak_distance":statistics.median(ds),"within_half_bin":sum(v<=.5 for v in ds),
   "within_one_bin":sum(v<=1 for v in ds),"within_two_bins":sum(v<=2 for v in ds),
   "distances":[round(v,5) for v in ds]}
 direct=stats(vals)
 reversed_stats=stats([bitrev(x,bits) for x in vals])
 rng=random.Random(a.seed)
 null=[rng.randrange(Q) for _ in range(a.draws)]
 null_dist=[nearest(v,Q,order) for v in null]
 observed=direct["mean_peak_distance"]
 # Estimate how often a null batch of the same size matches the observed mean.
 # Exact event: each frequency iid uniform over 0..2^bits-1, NOT Quaspy recovery.
 count=0
 for _ in range(max(1,a.draws//len(vals))):
  if statistics.mean(rng.choice(null_dist) for _ in vals)<=observed:count+=1
 batches=max(1,a.draws//len(vals))
 result={"experiment":"A52_INDEPENDENT_ORDER66_PHASE_GEOMETRY",
  "status":"COMPLETE_DISTRIBUTION_DIAGNOSTIC","source":a.aer,"n":n,"base":base,
  "bits":bits,"reference_order_diagnostic_only":order,
  "actual_measurements":"Aer simulation, not QPU",
  "direct_frequency_geometry":direct,"bit_reversed_frequency_geometry":reversed_stats,
  "uniform_frequency_null":{"draws":a.draws,"mean_peak_distance":statistics.mean(null_dist),
   "within_half_bin_rate":sum(v<=.5 for v in null_dist)/a.draws,
   "within_one_bin_rate":sum(v<=1 for v in null_dist)/a.draws,
   "batch_mean_tail_p_monte_carlo":(count+1)/(batches+1),
   "batch_count":batches},
  "warnings":["Eight shots are insufficient to establish full Fourier spectral shape.",
   "Zero peak distance is not required for correct finite-precision QPE.",
   "A separate circuit correctness test must verify the modular gate source and feedback signs."]}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,indent=2)+"\n")
 print("A52 order",order,"direct mean distance",round(direct["mean_peak_distance"],4),
       "reversed",round(reversed_stats["mean_peak_distance"],4),
       "null",round(result["uniform_frequency_null"]["mean_peak_distance"],4),
       "null batch p",result["uniform_frequency_null"]["batch_mean_tail_p_monte_carlo"])
 print("A52 STATUS",result["status"],"SAVED",out)
if __name__=="__main__":main()
