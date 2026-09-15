#!/usr/bin/env python3
"""Zero-QPU strict-width optimization of the N=35 recycled Shor circuit.

The preceding width sweep established two important operating points at eight
phase bits:

  * 7 logical/touched qubits with no explicit scratch ancilla;
  * 8 logical/touched qubits with one reusable clean scratch ancilla.

The 8-qubit point was dramatically cheaper in native CZ/depth, while the 7-qubit
point established the minimum width of the current architecture (one recycled
phase qubit plus the six-bit full-residue work register).

This script optimizes those two points across MCX HLS profiles, transpiler
optimization levels, and seeds.  A result is marked `strict_width_pass` only if
the compiled circuit touches no more physical qubits than the allocated logical
width.  This prevents a nominally small circuit from silently borrowing extra
backend qubits during synthesis/routing.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

SCRIPT_REVISION = "2026-09-15-strict-qubit-floor-profile-sweep-v1"
DEFAULT_OUT = Path("results/qubit_recycling/ibm_qubit_floor_profile_sweep.json")


def pareto(rows: list[dict]) -> list[dict]:
    good = [r for r in rows if r.get("success") and r.get("strict_width_pass")]
    out = []
    for row in good:
        dominated = False
        for other in good:
            if other is row:
                continue
            no_worse = (
                other["compiled_touched_qubits"] <= row["compiled_touched_qubits"]
                and other["native_cz"] <= row["native_cz"]
                and other["compiled_depth"] <= row["compiled_depth"]
            )
            strictly_better = (
                other["compiled_touched_qubits"] < row["compiled_touched_qubits"]
                or other["native_cz"] < row["native_cz"]
                or other["compiled_depth"] < row["compiled_depth"]
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            out.append(row)
    return sorted(
        out,
        key=lambda r: (
            r["compiled_touched_qubits"],
            r["native_cz"],
            r["compiled_depth"],
            r["profile"],
            r["optimization_level"],
            r["seed_transpiler"],
        ),
    )


def compact(row: dict | None) -> dict | None:
    if row is None:
        return None
    keys = (
        "scratch_bits",
        "logical_qubits",
        "compiled_touched_qubits",
        "extra_physical_qubits_borrowed",
        "profile",
        "optimization_level",
        "seed_transpiler",
        "native_cz",
        "compiled_depth",
        "compiled_size",
        "compile_seconds",
    )
    return {k: row.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU strict 7q/8q recycled-Shor compiler optimization"
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=8)
    ap.add_argument("--scratch-bits", nargs="+", type=int, default=[0, 1])
    ap.add_argument(
        "--profiles",
        nargs="+",
        default=["auto", "default", "noaux_v24", "1_clean_kg24", "n_clean_m15"],
    )
    ap.add_argument("--optimization-levels", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--seeds", default="8776,2026,9401")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bits = int(args.phase_bits)
    if bits < 1:
        raise SystemExit("--phase-bits must be >= 1")
    scratch_list = sorted(set(int(x) for x in args.scratch_bits))
    if not scratch_list or min(scratch_list) < 0:
        raise SystemExit("scratch bits must be >= 0")
    levels = sorted(set(int(x) for x in args.optimization_levels))
    if any(x not in (0, 1, 2, 3) for x in levels):
        raise SystemExit("optimization levels must be 0..3")
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("provide at least one transpiler seed")

    max_required = direct.WORK_BITS + 1 + max(scratch_list)
    service = width.ref.ibm_base.make_service()
    backend = width.ref.ibm_base.select_backend(service, max_required, args.backend)
    use_measure2 = width.ref.ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} qubits={backend.num_qubits} measure_2={use_measure2}")
    print("ZERO-QPU STRICT-WIDTH SWEEP: no Sampler or QPU job is used.")
    print(
        f"N={direct.N} phase_bits={bits} scratch_bits={scratch_list} "
        f"profiles={args.profiles} levels={levels} seeds={seeds}"
    )

    semantic = direct.semantic_summary(bits)
    if not semantic["pass"]:
        raise SystemExit("full-register semantic self-test failed")

    result = {
        "experiment": "ibm_qubit_floor_profile_sweep_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": backend.name,
        "backend_num_qubits": int(backend.num_qubits),
        "N": int(direct.N),
        "base": int(direct.A),
        "phase_bits": bits,
        "work_bits": int(direct.WORK_BITS),
        "scratch_bits": scratch_list,
        "profiles": list(args.profiles),
        "optimization_levels": levels,
        "seeds": seeds,
        "architecture_floor_note": (
            "With exact six-bit full-residue work semantics, one recycled phase qubit + six work qubits = 7 allocated qubits before optional scratch."
        ),
        "strict_width_definition": (
            "compiled_touched_qubits <= allocated logical_qubits; results that borrow additional backend qubits are excluded from strict-width winners"
        ),
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "semantic": semantic,
        "rows": [],
    }

    for scratch_bits in scratch_list:
        qc, rounds, semantic_row = width.build(
            "recycled", bits, scratch_bits, use_measure2
        )
        logical = int(qc.num_qubits)
        print(
            f"\n===== scratch={scratch_bits} allocated={logical}q "
            f"direct_mcx={sum(int(r.get('direct_mcx', 0)) for r in rounds)} ====="
        )
        for profile in args.profiles:
            for level in levels:
                for seed in seeds:
                    print(
                        f"compile scratch={scratch_bits} profile={profile} "
                        f"level={level} seed={seed}"
                    )
                    try:
                        stats = width.compile_one(qc, backend, profile, level, seed)
                        touched = int(stats["compiled_touched_qubits"])
                        row = {
                            "success": True,
                            "phase_bits": bits,
                            "scratch_bits": int(scratch_bits),
                            "logical_qubits": logical,
                            "work_register_qubits": int(direct.WORK_BITS),
                            "phase_register_qubits": 1,
                            "profile": profile,
                            "optimization_level": int(level),
                            "seed_transpiler": int(seed),
                            "semantic_pass": bool(semantic_row["pass"]),
                            "scratch_register_reused_across_all_rounds": bool(scratch_bits > 0),
                            "order_used_in_circuit_construction": False,
                            "orbit_encoding_used": False,
                            **stats,
                        }
                        row["extra_physical_qubits_borrowed"] = max(
                            0, touched - logical
                        )
                        row["strict_width_pass"] = touched <= logical
                        print(
                            f"  -> touched={touched} strict={row['strict_width_pass']} "
                            f"CZ={row['native_cz']} depth={row['compiled_depth']}"
                        )
                    except Exception as exc:
                        row = {
                            "success": False,
                            "phase_bits": bits,
                            "scratch_bits": int(scratch_bits),
                            "logical_qubits": logical,
                            "profile": profile,
                            "optimization_level": int(level),
                            "seed_transpiler": int(seed),
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                        print(f"  -> FAIL {type(exc).__name__}: {exc}")
                    result["rows"].append(row)
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(
                        json.dumps(result, indent=2, default=str) + "\n",
                        encoding="utf-8",
                    )

    strict = [
        r for r in result["rows"]
        if r.get("success") and r.get("strict_width_pass")
    ]
    best_by_scratch = {}
    for scratch_bits in scratch_list:
        subset = [r for r in strict if r["scratch_bits"] == scratch_bits]
        if not subset:
            best_by_scratch[str(scratch_bits)] = None
            continue
        best_by_scratch[str(scratch_bits)] = min(
            subset,
            key=lambda r: (
                r["native_cz"],
                r["compiled_depth"],
                r["compiled_touched_qubits"],
                r["optimization_level"],
                r["seed_transpiler"],
            ),
        )

    frontier = pareto(result["rows"])
    result["best_strict_by_scratch"] = best_by_scratch
    result["strict_pareto_front"] = frontier

    s0 = best_by_scratch.get("0")
    s1 = best_by_scratch.get("1")
    comparison = None
    if s0 and s1:
        comparison = {
            "seven_qubit_best": compact(s0),
            "eight_qubit_best": compact(s1),
            "extra_qubits_for_one_clean_ancilla": int(
                s1["compiled_touched_qubits"] - s0["compiled_touched_qubits"]
            ),
            "cz_ratio_8q_over_7q": float(s1["native_cz"] / s0["native_cz"]),
            "cz_reduction_8q_vs_7q": float(1.0 - s1["native_cz"] / s0["native_cz"]),
            "depth_ratio_8q_over_7q": float(
                s1["compiled_depth"] / s0["compiled_depth"]
            ),
            "depth_reduction_8q_vs_7q": float(
                1.0 - s1["compiled_depth"] / s0["compiled_depth"]
            ),
        }
    result["seven_vs_eight_qubit_comparison"] = comparison

    args.out.write_text(
        json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8"
    )

    print("\n===== BEST STRICT RESULT BY SCRATCH WIDTH =====")
    for key, row in best_by_scratch.items():
        print(f"scratch={key}: {json.dumps(compact(row), sort_keys=True)}")
    print("\n===== STRICT PARETO FRONT =====")
    for row in frontier:
        print(json.dumps(compact(row), sort_keys=True))
    print("\n===== 7Q VS 8Q =====")
    print(json.dumps(comparison, indent=2, default=str))
    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
