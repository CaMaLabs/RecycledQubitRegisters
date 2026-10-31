#!/usr/bin/env python3
"""A19: cost attribution by subtractive native compilation of individual public powers.
NO QPU jobs. Diagnostic isolation, not an additive decomposition of routed cost.
"""
import argparse,json,traceback,collections
from pathlib import Path
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
import qrr_n35_true_recycled_phase_feedforward as src
import qrr_n35_true_recycled_prune_idle_scratch as prune

def build(base,bits,omit):
    original=src.emit_public_controlled_power
    omitted=[]
    def guarded(qc,r,power):
        if power==omit:
            omitted.append(int(power))
            return 0
        return original(qc,r,power)
    try:
        if omit is not None:src.emit_public_controlled_power=guarded
        qc,r,c,schedule,feedback=src.build_dynamic_source(base,bits)
    finally:src.emit_public_controlled_power=original
    if omit is None:
        src.inspect_dynamic_source(qc,r,c,base,bits,schedule,feedback)
    lean,_=prune.reduction_with_exact_instruction_identity(qc,bits)
    return lean,schedule,omitted

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="results/qrr_a19_power_cost_attribution.json")
    p.add_argument("--base",type=int,default=8,choices=(2,8))
    p.add_argument("--bits",type=int,default=4,choices=(4,6,8))
    p.add_argument("--seeds",type=int,nargs="+",default=[509,1223])
    a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    report={"status":"STARTED","qpu_jobs":0,"base":a.base,"bits":a.bits,
        "warning":"Omission circuits are intentionally semantically INCORRECT. Their native deltas are diagnostic only; never deploy or claim they are optimized valid factoring circuits.",
        "rows":[]}
    def save():out.write_text(json.dumps(report,indent=2)+"\n")
    try:
        src.configure_original_public_arithmetic()
        full,schedule,_=build(a.base,a.bits,None)
        active=sorted({int(x["public_multiplier"]) for x in schedule if not x["identity_stage_skipped"]})
        report["active_public_powers"]=active;save()
        backend=QiskitRuntimeService().backend("ibm_fez")
        assert not getattr(backend,"simulator",False)
        variants={None:full}
        for k in active:
            qc,_,omitted=build(a.base,a.bits,k)
            assert omitted,("candidate stage not found",k)
            variants[k]=qc
        for seed in a.seeds:
            result={"seed":seed,"variants":[]}
            report["rows"].append(result);save()
            for omitted,qc in variants.items():
                pm=generate_preset_pass_manager(backend=backend,
                    optimization_level=1,seed_transpiler=seed)
                isa=pm.run(qc)
                item={"omitted_power":omitted,"source_instructions":len(qc.data),
                      "native_cz":int(isa.count_ops().get("cz",0)),
                      "native_depth":int(isa.depth()),
                      "native_measure":int(isa.count_ops().get("measure",0)),
                      "native_reset":int(isa.count_ops().get("reset",0))}
                result["variants"].append(item);save()
            baseline=result["variants"][0]
            for item in result["variants"][1:]:
                item["baseline_minus_omitted_cz"]=baseline["native_cz"]-item["native_cz"]
                item["baseline_minus_omitted_depth"]=baseline["native_depth"]-item["native_depth"]
            print("A19",seed,"baseline CZ",baseline["native_cz"],
                  "stage deltas",[(x["omitted_power"],x.get("baseline_minus_omitted_cz")) for x in result["variants"][1:]],flush=True)
        report["status"]="DIAGNOSTIC_PASS_NOT_SEMANTIC_REPLACEMENT";save()
        print(json.dumps({"status":report["status"],"qpu_jobs":0,
          "active_public_powers":active,"rows":report["rows"]},indent=2))
    except Exception:
        report["status"]="FAIL";report["error"]=traceback.format_exc();save();raise
if __name__=="__main__":main()
