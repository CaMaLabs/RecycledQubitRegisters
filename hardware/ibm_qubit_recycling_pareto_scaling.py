#!/usr/bin/env python3
"""Zero-QPU three-way qubit/gate Pareto scaling benchmark for N=35.

Architectures:
  * floor7: recycled QPE, six work qubits, zero scratch, noaux_hp24 profile.
  * optimum8: recycled QPE, six work qubits, one reusable clean scratch, auto profile.
  * wide: conventional wide phase register, six work qubits, one reusable clean scratch.

For each requested phase precision and transpiler seed, compile to an IBM backend
and require strict width: compiled_touched_qubits <= source logical qubits.
The script reports the best strict compile for each architecture and the
per-precision Pareto front over touched width, native CZ, and compiled depth.

No Sampler is instantiated and no QPU job is submitted.

Boundary: this uses the repository's exact small-N full-register N=35 modular
permutation. It is a qubit-recycling/resource benchmark, not scalable RSA
arithmetic.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

SCRIPT_REVISION = "2026-09-15-three-way-qubit-pareto-scaling-v1"
DEFAULT_OUT = Path("results/qubit_recycling/ibm_qubit_recycling_pareto_scaling.json")

ARCHITECTURES = {
    "floor7": {
        "kind": "recycled",
        "scratch_bits": 0,
        "profile": "noaux_hp24",
        "description": "absolute-width floor: 1 phase + 6 work",
    },
    "optimum8": {
        "kind": "recycled",
        "scratch_bits": 1,
        "profile": "auto",
        "description": "practical recycled optimum: 1 phase + 6 work + 1 clean scratch",
    },
    "wide": {
        "kind": "wide",
        "scratch_bits": 1,
        "profile": "auto",
        "description": "conventional wide phase register + 6 work + 1 clean scratch",
    },
}


def compact(row: dict | None) -> dict | None:
    if row is None:
        return None
    keys = (
        "architecture",
        "phase_bits",
        "logical_qubits",
        "compiled_touched_qubits",
        "extra_physical_qubits_borrowed",
        "profile",
        "seed_transpiler",
        "native_cz",
        "compiled_depth",
        "compiled_size",
        "compile_seconds",
    )
    return {k: row.get(k) for k in keys}


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
            r["architecture"],
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU 7q-vs-8q-vs-wide qubit/gate Pareto scaling benchmark"
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument(
        "--phase-bits",
        nargs="+",
        type=int,
        default=[4, 8, 12, 16, 20, 24, 32, 40, 48, 64],
    )
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seeds", default="8776,2026,9401")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bits_list = sorted(set(int(x) for x in args.phase_bits))
    if not bits_list or min(bits_list) < 1:
        raise SystemExit("phase bits must be >= 1")
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("provide at least one transpiler seed")

    max_wide_width = direct.WORK_BITS + max(bits_list) + 1
    service = width.ref.ibm_base.make_service()
    backend = width.ref.ibm_base.select_backend(service, max_wide_width, args.backend)
    use_measure2 = width.ref.ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} qubits={backend.num_qubits} measure_2={use_measure2}")
    print("ZERO-QPU THREE-WAY PARETO SWEEP: no Sampler or QPU job is used.")
    print(
        f"N={direct.N} work_bits={direct.WORK_BITS} phase_bits={bits_list} "
        f"level={args.optimization_level} seeds={seeds}"
    )

    result = {
        "experiment": "ibm_qubit_recycling_pareto_scaling_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": backend.name,
        "backend_num_qubits": int(backend.num_qubits),
        "N": int(direct.N),
        "base": int(direct.A),
        "work_bits": int(direct.WORK_BITS),
        "optimization_level": int(args.optimization_level),
        "seeds": seeds,
        "phase_bits": bits_list,
        "architectures": ARCHITECTURES,
        "strict_width_definition": "compiled_touched_qubits <= allocated logical qubits",
        "scope_boundary": "exact small-N full-register permutation synthesis; qubit/gate Pareto benchmark, not scalable RSA arithmetic",
        "rows": [],
    }

    for bits in bits_list:
        semantic = direct.semantic_summary(bits)
        if not semantic["pass"]:
            raise RuntimeError(f"semantic validation failed at phase_bits={bits}")

        for arch_name, arch in ARCHITECTURES.items():
            qc, rounds, _ = width.build(
                arch["kind"], bits, arch["scratch_bits"], use_measure2
            )
            logical = int(qc.num_qubits)
            expected = (
                direct.WORK_BITS + 1 + arch["scratch_bits"]
                if arch["kind"] == "recycled"
                else direct.WORK_BITS + bits + arch["scratch_bits"]
            )
            if logical != expected:
                raise AssertionError(
                    f"{arch_name} bits={bits}: logical width {logical} != expected {expected}"
                )

            print(
                f"\n===== bits={bits} arch={arch_name} allocated={logical}q "
                f"profile={arch['profile']} direct_mcx={sum(int(r.get('direct_mcx', 0)) for r in rounds)} ====="
            )
            for seed in seeds:
                print(f"compile arch={arch_name} bits={bits} seed={seed}")
                try:
                    stats = width.compile_one(
                        qc,
                        backend,
                        arch["profile"],
                        args.optimization_level,
                        seed,
                    )
                    touched = int(stats["compiled_touched_qubits"])
                    row = {
                        "success": True,
                        "architecture": arch_name,
                        "architecture_description": arch["description"],
                        "kind": arch["kind"],
                        "phase_bits": int(bits),
                        "scratch_bits": int(arch["scratch_bits"]),
                        "profile": arch["profile"],
                        "logical_qubits": logical,
                        "compiled_touched_qubits": touched,
                        "extra_physical_qubits_borrowed": max(0, touched - logical),
                        "strict_width_pass": touched <= logical,
                        "seed_transpiler": int(seed),
                        "semantic_pass": True,
                        "total_direct_mcx": int(sum(int(r.get("direct_mcx", 0)) for r in rounds)),
                        "total_basis_change_cx": int(sum(int(r.get("basis_change_cx", 0)) for r in rounds)),
                        "order_used_in_circuit_construction": False,
                        "orbit_encoding_used": False,
                        **{k: v for k, v in stats.items() if k != "compiled_touched_qubits"},
                    }
                    print(
                        f"  -> touched={touched} strict={row['strict_width_pass']} "
                        f"CZ={row['native_cz']} depth={row['compiled_depth']}"
                    )
                except Exception as exc:
                    row = {
                        "success": False,
                        "architecture": arch_name,
                        "phase_bits": int(bits),
                        "logical_qubits": logical,
                        "profile": arch["profile"],
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
    best = {}
    fronts = {}
    comparisons = {}

    for bits in bits_list:
        best[str(bits)] = {}
        candidates_for_front = []
        for arch_name in ARCHITECTURES:
            subset = [
                r for r in strict
                if r["phase_bits"] == bits and r["architecture"] == arch_name
            ]
            if not subset:
                best[str(bits)][arch_name] = None
                continue
            winner = min(
                subset,
                key=lambda r: (
                    r["native_cz"],
                    r["compiled_depth"],
                    r["seed_transpiler"],
                ),
            )
            best[str(bits)][arch_name] = winner
            candidates_for_front.append(winner)

        fronts[str(bits)] = pareto(candidates_for_front)
        f7 = best[str(bits)].get("floor7")
        o8 = best[str(bits)].get("optimum8")
        ww = best[str(bits)].get("wide")
        if f7 and o8 and ww:
            comparisons[str(bits)] = {
                "phase_bits": int(bits),
                "floor7_touched": int(f7["compiled_touched_qubits"]),
                "optimum8_touched": int(o8["compiled_touched_qubits"]),
                "wide_touched": int(ww["compiled_touched_qubits"]),
                "floor7_cz": int(f7["native_cz"]),
                "optimum8_cz": int(o8["native_cz"]),
                "wide_cz": int(ww["native_cz"]),
                "floor7_depth": int(f7["compiled_depth"]),
                "optimum8_depth": int(o8["compiled_depth"]),
                "wide_depth": int(ww["compiled_depth"]),
                "optimum8_cz_ratio_vs_floor7": float(o8["native_cz"] / f7["native_cz"]),
                "optimum8_depth_ratio_vs_floor7": float(o8["compiled_depth"] / f7["compiled_depth"]),
                "optimum8_cz_ratio_vs_wide": float(o8["native_cz"] / ww["native_cz"]),
                "optimum8_depth_ratio_vs_wide": float(o8["compiled_depth"] / ww["compiled_depth"]),
                "wide_qubits_saved_by_optimum8": int(ww["compiled_touched_qubits"] - o8["compiled_touched_qubits"]),
            }

    result["best_strict"] = best
    result["pareto_front_by_phase_bits"] = fronts
    result["comparisons"] = comparisons
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("\n===== THREE-WAY SCALING SUMMARY =====")
    for bits in bits_list:
        c = comparisons.get(str(bits))
        if not c:
            print(f"bits={bits}: missing strict result")
            continue
        print(
            f"bits={bits}: touched floor/opt/wide={c['floor7_touched']}/{c['optimum8_touched']}/{c['wide_touched']} "
            f"CZ={c['floor7_cz']}/{c['optimum8_cz']}/{c['wide_cz']} "
            f"depth={c['floor7_depth']}/{c['optimum8_depth']}/{c['wide_depth']} "
            f"8q_vs_7q_CZ={c['optimum8_cz_ratio_vs_floor7']:.4f} "
            f"8q_vs_wide_CZ={c['optimum8_cz_ratio_vs_wide']:.4f}"
        )

    print("\n===== PARETO FRONT BY PHASE BITS =====")
    for bits in bits_list:
        print(f"bits={bits}")
        for row in fronts.get(str(bits), []):
            print("  " + json.dumps(compact(row), sort_keys=True))

    print("\n===== BEST STRICT ROWS =====")
    for bits in bits_list:
        for arch_name in ARCHITECTURES:
            print(
                f"bits={bits} {arch_name}="
                + json.dumps(compact(best[str(bits)].get(arch_name)), sort_keys=True)
            )

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
