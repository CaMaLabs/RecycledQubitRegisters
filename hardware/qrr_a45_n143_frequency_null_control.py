#!/usr/bin/env python3
"""A45: falsification control for Quaspy N143 measured-frequency advantage.

Compare actual A42 quantum measurements to uniform random and fixed-frequency
null inputs using the identical public-only recovery adapter. A 100% success
rate on random frequencies invalidates attributing recovery to quantum data.
"""
import argparse,json,random,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",default="results/a42_n143_reproducibility.json")
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--random-samples",type=int,default=128)
 p.add_argument("--seed",type=int,default=20261031)
 p.add_argument("--output",default="results/a45_frequency_null_control.json")
 a=p.parse_args()
 if not 1<=a.random_samples<=2048:p.error("random-samples out of range")
 src=json.loads(Path(a.input).read_text())
 assert src["status"]=="PASS_REPEATED_ACTUAL_AER_MEASUREMENT_LEDGER" and src["n"]==143
 n,base,bits=143,src["base"],src["bits"]
 rng=random.Random(a.seed)
 cohorts={
  "actual_Aer":[int(r["frequency"]) for r in src["rows"]],
  "uniform_random":[rng.randrange(1<<bits) for _ in range(a.random_samples)],
  "constant_zero":[0]*len(src["rows"]),
  "constant_one":[1]*len(src["rows"]),
  "constant_middle":[1<<(bits-1)]*len(src["rows"])
 }
 post.load_upstream(a.upstream)
 result={"experiment":"A45_QUASPY_FREQUENCY_NULL_CONTROL","n":n,"base":base,
  "bits":bits,"qpu_jobs":0,"sample_sources":{"actual_Aer":"recorded A42 gate-level",
  "uniform_random":"local random integers, not quantum",
  "constant_*":"deliberately uninformative frequencies"},"cohorts":{}}
 for name,values in cohorts.items():
  cases=[]
  for freq in values:
   row={"frequency":freq}
   for method in ("cf","ekera"):
    r=post.recover(n,base,bits,freq,method=method,budget=100000,timeout=3)
    factors=r["factors"]
    if factors is not None:assert math.prod(factors)==n
    row[method]={"success":factors is not None,"status":r["status"],
     "pow_calls":r["ledger"]["pow_calls"]}
   cases.append(row)
  result["cohorts"][name]={
   "count":len(cases),"cf_successes":sum(x["cf"]["success"] for x in cases),
   "quaspy_successes":sum(x["ekera"]["success"] for x in cases),
   "cf_pow_calls":sum(x["cf"]["pow_calls"] for x in cases),
   "quaspy_pow_calls":sum(x["ekera"]["pow_calls"] for x in cases),
   "cases":cases}
  s=result["cohorts"][name]
  print(name,"n",s["count"],"CF",s["cf_successes"],"Quaspy",s["quaspy_successes"],flush=True)
 result["interpretation_gate"]="Compare quantum recovery against null frequency success, not just CF."
 result["status"]="PASS_NULL_CONTROL_MEASURED"
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,indent=2)+"\n")
 print("SAVED",out)
if __name__=="__main__":main()
