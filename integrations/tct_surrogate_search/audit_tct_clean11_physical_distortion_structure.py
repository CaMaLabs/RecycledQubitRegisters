#!/usr/bin/env python3
"""Zero-QPU structural audit of the second clean11 TCT hardware failure.

This connects the observed nine-bit hardware displacement to the exact replayed
252-CZ route and the Fez physical output qubits.  It also tests two deliberately
simple explanations:

1. convex global depolarization between ideal Grover and uniform;
2. a symmetric two-subspace model that is uniform within marked and unmarked
   states but uses the observed total marked probability.

Neither simple model is treated as a hardware noise model.  They are falsification
references only.  Current backend calibration is used only as descriptive
engineering metadata and is flagged if its timestamp differs from the hardware
run's recorded calibration snapshot.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_clean11_qpu_distribution_forensics as forensic
import audit_tct_model_derived_qpu_pilot_postmortem as post
import benchmark_tct_model_derived_clean_ancilla_hls as hls
import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import run_tct_model_derived_clean11_qpu_pilot_v2 as pilotv2
import run_tct_model_derived_one_round_qpu_pilot as pilot

REV = "2026-09-22-tct-clean11-physical-distortion-structure-v1"
DEFAULT_HLS = ROOT / "results" / "tct_surrogate_search" / "tct_model_derived_clean_ancilla_hls.json"
DEFAULT_RESULT_DIR = ROOT / "results" / "tct_surrogate_search" / "qpu_pilot_clean11_v2"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_clean11_physical_distortion_structure.json"


def latest_result(directory: Path) -> Path:
    xs = sorted(
        p for p in directory.glob("tct_model_derived_clean11_qpu_pilot_v2_*.json")
        if "preflight" not in p.name
    )
    if not xs:
        raise RuntimeError(f"no clean11 v2 result in {directory}")
    return xs[-1]


def bit_marginals_from_counts(row: dict, nbits: int) -> list[float]:
    shots = int(row["shots"])
    ones = [0] * nbits
    for k, count in row.get("state_counts_decimal", {}).items():
        s = int(k); c = int(count)
        for b in range(nbits):
            if (s >> b) & 1:
                ones[b] += c
    return [x / shots for x in ones]


def bit_marginals_from_distribution(dist: list[float], nbits: int) -> list[float]:
    return [sum(p for s, p in enumerate(dist) if (s >> b) & 1) for b in range(nbits)]


def symmetric_two_subspace_distribution(nstates: int, marked: set[int], marked_mass: float) -> list[float]:
    nm = len(marked)
    nu = nstates - nm
    pm = 0.0 if nm == 0 else marked_mass / nm
    pu = 0.0 if nu == 0 else (1.0 - marked_mass) / nu
    return [pm if s in marked else pu for s in range(nstates)]


def cosine(a: list[float], b: list[float]) -> float | None:
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    if na == 0.0 or nb == 0.0:
        return None
    return sum(x*y for x, y in zip(a, b)) / (na * nb)


def pearson(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    ma = sum(a)/len(a); mb = sum(b)/len(b)
    da = [x-ma for x in a]; db = [x-mb for x in b]
    den = math.sqrt(sum(x*x for x in da) * sum(y*y for y in db))
    if den == 0.0:
        return None
    return sum(x*y for x,y in zip(da,db))/den


def measure_error(backend, q: int) -> float | None:
    try:
        prop, _used, _found = pilot.cal.target_instruction_properties(backend, "measure", (int(q),))
        if prop is None:
            return None
        x = getattr(prop, "error", None)
        return None if x is None else float(x)
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--hls-result", type=Path, default=DEFAULT_HLS)
    ap.add_argument("--result", type=Path, default=None)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--optimization-level", type=int, choices=[0,1,2,3], default=3)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    result_path = args.result or latest_result(DEFAULT_RESULT_DIR)
    hw = json.loads(result_path.read_text(encoding="utf-8"))
    src = json.loads(args.hls_result.read_text(encoding="utf-8"))
    spec = json.loads(args.spec.read_text(encoding="utf-8"))

    if hw.get("experiment") != "tct_model_derived_clean11_qpu_pilot_v2_route_replay":
        raise RuntimeError(f"unexpected hardware result experiment {hw.get('experiment')!r}")
    if not hw.get("qpu_job_submitted"):
        raise RuntimeError("selected hardware result was not submitted")
    if src.get("experiment") != "tct_model_derived_clean_ancilla_hls_v1":
        raise RuntimeError("unexpected HLS artifact")

    nbits = int(hw["parameter_bits"]); nstates = 1 << nbits
    marked = {int(x) for x in hw["derived_marked_states"]}
    hwr = hw["hardware_results"]
    b = hwr["uniform_matched_output_baseline"]
    c = hwr["one_round_clean11_route_replay"]
    bm = bit_marginals_from_counts(b, nbits)
    cm = bit_marginals_from_counts(c, nbits)
    observed_delta = [cm[i]-bm[i] for i in range(nbits)]

    # Rebuild the logical ideal candidate for its expected amplification direction.
    base10, oracle = sweep.build_model_derived_circuit(spec, 1)
    plus11 = hls.extend_with_clean_helper(base10)
    sv = Statevector.from_instruction(plus11)
    ideal_dist = post.logical_parameter_distribution(sv, nbits)
    ideal_marg = bit_marginals_from_distribution(ideal_dist, nbits)
    ideal_delta = [x - 0.5 for x in ideal_marg]

    common = forensic.common_constraints(marked, nbits)
    common_bits = sorted(common)
    common_ideal = [ideal_delta[q] for q in common_bits]
    common_observed = [observed_delta[q] for q in common_bits]
    away_count = sum(1 for x,y in zip(common_ideal, common_observed) if x*y < 0)

    ideal_marked = float(hw["ideal_grover_marked_fraction"])
    uniform_marked = float(hw["ideal_uniform_marked_fraction"])
    observed_marked = float(c["marked_fraction"])
    depol_lambda = (observed_marked - uniform_marked) / (ideal_marked - uniform_marked)
    depol_convex_possible = 0.0 <= depol_lambda <= 1.0

    two_dist = symmetric_two_subspace_distribution(nstates, marked, observed_marked)
    two_marg = bit_marginals_from_distribution(two_dist, nbits)
    two_rmse = math.sqrt(sum((cm[i]-two_marg[i])**2 for i in range(nbits))/nbits)

    # Reproduce the exact route and attach current calibration metadata.
    selected = src["global_minimum_exposure"]
    patch_nodes = [int(x) for x in selected["patch_nodes"]]
    seed = int(selected["seed_transpiler"])
    method = selected.get("hls_method")
    clean = int(selected.get("requested_clean_ancillas", 1))

    service = width.ref.ibm_base.make_service()
    backend = width.ref.ibm_base.select_backend(service, 11, args.backend)
    current_cal = pilot.cal.calibration_timestamp(backend)
    run_cal = hw.get("calibration_last_update")
    calibration_snapshot_match = str(current_cal) == str(run_cal)

    fez_full = topo.symmetric(topo.backend_coupling(backend), int(backend.num_qubits))
    subcm = cap.relabeled_subgraph(fez_full, patch_nodes)
    patch_backend = topo.generic(11, subcm)
    local_compiled, local_stats_raw = hls.compile_with_hls(
        plus11, patch_backend, args.optimization_level, seed, None, hls.make_hls(method, clean)
    )
    local_stats = {
        "native_cz": int(local_stats_raw["native_cz"]),
        "compiled_depth": int(local_stats_raw["compiled_depth"]),
        "compiled_size": int(local_stats_raw["compiled_size"]),
    }
    final_local = pilotv2.final_local_parameter_qubits(local_compiled, nbits)
    lifted, lift_meta = pilotv2.lift_local_native_to_fez(
        local_compiled, backend, patch_nodes, final_local, nbits
    )

    op_rows = pilot.physical_op_rows(lifted, backend)
    incident_count = defaultdict(int); incident_sum_p = defaultdict(float)
    for r in op_rows:
        if r["name"] != "cz":
            continue
        err = 0.0 if r.get("error") is None else float(r["error"])
        for q in r["physical_qubits"]:
            incident_count[int(q)] += 1
            incident_sum_p[int(q)] += err

    qprops = getattr(backend.target, "qubit_properties", None)
    output_physical = [int(x) for x in lift_meta["output_parameter_physical_qubits"]]
    per_bit = []
    bshots = int(b["shots"]); cshots = int(c["shots"])
    for q in range(nbits):
        pq = output_physical[q]
        bp1 = bm[q]; cp1 = cm[q]
        bh = round(bp1*bshots); ch = round(cp1*cshots)
        z = pilot.two_proportion_z(int(bh), bshots, int(ch), cshots)
        qp = None if qprops is None else qprops[pq]
        target = common.get(q)
        ideal_dir = 0 if abs(ideal_delta[q]) < 1e-15 else (1 if ideal_delta[q] > 0 else -1)
        obs_dir = 0 if abs(observed_delta[q]) < 1e-15 else (1 if observed_delta[q] > 0 else -1)
        per_bit.append({
            "logical_bit": q,
            "physical_qubit": pq,
            "common_constraint": target,
            "baseline_p1": bp1,
            "candidate_p1": cp1,
            "observed_candidate_minus_baseline": observed_delta[q],
            "ideal_candidate_minus_uniform": ideal_delta[q],
            "two_subspace_predicted_candidate_p1": two_marg[q],
            "candidate_minus_two_subspace": cp1-two_marg[q],
            "two_proportion_z_approx": z,
            "direction_matches_ideal": ideal_dir != 0 and ideal_dir == obs_dir,
            "direction_opposes_ideal": ideal_dir != 0 and ideal_dir == -obs_dir,
            "incident_cz_count": int(incident_count[pq]),
            "incident_cz_sum_p": float(incident_sum_p[pq]),
            "readout_error_current": measure_error(backend, pq),
            "t1_s_current": None if qp is None else getattr(qp, "t1", None),
            "t2_s_current": None if qp is None else getattr(qp, "t2", None),
        })

    abs_delta = [abs(r["observed_candidate_minus_baseline"]) for r in per_bit]
    exposure = [r["incident_cz_sum_p"] for r in per_bit]
    czcounts = [float(r["incident_cz_count"]) for r in per_bit]
    readerrs = [r["readout_error_current"] for r in per_bit]
    corr_readout = None
    if all(x is not None for x in readerrs):
        corr_readout = pearson(abs_delta, [float(x) for x in readerrs])

    ranked = sorted(per_bit, key=lambda r: (-abs(r["observed_candidate_minus_baseline"]), r["logical_bit"]))

    out = {
        "experiment": "tct_clean11_physical_distortion_structure_v1",
        "script_revision": REV,
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_hardware_result": str(result_path),
        "hardware_job_id": hw.get("job_id"),
        "source_hls_result": str(args.hls_result),
        "run_calibration_last_update": run_cal,
        "current_calibration_last_update": current_cal,
        "calibration_snapshot_match": calibration_snapshot_match,
        "route_reproduction": {
            "selected_native_cz": int(selected["native_cz"]),
            "selected_depth": int(selected["compiled_depth"]),
            "selected_size": int(selected["compiled_size"]),
            "replayed": local_stats,
            "exact_stats": (
                int(selected["native_cz"]) == local_stats["native_cz"]
                and int(selected["compiled_depth"]) == local_stats["compiled_depth"]
                and int(selected["compiled_size"]) == local_stats["compiled_size"]
            ),
            "output_parameter_physical_qubits": output_physical,
        },
        "simple_model_falsification": {
            "uniform_marked_fraction": uniform_marked,
            "ideal_grover_marked_fraction": ideal_marked,
            "observed_candidate_marked_fraction": observed_marked,
            "global_depolarizing_mixture_lambda": depol_lambda,
            "global_depolarizing_convex_mixture_possible": depol_convex_possible,
            "two_subspace_model_bit_marginal_rmse": two_rmse,
        },
        "directionality": {
            "common_constraints": {str(k): int(v) for k,v in sorted(common.items())},
            "common_bits": common_bits,
            "common_ideal_delta": common_ideal,
            "common_observed_delta": common_observed,
            "common_bits_opposing_ideal_direction": away_count,
            "common_bit_count": len(common_bits),
            "cosine_observed_vs_ideal_all_bits": cosine(observed_delta, ideal_delta),
            "cosine_observed_vs_ideal_common_bits": cosine(common_observed, common_ideal),
        },
        "per_output_bit": per_bit,
        "ranked_by_abs_observed_shift": ranked,
        "descriptive_correlations_current_calibration": {
            "abs_shift_vs_incident_cz_sum_p": pearson(abs_delta, exposure),
            "abs_shift_vs_incident_cz_count": pearson(abs_delta, czcounts),
            "abs_shift_vs_readout_error": corr_readout,
            "warning": (
                "Current calibration correlations are only directly comparable to the run when calibration_snapshot_match is true. "
                "Nine output bits are too few for causal inference."
            ),
        },
        "interpretation_boundary": (
            "The audit can reject simple uniformizing descriptions and localize descriptive bit/physical-qubit structure. "
            "It cannot identify a unique coherent-error, crosstalk, relaxation, or control mechanism from one hardware job."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print("ZERO-QPU TCT CLEAN11 PHYSICAL DISTORTION STRUCTURE")
    print(f"job_id={hw.get('job_id')} result={result_path}")
    print(f"calibration_run={run_cal} current={current_cal} snapshot_match={calibration_snapshot_match}")
    print(
        f"route_exact={out['route_reproduction']['exact_stats']} CZ={local_stats['native_cz']} "
        f"depth={local_stats['compiled_depth']} size={local_stats['compiled_size']}"
    )
    print(
        f"global_depolarizing_lambda={depol_lambda:.6f} convex_possible={depol_convex_possible} "
        f"two_subspace_bit_rmse={two_rmse:.6f}"
    )
    print(
        f"common_bits_opposing_ideal={away_count}/{len(common_bits)} "
        f"cosine_all={out['directionality']['cosine_observed_vs_ideal_all_bits']} "
        f"cosine_common={out['directionality']['cosine_observed_vs_ideal_common_bits']}"
    )
    print("ranked_output_bits:")
    for r in ranked:
        print(
            f"  q{r['logical_bit']}->phys{r['physical_qubit']} common={r['common_constraint']} "
            f"ideal_delta={r['ideal_candidate_minus_uniform']:+.6f} "
            f"obs_delta={r['observed_candidate_minus_baseline']:+.6f} z={r['two_proportion_z_approx']} "
            f"CZ_incident={r['incident_cz_count']} sum_p_incident={r['incident_cz_sum_p']:.4f} "
            f"readout={r['readout_error_current']}"
        )
    print("correlations=" + json.dumps(out["descriptive_correlations_current_calibration"], default=str, sort_keys=True))
    print(f"wrote {args.out.resolve()}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
