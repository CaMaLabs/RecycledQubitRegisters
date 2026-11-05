#!/usr/bin/env python3
"""A49: preregistered replication of A48 phase-frequency separation.

Null=independent uniform phase frequencies; positive control=classically
known-order rounded peaks (NOT quantum measurements). Matched N/base/bits,
same adapter, internal budget and subprocess wall limit. Independent seed
cohorts and per-sample durable output. No quantum advantage claim.
"""
import argparse, json, math, random, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"hardware"))
from qrr_a48_quaspy_precision_sweep import order, run_worker

def wilson(k,n,z=1.96):
    p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return [round(c-h,4),round(c+h,4)]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--samples",type=int,default=64)
    p.add_argument("--seeds",nargs="+",type=int,default=[20261101,20261102])
    p.add_argument("--budget",type=int,default=1000)
    p.add_argument("--timeout",type=int,default=2)
    p.add_argument("--wall-timeout",type=float,default=5)
    p.add_argument("--base",type=int,default=8)
    p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
    p.add_argument("--output",default="results/a49_phase_frequency_replication.json")
    a=p.parse_args()
    if not 1<=a.samples<=512 or not 1<=len(a.seeds)<=12:p.error("invalid cohort size")
    if not 1<=a.timeout<a.wall_timeout<=60:p.error("invalid timeouts")
    cases=[(437,18),(667,20)]
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    report={"experiment":"A49_INDEPENDENT_PHASE_FREQUENCY_NULL_REPLICATION",
      "status":"IN_PROGRESS","qpu_jobs":0,"actual_quantum_measurements":0,
      "cohort_provenance":{"uniform_random":"independent uniform integer null",
        "oracle_peaks_NOT_MEASURED":"classically exact-order Fourier peak locations"},
      "samples_per_cohort_per_seed":a.samples,"seeds":a.seeds,
      "budget_proxy":a.budget,"rows":[]}
    def save():dest.write_text(json.dumps(report,indent=2)+"\n")
    save()
    for n,bits in cases:
      r=order(a.base,n);Q=1<<bits
      for seed in a.seeds:
        rng=random.Random(seed ^ (n<<9) ^ bits)
        arms={"uniform_random":[rng.randrange(Q) for _ in range(a.samples)],
              "oracle_peaks_NOT_MEASURED":[round(rng.randrange(r)*Q/r)%Q for _ in range(a.samples)]}
        for label,frequencies in arms.items():
          row={"n":n,"base":a.base,"bits":bits,"seed":seed,
             "cohort":label,"true_order_reference_not_solver_input":r,
             "cases":[],"status":"IN_PROGRESS"}
          report["rows"].append(row);save()
          for i,freq in enumerate(frequencies):
            data=run_worker({"n":n,"base":a.base,"bits":bits,"frequency":freq,
             "method":"ekera","budget":a.budget,"timeout":a.timeout,
             "upstream":a.upstream},a.wall_timeout)
            if data["status"]=="ERROR":
              row["status"]="FAIL_WORKER_ERROR";row["error"]=data.get("error");report["status"]="FAIL_WORKER_ERROR"
              save();raise RuntimeError(data.get("error"))
            if data.get("factors") is not None:assert math.prod(data["factors"])==n
            row["cases"].append({"frequency":freq,**data})
            save()
          row["successes"]=sum(x.get("factors") is not None for x in row["cases"])
          row["verified_exponents"]=sum(x.get("candidate_exponent") is not None for x in row["cases"])
          row["hard_timeouts"]=sum(x["status"]=="HARD_TIMEOUT" for x in row["cases"])
          row["wilson_95"]=wilson(row["successes"],a.samples)
          row["mean_wall_s"]=round(sum(x["wall_s"] for x in row["cases"])/a.samples,4)
          row["status"]="COMPLETE";save()
          print("A49",n,bits,seed,label,row["successes"],"/",a.samples,
                "CI",row["wilson_95"],"timeouts",row["hard_timeouts"],flush=True)
    report["status"]="PASS_REPLICATED_CLASSICAL_NULL_AND_ORDER_ORACLE_CONTROL"
    save();print("A49 STATUS",report["status"],"SAVED",dest,flush=True)

if __name__=="__main__":main()
