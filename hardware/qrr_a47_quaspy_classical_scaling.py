#!/usr/bin/env python3
"""A47: bounded classical-only Quaspy scaling with independent null controls.

Uses the pinned Quaspy adapter in A46. Records worker errors separately from
mathematical failure, hard timeouts, wall time, max RSS (Linux child rusage),
and per-case reproducible frequencies. Informed samples use known order and
are ORACLE-LABELED, not quantum observations. No QPU.
"""
import argparse,json,math,random,resource,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def order(a,n):
 v=1
 for r in range(1,n+1):
  v=v*a%n
  if v==1:return r
 raise RuntimeError("order not found")

def call(n,base,bits,freq,method,budget,seconds,upstream,wall):
 args=[n,base,bits,freq,method,budget,seconds,upstream]
 cmd=[sys.executable,str(Path(__file__).resolve()),"--worker",json.dumps(args)]
 t=time.perf_counter()
 try:
  r=subprocess.run(cmd,capture_output=True,text=True,timeout=wall)
  elapsed=time.perf_counter()-t
  if r.returncode:
   return {"status":"ERROR","success":False,"wall_s":round(elapsed,4),
           "error":r.stderr[-900:]}
  data=json.loads(r.stdout)
  factors=data.get("factors")
  if factors is not None:assert math.prod(factors)==n
  return {"status":data["status"],"success":factors is not None,
          "wall_s":round(elapsed,4),"ledger":data["ledger"]}
 except subprocess.TimeoutExpired:
  return {"status":"HARD_TIMEOUT","success":False,"wall_s":wall}
 except Exception as e:
  return {"status":"ERROR","success":False,"wall_s":round(time.perf_counter()-t,4),"error":repr(e)}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--worker")
 p.add_argument("--moduli",nargs="+",type=int,default=[143,221,323,437,667,899,1147,1763,2491])
 p.add_argument("--base",type=int,default=8)
 p.add_argument("--random-samples",type=int,default=12)
 p.add_argument("--informed-samples",type=int,default=6)
 p.add_argument("--budget",type=int,default=1000)
 p.add_argument("--timeout",type=int,default=2)
 p.add_argument("--wall-timeout",type=float,default=5)
 p.add_argument("--seed",type=int,default=20261031)
 p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
 p.add_argument("--output",default="results/a47_quaspy_classical_scaling.json")
 a=p.parse_args()
 if a.worker is not None:
  n,b,bits,freq,method,budget,lim,upstream=json.loads(a.worker)
  if method=="ekera":post.load_upstream(upstream)
  print(json.dumps(post.recover(n,b,bits,freq,method=method,budget=budget,timeout=lim)))
  return
 if not 1<=a.random_samples<=100 or not 1<=a.informed_samples<=100:p.error("bad sample count")
 if a.timeout<1 or a.wall_timeout<=a.timeout:p.error("wall timeout must exceed positive integer internal timeout")
 if a.budget<1:p.error("budget must be positive")
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 result={"experiment":"A47_BOUNDED_CLASSICAL_QUASPY_SCALING",
   "status":"IN_PROGRESS","qpu_jobs":0,"quantum_measurements":0,
   "frequency_provenance":"uniform random, zero/one, classically order-informed oracle",
   "limitation":"Process max RSS is tracked as cumulative child max (Linux), not exact per-call RSS; latency includes worker startup. Classical order for positive controls is excluded from recovery timing.",
   "rows":[]}
 def save():out.write_text(json.dumps(result,indent=2)+"\n")
 save()
 rng=random.Random(a.seed)
 for n in a.moduli:
  if n<9 or n%2==0 or math.gcd(a.base,n)!=1:
   print("A47 SKIP",n,"not an odd unit base",flush=True)
   continue
  bits=n.bit_length()+1
  r=order(a.base,n)
  Q=1<<bits
  cohorts={"uniform_random":[rng.randrange(Q) for _ in range(a.random_samples)],
   "constant_zero":[0],"constant_one":[1],
   "oracle_order_peaks_NOT_MEASURED":[round(rng.randrange(r)*Q/r)%Q for _ in range(a.informed_samples)]}
  for label,values in cohorts.items():
   cases=[]
   for freq in values:
    data=call(n,a.base,bits,freq,"ekera",a.budget,a.timeout,a.upstream,a.wall_timeout)
    cases.append({"frequency":freq,**data})
    if data["status"]=="ERROR":
     result["status"]="FAIL_WORKER_ERROR";save()
     raise RuntimeError(f"N={n}, cohort={label}: {data.get('error')}")
   row={"n":n,"base":a.base,"bits":bits,"budget":a.budget,
    "cohort":label,"samples":len(cases),
    "successes":sum(x["success"] for x in cases),
    "hard_timeouts":sum(x["status"]=="HARD_TIMEOUT" for x in cases),
    "work_limits":sum(x["status"]=="WORK_LIMIT" for x in cases),
    "total_wall_s":round(sum(x["wall_s"] for x in cases),3),
    "mean_wall_s":round(sum(x["wall_s"] for x in cases)/len(cases),4),
    "cumulative_child_maxrss_kb":resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
    "cases":cases}
   result["rows"].append(row);save()
   print("A47",n,label,"success",row["successes"],"/",row["samples"],
     "hard_timeout",row["hard_timeouts"],"mean_s",row["mean_wall_s"],flush=True)
 result["status"]="PASS_CLASSICAL_SCALING_LEDGER_NO_QUANTUM_CLAIM"
 save();print("A47 STATUS",result["status"],"SAVED",out,flush=True)
if __name__=="__main__":main()
