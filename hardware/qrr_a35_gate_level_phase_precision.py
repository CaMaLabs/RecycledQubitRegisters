#!/usr/bin/env python3
"""A35: measured gate-level phase-precision ablation, N35, no model substitutions.

6 bits CF-only; 7/8 bits Quaspy eligible. Identical Aer MPS memory readouts
for CF and Quaspy in each arm. No QPU. No cross-arm claims from one shot.
"""
import argparse, json, math, sys, time, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
from integrations.darkstar_hybrid import quaspy_public_postprocess as post
from integrations.darkstar_hybrid.qrr_a24_n35_public_first_gate import public_preflight
import qrr_n35_true_recycled_phase_feedforward as recycled

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
    p.add_argument("--shots",type=int,default=128)
    p.add_argument("--seed",type=int,default=20261030)
    p.add_argument("--threads",type=int,default=4)
    p.add_argument("--output",default="results/a35_phase_precision_ablation.json")
    a=p.parse_args()
    if not 1<=a.shots<=1024:p.error("shots must be 1..1024")
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    post.load_upstream(a.upstream)
    recycled.configure_original_public_arithmetic()
    sim=AerSimulator(method="matrix_product_state",max_parallel_threads=a.threads)
    rows=[]
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    report={"experiment":"A35_GATE_LEVEL_PHASE_PRECISION_ABLATION",
      "status":"IN_PROGRESS","shots_per_arm":a.shots,"qpu_jobs":0,
      "frequency_source":"actual Aer dynamic gate-level shot memory, NOT analytical distribution",
      "rows":rows}
    def save():dest.write_text(json.dumps(report,indent=2)+"\n")
    for base in (2,8):
      pre=public_preflight(35,base)
      assert pre["route"]=="CLASSICAL_FIRST_WHEEL"
      for bits in (6,7,8):
        t=time.perf_counter()
        qc,registers,classic,schedule,feedback=recycled.build_dynamic_source(base,bits)
        compiled=transpile(qc,sim,optimization_level=0,seed_transpiler=a.seed)
        result=sim.run(compiled,shots=a.shots,seed_simulator=a.seed+base*100+bits,memory=True).result()
        if not result.success:raise RuntimeError(str(result.status))
        memory=result.get_memory(compiled)
        assert len(memory)==a.shots
        outcomes=[]
        for word in memory:
          freq=int(str(word).replace(" ",""),2)
          item={"frequency":freq,"bitstring":str(word)}
          for method in ("cf","ekera"):
            if method=="ekera" and bits<=35 .bit_length():
              item["ekera"]={"status":"INELIGIBLE_PRECISION","factors":None,"ledger":{"pow_calls":0}}
              continue
            rec=post.recover(35,base,bits,freq,method,timeout=3)
            if rec["factors"]:assert math.prod(rec["factors"])==35
            item[method]=rec
          outcomes.append(item)
        row={"n":35,"base":base,"phase_bits":bits,"shots":a.shots,
          "quaspy_eligible":bits>35 .bit_length(),
          "quaspy_successes":sum(bool(x["ekera"]["factors"]) for x in outcomes) if bits>35 .bit_length() else None,
          "cf_successes":sum(bool(x["cf"]["factors"]) for x in outcomes),
          "quaspy_pow_calls":sum(x["ekera"]["ledger"]["pow_calls"] for x in outcomes) if bits>35 .bit_length() else None,
          "cf_pow_calls":sum(x["cf"]["ledger"]["pow_calls"] for x in outcomes),
          "qubits":qc.num_qubits,"measurements":qc.count_ops().get("measure",0),
          "resets":qc.count_ops().get("reset",0),"feedback_conditions":len(feedback),
          "source_counts":dict(qc.count_ops()),"transpiled_counts":dict(compiled.count_ops()),
          "transpiled_depth":compiled.depth(),"wall_seconds":round(time.perf_counter()-t,3),
          "outcomes":outcomes}
        rows.append(row);save()
        print(json.dumps({k:v for k,v in row.items() if k!="outcomes"}),flush=True)
    report["status"]="PASS_GATE_LEVEL_ABLATION";save()
    print("SAVED",dest,flush=True)
    return 0
if __name__=="__main__":raise SystemExit(main())
