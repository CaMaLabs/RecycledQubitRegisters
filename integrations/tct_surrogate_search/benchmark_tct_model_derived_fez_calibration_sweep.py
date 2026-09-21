#!/usr/bin/env python3
"""Zero-QPU Fez routing/calibration sweep for the model-derived TCT predicate.

This builds the six-round 10-qubit TCT phase oracle directly from the reduced-
order loss formula, fixed-point threshold, and finite parameter codebooks using
benchmark_tct_model_derived_threshold_predicate.py.  It does not use the frozen
marked-state list to construct the oracle.

The script samples connected exact-width Fez patches, compiles Qiskit-auto
layouts across multiple transpiler seeds on each patch, maps the resulting local
qubits back to authenticated ibm_fez physical qubits, and evaluates current CZ
error exposure and calibrated critical-path duration.  It then reports both the
lowest-CZ candidate and the lowest calibration-weighted CZ-exposure candidate.

Calibration products are engineering proxies, not measured circuit fidelity.
No Sampler is instantiated and no QPU job is submitted.
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
import benchmark_tct_model_derived_threshold_predicate as model
import benchmark_tct_semantic_factored_oracle as semantic
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-20-tct-model-derived-fez-calibration-sweep-v1"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_model_derived_fez_calibration_sweep.json"


def build_model_derived_circuit(spec: dict, rounds: int):
    """Construct the predicate from formula/threshold/codebooks only."""
    n = int(spec["parameter_register_bits"]["total_parameter_bits"])
    rows = model.enumerate_model_rows(spec)
    feasibility = model.feasibility_by_parameter(spec, rows)
    marked_rows = model.derived_marked_rows(spec, rows)
    model_states = model.state_set_from_rows(spec, marked_rows)
    common = model.common_constraints_from_necessary_sets(spec, feasibility)
    observed_common = semantic.common_constraints(sorted(model_states), n)
    if common != observed_common:
        raise AssertionError("necessary-code and model-state common constraints disagree")

    local_bits = [bit for bit in range(n) if bit not in common]
    local_marked = {semantic.local_state(state, local_bits) for state in model_states}
    esop_local = semantic.minimum_esop(local_marked, len(local_bits))
    esop_full = [
        semantic.merge_local_cube(cube, local_bits, common, n)
        for cube in esop_local
    ]
    model.verify_formula_predicate_all_basis(spec, esop_full, model_states)

    qc = semantic.build_variant(
        n,
        sorted(model_states),
        None,
        rounds,
        factored=True,
        local_cubes=esop_local,
        local_bits=local_bits,
        common=common,
    )
    return qc, {
        "construction_uses_frozen_marked_indices": False,
        "parameter_bits": n,
        "logical_width": int(qc.num_qubits),
        "derived_marked_count": len(model_states),
        "derived_marked_states": sorted(int(x) for x in model_states),
        "common_constraints": {str(k): int(v) for k, v in sorted(common.items())},
        "local_bits": [int(x) for x in local_bits],
        "local_esop": [semantic.audit.compact_cube(c) for c in esop_local],
        "basis_truth_table_verified_512": True,
    }


def summarize_candidate(compiled, stats: dict, fez, patch_nodes: list[int], seed: int) -> dict:
    op_rows = cal.op_calibration_rows(compiled, fez, patch_nodes)
    cz = cal.cz_edge_summary(op_rows)
    allerr = cal.error_summary(op_rows)
    timing = cal.critical_path_duration(compiled, op_rows)
    qprops = cal.qubit_properties(fez, patch_nodes)
    ratios = cal.add_coherence_ratios(qprops, timing)
    parameter_qubits, layout_error = cal.final_parameter_physical_qubits(
        compiled, patch_nodes, 9
    )
    readout = cal.readout_summary(fez, parameter_qubits, layout_error)
    return {
        "seed_transpiler": int(seed),
        "native_cz": int(stats["native_cz"]),
        "compiled_depth": int(stats["compiled_depth"]),
        "compiled_size": int(stats["compiled_size"]),
        "compile_seconds": float(stats["compile_seconds"]),
        "cz_mean_error": cz.get("per_operation_error", {}).get("mean"),
        "cz_sum_p": cz.get("expected_error_events_sum_p"),
        "cz_log10_no_error_proxy": cz.get("log10_independent_no_error_proxy"),
        "cz_calibration_coverage": cz.get("calibration_coverage_fraction"),
        "all_gate_sum_p": allerr.get("all_gates", {}).get("expected_error_events_sum_p"),
        "all_gate_log10_no_error_proxy": allerr.get("all_gates", {}).get("log10_independent_no_error_proxy"),
        "critical_path_s": float(timing["critical_path_duration_s"]),
        "duration_coverage": timing.get("duration_calibration_coverage_fraction"),
        "duration_over_median_t1": ratios.get("duration_over_t1_s_median"),
        "duration_over_median_t2": ratios.get("duration_over_t2_s_median"),
        "readout": readout,
    }


def best_by_exposure(rows: list[dict]) -> dict:
    return min(
        rows,
        key=lambda r: (
            math.inf if r.get("cz_sum_p") is None else float(r["cz_sum_p"]),
            int(r["native_cz"]),
            int(r["compiled_depth"]),
            int(r["seed_transpiler"]),
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--grover-rounds", type=int, default=6)
    ap.add_argument("--candidate-patches", type=int, default=24)
    ap.add_argument("--patch-seed", type=int, default=424242)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--transpiler-seeds", default="8776,2026,9401,42,1337")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.grover_rounds < 1 or args.candidate_patches < 1:
        raise SystemExit("invalid arguments")
    seeds = [int(x.strip()) for x in args.transpiler_seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("at least one transpiler seed is required")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    qc, oracle = build_model_derived_circuit(spec, args.grover_rounds)
    logical = int(qc.num_qubits)

    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, logical, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    patches = ens.patch_ensemble(fez_full, logical, args.candidate_patches, args.patch_seed)

    # Fully connected reference for a stable compiler baseline.
    probe_backend = topo.generic(logical, mapper.full_coupling(logical))
    probe_compiled, probe_elapsed = mapper.compile_circuit(
        qc, probe_backend, args.profile, args.optimization_level, 8776, list(range(logical))
    )
    probe_stats = mapper.compiled_stats(qc, probe_compiled, probe_elapsed)

    result = {
        "experiment": "tct_model_derived_fez_calibration_sweep_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "backend": str(fez.name),
        "calibration_last_update": cal.calibration_timestamp(fez),
        "oracle": oracle,
        "grover_rounds": int(args.grover_rounds),
        "candidate_patches": int(args.candidate_patches),
        "patch_seed": int(args.patch_seed),
        "transpiler_seeds": seeds,
        "fully_connected_reference": probe_stats,
        "rows": [],
        "claim_boundary": (
            "Finite-codebook model-derived threshold predicate routed on authenticated Fez connectivity. "
            "Calibration-weighted error products are engineering proxies, not measured fidelity. "
            "No QPU execution, fusion-physics validation, or end-to-end quantum-advantage claim."
        ),
    }

    print("ZERO-QPU TCT MODEL-DERIVED FEZ CALIBRATION SWEEP")
    print(
        f"backend={fez.name} calibration_last_update={result['calibration_last_update']} "
        f"logical_width={logical} rounds={args.grover_rounds} patches={len(patches)} seeds={seeds}"
    )
    print(
        f"fully_connected: CZ={probe_stats['native_cz']} depth={probe_stats['compiled_depth']} "
        f"size={probe_stats['compiled_size']}"
    )

    for patch in patches:
        patch_index = int(patch["patch_index"])
        nodes = [int(x) for x in patch["nodes"]]
        subcm = cap.relabeled_subgraph(fez_full, nodes)
        backend = topo.generic(logical, subcm)
        candidates = []
        for seed in seeds:
            compiled, elapsed = mapper.compile_circuit(
                qc, backend, args.profile, args.optimization_level, seed, None
            )
            stats = mapper.compiled_stats(qc, compiled, elapsed)
            if int(stats["compiled_touched_qubits"]) > logical:
                raise AssertionError("exact-width capacity lock violated")
            row = summarize_candidate(compiled, stats, fez, nodes, seed)
            row.update({
                "patch_index": patch_index,
                "patch_mode": patch["mode"],
                "patch_nodes": nodes,
                "patch_undirected_edges": int(patch["stats"]["undirected_edges"]),
                "patch_mean_degree": float(patch["stats"]["degree_mean"]),
            })
            candidates.append(row)

        best = best_by_exposure(candidates)
        result["rows"].append(best)
        print(
            f"patch={patch_index:02d} seed={best['seed_transpiler']:4d} "
            f"CZ={best['native_cz']:5d} depth={best['compiled_depth']:6d} "
            f"mean_CZ_error={best['cz_mean_error']:.6g} sum_p_CZ={best['cz_sum_p']:.3f} "
            f"log10_noerr={best['cz_log10_no_error_proxy']:.3f} "
            f"duration_us={1e6*best['critical_path_s']:.1f} "
            f"dur/T1={best['duration_over_median_t1']:.3f}"
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    by_cz = min(result["rows"], key=lambda r: (int(r["native_cz"]), int(r["compiled_depth"])))
    by_exposure = best_by_exposure(result["rows"])
    by_duration = min(result["rows"], key=lambda r: float(r["critical_path_s"]))
    result["best"] = {
        "minimum_cz": by_cz,
        "minimum_cz_error_exposure": by_exposure,
        "minimum_critical_path": by_duration,
    }
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("\n===== MODEL-DERIVED FEZ CALIBRATION SUMMARY =====")
    print(
        f"minimum_CZ: patch={by_cz['patch_index']} seed={by_cz['seed_transpiler']} "
        f"CZ={by_cz['native_cz']} depth={by_cz['compiled_depth']} sum_p={by_cz['cz_sum_p']:.3f} "
        f"duration_us={1e6*by_cz['critical_path_s']:.1f}"
    )
    print(
        f"minimum_exposure: patch={by_exposure['patch_index']} seed={by_exposure['seed_transpiler']} "
        f"CZ={by_exposure['native_cz']} depth={by_exposure['compiled_depth']} "
        f"sum_p={by_exposure['cz_sum_p']:.3f} log10_noerr={by_exposure['cz_log10_no_error_proxy']:.3f} "
        f"duration_us={1e6*by_exposure['critical_path_s']:.1f} "
        f"dur/T1={by_exposure['duration_over_median_t1']:.3f} "
        f"dur/T2={by_exposure['duration_over_median_t2']:.3f}"
    )
    print(
        f"minimum_duration: patch={by_duration['patch_index']} seed={by_duration['seed_transpiler']} "
        f"CZ={by_duration['native_cz']} duration_us={1e6*by_duration['critical_path_s']:.1f} "
        f"sum_p={by_duration['cz_sum_p']:.3f}"
    )
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
