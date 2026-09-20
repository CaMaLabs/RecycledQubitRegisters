#!/usr/bin/env python3
"""Zero-QPU live-calibration sweep over the frozen Fez routing patches.

This consumes the validated TCT arithmetic artifacts and the exhaustive
seed-314159 routing JSON.  For every sampled Fez qiskit-auto patch it rebuilds
and recompiles the same six-round 25-qubit grid-factored coherent objective
circuit using the saved winning transpiler seed, maps local patch qubits back
onto physical ibm_fez qubits, and evaluates the current Target calibration.

The purpose is to distinguish topology-optimal placement from calibration-aware
placement.  Reported independent-gate products are engineering exposure proxies,
not circuit fidelity predictions.  No Sampler or QPU job is used.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_grid_factored_shift_fez_calibration as cal
import benchmark_tct_grid_factored_shift_routing as routing
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width

REV = "2026-09-20-tct-fez-patch-calibration-sweep-v1"
DEFAULT_VALIDATION = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_oracle_validation.json"
DEFAULT_ROUTING = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_routing_6round_exhaustive_seed314159.json"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_fez_patch_calibration_sweep.json"


def finite_or_none(x):
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    ap.add_argument("--routing-json", type=Path, default=DEFAULT_ROUTING)
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    if not validation.get("all_passed"):
        raise RuntimeError("validation artifact is missing all_passed=True")
    routing_json = json.loads(args.routing_json.read_text(encoding="utf-8"))
    if not routing_json.get("exhaustive"):
        raise RuntimeError("routing JSON must be exhaustive")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    rounds = int(routing_json.get("grover_rounds", 6))
    qc, oracle_meta = routing.build_validated_circuit(spec, validation, rounds)

    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, qc.num_qubits, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))

    predicted = routing_json.get("topologies", {}).get("fez_heavy_hex_topology", {}).get("predicted", [])
    pred_by_idx = {int(p["patch_index"]): p for p in predicted}
    refs = [
        r for r in routing_json.get("compile_rows", [])
        if r.get("success")
        and r.get("topology") == "fez_heavy_hex_topology"
        and r.get("layout_mode") == "qiskit_auto"
    ]
    if not refs:
        raise RuntimeError("no Fez qiskit_auto rows in routing JSON")
    refs.sort(key=lambda r: int(r["patch_index"]))

    result = {
        "experiment": "tct_grid_factored_shift_fez_patch_calibration_sweep_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": str(fez.name),
        "calibration_last_update": cal.calibration_timestamp(fez),
        "source_spec": str(args.spec),
        "validation_artifact": str(args.validation),
        "routing_artifact": str(args.routing_json),
        "oracle": oracle_meta,
        "rows": [],
        "claim_boundary": (
            "Current-calibration engineering sweep over the frozen sampled Fez patches. "
            "Independent gate-error products are exposure proxies, not hardware fidelity predictions."
        ),
    }

    print("ZERO-QPU TCT FEZ PATCH CALIBRATION SWEEP")
    print(
        f"backend={fez.name} calibration_last_update={result['calibration_last_update']} "
        f"patches={len(refs)} logical_width={qc.num_qubits} rounds={rounds}"
    )
    print("patch rank seed CZ mean_CZ_error sum_p_CZ log10_noerr duration_ms dur/T1 exact")

    for ref in refs:
        idx = int(ref["patch_index"])
        pred = pred_by_idx.get(idx)
        if pred is None or not pred.get("patch_nodes"):
            raise RuntimeError(f"missing physical nodes for patch {idx}")
        nodes = [int(x) for x in pred["patch_nodes"]]
        seed = int(ref["seed_transpiler"])

        compiled, stats = cal.compile_frozen_patch(
            qc, fez_full, nodes, seed, args.profile, args.optimization_level
        )
        exact = (
            int(stats["native_cz"]) == int(ref["native_cz"])
            and int(stats["compiled_depth"]) == int(ref["compiled_depth"])
        )

        op_rows = cal.op_calibration_rows(compiled, fez, nodes)
        cz = cal.cz_edge_summary(op_rows)
        all_err = cal.error_summary(op_rows)
        timing = cal.critical_path_duration(compiled, op_rows)
        qp = cal.qubit_properties(fez, nodes)

        mean_cz = finite_or_none(cz.get("per_operation_error", {}).get("mean"))
        sum_p_cz = finite_or_none(cz.get("expected_error_events_sum_p"))
        log10_cz = finite_or_none(cz.get("log10_independent_no_error_proxy"))
        duration_s = finite_or_none(timing.get("critical_path_duration_s")) or 0.0
        t1_med = finite_or_none(qp.get("t1_s", {}).get("median"))
        t2_med = finite_or_none(qp.get("t2_s", {}).get("median"))
        d_t1 = None if not t1_med else duration_s / t1_med
        d_t2 = None if not t2_med else duration_s / t2_med

        row = {
            "patch_index": idx,
            "predictor_rank": int(pred.get("predictor_rank", -1)),
            "patch_diameter": int(pred.get("patch_diameter", -1)),
            "physical_nodes": nodes,
            "seed_transpiler": seed,
            "reference_native_cz": int(ref["native_cz"]),
            "reference_depth": int(ref["compiled_depth"]),
            "recompiled_native_cz": int(stats["native_cz"]),
            "recompiled_depth": int(stats["compiled_depth"]),
            "exact_compile_reproduction": bool(exact),
            "cz": cz,
            "all_gate_error_exposure": all_err,
            "timing": timing,
            "qubit_properties": qp,
            "duration_over_median_t1": d_t1,
            "duration_over_median_t2": d_t2,
        }
        result["rows"].append(row)
        print(
            f"{idx:02d} {row['predictor_rank']:02d} {seed} {stats['native_cz']} "
            f"{mean_cz:.6g} {sum_p_cz:.3f} {log10_cz:.3f} "
            f"{duration_s*1e3:.3f} {d_t1:.2f} {exact}"
        )

    def by_survival(r):
        v = r["cz"].get("log10_independent_no_error_proxy")
        return -math.inf if v is None else float(v)

    best_survival = max(result["rows"], key=by_survival)
    best_sum_p = min(
        result["rows"],
        key=lambda r: float(r["cz"].get("expected_error_events_sum_p", math.inf)),
    )
    topo_best = min(result["rows"], key=lambda r: (r["reference_native_cz"], r["reference_depth"]))
    result["summary"] = {
        "topology_best_patch": int(topo_best["patch_index"]),
        "calibration_best_by_log10_no_error_patch": int(best_survival["patch_index"]),
        "calibration_best_by_sum_p_patch": int(best_sum_p["patch_index"]),
        "topology_best": {
            "CZ": topo_best["recompiled_native_cz"],
            "mean_cz_error": topo_best["cz"]["per_operation_error"].get("mean"),
            "sum_p_cz": topo_best["cz"].get("expected_error_events_sum_p"),
            "log10_no_error_proxy": topo_best["cz"].get("log10_independent_no_error_proxy"),
            "critical_path_s": topo_best["timing"].get("critical_path_duration_s"),
        },
        "calibration_best": {
            "patch_index": int(best_survival["patch_index"]),
            "CZ": best_survival["recompiled_native_cz"],
            "mean_cz_error": best_survival["cz"]["per_operation_error"].get("mean"),
            "sum_p_cz": best_survival["cz"].get("expected_error_events_sum_p"),
            "log10_no_error_proxy": best_survival["cz"].get("log10_independent_no_error_proxy"),
            "critical_path_s": best_survival["timing"].get("critical_path_duration_s"),
        },
    }

    print("\n===== CALIBRATION-AWARE PATCH SUMMARY =====")
    print(
        f"topology_best_patch={topo_best['patch_index']} "
        f"calibration_best_patch={best_survival['patch_index']} "
        f"min_sum_p_patch={best_sum_p['patch_index']}"
    )
    print(
        "topology_best: "
        f"CZ={topo_best['recompiled_native_cz']} "
        f"mean_CZ_error={topo_best['cz']['per_operation_error'].get('mean')} "
        f"sum_p={topo_best['cz'].get('expected_error_events_sum_p')} "
        f"log10_noerr={topo_best['cz'].get('log10_independent_no_error_proxy')}"
    )
    print(
        "calibration_best: "
        f"CZ={best_survival['recompiled_native_cz']} "
        f"mean_CZ_error={best_survival['cz']['per_operation_error'].get('mean')} "
        f"sum_p={best_survival['cz'].get('expected_error_events_sum_p')} "
        f"log10_noerr={best_survival['cz'].get('log10_independent_no_error_proxy')}"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=cal.jsonable) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
