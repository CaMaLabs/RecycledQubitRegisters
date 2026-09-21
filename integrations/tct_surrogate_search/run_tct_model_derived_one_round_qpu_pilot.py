#!/usr/bin/env python3
"""Guarded IBM Fez pilot for the one-round model-derived TCT predicate.

Default behavior is PRE-FLIGHT ONLY. No QPU job is submitted unless --run is
explicitly supplied.

The script consumes the zero-QPU round-feasibility artifact, takes its frozen
best-round candidate (currently one Grover round on Fez patch 10 / seed 42),
reconstructs the TCT predicate from the reduced-order formula, fixed-point
threshold, and finite parameter codebooks, and prepares two circuits on the
same initial physical patch:

1. uniform_baseline: H on the nine parameter qubits, then measure;
2. one_round_grover: the model-derived one-round Grover circuit, then measure.

Before submission it recompiles both circuits against the current authenticated
ibm_fez target, audits the candidate's current CZ error exposure and calibrated
critical-path duration, verifies that the transpiler did not leave the frozen
physical patch, and applies conservative preregistered guardrails.

If any guardrail fails, submission is refused even when --run was supplied.
Calibration products are engineering proxies, not predicted hardware fidelity.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_grid_factored_shift_fez_calibration as cal
import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-21-tct-model-derived-one-round-qpu-pilot-v1"
DEFAULT_FEASIBILITY = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_round_feasibility.json"
)
DEFAULT_OUTDIR = ROOT / "results" / "tct_surrogate_search" / "qpu_pilot"


def add_param_measurements(qc: QuantumCircuit, parameter_bits: int = 9) -> QuantumCircuit:
    out = qc.copy()
    creg = ClassicalRegister(parameter_bits, "params")
    out.add_register(creg)
    for i in range(parameter_bits):
        out.measure(i, creg[i])
    return out


def build_uniform_baseline(logical_width: int, parameter_bits: int = 9) -> QuantumCircuit:
    qc = QuantumCircuit(logical_width)
    qc.h(list(range(parameter_bits)))
    return add_param_measurements(qc, parameter_bits)


def compile_physical(circuit, backend, patch_nodes: list[int], seed: int, level: int):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=int(level),
        seed_transpiler=int(seed),
        initial_layout=list(patch_nodes),
    )
    compiled = pm.run(circuit)
    return compiled


def physical_touched_qubits(compiled) -> list[int]:
    touched = set()
    for item in compiled.data:
        for q in item.qubits:
            touched.add(int(compiled.find_bit(q).index))
    return sorted(touched)


def physical_op_rows(compiled, backend) -> list[dict]:
    rows = []
    for item in compiled.data:
        name = str(item.operation.name)
        if name == "barrier":
            continue
        physical = tuple(int(compiled.find_bit(q).index) for q in item.qubits)
        if name == "delay":
            rows.append({
                "name": name,
                "local_qubits": list(physical),
                "physical_qubits": list(physical),
                "error": None,
                "duration_s": None,
                "calibration_found": False,
            })
            continue
        prop, used, found = cal.target_instruction_properties(backend, name, physical)
        error = None if prop is None else getattr(prop, "error", None)
        duration = None if prop is None else getattr(prop, "duration", None)
        virtual_default = False
        if name == "rz" and (prop is None or duration is None):
            duration = 0.0
            if error is None:
                error = 0.0
            virtual_default = True
        rows.append({
            "name": name,
            "local_qubits": list(physical),
            "physical_qubits": list(physical),
            "lookup_physical_qubits": None if used is None else list(used),
            "error": None if error is None else float(error),
            "duration_s": None if duration is None else float(duration),
            "calibration_found": bool(found),
            "virtual_rz_default": virtual_default,
        })
    return rows


def physical_critical_path(compiled, rows: list[dict]) -> dict:
    ready = [0.0] * compiled.num_qubits
    missing = {}
    calibrated = 0
    for item, row in zip(
        [i for i in compiled.data if str(i.operation.name) != "barrier"], rows
    ):
        qs = [int(compiled.find_bit(q).index) for q in item.qubits]
        d = row.get("duration_s")
        if d is None:
            name = row["name"]
            missing[name] = missing.get(name, 0) + 1
            d = 0.0
        else:
            calibrated += 1
        if not qs:
            continue
        start = max(ready[q] for q in qs)
        finish = start + float(d)
        for q in qs:
            ready[q] = finish
    return {
        "critical_path_duration_s": max(ready) if ready else 0.0,
        "duration_calibration_coverage_fraction": 0.0 if not rows else calibrated / len(rows),
        "missing_duration_counts": missing,
        "is_lower_bound_if_missing": bool(missing),
    }


def compile_stats(original, compiled) -> dict:
    stats = mapper.compiled_stats(original, compiled, 0.0)
    return {
        "native_cz": int(stats["native_cz"]),
        "compiled_depth": int(stats["compiled_depth"]),
        "compiled_size": int(stats["compiled_size"]),
        "compiled_touched_qubits": int(stats["compiled_touched_qubits"]),
    }


def calibration_audit(compiled, backend, patch_nodes: list[int]) -> dict:
    rows = physical_op_rows(compiled, backend)
    cz = cal.cz_edge_summary(rows)
    allerr = cal.error_summary(rows)
    timing = physical_critical_path(compiled, rows)
    qprops = cal.qubit_properties(backend, patch_nodes)
    duration = float(timing["critical_path_duration_s"])
    t1 = qprops.get("t1_s", {}).get("median")
    t2 = qprops.get("t2_s", {}).get("median")
    return {
        "cz_count": int(cz["cz_count"]),
        "cz_mean_error": cz.get("per_operation_error", {}).get("mean"),
        "cz_sum_p": cz.get("expected_error_events_sum_p"),
        "cz_log10_no_error_proxy": cz.get("log10_independent_no_error_proxy"),
        "all_gate_sum_p": allerr.get("all_gates", {}).get("expected_error_events_sum_p"),
        "critical_path_s": duration,
        "duration_us": 1e6 * duration,
        "median_t1_s": t1,
        "median_t2_s": t2,
        "duration_over_median_t1": None if not t1 else duration / float(t1),
        "duration_over_median_t2": None if not t2 else duration / float(t2),
        "duration_coverage": timing.get("duration_calibration_coverage_fraction"),
        "missing_duration_counts": timing.get("missing_duration_counts"),
    }


def parse_counts(counts: dict[str, int], marked_states: set[int], shots: int) -> dict:
    marked_hits = 0
    parsed = {}
    for key, count in counts.items():
        bits = str(key).replace(" ", "")
        state = int(bits, 2)
        parsed[str(state)] = parsed.get(str(state), 0) + int(count)
        if state in marked_states:
            marked_hits += int(count)
    return {
        "shots": int(shots),
        "marked_hits": int(marked_hits),
        "marked_fraction": 0.0 if shots <= 0 else marked_hits / shots,
        "state_counts_decimal": parsed,
        "raw_counts": counts,
    }


def two_proportion_z(a_hits: int, a_n: int, b_hits: int, b_n: int) -> float | None:
    if a_n <= 0 or b_n <= 0:
        return None
    p1 = a_hits / a_n
    p2 = b_hits / b_n
    pooled = (a_hits + b_hits) / (a_n + b_n)
    se = math.sqrt(max(pooled * (1.0 - pooled) * (1.0 / a_n + 1.0 / b_n), 0.0))
    if se == 0.0:
        return None
    return (p2 - p1) / se


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--feasibility", type=Path, default=DEFAULT_FEASIBILITY)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--max-execution-time", type=int, default=120)
    ap.add_argument("--max-cz", type=int, default=750)
    ap.add_argument("--max-cz-sum-p", type=float, default=1.5)
    ap.add_argument("--max-duration-over-t1", type=float, default=0.5)
    ap.add_argument("--max-duration-over-t2", type=float, default=0.5)
    ap.add_argument("--run", action="store_true", help="Actually submit the two-circuit QPU job")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    if args.shots < 1:
        raise SystemExit("--shots must be positive")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    feas = json.loads(args.feasibility.read_text(encoding="utf-8"))
    if feas.get("experiment") != "tct_model_derived_round_feasibility_v1":
        raise RuntimeError("unexpected feasibility artifact")

    selected_summary = feas.get("ranking_heuristic_best_round")
    if not selected_summary:
        raise RuntimeError("feasibility artifact has no ranking_heuristic_best_round")
    selected = selected_summary["maximum_ranking_heuristic"]
    rounds = int(selected_summary["rounds"])
    patch_nodes = [int(x) for x in selected["patch_nodes"]]
    patch_index = int(selected["patch_index"])
    seed = int(selected["seed_transpiler"])

    candidate_unmeasured, oracle = sweep.build_model_derived_circuit(spec, rounds)
    if rounds != 1:
        raise RuntimeError(
            f"guarded pilot is intentionally restricted to one round; feasibility selected {rounds}"
        )
    parameter_bits = int(oracle["parameter_bits"])
    marked_states = {int(x) for x in oracle["derived_marked_states"]}
    candidate = add_param_measurements(candidate_unmeasured, parameter_bits)
    baseline = build_uniform_baseline(candidate_unmeasured.num_qubits, parameter_bits)

    service = width.ref.ibm_base.make_service()
    usage_before = width.ref.ibm_base.safe_usage(service)
    backend = width.ref.ibm_base.select_backend(service, candidate.num_qubits, args.backend)

    compiled_baseline = compile_physical(
        baseline, backend, patch_nodes, seed, args.optimization_level
    )
    compiled_candidate = compile_physical(
        candidate, backend, patch_nodes, seed, args.optimization_level
    )

    patch_set = set(patch_nodes)
    touched_baseline = physical_touched_qubits(compiled_baseline)
    touched_candidate = physical_touched_qubits(compiled_candidate)
    baseline_inside = set(touched_baseline).issubset(patch_set)
    candidate_inside = set(touched_candidate).issubset(patch_set)

    baseline_stats = compile_stats(baseline, compiled_baseline)
    candidate_stats = compile_stats(candidate, compiled_candidate)
    audit = calibration_audit(compiled_candidate, backend, patch_nodes)

    guardrails = {
        "one_round_only": rounds == 1,
        "candidate_stays_on_frozen_patch": candidate_inside,
        "baseline_stays_on_frozen_patch": baseline_inside,
        "cz_at_most_limit": candidate_stats["native_cz"] <= args.max_cz,
        "cz_sum_p_at_most_limit": (
            audit["cz_sum_p"] is not None and float(audit["cz_sum_p"]) <= args.max_cz_sum_p
        ),
        "duration_over_t1_at_most_limit": (
            audit["duration_over_median_t1"] is not None
            and float(audit["duration_over_median_t1"]) <= args.max_duration_over_t1
        ),
        "duration_over_t2_at_most_limit": (
            audit["duration_over_median_t2"] is not None
            and float(audit["duration_over_median_t2"]) <= args.max_duration_over_t2
        ),
        "duration_calibration_complete": (
            float(audit.get("duration_coverage") or 0.0) >= 0.999999
            and not audit.get("missing_duration_counts")
        ),
    }
    all_guardrails_pass = all(bool(v) for v in guardrails.values())

    ideal_uniform = len(marked_states) / (1 << parameter_bits)
    ideal_grover = float(selected["ideal_grover_success"])

    out = {
        "experiment": "tct_model_derived_one_round_qpu_pilot_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_spec": str(args.spec),
        "source_feasibility": str(args.feasibility),
        "backend": str(backend.name),
        "calibration_last_update": cal.calibration_timestamp(backend),
        "rounds": rounds,
        "patch_index": patch_index,
        "patch_nodes": patch_nodes,
        "seed_transpiler": seed,
        "shots_per_circuit": int(args.shots),
        "parameter_bits": parameter_bits,
        "derived_marked_states": sorted(marked_states),
        "ideal_uniform_marked_fraction": ideal_uniform,
        "ideal_grover_marked_fraction": ideal_grover,
        "baseline_stats": baseline_stats,
        "candidate_stats": candidate_stats,
        "baseline_touched_physical_qubits": touched_baseline,
        "candidate_touched_physical_qubits": touched_candidate,
        "candidate_calibration_audit": audit,
        "guardrail_limits": {
            "max_cz": args.max_cz,
            "max_cz_sum_p": args.max_cz_sum_p,
            "max_duration_over_t1": args.max_duration_over_t1,
            "max_duration_over_t2": args.max_duration_over_t2,
        },
        "guardrails": guardrails,
        "all_guardrails_pass": all_guardrails_pass,
        "account_usage_before": usage_before,
        "qpu_job_submitted": False,
        "claim_boundary": (
            "Pilot of a finite-codebook, model-derived TCT threshold predicate. "
            "The uniform-vs-one-round comparison tests marked-state amplification on hardware; "
            "it is not fusion validation and cannot establish end-to-end quantum advantage."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    preflight_path = args.outdir / "tct_model_derived_one_round_qpu_pilot_preflight.json"
    preflight_path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print("TCT MODEL-DERIVED ONE-ROUND QPU PILOT PREFLIGHT")
    print(
        f"backend={backend.name} calibration_last_update={out['calibration_last_update']} "
        f"patch={patch_index} seed={seed} shots={args.shots}"
    )
    print(
        f"baseline: CZ={baseline_stats['native_cz']} depth={baseline_stats['compiled_depth']} "
        f"touched={touched_baseline}"
    )
    print(
        f"candidate: CZ={candidate_stats['native_cz']} depth={candidate_stats['compiled_depth']} "
        f"sum_p_CZ={audit['cz_sum_p']:.3f} log10_noerr={audit['cz_log10_no_error_proxy']:.3f} "
        f"duration_us={audit['duration_us']:.1f} "
        f"dur/T1={audit['duration_over_median_t1']:.3f} "
        f"dur/T2={audit['duration_over_median_t2']:.3f}"
    )
    print("guardrails=" + json.dumps(guardrails, sort_keys=True))
    print(f"all_guardrails_pass={all_guardrails_pass}")
    print(f"saved preflight {preflight_path.resolve()}")

    if not args.run:
        print("NO QPU JOB SUBMITTED. Add --run only after reviewing this preflight.")
        return 0

    if not all_guardrails_pass:
        raise SystemExit("REFUSING QPU SUBMISSION: one or more preregistered guardrails failed")

    print(f"Submitting paired baseline + one-round candidate: 2 circuits x {args.shots} shots")
    sampler = SamplerV2(mode=backend, options={"max_execution_time": args.max_execution_time})
    job = sampler.run([compiled_baseline, compiled_candidate], shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    baseline_counts = pubs[0].data.params.get_counts()
    candidate_counts = pubs[1].data.params.get_counts()
    b = parse_counts(baseline_counts, marked_states, args.shots)
    c = parse_counts(candidate_counts, marked_states, args.shots)
    z = two_proportion_z(b["marked_hits"], args.shots, c["marked_hits"], args.shots)

    out.update({
        "qpu_job_submitted": True,
        "job_id": job.job_id(),
        "job_metrics": width.ref.ibm_base.safe_metrics(job),
        "account_usage_after": width.ref.ibm_base.safe_usage(service),
        "hardware_results": {
            "uniform_baseline": b,
            "one_round_grover": c,
            "marked_fraction_difference": c["marked_fraction"] - b["marked_fraction"],
            "marked_fraction_ratio": None if b["marked_fraction"] == 0 else c["marked_fraction"] / b["marked_fraction"],
            "two_proportion_z_approx": z,
        },
    })

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = args.outdir / f"tct_model_derived_one_round_qpu_pilot_{stamp}.json"
    result_path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print("RESULT")
    print(
        f"baseline marked={b['marked_hits']}/{args.shots}={b['marked_fraction']:.6f} | "
        f"candidate marked={c['marked_hits']}/{args.shots}={c['marked_fraction']:.6f} | "
        f"difference={c['marked_fraction'] - b['marked_fraction']:.6f} | z~{z}"
    )
    print("saved", result_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
