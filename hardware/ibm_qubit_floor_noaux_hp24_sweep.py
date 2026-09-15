#!/usr/bin/env python3
"""Zero-QPU strict 7-qubit MCX synthesis sweep for the N=35 recycled path.

The preceding strict-width sweep established:
  * 7 qubits = architectural floor (1 recycled phase + 6 full-residue work);
  * 8 qubits = current practical Pareto knee with one reusable clean ancilla.

This follow-up asks whether Qiskit's newer zero-auxiliary Huang-Palsberg 2024
MCX synthesis can reduce the native cost of the strict seven-qubit circuit.
The relevant high-level primitive has six controls, so this is exactly the
regime where the no-auxiliary linear-CX method is intended to help.

Every candidate is rejected from the strict winner if compilation touches more
than the seven allocated qubits.  No Sampler is instantiated and no QPU job is
submitted.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

SCRIPT_REVISION = "2026-09-15-strict-7q-noaux-hp24-sweep-v1"
DEFAULT_OUT = Path("results/qubit_recycling/ibm_qubit_floor_noaux_hp24_sweep.json")


def compact(row):
    if row is None:
        return None
    keys = (
        "profile", "optimization_level", "seed_transpiler", "logical_qubits",
        "compiled_touched_qubits", "strict_width_pass", "native_cz",
        "compiled_depth", "compiled_size", "compile_seconds",
    )
    return {k: row.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(description="Strict 7q noaux HP24 MCX sweep")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=8)
    ap.add_argument(
        "--profiles", nargs="+",
        default=["noaux_hp24", "noaux_v24", "auto", "default"],
    )
    ap.add_argument("--optimization-levels", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--seeds", default="8776,2026,9401")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bits = int(args.phase_bits)
    levels = sorted(set(int(x) for x in args.optimization_levels))
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if bits < 1:
        raise SystemExit("phase bits must be >= 1")
    if any(x not in (0, 1, 2, 3) for x in levels):
        raise SystemExit("optimization levels must be 0..3")
    if not seeds:
        raise SystemExit("provide at least one transpiler seed")

    required = direct.WORK_BITS + 1
    service = width.ref.ibm_base.make_service()
    backend = width.ref.ibm_base.select_backend(service, required, args.backend)
    use_measure2 = width.ref.ibm_base.backend_has_measure2(backend)

    semantic = direct.semantic_summary(bits)
    if not semantic["pass"]:
        raise SystemExit("full-register semantic self-test failed")

    qc, rounds, semantic_row = width.build("recycled", bits, 0, use_measure2)
    if qc.num_qubits != required:
        raise AssertionError(f"expected {required} logical qubits, got {qc.num_qubits}")

    print(f"backend={backend.name} qubits={backend.num_qubits} measure_2={use_measure2}")
    print("ZERO-QPU STRICT-7Q SWEEP: no Sampler or QPU job is used.")
    print(
        f"N={direct.N} phase_bits={bits} allocated={qc.num_qubits}q "
        f"direct_mcx={sum(int(r.get('direct_mcx', 0)) for r in rounds)}"
    )
    print(f"profiles={args.profiles} levels={levels} seeds={seeds}")

    result = {
        "experiment": "ibm_qubit_floor_noaux_hp24_sweep_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": backend.name,
        "N": int(direct.N),
        "base": int(direct.A),
        "phase_bits": bits,
        "work_bits": int(direct.WORK_BITS),
        "logical_qubits": int(qc.num_qubits),
        "scratch_bits": 0,
        "profiles": list(args.profiles),
        "optimization_levels": levels,
        "seeds": seeds,
        "semantic_pass": bool(semantic_row["pass"]),
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "strict_width_definition": "compiled_touched_qubits <= 7",
        "rows": [],
    }

    for profile in args.profiles:
        for level in levels:
            for seed in seeds:
                print(f"compile profile={profile} level={level} seed={seed}")
                try:
                    stats = width.compile_one(qc, backend, profile, level, seed)
                    touched = int(stats["compiled_touched_qubits"])
                    row = {
                        "success": True,
                        "profile": profile,
                        "optimization_level": int(level),
                        "seed_transpiler": int(seed),
                        "logical_qubits": int(qc.num_qubits),
                        **stats,
                    }
                    row["strict_width_pass"] = touched <= qc.num_qubits
                    row["extra_physical_qubits_borrowed"] = max(0, touched - qc.num_qubits)
                    print(
                        f"  -> touched={touched} strict={row['strict_width_pass']} "
                        f"CZ={row['native_cz']} depth={row['compiled_depth']}"
                    )
                except Exception as exc:
                    row = {
                        "success": False,
                        "profile": profile,
                        "optimization_level": int(level),
                        "seed_transpiler": int(seed),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                    print(f"  -> FAIL {type(exc).__name__}: {exc}")
                result["rows"].append(row)
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    strict = [r for r in result["rows"] if r.get("success") and r.get("strict_width_pass")]
    best = min(
        strict,
        key=lambda r: (r["native_cz"], r["compiled_depth"], r["compiled_size"], r["seed_transpiler"]),
    ) if strict else None

    by_profile = {}
    for profile in args.profiles:
        rows = [r for r in strict if r["profile"] == profile]
        by_profile[profile] = min(
            rows,
            key=lambda r: (r["native_cz"], r["compiled_depth"], r["compiled_size"], r["seed_transpiler"]),
        ) if rows else None

    prior_cz = 45754
    prior_depth = 116578
    comparison = None
    if best:
        comparison = {
            "prior_best_7q_native_cz": prior_cz,
            "new_best_7q_native_cz": int(best["native_cz"]),
            "cz_ratio_new_over_prior": float(best["native_cz"] / prior_cz),
            "cz_reduction_fraction_vs_prior": float(1.0 - best["native_cz"] / prior_cz),
            "prior_best_7q_depth": prior_depth,
            "new_best_7q_depth": int(best["compiled_depth"]),
            "depth_ratio_new_over_prior": float(best["compiled_depth"] / prior_depth),
            "depth_reduction_fraction_vs_prior": float(1.0 - best["compiled_depth"] / prior_depth),
        }

    result["best_strict"] = best
    result["best_strict_by_profile"] = by_profile
    result["comparison_to_prior_7q_best"] = comparison
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("\n===== BEST STRICT BY PROFILE =====")
    for profile, row in by_profile.items():
        print(f"{profile}: {json.dumps(compact(row), sort_keys=True)}")
    print("\n===== BEST STRICT 7Q =====")
    print(json.dumps(compact(best), indent=2, default=str))
    print("\n===== VS PRIOR 7Q BEST =====")
    print(json.dumps(comparison, indent=2, default=str))
    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
