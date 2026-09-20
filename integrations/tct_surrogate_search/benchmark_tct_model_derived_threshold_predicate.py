#!/usr/bin/env python3
"""Derive and compile the frozen TCT low-loss predicate from the model itself.

This zero-QPU experiment is deliberately distinct from the earlier semantic
truth-table compression audit.  It does NOT use ``spec['marked_indices']`` to
construct the oracle.  Instead it:

1. reads the reduced-order loss formula constants, fixed-point threshold, and
   parameter codebooks from the reversible-oracle specification;
2. evaluates the formula over the valid finite codebooks using the same
   fixed-point rounding rule as the source specification;
3. derives necessary code constraints from threshold feasibility;
4. derives the remaining local predicate from those model-based constraints;
5. synthesizes a minimum ESOP of that *model-derived* local predicate;
6. verifies the resulting 9-bit phase predicate over all 512 basis states; and
7. only then compares the derived classification with the frozen marked list as
   an independent regression check.

This removes the 16-bit score accumulator/comparator for this frozen finite
codebook.  It is a model-specialized threshold predicate, not a general
reversible numerical evaluator and not a scalable quantum-advantage claim.

No IBM service, Sampler, or QPU job is used.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import audit_tct_boolean_oracle_compression as audit
import benchmark_tct_reversible_arithmetic_oracle as arithmetic
import benchmark_tct_semantic_factored_oracle as semantic

REV = "2026-09-20-tct-model-derived-threshold-predicate-v1"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_model_derived_threshold_predicate.json"

FIELDS = (
    ("standing_bias", "bias_code"),
    ("boost_reduction", "boost_code"),
    ("false_trigger_cost_multiplier", "false_code"),
    ("event_rate_multiplier", "event_code"),
)


def codebook_lookup(spec: dict) -> dict[str, dict[int, float]]:
    return {
        name: {int(r["code"]): float(r["value"]) for r in spec["parameter_codebooks"][name]}
        for name, _ in FIELDS
    }


def field_bit_ranges(spec: dict) -> dict[str, list[int]]:
    widths = spec["parameter_register_bits"]
    cursor = 0
    out = {}
    for name, _ in FIELDS:
        width = int(widths[name])
        out[name] = list(range(cursor, cursor + width))
        cursor += width
    if cursor != int(widths["total_parameter_bits"]):
        raise AssertionError("parameter-register width mismatch")
    return out


def compose_codes(codes: dict[str, int], bit_ranges: dict[str, list[int]]) -> int:
    state = 0
    for name, _ in FIELDS:
        bits = bit_ranges[name]
        code = int(codes[name])
        if code >= (1 << len(bits)):
            raise ValueError(f"code {code} does not fit {name} width")
        state |= code << bits[0]
    return state


def formula_loss(spec: dict, values: dict[str, float]) -> float:
    c = spec["formula_constants"]
    return (
        float(c["A_event_base"])
        * values["event_rate_multiplier"]
        * (1.0 - values["standing_bias"])
        * (1.0 - float(c["reachable_fraction"]) * values["boost_reduction"])
        + float(c["B_bias_cost_per_unit_bias"]) * values["standing_bias"]
        + float(c["C_false_cost_per_unit_multiplier"])
        * values["false_trigger_cost_multiplier"]
    )


def enumerate_model_rows(spec: dict) -> list[dict]:
    books = codebook_lookup(spec)
    scale = int(spec["fixed_point"]["scale"])
    rows = []
    index = 0
    for bc, bias in books["standing_bias"].items():
        for gc, boost in books["boost_reduction"].items():
            for fc, false_mult in books["false_trigger_cost_multiplier"].items():
                for ec, event_mult in books["event_rate_multiplier"].items():
                    values = {
                        "standing_bias": bias,
                        "boost_reduction": boost,
                        "false_trigger_cost_multiplier": false_mult,
                        "event_rate_multiplier": event_mult,
                    }
                    loss = formula_loss(spec, values)
                    rows.append(
                        {
                            "index": index,
                            "standing_bias": bias,
                            "boost_reduction": boost,
                            "false_trigger_cost_multiplier": false_mult,
                            "event_rate_multiplier": event_mult,
                            "standing_bias_code": bc,
                            "boost_reduction_code": gc,
                            "false_trigger_cost_multiplier_code": fc,
                            "event_rate_multiplier_code": ec,
                            "score_int": int(round(scale * loss)),
                            "loss": loss,
                        }
                    )
                    index += 1
    if len(rows) != int(spec["valid_candidate_count"]):
        raise AssertionError("codebook Cartesian product does not match valid_candidate_count")
    return rows


def feasibility_by_parameter(spec: dict, rows: list[dict]) -> dict:
    threshold = int(spec["fixed_point"]["threshold_int"])
    out = {}
    for name, _ in FIELDS:
        code_key = name + "_code"
        groups = defaultdict(list)
        for row in rows:
            groups[int(row[code_key])].append(int(row["score_int"]))
        code_rows = []
        for code in sorted(groups):
            vals = groups[code]
            mn = min(vals)
            code_rows.append(
                {
                    "code": code,
                    "value": codebook_lookup(spec)[name][code],
                    "minimum_score_over_other_parameters": mn,
                    "can_pass_threshold": bool(mn <= threshold),
                }
            )
        out[name] = code_rows
    return out


def derived_marked_rows(spec: dict, rows: list[dict]) -> list[dict]:
    threshold = int(spec["fixed_point"]["threshold_int"])
    return [row for row in rows if int(row["score_int"]) <= threshold]


def conditional_false_rule(spec: dict, marked_rows: list[dict]) -> dict[str, list[int]]:
    out = defaultdict(set)
    for row in marked_rows:
        out[str(int(row["standing_bias_code"]))].add(
            int(row["false_trigger_cost_multiplier_code"])
        )
    return {key: sorted(vals) for key, vals in sorted(out.items(), key=lambda kv: int(kv[0]))}


def state_set_from_rows(spec: dict, rows: list[dict]) -> set[int]:
    ranges = field_bit_ranges(spec)
    out = set()
    for row in rows:
        codes = {
            "standing_bias": int(row["standing_bias_code"]),
            "boost_reduction": int(row["boost_reduction_code"]),
            "false_trigger_cost_multiplier": int(row["false_trigger_cost_multiplier_code"]),
            "event_rate_multiplier": int(row["event_rate_multiplier_code"]),
        }
        out.add(compose_codes(codes, ranges))
    return out


def regression_marked_states(spec: dict) -> set[int]:
    """Independent regression target only; never used to construct predicate."""
    widths = spec["parameter_register_bits"]
    rows = list(arithmetic.code_tuples(spec))
    out = set()
    for i in [int(x) for x in spec["marked_indices"]]:
        bc, _b, gc, _g, fc, _f, ec, _e = rows[i]
        out.add(
            audit.compose_state(
                {
                    "bias_code": bc,
                    "boost_code": gc,
                    "false_code": fc,
                    "event_code": ec,
                },
                widths,
            )
        )
    return out


def common_constraints_from_necessary_sets(spec: dict, feasibility: dict) -> dict[int, int]:
    ranges = field_bit_ranges(spec)
    common = {}
    for name, _ in FIELDS:
        allowed_codes = [
            int(r["code"]) for r in feasibility[name] if r["can_pass_threshold"]
        ]
        if not allowed_codes:
            raise RuntimeError(f"no threshold-feasible code for {name}")
        for local_bit, global_bit in enumerate(ranges[name]):
            vals = {(code >> local_bit) & 1 for code in allowed_codes}
            if len(vals) == 1:
                common[global_bit] = next(iter(vals))
    return common


def verify_formula_predicate_all_basis(
    spec: dict,
    full_esop: list[tuple[int, ...]],
    model_states: set[int],
) -> None:
    n = int(spec["parameter_register_bits"]["total_parameter_bits"])
    semantic.verify_xor_cubes(full_esop, model_states, n)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    n = int(spec["parameter_register_bits"]["total_parameter_bits"])
    threshold = int(spec["fixed_point"]["threshold_int"])
    scale = int(spec["fixed_point"]["scale"])

    rows = enumerate_model_rows(spec)
    feasibility = feasibility_by_parameter(spec, rows)
    marked_rows = derived_marked_rows(spec, rows)
    model_states = state_set_from_rows(spec, marked_rows)

    # This is the key methodological boundary: construction above used formula,
    # threshold, and codebooks only.  The frozen marked list appears only here.
    regression_states = regression_marked_states(spec)
    regression_match = model_states == regression_states
    if not regression_match:
        raise AssertionError(
            f"model-derived classification disagrees with frozen marked target: "
            f"derived={sorted(model_states)} expected={sorted(regression_states)}"
        )

    # Derive common bit constraints first from per-parameter threshold
    # feasibility, then confirm they match the constraints common to all
    # formula-derived passing states.
    necessary_common = common_constraints_from_necessary_sets(spec, feasibility)
    observed_common = semantic.common_constraints(sorted(model_states), n)
    if necessary_common != observed_common:
        raise AssertionError(
            f"necessary-code common constraints {necessary_common} != "
            f"model-state common constraints {observed_common}"
        )

    local_bits = [bit for bit in range(n) if bit not in necessary_common]
    local_marked = {semantic.local_state(s, local_bits) for s in model_states}
    esop_local = semantic.minimum_esop(local_marked, len(local_bits))
    esop_full = [
        semantic.merge_local_cube(cube, local_bits, necessary_common, n)
        for cube in esop_local
    ]
    verify_formula_predicate_all_basis(spec, esop_full, model_states)

    conditional_false = conditional_false_rule(spec, marked_rows)

    compiled = {}
    circuits = {}
    for rounds in (1, 6):
        qc = semantic.build_variant(
            n,
            sorted(model_states),
            None,
            rounds,
            factored=True,
            local_cubes=esop_local,
            local_bits=local_bits,
            common=necessary_common,
        )
        circuits[rounds] = qc
        compiled[str(rounds)] = semantic.compile_probe(
            qc, args.optimization_level, args.seed_transpiler, args.profile
        )

    print("===== TCT MODEL-DERIVED THRESHOLD PREDICATE =====")
    print(
        f"threshold_int={threshold} scale={scale} valid={len(rows)} "
        f"derived_marked={len(model_states)} regression_match={regression_match}"
    )
    print("\n===== NECESSARY CODE FEASIBILITY FROM MODEL =====")
    for name, _ in FIELDS:
        passing = [r["code"] for r in feasibility[name] if r["can_pass_threshold"]]
        print(f"{name}: threshold_feasible_codes={passing}")
        for r in feasibility[name]:
            print(
                f"  code={r['code']} value={r['value']} "
                f"best_score={r['minimum_score_over_other_parameters']} "
                f"can_pass={r['can_pass_threshold']}"
            )

    print("\n===== DERIVED PREDICATE STRUCTURE =====")
    print(
        "common_constraints={" + ", ".join(
            f"q{b}={v}" for b, v in sorted(necessary_common.items())
        ) + "}"
    )
    print(f"local_bits={local_bits}")
    print(f"conditional_false_codes_by_bias={json.dumps(conditional_false, sort_keys=True)}")
    print(f"local_esop_terms={len(esop_local)}")
    for cube in esop_local:
        print("  local_esop=" + audit.compact_cube(cube))
    print(f"model_derived_states={sorted(model_states)}")

    print("\n===== COMPILER RESULTS =====")
    for rounds in (1, 6):
        r = compiled[str(rounds)]
        print(
            f"rounds={rounds} width={circuits[rounds].num_qubits} "
            f"CZ={r['native_cz']} depth={r['compiled_depth']} "
            f"size={r['compiled_size']} weighted_edges={r['weighted_edge_count']}"
        )
    six = compiled["6"]
    print(
        f"six_round_CZ_ratio_vs_grid_factored_arithmetic={six['native_cz']/42756:.6f} "
        f"six_round_depth_ratio_vs_grid_factored_arithmetic={six['compiled_depth']/132481:.6f}"
    )

    result = {
        "experiment": "tct_model_derived_threshold_predicate_v1",
        "script_revision": REV,
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "construction_uses_frozen_marked_indices": False,
        "marked_indices_used_only_for_regression_check": True,
        "fixed_point": {"scale": scale, "threshold_int": threshold},
        "formula": spec.get("formula"),
        "formula_constants": spec.get("formula_constants"),
        "feasibility_by_parameter": feasibility,
        "conditional_false_codes_by_bias": conditional_false,
        "derived_marked_states": sorted(model_states),
        "regression_marked_states": sorted(regression_states),
        "regression_match": regression_match,
        "common_constraints": {str(k): int(v) for k, v in sorted(necessary_common.items())},
        "local_bits": local_bits,
        "model_derived_local_esop": [audit.compact_cube(c) for c in esop_local],
        "basis_truth_table_verified_512": True,
        "compiled": compiled,
        "claim_boundary": (
            "Finite-codebook model-derived threshold specialization. The oracle is "
            "constructed from the reduced-order loss formula, fixed-point threshold, "
            "and frozen codebooks rather than a prelisted marked-state table. This is "
            "still not a general scalable numerical objective evaluator, not fusion "
            "validation, and not evidence of end-to-end quantum advantage."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
