#!/usr/bin/env python3
"""A13: control-flow-aware calibration coverage and log-risk (CPU-only Fez target).
Does NOT predict actual shot fidelity or readout BER. Preserves original arithmetic.
"""
import argparse,json,math,traceback,statistics
from pathlib import Path
from datetime import datetime,timezone
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
import qrr_n35_true_recycled_phase_feedforward as src
import qrr_n35_true_recycled_prune_idle_scratch as prune

def audit(isa,target):
    stats={"top_level_instructions":len(isa.data),"branches":0,"branch_arms":0,
           "scored":0,"missing":{},"op_counts":{},"total_calibrated_log_risk":0.,
           "unscored_branch_operations":0,"measures":[],"two_qubit":[],"resets":[]}
    def add(name,qs):
        stats["op_counts"][name]=stats["op_counts"].get(name,0)+1
        if name in ("barrier","delay"):
            stats["missing"][name]=stats["missing"].get(name,0)+1
            return
        try:
            prop=target[name].get(qs)
            e=None if prop is None else prop.error
        except (KeyError,TypeError,ValueError,AttributeError):
            e=None
        if e is None or not 0<=float(e)<1:
            stats["missing"][name]=stats["missing"].get(name,0)+1
            return
        e=float(e)
        stats["scored"]+=1
        stats["total_calibrated_log_risk"]+=-math.log1p(-e)
        if name=="measure":stats["measures"].append({"physical":qs[0],"error":e})
        if name=="reset":stats["resets"].append({"physical":qs[0],"error":e})
        if len(qs)==2:stats["two_qubit"].append(e)
    def walk(circuit,phys,inside=False):
        for instruction in circuit.data:
            op=instruction.operation
            qs=tuple(phys[circuit.find_bit(q).index] for q in instruction.qubits)
            if getattr(op,"blocks",()):
                stats["branches"]+=1
                # Conditional branches need a branch-specific execution probability;
                # only analyze their gates separately, never sum them into shot risk.
                for block in op.blocks:
                    stats["branch_arms"]+=1
                    before=stats["scored"]
                    # Instruction qargs map to sub-block qargs by positional index.
                    assert block.num_qubits==len(qs),("unexpected block wires",op.name)
                    count_before=sum(stats["op_counts"].values())
                    walk(block,qs,True)
                    stats["unscored_branch_operations"]+=sum(stats["op_counts"].values())-count_before
                continue
            add(op.name,qs)
    walk(isa,tuple(range(isa.num_qubits)))
    stats["naive_all_branches_log_risk_upper_proxy"]=stats.pop("total_calibrated_log_risk")
    stats["naive_all_branches_risk_saturates"]=stats["naive_all_branches_log_risk_upper_proxy"]>36
    stats["conditional_caveat"]="All branch gates counted even when mutually exclusive; upper proxy, NOT per-shot probability"
    stats["measurement_error_mean"]=statistics.mean(x["error"] for x in stats["measures"]) if stats["measures"] else None
    stats["two_qubit_error_mean"]=statistics.mean(stats["two_qubit"]) if stats["two_qubit"] else None
    stats["calibration_coverage"]=stats["scored"]/max(1,stats["scored"]+sum(stats["missing"].values()))
    return stats

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="results/qrr_a13_fez_branch_calibration.json")
    p.add_argument("--bases",type=int,nargs="+",default=[2,8])
    p.add_argument("--bits",type=int,nargs="+",default=[4,6,8])
    p.add_argument("--seeds",type=int,nargs="+",default=[509,1223,4093,8776])
    a=p.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"STARTED","utc":datetime.now(timezone.utc).isoformat(),"qpu_jobs":0,
            "scope":"read-only native Fez target, no source modifications, all-branches cost upper proxy only",
            "rows":[]}
    def save():out.write_text(json.dumps(result,indent=2)+"\n")
    try:
        src.configure_original_public_arithmetic()
        backend=QiskitRuntimeService().backend("ibm_fez")
        assert not getattr(backend,"simulator",False)
        for base in a.bases:
            for bits in a.bits:
                full,reg,c,sched,feed=src.build_dynamic_source(base,bits)
                src.inspect_dynamic_source(full,reg,c,base,bits,sched,feed)
                qc,_=prune.reduction_with_exact_instruction_identity(full,bits)
                row={"base":base,"bits":bits,"seeds":[]}
                result["rows"].append(row);save()
                for seed in a.seeds:
                    isa=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=seed).run(qc)
                    details=audit(isa,backend.target)
                    row["seeds"].append({"seed":seed,"cz_top_level":isa.count_ops().get("cz",0),
                      "depth":isa.depth(),"details":details})
                    print("A13",base,bits,seed,"coverage",round(details["calibration_coverage"],3),
                      "branches",details["branches"],"nested_operations",
                      details["unscored_branch_operations"],"log_risk_upper",
                      round(details["naive_all_branches_log_risk_upper_proxy"],2),flush=True)
                    save()
        result["status"]="COMPLETE_BRANCH_AWARE_PROXY_ONLY";save()
        print(json.dumps({"status":result["status"],"qpu_jobs":0,"rows":len(result["rows"])},indent=2))
    except Exception:
        result["status"]="FAIL";result["error"]=traceback.format_exc();save();raise
if __name__=="__main__":main()
