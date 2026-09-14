#!/usr/bin/env python3
"""Zero-QPU phase-width scaling for the best full-residue N=35 permutation synthesis.

Uses the order/orbit-independent full six-bit modular permutation from
`ibm_shor35_generic_full_permutation_mcx_sweep.py` and freezes one MCX HLS
profile (default: 1_clean_kg24).  It compiles recycled and wide circuits at
several QPE precisions against one IBM backend target and records native CZ,
depth, size, width, and compile time.  It NEVER submits a QPU job.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler.passes.synthesis import HLSConfig
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import ibm_shor35_generic_full_permutation_mcx_sweep as sweep
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-full-permutation-scale-v1"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU phase-width scaling for generic full-residue N=35 Shor permutation."
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, nargs="+", default=[2, 4, 6, 8])
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="both")
    ap.add_argument("--profile", default="1_clean_kg24")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor35_generic_permutation"),
    )
    args = ap.parse_args()

    bits_list = sorted(set(args.phase_bits))
    if not bits_list or bits_list[0] < 1:
        raise SystemExit("all --phase-bits values must be >= 1")

    # Select the backend once using the largest requested logical width.
    max_bits = max(bits_list)
    max_semantic = sweep.base.semantic_report(max_bits)
    if args.kind in ("wide", "both"):
        required = max_semantic["wide_logical_qubits"]
    else:
        required = max_semantic["recycled_logical_qubits"]

    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, required, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)
    print(f"backend={backend.name} measure_2={use_measure2}")
    print(f"MCX profile={args.profile} optimization_level={args.optimization_level}")
    print("NO QPU JOBS WILL BE SUBMITTED.")

    hls = HLSConfig(mcx=[args.profile])
    rows = []

    for bits in bits_list:
        semantic = sweep.base.semantic_report(bits)
        print(f"\n===== PHASE BITS: {bits} =====")
        print(
            json.dumps(
                {
                    "order_used_in_circuit_construction": semantic[
                        "order_used_in_circuit_construction"
                    ],
                    "orbit_encoding_used": semantic["orbit_encoding_used"],
                    "recycled_logical_qubits": semantic["recycled_logical_qubits"],
                    "wide_logical_qubits": semantic["wide_logical_qubits"],
                    "multipliers": [r["multiplier"] for r in semantic["rounds"]],
                    "adjacent_basis_swaps_by_round": [
                        r["adjacent_basis_swaps"] for r in semantic["rounds"]
                    ],
                },
                indent=2,
            )
        )

        circuits = []
        if args.kind in ("recycled", "both"):
            qc, rounds = sweep.build_recycled(bits, use_measure2)
            circuits.append(("recycled", qc, rounds))
        if args.kind in ("wide", "both"):
            qc, rounds = sweep.build_wide(bits)
            circuits.append(("wide", qc, rounds))

        compiled_by_kind = {}
        for kind, qc, rounds in circuits:
            pm = generate_preset_pass_manager(
                backend=backend,
                optimization_level=args.optimization_level,
                seed_transpiler=args.seed_transpiler,
                hls_config=hls,
                qubits_initially_zero=True,
            )
            t0 = time.perf_counter()
            compiled = pm.run(qc)
            elapsed = time.perf_counter() - t0
            stat = sweep.stats(qc, compiled, elapsed)
            row = {
                "phase_bits": bits,
                "profile": args.profile,
                "kind": kind,
                "success": True,
                "order_used_in_circuit_construction": False,
                "orbit_encoding_used": False,
                "round_multipliers": [r["multiplier"] for r in rounds],
                "round_adjacent_basis_swaps": [
                    r["adjacent_basis_swaps"] for r in rounds
                ],
                **stat,
            }
            rows.append(row)
            compiled_by_kind[kind] = row
            print(f"\n--- {kind} ---")
            print(json.dumps(row, indent=2, default=str))

        if "recycled" in compiled_by_kind and "wide" in compiled_by_kind:
            r = compiled_by_kind["recycled"]
            w = compiled_by_kind["wide"]
            comp = {
                "phase_bits": bits,
                "logical_qubits_saved": w["logical_qubits"] - r["logical_qubits"],
                "cz_recycled": r["cz"],
                "cz_wide": w["cz"],
                "cz_recycled_minus_wide": r["cz"] - w["cz"],
                "depth_recycled": r["compiled_depth"],
                "depth_wide": w["compiled_depth"],
                "depth_recycled_minus_wide": r["compiled_depth"] - w["compiled_depth"],
            }
            print("\n--- comparison ---")
            print(json.dumps(comp, indent=2))

    summary = []
    for bits in bits_list:
        by = {r["kind"]: r for r in rows if r["phase_bits"] == bits}
        s = {"phase_bits": bits}
        for kind in ("recycled", "wide"):
            if kind in by:
                s[f"{kind}_logical_qubits"] = by[kind]["logical_qubits"]
                s[f"{kind}_cz"] = by[kind]["cz"]
                s[f"{kind}_depth"] = by[kind]["compiled_depth"]
                s[f"{kind}_size"] = by[kind]["compiled_size"]
                s[f"{kind}_compile_seconds"] = by[kind]["compile_seconds"]
        if "recycled" in by and "wide" in by:
            s["logical_qubits_saved"] = by["wide"]["logical_qubits"] - by["recycled"]["logical_qubits"]
            s["cz_recycled_minus_wide"] = by["recycled"]["cz"] - by["wide"]["cz"]
            s["depth_recycled_minus_wide"] = by["recycled"]["compiled_depth"] - by["wide"]["compiled_depth"]
        summary.append(s)

    print("\n===== SCALING SUMMARY =====")
    print(json.dumps(summary, indent=2))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": sweep.N,
        "a": sweep.A,
        "profile": args.profile,
        "phase_bits": bits_list,
        "optimization_level": args.optimization_level,
        "seed_transpiler": args.seed_transpiler,
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "rows": rows,
        "summary": summary,
        "scope_note": (
            "Full-register truth-table/permutation synthesis for small N; "
            "order/orbit-independent but not scalable modular arithmetic."
        ),
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"generic_full_permutation_scale_{backend.name}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
