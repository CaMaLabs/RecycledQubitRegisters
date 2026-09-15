#!/usr/bin/env python3
"""Zero-QPU counterfactual ablation of the N=209 staged native-cost result.

Input is the JSON receipt produced by
`ibm_shor209_public_cube_staged_cost_preflight.py`.

The native-cost result mixes two effects:

1. stopping effect: public cube preconditioning changes the ideal staged-QPE
   stopping pattern (fewer precision stages / shots on many sessions);
2. circuit-cost effect: at the same phase precision, the base-27 modular-unitary
   circuit can have a different compiled native cost than the base-3 circuit.

This script replays the exact deterministic staged simulations and evaluates four
counterfactual worlds on the paired sessions where both policies succeed:

    BB = baseline stopping pattern     + baseline circuit-cost table
    BT = baseline stopping pattern     + transformed circuit-cost table
    TB = transformed stopping pattern  + baseline circuit-cost table
    TT = transformed stopping pattern  + transformed circuit-cost table

Thus TB/BB isolates the stopping-pattern contribution while BT/BB isolates the
per-stage compiled-circuit contribution on the baseline execution schedule. TT/BB
is the combined result already reported by the native-cost preflight.

No IBM service is contacted and no QPU job is submitted. The hidden orders stored
in the receipt are validation labels used only to reproduce the same ideal QPE
sampling experiment; they are not used to choose the public exponent or stopping
rule.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median

import dark_star_shor_staged_stopping_time_audit as staged

DEFAULT_INPUT = Path(
    "results/dark_star_ptp/ibm_shor209_public_cube_staged_cost_preflight.json"
)
DEFAULT_OUTPUT = Path(
    "results/dark_star_ptp/dark_star_shor_n209_native_cost_ablation.json"
)


def native_cost(session: dict, stage_bits: list[int], table: dict, shots_per_stage: int) -> dict:
    by_bits = {int(k): v for k, v in table.items()}
    total_cz = 0
    total_depth = 0
    total_shots = 0

    if session["success"]:
        stop_idx = int(session["stage_index"])
        stop_shots = int(session["shot_in_stop_stage"])
        used = stage_bits[: stop_idx + 1]
        for idx, m in enumerate(used):
            shots = stop_shots if idx == stop_idx else shots_per_stage
            best = by_bits[m]["best"]
            total_shots += shots
            total_cz += shots * int(best["cz"])
            total_depth += shots * int(best["compiled_depth"])
    else:
        for m in stage_bits:
            best = by_bits[m]["best"]
            total_shots += shots_per_stage
            total_cz += shots_per_stage * int(best["cz"])
            total_depth += shots_per_stage * int(best["compiled_depth"])

    return {
        "cz": total_cz,
        "depth": total_depth,
        "shots": total_shots,
    }


def replay(policy: str, n: int, a: int, order: int, stage_bits: list[int], shots_per_stage: int, replicates: int) -> list[dict]:
    step = stage_bits[1] - stage_bits[0]
    out = []
    for rep in range(replicates):
        rng = staged.deterministic_rng("n209", policy, rep)
        out.append(
            staged.simulate_session(
                n,
                a,
                order,
                start_bits=stage_bits[0],
                step_bits=step,
                shots_per_stage=shots_per_stage,
                rng=rng,
            )
        )
    return out


def avg_ratio(rows: list[tuple[dict, dict]], num_key: str, den_key: str) -> float | None:
    vals = [r[0][num_key] / r[1][den_key] for r in rows if r[1][den_key]]
    return mean(vals) if vals else None


def main() -> int:
    ap = argparse.ArgumentParser(description="N209 staged native-cost counterfactual ablation")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    if data.get("N") != 209:
        raise SystemExit("input is not the expected N=209 staged native-cost receipt")
    if not data.get("zero_qpu", False):
        raise SystemExit("input receipt is not marked zero_qpu")

    n = int(data["N"])
    a0 = int(data["seed_base"])
    a1 = int(data["transformed_base"])
    r0 = int(data["baseline_order_validation_only"])
    r1 = int(data["transformed_order_validation_only"])
    stage_bits = [int(x) for x in data["stage_bits"]]
    shots_per_stage = int(data["shots_per_stage"])
    replicates = int(data["replicates"])
    tables = data["compile_tables"]
    t0 = tables["baseline"]
    t1 = tables["ptp3_conditional"]

    baseline = replay("baseline", n, a0, r0, stage_bits, shots_per_stage, replicates)
    transformed = replay(
        "ptp3_conditional", n, a1, r1, stage_bits, shots_per_stage, replicates
    )

    stage_cost_ratios = {}
    for m in stage_bits:
        b = t0[str(m)]["best"]
        t = t1[str(m)]["best"]
        stage_cost_ratios[str(m)] = {
            "baseline_cz": int(b["cz"]),
            "transformed_cz": int(t["cz"]),
            "transformed_over_baseline_cz": float(t["cz"]) / float(b["cz"]) if b["cz"] else None,
            "baseline_depth": int(b["compiled_depth"]),
            "transformed_depth": int(t["compiled_depth"]),
            "transformed_over_baseline_depth": float(t["compiled_depth"]) / float(b["compiled_depth"]) if b["compiled_depth"] else None,
        }

    worlds = []
    for sb, st in zip(baseline, transformed):
        if not (sb["success"] and st["success"]):
            continue
        bb = native_cost(sb, stage_bits, t0, shots_per_stage)
        bt = native_cost(sb, stage_bits, t1, shots_per_stage)
        tb = native_cost(st, stage_bits, t0, shots_per_stage)
        tt = native_cost(st, stage_bits, t1, shots_per_stage)
        worlds.append({
            "baseline_session": sb,
            "transformed_session": st,
            "BB": bb,
            "BT": bt,
            "TB": tb,
            "TT": tt,
        })

    if not worlds:
        raise SystemExit("no paired successful sessions")

    def ratios(num_world: str, den_world: str, key: str) -> list[float]:
        return [
            float(w[num_world][key]) / float(w[den_world][key])
            for w in worlds
            if w[den_world][key]
        ]

    precision_saved = [
        int(w["baseline_session"]["stop_precision_bits"])
        - int(w["transformed_session"]["stop_precision_bits"])
        for w in worlds
    ]

    stop_cz = ratios("TB", "BB", "cz")
    circuit_cz = ratios("BT", "BB", "cz")
    combined_cz = ratios("TT", "BB", "cz")
    stop_depth = ratios("TB", "BB", "depth")
    circuit_depth = ratios("BT", "BB", "depth")
    combined_depth = ratios("TT", "BB", "depth")

    # Same transformed stopping schedule, swapping only the cost table, gives a
    # second view of the circuit-cost contribution under the transformed schedule.
    circuit_on_transformed_cz = ratios("TT", "TB", "cz")
    circuit_on_transformed_depth = ratios("TT", "TB", "depth")

    summary = {
        "paired_success_sessions": len(worlds),
        "mean_stop_precision_bits_saved": mean(precision_saved),
        "median_stop_precision_bits_saved": median(precision_saved),
        "fraction_transformed_stops_lower": sum(x > 0 for x in precision_saved) / len(precision_saved),
        "stopping_only": {
            "mean_cz_ratio_TB_over_BB": mean(stop_cz),
            "mean_cz_reduction_fraction": 1.0 - mean(stop_cz),
            "mean_depth_ratio_TB_over_BB": mean(stop_depth),
            "mean_depth_reduction_fraction": 1.0 - mean(stop_depth),
        },
        "circuit_only_on_baseline_schedule": {
            "mean_cz_ratio_BT_over_BB": mean(circuit_cz),
            "mean_cz_reduction_fraction": 1.0 - mean(circuit_cz),
            "mean_depth_ratio_BT_over_BB": mean(circuit_depth),
            "mean_depth_reduction_fraction": 1.0 - mean(circuit_depth),
        },
        "circuit_only_on_transformed_schedule": {
            "mean_cz_ratio_TT_over_TB": mean(circuit_on_transformed_cz),
            "mean_cz_reduction_fraction": 1.0 - mean(circuit_on_transformed_cz),
            "mean_depth_ratio_TT_over_TB": mean(circuit_on_transformed_depth),
            "mean_depth_reduction_fraction": 1.0 - mean(circuit_on_transformed_depth),
        },
        "combined": {
            "mean_cz_ratio_TT_over_BB": mean(combined_cz),
            "mean_cz_reduction_fraction": 1.0 - mean(combined_cz),
            "mean_depth_ratio_TT_over_BB": mean(combined_depth),
            "mean_depth_reduction_fraction": 1.0 - mean(combined_depth),
        },
        "interpretation_boundary": (
            "This is a counterfactual decomposition of an ideal staged-stopping simulation weighted by compiled native costs. It is not a hardware runtime, fidelity, or asymptotic-complexity measurement."
        ),
    }

    result = {
        "experiment": "dark_star_shor_n209_native_cost_counterfactual_ablation_v1",
        "zero_qpu": True,
        "source_receipt": str(args.input),
        "N": n,
        "seed_base": a0,
        "transformed_base": a1,
        "public_exponent": int(data["public_exponent"]),
        "stage_bits": stage_bits,
        "shots_per_stage": shots_per_stage,
        "replicates": replicates,
        "stage_cost_ratios": stage_cost_ratios,
        "summary": summary,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== N209 STAGE COST RATIOS =====")
    print(json.dumps(stage_cost_ratios, indent=2))
    print("\n===== N209 COUNTERFACTUAL NATIVE-COST ABLATION =====")
    print(json.dumps(summary, indent=2))
    print("\n===== OVERALL =====")
    print(json.dumps({
        "pass": True,
        "zero_qpu": True,
        "saved": str(args.out.resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
