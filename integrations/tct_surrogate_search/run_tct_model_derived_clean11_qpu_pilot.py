#!/usr/bin/env python3
"""Guarded IBM Fez pilot for the 11q clean-ancilla one-round TCT predicate.

Default behavior is PRE-FLIGHT ONLY. No QPU job is submitted unless --run is
explicitly supplied.

The script consumes the zero-QPU clean-ancilla HLS artifact, freezes its global
minimum-exposure candidate (currently width 11 / patch 6 / seed 42), rebuilds the
one-round model-derived TCT predicate from the reduced-order formula, threshold,
and finite codebooks, adds one clean helper qubit, and prepares two circuits on
the same physical Fez patch:

1. uniform_baseline: H on the nine parameter qubits, then measure;
2. one_round_clean11: one Grover round, original predicate ancilla, one extra
   clean HLS helper, then measure the nine parameter qubits.

Before submission it recompiles against the current authenticated ibm_fez target,
checks that both circuits remain inside the frozen patch, audits current CZ error
exposure and calibrated critical-path duration, and statevector-verifies the exact
transpiled native candidate including measurement mapping and clean return of both
unmeasured ancillas.

Calibration products are engineering proxies, not predicted hardware fidelity.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime import SamplerV2

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_model_derived_qpu_pilot_postmortem as post
import benchmark_tct_model_derived_clean_ancilla_hls as hls
import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import run_tct_model_derived_one_round_qpu_pilot as pilot
import ibm_qubit_recycling_width_sweep as width

REV = "2026-09-22-tct-model-derived-clean11-qpu-pilot-v1"
DEFAULT_HLS = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_clean_ancilla_hls.json"
)
DEFAULT_OUTDIR = (
    ROOT / "results" / "tct_surrogate_search" / "qpu_pilot_clean11"
)


def semantic_audit(compiled, parameter_bits: int, marked: set[int], expected: float) -> dict:
    compact, meta, c2l = post.compact_native_circuit(compiled, parameter_bits)
    sv = Statevector.from_instruction(compact)
    dist = post.parameter_distribution_from_statevector(sv, c2l, parameter_bits)
    marked_p = post.marked_probability(dist, marked)
    ancilla_probs = [
        post.qubit_one_probability(sv, q)
        for q in meta["unmeasured_local_qubits"]
    ]
    max_unmeasured_p1 = max(ancilla_probs) if ancilla_probs else 0.0
    return {
        "marked_probability": float(marked_p),
        "expected_marked_probability": float(expected),
        "marked_probability_abs_error": abs(float(marked_p) - float(expected)),
        "max_unmeasured_qubit_p1": float(max_unmeasured_p1),
        "measurement_map_complete": set(c2l) == set(range(parameter_bits)),
        "mapping": meta,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--hls-result", type=Path, default=DEFAULT_HLS)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--max-execution-time", type=int, default=120)
    ap.add_argument("--max-cz", type=int, default=325)
    ap.add_argument("--max-cz-sum-p", type=float, default=0.8)
    ap.add_argument("--max-duration-us", type=float, default=30.0)
    ap.add_argument("--max-duration-over-t1", type=float, default=0.3)
    ap.add_argument("--max-duration-over-t2", type=float, default=0.3)
    ap.add_argument("--run", action="store_true", help="Actually submit the paired QPU job")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    if args.shots < 1:
        raise SystemExit("--shots must be positive")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    src = json.loads(args.hls_result.read_text(encoding="utf-8"))
    if src.get("experiment") != "tct_model_derived_clean_ancilla_hls_v1":
        raise RuntimeError("unexpected HLS result artifact")
    if not src.get("ideal_width11_equivalent"):
        raise RuntimeError("source HLS artifact did not pass width-11 ideal equivalence")

    selected = src.get("global_minimum_exposure")
    if not selected:
        raise RuntimeError("HLS result has no global_minimum_exposure")
    if int(selected.get("logical_width", -1)) != 11:
        raise RuntimeError("global minimum-exposure candidate is not width 11")
    if selected.get("variant") not in {"default_one_clean_11q", "one_clean_kg24_11q"}:
        raise RuntimeError(f"unexpected selected variant {selected.get('variant')!r}")

    patch_nodes = [int(x) for x in selected["patch_nodes"]]
    patch_index = int(selected["patch_index"])
    seed = int(selected["seed_transpiler"])
    method = selected.get("hls_method")
    clean = int(selected.get("requested_clean_ancillas", 1))

    base10, oracle = sweep.build_model_derived_circuit(spec, 1)
    candidate_unmeasured = hls.extend_with_clean_helper(base10)
    if candidate_unmeasured.num_qubits != 11:
        raise AssertionError("clean-helper circuit is not width 11")
    parameter_bits = int(oracle["parameter_bits"])
    marked = {int(x) for x in oracle["derived_marked_states"]}
    candidate = pilot.add_param_measurements(candidate_unmeasured, parameter_bits)
    baseline = pilot.build_uniform_baseline(candidate_unmeasured.num_qubits, parameter_bits)

    ideal_uniform = len(marked) / (1 << parameter_bits)
    logical_sv = Statevector.from_instruction(candidate_unmeasured)
    logical_dist = post.logical_parameter_distribution(logical_sv, parameter_bits)
    ideal_grover = post.marked_probability(logical_dist, marked)
    logical_unmeasured = [
        post.qubit_one_probability(logical_sv, q)
        for q in range(parameter_bits, candidate_unmeasured.num_qubits)
    ]
    logical_max_unmeasured_p1 = max(logical_unmeasured) if logical_unmeasured else 0.0

    service = width.ref.ibm_base.make_service()
    usage_before = width.ref.ibm_base.safe_usage(service)
    backend = width.ref.ibm_base.select_backend(service, 11, args.backend)
    hls_cfg = hls.make_hls(method, clean)

    compiled_baseline, baseline_stats_raw = hls.compile_with_hls(
        baseline, backend, args.optimization_level, seed, list(patch_nodes), hls_cfg
    )
    compiled_candidate, candidate_stats_raw = hls.compile_with_hls(
        candidate, backend, args.optimization_level, seed, list(patch_nodes), hls_cfg
    )
    baseline_stats = {
        "native_cz": int(baseline_stats_raw["native_cz"]),
        "compiled_depth": int(baseline_stats_raw["compiled_depth"]),
        "compiled_size": int(baseline_stats_raw["compiled_size"]),
        "compiled_touched_qubits": int(baseline_stats_raw["compiled_touched_qubits"]),
    }
    candidate_stats = {
        "native_cz": int(candidate_stats_raw["native_cz"]),
        "compiled_depth": int(candidate_stats_raw["compiled_depth"]),
        "compiled_size": int(candidate_stats_raw["compiled_size"]),
        "compiled_touched_qubits": int(candidate_stats_raw["compiled_touched_qubits"]),
    }

    touched_baseline = pilot.physical_touched_qubits(compiled_baseline)
    touched_candidate = pilot.physical_touched_qubits(compiled_candidate)
    patch_set = set(patch_nodes)
    baseline_inside = set(touched_baseline).issubset(patch_set)
    candidate_inside = set(touched_candidate).issubset(patch_set)

    audit = pilot.calibration_audit(compiled_candidate, backend, patch_nodes)
    base_sem = semantic_audit(compiled_baseline, parameter_bits, marked, ideal_uniform)
    cand_sem = semantic_audit(compiled_candidate, parameter_bits, marked, ideal_grover)

    guardrails = {
        "width11_clean_helper": candidate_unmeasured.num_qubits == 11 and clean >= 1,
        "candidate_stays_on_frozen_patch": candidate_inside,
        "baseline_stays_on_frozen_patch": baseline_inside,
        "cz_at_most_limit": candidate_stats["native_cz"] <= args.max_cz,
        "cz_sum_p_at_most_limit": (
            audit["cz_sum_p"] is not None and float(audit["cz_sum_p"]) <= args.max_cz_sum_p
        ),
        "duration_us_at_most_limit": float(audit["duration_us"]) <= args.max_duration_us,
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
        "logical_clean_ancillas_return_zero": logical_max_unmeasured_p1 <= 1e-10,
        "transpiled_baseline_probability_matches_uniform": base_sem["marked_probability_abs_error"] <= 1e-10,
        "transpiled_candidate_probability_matches_expected": cand_sem["marked_probability_abs_error"] <= 1e-9,
        "transpiled_clean_ancillas_return_zero": cand_sem["max_unmeasured_qubit_p1"] <= 1e-9,
        "baseline_measurement_map_complete": bool(base_sem["measurement_map_complete"]),
        "candidate_measurement_map_complete": bool(cand_sem["measurement_map_complete"]),
    }
    all_guardrails_pass = all(bool(v) for v in guardrails.values())

    out = {
        "experiment": "tct_model_derived_clean11_qpu_pilot_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_spec": str(args.spec),
        "source_hls_result": str(args.hls_result),
        "backend": str(backend.name),
        "calibration_last_update": pilot.cal.calibration_timestamp(backend),
        "variant": selected["variant"],
        "hls_method": method,
        "requested_clean_ancillas": clean,
        "patch_index": patch_index,
        "patch_nodes": patch_nodes,
        "seed_transpiler": seed,
        "shots_per_circuit": int(args.shots),
        "parameter_bits": parameter_bits,
        "derived_marked_states": sorted(marked),
        "ideal_uniform_marked_fraction": ideal_uniform,
        "ideal_grover_marked_fraction": ideal_grover,
        "logical_max_unmeasured_qubit_p1": logical_max_unmeasured_p1,
        "baseline_stats": baseline_stats,
        "candidate_stats": candidate_stats,
        "baseline_touched_physical_qubits": touched_baseline,
        "candidate_touched_physical_qubits": touched_candidate,
        "candidate_calibration_audit": audit,
        "baseline_semantic_audit": base_sem,
        "candidate_semantic_audit": cand_sem,
        "guardrail_limits": {
            "max_cz": args.max_cz,
            "max_cz_sum_p": args.max_cz_sum_p,
            "max_duration_us": args.max_duration_us,
            "max_duration_over_t1": args.max_duration_over_t1,
            "max_duration_over_t2": args.max_duration_over_t2,
        },
        "guardrails": guardrails,
        "all_guardrails_pass": all_guardrails_pass,
        "account_usage_before": usage_before,
        "qpu_job_submitted": False,
        "preregistered_interpretation": {
            "strong_amplification_evidence": "candidate marked fraction > baseline and two-proportion z >= 3",
            "same_job_pairing": True,
            "no_posthoc_threshold_change": True,
        },
        "claim_boundary": (
            "Second hardware pilot of the finite-codebook model-derived TCT threshold predicate, "
            "using one additional clean synthesis helper. This tests marked-state amplification only; "
            "it is not fusion validation and cannot establish end-to-end quantum advantage."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    preflight_path = args.outdir / "tct_model_derived_clean11_qpu_pilot_preflight.json"
    preflight_path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print("TCT MODEL-DERIVED CLEAN11 QPU PILOT PREFLIGHT")
    print(
        f"backend={backend.name} calibration_last_update={out['calibration_last_update']} "
        f"variant={selected['variant']} patch={patch_index} seed={seed} shots={args.shots}"
    )
    print(
        f"baseline: CZ={baseline_stats['native_cz']} depth={baseline_stats['compiled_depth']} "
        f"touched={touched_baseline} ideal_marked={base_sem['marked_probability']:.9f}"
    )
    print(
        f"candidate: CZ={candidate_stats['native_cz']} depth={candidate_stats['compiled_depth']} "
        f"sum_p_CZ={audit['cz_sum_p']:.3f} log10_noerr={audit['cz_log10_no_error_proxy']:.3f} "
        f"duration_us={audit['duration_us']:.1f} "
        f"dur/T1={audit['duration_over_median_t1']:.3f} "
        f"dur/T2={audit['duration_over_median_t2']:.3f} "
        f"ideal_marked={cand_sem['marked_probability']:.9f} "
        f"max_unmeasured_p1={cand_sem['max_unmeasured_qubit_p1']:.3e}"
    )
    print("guardrails=" + json.dumps(guardrails, sort_keys=True))
    print(f"all_guardrails_pass={all_guardrails_pass}")
    print(f"saved preflight {preflight_path.resolve()}")

    if not args.run:
        print("NO QPU JOB SUBMITTED. Add --run only after reviewing this preflight.")
        return 0

    if not all_guardrails_pass:
        raise SystemExit("REFUSING QPU SUBMISSION: one or more preregistered guardrails failed")

    print(f"Submitting paired baseline + clean11 candidate: 2 circuits x {args.shots} shots")
    sampler = SamplerV2(mode=backend, options={"max_execution_time": args.max_execution_time})
    job = sampler.run([compiled_baseline, compiled_candidate], shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    baseline_counts = pubs[0].data.params.get_counts()
    candidate_counts = pubs[1].data.params.get_counts()
    b = pilot.parse_counts(baseline_counts, marked, args.shots)
    c = pilot.parse_counts(candidate_counts, marked, args.shots)
    z = pilot.two_proportion_z(b["marked_hits"], args.shots, c["marked_hits"], args.shots)

    out.update({
        "qpu_job_submitted": True,
        "job_id": job.job_id(),
        "job_metrics": width.ref.ibm_base.safe_metrics(job),
        "account_usage_after": width.ref.ibm_base.safe_usage(service),
        "hardware_results": {
            "uniform_baseline": b,
            "one_round_clean11": c,
            "marked_fraction_difference": c["marked_fraction"] - b["marked_fraction"],
            "marked_fraction_ratio": None if b["marked_fraction"] == 0 else c["marked_fraction"] / b["marked_fraction"],
            "two_proportion_z_approx": z,
            "strong_amplification_evidence_preregistered": (
                c["marked_fraction"] > b["marked_fraction"] and z is not None and z >= 3.0
            ),
        },
    })

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = args.outdir / f"tct_model_derived_clean11_qpu_pilot_{stamp}.json"
    result_path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print("RESULT")
    print(
        f"baseline marked={b['marked_hits']}/{args.shots}={b['marked_fraction']:.6f} | "
        f"candidate marked={c['marked_hits']}/{args.shots}={c['marked_fraction']:.6f} | "
        f"difference={c['marked_fraction'] - b['marked_fraction']:.6f} | z~{z}"
    )
    print(f"saved {result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
