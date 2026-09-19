#!/usr/bin/env python3
"""Measure where the TCT reversible arithmetic oracle spends its compiler cost.

This is a zero-QPU diagnostic for benchmark_tct_reversible_arithmetic_oracle.py.
It recompiles isolated logical blocks on an exact-width fully connected synthetic
backend so the dominant arithmetic component can be identified before changing
the oracle architecture.

The audit is intentionally a compiler-cost decomposition, not a replacement
oracle and not a quantum-advantage result.
"""
from __future__ import annotations

import argparse
import json
import sys
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

DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_arithmetic_oracle_cost_breakdown.json"
REV = "2026-09-19-tct-arithmetic-cost-breakdown-v1"


def registers(spec: dict, enc: dict):
    widths = spec["parameter_register_bits"]
    bias_bits = int(widths["standing_bias"])
    boost_bits = int(widths["boost_reduction"])
    false_bits = int(widths["false_trigger_cost_multiplier"])
    event_bits = int(widths["event_rate_multiplier"])
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


def compile_stats(qc: QuantumCircuit, level: int, seed: int, profile: str) -> dict:
    backend = topo.generic(qc.num_qubits, mapper.full_coupling(qc.num_qubits))
    compiled, elapsed = mapper.compile_circuit(
        qc, backend, profile, level, seed, list(range(qc.num_qubits))
    )
    pair_weights, meta = mapper.extract_two_qubit_interactions(compiled)
    stats = mapper.compiled_stats(qc, compiled, elapsed)
    return {
        "weighted_edges": int(meta["weighted_edge_count"]),
        "total_2q_weight": float(meta["total_two_qubit_weight"]),
        "pair_weights": [
            {"i": int(i), "j": int(j), "weight": float(w)}
            for (i, j), w in sorted(pair_weights.items())
        ],
        **stats,
    }


def qft_wrapped_component(
    total: int,
    regs: dict[str, list[int]],
    acc: list[int],
    event_table,
    bias_table,
    false_table,
    offset: int,
    include_event: bool,
    include_bias: bool,
    include_false: bool,
    include_offset: bool,
) -> QuantumCircuit:
    qc = QuantumCircuit(total)
    arith.qft_inplace(qc, acc)
    arith.apply_score_and_offset_phases(
        qc,
        regs,
        acc,
        event_table if include_event else [],
        bias_table if include_bias else [],
        false_table if include_false else [],
        offset if include_offset else 0,
        +1,
    )
    arith.iqft_inplace(qc, acc)
    return qc


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
    regs, params, acc, total = registers(spec, enc)
    event_table, bias_table, false_table = arith.contribution_tables(spec, enc)
    modulus = 1 << len(acc)
    offset = modulus - (int(enc["threshold_int"]) + 1)

    components: dict[str, QuantumCircuit] = {}

    # QFT transform cost with no arithmetic contribution.
    qft_pair = QuantumCircuit(total)
    arith.qft_inplace(qft_pair, acc)
    arith.iqft_inplace(qft_pair, acc)
    components["qft_plus_iqft_only"] = qft_pair

    components["offset_forward"] = qft_wrapped_component(
        total, regs, acc, event_table, bias_table, false_table, offset,
        False, False, False, True,
    )
    components["event_forward"] = qft_wrapped_component(
        total, regs, acc, event_table, bias_table, false_table, offset,
        True, False, False, False,
    )
    components["bias_forward"] = qft_wrapped_component(
        total, regs, acc, event_table, bias_table, false_table, offset,
        False, True, False, False,
    )
    components["false_forward"] = qft_wrapped_component(
        total, regs, acc, event_table, bias_table, false_table, offset,
        False, False, True, False,
    )
    components["score_forward_all"] = qft_wrapped_component(
        total, regs, acc, event_table, bias_table, false_table, offset,
        True, True, True, True,
    )

    mark = QuantumCircuit(total)
    arith.phase_mark_valid_low_score(mark, regs["false"], acc[-1])
    components["valid_low_score_phase_mark"] = mark

    diff = QuantumCircuit(total)
    arith.diffuser(diff, params)
    components["parameter_diffuser"] = diff

    full_round, meta = arith.build_circuit(spec, enc, 1)
    components["full_one_round"] = full_round

    results = {}
    print("===== TCT ARITHMETIC ORACLE COST BREAKDOWN =====")
    print(
        f"logical_width={total} parameter_bits={len(params)} accumulator_bits={len(acc)} "
        f"event_constants={len(event_table)} bias_constants={len(bias_table)} "
        f"false_constants={len(false_table)} threshold={enc['threshold_int']} offset={offset}"
    )
    for name, qc in components.items():
        row = compile_stats(qc, args.optimization_level, args.seed_transpiler, args.profile)
        results[name] = row
        print(
            f"{name}: CZ={row['native_cz']} depth={row['compiled_depth']} "
            f"size={row['compiled_size']} weighted_edges={row['weighted_edges']}"
        )

    full = results["full_one_round"]
    print("\n===== FRACTIONS OF FULL ONE-ROUND CZ =====")
    for name in (
        "qft_plus_iqft_only", "offset_forward", "event_forward", "bias_forward",
        "false_forward", "score_forward_all", "valid_low_score_phase_mark",
        "parameter_diffuser",
    ):
        row = results[name]
        print(f"{name}: {row['native_cz']/full['native_cz']:.6f}")

    payload = {
        "experiment": "tct_arithmetic_oracle_cost_breakdown_v1",
        "script_revision": REV,
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "encoding": {
            "scale": int(enc["scale"]),
            "threshold_int": int(enc["threshold_int"]),
            "maximum_score_int": int(enc["maximum_score_int"]),
            "parameter_bits": len(params),
            "accumulator_bits": len(acc),
            "logical_width": total,
            "offset": offset,
            "event_conditioned_constants": len(event_table),
            "bias_conditioned_constants": len(bias_table),
            "false_conditioned_constants": len(false_table),
        },
        "components": results,
        "claim_boundary": (
            "Fully connected compiler-cost decomposition of the current coherent arithmetic "
            "oracle. Component costs are not additive because transpiler optimizations can "
            "cross block boundaries. This is a bottleneck diagnostic, not a speedup claim."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
