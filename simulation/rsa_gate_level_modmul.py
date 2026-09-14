#!/usr/bin/env python3
"""
Exact gate-synthesis resource benchmark for toy RSA modular multiplication.

This is the next layer after the functional/statevector Shor tests.  For each
self-generated toy semiprime N and coprime base a, it constructs every
controlled modular-multiplication power used by QPE,

    |c>|y> -> |c>|y>                         if c = 0
               |c>|a^(2^k) y mod N>          if c = 1 and y < N,

with basis states y >= N left unchanged.

The work-register permutation is decomposed exactly:
    permutation cycles
      -> arbitrary basis-state transpositions
      -> Gray-path adjacent basis-state swaps
      -> one MCX per adjacent swap
      -> Toffoli chain using clean ancillas.

The permutation decomposition is validated exhaustively over every work basis
state.  The MCX-to-Toffoli construction is independently truth-table validated.

This is an exact but deliberately generic synthesis.  It is NOT an optimized
modular-adder/multiplier construction and its gate counts should be interpreted
as a reproducible upper-bound-style reference, not as state-of-the-art Shor
resource estimates.

Scope: self-generated toy semiprimes only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from dataclasses import dataclass, asdict
from pathlib import Path

from rsa_shor_end_to_end import generate_toy_rsa


@dataclass
class PowerResource:
    bit_index: int
    multiplier: int
    identity: bool
    cycles: int
    transpositions: int
    adjacent_basis_swaps: int
    mcx_count: int
    mask_x_count: int
    toffoli_count: int
    cnot_equiv_6_per_toffoli: int
    t_count_7_per_toffoli: int
    permutation_validated: bool


def modular_permutation(n: int, multiplier: int, work_bits: int) -> list[int]:
    width = 1 << work_bits
    perm = list(range(width))
    for y in range(n):
        perm[y] = (multiplier * y) % n
    if len(set(perm)) != width:
        raise RuntimeError("modular map is not a permutation")
    return perm


def permutation_cycles(perm: list[int]) -> list[list[int]]:
    seen = [False] * len(perm)
    out: list[list[int]] = []
    for start in range(len(perm)):
        if seen[start]:
            continue
        cycle = []
        x = start
        while not seen[x]:
            seen[x] = True
            cycle.append(x)
            x = perm[x]
        if len(cycle) > 1:
            out.append(cycle)
    return out


def gray_path(x: int, y: int, work_bits: int) -> list[int]:
    """Deterministic Hamming-one path from x to y."""
    path = [x]
    current = x
    diff = x ^ y
    for bit in range(work_bits):
        if (diff >> bit) & 1:
            current ^= 1 << bit
            path.append(current)
    if current != y:
        raise AssertionError("Gray path construction failed")
    return path


def adjacent_swaps_for_transposition(
    x: int, y: int, work_bits: int
) -> list[tuple[int, int]]:
    """
    Implement basis transposition (x y) with Hamming-one swaps.

    For path p0..pd, use:
      (p0 p1)(p1 p2)...(p[d-1] pd)
      (p[d-2] p[d-1])...(p0 p1)
    so intermediate basis states are restored.
    """
    path = gray_path(x, y, work_bits)
    forward = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    return forward + list(reversed(forward[:-1]))


def synthesize_permutation(
    perm: list[int], work_bits: int
) -> tuple[list[tuple[int, int]], int, int]:
    cycles = permutation_cycles(perm)
    swaps: list[tuple[int, int]] = []
    transpositions = 0
    for cycle in cycles:
        pivot = cycle[0]
        # Applied left-to-right, (p,c1),(p,c2),... realizes the cycle.
        for other in cycle[1:]:
            transpositions += 1
            swaps.extend(
                adjacent_swaps_for_transposition(pivot, other, work_bits)
            )
    return swaps, len(cycles), transpositions


def validate_swap_network(
    perm: list[int], swaps: list[tuple[int, int]]
) -> bool:
    """O(number of swaps + basis states) exact permutation validation."""
    current = list(range(len(perm)))
    location = list(range(len(perm)))
    for u, v in swaps:
        i, j = location[u], location[v]
        current[i], current[j] = current[j], current[i]
        location[u], location[v] = j, i
    return current == perm


def mcx_toffoli_cost(control_count: int) -> tuple[int, int]:
    """
    Clean-ancilla linear MCX construction.

    For k >= 2 controls:
      clean ancillas = k - 2
      Toffolis      = 2k - 3
    """
    if control_count < 0:
        raise ValueError("negative control count")
    if control_count == 0:
        return 0, 0
    if control_count == 1:
        return 0, 0  # one CNOT, not used by this benchmark
    return control_count - 2, 2 * control_count - 3


def _apply_toffoli(bits: list[int], a: int, b: int, target: int) -> None:
    if bits[a] and bits[b]:
        bits[target] ^= 1


def simulate_clean_ancilla_mcx(
    controls: list[int], target_value: int
) -> tuple[int, list[int]]:
    """Classical truth-table simulation of the Toffoli-chain MCX."""
    k = len(controls)
    if k == 0:
        return target_value ^ 1, []
    if k == 1:
        return target_value ^ controls[0], []
    if k == 2:
        return target_value ^ (controls[0] & controls[1]), []

    # controls | target | k-2 ancillas
    target_idx = k
    anc_start = k + 1
    bits = controls[:] + [target_value] + [0] * (k - 2)

    # compute
    _apply_toffoli(bits, 0, 1, anc_start)
    for i in range(2, k - 1):
        _apply_toffoli(bits, anc_start + i - 2, i, anc_start + i - 1)

    # target
    _apply_toffoli(bits, anc_start + k - 3, k - 1, target_idx)

    # uncompute
    for i in range(k - 2, 1, -1):
        _apply_toffoli(bits, anc_start + i - 2, i, anc_start + i - 1)
    _apply_toffoli(bits, 0, 1, anc_start)

    return bits[target_idx], bits[anc_start:]


def validate_mcx_chain(control_count: int) -> bool:
    for pattern in range(1 << control_count):
        controls = [(pattern >> i) & 1 for i in range(control_count)]
        expected_flip = int(all(controls))
        for target in (0, 1):
            got, ancillas = simulate_clean_ancilla_mcx(controls, target)
            if got != (target ^ expected_flip):
                return False
            if any(ancillas):
                return False
    return True


def adjacent_swap_mask_x_count(u: int, v: int, work_bits: int) -> int:
    diff = u ^ v
    if diff == 0 or diff & (diff - 1):
        raise ValueError("adjacent basis swap must differ in exactly one bit")
    target_bit = diff.bit_length() - 1
    zeros = 0
    for bit in range(work_bits):
        if bit == target_bit:
            continue
        if ((u >> bit) & 1) == 0:
            zeros += 1
    # Negative controls: X before and after the MCX.
    return 2 * zeros


def synthesize_controlled_power(
    n: int, multiplier: int, work_bits: int, bit_index: int
) -> PowerResource:
    if multiplier == 1:
        return PowerResource(
            bit_index, multiplier, True, 0, 0, 0, 0, 0, 0, 0, 0, True
        )

    perm = modular_permutation(n, multiplier, work_bits)
    swaps, cycle_count, transpositions = synthesize_permutation(
        perm, work_bits
    )
    valid = validate_swap_network(perm, swaps)

    # One external phase control + (work_bits-1) pattern controls.
    mcx_controls = work_bits
    _, toffoli_per_mcx = mcx_toffoli_cost(mcx_controls)
    mask_x = sum(
        adjacent_swap_mask_x_count(u, v, work_bits) for u, v in swaps
    )
    toffoli = len(swaps) * toffoli_per_mcx

    return PowerResource(
        bit_index=bit_index,
        multiplier=multiplier,
        identity=False,
        cycles=cycle_count,
        transpositions=transpositions,
        adjacent_basis_swaps=len(swaps),
        mcx_count=len(swaps),
        mask_x_count=mask_x,
        toffoli_count=toffoli,
        cnot_equiv_6_per_toffoli=6 * toffoli,
        t_count_7_per_toffoli=7 * toffoli,
        permutation_validated=valid,
    )


def choose_coprime_base(n: int, rng: random.Random) -> int:
    for _ in range(10000):
        a = rng.randrange(2, n - 1)
        if math.gcd(a, n) == 1:
            return a
    raise RuntimeError("could not choose coprime base")


def run_case(bits: int, trial: int, seed: int) -> tuple[dict, list[dict]]:
    rng = random.Random((seed << 20) ^ (bits << 12) ^ trial)
    key = generate_toy_rsa(bits, rng)
    n = key.n
    work_bits = n.bit_length()
    phase_bits = 2 * work_bits
    a = choose_coprime_base(n, rng)

    if not validate_mcx_chain(work_bits):
        raise RuntimeError(f"MCX chain failed for {work_bits} controls")

    powers: list[PowerResource] = []
    for k in range(phase_bits):
        multiplier = pow(a, 1 << k, n)
        powers.append(
            synthesize_controlled_power(n, multiplier, work_bits, k)
        )

    if not all(p.permutation_validated for p in powers):
        raise RuntimeError("a synthesized modular permutation failed validation")

    arithmetic_ancillas, _ = mcx_toffoli_cost(work_bits)
    wide_total = work_bits + phase_bits + arithmetic_ancillas
    recycled_total = work_bits + 1 + arithmetic_ancillas

    row = {
        "bits": bits,
        "trial": trial,
        "n": n,
        "truth_p": key.p,
        "truth_q": key.q,
        "base_a": a,
        "work_qubits": work_bits,
        "phase_bits": phase_bits,
        "nominal_controlled_modmul_powers": phase_bits,
        "active_nonidentity_powers": sum(not p.identity for p in powers),
        "arithmetic_clean_ancillas": arithmetic_ancillas,
        "wide_total_qubits_incl_arith_ancilla": wide_total,
        "recycled_total_qubits_incl_arith_ancilla": recycled_total,
        "total_width_reduction": wide_total / recycled_total,
        "total_cycles": sum(p.cycles for p in powers),
        "total_basis_transpositions": sum(p.transpositions for p in powers),
        "total_adjacent_basis_swaps": sum(p.adjacent_basis_swaps for p in powers),
        "total_mcx": sum(p.mcx_count for p in powers),
        "total_mask_x": sum(p.mask_x_count for p in powers),
        "total_toffoli": sum(p.toffoli_count for p in powers),
        "total_cnot_equiv_6_per_toffoli": sum(
            p.cnot_equiv_6_per_toffoli for p in powers
        ),
        "total_t_count_7_per_toffoli": sum(
            p.t_count_7_per_toffoli for p in powers
        ),
        "wide_iqft_two_qubit_rotations": phase_bits * (phase_bits - 1) // 2,
        "recycled_feedback_conditional_rotations": phase_bits
        * (phase_bits - 1)
        // 2,
        "recycled_midcircuit_measurements": phase_bits,
        "recycled_resets": phase_bits,
        "mcx_truth_table_validated": True,
        "all_modmul_permutations_validated": True,
    }

    power_rows = []
    for p in powers:
        pr = {
            "bits": bits,
            "trial": trial,
            "n": n,
            "base_a": a,
            **asdict(p),
        }
        power_rows.append(pr)
    return row, power_rows


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    for bits in sorted(set(r["bits"] for r in rows)):
        rr = [r for r in rows if r["bits"] == bits]
        out.append(
            {
                "bits": bits,
                "trials": len(rr),
                "distinct_moduli": len(set(r["n"] for r in rr)),
                "wide_total_qubits_incl_arith_ancilla": rr[0][
                    "wide_total_qubits_incl_arith_ancilla"
                ],
                "recycled_total_qubits_incl_arith_ancilla": rr[0][
                    "recycled_total_qubits_incl_arith_ancilla"
                ],
                "total_width_reduction": rr[0]["total_width_reduction"],
                "median_active_nonidentity_powers": statistics.median(
                    r["active_nonidentity_powers"] for r in rr
                ),
                "median_adjacent_basis_swaps": statistics.median(
                    r["total_adjacent_basis_swaps"] for r in rr
                ),
                "median_toffoli": statistics.median(
                    r["total_toffoli"] for r in rr
                ),
                "min_toffoli": min(r["total_toffoli"] for r in rr),
                "max_toffoli": max(r["total_toffoli"] for r in rr),
                "median_cnot_equiv": statistics.median(
                    r["total_cnot_equiv_6_per_toffoli"] for r in rr
                ),
                "median_t_count": statistics.median(
                    r["total_t_count_7_per_toffoli"] for r in rr
                ),
                "all_validated": all(
                    r["mcx_truth_table_validated"]
                    and r["all_modmul_permutations_validated"]
                    for r in rr
                ),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bits", type=int, nargs="+", default=[6, 7, 8, 9])
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/rsa_gate_level"),
    )
    args = ap.parse_args()

    rows: list[dict] = []
    power_rows: list[dict] = []
    for bits in args.bits:
        for trial in range(args.trials):
            row, pr = run_case(bits, trial, args.seed)
            rows.append(row)
            power_rows.extend(pr)
            print(
                f"bits={bits} trial={trial} N={row['n']} a={row['base_a']} "
                f"width={row['wide_total_qubits_incl_arith_ancilla']}Q"
                f"->{row['recycled_total_qubits_incl_arith_ancilla']}Q "
                f"Toffoli={row['total_toffoli']:,} "
                f"validated={row['all_modmul_permutations_validated']}"
            )

    summary = summarize(rows)
    args.outdir.mkdir(parents=True, exist_ok=True)
    write_csv(args.outdir / "gate_level_trials.csv", rows)
    write_csv(args.outdir / "gate_level_powers.csv", power_rows)
    write_csv(args.outdir / "gate_level_summary.csv", summary)
    (args.outdir / "gate_level_results.json").write_text(
        json.dumps(
            {
                "benchmark": "exact generic gate synthesis of controlled modular multiplication",
                "seed": args.seed,
                "important_limit": (
                    "Exact permutation synthesis via Gray-path basis transpositions; "
                    "gate counts are generic and intentionally unoptimized, not "
                    "state-of-the-art modular-arithmetic estimates."
                ),
                "mcx_model": (
                    "one external phase control plus work-register pattern controls; "
                    "k-control MCX uses k-2 clean ancillas and 2k-3 Toffolis; "
                    "Toffoli-equivalent reporting also shows 6 CNOT + 7 T per Toffoli."
                ),
                "summary": summary,
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )

    print("\nSUMMARY")
    for s in summary:
        print(json.dumps(s, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
