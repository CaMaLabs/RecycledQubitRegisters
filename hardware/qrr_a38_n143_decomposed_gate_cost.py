#!/usr/bin/env python3
"""A38: apples-to-apples decomposed gate cost for A36 versus A37, N=143.

Preserves original gate sources. Uses identical Qiskit transpilation settings;
does not run hardware or claim fault-tolerant cost. No substitutions for MCX.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware"))
import qrr_a37_n143_gate_audit_optimizer as a37
from qiskit import transpile

def counts(circuit):
    return {str(k): int(v) for k, v in circuit.count_ops().items()}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bases", nargs="+", type=int, default=[2, 8])
    p.add_argument("--output", default="results/a38_native_cost_audit.json")
    p.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=0)
    args = p.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "experiment": "A38_N143_IDENTICAL_BASIS_GATE_COST",
        "status": "IN_PROGRESS",
        "qpu_jobs": 0,
        "basis_gates": ["u", "cx"],
        "optimization_level": args.optimization_level,
        "noise_model": None,
        "hardware_topology": None,
        "fault_tolerant_resources": None,
        "n143_recycled_qpe_integrated": False,
        "n143_quaspy_integrated": False,
        "rows": []
    }
    def save():
        out.write_text(json.dumps(report, indent=2) + "\n")
    save()
    try:
        for base in args.bases:
            t0 = time.perf_counter()
            original = a37.original_multiply(base)
            optimized = a37.optimized_multiply(base)
            # Independently verify all 512 basis inputs before transpilation.
            assert a37.verify(original, base) == 512
            assert a37.verify(optimized, base) == 512
            compiled = {}
            for label, circuit in (("original", original), ("x_frame", optimized)):
                begin = time.perf_counter()
                lowered = transpile(circuit, basis_gates=["u", "cx"],
                                    optimization_level=args.optimization_level,
                                    seed_transpiler=20261030)
                ops = counts(lowered)
                assert set(ops).issubset({"u", "cx"}), ops
                compiled[label] = {
                    "source_counts": counts(circuit),
                    "decomposed_counts": ops,
                    "decomposed_depth": lowered.depth(),
                    "compile_seconds": round(time.perf_counter() - begin, 4),
                    "logical_qubits": lowered.num_qubits,
                }
                print(base, label, ops, "depth", lowered.depth(), flush=True)
            c0 = compiled["original"]["decomposed_counts"].get("cx", 0)
            c1 = compiled["x_frame"]["decomposed_counts"].get("cx", 0)
            u0 = compiled["original"]["decomposed_counts"].get("u", 0)
            u1 = compiled["x_frame"]["decomposed_counts"].get("u", 0)
            row = {
                "n": 143, "base": base, "verified_input_states_each": 512,
                "original": compiled["original"], "x_frame": compiled["x_frame"],
                "cx_difference": c0 - c1,
                "u_difference": u0 - u1,
                "cx_reduction_fraction": (c0-c1)/c0 if c0 else None,
                "u_reduction_fraction": (u0-u1)/u0 if u0 else None,
                "depth_difference": compiled["original"]["decomposed_depth"] - compiled["x_frame"]["decomposed_depth"],
                "wall_seconds": round(time.perf_counter()-t0, 3),
            }
            report["rows"].append(row)
            save()
        report["status"] = "PASS_IDENTICAL_BASIS_COST_COMPARISON"
    except Exception as exc:
        report["status"] = "FAIL_NOT_VALIDATED"
        report["error"] = repr(exc)
        report["traceback"] = traceback.format_exc()[-5000:]
        save()
        raise
    save()
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    print("SAVED", out)
if __name__ == "__main__":
    main()
