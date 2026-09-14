#!/usr/bin/env python3
"""Zero-QPU MCX synthesis sweep for the full-residue N=35 Shor permutation.

This follows `ibm_shor35_generic_full_permutation_preflight.py`, which showed
that the order-agnostic full six-bit modular permutation compiles much smaller
than the generic arithmetic paths but is still dominated by explicit Toffoli
chains.

Here the same adjacent basis-state swaps are represented as high-level MCXGate
objects. Four otherwise-idle ancillas are included so Qiskit's HLS stage can
choose ancilla-assisted MCX syntheses. We sweep several built-in MCX methods
against the same Fez target and report native CZ/depth only. No QPU job is ever
submitted.
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

import ibm_shor35_generic_full_permutation_preflight as base
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-full-permutation-mcx-hls-sweep-v1"
N = base.N
A = base.A
WORK_BITS = base.WORK_BITS
SCRATCH_BITS = max(0, WORK_BITS - 2)


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


def append_controlled_modular_permutation_mcx(qc, phase_control, work, multiplier: int) -> dict:
    perm = base.modular_permutation(multiplier)
    swaps, meta = base.synthesize_swaps(perm)
    if not base.validate_swap_network(perm, swaps):
        raise AssertionError(f"swap synthesis failed for multiplier={multiplier}")
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
    # Deliberately idle at circuit-construction time. HLS may borrow them as
    # clean ancillas when lowering MCXGate objects.
    scratch = AncillaRegister(SCRATCH_BITS, "mcx_hls_scratch")
    return phase_q, work, scratch


def build_recycled(phase_bits: int, use_measure2: bool):
    phase_q, work, scratch = make_registers(1)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(
        phase_q, work, scratch, phase,
        name=f"shor35_generic_perm_mcx_recycled_{phase_bits}b",
    )
    anc = phase_q[0]
    qc.x(work[0])
    rounds = []
    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        multiplier = pow(A, 1 << k, N)
        meta = append_controlled_modular_permutation_mcx(qc, anc, work, multiplier)
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
        name=f"shor35_generic_perm_mcx_wide_{phase_bits}b",
    )
    qc.x(work[0])
    rounds = []
    for k in range(phase_bits):
        qc.h(phase_q[k])
        multiplier = pow(A, 1 << k, N)
        meta = append_controlled_modular_permutation_mcx(qc, phase_q[k], work, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc, rounds


def stats(original, compiled, seconds: float) -> dict:
    ops = {str(k): int(v) for k, v in compiled.count_ops().items()}
    return {
        "logical_qubits": original.num_qubits,
        "high_level_depth": original.depth(),
        "high_level_size": original.size(),
        "high_level_ops": {str(k): int(v) for k, v in original.count_ops().items()},
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


def hls_for_profile(profile: str):
    if profile == "auto":
        return None
    return HLSConfig(mcx=[profile])


def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-QPU MCX-HLS sweep for generic full-residue N=35 Shor.")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=1)
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="both")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument(
        "--profiles",
        nargs="+",
        default=["auto", "n_clean_m15", "1_clean_kg24", "noaux_v24"],
        help="MCX HLS methods to test; 'auto' uses the backend/default HLS choice.",
    )
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor35_generic_permutation"))
    args = ap.parse_args()

    semantic = base.semantic_report(args.phase_bits)
    print("Full-residue semantic self-test: PASS")
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

    results = []
    for profile in args.profiles:
        print(f"\n===== MCX PROFILE: {profile} =====")
        for kind, qc, rounds in circuits:
            print(f"\n=== {kind} / {profile} ===")
            print(json.dumps({
                "logical_qubits": qc.num_qubits,
                "depth": qc.depth(),
                "size": qc.size(),
                "ops": {str(k): int(v) for k, v in qc.count_ops().items()},
                "rounds": rounds,
            }, indent=2))
            try:
                pm = generate_preset_pass_manager(
                    backend=backend,
                    optimization_level=args.optimization_level,
                    seed_transpiler=args.seed_transpiler,
                    hls_config=hls_for_profile(profile),
                    qubits_initially_zero=True,
                )
                t0 = time.perf_counter()
                compiled = pm.run(qc)
                elapsed = time.perf_counter() - t0
                row = {
                    "profile": profile,
                    "kind": kind,
                    "success": True,
                    **stats(qc, compiled, elapsed),
                }
                print(json.dumps(row, indent=2, default=str))
            except Exception as exc:
                row = {
                    "profile": profile,
                    "kind": kind,
                    "success": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                print(json.dumps(row, indent=2))
            results.append(row)

    good = [r for r in results if r.get("success")]
    best = min(good, key=lambda r: (r["cz"], r["compiled_depth"])) if good else None
    if best:
        print("\n=== BEST NATIVE RESULT ===")
        print(json.dumps(best, indent=2, default=str))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": N,
        "a": A,
        "phase_bits": args.phase_bits,
        "optimization_level": args.optimization_level,
        "seed_transpiler": args.seed_transpiler,
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "semantic": semantic,
        "profiles": args.profiles,
        "results": results,
        "best_native_result": best,
        "scope_note": "Full-register truth-table/permutation synthesis for small N; not scalable modular arithmetic.",
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"generic_full_permutation_mcx_sweep_{args.phase_bits}b_{backend.name}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
