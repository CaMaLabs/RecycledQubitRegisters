#!/usr/bin/env python3
"""Exact statevector validation for the shared-control TCT semantic oracle.

This validates the two shared-common-control implementations from
benchmark_tct_semantic_factored_oracle.py on every one of the 2^9 parameter
basis states.  For each input it checks that:

1. the phase is -1 exactly for the eight frozen marked states and +1 otherwise;
2. the clean ancilla returns to |0>;
3. there is no amplitude leakage to another basis state.

This is a zero-QPU correctness check for the fixed-instance Boolean/ESOP oracle.
It is not a scalable surrogate implementation or a quantum-advantage result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import audit_tct_boolean_oracle_compression as audit
import benchmark_tct_reversible_arithmetic_oracle as arithmetic
import benchmark_tct_semantic_factored_oracle as semantic


def oracle_only_circuit(
    n: int,
    local_cubes: list[tuple[int, ...]],
    local_bits: list[int],
    common: dict[int, int],
) -> QuantumCircuit:
    qc = QuantumCircuit(n + 1)
    params = list(range(n))
    anc = n
    semantic.compute_common(qc, params, anc, common)
    for cube in local_cubes:
        semantic.apply_local_cube_with_common_anc(
            qc, params, anc, local_bits, cube
        )
    semantic.compute_common(qc, params, anc, common)
    return qc


def validate_variant(
    name: str,
    n: int,
    marked: set[int],
    local_cubes: list[tuple[int, ...]],
    local_bits: list[int],
    common: dict[int, int],
    tol: float,
) -> dict:
    oracle = oracle_only_circuit(n, local_cubes, local_bits, common)
    total = n + 1
    dim = 1 << total
    anc_mask = 1 << n
    failures = []
    max_leakage = 0.0
    max_phase_error = 0.0

    for state in range(1 << n):
        prep = QuantumCircuit(total)
        for bit in range(n):
            if (state >> bit) & 1:
                prep.x(bit)
        prep.compose(oracle, inplace=True)
        sv = Statevector.from_instruction(prep)

        expected_index = state  # ancilla expected to return to zero
        expected_phase = -1.0 if state in marked else 1.0
        amp = complex(sv.data[expected_index])
        phase_error = abs(amp - expected_phase)
        max_phase_error = max(max_phase_error, phase_error)

        # Probability outside the original parameter state with ancilla=0.
        expected_prob = abs(amp) ** 2
        leakage = max(0.0, 1.0 - expected_prob)
        max_leakage = max(max_leakage, leakage)

        anc_one_prob = 0.0
        for idx, a in enumerate(sv.data):
            if idx & anc_mask:
                anc_one_prob += abs(complex(a)) ** 2

        if phase_error > tol or leakage > tol or anc_one_prob > tol:
            failures.append(
                {
                    "state": state,
                    "marked": state in marked,
                    "amplitude": [amp.real, amp.imag],
                    "phase_error": phase_error,
                    "leakage": leakage,
                    "ancilla_one_probability": anc_one_prob,
                }
            )

    return {
        "name": name,
        "passed": not failures,
        "tested_states": 1 << n,
        "max_phase_error": max_phase_error,
        "max_leakage": max_leakage,
        "failure_count": len(failures),
        "failures": failures[:20],
        "dimension": dim,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--tol", type=float, default=1e-9)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("results/tct_surrogate_search/tct_semantic_factored_oracle_validation.json"),
    )
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    enc = arithmetic.factorized_encoding(spec)
    widths = spec["parameter_register_bits"]
    n = int(widths["total_parameter_bits"])
    marked, _decoded = semantic.decode_marked(spec, enc)
    marked_set = set(marked)

    valid = audit.valid_cubes(n, frozenset(marked))
    disjoint_rows = audit.exact_cover(valid, marked, "cube_count")
    disjoint_full = [tuple(row["cube"]) for row in disjoint_rows]

    common = semantic.common_constraints(marked, n)
    local_bits = [bit for bit in range(n) if bit not in common]
    local_marked = {semantic.local_state(state, local_bits) for state in marked}
    esop_local = semantic.minimum_esop(local_marked, len(local_bits))
    disjoint_local = [
        semantic.strip_common_cube(cube, local_bits, common)
        for cube in disjoint_full
    ]

    results = [
        validate_variant(
            "four_cube_common_factored",
            n,
            marked_set,
            disjoint_local,
            local_bits,
            common,
            args.tol,
        ),
        validate_variant(
            "three_term_esop_common_factored",
            n,
            marked_set,
            esop_local,
            local_bits,
            common,
            args.tol,
        ),
    ]

    print("===== TCT SEMANTIC FACTORED ORACLE STATEVECTOR VALIDATION =====")
    print(f"logical_parameter_bits={n} marked_states={marked}")
    for row in results:
        print(
            f"{row['name']}: passed={row['passed']} tested={row['tested_states']} "
            f"max_phase_error={row['max_phase_error']:.3e} "
            f"max_leakage={row['max_leakage']:.3e} failures={row['failure_count']}"
        )

    payload = {
        "experiment": "tct_semantic_factored_oracle_statevector_validation_v1",
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "marked_states": marked,
        "common_constraints": {str(k): int(v) for k, v in sorted(common.items())},
        "local_bits": local_bits,
        "results": results,
        "all_passed": all(row["passed"] for row in results),
        "claim_boundary": (
            "Exact basis-state statevector validation of fixed-instance Boolean/ESOP "
            "oracle circuits only; not a scalable coherent surrogate or end-to-end "
            "quantum-advantage result."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")

    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
