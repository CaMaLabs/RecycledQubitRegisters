#!/usr/bin/env python3
"""A12: read-only Fez calibration-aware mapping exposure audit.
Not hardware-fidelity prediction: sums per-instruction error proxies without
correlations, leakage, scheduling, conditional readout/reset timing or crosstalk.
Never submits a QPU job. Does not change original arithmetic or Quaspy solver.
"""
import argparse,json,math,statistics,traceback
from datetime import datetime,timezone
from pathlib import Path
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService
import qrr_n35_true_recycled_phase_feedforward as src
import qrr_n35_true_recycled_prune_idle_scratch as pruning

def exposure(qc,target):
    """Recursive operation-local calibration proxy. Missing values are tracked,
    and control-flow block counts are structural, not branch-weighted."""
    stats={"operations":{},"missing_calibration":{},"calibrated_log_survival":0.,
           "calibrated_gates":0,"measurement_errors":[],"two_qubit_errors":[],
           "unscored_dynamic_blocks":0}
    def walk(circuit,physical):
        for ins in circuit.data:
            op=ins.operation
            name=op.name
            stats["operations"][name]=stats["operations"].get(name,0)+1
            qubits=tuple(physical[circuit.find_bit(q).index] for q in ins.qubits)
            if name in ("if_else","while_loop","for_loop","switch_case"):
                # A control-flow branch executes conditionally. Do not claim that
                # summing every possible branch gives a physical shot prediction.
                stats["unscored_dynamic_blocks"]+=1
                continue
            try:
                spec=target[name]
                prop=spec.get(qubits)
                err=None if prop is None else prop.error
            except (KeyError,ValueError,TypeError,AttributeError):
                err=None
            if err is None or not (0<=float(err)<1):
                stats["missing_calibration"][name]=stats["missing_calibration"].get(name,0)+1
                continue
            err=float(err)
            stats["calibrated_log_survival"]+=-math.log1p(-err)
            stats["calibrated_gates"]+=1
            if name=="measure":stats["measurement_errors"].append(err)
            if len(qubits)==2:stats["two_qubit_errors"].append(err)
    walk(qc,list(range(qc.num_qubits)))
    stats["measured_error_proxy"]=1-math.exp(-stats["calibrated_log_survival"])
    stats["calibration_coverage_warning"]=bool(stats["missing_calibration"] or stats["unscored_dynamic_blocks"])
    stats["estimated_error_per_readout_bit"]=(
        statistics.mean(stats["measurement_errors"]) if stats["measurement_errors"] else None)
    return stats

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="results/qrr_a12_fez_mapping_exposure.json")
    ap.add_argument("--bases",type=int,nargs="+",default=[2,8])
    ap.add_argument("--bits",type=int,nargs="+",default=[4,6,8])
    ap.add_argument("--seeds",type=int,nargs="+",default=[509,1223,4093,8776])
    a=ap.parse_args()
    report={"status":"STARTED","created_utc":datetime.now(timezone.utc).isoformat(),
      "backend":"ibm_fez","zero_qpu_jobs":True,
      "warning":"CPU-only compilation + live read-only backend error metadata; unscored dynamic branches and missing calibrations prevent a faithful whole-shot error rate",
      "source":"A7 original arithmetic, NOT rejected selective-k23 candidate",
      "rows":[]}
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    def save():path.write_text(json.dumps(report,indent=2,default=str)+"\n")
    try:
        src.configure_original_public_arithmetic()
        service=QiskitRuntimeService()
        backend=service.backend("ibm_fez")
        assert not getattr(backend,"simulator",False)
        target=backend.target
        report["target_num_qubits"]=backend.num_qubits
        report["target_updated_at"]=str(getattr(target,"dt",None))
        for base in a.bases:
            for bits in a.bits:
                full,registers,clbits,schedule,feedback=src.build_dynamic_source(base,bits)
                src.inspect_dynamic_source(full,registers,clbits,base,bits,schedule,feedback)
                qc,proof=pruning.reduction_with_exact_instruction_identity(full,bits)
                row={"base":base,"bits":bits,"source_qubits":qc.num_qubits,
                     "baseline_preserved":True,"placements":[]}
                report["rows"].append(row);save()
                for seed in a.seeds:
                    compiled=generate_preset_pass_manager(
                        backend=backend,optimization_level=1,seed_transpiler=seed).run(qc)
                    cost=exposure(compiled,target)
                    row["placements"].append({"seed":seed,
                        "cz":int(compiled.count_ops().get("cz",0)),
                        "depth":int(compiled.depth()),
                        "exposure":cost})
                    print("A12",base,bits,seed,"CZ",row["placements"][-1]["cz"],
                          "depth",row["placements"][-1]["depth"],
                          "partial_error_proxy",round(cost["measured_error_proxy"],6),
                          "missing",cost["calibration_coverage_warning"],flush=True)
                    save()
                # Rank by calibrated error proxy, with explicit partial-coverage caveat.
                ranked=sorted(row["placements"],key=lambda p:p["exposure"]["calibrated_log_survival"])
                row["best_seed_by_partial_proxy"]=ranked[0]["seed"]
                row["worst_seed_by_partial_proxy"]=ranked[-1]["seed"]
                row["full_readout_error_rate_verified"]=False
                save()
        report["status"]="COMPLETE_PARTIAL_PROXY_ONLY";save()
        print(json.dumps({"status":report["status"],"qpu_jobs":0,
          "cases":[{"base":r["base"],"bits":r["bits"],
            "best_seed":r["best_seed_by_partial_proxy"],
            "worst_seed":r["worst_seed_by_partial_proxy"],
            "dynamic_unscored":max(p["exposure"]["unscored_dynamic_blocks"] for p in r["placements"])}
            for r in report["rows"]]},indent=2))
    except Exception:
        report["status"]="ERROR";report["traceback"]=traceback.format_exc();save()
        raise
if __name__=="__main__":main()
