#!/usr/bin/env python3
"""A42: repeated ACTUAL Aer dynamic N143 samples, matched CF/Quaspy, gate costs.

No model-generated measurements. An independently seeded 1-shot simulator job
is used for each requested seed. All individual measurements retained.
Avoids hard-coded factor/order success shortcuts. Zero QPU jobs.
"""
from __future__ import annotations
import argparse,json,math,sys,time,traceback
from pathlib import Path
from qiskit import transpile
from qiskit_aer import AerSimulator
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
import qrr_a41_n143_dynamic_recycled_quaspy as a41
from integrations.darkstar_hybrid import quaspy_public_postprocess as post

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",type=int,default=8)
    p.add_argument("--bits",type=int,default=9)
    p.add_argument("--shots",type=int,default=16,help="Independent one-shot simulator seeds")
    p.add_argument("--seed",type=int,default=20261031)
    p.add_argument("--threads",type=int,default=4)
    p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
    p.add_argument("--output",default="results/a42_n143_reproducibility.json")
    a=p.parse_args()
    if not 1<=a.shots<=256:p.error("shots must be 1..256")
    if not 9<=a.bits<=16:p.error("bits must be 9..16")
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    report={"experiment":"A42_ACTUAL_N143_GATE_LEVEL_REPRODUCIBILITY",
      "status":"IN_PROGRESS","n":143,"base":a.base,"bits":a.bits,
      "independent_seed_shots":a.shots,"seed_start":a.seed,
      "qpu_jobs":0,"model_sampled_readouts":False,
      "noise_model":None,"rows":[]}
    def save():dest.write_text(json.dumps(report,indent=2)+"\n")
    save()
    t0=time.perf_counter()
    try:
        circuit,schedule=a41.build(a.base,a.bits)
        sim=AerSimulator(method="matrix_product_state",max_parallel_threads=a.threads)
        t=time.perf_counter()
        compiled=transpile(circuit,sim,optimization_level=0,seed_transpiler=a.seed)
        compile_time=time.perf_counter()-t
        report["circuit"]={"qubits":circuit.num_qubits,"clbits":circuit.num_clbits,
          "source_counts":dict(circuit.count_ops()),"source_depth":circuit.depth(),
          "transpiled_counts":dict(compiled.count_ops()),
          "transpiled_depth":compiled.depth(),"compile_seconds":round(compile_time,3),
          "public_schedule":schedule}
        save()
        print("A42 COMPILED",json.dumps({k:v for k,v in report["circuit"].items() if k!="public_schedule"}),flush=True)
        post.load_upstream(a.upstream)
        for i in range(a.shots):
            seed=a.seed+i
            t=time.perf_counter()
            result=sim.run(compiled,shots=1,memory=True,seed_simulator=seed).result()
            if not result.success:raise RuntimeError(str(result.status))
            word=str(result.get_memory(compiled)[0])
            frequency=int(word.replace(" ",""),2)
            entry={"index":i,"seed":seed,"bitstring":word,"frequency":frequency,
                "sim_seconds":round(time.perf_counter()-t,4)}
            for method in ("cf","ekera"):
                recovery=post.recover(143,a.base,a.bits,frequency,method=method,
                                      budget=100000,timeout=3)
                factors=recovery["factors"]
                if factors is not None:assert math.prod(factors)==143
                entry[method]=recovery
            report["rows"].append(entry);save()
            print("A42 SHOT",i+1,"/",a.shots,"frequency",frequency,
                "CF",entry["cf"]["status"],"Quaspy",entry["ekera"]["status"],flush=True)
        n=len(report["rows"])
        report["summary"]={
          "shots":n,
          "cf_factor_successes":sum(r["cf"]["factors"] is not None for r in report["rows"]),
          "quaspy_factor_successes":sum(r["ekera"]["factors"] is not None for r in report["rows"]),
          "cf_pow_calls":sum(r["cf"]["ledger"]["pow_calls"] for r in report["rows"]),
          "quaspy_pow_calls":sum(r["ekera"]["ledger"]["pow_calls"] for r in report["rows"]),
          "mean_sim_seconds_per_shot":sum(r["sim_seconds"] for r in report["rows"])/n,
          "distinct_frequencies":len({r["frequency"] for r in report["rows"]}),
        }
        report["status"]="PASS_REPEATED_ACTUAL_AER_MEASUREMENT_LEDGER"
    except Exception as exc:
        report["status"]="FAIL_NOT_VALIDATED"
        report["error"]=repr(exc)
        report["traceback"]=traceback.format_exc()[-4000:]
        save()
        raise
    report["wall_seconds"]=round(time.perf_counter()-t0,2)
    save()
    print("A42 SUMMARY",json.dumps(report["summary"]),flush=True)
    print("A42 STATUS",report["status"],"SAVED",dest,flush=True)
if __name__=="__main__":main()
