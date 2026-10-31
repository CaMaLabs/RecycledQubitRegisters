#!/usr/bin/env python3
"""A33: N35 same-process recovered Quaspy handoff from recycled branch model.

The dynamic gate SOURCE is constructed; frequency samples are from the existing
exact coherent-work BRANCH MODEL, NOT measurements from gate-level execution.
No QPU. Factor oracle/order are never inputs to public recovery.
"""
from __future__ import annotations
import argparse,json,math,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/"hardware")]
from integrations.darkstar_hybrid import quaspy_public_postprocess as post
from integrations.darkstar_hybrid.qrr_a24_n35_public_first_gate import public_preflight
import qrr_n35_true_recycled_phase_feedforward as recycled

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--upstream",default="/tmp/qrr-indie-quaspy")
    ap.add_argument("--shots",type=int,default=32)
    ap.add_argument("--seed",type=int,default=20261030)
    ap.add_argument("--output",default="results/a33_n35_actual_handoff.json")
    a=ap.parse_args()
    if not 1<=a.shots<=10000:ap.error("shots must be 1..10000")
    post.load_upstream(a.upstream)
    recycled.configure_original_public_arithmetic()
    rows=[]
    for base in (2,8):
        pre=public_preflight(35,base)
        assert pre["route"]=="CLASSICAL_FIRST_WHEEL" and pre["factors"]==[5,7]
        qc,r,c,schedule,feedback=recycled.build_dynamic_source(base,8)
        assert qc.num_qubits==32 and qc.num_clbits==8
        assert qc.count_ops().get("measure",0)==8
        distribution,proof=recycled.emit_branch_model_probabilities(base,8)
        assert proof["pass_all"] and abs(sum(distribution)-1)<1e-9
        randomizer=random.Random(a.seed+base)
        frequencies=randomizer.choices(range(256),weights=distribution,k=a.shots)
        records=[]
        for f in frequencies:
            cf=post.recover(35,base,8,f,"cf",timeout=2)
            ek=post.recover(35,base,8,f,"ekera",timeout=2)
            for result in (cf,ek):
                if result["factors"]:
                    assert math.prod(result["factors"])==35
            records.append(dict(frequency=f,cf_status=cf["status"],
                cf_factors=cf["factors"],quaspy_status=ek["status"],
                quaspy_factors=ek["factors"],
                cf_pow_calls=cf["ledger"]["pow_calls"],
                quaspy_pow_calls=ek["ledger"]["pow_calls"]))
        rows.append(dict(n=35,base=base,
            route=pre["route"],classical_factors=pre["factors"],
            quantum_needed_for_factorization=False,
            circuit_source_qubits=qc.num_qubits,measurements=qc.count_ops().get("measure",0),
            resets=qc.count_ops().get("reset",0),feedback_conditions=len(feedback),
            phase_bits=8,shot_count=a.shots,
            frequency_source="exact coherent-work recycled branch model; NOT gate-level shots",
            quaspy_successes=sum(x["quaspy_factors"] is not None for x in records),
            cf_successes=sum(x["cf_factors"] is not None for x in records),
            quaspy_pow_calls=sum(x["quaspy_pow_calls"] for x in records),
            cf_pow_calls=sum(x["cf_pow_calls"] for x in records),
            readouts=records))
    report=dict(experiment="A33_N35_SOURCE_PLUS_BRANCH_READOUT_TO_QUASPY",
        status="PASS_BRANCH_MODEL_TO_QUASPY_HANDOFF",qpu_jobs=0,
        gate_level_measurements_generated=False,
        same_process_public_frequency_handoff=True,
        actual_full_shor_execution=False,quantum_advantage=False,rows=rows)
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v if k!="rows" else [{kk:vv for kk,vv in row.items() if kk!="readouts"} for row in v] for k,v in report.items()},indent=2))
    print("SAVED",dest)
    return 0
if __name__=="__main__":raise SystemExit(main())
