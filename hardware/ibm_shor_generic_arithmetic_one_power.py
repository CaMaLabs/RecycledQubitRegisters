#!/usr/bin/env python3
"""Zero-QPU one-power IBM preflight for the direct reversible-arithmetic Shor path.

This uses `ibm_shor_generic_arithmetic.py`, whose circuit constructor depends on
N and a but not the multiplicative order or a compiled modular orbit.  It builds
exactly one controlled modular-multiplication round and transpiles recycled and
wide variants to an IBM backend target.  No Sampler job is ever submitted.

The purpose is to measure the native cost of the explicit MCX/ripple-style
arithmetic after the high-level-HLS route proved catastrophically expensive.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler import generate_preset_pass_manager

import ibm_shor_generic_arithmetic as ga
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-direct-arithmetic-one-power-v1"


def compile_one(qc, backend, level: int, seed: int):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=level,
        seed_transpiler=seed,
    )
    t0 = time.perf_counter()
    compiled = pm.run(qc)
    elapsed = time.perf_counter() - t0
    row = ga.compiled_stats(qc, compiled)
    row["compile_seconds"] = elapsed
    return row


def main() -> int:
    ap = argparse.ArgumentParser(
        description="One controlled modular-multiply compiler preflight; never submits a QPU job."
    )
    ap.add_argument("--N", type=int, default=35)
    ap.add_argument("--a", type=int, default=2)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="both")
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor_generic_arithmetic"),
    )
    args = ap.parse_args()

    phase_bits = 1
    test = ga.exhaustive_self_test(args.N, args.a, phase_bits)
    print("Generic direct-arithmetic self-test:", "PASS" if test["pass"] else "FAIL")
    print(json.dumps(test, indent=2))
    if not test["pass"]:
        raise SystemExit("Generic arithmetic self-test failed")

    work_bits = (args.N - 1).bit_length()
    recycled_width = 1 + work_bits + (work_bits + 1) + 1
    wide_width = phase_bits + work_bits + (work_bits + 1) + 1
    required = max(recycled_width, wide_width)

    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, required, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    circuits = []
    if args.kind in ("recycled", "both"):
        circuits.append(("recycled", ga.build_recycled(args.N, args.a, phase_bits, use_measure2)))
    if args.kind in ("wide", "both"):
        circuits.append(("wide", ga.build_wide(args.N, args.a, phase_bits)))

    print("\n=== target ===")
    print(f"backend={backend.name} measure_2={use_measure2}")
    print(json.dumps({
        "work_bits": work_bits,
        "accumulator_bits": work_bits + 1,
        "flag_bits": 1,
        "recycled_logical_qubits": recycled_width,
        "wide_logical_qubits": wide_width,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
    }, indent=2))

    rows = {}
    for kind, qc in circuits:
        print(f"\n=== compiling {kind} ===")
        print(json.dumps(ga.circuit_stats(qc), indent=2))
        row = compile_one(qc, backend, args.optimization_level, args.seed_transpiler)
        rows[kind] = row
        print(json.dumps(row, indent=2, default=str))

    comparison = None
    if "recycled" in rows and "wide" in rows:
        r, w = rows["recycled"], rows["wide"]
        comparison = {
            "logical_qubits_saved": w["logical_qubits"] - r["logical_qubits"],
            "cz_difference_recycled_minus_wide": r["cz"] - w["cz"],
            "depth_difference_recycled_minus_wide": r["depth"] - w["depth"],
            "note": "At one phase bit both architectures should have the same arithmetic cost; this is a compiler sanity check, not an architecture advantage test.",
        }
        print("\n=== comparison ===")
        print(json.dumps(comparison, indent=2))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": args.N,
        "a": args.a,
        "phase_bits": phase_bits,
        "optimization_level": args.optimization_level,
        "seed_transpiler": args.seed_transpiler,
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "construction": "direct_reversible_constant_modular_addition_multiplier",
        "self_test": test,
        "compiled_stats": rows,
        "comparison": comparison,
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"generic_direct_one_power_N{args.N}_a{args.a}_{backend.name}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")

    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
