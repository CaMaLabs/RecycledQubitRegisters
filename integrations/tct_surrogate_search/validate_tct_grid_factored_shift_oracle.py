#!/usr/bin/env python3
"""Zero-QPU validation for the TCT grid-factored/shift arithmetic oracle.

This independently re-derives the transformed encoding used by
benchmark_tct_grid_factored_shift_oracle.py and validates the pieces that matter
for the 25-qubit coherent arithmetic circuit without attempting an impractical
full 2^25 statevector simulation.

Checks:
1. the transformed integer scores reproduce exactly the frozen marked set over
   all 320 valid scenarios;
2. the 4-bit bias/boost Mobius polynomial reproduces every one of its 16 event
   base values exactly;
3. the comparator-offset identity is correct for every one of the 320 scores;
4. every event base has enough accumulator headroom for event-code shifts;
5. the *actual 16-bit* controlled-shift circuit maps every reachable event base
   and all four event codes to x << code and the inverse returns exactly to x.

The QFT constant-adder primitive is inherited from the arithmetic benchmark,
which already has its own statevector unit test. No IBM service or QPU is used.
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

import benchmark_tct_event_polynomial_oracle as poly
import benchmark_tct_grid_factored_shift_oracle as grid
import benchmark_tct_reversible_arithmetic_oracle as arith


def validate_full_width_shifts(
    nacc: int,
    base_values: list[int],
    tol: float,
) -> dict:
    total = nacc + 2
    acc = list(range(nacc))
    event = [nacc, nacc + 1]
    modulus = 1 << nacc
    failures: list[dict] = []
    max_probability_error = 0.0

    for x in sorted(set(int(v) for v in base_values)):
        for code in range(4):
            expected_value = x << code
            if expected_value >= modulus:
                failures.append(
                    {
                        "kind": "overflow",
                        "base": x,
                        "event_code": code,
                        "expected_value": expected_value,
                        "modulus": modulus,
                    }
                )
                continue

            qc = QuantumCircuit(total)
            for bit in range(nacc):
                if (x >> bit) & 1:
                    qc.x(acc[bit])
            for bit in range(2):
                if (code >> bit) & 1:
                    qc.x(event[bit])

            grid.apply_event_shift_forward(qc, acc, event)

            expected_index = expected_value
            expected_index |= ((code >> 0) & 1) << nacc
            expected_index |= ((code >> 1) & 1) << (nacc + 1)
            sv = Statevector.from_instruction(qc)
            p = abs(complex(sv.data[expected_index])) ** 2
            max_probability_error = max(max_probability_error, abs(1.0 - p))
            if p < 1.0 - tol:
                failures.append(
                    {
                        "kind": "forward_shift",
                        "base": x,
                        "event_code": code,
                        "probability": p,
                        "expected_value": expected_value,
                    }
                )

            qc_inv = qc.copy()
            grid.apply_event_shift_inverse(qc_inv, acc, event)
            original_index = x
            original_index |= ((code >> 0) & 1) << nacc
            original_index |= ((code >> 1) & 1) << (nacc + 1)
            sv_inv = Statevector.from_instruction(qc_inv)
            p_inv = abs(complex(sv_inv.data[original_index])) ** 2
            max_probability_error = max(max_probability_error, abs(1.0 - p_inv))
            if p_inv < 1.0 - tol:
                failures.append(
                    {
                        "kind": "inverse_shift",
                        "base": x,
                        "event_code": code,
                        "probability": p_inv,
                    }
                )

    return {
        "passed": not failures,
        "tested_base_event_pairs": len(set(base_values)) * 4,
        "accumulator_bits": nacc,
        "max_probability_error": max_probability_error,
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--tol", type=float, default=1e-9)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(
            "results/tct_surrogate_search/"
            "tct_grid_factored_shift_oracle_validation.json"
        ),
    )
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    factors = grid.derive_grid_factors(spec)
    enc = grid.transformed_encoding(spec, factors)
    contract = grid.verify_classical_circuit_contract(spec, factors, enc)

    marked_expected = {int(x) for x in spec["marked_indices"]}
    marked_observed = {
        i
        for i, row in enumerate(enc["rows"])
        if int(row["score"]) <= int(enc["threshold_int"])
    }
    classification_passed = marked_observed == marked_expected

    base_values = grid.base_event_truth_table(spec, factors, enc)
    coeff = poly.mobius_coefficients(base_values)
    polynomial_failures = []
    for assignment, expected in enumerate(base_values):
        observed = poly.evaluate_polynomial(coeff, assignment)
        if int(observed) != int(expected):
            polynomial_failures.append(
                {
                    "assignment": assignment,
                    "expected": int(expected),
                    "observed": int(observed),
                }
            )
    polynomial_passed = not polynomial_failures

    nacc = int(contract["nacc"])
    shift = validate_full_width_shifts(nacc, base_values, args.tol)

    max_shifted_base = max(base_values) << 3
    headroom_passed = max_shifted_base < (1 << nacc)

    # Re-run the generic QFT adder primitive unit test as part of this validator.
    arith.self_test_qft_constant_adder()
    qft_adder_self_test = True

    all_passed = bool(
        classification_passed
        and polynomial_passed
        and shift["passed"]
        and headroom_passed
        and enc.get("classification_exact")
    )

    payload = {
        "experiment": "tct_grid_factored_shift_oracle_validation_v1",
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "classification_exact": bool(enc.get("classification_exact")),
        "classification_passed": classification_passed,
        "expected_marked_indices": sorted(marked_expected),
        "observed_marked_indices": sorted(marked_observed),
        "base_polynomial_passed": polynomial_passed,
        "base_polynomial_failure_count": len(polynomial_failures),
        "base_polynomial_failures": polynomial_failures[:20],
        "base_event_values": [int(v) for v in base_values],
        "base_event_nonzero_monomials": sum(1 for c in coeff if c),
        "qft_adder_self_test": qft_adder_self_test,
        "classical_circuit_contract": contract,
        "max_shifted_event_base": int(max_shifted_base),
        "accumulator_modulus": 1 << nacc,
        "headroom_passed": headroom_passed,
        "full_width_shift_statevector": shift,
        "max_abs_loss_error": float(enc["max_abs_loss_error"]),
        "all_passed": all_passed,
        "claim_boundary": (
            "Componentwise validation of the specialized grid-factored reduced-order "
            "arithmetic oracle. This is not a 2^25 full-circuit statevector proof, "
            "not a scalable arbitrary-function oracle, and not evidence of end-to-end "
            "quantum advantage or fusion-physics validity."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("===== TCT GRID-FACTORED SHIFT ORACLE VALIDATION =====")
    print(
        f"classification_passed={classification_passed} tested_scores={len(enc['rows'])} "
        f"marked={len(marked_observed)}"
    )
    print(
        f"base_polynomial_passed={polynomial_passed} assignments={len(base_values)} "
        f"nonzero_monomials={sum(1 for c in coeff if c)}"
    )
    print(
        f"headroom_passed={headroom_passed} max_shifted_base={max_shifted_base} "
        f"modulus={1 << nacc}"
    )
    print(
        f"full_width_shift_passed={shift['passed']} "
        f"tested={shift['tested_base_event_pairs']} "
        f"max_probability_error={shift['max_probability_error']:.3e} "
        f"failures={shift['failure_count']}"
    )
    print(f"qft_adder_self_test={qft_adder_self_test} all_passed={all_passed}")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
