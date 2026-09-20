#!/usr/bin/env python3
"""Compile the validated grid-factored TCT arithmetic oracle for multiple Grover rounds.

This zero-QPU harness requires the passing validation artifact produced by
validate_tct_grid_factored_shift_oracle.py, rebuilds the transformed arithmetic
encoding and structured event implementation, and compiles a single coherent
multi-round Grover circuit. The initial parameter-register superposition is
prepared once, not once per repeated round.

The default is six Grover rounds, matching the idealized query count for the
frozen 320-valid-state / 8-marked-state search problem.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import benchmark_tct_reversible_arithmetic_oracle as arith
import benchmark_tct_event_polynomial_oracle as poly
import benchmark_tct_grid_factored_shift_oracle as grid

REV = "2026-09-19-tct-grid-factored-shift-6round-v1"
DEFAULT_VALIDATION = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_oracle_validation.json"
DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_grid_factored_shift_oracle_6round.json"


def build_multi_round(
    spec: dict,
    enc: dict,
    coeff: list[int],
    bias_table,
    false_table,
    rounds: int,
) -> QuantumCircuit:
    regs, params, acc, total = grid.register_layout(spec, enc)
    qc = QuantumCircuit(total, name=f"tct_grid_factored_shift_grover_{rounds}round")
    modulus = 1 << len(acc)
    offset = modulus - (int(enc["threshold_int"]) + 1)

    qc.h(params)

    for _ in range(rounds):
        # Event term: exact four-bit bias/boost base polynomial followed by the
        # reversible power-of-two event-rate shift.
        arith.qft_inplace(qc, acc)
        grid.apply_base_polynomial(qc, acc, regs, coeff, +1)
        arith.iqft_inplace(qc, acc)
        grid.apply_event_shift_forward(qc, acc, regs["event"])

        # Add bias/false terms and modular comparator offset.
        arith.qft_inplace(qc, acc)
        grid.apply_additives(qc, regs, acc, bias_table, false_table, offset, +1)
        arith.iqft_inplace(qc, acc)

        arith.phase_mark_valid_low_score(qc, regs["false"], acc[-1])

        # Exact uncomputation.
        arith.qft_inplace(qc, acc)
        grid.apply_additives(qc, regs, acc, bias_table, false_table, offset, -1)
        arith.iqft_inplace(qc, acc)
        grid.apply_event_shift_inverse(qc, acc, regs["event"])
        arith.qft_inplace(qc, acc)
        grid.apply_base_polynomial(qc, acc, regs, coeff, -1)
        arith.iqft_inplace(qc, acc)

        arith.diffuser(qc, params)

    return qc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    ap.add_argument("--grover-rounds", type=int, default=6)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.grover_rounds < 1:
        raise SystemExit("grover rounds must be >= 1")

    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    if not validation.get("all_passed"):
        raise RuntimeError("validation artifact is missing all_passed=True")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    factors = grid.derive_grid_factors(spec)
    enc = grid.transformed_encoding(spec, factors)
    if not enc.get("classification_exact"):
        raise RuntimeError("grid-factored transformed encoding is not classification-exact")

    contract = grid.verify_classical_circuit_contract(spec, factors, enc)
    base_values = grid.base_event_truth_table(spec, factors, enc)
    coeff = poly.mobius_coefficients(base_values)
    poly.verify_polynomial(base_values, coeff)
    bias_table, false_table = grid.transformed_additive_tables(spec, factors, enc)

    qc = build_multi_round(
        spec,
        enc,
        coeff,
        bias_table,
        false_table,
        args.grover_rounds,
    )
    stats = grid.compile_probe(qc, args.optimization_level, args.seed_transpiler, args.profile)

    one_round_cz = 7126
    one_round_depth = 22081
    naive_cz = one_round_cz * args.grover_rounds
    naive_depth = one_round_depth * args.grover_rounds

    print("===== TCT GRID-FACTORED SHIFT MULTI-ROUND =====")
    print(
        f"validation_all_passed=True classification_exact=True "
        f"grover_rounds={args.grover_rounds} logical_width={qc.num_qubits} "
        f"accumulator_bits={contract['nacc']}"
    )
    print(
        f"compiled: CZ={stats['native_cz']} depth={stats['compiled_depth']} "
        f"size={stats['compiled_size']} weighted_edges={stats['weighted_edge_count']}"
    )
    print(
        f"naive_linear_from_one_round: CZ={naive_cz} depth={naive_depth} "
        f"CZ_ratio={stats['native_cz']/naive_cz:.6f} "
        f"depth_ratio={stats['compiled_depth']/naive_depth:.6f}"
    )

    payload = {
        "experiment": "tct_grid_factored_shift_multi_round_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "validation_artifact": str(args.validation),
        "validation_all_passed": True,
        "classification_exact": True,
        "grover_rounds": args.grover_rounds,
        "logical_width": qc.num_qubits,
        "accumulator_bits": int(contract["nacc"]),
        "base_event_nonzero_monomials": sum(1 for c in coeff if c),
        "compiled": stats,
        "one_round_reference": {"native_cz": one_round_cz, "compiled_depth": one_round_depth},
        "naive_linear_reference": {"native_cz": naive_cz, "compiled_depth": naive_depth},
        "claim_boundary": (
            "Validated classification-exact transformed arithmetic over the frozen reduced-order TCT search. "
            "This is a zero-QPU compiler result, not fusion-physics validation or an end-to-end quantum-speedup claim."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
