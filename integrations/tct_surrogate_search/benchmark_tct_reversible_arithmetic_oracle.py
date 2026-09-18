#!/usr/bin/env python3
"""Build and compile a reversible arithmetic oracle for the TCT reduced-order search.

Unlike benchmark_tct_surrogate_search.py, this script does not phase-mark a
precomputed list of basis states.  It coherently computes a factorized fixed-
point form of the FAIR-MAST-seeded Mirnov/toroidal loss into an accumulator,
compares the result with the frozen low-loss threshold, phase-marks valid
parameter codes, and uncomputes the accumulator.

The source arithmetic specification is produced by
Fusion_Blanket_Design_TCT/fair_mast_tct_reversible_oracle_spec.py.

The factorized loss is

    L = A * event_mult * (1-bias) * (1-reachable*boost)
        + B*bias + C*false_mult

The implementation uses code-controlled modular constant additions in the QFT
basis.  It is therefore a coherent arithmetic/function oracle, not a table of
320 full-state marks.  The three-factor event term is represented by its 64
small code-conditioned constants; bias and false-trigger terms add 4 and 5
constants respectively.  The script searches for the smallest decimal scale
whose *factorized integer arithmetic* reproduces the frozen 8-state marked set
exactly before it constructs any quantum circuit.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "hardware"
if str(HARDWARE) not in sys.path:
    sys.path.insert(0, str(HARDWARE))

import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-18-tct-reversible-arithmetic-oracle-v1"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_reversible_arithmetic_oracle_probe.json"


def ceil_log2(n: int) -> int:
    return max(1, math.ceil(math.log2(max(1, n))))


def bits_of(code: int, width: int) -> list[int]:
    return [(code >> i) & 1 for i in range(width)]


def code_tuples(spec: dict):
    books = spec["parameter_codebooks"]
    # Preserve the source sensitivity-loop ordering exactly:
    # bias -> boost -> false multiplier -> event multiplier.
    for b in books["standing_bias"]:
        for g in books["boost_reduction"]:
            for f in books["false_trigger_cost_multiplier"]:
                for e in books["event_rate_multiplier"]:
                    yield (
                        int(b["code"]), float(b["value"]),
                        int(g["code"]), float(g["value"]),
                        int(f["code"]), float(f["value"]),
                        int(e["code"]), float(e["value"]),
                    )


def factorized_encoding(spec: dict) -> dict:
    c = spec["formula_constants"]
    A = float(c["A_event_base"])
    r = float(c["reachable_fraction"])
    B = float(c["B_bias_cost_per_unit_bias"])
    C = float(c["C_false_cost_per_unit_multiplier"])
    marked = {int(x) for x in spec["marked_indices"]}
    rows = list(code_tuples(spec))
    if len(rows) != int(spec["valid_candidate_count"]):
        raise RuntimeError("parameter-codebook Cartesian product does not match valid count")

    start_digits = int(spec["fixed_point"]["decimal_digits"])
    for digits in range(start_digits, 8):
        scale = 10 ** digits
        scores = []
        term_rows = []
        for row in rows:
            bc, bias, gc, boost, fc, false_mult, ec, event_mult = row
            event_term = int(round(scale * A * event_mult * (1.0 - bias) * (1.0 - r * boost)))
            bias_term = int(round(scale * B * bias))
            false_term = int(round(scale * C * false_mult))
            score = event_term + bias_term + false_term
            scores.append(score)
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
            max_score = max(scores)
            return {
                "decimal_digits": digits,
                "scale": scale,
                "threshold_int": int(threshold),
                "maximum_score_int": int(max_score),
                "minimum_score_int": int(min(scores)),
                "marked_indices": sorted(marked),
                "classification_exact": True,
                "rows": term_rows,
            }
    raise RuntimeError("factorized integer arithmetic failed to reproduce marked set through 1e7 scale")


def choose_comparison_bits(max_score: int, threshold: int) -> int:
    # We compare score <= threshold without a comparator ancilla by adding
    # 2^n-(threshold+1) modulo 2^n and reading the accumulator MSB.
    # Pick n so low scores occupy the upper half and every high score wraps
    # into the lower half.
    n = ceil_log2(max_score + 1)
    while True:
        half = 1 << (n - 1)
        if threshold + 1 <= half and max_score - threshold - 1 < half:
            return n
        n += 1


def qft_inplace(qc: QuantumCircuit, qs: list[int]) -> None:
    n = len(qs)
    for j in range(n):
        qc.h(qs[j])
        for k in range(j + 1, n):
            qc.cp(math.pi / (2 ** (k - j)), qs[k], qs[j])
    for j in range(n // 2):
        qc.swap(qs[j], qs[n - j - 1])


def iqft_inplace(qc: QuantumCircuit, qs: list[int]) -> None:
    n = len(qs)
    for j in range(n // 2):
        qc.swap(qs[j], qs[n - j - 1])
    for j in reversed(range(n)):
        for k in reversed(range(j + 1, n)):
            qc.cp(-math.pi / (2 ** (k - j)), qs[k], qs[j])
        qc.h(qs[j])


def phase_add_constant(
    qc: QuantumCircuit,
    acc: list[int],
    value: int,
    controls: list[int] | None = None,
) -> None:
    """Add a classical constant while acc is in the full-QFT basis."""
    controls = controls or []
    modulus = 1 << len(acc)
    value %= modulus
    for j, q in enumerate(acc):
        angle = 2.0 * math.pi * value * (1 << j) / modulus
        # Drop exact/full-turn phases to keep the circuit smaller.
        angle = math.fmod(angle, 2.0 * math.pi)
        if abs(angle) < 1e-14:
            continue
        if controls:
            qc.mcp(angle, controls, q)
        else:
            qc.p(angle, q)


def with_pattern(
    qc: QuantumCircuit,
    qubits: list[int],
    code: int,
    fn,
) -> None:
    bits = bits_of(code, len(qubits))
    zeros = [q for q, bit in zip(qubits, bits) if bit == 0]
    for q in zeros:
        qc.x(q)
    fn()
    for q in reversed(zeros):
        qc.x(q)


def with_three_patterns(
    qc: QuantumCircuit,
    regs_codes: list[tuple[list[int], int]],
    fn,
) -> None:
    zeros = []
    controls = []
    for qubits, code in regs_codes:
        bits = bits_of(code, len(qubits))
        controls.extend(qubits)
        zeros.extend(q for q, bit in zip(qubits, bits) if bit == 0)
    for q in zeros:
        qc.x(q)
    fn(controls)
    for q in reversed(zeros):
        qc.x(q)


def contribution_tables(spec: dict, enc: dict):
    books = spec["parameter_codebooks"]
    c = spec["formula_constants"]
    scale = int(enc["scale"])
    A = float(c["A_event_base"])
    r = float(c["reachable_fraction"])
    B = float(c["B_bias_cost_per_unit_bias"])
    C = float(c["C_false_cost_per_unit_multiplier"])

    event = []
    for e in books["event_rate_multiplier"]:
        for b in books["standing_bias"]:
            for g in books["boost_reduction"]:
                value = int(round(
                    scale * A * float(e["value"]) * (1.0 - float(b["value"]))
                    * (1.0 - r * float(g["value"]))
                ))
                if value:
                    event.append((int(e["code"]), int(b["code"]), int(g["code"]), value))

    bias = []
    for b in books["standing_bias"]:
        value = int(round(scale * B * float(b["value"])))
        if value:
            bias.append((int(b["code"]), value))

    false = []
    for f in books["false_trigger_cost_multiplier"]:
        value = int(round(scale * C * float(f["value"])))
        if value:
            false.append((int(f["code"]), value))
    return event, bias, false


def apply_score_and_offset_phases(
    qc: QuantumCircuit,
    regs: dict[str, list[int]],
    acc: list[int],
    event_table,
    bias_table,
    false_table,
    offset: int,
    sign: int,
) -> None:
    phase_add_constant(qc, acc, sign * offset)

    for ec, bc, gc, value in event_table:
        with_three_patterns(
            qc,
            [
                (regs["event"], ec),
                (regs["bias"], bc),
                (regs["boost"], gc),
            ],
            lambda controls, v=sign * value: phase_add_constant(qc, acc, v, controls),
        )

    for bc, value in bias_table:
        with_pattern(
            qc,
            regs["bias"],
            bc,
            lambda v=sign * value, ctrls=list(regs["bias"]): phase_add_constant(qc, acc, v, ctrls),
        )

    for fc, value in false_table:
        with_pattern(
            qc,
            regs["false"],
            fc,
            lambda v=sign * value, ctrls=list(regs["false"]): phase_add_constant(qc, acc, v, ctrls),
        )


def phase_mark_valid_low_score(qc: QuantumCircuit, false_reg: list[int], score_msb: int) -> None:
    # false-trigger multiplier has five valid codes: 0..4.  Codes 5..7 are
    # padding states and must never be marked, even if their arithmetic happens
    # to fall below threshold.
    for code in range(5):
        with_pattern(
            qc,
            false_reg,
            code,
            lambda ctrls=list(false_reg): qc.mcp(math.pi, ctrls, score_msb),
        )


def diffuser(qc: QuantumCircuit, params: list[int]) -> None:
    qc.h(params)
    qc.x(params)
    qc.h(params[-1])
    qc.mcx(params[:-1], params[-1])
    qc.h(params[-1])
    qc.x(params)
    qc.h(params)


def build_circuit(spec: dict, enc: dict, rounds: int) -> tuple[QuantumCircuit, dict]:
    # Source register widths are fixed by the fusion specification.
    bias_bits = int(spec["parameter_register_bits"]["standing_bias"])
    boost_bits = int(spec["parameter_register_bits"]["boost_reduction"])
    false_bits = int(spec["parameter_register_bits"]["false_trigger_cost_multiplier"])
    event_bits = int(spec["parameter_register_bits"]["event_rate_multiplier"])
    param_bits = bias_bits + boost_bits + false_bits + event_bits

    nacc = choose_comparison_bits(enc["maximum_score_int"], enc["threshold_int"])
    total = param_bits + nacc
    qc = QuantumCircuit(total, name="tct_reversible_arithmetic_grover")

    cursor = 0
    regs = {}
    regs["bias"] = list(range(cursor, cursor + bias_bits)); cursor += bias_bits
    regs["boost"] = list(range(cursor, cursor + boost_bits)); cursor += boost_bits
    regs["false"] = list(range(cursor, cursor + false_bits)); cursor += false_bits
    regs["event"] = list(range(cursor, cursor + event_bits)); cursor += event_bits
    params = list(range(param_bits))
    acc = list(range(cursor, cursor + nacc))

    event_table, bias_table, false_table = contribution_tables(spec, enc)
    modulus = 1 << nacc
    offset = modulus - (int(enc["threshold_int"]) + 1)

    qc.h(params)
    for _ in range(rounds):
        qft_inplace(qc, acc)
        apply_score_and_offset_phases(
            qc, regs, acc, event_table, bias_table, false_table, offset, +1
        )
        iqft_inplace(qc, acc)

        phase_mark_valid_low_score(qc, regs["false"], acc[-1])

        qft_inplace(qc, acc)
        apply_score_and_offset_phases(
            qc, regs, acc, event_table, bias_table, false_table, offset, -1
        )
        iqft_inplace(qc, acc)

        diffuser(qc, params)

    meta = {
        "parameter_bits": param_bits,
        "accumulator_bits_source_spec": int(spec["fixed_point"]["accumulator_bits_unsigned"]),
        "accumulator_bits_comparison_safe": nacc,
        "logical_width": total,
        "offset": offset,
        "event_conditioned_constants": len(event_table),
        "bias_conditioned_constants": len(bias_table),
        "false_conditioned_constants": len(false_table),
    }
    return qc, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--grover-rounds", type=int, default=1)
    ap.add_argument("--probe-optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if args.grover_rounds < 1:
        raise SystemExit("--grover-rounds must be >= 1")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if not spec.get("verification", {}).get("integer_threshold_reproduces_marked_set_exactly"):
        raise RuntimeError("source fusion arithmetic specification is not classification-exact")

    enc = factorized_encoding(spec)
    qc, circuit_meta = build_circuit(spec, enc, args.grover_rounds)
    logical = qc.num_qubits

    print("===== TCT REVERSIBLE ARITHMETIC ORACLE =====")
    print(
        f"valid={spec['valid_candidate_count']} marked={spec['marked_count']} "
        f"factorized_scale={enc['scale']} threshold={enc['threshold_int']} "
        f"classification_exact={enc['classification_exact']}"
    )
    print(
        f"parameter_bits={circuit_meta['parameter_bits']} "
        f"source_accumulator_bits={circuit_meta['accumulator_bits_source_spec']} "
        f"comparison_safe_accumulator_bits={circuit_meta['accumulator_bits_comparison_safe']} "
        f"logical_width={logical} rounds={args.grover_rounds}"
    )
    print(
        f"conditioned_constants event={circuit_meta['event_conditioned_constants']} "
        f"bias={circuit_meta['bias_conditioned_constants']} "
        f"false={circuit_meta['false_conditioned_constants']}"
    )

    # First benchmark only the logical/HLS burden on an exact-width fully
    # connected synthetic backend.  This deliberately avoids IBM service access
    # and routing so we can measure reversible-oracle overhead before spending
    # time on physical-patch searches.
    backend = topo.generic(logical, mapper.full_coupling(logical))
    compiled, elapsed = mapper.compile_circuit(
        qc,
        backend,
        args.profile,
        args.probe_optimization_level,
        args.seed_transpiler,
        list(range(logical)),
    )
    pair_weights, interaction_meta = mapper.extract_two_qubit_interactions(compiled)
    stats = mapper.compiled_stats(qc, compiled, elapsed)

    print("\n===== REVERSIBLE ORACLE PROBE =====")
    print(
        f"logical_width={logical} weighted_edges={interaction_meta['weighted_edges']} "
        f"total_2q_weight={interaction_meta['total_2q_weight']} "
        f"CZ={stats['native_cz']} depth={stats['compiled_depth']} "
        f"size={stats['compiled_size']} compile_seconds={stats['compile_seconds']:.3f}"
    )

    result = {
        "experiment": "tct_reversible_arithmetic_oracle_probe_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "source_spec_experiment": spec.get("experiment"),
        "factorized_encoding": {k: v for k, v in enc.items() if k != "rows"},
        "circuit": circuit_meta,
        "grover_rounds": args.grover_rounds,
        "interaction_probe": {**interaction_meta, **stats},
        "pair_weights": [
            {"i": int(i), "j": int(j), "weight": int(w)}
            for (i, j), w in sorted(pair_weights.items())
        ],
        "claim_boundary": (
            "Zero-QPU compiler probe of a coherent factorized fixed-point arithmetic "
            "oracle for the reduced-order FAIR-MAST-seeded TCT objective. It does not "
            "establish end-to-end quantum advantage, fault-tolerant feasibility, or "
            "fusion-physics validity. The oracle still uses classically frozen model "
            "constants and a classically chosen low-loss threshold."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
