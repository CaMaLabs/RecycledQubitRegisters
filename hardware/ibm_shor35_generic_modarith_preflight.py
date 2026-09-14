#!/usr/bin/env python3
"""Zero-QPU IBM preflight for generic-arithmetic N=35 Shor order finding.

This compiles the full-residue reversible arithmetic circuits from
`generic_modarith_shor.py` against a real IBM backend target.  It NEVER submits
a Sampler job.  The purpose is to answer the resource-boundary question before
spending QPU time:

  Can the order-agnostic modular-arithmetic implementation be lowered to the
  backend ISA at a plausible width/depth/CZ cost, and how much does recycling
  the phase register save once arithmetic ancillas are included?

Start with one phase bit to measure one controlled modular multiplier, then
scale to 4/6/8 phase bits only if compilation remains tractable.

Qiskit HLS note
---------------
The arithmetic builder intentionally represents controlled high-level arithmetic
as AnnotatedOperations.  Some ancilla-using HLS plugins synthesize the inner
operation onto more qubits than are explicitly carried by the annotated control
wrapper.  In Qiskit 2.5.x this can fail during recursive annotated synthesis with
errors such as::

    CircuitError: Cannot compose onto a circuit with fewer qubits (... > ...)

For the first backend preflight we therefore default to *ancilla-free* inner HLS
methods (`IntComp.noaux` and `ModularAdder.qft_d00`).  This is a conservative
compiler bridge, not the final arithmetic optimization.  Once the full generic
circuit lowers successfully, explicit clean-ancilla arithmetic can be introduced
in the circuit itself and benchmarked separately.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from qiskit.circuit.exceptions import CircuitError
from qiskit.transpiler.passes.synthesis import HLSConfig
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import generic_modarith_shor as gm
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-modarith-preflight-v2"
N = 35
A = 2


def compile_circuit(circuit, backend, *, level: int, seed: int, hls_config: HLSConfig):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=level,
        seed_transpiler=seed,
        hls_config=hls_config,
    )
    t0 = time.perf_counter()
    compiled = pm.run(circuit)
    elapsed = time.perf_counter() - t0
    return compiled, elapsed


def circuit_stats(original, compiled, kind: str, compile_seconds: float) -> dict:
    ops = {str(k): int(v) for k, v in compiled.count_ops().items()}
    try:
        physical = compiled.layout.final_index_layout(filter_ancillas=True)
    except Exception:
        physical = None
    return {
        "kind": kind,
        "logical_qubits": original.num_qubits,
        "high_level_depth": original.depth(),
        "high_level_size": original.size(),
        "compiled_num_qubits": compiled.num_qubits,
        "compiled_depth": compiled.depth(),
        "compiled_size": compiled.size(),
        "cz": int(ops.get("cz", 0)),
        "cx": int(ops.get("cx", 0)),
        "ecr": int(ops.get("ecr", 0)),
        "reset": int(ops.get("reset", 0)),
        "measure": int(ops.get("measure", 0)),
        "measure_2": int(ops.get("measure_2", 0)),
        "if_else": int(ops.get("if_else", 0)),
        "count_ops": ops,
        "compile_seconds": compile_seconds,
        "physical_layout_after_transpile": physical,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compile generic modular-arithmetic N=35 Shor circuits; no QPU submission."
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=1)
    ap.add_argument("--architecture", choices=["recycled", "wide", "both"], default="both")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument(
        "--comparator-hls",
        choices=["default", "twos", "noaux"],
        default="noaux",
        help=(
            "Qiskit IntComp HLS plugin. 'noaux' is the safe default for annotated "
            "controlled arithmetic on Qiskit 2.5.x."
        ),
    )
    ap.add_argument(
        "--adder-hls",
        choices=["default", "modular_v17", "ripple_c04", "ripple_v95", "qft_d00"],
        default="qft_d00",
        help=(
            "Qiskit ModularAdder HLS plugin. 'qft_d00' is the safe ancilla-free "
            "default for the first controlled-arithmetic backend preflight."
        ),
    )
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor35_generic_modarith"),
    )
    args = ap.parse_args()

    if args.phase_bits < 1:
        raise SystemExit("--phase-bits must be >= 1")

    print("=== semantic self-test (no order/orbit supplied to synthesis) ===")
    semantic = gm.semantic_self_test(N, A, args.phase_bits)
    print(json.dumps(semantic, indent=2))

    resources = gm.arithmetic_resources(N, A, args.phase_bits)
    required = resources.wide_logical_qubits if args.architecture in ("wide", "both") else resources.recycled_logical_qubits

    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, required, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    print("\n=== target ===")
    print(f"backend={backend.name} measure_2={use_measure2}")
    print("logical resource model:")
    print(json.dumps(asdict(resources), indent=2))
    print(
        "HLS profile: "
        f"IntComp={args.comparator_hls} ModularAdder={args.adder_hls}"
    )

    def ibm_mid_measure(qc, qubit, clbit):
        ref.ibm_base.mid_measure(qc, qubit, clbit, use_measure2)

    circuits = []
    if args.architecture in ("recycled", "both"):
        circuits.append(
            (
                "recycled",
                gm.build_recycled_order_finder(
                    N, A, args.phase_bits, mid_measure=ibm_mid_measure
                ),
            )
        )
    if args.architecture in ("wide", "both"):
        circuits.append(("wide", gm.build_wide_order_finder(N, A, args.phase_bits)))

    hls_config = HLSConfig(
        IntComp=[args.comparator_hls],
        ModularAdder=[args.adder_hls],
    )

    stats = []
    for kind, circuit in circuits:
        print(f"\n=== compiling {kind} ===")
        print(
            json.dumps(
                {
                    "logical_qubits": circuit.num_qubits,
                    "high_level_depth": circuit.depth(),
                    "high_level_size": circuit.size(),
                },
                indent=2,
            )
        )
        try:
            compiled, elapsed = compile_circuit(
                circuit,
                backend,
                level=args.optimization_level,
                seed=args.seed_transpiler,
                hls_config=hls_config,
            )
        except CircuitError as exc:
            message = str(exc)
            if "fewer qubits" in message:
                raise SystemExit(
                    "Qiskit HLS failed while recursively synthesizing a controlled "
                    "arithmetic operation because the selected inner HLS method used "
                    "implicit ancillas. Re-run with --comparator-hls noaux "
                    "--adder-hls qft_d00. No QPU job was submitted.\n"
                    f"Original error: {message}"
                ) from exc
            raise
        row = circuit_stats(circuit, compiled, kind, elapsed)
        stats.append(row)
        print(json.dumps(row, indent=2, default=str))

    by = {row["kind"]: row for row in stats}
    comparison = None
    if "recycled" in by and "wide" in by:
        r, w = by["recycled"], by["wide"]
        comparison = {
            "logical_qubits_saved": w["logical_qubits"] - r["logical_qubits"],
            "logical_width_ratio_wide_over_recycled": w["logical_qubits"] / r["logical_qubits"],
            "compiled_depth_difference_recycled_minus_wide": r["compiled_depth"] - w["compiled_depth"],
            "cz_difference_recycled_minus_wide": r["cz"] - w["cz"],
            "cx_difference_recycled_minus_wide": r["cx"] - w["cx"],
            "note": (
                "This is a zero-QPU compiler/resource comparison. Auto layout is not a "
                "matched physical-layout experiment and must not be interpreted as a "
                "hardware performance comparison."
            ),
        }
        print("\n=== preflight comparison ===")
        print(json.dumps(comparison, indent=2))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": N,
        "a": A,
        "phase_bits": args.phase_bits,
        "optimization_level": args.optimization_level,
        "seed_transpiler": args.seed_transpiler,
        "hls": {
            "IntComp": args.comparator_hls,
            "ModularAdder": args.adder_hls,
            "profile_note": (
                "Ancilla-free HLS defaults are used to avoid Qiskit 2.5.x recursive "
                "AnnotatedOperation ancilla-width mismatch. This is a conservative "
                "compiler bridge, not the final arithmetic implementation."
            ),
        },
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "arithmetic_scope": (
            "full 6-bit residue register; multiplication modulo 35 for y<35 and "
            "identity for y>=35; accumulator/constant/flags uncomputed"
        ),
        "semantic_self_test": semantic,
        "logical_resources": asdict(resources),
        "compiled_stats": stats,
        "comparison": comparison,
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"generic_modarith_preflight_{args.phase_bits}b_{backend.name}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
