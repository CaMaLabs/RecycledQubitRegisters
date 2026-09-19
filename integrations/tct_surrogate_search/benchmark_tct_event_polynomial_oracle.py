#!/usr/bin/env python3
"""Benchmark exact multilinear/Mobius synthesis of the TCT event term.

The v1 reversible arithmetic oracle evaluates the event contribution by
selecting one of 64 precomputed constants with an equality pattern over six
parameter bits (2 event-rate, 2 standing-bias, 2 boost).  That block dominates
~99% of forward-score CZ.

This zero-QPU experiment keeps the *same exact 64 integer event values* but
rewrites the six-bit integer-valued function in its unique multilinear form

    f(x) = sum_S c_S prod_{i in S} x_i

using a Mobius transform.  Each nonzero monomial becomes one constant addition
controlled only by the bits in that monomial; no equality-pattern X masks are
needed.  The script:

1. reconstructs the classification-exact factorized encoding;
2. derives and exhaustively verifies the exact multilinear event function over
   all 64 event/bias/boost code assignments;
3. reports the nonzero coefficient/control-degree distribution;
4. compiles the old equality-pattern event block and the new polynomial block
   on the same fully connected 24-qubit synthetic backend; and
5. compiles a full one-round arithmetic Grover circuit with the polynomial
   event block substituted, leaving thresholding, validity checks, bias/false
   terms, uncomputation, and diffuser otherwise unchanged.

This is an exact structured-function synthesis experiment, but it is still a
finite six-bit event-function representation rather than a general reversible
multiplier.  No IBM service or QPU job is used.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import benchmark_tct_reversible_arithmetic_oracle as arith
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-19-tct-event-polynomial-oracle-v1"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_event_polynomial_oracle.json"


def code_bits(code: int, width: int = 2) -> list[int]:
    return [(code >> i) & 1 for i in range(width)]


def event_truth_table(event_table) -> list[int]:
    """Return f(mask) for variables [b0,b1,g0,g1,e0,e1]."""
    values: list[int | None] = [None] * 64
    for ec, bc, gc, value in event_table:
        b = code_bits(int(bc))
        g = code_bits(int(gc))
        e = code_bits(int(ec))
        bits = b + g + e
        mask = sum(bit << i for i, bit in enumerate(bits))
        if values[mask] is not None:
            raise AssertionError(f"duplicate event truth-table assignment mask={mask}")
        values[mask] = int(value)
    if any(v is None for v in values):
        missing = [i for i, v in enumerate(values) if v is None]
        raise RuntimeError(f"event table is not a complete 6-bit function; missing={missing}")
    return [int(v) for v in values]


def mobius_coefficients(values: list[int]) -> list[int]:
    """Integer multilinear coefficients for f(x) on the Boolean cube."""
    n = (len(values)).bit_length() - 1
    if (1 << n) != len(values):
        raise ValueError("truth-table length must be a power of two")
    coeff = list(values)
    for bit in range(n):
        for mask in range(1 << n):
            if mask & (1 << bit):
                coeff[mask] -= coeff[mask ^ (1 << bit)]
    return coeff


def evaluate_polynomial(coeff: list[int], assignment: int) -> int:
    total = 0
    sub = assignment
    while True:
        total += int(coeff[sub])
        if sub == 0:
            break
        sub = (sub - 1) & assignment
    return total


def verify_polynomial(values: list[int], coeff: list[int]) -> None:
    errors = []
    for x, expected in enumerate(values):
        observed = evaluate_polynomial(coeff, x)
        if observed != expected:
            errors.append((x, expected, observed))
    if errors:
        raise AssertionError(f"Mobius polynomial verification failed: {errors[:8]}")


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


def polynomial_variable_qubits(regs: dict[str, list[int]]) -> list[int]:
    # Must match event_truth_table variable order [b0,b1,g0,g1,e0,e1].
    return list(regs["bias"]) + list(regs["boost"]) + list(regs["event"])


def apply_event_polynomial(
    qc: QuantumCircuit,
    acc: list[int],
    variable_qubits: list[int],
    coeff: list[int],
    sign: int,
    skip_constant: bool = False,
) -> None:
    for mask, c in enumerate(coeff):
        if c == 0 or (skip_constant and mask == 0):
            continue
        controls = [variable_qubits[i] for i in range(len(variable_qubits)) if mask & (1 << i)]
        arith.phase_add_constant(qc, acc, sign * int(c), controls)


def apply_bias_false(
    qc: QuantumCircuit,
    regs: dict[str, list[int]],
    acc: list[int],
    bias_table,
    false_table,
    sign: int,
) -> None:
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


def build_lookup_event_forward(spec: dict, enc: dict, event_table) -> QuantumCircuit:
    regs, _params, acc, total = register_layout(spec, enc)
    qc = QuantumCircuit(total, name="tct_event_lookup_forward")
    arith.qft_inplace(qc, acc)
    for ec, bc, gc, value in event_table:
        arith.with_three_patterns(
            qc,
            [(regs["event"], ec), (regs["bias"], bc), (regs["boost"], gc)],
            lambda controls, v=value: arith.phase_add_constant(qc, acc, v, controls),
        )
    arith.iqft_inplace(qc, acc)
    return qc


def build_polynomial_event_forward(spec: dict, enc: dict, coeff: list[int]) -> QuantumCircuit:
    regs, _params, acc, total = register_layout(spec, enc)
    qc = QuantumCircuit(total, name="tct_event_polynomial_forward")
    arith.qft_inplace(qc, acc)
    apply_event_polynomial(qc, acc, polynomial_variable_qubits(regs), coeff, +1)
    arith.iqft_inplace(qc, acc)
    return qc


def build_full_polynomial_round(
    spec: dict,
    enc: dict,
    coeff: list[int],
    bias_table,
    false_table,
) -> QuantumCircuit:
    regs, params, acc, total = register_layout(spec, enc)
    qc = QuantumCircuit(total, name="tct_polynomial_arithmetic_grover")
    variables = polynomial_variable_qubits(regs)
    modulus = 1 << len(acc)
    offset = modulus - (int(enc["threshold_int"]) + 1)
    constant = int(coeff[0])

    # The unconditional polynomial constant and comparator offset are merged.
    qc.h(params)

    arith.qft_inplace(qc, acc)
    arith.phase_add_constant(qc, acc, offset + constant)
    apply_event_polynomial(qc, acc, variables, coeff, +1, skip_constant=True)
    apply_bias_false(qc, regs, acc, bias_table, false_table, +1)
    arith.iqft_inplace(qc, acc)

    arith.phase_mark_valid_low_score(qc, regs["false"], acc[-1])

    arith.qft_inplace(qc, acc)
    arith.phase_add_constant(qc, acc, -(offset + constant))
    apply_event_polynomial(qc, acc, variables, coeff, -1, skip_constant=True)
    apply_bias_false(qc, regs, acc, bias_table, false_table, -1)
    arith.iqft_inplace(qc, acc)

    arith.diffuser(qc, params)
    return qc


def compile_probe(qc: QuantumCircuit, level: int, seed: int, profile: str) -> dict:
    backend = topo.generic(qc.num_qubits, mapper.full_coupling(qc.num_qubits))
    compiled, elapsed = mapper.compile_circuit(
        qc, backend, profile, level, seed, list(range(qc.num_qubits))
    )
    pair_weights, meta = mapper.extract_two_qubit_interactions(compiled)
    stats = mapper.compiled_stats(qc, compiled, elapsed)
    return {
        "weighted_edge_count": int(meta["weighted_edge_count"]),
        "total_two_qubit_weight": float(meta["total_two_qubit_weight"]),
        **stats,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    enc = arith.factorized_encoding(spec)
    if not enc["classification_exact"]:
        raise RuntimeError("factorized encoding is not classification-exact")

    event_table, bias_table, false_table = arith.contribution_tables(spec, enc)
    values = event_truth_table(event_table)
    coeff = mobius_coefficients(values)
    verify_polynomial(values, coeff)

    nonzero = [(mask, int(c)) for mask, c in enumerate(coeff) if c]
    degree_counts = Counter(mask.bit_count() for mask, _ in nonzero)
    abs_coeff_max = max(abs(c) for _, c in nonzero)

    lookup_qc = build_lookup_event_forward(spec, enc, event_table)
    poly_qc = build_polynomial_event_forward(spec, enc, coeff)
    full_poly_qc = build_full_polynomial_round(spec, enc, coeff, bias_table, false_table)

    compiled = {
        "lookup_event_forward": compile_probe(lookup_qc, args.optimization_level, args.seed_transpiler, args.profile),
        "polynomial_event_forward": compile_probe(poly_qc, args.optimization_level, args.seed_transpiler, args.profile),
        "full_one_round_polynomial": compile_probe(full_poly_qc, args.optimization_level, args.seed_transpiler, args.profile),
    }

    old_event = compiled["lookup_event_forward"]
    new_event = compiled["polynomial_event_forward"]
    full_new = compiled["full_one_round_polynomial"]
    baseline_full_cz = 272126
    baseline_full_depth = 1083704

    print("===== TCT EVENT POLYNOMIAL SYNTHESIS =====")
    print(
        f"logical_width={full_poly_qc.num_qubits} event_values={len(values)} "
        f"nonzero_monomials={len(nonzero)} max_abs_coefficient={abs_coeff_max}"
    )
    print("degree_distribution=" + json.dumps({str(k): degree_counts[k] for k in sorted(degree_counts)}))
    print("polynomial_exact_over_64_states=True")
    print("nonzero_coefficients:")
    for mask, c in nonzero:
        print(f"  mask={mask:06b} degree={mask.bit_count()} coefficient={c}")

    print("\n===== EVENT/FULL COMPILER COMPARISON =====")
    for name, row in compiled.items():
        print(
            f"{name}: CZ={row['native_cz']} depth={row['compiled_depth']} "
            f"size={row['compiled_size']} weighted_edges={row['weighted_edge_count']}"
        )
    print(
        f"event_CZ_ratio={new_event['native_cz']/old_event['native_cz']:.6f} "
        f"event_depth_ratio={new_event['compiled_depth']/old_event['compiled_depth']:.6f}"
    )
    print(
        f"full_CZ_ratio_vs_v1={full_new['native_cz']/baseline_full_cz:.6f} "
        f"full_depth_ratio_vs_v1={full_new['compiled_depth']/baseline_full_depth:.6f}"
    )

    payload = {
        "experiment": "tct_event_polynomial_oracle_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "logical_width": full_poly_qc.num_qubits,
        "event_truth_values": values,
        "polynomial_exact_over_64_states": True,
        "nonzero_monomial_count": len(nonzero),
        "degree_distribution": {str(k): int(v) for k, v in sorted(degree_counts.items())},
        "coefficients": [
            {"mask": mask, "mask_binary": f"{mask:06b}", "degree": mask.bit_count(), "coefficient": c}
            for mask, c in nonzero
        ],
        "compiled": compiled,
        "baseline_full_v1": {"native_cz": baseline_full_cz, "compiled_depth": baseline_full_depth},
        "claim_boundary": (
            "Exact multilinear synthesis of the finite six-bit event function. "
            "It preserves the integer event table exactly and is more structured than 64 equality-pattern selects, "
            "but it is not yet a general reversible multiplier or evidence of end-to-end quantum advantage."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
