#!/usr/bin/env python3
"""A46: Quaspy classical-only limitation / frequency-information controls.

Every recovery is isolated in a subprocess with hard wall timeout. "informed"
frequencies use an independently computed classical multiplicative order ONLY
to create an oracle-labeled positive control; these are NOT QPU or Aer shots.
No performance or quantum-advantage claim follows from those controls.
"""
from __future__ import annotations
import argparse,json,math,random,subprocess,sys,time
from pathlib import Path

def exact_order(a,n):
 if math.gcd(a,n)!=1:raise ValueError("nonunit base")
 x=1
 for r in range(1,n+1):
  x=x*a%n
  if x==1:return r
 raise AssertionError("no order")

def one_worker(argv):
 from integrations.darkstar_hybrid import quaspy_public_postprocess as post
 n,base,bits,freq,method,budget,limit,upstream=argv
 if method=="ekera":post.load_upstream(upstream)
 return post.recover(n,base,bits,freq,method=method,budget=budget,timeout=limit)

def invoke_worker(args,wall):
 cmd=[sys.executable,str(Path(__file__).resolve()),"--worker",json.dumps(args)]
 start=time.perf_counter()
 try:
  cp=subprocess.run(cmd,capture_output=True,text=True,timeout=wall,check=False)
  dt=time.perf_counter()-start
  if cp.returncode: return {"status":"ERROR","error":cp.stderr[-600:],"seconds":round(dt,4),"success":False}
  obj=json.loads(cp.stdout)
  pair=obj.get("factors")
  return {"status":obj["status"],"success":pair is not None,
    "factors":pair,"seconds":round(dt,4),"ledger":obj["ledger"]}
 except subprocess.TimeoutExpired:
  return {"status":"HARD_TIMEOUT","success":False,"seconds":wall}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--worker",default=None,help=argparse.SUPPRESS)
 p.add_argument("--moduli",nargs="+",type=int,default=[143,221,323,437,667])
 p.add_argument("--base",type=int,default=2)
 p.add_argument("--random-samples",type=int,default=12)
 p.add_argument("--informed-samples",type=int,default=6)
 p.add_argument("--budgets",nargs="+",type=int,default=[1000,100000])
 p.add_argument("--timeout",type=float,default=2.0)
 p.add_argument("--wall-timeout",type=float,default=4.0)
 p.add_argument("--seed",type=int,default=20261031)
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--output",default="results/a46_quaspy_classical_limit.json")
 a=p.parse_args()
 if a.worker is not None:
  print(json.dumps(one_worker(json.loads(a.worker))))
  return
 if not(1<=a.random_samples<=128 and 1<=a.informed_samples<=128):p.error("sample counts 1..128")
 if not(0<a.timeout<a.wall_timeout and a.wall_timeout<=60):p.error("require 0 < timeout < wall-timeout <= 60")
 if any(b<1 for b in a.budgets):p.error("budget must be positive")
 rng=random.Random(a.seed)
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 result={"experiment":"A46_QUASPY_CLASSICAL_ONLY_SCALING","status":"IN_PROGRESS",
 "no_quantum_samples_generated":True,"oracle_informed_positive_control_only":True,
 "upstream":a.upstream,"rows":[]}
 def save():out.write_text(json.dumps(result,indent=2)+"\n")
 save()
 for n in a.moduli:
  if n<9 or n%2==0 or math.gcd(a.base,n)!=1:
   print("SKIP non-coprime/non-odd",n,flush=True);continue
  bits=n.bit_length()+1
  order=exact_order(a.base,n)
  Q=1<<bits
  # Fourier peak locations derived from *known* order: positive controls only.
  informed=[round(k*Q/order)%Q for k in
      [rng.randrange(order) for _ in range(a.informed_samples)]]
  cohorts={"uniform_random":[rng.randrange(Q) for _ in range(a.random_samples)],
           "constant_zero":[0],
           "constant_one":[1],
           "oracle_order_peaks_NOT_MEASURED":informed}
  for budget in a.budgets:
   for label,values in cohorts.items():
    cases=[]
    for freq in values:
     row={"frequency":freq}
     for method in ("cf","ekera"):
      params=[n,a.base,bits,freq,method,budget,a.timeout,a.upstream]
      res=invoke_worker(params,a.wall_timeout)
      if res.get("factors") is not None:assert math.prod(res["factors"])==n
      row[method]=res
     cases.append(row)
    summary={"n":n,"base":a.base,"bits":bits,"budget_proxy":budget,
      "cohort":label,"samples":len(cases),
      "cf_success":sum(x["cf"]["success"] for x in cases),
      "quaspy_success":sum(x["ekera"]["success"] for x in cases),
      "cf_hard_timeouts":sum(x["cf"]["status"]=="HARD_TIMEOUT" for x in cases),
      "quaspy_hard_timeouts":sum(x["ekera"]["status"]=="HARD_TIMEOUT" for x in cases),
      "cf_total_wall_s":round(sum(x["cf"]["seconds"] for x in cases),3),
      "quaspy_total_wall_s":round(sum(x["ekera"]["seconds"] for x in cases),3),
      "cases":cases}
    result["rows"].append(summary);save()
    print("A46",n,budget,label,"n",len(cases),"CF",summary["cf_success"],
      "QUASPY",summary["quaspy_success"],"Q_timeout",summary["quaspy_hard_timeouts"],flush=True)
 result["status"]="PASS_CLASSICAL_NULL_AND_ORACLE_CONTROL_LEDGER"
 save();print("A46 STATUS",result["status"],"SAVED",out,flush=True)
if __name__=="__main__":main()
