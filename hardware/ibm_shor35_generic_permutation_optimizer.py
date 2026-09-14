#!/usr/bin/env python3
"""Zero-QPU optimizer for the order/orbit-independent N=35 Shor permutation path.

This stage runs only after exact ideal validation has passed.  It keeps the full
six-bit residue semantics

    y < 35  -> m*y mod 35
    y >= 35 -> y

and never supplies the multiplicative order or a compiled orbit to circuit
construction.

Two optimizations are tested here:

1. For each nontrivial cycle in the full-register modular permutation, choose
   the star-transposition pivot that minimizes the number of Gray-path adjacent
   basis swaps.  Every candidate factorization is checked against the exact
   cycle before use, and the complete swap network is revalidated against the
   generated 64-state permutation.
2. Sweep backend transpiler seeds, optimization levels, and MCX HLS profiles.

The script is compiler-only and NEVER submits a QPU job.
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

import ibm_shor35_generic_full_permutation_mcx_sweep as sweep
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-full-permutation-optimizer-v1"
N = sweep.N
A = sweep.A
WORK_BITS = sweep.WORK_BITS
SCRATCH_BITS = sweep.SCRATCH_BITS


def apply_transpositions(x: int, transpositions: list[tuple[int, int]]) -> int:
    y = x
    for u, v in transpositions:
        if y == u:
            y = v
        elif y == v:
            y = u
    return y


def star_transpositions(cycle: list[int], pivot_index: int) -> list[tuple[int, int]]:
    """Exact factorization of one directed cycle using a selected pivot."""
    rotated = cycle[pivot_index:] + cycle[:pivot_index]
    pivot = rotated[0]
    transpositions = [(pivot, other) for other in rotated[1:]]

    # Applying these in forward order must reproduce the original directed
    # cycle, independent of which cyclic rotation was chosen as the pivot.
    expected = {cycle[i]: cycle[(i + 1) % len(cycle)] for i in range(len(cycle))}
    got = {x: apply_transpositions(x, transpositions) for x in cycle}
    if got != expected:
        raise AssertionError(
            f"star factorization mismatch for pivot {pivot}: got={got}, expected={expected}"
        )
    return transpositions


def expand_transpositions(transpositions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    swaps: list[tuple[int, int]] = []
    for u, v in transpositions:
        swaps.extend(sweep.base.adjacent_swaps_for_transposition(u, v))
    return swaps


def optimized_swaps(perm: list[int]) -> tuple[list[tuple[int, int]], dict]:
    cycles = sweep.base.permutation_cycles(perm)
    all_swaps: list[tuple[int, int]] = []
    choices = []

    baseline_swaps, baseline_meta = sweep.base.synthesize_swaps(perm)

    for cycle in cycles:
        candidates = []
        for pivot_index in range(len(cycle)):
            trans = star_transpositions(cycle, pivot_index)
            swaps = expand_transpositions(trans)
            candidates.append(
                {
                    "pivot_index": pivot_index,
                    "pivot": cycle[pivot_index],
                    "adjacent_basis_swaps": len(swaps),
                    "transpositions": trans,
                    "swaps": swaps,
                }
            )
        best = min(candidates, key=lambda row: (row["adjacent_basis_swaps"], row["pivot"]))
        all_swaps.extend(best["swaps"])
        choices.append(
            {
                "cycle": cycle,
                "chosen_pivot": best["pivot"],
                "chosen_pivot_index": best["pivot_index"],
                "adjacent_basis_swaps": best["adjacent_basis_swaps"],
                "candidate_costs": [
                    {
                        "pivot": row["pivot"],
                        "adjacent_basis_swaps": row["adjacent_basis_swaps"],
                    }
                    for row in candidates
                ],
            }
        )

    if not sweep.base.validate_swap_network(perm, all_swaps):
        raise AssertionError("optimized swap network failed full-register validation")

    return all_swaps, {
        "cycle_count": len(cycles),
        "cycle_lengths": [len(c) for c in cycles],
        "basis_transpositions": sum(len(c) - 1 for c in cycles),
        "baseline_adjacent_basis_swaps": len(baseline_swaps),
        "optimized_adjacent_basis_swaps": len(all_swaps),
        "adjacent_swap_reduction": len(baseline_swaps) - len(all_swaps),
        "adjacent_swap_reduction_fraction": (
            0.0 if not baseline_swaps else (len(baseline_swaps) - len(all_swaps)) / len(baseline_swaps)
        ),
        "baseline_meta": baseline_meta,
        "cycle_choices": choices,
    }


def append_adjacent_swap_mcx(qc, phase_control, work, u: int, v: int) -> None:
    diff = u ^ v
    if diff == 0 or (diff & (diff - 1)):
        raise ValueError("adjacent basis states must differ in exactly one bit")
    target_bit = diff.bit_length() - 1

    controls = [phase_control]
    masked = []
    for bit, q in enumerate(work):
        if bit == target_bit:
            continue
        controls.append(q)
        if ((u >> bit) & 1) == 0:
            qc.x(q)
            masked.append(q)

    qc.append(MCXGate(len(controls)), controls + [work[target_bit]])

    for q in reversed(masked):
        qc.x(q)


def append_optimized_modular_permutation(qc, phase_control, work, multiplier: int) -> dict:
    perm = sweep.base.modular_permutation(multiplier)
    swaps, meta = optimized_swaps(perm)
    for u, v in swaps:
        append_adjacent_swap_mcx(qc, phase_control, list(work), u, v)
    return {
        **meta,
        "multiplier": int(multiplier),
        "full_register_validation": True,
        "mcx_controls_per_adjacent_swap": WORK_BITS,
        "idle_clean_scratch_available": SCRATCH_BITS,
        "high_level_mcx": len(swaps),
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
        phase_q,
        work,
        scratch,
        phase,
        name=f"shor35_generic_perm_opt_recycled_{phase_bits}b",
    )
    anc = phase_q[0]
    qc.x(work[0])
    rounds = []

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        multiplier = pow(A, 1 << k, N)
        meta = append_optimized_modular_permutation(qc, anc, work, multiplier)
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
        phase_q,
        work,
        scratch,
        phase,
        name=f"shor35_generic_perm_opt_wide_{phase_bits}b",
    )
    qc.x(work[0])
    rounds = []
    for k in range(phase_bits):
        qc.h(phase_q[k])
        multiplier = pow(A, 1 << k, N)
        meta = append_optimized_modular_permutation(qc, phase_q[k], work, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc, rounds


def hls_for_profile(profile: str):
    if profile == "auto":
        return None
    return HLSConfig(mcx=[profile])


def compile_one(qc, backend, level: int, seed: int, profile: str):
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
    row = sweep.stats(qc, compiled, elapsed)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU synthesis optimizer for the generic full-residue N=35 Shor path."
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, nargs="+", default=[6, 8])
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="recycled")
    ap.add_argument(
        "--profiles",
        nargs="+",
        default=["1_clean_kg24", "n_clean_m15", "auto"],
    )
    ap.add_argument("--optimization-levels", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--seeds", type=int, nargs="+", default=[8776, 9401, 2026])
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor35_generic_permutation"),
    )
    args = ap.parse_args()

    bits_list = sorted(set(args.phase_bits))
    levels = sorted(set(args.optimization_levels))
    if not bits_list or bits_list[0] < 1:
        raise SystemExit("all --phase-bits values must be >= 1")
    if any(level not in (0, 1, 2, 3) for level in levels):
        raise SystemExit("optimization levels must be in 0..3")

    max_bits = max(bits_list)
    semantic = sweep.base.semantic_report(max_bits)
    required = (
        semantic["wide_logical_qubits"]
        if args.kind in ("wide", "both")
        else semantic["recycled_logical_qubits"]
    )
    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, required, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} measure_2={use_measure2}")
    print("NO QPU JOBS WILL BE SUBMITTED.")

    rows = []
    semantic_rows = []

    for bits in bits_list:
        circuits = []
        if args.kind in ("recycled", "both"):
            qc, rounds = build_recycled(bits, use_measure2)
            circuits.append(("recycled", qc, rounds))
        if args.kind in ("wide", "both"):
            qc, rounds = build_wide(bits)
            circuits.append(("wide", qc, rounds))

        sem = {
            "phase_bits": bits,
            "order_used_in_circuit_construction": False,
            "orbit_encoding_used": False,
            "round_multipliers": [pow(A, 1 << k, N) for k in range(bits)],
            "baseline_adjacent_basis_swaps": sum(
                len(sweep.base.synthesize_swaps(sweep.base.modular_permutation(pow(A, 1 << k, N)))[0])
                for k in range(bits)
            ),
            "optimized_adjacent_basis_swaps": sum(
                len(optimized_swaps(sweep.base.modular_permutation(pow(A, 1 << k, N)))[0])
                for k in range(bits)
            ),
        }
        sem["adjacent_swap_reduction"] = (
            sem["baseline_adjacent_basis_swaps"] - sem["optimized_adjacent_basis_swaps"]
        )
        sem["adjacent_swap_reduction_fraction"] = (
            sem["adjacent_swap_reduction"] / sem["baseline_adjacent_basis_swaps"]
        )
        semantic_rows.append(sem)
        print(f"\n===== {bits} PHASE BITS =====")
        print(json.dumps(sem, indent=2))

        for kind, qc, rounds in circuits:
            print(
                json.dumps(
                    {
                        "kind": kind,
                        "logical_qubits": qc.num_qubits,
                        "high_level_depth": qc.depth(),
                        "high_level_size": qc.size(),
                        "high_level_ops": {str(k): int(v) for k, v in qc.count_ops().items()},
                        "optimized_swaps_by_round": [r["optimized_adjacent_basis_swaps"] for r in rounds],
                        "baseline_swaps_by_round": [r["baseline_adjacent_basis_swaps"] for r in rounds],
                    },
                    indent=2,
                )
            )

            for profile in args.profiles:
                for level in levels:
                    for seed in args.seeds:
                        print(
                            f"compile bits={bits} kind={kind} profile={profile} "
                            f"level={level} seed={seed}"
                        )
                        try:
                            stat = compile_one(qc, backend, level, seed, profile)
                            row = {
                                "phase_bits": bits,
                                "kind": kind,
                                "profile": profile,
                                "optimization_level": level,
                                "seed_transpiler": seed,
                                "success": True,
                                "order_used_in_circuit_construction": False,
                                "orbit_encoding_used": False,
                                "baseline_adjacent_basis_swaps": sem[
                                    "baseline_adjacent_basis_swaps"
                                ],
                                "optimized_adjacent_basis_swaps": sem[
                                    "optimized_adjacent_basis_swaps"
                                ],
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
            candidates = [
                r
                for r in rows
                if r.get("success") and r["phase_bits"] == bits and r["kind"] == kind
            ]
            if candidates:
                best[f"{bits}b_{kind}"] = min(
                    candidates, key=lambda r: (r["cz"], r["compiled_depth"], r["compiled_size"])
                )

    print("\n===== BEST RESULTS =====")
    print(json.dumps(best, indent=2, default=str))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": N,
        "a": A,
        "phase_bits": bits_list,
        "profiles": args.profiles,
        "optimization_levels": levels,
        "seeds": args.seeds,
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "semantic": semantic_rows,
        "results": rows,
        "best": best,
        "scope_note": (
            "Full-register small-N permutation synthesis; order/orbit-independent but not "
            "scalable modular arithmetic. This is a compiler-only optimization sweep."
        ),
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    path = args.outdir / "generic_full_permutation_optimizer.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
