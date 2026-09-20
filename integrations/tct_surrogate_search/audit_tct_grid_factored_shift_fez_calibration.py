#!/usr/bin/env python3
"""Calibration-aware zero-QPU feasibility audit for the routed TCT oracle.

This consumes the validated TCT arithmetic specification/validation artifacts and
an exhaustive routing JSON, rebuilds the six-round 25-qubit grid-factored
coherent objective circuit, recompiles the best sampled Fez qiskit-auto patch,
and maps the resulting local physical qubits back onto authenticated ibm_fez
physical qubits.

It then reads the *current* backend target calibration metadata and reports:

* gate-error exposure by gate type and by CZ edge;
* an independent-gate no-error product proxy (reported primarily in log10 form);
* an ASAP critical-path duration using calibrated instruction durations;
* patch T1/T2 context and circuit-duration/coherence ratios; and
* a final nine-parameter-bit readout-error product proxy when the final layout
  can be recovered.

These are calibration-based engineering proxies, not a hardware fidelity
prediction. Correlated errors, crosstalk, leakage, drift, DD, pulse scheduling,
and error mitigation are not modeled. No Sampler is instantiated and no QPU job
is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import benchmark_tct_grid_factored_shift_routing as routing
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-20-tct-fez-calibration-audit-v1"
DEFAULT_VALIDATION = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_oracle_validation.json"
DEFAULT_ROUTING = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_routing_6round_exhaustive_seed314159.json"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_fez_calibration_audit.json"


def jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return str(value)


def safe_stats(values: list[float]) -> dict:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not vals:
        return {"count": 0}
    vals.sort()
    return {
        "count": len(vals),
        "min": min(vals),
        "median": statistics.median(vals),
        "mean": statistics.fmean(vals),
        "max": max(vals),
    }


def target_instruction_properties(backend, name: str, qargs: tuple[int, ...]):
    """Best-effort current Target InstructionProperties lookup.

    CZ is symmetric for this audit's topology treatment, so a reversed qarg
    lookup is accepted when the backend target exposes only one orientation.
    """
    try:
        table = backend.target[name]
    except Exception:
        return None, None, False
    prop = None
    used_qargs = qargs
    try:
        prop = table.get(qargs)
    except Exception:
        try:
            prop = table[qargs]
        except Exception:
            prop = None
    if prop is None and len(qargs) == 2:
        rev = tuple(reversed(qargs))
        try:
            prop = table.get(rev)
        except Exception:
            try:
                prop = table[rev]
            except Exception:
                prop = None
        if prop is not None:
            used_qargs = rev
    return prop, used_qargs, prop is not None


def calibration_timestamp(backend):
    try:
        props = backend.properties()
        ts = getattr(props, "last_update_date", None)
        return None if ts is None else str(ts)
    except Exception:
        return None


def qubit_properties(backend, physical_nodes: list[int]) -> dict:
    props = getattr(backend.target, "qubit_properties", None)
    rows = []
    if props is None:
        return {"available": False, "rows": [], "t1_s": {"count": 0}, "t2_s": {"count": 0}}
    for q in physical_nodes:
        try:
            p = props[q]
        except Exception:
            p = None
        rows.append({
            "physical_qubit": int(q),
            "t1_s": None if p is None else getattr(p, "t1", None),
            "t2_s": None if p is None else getattr(p, "t2", None),
            "frequency_hz": None if p is None else getattr(p, "frequency", None),
        })
    return {
        "available": True,
        "rows": rows,
        "t1_s": safe_stats([r["t1_s"] for r in rows if r["t1_s"] is not None]),
        "t2_s": safe_stats([r["t2_s"] for r in rows if r["t2_s"] is not None]),
    }


def best_fez_auto_row(routing_json: dict) -> tuple[dict, dict]:
    rows = [
        r for r in routing_json.get("compile_rows", [])
        if r.get("success")
        and r.get("topology") == "fez_heavy_hex_topology"
        and r.get("layout_mode") == "qiskit_auto"
    ]
    if not rows:
        raise RuntimeError("routing JSON contains no successful Fez qiskit_auto rows")
    best = min(rows, key=lambda r: (int(r["native_cz"]), int(r["compiled_depth"])))
    predicted = routing_json.get("topologies", {}).get("fez_heavy_hex_topology", {}).get("predicted", [])
    pred = next((p for p in predicted if int(p["patch_index"]) == int(best["patch_index"])), None)
    if pred is None:
        raise RuntimeError(f"routing JSON missing predicted patch {best['patch_index']}")
    nodes = pred.get("patch_nodes")
    if not nodes:
        raise RuntimeError("routing JSON patch is missing patch_nodes")
    return best, pred


def compile_frozen_patch(qc, fez_full, patch_nodes: list[int], seed: int, profile: str, level: int):
    subcm = cap.relabeled_subgraph(fez_full, patch_nodes)
    backend = topo.generic(qc.num_qubits, subcm)
    compiled, elapsed = mapper.compile_circuit(qc, backend, profile, level, seed, None)
    stats = mapper.compiled_stats(qc, compiled, elapsed)
    if int(stats["compiled_touched_qubits"]) > qc.num_qubits:
        raise AssertionError("exact-width capacity lock violated")
    return compiled, stats


def op_calibration_rows(compiled, backend, patch_nodes: list[int]):
    rows = []
    for item in compiled.data:
        name = str(item.operation.name)
        if name in {"barrier"}:
            continue
        locals_ = tuple(int(compiled.find_bit(q).index) for q in item.qubits)
        physical = tuple(int(patch_nodes[i]) for i in locals_)
        if name == "delay":
            rows.append({
                "name": name,
                "local_qubits": list(locals_),
                "physical_qubits": list(physical),
                "error": None,
                "duration_s": None,
                "calibration_found": False,
            })
            continue
        prop, used_qargs, found = target_instruction_properties(backend, name, physical)
        error = None if prop is None else getattr(prop, "error", None)
        duration = None if prop is None else getattr(prop, "duration", None)
        # RZ is virtual on IBM hardware; if Target omits explicit properties,
        # use the conventional zero-time/zero-error proxy and mark it as such.
        virtual_default = False
        if name == "rz" and (prop is None or duration is None):
            duration = 0.0
            if error is None:
                error = 0.0
            virtual_default = True
        rows.append({
            "name": name,
            "local_qubits": list(locals_),
            "physical_qubits": list(physical),
            "lookup_physical_qubits": None if used_qargs is None else list(used_qargs),
            "error": None if error is None else float(error),
            "duration_s": None if duration is None else float(duration),
            "calibration_found": bool(found),
            "virtual_rz_default": virtual_default,
        })
    return rows


def error_summary(rows: list[dict]) -> dict:
    grouped = defaultdict(lambda: {"count": 0, "with_error": 0, "sum_error": 0.0, "log_survival": 0.0})
    total = {"count": 0, "with_error": 0, "sum_error": 0.0, "log_survival": 0.0}
    for row in rows:
        if row["name"] in {"delay", "measure"}:
            continue
        g = grouped[row["name"]]
        g["count"] += 1
        total["count"] += 1
        p = row.get("error")
        if p is None:
            continue
        p = min(max(float(p), 0.0), 1.0 - 1e-15)
        g["with_error"] += 1
        g["sum_error"] += p
        g["log_survival"] += math.log1p(-p)
        total["with_error"] += 1
        total["sum_error"] += p
        total["log_survival"] += math.log1p(-p)

    out_groups = {}
    for name, g in sorted(grouped.items()):
        c = g["with_error"]
        out_groups[name] = {
            "count": g["count"],
            "error_coverage_fraction": 0.0 if g["count"] == 0 else c / g["count"],
            "mean_error_when_available": None if c == 0 else g["sum_error"] / c,
            "expected_error_events_sum_p": g["sum_error"],
            "log10_independent_no_error_proxy": None if c == 0 else g["log_survival"] / math.log(10.0),
        }
    return {
        "all_gates": {
            "count": total["count"],
            "error_coverage_fraction": 0.0 if total["count"] == 0 else total["with_error"] / total["count"],
            "expected_error_events_sum_p": total["sum_error"],
            "log10_independent_no_error_proxy": None if total["with_error"] == 0 else total["log_survival"] / math.log(10.0),
        },
        "by_gate": out_groups,
    }


def cz_edge_summary(rows: list[dict]) -> dict:
    by_edge = defaultdict(lambda: {"count": 0, "error": None, "duration_s": None})
    errors = []
    durations = []
    weighted_errors = []
    for row in rows:
        if row["name"] != "cz":
            continue
        edge = tuple(sorted(int(x) for x in row["physical_qubits"]))
        e = by_edge[edge]
        e["count"] += 1
        if row.get("error") is not None:
            e["error"] = float(row["error"])
            errors.append(float(row["error"]))
            weighted_errors.append(float(row["error"]))
        if row.get("duration_s") is not None:
            e["duration_s"] = float(row["duration_s"])
            durations.append(float(row["duration_s"]))
    edge_rows = []
    for edge, d in by_edge.items():
        edge_rows.append({
            "physical_edge": list(edge),
            "count": int(d["count"]),
            "error": d["error"],
            "duration_s": d["duration_s"],
            "error_exposure_count_times_p": None if d["error"] is None else d["count"] * d["error"],
        })
    edge_rows.sort(key=lambda r: (-(r["error_exposure_count_times_p"] or -1.0), -r["count"], r["physical_edge"]))

    cz_rows = [r for r in rows if r["name"] == "cz"]
    cz_with_error = [r for r in cz_rows if r.get("error") is not None]
    log_surv = sum(math.log1p(-min(max(float(r["error"]), 0.0), 1.0 - 1e-15)) for r in cz_with_error)
    return {
        "cz_count": len(cz_rows),
        "calibrated_cz_count": len(cz_with_error),
        "calibration_coverage_fraction": 0.0 if not cz_rows else len(cz_with_error) / len(cz_rows),
        "per_operation_error": safe_stats([float(r["error"]) for r in cz_with_error]),
        "per_operation_duration_s": safe_stats([float(r["duration_s"]) for r in cz_rows if r.get("duration_s") is not None]),
        "expected_error_events_sum_p": sum(float(r["error"]) for r in cz_with_error),
        "log10_independent_no_error_proxy": None if not cz_with_error else log_surv / math.log(10.0),
        "physical_edges_used": len(edge_rows),
        "top_edges_by_error_exposure": edge_rows[:12],
        "edge_rows": edge_rows,
    }


def critical_path_duration(compiled, rows: list[dict]) -> dict:
    ready = [0.0] * compiled.num_qubits
    missing = Counter()
    gate_time_sum = 0.0
    calibrated_ops = 0
    for item, row in zip([i for i in compiled.data if str(i.operation.name) != "barrier"], rows):
        name = row["name"]
        if name == "barrier":
            continue
        locals_ = [int(compiled.find_bit(q).index) for q in item.qubits]
        duration = row.get("duration_s")
        if duration is None:
            missing[name] += 1
            duration = 0.0
        else:
            calibrated_ops += 1
        duration = float(duration)
        gate_time_sum += duration
        if not locals_:
            continue
        start = max(ready[q] for q in locals_)
        finish = start + duration
        for q in locals_:
            ready[q] = finish
    return {
        "critical_path_duration_s": max(ready) if ready else 0.0,
        "sum_of_gate_durations_s": gate_time_sum,
        "duration_calibration_coverage_fraction": 0.0 if not rows else calibrated_ops / len(rows),
        "missing_duration_counts": dict(missing),
        "is_lower_bound_if_missing": bool(missing),
        "per_local_qubit_finish_s": ready,
    }


def final_parameter_physical_qubits(compiled, patch_nodes: list[int], parameter_bits: int) -> tuple[list[int] | None, str | None]:
    layout = getattr(compiled, "layout", None)
    if layout is None:
        return None, "compiled circuit has no layout metadata"
    try:
        final_local = list(layout.final_index_layout(filter_ancillas=True))
    except Exception as exc:
        return None, f"final_index_layout failed: {type(exc).__name__}: {exc}"
    if len(final_local) < parameter_bits:
        return None, f"final layout has only {len(final_local)} entries"
    try:
        physical = [int(patch_nodes[int(final_local[i])]) for i in range(parameter_bits)]
    except Exception as exc:
        return None, f"final layout mapping failed: {type(exc).__name__}: {exc}"
    return physical, None


def readout_summary(backend, physical_qubits: list[int] | None, error_note: str | None) -> dict:
    if physical_qubits is None:
        return {"available": False, "error": error_note}
    rows = []
    log_surv = 0.0
    complete = True
    for q in physical_qubits:
        prop, used, found = target_instruction_properties(backend, "measure", (int(q),))
        p = None if prop is None else getattr(prop, "error", None)
        d = None if prop is None else getattr(prop, "duration", None)
        if p is None:
            complete = False
        else:
            log_surv += math.log1p(-min(max(float(p), 0.0), 1.0 - 1e-15))
        rows.append({
            "physical_qubit": int(q),
            "readout_error": None if p is None else float(p),
            "measure_duration_s": None if d is None else float(d),
            "calibration_found": bool(found),
        })
    return {
        "available": True,
        "parameter_physical_qubits": [int(q) for q in physical_qubits],
        "rows": rows,
        "readout_error": safe_stats([r["readout_error"] for r in rows if r["readout_error"] is not None]),
        "complete_error_coverage": complete,
        "log10_independent_all_nine_correct_proxy": None if not complete else log_surv / math.log(10.0),
    }


def add_coherence_ratios(qprops: dict, timing: dict) -> dict:
    duration = float(timing["critical_path_duration_s"])
    out = {"critical_path_duration_s": duration}
    for label in ("t1_s", "t2_s"):
        st = qprops.get(label, {})
        for stat in ("min", "median", "mean", "max"):
            value = st.get(stat)
            out[f"duration_over_{label}_{stat}"] = None if not value else duration / float(value)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    ap.add_argument("--routing-json", type=Path, default=DEFAULT_ROUTING)
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--grover-rounds", type=int, default=6)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    route = json.loads(args.routing_json.read_text(encoding="utf-8"))
    if not validation.get("all_passed"):
        raise RuntimeError("validation artifact is missing all_passed=True")
    if not route.get("exhaustive"):
        raise RuntimeError("routing artifact must be exhaustive for this audit")

    qc, oracle = routing.build_validated_circuit(spec, validation, args.grover_rounds)
    route_best, pred = best_fez_auto_row(route)
    patch_nodes = [int(x) for x in pred["patch_nodes"]]
    if len(patch_nodes) != qc.num_qubits:
        raise RuntimeError("frozen patch width does not match logical circuit width")

    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, qc.num_qubits, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))

    seed = int(route_best["seed_transpiler"])
    compiled, stats = compile_frozen_patch(
        qc, fez_full, patch_nodes, seed, args.profile, args.optimization_level
    )
    compile_matches = (
        int(stats["native_cz"]) == int(route_best["native_cz"])
        and int(stats["compiled_depth"]) == int(route_best["compiled_depth"])
    )

    rows = op_calibration_rows(compiled, fez, patch_nodes)
    errors = error_summary(rows)
    cz = cz_edge_summary(rows)
    timing = critical_path_duration(compiled, rows)
    qp = qubit_properties(fez, patch_nodes)
    coherence = add_coherence_ratios(qp, timing)
    parameter_physical, parameter_map_error = final_parameter_physical_qubits(
        compiled, patch_nodes, int(oracle["parameter_bits"])
    )
    readout = readout_summary(fez, parameter_physical, parameter_map_error)

    result = {
        "experiment": "tct_grid_factored_shift_fez_calibration_audit_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend_name": str(fez.name),
        "calibration_last_update": calibration_timestamp(fez),
        "source_spec": str(args.spec),
        "validation_artifact": str(args.validation),
        "routing_artifact": str(args.routing_json),
        "oracle": oracle,
        "frozen_routing_best": route_best,
        "frozen_patch_prediction": pred,
        "physical_patch_nodes": patch_nodes,
        "recompiled": stats,
        "recompiled_matches_routing_reference_cz_and_depth": compile_matches,
        "gate_error_exposure": errors,
        "cz_calibration": cz,
        "timing": timing,
        "patch_qubit_properties": qp,
        "coherence_context": coherence,
        "parameter_readout": readout,
        "claim_boundary": (
            "Calibration-aware engineering proxy only. Independent per-gate no-error products are not circuit fidelity estimates; "
            "they ignore correlated noise, crosstalk, coherent error, leakage, drift during execution, dynamical decoupling, "
            "pulse-level scheduling, mitigation, and fault tolerance. Timing is an ASAP duration estimate using current target "
            "instruction durations. No QPU job is submitted."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(jsonable(result), indent=2) + "\n", encoding="utf-8")

    print("ZERO-QPU TCT FEZ CALIBRATION-AWARE FEASIBILITY AUDIT")
    print(
        f"backend={fez.name} calibration_last_update={result['calibration_last_update']} "
        f"patch={route_best['patch_index']} seed={seed} logical_width={qc.num_qubits} rounds={args.grover_rounds}"
    )
    print(
        f"routing_reference: CZ={route_best['native_cz']} depth={route_best['compiled_depth']} | "
        f"recompiled: CZ={stats['native_cz']} depth={stats['compiled_depth']} "
        f"exact_match={compile_matches}"
    )
    print("\n===== CZ CALIBRATION EXPOSURE =====")
    print(
        f"CZ={cz['cz_count']} coverage={cz['calibration_coverage_fraction']:.3%} "
        f"mean_error={cz['per_operation_error'].get('mean')} "
        f"sum_p={cz['expected_error_events_sum_p']:.6g} "
        f"log10_no_error_proxy={cz['log10_independent_no_error_proxy']}"
    )
    print("\n===== ALL CALIBRATED GATE EXPOSURE =====")
    ag = errors["all_gates"]
    print(
        f"ops={ag['count']} error_coverage={ag['error_coverage_fraction']:.3%} "
        f"sum_p={ag['expected_error_events_sum_p']:.6g} "
        f"log10_no_error_proxy={ag['log10_independent_no_error_proxy']}"
    )
    print("\n===== CALIBRATED TIMING / COHERENCE CONTEXT =====")
    print(
        f"critical_path_s={timing['critical_path_duration_s']:.9g} "
        f"duration_coverage={timing['duration_calibration_coverage_fraction']:.3%} "
        f"missing={timing['missing_duration_counts']}"
    )
    print(
        f"T1_median_s={qp['t1_s'].get('median')} T2_median_s={qp['t2_s'].get('median')} "
        f"duration/T1_median={coherence.get('duration_over_t1_s_median')} "
        f"duration/T2_median={coherence.get('duration_over_t2_s_median')}"
    )
    print("\n===== FINAL 9-BIT READOUT PROXY =====")
    if readout.get("available"):
        print(
            f"physical_qubits={readout['parameter_physical_qubits']} "
            f"mean_readout_error={readout['readout_error'].get('mean')} "
            f"log10_all_nine_correct={readout.get('log10_independent_all_nine_correct_proxy')}"
        )
    else:
        print(f"unavailable: {readout.get('error')}")
    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
