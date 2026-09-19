#!/usr/bin/env python3
"""Benchmark a grid-factored/shift implementation of the TCT arithmetic oracle.

The previous exact event-polynomial experiment preserved all 64 independently
rounded event-table values and reduced the event block substantially, but the
result still contained 54 Boolean monomials through degree six.

This zero-QPU experiment instead goes back to the source reduced-order formula

    L = A * event_mult * (1-bias) * (1-r*boost)
        + B*bias + C*false_mult

and exploits exact structure in the frozen parameter grids:

* standing bias is affine in its two-bit code;
* boost is affine in its two-bit code;
* the Mirnov+toroidal reachable fraction is recovered as the rational 38/59;
* event multiplier values 0.25, 0.5, 1, 2 become powers of two after a common
  denominator is removed.

After removing common rational denominators, the bias/boost event base is a
four-bit degree-2 polynomial.  Event-rate scaling is then implemented by
reversible controlled bit rotations (safe left shifts on the bounded event
subspace), rather than by 64 equality selects or a six-bit truth-table
polynomial.

A transformed integer scale is searched classically and accepted only if an
inclusive threshold reproduces exactly the same eight marked scenarios across
all 320 valid candidates.  This therefore preserves the frozen marked-set
classification, but it intentionally does *not* preserve each previously
rounded integer event-table value.

No IBM service, Sampler, or QPU job is used.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from functools import reduce
from pathlib import Path
from math import gcd, lcm

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import benchmark_tct_reversible_arithmetic_oracle as arith
import benchmark_tct_event_polynomial_oracle as poly
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-19-tct-grid-factored-shift-oracle-v1"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_oracle.json"


def ffrac(value: float, max_denominator: int = 10000) -> Fraction:
    return Fraction(str(float(value))).limit_denominator(max_denominator)


def codebook_map(spec: dict, name: str) -> dict[int, float]:
    return {
        int(row["code"]): float(row["value"])
        for row in spec["parameter_codebooks"][name]
    }


def common_denominator(values: list[Fraction]) -> int:
    return reduce(lcm, (v.denominator for v in values), 1)


def derive_grid_factors(spec: dict) -> dict:
    bias_values = codebook_map(spec, "standing_bias")
    boost_values = codebook_map(spec, "boost_reduction")
    event_values = codebook_map(spec, "event_rate_multiplier")

    bias_frac = {k: ffrac(v) for k, v in bias_values.items()}
    boost_frac = {k: ffrac(v) for k, v in boost_values.items()}
    event_frac = {k: ffrac(v) for k, v in event_values.items()}

    bias_den = common_denominator(list(bias_frac.values()))
    boost_den = common_denominator(list(boost_frac.values()))
    event_den = common_denominator(list(event_frac.values()))

    bias_num = {k: int(v * bias_den) for k, v in bias_frac.items()}
    boost_num = {k: int(v * boost_den) for k, v in boost_frac.items()}
    event_num = {k: int(v * event_den) for k, v in event_frac.items()}

    r_float = float(spec["formula_constants"]["reachable_fraction"])
    r = Fraction(r_float).limit_denominator(10000)
    if abs(float(r) - r_float) > 1e-12:
        raise RuntimeError(f"reachable fraction was not recovered cleanly as a small rational: {r}")

    bias_factor = {k: bias_den - n for k, n in bias_num.items()}
    boost_raw = {
        k: boost_den * r.denominator - r.numerator * n
        for k, n in boost_num.items()
    }
    boost_gcd = reduce(gcd, (abs(v) for v in boost_raw.values()))
    boost_factor = {k: v // boost_gcd for k, v in boost_raw.items()}

    expected_event = {code: 1 << code for code in sorted(event_num)}
    if event_num != expected_event:
        raise RuntimeError(
            "event grid is not the expected power-of-two sequence after common denominator removal: "
            f"observed={event_num} expected={expected_event}"
        )

    c = spec["formula_constants"]
    A = float(c["A_event_base"])
    event_unit_loss = (
        A
        * boost_gcd
        / (event_den * bias_den * boost_den * r.denominator)
    )
    if event_unit_loss <= 0:
        raise RuntimeError("invalid event-unit loss")

    return {
        "bias_denominator": bias_den,
        "boost_denominator": boost_den,
        "event_denominator": event_den,
        "reachable_fraction": {"numerator": r.numerator, "denominator": r.denominator},
        "bias_numerators": bias_num,
        "boost_numerators": boost_num,
        "event_numerators": event_num,
        "bias_factors": bias_factor,
        "boost_raw_factors": boost_raw,
        "boost_common_gcd": boost_gcd,
        "boost_factors": boost_factor,
        "event_unit_loss": event_unit_loss,
    }


def transformed_encoding(spec: dict, factors: dict, max_q: int = 100000) -> dict:
    c = spec["formula_constants"]
    B = float(c["B_bias_cost_per_unit_bias"])
    C = float(c["C_false_cost_per_unit_multiplier"])
    D = float(factors["event_unit_loss"])
    marked = {int(x) for x in spec["marked_indices"]}
    rows = list(arith.code_tuples(spec))

    bias_factor = {int(k): int(v) for k, v in factors["bias_factors"].items()}
    boost_factor = {int(k): int(v) for k, v in factors["boost_factors"].items()}
    event_num = {int(k): int(v) for k, v in factors["event_numerators"].items()}

    for qscale in range(1, max_q + 1):
        scores = []
        term_rows = []
        loss_errors = []
        for row in rows:
            bc, bias, gc, boost, fc, false_mult, ec, event_mult = row
            event_term = qscale * event_num[ec] * bias_factor[bc] * boost_factor[gc]
            bias_term = int(round(qscale * B * bias / D))
            false_term = int(round(qscale * C * false_mult / D))
            score = event_term + bias_term + false_term
            exact_loss = (
                float(c["A_event_base"])
                * event_mult
                * (1.0 - bias)
                * (1.0 - float(c["reachable_fraction"]) * boost)
                + B * bias
                + C * false_mult
            )
            reconstructed = D * score / qscale
            scores.append(score)
            loss_errors.append(abs(reconstructed - exact_loss))
            term_rows.append(
                {
                    "bias_code": bc,
                    "boost_code": gc,
                    "false_code": fc,
                    "event_code": ec,
                    "event_term": event_term,
                    "bias_term": bias_term,
                    "false_term": false_term,
                    "score": score,
                }
            )

        threshold = max(scores[i] for i in sorted(marked))
        classified = {i for i, score in enumerate(scores) if score <= threshold}
        if classified == marked:
            return {
                "qscale": qscale,
                "threshold_int": int(threshold),
                "maximum_score_int": int(max(scores)),
                "minimum_score_int": int(min(scores)),
                "classification_exact": True,
                "rows": term_rows,
                "max_abs_loss_error": float(max(loss_errors)),
                "marked_indices": sorted(marked),
            }
    raise RuntimeError(f"no classification-exact transformed scale found through q={max_q}")


def base_event_truth_table(spec: dict, factors: dict, enc: dict) -> list[int]:
    qscale = int(enc["qscale"])
    bf = {int(k): int(v) for k, v in factors["bias_factors"].items()}
    gf = {int(k): int(v) for k, v in factors["boost_factors"].items()}
    values = [0] * 16
    for bc in range(4):
        for gc in range(4):
            mask = bc | (gc << 2)  # variables [b0,b1,g0,g1]
            values[mask] = qscale * bf[bc] * gf[gc]
    return values


def register_layout(spec: dict, enc: dict):
    bias_bits = int(spec["parameter_register_bits"]["standing_bias"])
    boost_bits = int(spec["parameter_register_bits"]["boost_reduction"])
    false_bits = int(spec["parameter_register_bits"]["false_trigger_cost_multiplier"])
    event_bits = int(spec["parameter_register_bits"]["event_rate_multiplier"])
    param_bits = bias_bits + boost_bits + false_bits + event_bits
    nacc = arith.choose_comparison_bits(enc["maximum_score_int"], enc["threshold_int"])

    cursor = 0
    regs = {}
    regs["bias"] = list(range(cursor, cursor + bias_bits)); cursor += bias_bits
    regs["boost"] = list(range(cursor, cursor + boost_bits)); cursor += boost_bits
    regs["false"] = list(range(cursor, cursor + false_bits)); cursor += false_bits
    regs["event"] = list(range(cursor, cursor + event_bits)); cursor += event_bits
    params = list(range(param_bits))
    acc = list(range(cursor, cursor + nacc))
    return regs, params, acc, param_bits + nacc


def apply_base_polynomial(
    qc: QuantumCircuit,
    acc: list[int],
    regs: dict[str, list[int]],
    coeff: list[int],
    sign: int,
) -> None:
    variables = list(regs["bias"]) + list(regs["boost"])
    for mask, c in enumerate(coeff):
        if c == 0:
            continue
        controls = [variables[i] for i in range(4) if mask & (1 << i)]
        arith.phase_add_constant(qc, acc, sign * int(c), controls)


def rotate_left_once(qc: QuantumCircuit, acc: list[int], control: int) -> None:
    # Cyclic left rotation of integer bit positions. On the bounded subspace used
    # here the high bit is zero, so this equals multiplication by two.
    for j in range(len(acc) - 1, 0, -1):
        qc.cswap(control, acc[j], acc[j - 1])


def rotate_right_once(qc: QuantumCircuit, acc: list[int], control: int) -> None:
    # Exact inverse of rotate_left_once.
    for j in range(1, len(acc)):
        qc.cswap(control, acc[j], acc[j - 1])


def apply_event_shift_forward(qc: QuantumCircuit, acc: list[int], event: list[int]) -> None:
    if len(event) != 2:
        raise RuntimeError("v1 grid-factored shift benchmark expects two event-code bits")
    rotate_left_once(qc, acc, event[0])
    rotate_left_once(qc, acc, event[1])
    rotate_left_once(qc, acc, event[1])


def apply_event_shift_inverse(qc: QuantumCircuit, acc: list[int], event: list[int]) -> None:
    rotate_right_once(qc, acc, event[1])
    rotate_right_once(qc, acc, event[1])
    rotate_right_once(qc, acc, event[0])


def self_test_controlled_shifts() -> None:
    n = 7
    total = n + 2
    acc = list(range(n))
    event = [n, n + 1]
    for x in range(8):  # leaves three guaranteed headroom bits
        for code in range(4):
            qc = QuantumCircuit(total)
            for bit in range(n):
                if (x >> bit) & 1:
                    qc.x(bit)
            for bit in range(2):
                if (code >> bit) & 1:
                    qc.x(event[bit])
            apply_event_shift_forward(qc, acc, event)
            sv = Statevector.from_instruction(qc)
            expected_value = x << code
            expected_index = expected_value | (((code >> 0) & 1) << n) | (((code >> 1) & 1) << (n + 1))
            p = abs(complex(sv.data[expected_index])) ** 2
            if p < 1.0 - 1e-9:
                raise AssertionError(
                    f"controlled-shift self-test failed x={x} code={code} p={p}"
                )


def transformed_additive_tables(spec: dict, factors: dict, enc: dict):
    c = spec["formula_constants"]
    B = float(c["B_bias_cost_per_unit_bias"])
    C = float(c["C_false_cost_per_unit_multiplier"])
    D = float(factors["event_unit_loss"])
    qscale = int(enc["qscale"])

    bias_table = []
    for row in spec["parameter_codebooks"]["standing_bias"]:
        value = int(round(qscale * B * float(row["value"]) / D))
        if value:
            bias_table.append((int(row["code"]), value))

    false_table = []
    for row in spec["parameter_codebooks"]["false_trigger_cost_multiplier"]:
        value = int(round(qscale * C * float(row["value"]) / D))
        if value:
            false_table.append((int(row["code"]), value))
    return bias_table, false_table


def apply_additives(
    qc: QuantumCircuit,
    regs: dict[str, list[int]],
    acc: list[int],
    bias_table,
    false_table,
    offset: int,
    sign: int,
) -> None:
    arith.phase_add_constant(qc, acc, sign * offset)
    for bc, value in bias_table:
        arith.with_pattern(
            qc,
            regs["bias"],
            bc,
            lambda v=sign * value, ctrls=list(regs["bias"]): arith.phase_add_constant(qc, acc, v, ctrls),
        )
    for fc, value in false_table:
        arith.with_pattern(
            qc,
            regs["false"],
            fc,
            lambda v=sign * value, ctrls=list(regs["false"]): arith.phase_add_constant(qc, acc, v, ctrls),
        )


def verify_classical_circuit_contract(spec: dict, factors: dict, enc: dict) -> dict:
    regs_dummy = None
    nacc = arith.choose_comparison_bits(enc["maximum_score_int"], enc["threshold_int"])
    modulus = 1 << nacc
    offset = modulus - (int(enc["threshold_int"]) + 1)
    failures = []
    max_event = 0
    for row in enc["rows"]:
        event_term = int(row["event_term"])
        max_event = max(max_event, event_term)
        if event_term >= modulus:
            failures.append({"kind": "event_overflow", "row": row})
        score = int(row["score"])
        shifted = (score + offset) % modulus
        observed = bool((shifted >> (nacc - 1)) & 1)
        expected = score <= int(enc["threshold_int"])
        if observed != expected:
            failures.append({"kind": "comparator", "row": row, "shifted": shifted})
    if failures:
        raise AssertionError(f"classical transformed-circuit contract failed: {failures[:4]}")
    return {"nacc": nacc, "modulus": modulus, "offset": offset, "maximum_event_term": max_event}


def build_event_forward(spec: dict, enc: dict, coeff: list[int]) -> QuantumCircuit:
    regs, _params, acc, total = register_layout(spec, enc)
    qc = QuantumCircuit(total, name="tct_grid_factored_shift_event_forward")
    arith.qft_inplace(qc, acc)
    apply_base_polynomial(qc, acc, regs, coeff, +1)
    arith.iqft_inplace(qc, acc)
    apply_event_shift_forward(qc, acc, regs["event"])
    return qc


def build_full_round(spec: dict, enc: dict, coeff: list[int], bias_table, false_table) -> QuantumCircuit:
    regs, params, acc, total = register_layout(spec, enc)
    qc = QuantumCircuit(total, name="tct_grid_factored_shift_grover")
    modulus = 1 << len(acc)
    offset = modulus - (int(enc["threshold_int"]) + 1)

    qc.h(params)

    # Compute event base P(bias,boost), then multiply by event_num=2^code
    # through reversible bounded rotations.
    arith.qft_inplace(qc, acc)
    apply_base_polynomial(qc, acc, regs, coeff, +1)
    arith.iqft_inplace(qc, acc)
    apply_event_shift_forward(qc, acc, regs["event"])

    # Add bias/false terms and comparator offset.
    arith.qft_inplace(qc, acc)
    apply_additives(qc, regs, acc, bias_table, false_table, offset, +1)
    arith.iqft_inplace(qc, acc)

    arith.phase_mark_valid_low_score(qc, regs["false"], acc[-1])

    # Uncompute in exact reverse order.
    arith.qft_inplace(qc, acc)
    apply_additives(qc, regs, acc, bias_table, false_table, offset, -1)
    arith.iqft_inplace(qc, acc)
    apply_event_shift_inverse(qc, acc, regs["event"])
    arith.qft_inplace(qc, acc)
    apply_base_polynomial(qc, acc, regs, coeff, -1)
    arith.iqft_inplace(qc, acc)

    arith.diffuser(qc, params)
    return qc


def compile_probe(qc: QuantumCircuit, level: int, seed: int, profile: str) -> dict:
    backend = topo.generic(qc.num_qubits, mapper.full_coupling(qc.num_qubits))
    compiled, elapsed = mapper.compile_circuit(
        qc, backend, profile, level, seed, list(range(qc.num_qubits))
    )
    _pairs, meta = mapper.extract_two_qubit_interactions(compiled)
    stats = mapper.compiled_stats(qc, compiled, elapsed)
    return {
        "weighted_edge_count": int(meta["weighted_edge_count"]),
        "total_two_qubit_weight": float(meta["total_two_qubit_weight"]),
        **stats,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--max-qscale", type=int, default=100000)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    self_test_controlled_shifts()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    factors = derive_grid_factors(spec)
    enc = transformed_encoding(spec, factors, args.max_qscale)
    if not enc["classification_exact"]:
        raise RuntimeError("transformed integer encoding is not classification-exact")

    contract = verify_classical_circuit_contract(spec, factors, enc)
    values = base_event_truth_table(spec, factors, enc)
    coeff = poly.mobius_coefficients(values)
    poly.verify_polynomial(values, coeff)
    nonzero = [(mask, int(c)) for mask, c in enumerate(coeff) if c]
    degree_counts = Counter(mask.bit_count() for mask, _ in nonzero)
    if max(degree_counts) > 2:
        raise AssertionError(f"expected degree-2 bias/boost base polynomial, got {degree_counts}")

    bias_table, false_table = transformed_additive_tables(spec, factors, enc)
    event_qc = build_event_forward(spec, enc, coeff)
    full_qc = build_full_round(spec, enc, coeff, bias_table, false_table)

    compiled = {
        "grid_factored_shift_event_forward": compile_probe(
            event_qc, args.optimization_level, args.seed_transpiler, args.profile
        ),
        "full_one_round_grid_factored_shift": compile_probe(
            full_qc, args.optimization_level, args.seed_transpiler, args.profile
        ),
    }

    full = compiled["full_one_round_grid_factored_shift"]
    old_v1 = {"native_cz": 272126, "compiled_depth": 1083704}
    old_poly = {"native_cz": 49958, "compiled_depth": 213221}

    print("===== TCT GRID-FACTORED SHIFT ENCODING =====")
    print(
        f"reachable_fraction={factors['reachable_fraction']['numerator']}/"
        f"{factors['reachable_fraction']['denominator']} "
        f"event_unit_loss={factors['event_unit_loss']:.12g}"
    )
    print(
        f"qscale={enc['qscale']} threshold={enc['threshold_int']} "
        f"max_score={enc['maximum_score_int']} accumulator_bits={contract['nacc']} "
        f"logical_width={full_qc.num_qubits}"
    )
    print(
        f"classification_exact=True controlled_shift_self_test=True "
        f"max_abs_loss_error={enc['max_abs_loss_error']:.6g}"
    )
    print(
        f"bias_factors={factors['bias_factors']} boost_factors={factors['boost_factors']} "
        f"event_numerators={factors['event_numerators']}"
    )
    print(
        f"base_event_nonzero_monomials={len(nonzero)} "
        f"degree_distribution={json.dumps({str(k): degree_counts[k] for k in sorted(degree_counts)})}"
    )
    print("base_event_coefficients:")
    for mask, c in nonzero:
        print(f"  mask={mask:04b} degree={mask.bit_count()} coefficient={c}")

    print("\n===== GRID-FACTORED SHIFT COMPILER COMPARISON =====")
    for name, row in compiled.items():
        print(
            f"{name}: CZ={row['native_cz']} depth={row['compiled_depth']} "
            f"size={row['compiled_size']} weighted_edges={row['weighted_edge_count']}"
        )
    print(
        f"full_CZ_ratio_vs_exact_polynomial={full['native_cz']/old_poly['native_cz']:.6f} "
        f"full_depth_ratio_vs_exact_polynomial={full['compiled_depth']/old_poly['compiled_depth']:.6f}"
    )
    print(
        f"full_CZ_ratio_vs_v1={full['native_cz']/old_v1['native_cz']:.6f} "
        f"full_depth_ratio_vs_v1={full['compiled_depth']/old_v1['compiled_depth']:.6f}"
    )

    payload = {
        "experiment": "tct_grid_factored_shift_oracle_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "factors": factors,
        "transformed_encoding": {
            k: v for k, v in enc.items() if k != "rows"
        },
        "classical_contract": contract,
        "controlled_shift_self_test": True,
        "base_event_truth_values": values,
        "base_event_coefficients": [
            {
                "mask": mask,
                "mask_binary": f"{mask:04b}",
                "degree": mask.bit_count(),
                "coefficient": c,
            }
            for mask, c in nonzero
        ],
        "base_event_degree_distribution": {
            str(k): int(v) for k, v in sorted(degree_counts.items())
        },
        "compiled": compiled,
        "comparison_baselines": {
            "arithmetic_v1": old_v1,
            "exact_event_polynomial_v1": old_poly,
        },
        "claim_boundary": (
            "Classification-exact transformed fixed-point implementation of the frozen reduced-order TCT grid. "
            "It exploits affine grid structure and power-of-two event scaling and does not preserve each prior rounded event-table value. "
            "It is not fusion-physics validation and does not establish end-to-end quantum advantage."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
