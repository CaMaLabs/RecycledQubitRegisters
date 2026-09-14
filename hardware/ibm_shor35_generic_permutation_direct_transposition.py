#!/usr/bin/env python3
"""Zero-QPU direct-transposition synthesis for the generic full-residue N=35 Shor path.

This keeps the same order/orbit-independent six-bit modular semantics used by
`ibm_shor35_generic_permutation_optimizer.py`, but replaces the expensive
Gray-path expansion of each arbitrary basis-state transposition.

Key identity
------------
For a transposition |u> <-> |v>, let d = u xor v and choose one set bit t of d.
An invertible CNOT basis change using CNOT(t -> j) for every other set bit j of d
maps u and v to two basis states that differ only in bit t.  One phase-controlled
pattern MCX then swaps those adjacent states.  Undoing the CNOT basis change
implements the original controlled transposition exactly.

Thus one arbitrary transposition uses:

    1 six-control MCX + 2*(HammingDistance(u,v)-1) CNOTs

instead of the previous Gray-path realization:

    (2*HammingDistance(u,v)-1) six-control MCXs.

The full 64-state modular permutation is still generated only from N, a, and the
QPE bit index.  The multiplicative order and the known 12-state orbit are never
supplied to circuit construction.  Every direct transposition primitive and every
complete generated permutation are exhaustively validated on computational-basis
states before compilation.

This script is compiler-only and NEVER submits a QPU job.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import MCXGate, QFTGate
from qiskit.transpiler.passes.synthesis import HLSConfig
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import ibm_shor35_generic_permutation_optimizer as opt
import ibm_shor35_generic_full_permutation_mcx_sweep as sweep
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-full-permutation-direct-transposition-v1"
N = sweep.N
A = sweep.A
WORK_BITS = sweep.WORK_BITS
SCRATCH_BITS = sweep.SCRATCH_BITS
WORK_DIM = 1 << WORK_BITS


def bit(value: int, index: int) -> int:
    return (value >> index) & 1


def apply_linear_fold(value: int, target_bit: int, diff: int) -> int:
    """Apply the CNOT(t -> j) basis fold used by the direct transposition."""
    out = int(value)
    if bit(out, target_bit):
        for j in range(WORK_BITS):
            if j != target_bit and bit(diff, j):
                out ^= 1 << j
    return out


def choose_target_bit(u: int, v: int) -> dict:
    diff = u ^ v
    if diff == 0:
        raise ValueError("transposition endpoints must be distinct")

    candidates = []
    for target in range(WORK_BITS):
        if not bit(diff, target):
            continue
        transformed_u = apply_linear_fold(u, target, diff)
        transformed_v = apply_linear_fold(v, target, diff)
        if transformed_u ^ transformed_v != (1 << target):
            raise AssertionError("basis fold did not make transposition adjacent")
        zero_masks = sum(
            1
            for j in range(WORK_BITS)
            if j != target and bit(transformed_u, j) == 0
        )
        candidates.append(
            {
                "target_bit": target,
                "transformed_u": transformed_u,
                "transformed_v": transformed_v,
                "zero_mask_count": zero_masks,
            }
        )

    # Entangling cost is identical for all valid target choices.  Prefer fewer
    # X masks, then a stable target index for deterministic synthesis.
    return min(candidates, key=lambda row: (row["zero_mask_count"], row["target_bit"]))


def apply_direct_primitive_classical(x: int, u: int, v: int, target_bit: int) -> int:
    """Classically emulate the work-register part of one direct primitive."""
    diff = u ^ v
    y = apply_linear_fold(x, target_bit, diff)
    u2 = apply_linear_fold(u, target_bit, diff)

    match = True
    for j in range(WORK_BITS):
        if j == target_bit:
            continue
        if bit(y, j) != bit(u2, j):
            match = False
            break
    if match:
        y ^= 1 << target_bit

    # The CNOT basis fold is self-inverse.
    y = apply_linear_fold(y, target_bit, diff)
    return y


def validate_direct_primitive(u: int, v: int, target_bit: int) -> bool:
    for x in range(WORK_DIM):
        got = apply_direct_primitive_classical(x, u, v, target_bit)
        expected = v if x == u else u if x == v else x
        if got != expected:
            return False
    return True


def append_direct_controlled_transposition(qc, phase_control, work, u: int, v: int) -> dict:
    work = list(work)
    diff = u ^ v
    choice = choose_target_bit(u, v)
    target = int(choice["target_bit"])
    transformed_u = int(choice["transformed_u"])

    if not validate_direct_primitive(u, v, target):
        raise AssertionError(f"direct transposition primitive failed for ({u}, {v})")

    folded_bits = [
        j for j in range(WORK_BITS) if j != target and bit(diff, j)
    ]
    for j in folded_bits:
        qc.cx(work[target], work[j])

    pattern_controls = [work[j] for j in range(WORK_BITS) if j != target]
    masked = []
    for j in range(WORK_BITS):
        if j == target:
            continue
        if bit(transformed_u, j) == 0:
            qc.x(work[j])
            masked.append(work[j])

    qc.append(MCXGate(1 + len(pattern_controls)), [phase_control] + pattern_controls + [work[target]])

    for q in reversed(masked):
        qc.x(q)
    for j in reversed(folded_bits):
        qc.cx(work[target], work[j])

    return {
        "u": int(u),
        "v": int(v),
        "hamming_distance": int(diff.bit_count()),
        "target_bit": target,
        "basis_change_cx": 2 * len(folded_bits),
        "pattern_x": 2 * len(masked),
        "mcx": 1,
    }


def cycle_transpositions_min_hamming(cycle: list[int]) -> tuple[list[tuple[int, int]], dict]:
    """Choose a star pivot minimizing direct-transposition basis-change cost."""
    candidates = []
    for pivot_index in range(len(cycle)):
        trans = opt.star_transpositions(cycle, pivot_index)
        hamming_sum = sum((u ^ v).bit_count() for u, v in trans)
        basis_change_cx = sum(2 * ((u ^ v).bit_count() - 1) for u, v in trans)
        pattern_x = 0
        choices = []
        for u, v in trans:
            choice = choose_target_bit(u, v)
            pattern_x += 2 * int(choice["zero_mask_count"])
            choices.append({"u": u, "v": v, **choice})
        candidates.append(
            {
                "pivot_index": pivot_index,
                "pivot": cycle[pivot_index],
                "transpositions": trans,
                "hamming_sum": hamming_sum,
                "basis_change_cx": basis_change_cx,
                "pattern_x": pattern_x,
                "primitive_choices": choices,
            }
        )
    best = min(
        candidates,
        key=lambda row: (row["basis_change_cx"], row["pattern_x"], row["pivot"]),
    )
    return best["transpositions"], {
        "cycle": cycle,
        "chosen_pivot": best["pivot"],
        "chosen_pivot_index": best["pivot_index"],
        "hamming_sum": best["hamming_sum"],
        "basis_change_cx": best["basis_change_cx"],
        "pattern_x": best["pattern_x"],
        "candidate_costs": [
            {
                "pivot": row["pivot"],
                "basis_change_cx": row["basis_change_cx"],
                "pattern_x": row["pattern_x"],
                "hamming_sum": row["hamming_sum"],
            }
            for row in candidates
        ],
    }


def direct_transpositions(perm: list[int]) -> tuple[list[tuple[int, int]], dict]:
    cycles = sweep.base.permutation_cycles(perm)
    all_trans = []
    cycle_rows = []
    for cycle in cycles:
        trans, row = cycle_transpositions_min_hamming(cycle)
        all_trans.extend(trans)
        cycle_rows.append(row)

    # Exact full-register semantic check of the star-transposition network.
    for x in range(len(perm)):
        if opt.apply_transpositions(x, all_trans) != perm[x]:
            raise AssertionError("direct transposition network failed full-register validation")

    # Exhaustively validate every basis-change primitive too.
    primitive_checks = []
    total_basis_cx = 0
    total_pattern_x = 0
    total_hamming = 0
    for u, v in all_trans:
        choice = choose_target_bit(u, v)
        ok = validate_direct_primitive(u, v, int(choice["target_bit"]))
        if not ok:
            raise AssertionError(f"primitive validation failed for ({u}, {v})")
        h = (u ^ v).bit_count()
        cx = 2 * (h - 1)
        px = 2 * int(choice["zero_mask_count"])
        total_basis_cx += cx
        total_pattern_x += px
        total_hamming += h
        primitive_checks.append(
            {
                "u": u,
                "v": v,
                "pass": True,
                "hamming_distance": h,
                "target_bit": int(choice["target_bit"]),
                "basis_change_cx": cx,
                "pattern_x": px,
            }
        )

    gray_swaps, _ = opt.optimized_swaps(perm)
    return all_trans, {
        "cycle_count": len(cycles),
        "cycle_lengths": [len(c) for c in cycles],
        "basis_transpositions": len(all_trans),
        "direct_mcx": len(all_trans),
        "basis_change_cx": total_basis_cx,
        "pattern_x": total_pattern_x,
        "hamming_sum": total_hamming,
        "previous_optimized_gray_mcx": len(gray_swaps),
        "mcx_reduction_vs_optimized_gray": len(gray_swaps) - len(all_trans),
        "mcx_reduction_fraction_vs_optimized_gray": (
            0.0 if not gray_swaps else (len(gray_swaps) - len(all_trans)) / len(gray_swaps)
        ),
        "cycle_choices": cycle_rows,
        "primitive_checks": primitive_checks,
        "full_register_validation": True,
    }


def append_direct_modular_permutation(qc, phase_control, work, multiplier: int) -> dict:
    perm = sweep.base.modular_permutation(multiplier)
    trans, meta = direct_transpositions(perm)
    primitive_rows = []
    for u, v in trans:
        primitive_rows.append(
            append_direct_controlled_transposition(qc, phase_control, work, u, v)
        )
    return {
        **meta,
        "multiplier": int(multiplier),
        "high_level_mcx": len(trans),
        "direct_primitive_rows": primitive_rows,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
    }


def make_registers(phase_width: int):
    phase_q = QuantumRegister(phase_width, "phase_q")
    work = QuantumRegister(WORK_BITS, "work")
    scratch = AncillaRegister(SCRATCH_BITS, "mcx_hls_scratch")
    return phase_q, work, scratch


def build_recycled(phase_bits: int, use_measure2: bool):
    phase_q, work, scratch = make_registers(1)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(
        phase_q, work, scratch, phase,
        name=f"shor35_generic_direct_recycled_{phase_bits}b",
    )
    anc = phase_q[0]
    qc.x(work[0])
    rounds = []
    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        multiplier = pow(A, 1 << k, N)
        meta = append_direct_modular_permutation(qc, anc, work, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * 3.141592653589793 / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)
        qc.h(anc)
        ref.ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)
    return qc, rounds


def build_wide(phase_bits: int):
    phase_q, work, scratch = make_registers(phase_bits)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(
        phase_q, work, scratch, phase,
        name=f"shor35_generic_direct_wide_{phase_bits}b",
    )
    qc.x(work[0])
    rounds = []
    for k in range(phase_bits):
        qc.h(phase_q[k])
        multiplier = pow(A, 1 << k, N)
        meta = append_direct_modular_permutation(qc, phase_q[k], work, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc, rounds


def hls_for_profile(profile: str):
    if profile in ("auto", "default"):
        return None if profile == "auto" else HLSConfig(mcx=["default"])
    return HLSConfig(mcx=[profile])


def compile_one(qc, backend, profile: str, level: int, seed: int) -> dict:
    kwargs = {
        "backend": backend,
        "optimization_level": level,
        "seed_transpiler": seed,
        "qubits_initially_zero": True,
    }
    hls = hls_for_profile(profile)
    if hls is not None:
        kwargs["hls_config"] = hls
    pm = generate_preset_pass_manager(**kwargs)
    t0 = time.perf_counter()
    compiled = pm.run(qc)
    elapsed = time.perf_counter() - t0
    return sweep.stats(qc, compiled, elapsed)


def semantic_summary(phase_bits: int) -> dict:
    rows = []
    for k in range(phase_bits):
        multiplier = pow(A, 1 << k, N)
        perm = sweep.base.modular_permutation(multiplier)
        _, meta = direct_transpositions(perm)
        rows.append({
            "qpe_bit": k,
            "multiplier": multiplier,
            "basis_transpositions": meta["basis_transpositions"],
            "direct_mcx": meta["direct_mcx"],
            "basis_change_cx": meta["basis_change_cx"],
            "previous_optimized_gray_mcx": meta["previous_optimized_gray_mcx"],
            "full_register_validation": meta["full_register_validation"],
        })
    return {
        "pass": all(r["full_register_validation"] for r in rows),
        "phase_bits": phase_bits,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "rows": rows,
        "total_direct_mcx": sum(r["direct_mcx"] for r in rows),
        "total_basis_change_cx": sum(r["basis_change_cx"] for r in rows),
        "total_previous_optimized_gray_mcx": sum(r["previous_optimized_gray_mcx"] for r in rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU direct-transposition optimizer for generic full-residue N=35 Shor."
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, nargs="+", default=[6, 8])
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="recycled")
    ap.add_argument(
        "--profiles",
        nargs="+",
        default=["n_clean_m15", "1_clean_kg24", "2_clean_kg24", "default"],
    )
    ap.add_argument("--optimization-levels", type=int, nargs="+", default=[2, 3])
    ap.add_argument("--seeds", type=int, nargs="+", default=[2026, 8776, 9401])
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor35_generic_permutation"),
    )
    args = ap.parse_args()

    bits_list = sorted(set(args.phase_bits))
    levels = sorted(set(args.optimization_levels))
    if not bits_list or bits_list[0] < 1:
        raise SystemExit("all phase widths must be >= 1")

    max_bits = max(bits_list)
    semantic = sweep.base.semantic_report(max_bits)
    required = semantic["wide_logical_qubits"] if args.kind in ("wide", "both") else semantic["recycled_logical_qubits"]
    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, required, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} measure_2={use_measure2}")
    print("DIRECT TRANSPOSITION PATH: NO QPU JOBS WILL BE SUBMITTED.")

    rows = []
    semantic_rows = []
    for bits in bits_list:
        sem = semantic_summary(bits)
        semantic_rows.append(sem)
        print(f"\n===== DIRECT SEMANTIC SUMMARY: {bits} PHASE BITS =====")
        print(json.dumps(sem, indent=2))
        if not sem["pass"]:
            raise SystemExit("semantic validation failed")

        circuits = []
        if args.kind in ("recycled", "both"):
            qc, rounds = build_recycled(bits, use_measure2)
            circuits.append(("recycled", qc, rounds))
        if args.kind in ("wide", "both"):
            qc, rounds = build_wide(bits)
            circuits.append(("wide", qc, rounds))

        for kind, qc, rounds in circuits:
            print(f"\n=== {bits}b {kind} abstract ===")
            print(json.dumps({
                "logical_qubits": qc.num_qubits,
                "high_level_depth": qc.depth(),
                "high_level_size": qc.size(),
                "high_level_ops": {str(k): int(v) for k, v in qc.count_ops().items()},
                "round_multipliers": [r["multiplier"] for r in rounds],
                "direct_mcx_by_round": [r["direct_mcx"] for r in rounds],
                "basis_change_cx_by_round": [r["basis_change_cx"] for r in rounds],
                "previous_optimized_gray_mcx_by_round": [r["previous_optimized_gray_mcx"] for r in rounds],
            }, indent=2))

            for profile in args.profiles:
                for level in levels:
                    for seed in args.seeds:
                        print(f"compile bits={bits} kind={kind} profile={profile} level={level} seed={seed}")
                        try:
                            stat = compile_one(qc, backend, profile, level, seed)
                            row = {
                                "phase_bits": bits,
                                "kind": kind,
                                "profile": profile,
                                "optimization_level": level,
                                "seed_transpiler": seed,
                                "success": True,
                                "order_used_in_circuit_construction": False,
                                "orbit_encoding_used": False,
                                "total_direct_mcx": sem["total_direct_mcx"],
                                "total_basis_change_cx": sem["total_basis_change_cx"],
                                "total_previous_optimized_gray_mcx": sem["total_previous_optimized_gray_mcx"],
                                **stat,
                            }
                        except Exception as exc:
                            row = {
                                "phase_bits": bits,
                                "kind": kind,
                                "profile": profile,
                                "optimization_level": level,
                                "seed_transpiler": seed,
                                "success": False,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            }
                        rows.append(row)
                        print(json.dumps(row, indent=2, default=str))

    best = {}
    for bits in bits_list:
        for kind in ("recycled", "wide"):
            candidates = [r for r in rows if r.get("success") and r["phase_bits"] == bits and r["kind"] == kind]
            if candidates:
                best[f"{bits}b_{kind}"] = min(
                    candidates,
                    key=lambda r: (r["cz"], r["compiled_depth"], r["compiled_size"]),
                )

    print("\n===== BEST DIRECT-TRANSPOSITION RESULTS =====")
    print(json.dumps(best, indent=2, default=str))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": N,
        "a": A,
        "phase_bits": bits_list,
        "kind": args.kind,
        "profiles": args.profiles,
        "optimization_levels": levels,
        "seeds": args.seeds,
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "semantic": semantic_rows,
        "rows": rows,
        "best": best,
        "scope_note": (
            "Exact full-register small-N permutation synthesis using affine basis folds around one MCX per basis-state transposition; "
            "order/orbit-independent, but still not scalable modular arithmetic."
        ),
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    path = args.outdir / "generic_full_permutation_direct_transposition.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
