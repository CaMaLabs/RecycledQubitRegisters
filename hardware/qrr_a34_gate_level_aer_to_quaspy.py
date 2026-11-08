#!/usr/bin/env python3
"""A34: execute actual N35 dynamic recycled circuit in Qiskit Aer MPS.

Unlike A33 this NEVER substitutes model-sampled frequencies for a simulator
measurement. Aer missing / unsupported dynamic control / timeout are recorded
as non-PASS outcomes. Use small shots first: 32-qubit arithmetic is expensive.
"""
from __future__ import annotations
import argparse,json,math,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
from integrations.darkstar_hybrid import quaspy_public_postprocess as post
from integrations.darkstar_hybrid.qrr_a24_n35_public_first_gate import public_preflight
import qrr_n35_true_recycled_phase_feedforward as recycled

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
    p.add_argument("--base",type=int,choices=(2,8),default=8)
    p.add_argument("--bits",type=int,choices=(4,6,8),default=8)
    p.add_argument("--shots",type=int,default=1)
    p.add_argument("--seed",type=int,default=20261030)
    p.add_argument("--threads",type=int,default=4)
    p.add_argument("--output",default="results/a34_gate_level_measurements.json")
    a=p.parse_args()
    if not 1<=a.shots<=64 or not 1<=a.threads<=32:p.error("shots 1..64, threads 1..32")
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    report={"experiment":"A34_GATE_LEVEL_DYNAMIC_READOUT_TO_QUASPY","status":"STARTED",
       "simulation_method":"Qiskit Aer matrix_product_state",
       "qpu_jobs":0,"gate_level_readouts":False,"model_sampled_readouts":False,
       "n":35,"base":a.base,"bits":a.bits,"shots":a.shots,"seed":a.seed}
    def save():dest.write_text(json.dumps(report,indent=2,default=str)+"\n")
    save()
    try:
        from qiskit_aer import AerSimulator
        public=public_preflight(35,a.base)
        assert public["route"]=="CLASSICAL_FIRST_WHEEL"
        report["public_preflight"]=public
        recycled.configure_original_public_arithmetic()
        qc,r,c,schedule,feedback=recycled.build_dynamic_source(a.base,a.bits)
        assert qc.num_qubits==32 and qc.count_ops().get("measure",0)==a.bits
        report["source_gate_counts"]={str(k):int(v) for k,v in qc.count_ops().items()}
        report["source_qubits"]=qc.num_qubits
        report["feedback_conditions"]=len(feedback)
        simulator=AerSimulator(method="matrix_product_state",max_parallel_threads=a.threads)
        from qiskit import transpile
        compiled=transpile(qc,simulator,optimization_level=0,seed_transpiler=a.seed)
        report["transpiled_gate_counts"]={str(k):int(v) for k,v in compiled.count_ops().items()}
        report["transpiled_depth"]=compiled.depth()
        save()
        t=time.perf_counter()
        result=simulator.run(compiled,shots=a.shots,seed_simulator=a.seed,memory=True).result()
        if not result.success:
            raise RuntimeError("Aer simulator failure: "+str(result.status))
        measurements=result.get_memory(compiled)
        if len(measurements)!=a.shots:raise AssertionError("missing shots")
        readouts=[]
        for measured in measurements:
            freq=int(str(measured).replace(" ",""),2)
            if not 0<=freq<1<<a.bits:raise AssertionError("invalid bitstring")
            item={"bitstring":measured,"frequency":freq}
            for method in ("cf","ekera"):
                if method=="ekera" and a.bits<=35 .bit_length():
                    item[method]={"status":"INELIGIBLE_PHASE_PRECISION"}
                    continue
                post.load_upstream(a.upstream) if method=="ekera" and not readouts and "ekera" not in item else None
                x=post.recover(35,a.base,a.bits,freq,method,timeout=4)
                if x["factors"]:assert math.prod(x["factors"])==35
                item[method]=x
            readouts.append(item)
        report.update(status="PASS_ACTUAL_AER_GATE_LEVEL_READOUTS",gate_level_readouts=True,
                      readouts=readouts,simulation_seconds=round(time.perf_counter()-t,3),
                      quaspy_verified=sum(bool(x.get("ekera",{}).get("factors")) for x in readouts),
                      cf_verified=sum(bool(x.get("cf",{}).get("factors")) for x in readouts),
                      interpretation="Real gate-level Aer dynamic-circuit simulated measurements, not QPU shots. Classical wheel already factors N35; no quantum advantage.")
    except Exception as exc:
        report.update(status="NOT_VALIDATED",error=repr(exc),traceback=traceback.format_exc(),
          interpretation="No PASS claimed; gate-level simulation or recovery unavailable/failed.")
    save()
    print(json.dumps({k:v for k,v in report.items() if k!="readouts" and k!="traceback"},indent=2))
    if report.get("gate_level_readouts"):print("READOUTS",json.dumps([{k:v for k,v in x.items() if k in ("bitstring","frequency","cf","ekera")} for x in report["readouts"]],default=str))
    print("SAVED",dest)
    return 0 if report["gate_level_readouts"] else 1
if __name__=="__main__":raise SystemExit(main())
