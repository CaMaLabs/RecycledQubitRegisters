#!/usr/bin/env python3
"""Zero-QPU IBM preflight for an order-agnostic full-residue Shor modular unitary.

This path is deliberately distinct from both the affine orbit encoding and the
reversible-arithmetic experiments.

For each QPE power it constructs the complete six-bit permutation

    y -> m*y mod N   for y < N
    y -> y           for y >= N

from only N, a, and the QPE bit index.  It does not use the multiplicative
order or a precomputed orbit labeling.  The permutation is synthesized by
cycle decomposition -> basis-state transpositions -> Gray-path adjacent
basis-state swaps.  Each adjacent swap is one phase-controlled pattern MCX,
lowered explicitly with a reusable clean-ancilla Toffoli chain.

This is generic full-register reversible synthesis for small N, but it is NOT a
scalable arithmetic construction: truth-table/permutation synthesis grows
exponentially with work-register width.  Its purpose is to separate two
questions:

1. Can we remove prior knowledge of r/the orbit and still obtain a tractable
   present-day hardware circuit for N=35?
2. How much extra cost comes specifically from insisting on scalable arithmetic
   rather than generic full-register synthesis?

This file never submits a QPU job.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import QFTGate
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-full-permutation-v1"
N = 35
A = 2
WORK_BITS = (N - 1).bit_length()


def modular_permutation(multiplier: int) -> list[int]:
    width = 1 << WORK_BITS
    perm = list(range(width))
    for y in range(N):
        perm[y] = (int(multiplier) * y) % N
    if len(set(perm)) != width:
        raise AssertionError("modular map is not a permutation on the full register")
    return perm


def permutation_cycles(perm: list[int]) -> list[list[int]]:
    seen = [False] * len(perm)
    cycles: list[list[int]] = []
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
            cycles.append(cycle)
    return cycles


def gray_path(x: int, y: int) -> list[int]:
    path = [x]
    current = x
    diff = x ^ y
    for bit in range(WORK_BITS):
        if (diff >> bit) & 1:
            current ^= 1 << bit
            path.append(current)
    if current != y:
        raise AssertionError("Gray path failed")
    return path


def adjacent_swaps_for_transposition(x: int, y: int) -> list[tuple[int, int]]:
    path = gray_path(x, y)
    forward = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    return forward + list(reversed(forward[:-1]))


def synthesize_swaps(perm: list[int]) -> tuple[list[tuple[int, int]], dict]:
    cycles = permutation_cycles(perm)
    swaps: list[tuple[int, int]] = []
    transpositions = 0
    for cycle in cycles:
        pivot = cycle[0]
        for other in cycle[1:]:
            transpositions += 1
            swaps.extend(adjacent_swaps_for_transposition(pivot, other))
    meta = {
        "cycle_count": len(cycles),
        "cycle_lengths": [len(c) for c in cycles],
        "basis_transpositions": transpositions,
        "adjacent_basis_swaps": len(swaps),
    }
    return swaps, meta


def validate_swap_network(perm: list[int], swaps: list[tuple[int, int]]) -> bool:
    for x in range(len(perm)):
        y = x
        for u, v in swaps:
            if y == u:
                y = v
            elif y == v:
                y = u
        if y != perm[x]:
            return False
    return True


def append_clean_mcx(qc: QuantumCircuit, controls, target, scratch) -> None:
    controls = list(controls)
    scratch = list(scratch)
    k = len(controls)
    if k == 0:
        qc.x(target)
        return
    if k == 1:
        qc.cx(controls[0], target)
        return
    if k == 2:
        qc.ccx(controls[0], controls[1], target)
        return
    need = k - 2
    if len(scratch) < need:
        raise ValueError(f"need {need} clean MCX scratch qubits, got {len(scratch)}")

    qc.ccx(controls[0], controls[1], scratch[0])
    for i in range(2, k - 1):
        qc.ccx(scratch[i - 2], controls[i], scratch[i - 1])
    qc.ccx(scratch[k - 3], controls[k - 1], target)
    for i in range(k - 2, 1, -1):
        qc.ccx(scratch[i - 2], controls[i], scratch[i - 1])
    qc.ccx(controls[0], controls[1], scratch[0])


def append_adjacent_swap(qc: QuantumCircuit, phase_control, work, scratch, u: int, v: int) -> None:
    diff = u ^ v
    if diff == 0 or (diff & (diff - 1)):
        raise ValueError("adjacent basis states must differ in exactly one bit")
    target_bit = diff.bit_length() - 1

    pattern_controls = []
    masked = []
    for bit, q in enumerate(work):
        if bit == target_bit:
            continue
        pattern_controls.append(q)
        if ((u >> bit) & 1) == 0:
            qc.x(q)
            masked.append(q)

    append_clean_mcx(
        qc,
        [phase_control] + pattern_controls,
        work[target_bit],
        scratch,
    )

    for q in reversed(masked):
        qc.x(q)


def append_controlled_modular_permutation(
    qc: QuantumCircuit,
    phase_control,
    work,
    scratch,
    multiplier: int,
) -> dict:
    perm = modular_permutation(multiplier)
    swaps, meta = synthesize_swaps(perm)
    if not validate_swap_network(perm, swaps):
        raise AssertionError(f"swap synthesis failed for multiplier={multiplier}")
    for u, v in swaps:
        append_adjacent_swap(qc, phase_control, list(work), list(scratch), u, v)
    controls_per_swap = WORK_BITS  # phase control + WORK_BITS-1 pattern controls
    meta = {
        **meta,
        "multiplier": int(multiplier),
        "full_register_validation": True,
        "mcx_controls_per_adjacent_swap": controls_per_swap,
        "clean_scratch_required": max(0, controls_per_swap - 2),
        "ccx_per_adjacent_swap": 2 * controls_per_swap - 3,
        "abstract_ccx_from_clean_mcx": len(swaps) * (2 * controls_per_swap - 3),
    }
    return meta


def initialize_work_one(qc: QuantumCircuit, work) -> None:
    qc.x(list(work)[0])


def make_registers(phase_width: int):
    phase_q = QuantumRegister(phase_width, "phase_q")
    work = QuantumRegister(WORK_BITS, "work")
    scratch = AncillaRegister(max(0, WORK_BITS - 2), "mcx_scratch")
    return phase_q, work, scratch


def build_recycled(phase_bits: int, use_measure2: bool) -> tuple[QuantumCircuit, list[dict]]:
    phase_q, work, scratch = make_registers(1)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work, scratch, phase, name=f"shor35_generic_perm_recycled_{phase_bits}b")
    anc = phase_q[0]
    initialize_work_one(qc, work)
    rounds = []

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        multiplier = pow(A, 1 << k, N)
        meta = append_controlled_modular_permutation(qc, anc, work, scratch, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)
        qc.h(anc)
        ref.ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)
    return qc, rounds


def build_wide(phase_bits: int) -> tuple[QuantumCircuit, list[dict]]:
    phase_q, work, scratch = make_registers(phase_bits)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work, scratch, phase, name=f"shor35_generic_perm_wide_{phase_bits}b")
    initialize_work_one(qc, work)
    rounds = []
    for k in range(phase_bits):
        qc.h(phase_q[k])
        multiplier = pow(A, 1 << k, N)
        meta = append_controlled_modular_permutation(qc, phase_q[k], work, scratch, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc, rounds


def semantic_report(phase_bits: int) -> dict:
    rounds = []
    for k in range(phase_bits):
        multiplier = pow(A, 1 << k, N)
        perm = modular_permutation(multiplier)
        swaps, meta = synthesize_swaps(perm)
        ok = validate_swap_network(perm, swaps)
        if not ok:
            raise AssertionError(f"semantic validation failed for bit {k}")
        rounds.append({"qpe_bit": k, "multiplier": multiplier, **meta, "pass": True})
    scratch = max(0, WORK_BITS - 2)
    arithmetic = WORK_BITS + scratch
    return {
        "pass": True,
        "N": N,
        "a": A,
        "work_bits": WORK_BITS,
        "phase_bits": phase_bits,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "construction": "full_residue_permutation_from_N_a",
        "invalid_basis_states": "identity",
        "mcx_clean_scratch": scratch,
        "recycled_logical_qubits": arithmetic + 1,
        "wide_logical_qubits": arithmetic + phase_bits,
        "rounds": rounds,
        "scope_note": "Generic full-register reversible synthesis for small N; not scalable arithmetic.",
    }


def compile_stats(original: QuantumCircuit, compiled: QuantumCircuit, seconds: float) -> dict:
    ops = {str(k): int(v) for k, v in compiled.count_ops().items()}
    return {
        "logical_qubits": original.num_qubits,
        "high_level_depth": original.depth(),
        "high_level_size": original.size(),
        "abstract_ops": {str(k): int(v) for k, v in original.count_ops().items()},
        "compiled_qubits": compiled.num_qubits,
        "compiled_depth": compiled.depth(),
        "compiled_size": compiled.size(),
        "cz": int(ops.get("cz", 0)),
        "measure": int(ops.get("measure", 0)),
        "measure_2": int(ops.get("measure_2", 0)),
        "reset": int(ops.get("reset", 0)),
        "if_else": int(ops.get("if_else", 0)),
        "compiled_ops": ops,
        "compile_seconds": seconds,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-QPU full-residue permutation Shor preflight.")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=1)
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="both")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor35_generic_permutation"))
    args = ap.parse_args()

    if args.phase_bits < 1:
        raise SystemExit("--phase-bits must be >= 1")

    semantic = semantic_report(args.phase_bits)
    print("Full-residue permutation self-test: PASS")
    print(json.dumps(semantic, indent=2))

    service = ref.ibm_base.make_service()
    required = semantic["wide_logical_qubits"] if args.kind in ("wide", "both") else semantic["recycled_logical_qubits"]
    backend = ref.ibm_base.select_backend(service, required, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)
    print(f"backend={backend.name} measure_2={use_measure2}")

    circuits = []
    if args.kind in ("recycled", "both"):
        qc, rounds = build_recycled(args.phase_bits, use_measure2)
        circuits.append(("recycled", qc, rounds))
    if args.kind in ("wide", "both"):
        qc, rounds = build_wide(args.phase_bits)
        circuits.append(("wide", qc, rounds))

    compiled_rows = {}
    for kind, qc, rounds in circuits:
        print(f"\n=== {kind} abstract ===")
        print(json.dumps({
            "logical_qubits": qc.num_qubits,
            "depth": qc.depth(),
            "size": qc.size(),
            "ops": {str(k): int(v) for k, v in qc.count_ops().items()},
            "rounds": rounds,
        }, indent=2))
        pm = generate_preset_pass_manager(
            backend=backend,
            optimization_level=args.optimization_level,
            seed_transpiler=args.seed_transpiler,
        )
        t0 = time.perf_counter()
        compiled = pm.run(qc)
        elapsed = time.perf_counter() - t0
        row = compile_stats(qc, compiled, elapsed)
        compiled_rows[kind] = row
        print(f"=== {kind} compiled ===")
        print(json.dumps(row, indent=2, default=str))

    comparison = None
    if "recycled" in compiled_rows and "wide" in compiled_rows:
        r = compiled_rows["recycled"]
        w = compiled_rows["wide"]
        comparison = {
            "logical_qubits_saved": w["logical_qubits"] - r["logical_qubits"],
            "cz_difference_recycled_minus_wide": r["cz"] - w["cz"],
            "depth_difference_recycled_minus_wide": r["compiled_depth"] - w["compiled_depth"],
            "note": "At one phase bit arithmetic/permutation cost should be equal; larger widths test phase-register recycling only after this synthesis passes the absolute-cost gate.",
        }
        print("\n=== comparison ===")
        print(json.dumps(comparison, indent=2))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "phase_bits": args.phase_bits,
        "optimization_level": args.optimization_level,
        "seed_transpiler": args.seed_transpiler,
        "qpu_submitted": False,
        "semantic": semantic,
        "compiled_stats": compiled_rows,
        "comparison": comparison,
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"generic_full_permutation_{args.phase_bits}b_{backend.name}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
