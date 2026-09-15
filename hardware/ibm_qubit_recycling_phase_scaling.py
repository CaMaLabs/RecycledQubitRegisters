#!/usr/bin/env python3
"""Zero-QPU phase-precision scaling benchmark for recycled vs wide N=35 QPE.

The recycled path is held at one phase qubit + six work qubits + one reusable
clean ancilla = eight allocated qubits, independent of requested phase
precision.  The wide path uses one phase qubit per precision bit, so its width
is 7 + phase_bits with the same one clean ancilla.

For each precision and transpiler seed this script compiles both constructions
to an IBM backend target, records actually touched physical qubits and native
CZ/depth, and reports the best strict-width result.  A strict result may not
borrow more physical qubits than were allocated by the source circuit.

No Sampler is instantiated and no QPU job is submitted.

Boundary: the modular unitary is still the exact small-N full-register
permutation used elsewhere in this repository.  This measures qubit-recycling
scaling, not scalable RSA modular arithmetic.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

SCRIPT_REVISION = "2026-09-15-fixed-8q-phase-scaling-v1"
DEFAULT_OUT = Path("results/qubit_recycling/ibm_qubit_recycling_phase_scaling.json")


def compact(row: dict | None) -> dict | None:
    if row is None:
        return None
    keys = (
        "kind",
        "phase_bits",
        "logical_qubits",
        "compiled_touched_qubits",
        "extra_physical_qubits_borrowed",
        "seed_transpiler",
        "native_cz",
        "compiled_depth",
        "compiled_size",
        "compile_seconds",
    )
    return {k: row.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU fixed-width recycled-vs-wide phase scaling benchmark"
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", nargs="+", type=int, default=[4, 8, 12, 16, 20])
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seeds", default="8776,2026,9401")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bits_list = sorted(set(int(x) for x in args.phase_bits))
    if not bits_list or min(bits_list) < 1:
        raise SystemExit("phase bits must be >= 1")
    if args.scratch_bits < 0:
        raise SystemExit("scratch bits must be >= 0")
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("provide at least one transpiler seed")

    recycled_width = direct.WORK_BITS + 1 + args.scratch_bits
    max_wide_width = direct.WORK_BITS + max(bits_list) + args.scratch_bits

    service = width.ref.ibm_base.make_service()
    backend = width.ref.ibm_base.select_backend(service, max_wide_width, args.backend)
    use_measure2 = width.ref.ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} qubits={backend.num_qubits} measure_2={use_measure2}")
    print("ZERO-QPU PHASE-SCALING SWEEP: no Sampler or QPU job is used.")
    print(
        f"N={direct.N} work_bits={direct.WORK_BITS} scratch={args.scratch_bits} "
        f"recycled_allocated_width={recycled_width} phase_bits={bits_list} "
        f"profile={args.profile} level={args.optimization_level} seeds={seeds}"
    )

    result = {
        "experiment": "ibm_qubit_recycling_phase_scaling_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": backend.name,
        "backend_num_qubits": int(backend.num_qubits),
        "N": int(direct.N),
        "base": int(direct.A),
        "work_bits": int(direct.WORK_BITS),
        "scratch_bits": int(args.scratch_bits),
        "recycled_allocated_width": int(recycled_width),
        "profile": args.profile,
        "optimization_level": int(args.optimization_level),
        "seeds": seeds,
        "phase_bits": bits_list,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "strict_width_definition": "compiled_touched_qubits <= allocated logical qubits",
        "scope_boundary": "exact small-N full-register permutation synthesis; phase-register recycling benchmark, not scalable RSA arithmetic",
        "rows": [],
    }

    for bits in bits_list:
        semantic = direct.semantic_summary(bits)
        if not semantic["pass"]:
            raise RuntimeError(f"semantic validation failed at phase_bits={bits}")

        for kind in ("recycled", "wide"):
            qc, rounds, _ = width.build(kind, bits, args.scratch_bits, use_measure2)
            logical = int(qc.num_qubits)
            expected = recycled_width if kind == "recycled" else direct.WORK_BITS + bits + args.scratch_bits
            if logical != expected:
                raise AssertionError(f"{kind} bits={bits}: logical width {logical} != expected {expected}")

            print(
                f"\n===== bits={bits} kind={kind} allocated={logical}q "
                f"direct_mcx={sum(int(r.get('direct_mcx', 0)) for r in rounds)} ====="
            )
            for seed in seeds:
                print(f"compile kind={kind} bits={bits} seed={seed}")
                try:
                    stats = width.compile_one(
                        qc,
                        backend,
                        args.profile,
                        args.optimization_level,
                        seed,
                    )
                    touched = int(stats["compiled_touched_qubits"])
                    row = {
                        "success": True,
                        "kind": kind,
                        "phase_bits": int(bits),
                        "scratch_bits": int(args.scratch_bits),
                        "phase_register_qubits": 1 if kind == "recycled" else int(bits),
                        "work_register_qubits": int(direct.WORK_BITS),
                        "logical_qubits": logical,
                        "seed_transpiler": int(seed),
                        "semantic_pass": True,
                        "total_direct_mcx": int(sum(int(r.get("direct_mcx", 0)) for r in rounds)),
                        "total_basis_change_cx": int(sum(int(r.get("basis_change_cx", 0)) for r in rounds)),
                        "compiled_touched_qubits": touched,
                        "extra_physical_qubits_borrowed": max(0, touched - logical),
                        "strict_width_pass": touched <= logical,
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
                        "kind": kind,
                        "phase_bits": int(bits),
                        "logical_qubits": logical,
                        "seed_transpiler": int(seed),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                    print(f"  -> FAIL {type(exc).__name__}: {exc}")
                result["rows"].append(row)
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    strict = [r for r in result["rows"] if r.get("success") and r.get("strict_width_pass")]
    best = {}
    comparisons = {}
    for bits in bits_list:
        best[str(bits)] = {}
        for kind in ("recycled", "wide"):
            subset = [r for r in strict if r["phase_bits"] == bits and r["kind"] == kind]
            if not subset:
                best[str(bits)][kind] = None
                continue
            best[str(bits)][kind] = min(
                subset,
                key=lambda r: (r["native_cz"], r["compiled_depth"], r["seed_transpiler"]),
            )

        rr = best[str(bits)].get("recycled")
        ww = best[str(bits)].get("wide")
        if rr and ww:
            comparisons[str(bits)] = {
                "phase_bits": int(bits),
                "recycled_logical_qubits": int(rr["logical_qubits"]),
                "wide_logical_qubits": int(ww["logical_qubits"]),
                "logical_qubits_saved": int(ww["logical_qubits"] - rr["logical_qubits"]),
                "logical_qubit_reduction_fraction": float((ww["logical_qubits"] - rr["logical_qubits"]) / ww["logical_qubits"]),
                "recycled_touched_qubits": int(rr["compiled_touched_qubits"]),
                "wide_touched_qubits": int(ww["compiled_touched_qubits"]),
                "recycled_native_cz": int(rr["native_cz"]),
                "wide_native_cz": int(ww["native_cz"]),
                "cz_ratio_recycled_over_wide": float(rr["native_cz"] / ww["native_cz"]) if ww["native_cz"] else None,
                "recycled_depth": int(rr["compiled_depth"]),
                "wide_depth": int(ww["compiled_depth"]),
                "depth_ratio_recycled_over_wide": float(rr["compiled_depth"] / ww["compiled_depth"]) if ww["compiled_depth"] else None,
                "recycled_seed": int(rr["seed_transpiler"]),
                "wide_seed": int(ww["seed_transpiler"]),
            }

    result["best_strict"] = best
    result["comparisons"] = comparisons
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("\n===== FIXED-WIDTH SCALING SUMMARY =====")
    for bits in bits_list:
        rr = best[str(bits)].get("recycled")
        ww = best[str(bits)].get("wide")
        if not rr or not ww:
            print(f"bits={bits}: missing strict result")
            continue
        c = comparisons[str(bits)]
        print(
            f"bits={bits}: width {ww['logical_qubits']}->{rr['logical_qubits']} "
            f"saved={c['logical_qubits_saved']} touched {ww['compiled_touched_qubits']}->{rr['compiled_touched_qubits']} "
            f"CZ_ratio={c['cz_ratio_recycled_over_wide']:.4f} "
            f"depth_ratio={c['depth_ratio_recycled_over_wide']:.4f}"
        )

    print("\n===== BEST STRICT ROWS =====")
    for bits in bits_list:
        print(f"bits={bits} recycled={json.dumps(compact(best[str(bits)].get('recycled')), sort_keys=True)}")
        print(f"bits={bits} wide={json.dumps(compact(best[str(bits)].get('wide')), sort_keys=True)}")

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
