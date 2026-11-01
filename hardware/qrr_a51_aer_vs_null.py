#!/usr/bin/env python3
"""A51 analyze genuine A50 Aer readouts versus independent A49 null controls.

Never uses the known order to recover factors; order is diagnostic only.
A simulated quantum circuit is not a QPU. No speedup claim.
"""
import argparse,json,math
from pathlib import Path
def read(path):return json.loads(Path(path).read_text())
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--aer",default="results/a51_n437_aer8.json")
 p.add_argument("--null",default="results/a49_phase_frequency_replication.json")
 p.add_argument("--output",default="results/a51_n437_aer_vs_null.json")
 a=p.parse_args()
 aer=read(a.aer)
 if aer.get("status")!="PASS_ACTUAL_AER_MEASUREMENTS_POSTPROCESSED" or not aer.get("actual_Aer_measured_readouts"):
  raise SystemExit("FAIL: missing completed actual Aer measurements")
 if (aer.get("n"),aer.get("base"),aer.get("bits"))!=(437,8,18):
  raise SystemExit("FAIL: Aer parameters do not match A49 reference")
 shots=aer["readouts"]
 if len(shots)<2:raise SystemExit("FAIL: need multiple measured shots")
 null=read(a.null)
 rows=[r for r in null["rows"] if r["n"]==437 and r["bits"]==18 and r["cohort"]=="uniform_random" and r.get("status")=="COMPLETE"]
 if not rows:raise SystemExit("FAIL: missing completed A49 control rows")
 nnull=sum(len(r["cases"]) for r in rows)
 knull=sum(sum(x.get("factors") is not None for x in r["cases"]) for r in rows)
 p0=knull/nnull
 outcomes=[]
 for shot in shots:
  freq=shot["frequency"];post=shot["ekera"]
  assert freq==int(shot["measured_bitstring"].replace(" ",""),2)
  if post.get("factors") is not None:assert math.prod(post["factors"])==437
  # This diagnostics-only reference must not be passed to Quaspy.
  order=66;Q=1<<18
  dist=min(abs(freq-k*Q/order) for k in range(order+1))
  outcomes.append({"frequency":freq,"factors":post.get("factors"),
      "candidate_exponent":post.get("candidate_exponent"),
      "distance_to_nearest_ideal_order_peak":round(dist,4)})
 k=sum(x["factors"] is not None for x in outcomes);n=len(outcomes)
 tail=sum(math.comb(n,i)*p0**i*(1-p0)**(n-i) for i in range(k,n+1))
 result={"experiment":"A51_AER8_VS_A49_NULL","status":"COMPLETE_ANALYSIS",
  "measurement_provenance":"Aer noiseless circuit simulation; no QPU",
  "control_provenance":"A49 independent uniform random frequencies",
  "n":437,"base":8,"bits":18,"Aer_shots":n,"Aer_verified_factors":k,
  "Aer_success_rate":k/n,"A49_null_successes":knull,"A49_null_trials":nnull,
  "A49_null_rate":p0,"one_sided_binomial_tail_conditional_on_null_rate":tail,
  "interpretation":"Exploratory small-sample comparison. Null rate estimated, not fixed; this test does not prove quantum advantage or circuit correctness.",
  "shots":outcomes}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,indent=2)+"\n")
 print("A51 N437 18-bit Aer",k,"/",n,"null",knull,"/",nnull,
       "one-sided exploratory p",round(tail,6))
 print("A51 SAVED",out)
if __name__=="__main__":main()
