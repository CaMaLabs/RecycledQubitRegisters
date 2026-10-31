#!/usr/bin/env python3
"""A18: strict CPU-only hardware feasibility gate for two Fez placement seeds.
NEVER submits Sampler/Estimator jobs or invokes hardware execution.
"""
import argparse,json,traceback
from pathlib import Path
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
import qrr_n35_true_recycled_phase_feedforward as source
import qrr_n35_true_recycled_prune_idle_scratch as prune
from qrr_a15_fez_measure_reset_calibration import inspect

def run():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="results/qrr_a18_hardware_go_nogo.json")
    p.add_argument("--max-cz",type=int,default=1000)
    p.add_argument("--max-depth",type=int,default=3000)
    a=p.parse_args()
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"STARTED","backend":"ibm_fez","qpu_jobs":0,
      "precision":4,"base":8,"seeds":[509,1223],
      "limits":{"max_cz":a.max_cz,"max_depth":a.max_depth},
      "physical_execution_authorized":False,"rows":[]}
    def save():dest.write_text(json.dumps(result,indent=2)+"\n")
    save()
    try:
        source.configure_original_public_arithmetic()
        full,r,c,sched,feedback=source.build_dynamic_source(8,4)
        source.inspect_dynamic_source(full,r,c,8,4,sched,feedback)
        qc,_=prune.reduction_with_exact_instruction_identity(full,4)
        backend=QiskitRuntimeService().backend("ibm_fez")
        assert not getattr(backend,"simulator",False)
        for seed in (509,1223):
            isa=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed).run(qc)
            cal=inspect(isa,backend.target)
            cz=int(isa.count_ops().get("cz",0));depth=int(isa.depth())
            row={"seed":seed,"cz":cz,"depth":depth,"calibration":cal,
                 "individual_feasible":cz<=a.max_cz and depth<=a.max_depth}
            result["rows"].append(row);save()
            print("A18",seed,"CZ",cz,"depth",depth,
                  "mean_readout_error",cal["measure"]["mean_calibrated_error"],
                  "GO" if row["individual_feasible"] else "NO_GO",flush=True)
        result["matched_pair_go"]=all(r["individual_feasible"] for r in result["rows"])
        result["status"]="CPU_GATE_GO_REQUIRES_EXPLICIT_HARDWARE_APPROVAL" if result["matched_pair_go"] else "CPU_GATE_NO_GO"
        save()
        print(json.dumps({"status":result["status"],"qpu_jobs":0,
          "matched_pair_go":result["matched_pair_go"],
          "rows":[{"seed":r["seed"],"cz":r["cz"],"depth":r["depth"],"go":r["individual_feasible"]} for r in result["rows"]]},indent=2))
    except Exception:
        result["status"]="ERROR";result["error"]=traceback.format_exc();save();raise
if __name__=="__main__":run()
