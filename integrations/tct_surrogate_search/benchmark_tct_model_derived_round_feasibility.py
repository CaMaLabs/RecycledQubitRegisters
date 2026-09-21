#!/usr/bin/env python3
"""Zero-QPU Grover-round feasibility sweep for the model-derived TCT predicate.

This follows the six-round Fez calibration sweep of the 10-qubit finite-codebook
TCT threshold predicate.  It reuses the strongest physical patches from that
frozen patch ensemble and recompiles Grover rounds 1..6 under the *current*
ibm_fez calibration across multiple transpiler seeds.

For each round count it reports separately:

* ideal Grover marked-state probability;
* routed CZ/depth;
* calibration-weighted CZ exposure;
* calibrated critical-path duration and T1/T2 ratios; and
* a deliberately labeled ranking heuristic equal to

      ideal_Grover_success * independent_no_CZ_error_proxy.

That product is NOT a noisy-hardware success probability.  It ignores coherent
and correlated errors, leakage, crosstalk, relaxation structure, measurement,
DD, pulse optimization, mitigation, and calibration drift.  It is included only
to identify whether a shallower round count is a more plausible hardware test.

The oracle is reconstructed from the reduced-order loss formula, fixed-point
threshold, and finite parameter codebooks.  The frozen marked-state list is not
used to construct it.  No Sampler is instantiated and no QPU job is submitted.
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

import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-20-tct-model-derived-round-feasibility-v1"
DEFAULT_SOURCE = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_fez_calibration_sweep.json"
)
DEFAULT_OUT = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_round_feasibility.json"
)


def parse_int_list(text: str) -> list[int]:
    out = [int(x.strip()) for x in text.split(",") if x.strip()]
    if not out:
        raise ValueError("empty integer list")
    return out


def selected_patch_rows(source: dict, top_exposure: int, all_patches: bool) -> list[dict]:
    rows = [r for r in source.get("rows", []) if r.get("patch_nodes")]
    if not rows:
        raise RuntimeError("source sweep has no patch rows with patch_nodes")
    if all_patches:
        return sorted(rows, key=lambda r: int(r["patch_index"]))

    by_exp = sorted(
        rows,
        key=lambda r: (
            math.inf if r.get("cz_sum_p") is None else float(r["cz_sum_p"]),
            int(r["native_cz"]),
            int(r["compiled_depth"]),
        ),
    )
    chosen = by_exp[: max(1, int(top_exposure))]
    chosen += [
        min(rows, key=lambda r: (int(r["native_cz"]), int(r["compiled_depth"]))),
        min(rows, key=lambda r: float(r["critical_path_s"])),
    ]
    dedup = {}
    for row in chosen:
        dedup[int(row["patch_index"])] = row
    return [dedup[i] for i in sorted(dedup)]


def ideal_grover_success(parameter_bits: int, marked_count: int, rounds: int) -> float:
    nstates = 1 << int(parameter_bits)
    if not (0 < marked_count < nstates):
        raise ValueError("invalid Grover search cardinality")
    theta = math.asin(math.sqrt(marked_count / nstates))
    return math.sin((2 * int(rounds) + 1) * theta) ** 2


def independent_proxy(log10_noerr: float | None) -> float | None:
    if log10_noerr is None:
        return None
    x = float(log10_noerr)
    if x < -300:
        return 0.0
    return 10.0 ** x


def candidate_key(row: dict):
    return (
        math.inf if row.get("cz_sum_p") is None else float(row["cz_sum_p"]),
        int(row["native_cz"]),
        int(row["compiled_depth"]),
        int(row["seed_transpiler"]),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--source-sweep", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--rounds", default="1,2,3,4,5,6")
    ap.add_argument("--top-exposure-patches", type=int, default=6)
    ap.add_argument("--all-source-patches", action="store_true")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--transpiler-seeds", default="8776,2026,9401,42,1337")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rounds_list = sorted(set(parse_int_list(args.rounds)))
    if rounds_list[0] < 1:
        raise SystemExit("round counts must be >= 1")
    seeds = parse_int_list(args.transpiler_seeds)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    source = json.loads(args.source_sweep.read_text(encoding="utf-8"))
    if source.get("experiment") != "tct_model_derived_fez_calibration_sweep_v1":
        raise RuntimeError("source sweep is not the expected model-derived Fez sweep")

    source_rows = selected_patch_rows(source, args.top_exposure_patches, args.all_source_patches)
    patch_indices = [int(r["patch_index"]) for r in source_rows]

    # Build once only to obtain the logical width and authenticated backend.
    qc0, oracle0 = sweep.build_model_derived_circuit(spec, rounds_list[0])
    logical = int(qc0.num_qubits)
    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, logical, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))

    result = {
        "experiment": "tct_model_derived_round_feasibility_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "source_six_round_sweep": str(args.source_sweep),
        "backend": str(fez.name),
        "calibration_last_update": sweep.cal.calibration_timestamp(fez),
        "logical_width": logical,
        "parameter_bits": int(oracle0["parameter_bits"]),
        "marked_count": int(oracle0["derived_marked_count"]),
        "rounds": rounds_list,
        "transpiler_seeds": seeds,
        "selected_patch_indices": patch_indices,
        "selection_mode": "all_source_patches" if args.all_source_patches else "top_exposure_union_min_cz_min_duration",
        "rows": [],
        "round_summaries": [],
        "claim_boundary": (
            "Zero-QPU engineering screen for choosing Grover round count. Ideal Grover "
            "success is analytical; calibration products are independent-gate proxies. "
            "Their product is a ranking heuristic only and is not predicted hardware "
            "success probability. Finite-codebook reduced-order TCT predicate only."
        ),
    }

    print("ZERO-QPU TCT MODEL-DERIVED GROVER-ROUND FEASIBILITY")
    print(
        f"backend={fez.name} calibration_last_update={result['calibration_last_update']} "
        f"logical_width={logical} patches={patch_indices} seeds={seeds} rounds={rounds_list}"
    )
    print(
        f"search_states={1 << result['parameter_bits']} marked={result['marked_count']} "
        f"uniform_baseline_success={result['marked_count']/(1 << result['parameter_bits']):.8f}"
    )

    for rounds in rounds_list:
        qc, oracle = sweep.build_model_derived_circuit(spec, rounds)
        if int(qc.num_qubits) != logical:
            raise AssertionError("logical width changed across round count")
        ideal = ideal_grover_success(
            int(oracle["parameter_bits"]), int(oracle["derived_marked_count"]), rounds
        )
        round_rows = []

        for source_row in source_rows:
            patch_index = int(source_row["patch_index"])
            nodes = [int(x) for x in source_row["patch_nodes"]]
            if len(nodes) != logical:
                raise RuntimeError(f"patch {patch_index} width mismatch")
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
                row = sweep.summarize_candidate(compiled, stats, fez, nodes, seed)
                row.update({
                    "rounds": int(rounds),
                    "patch_index": patch_index,
                    "patch_nodes": nodes,
                    "ideal_grover_success": float(ideal),
                })
                proxy = independent_proxy(row.get("cz_log10_no_error_proxy"))
                row["independent_no_cz_error_proxy"] = proxy
                if row.get("cz_log10_no_error_proxy") is None or ideal <= 0.0:
                    row["log10_ideal_times_no_cz_error_proxy"] = None
                    row["ideal_times_no_cz_error_proxy"] = None
                else:
                    logh = math.log10(ideal) + float(row["cz_log10_no_error_proxy"])
                    row["log10_ideal_times_no_cz_error_proxy"] = logh
                    row["ideal_times_no_cz_error_proxy"] = 0.0 if logh < -300 else 10.0 ** logh
                candidates.append(row)

            best_patch = min(candidates, key=candidate_key)
            round_rows.append(best_patch)
            result["rows"].append(best_patch)

        best_exp = min(round_rows, key=candidate_key)
        best_duration = min(round_rows, key=lambda r: float(r["critical_path_s"]))
        best_cz = min(round_rows, key=lambda r: (int(r["native_cz"]), int(r["compiled_depth"])))
        best_heur = max(
            round_rows,
            key=lambda r: -math.inf if r.get("log10_ideal_times_no_cz_error_proxy") is None
            else float(r["log10_ideal_times_no_cz_error_proxy"]),
        )
        summary = {
            "rounds": int(rounds),
            "ideal_grover_success": float(ideal),
            "minimum_exposure": best_exp,
            "minimum_duration": best_duration,
            "minimum_cz": best_cz,
            "maximum_ranking_heuristic": best_heur,
        }
        result["round_summaries"].append(summary)

        print(
            f"rounds={rounds} ideal_success={ideal:.6f} "
            f"best_patch={best_exp['patch_index']} seed={best_exp['seed_transpiler']} "
            f"CZ={best_exp['native_cz']} depth={best_exp['compiled_depth']} "
            f"sum_p={best_exp['cz_sum_p']:.3f} "
            f"log10_noerr={best_exp['cz_log10_no_error_proxy']:.3f} "
            f"duration_us={1e6*best_exp['critical_path_s']:.1f} "
            f"dur/T1={best_exp['duration_over_median_t1']:.3f} "
            f"dur/T2={best_exp['duration_over_median_t2']:.3f} "
            f"log10_rank_heur={best_exp['log10_ideal_times_no_cz_error_proxy']:.3f}"
        )

        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    # Best round by the ranking heuristic. Again, this is NOT predicted hardware success.
    global_heur = max(
        result["round_summaries"],
        key=lambda s: float(s["maximum_ranking_heuristic"]["log10_ideal_times_no_cz_error_proxy"]),
    )
    result["ranking_heuristic_best_round"] = global_heur
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    h = global_heur["maximum_ranking_heuristic"]
    print("\n===== ROUND-COUNT FEASIBILITY SUMMARY =====")
    print(
        f"ranking_heuristic_best_round={global_heur['rounds']} "
        f"patch={h['patch_index']} seed={h['seed_transpiler']} "
        f"ideal_success={h['ideal_grover_success']:.6f} CZ={h['native_cz']} "
        f"sum_p={h['cz_sum_p']:.3f} log10_noerr={h['cz_log10_no_error_proxy']:.3f} "
        f"duration_us={1e6*h['critical_path_s']:.1f} "
        f"log10_rank_heur={h['log10_ideal_times_no_cz_error_proxy']:.3f}"
    )
    print("IMPORTANT: ranking heuristic is not a predicted noisy-hardware success probability.")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
