#!/usr/bin/env python3
"""A15: read-only Fez measurement/reset calibration exposure by placement.
Does not infer independent phase bit error or submit QPU jobs.
"""
import argparse,json,statistics,traceback
from pathlib import Path
from datetime import datetime,timezone
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
import qrr_n35_true_recycled_phase_feedforward as source
import qrr_n35_true_recycled_prune_idle_scratch as prune

def calibrated(target,name,qubits):
    try:
        prop=target[name].get(tuple(qubits))
        e=None if prop is None else prop.error
        d=None if prop is None else prop.duration
        return {"error":float(e) if e is not None else None,
                "duration_s":float(d) if d is not None else None}
    except (KeyError,TypeError,ValueError,AttributeError):
        return {"error":None,"duration_s":None}

def inspect(isa,target):
    records=[]
    branch_records=[]
    def scan(circuit,physical,conditional=False):
        for ins in circuit.data:
            op=ins.operation
            mapped=tuple(physical[circuit.find_bit(q).index] for q in ins.qubits)
            if getattr(op,"blocks",()):
                for block in op.blocks:
                    assert block.num_qubits==len(mapped)
                    scan(block,mapped,True)
                continue
            if op.name in ("measure","reset"):
                obj={"kind":op.name,"physical_qubit":mapped[0],
                     "conditional_branch":conditional,
                     **calibrated(target,op.name,mapped)}
                (branch_records if conditional else records).append(obj)
    scan(isa,tuple(range(isa.num_qubits)))
    result={}
    for kind in ("measure","reset"):
        xs=[r for r in records if r["kind"]==kind]
        result[kind]={"count":len(xs),
                      "physical_qubits":[x["physical_qubit"] for x in xs],
                      "error_rates":[x["error"] for x in xs],
                      "mean_calibrated_error":statistics.mean(x["error"] for x in xs) if xs and all(x["error"] is not None for x in xs) else None,
                      "max_calibrated_error":max(x["error"] for x in xs) if xs and all(x["error"] is not None for x in xs) else None,
                      "duration_s":[x["duration_s"] for x in xs]}
    result["conditional_measure_reset_count"]=len(branch_records)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="results/qrr_a15_fez_measure_reset_calibration.json")
    p.add_argument("--seeds",type=int,nargs="+",default=[509,1223,4093,8776])
    a=p.parse_args()
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"STARTED","utc":datetime.now(timezone.utc).isoformat(),
       "backend":"ibm_fez","qpu_jobs":0,"rows":[],
       "scope":"calibration metadata on mapped measure/reset instructions, NOT phase-readout BER or circuit success probability"}
    def save():dest.write_text(json.dumps(result,indent=2)+"\n")
    try:
        source.configure_original_public_arithmetic()
        backend=QiskitRuntimeService().backend("ibm_fez")
        assert not getattr(backend,"simulator",False)
        for base in (2,8):
            for bits in (4,6,8):
                full,r,c,sched,feed=source.build_dynamic_source(base,bits)
                source.inspect_dynamic_source(full,r,c,base,bits,sched,feed)
                lean,_=prune.reduction_with_exact_instruction_identity(full,bits)
                row={"base":base,"bits":bits,"seeds":[]}
                result["rows"].append(row);save()
                for seed in a.seeds:
                    isa=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed).run(lean)
                    values=inspect(isa,backend.target)
                    assert values["measure"]["count"]==bits
                    assert values["reset"]["count"]==bits-1
                    assert values["conditional_measure_reset_count"]==0
                    point={"seed":seed,"native_cz":int(isa.count_ops().get("cz",0)),
                      "native_depth":isa.depth(),**values}
                    row["seeds"].append(point);save()
                    print("A15",base,bits,seed,"measure_mean",values["measure"]["mean_calibrated_error"],
                          "reset_mean",values["reset"]["mean_calibrated_error"],
                          "measured_locations",values["measure"]["physical_qubits"],flush=True)
                valid=[s for s in row["seeds"] if s["measure"]["mean_calibrated_error"] is not None]
                row["min_measure_error_seed"]=min(valid,key=lambda s:s["measure"]["mean_calibrated_error"])["seed"] if valid else None
                row["calibration_complete"]=len(valid)==len(a.seeds) and all(
                    s["reset"]["mean_calibrated_error"] is not None for s in row["seeds"])
                save()
        result["status"]="COMPLETE_CALIBRATION_METADATA_ONLY";save()
        print(json.dumps({"status":result["status"],"qpu_jobs":0,
            "summary":[{"base":r["base"],"bits":r["bits"],"min_measure_error_seed":r["min_measure_error_seed"],
                        "calibration_complete":r["calibration_complete"]} for r in result["rows"]]},indent=2))
    except Exception:
        result["status"]="FAIL";result["traceback"]=traceback.format_exc();save();raise
if __name__=="__main__":main()
