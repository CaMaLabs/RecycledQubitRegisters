#!/usr/bin/env python3
"""A48: phase-precision/parameter audit of pinned Quaspy adapter.

Quantum measurements are NOT used. Oracle peak frequencies are computed from
the exact classical order and labeled as positive controls. Each Quaspy run
executes in its own hard-timeout process; errors never count as mathematical
failures. Distinguish recovered exponent, verified factors, and failure.
"""
from __future__ import annotations
import argparse,json,math,random,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def order(a,n):
 x=1
 for r in range(1,n+1):
  x=x*a%n
  if x==1:return r
 raise ValueError("order unavailable")

def run_worker(payload,wall):
 cmd=[sys.executable,str(Path(__file__).resolve()),"--worker",json.dumps(payload)]
 t=time.perf_counter()
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=wall)
  if p.returncode:
   return {"status":"ERROR","error":p.stderr[-1200:],"wall_s":round(time.perf_counter()-t,4)}
  d=json.loads(p.stdout)
  return {"status":d["status"],"candidate_exponent":d["candidate_exponent"],
          "factors":d["factors"],"ledger":d["ledger"],
          "wall_s":round(time.perf_counter()-t,4)}
 except subprocess.TimeoutExpired:
  return {"status":"HARD_TIMEOUT","wall_s":wall}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--worker",type=str)
 p.add_argument("--moduli",nargs="+",type=int,default=[437,667,2491])
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--random-samples",type=int,default=12)
 p.add_argument("--informed-samples",type=int,default=12)
 p.add_argument("--budgets",nargs="+",type=int,default=[1000,100000])
 p.add_argument("--timeout",type=int,default=2)
 p.add_argument("--wall-timeout",type=float,default=5)
 p.add_argument("--seed",type=int,default=20261031)
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--output",default="results/a48_precision_recovery_audit.json")
 a=p.parse_args()
 if a.worker is not None:
  d=json.loads(a.worker)
  if d["method"]=="ekera":post.load_upstream(d["upstream"])
  print(json.dumps(post.recover(d["n"],d["base"],d["bits"],d["frequency"],
    method=d["method"],budget=d["budget"],timeout=d["timeout"])))
  return
 if not 1<=a.random_samples<=128 or not 1<=a.informed_samples<=128:p.error("invalid samples")
 if not 1<=a.timeout<a.wall_timeout<=60:p.error("invalid timeouts")
 rng=random.Random(a.seed)
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 report={"experiment":"A48_QUASPY_PRECISION_SWEEP","status":"IN_PROGRESS",
   "qpu_jobs":0,"quantum_measurements":0,
   "controls":"uniform random vs classically exact-order oracle peaks, not hardware",
   "rows":[]}
 def save():out.write_text(json.dumps(report,indent=2)+"\n")
 save()
 for n in a.moduli:
  if n%2==0 or n<9 or math.gcd(a.base,n)!=1:
   print("SKIP",n,"nonunit/invalid",flush=True);continue
  m=n.bit_length()
  r=order(a.base,n)
  for bits in range(m+1,2*m+1):
   Q=1<<bits
   # Distinct randomized streams for each precision; same case frequencies
   # passed to all budget/method arms at that precision.
   cohorts={
    "uniform_random":[rng.randrange(Q) for _ in range(a.random_samples)],
    "oracle_peaks_NOT_MEASURED":[round(rng.randrange(r)*Q/r)%Q for _ in range(a.informed_samples)],
    "constant_zero":[0]
   }
   for label,values in cohorts.items():
    for budget in a.budgets:
     cases=[]
     for freq in values:
      entry={"frequency":freq}
      for method in ("cf","ekera"):
       payload={"n":n,"base":a.base,"bits":bits,"frequency":freq,
                "method":method,"budget":budget,"timeout":a.timeout,
                "upstream":a.upstream}
       result=run_worker(payload,a.wall_timeout)
       if result["status"]=="ERROR":
        report["status"]="FAIL_WORKER_ERROR";report["error"]=result["error"]
        save();raise RuntimeError(result["error"])
       if result.get("factors") is not None:assert math.prod(result["factors"])==n
       entry[method]=result
      cases.append(entry)
     row={"n":n,"base":a.base,"true_order_reference_only":r,"bits":bits,
      "budget":budget,"cohort":label,"samples":len(cases),
      "cf_verified_exponent":sum(x["cf"].get("candidate_exponent") is not None for x in cases),
      "ekera_verified_exponent":sum(x["ekera"].get("candidate_exponent") is not None for x in cases),
      "cf_factors":sum(x["cf"].get("factors") is not None for x in cases),
      "ekera_factors":sum(x["ekera"].get("factors") is not None for x in cases),
      "ekera_work_limits":sum(x["ekera"]["status"]=="WORK_LIMIT" for x in cases),
      "ekera_hard_timeouts":sum(x["ekera"]["status"]=="HARD_TIMEOUT" for x in cases),
      "ekera_mean_wall_s":round(sum(x["ekera"]["wall_s"] for x in cases)/len(cases),4),
      "cases":cases}
     report["rows"].append(row);save()
     print("A48 N",n,"bits",bits,"budget",budget,label,
       "Eorder",row["ekera_verified_exponent"],"Efactors",row["ekera_factors"],
       "/",len(cases),flush=True)
 report["status"]="PASS_PRECISION_NULL_AND_ORACLE_SWEEP"
 save();print("A48 STATUS",report["status"],"SAVED",out,flush=True)
if __name__=="__main__":main()
