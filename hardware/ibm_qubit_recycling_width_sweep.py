#!/usr/bin/env python3
"""Zero-QPU qubit-width optimization sweep for the N=35 recycled Shor path.

This returns the project to its original resource-optimization question: how few
simultaneously allocated qubits are needed when the phase register is recycled,
and how much native CZ/depth cost is paid for that reduction?

The existing direct-transposition implementation allocates four otherwise-idle
scratch ancillas because WORK_BITS=6 and the original HLS sweep used
SCRATCH_BITS=WORK_BITS-2.  The commonly selected MCX synthesis profile is
`1_clean_kg24`, so this experiment explicitly sweeps scratch allocation instead
of assuming four ancillas are required.

For each requested phase precision, scratch width, and QPE construction
(recycled or wide), the script:
  * preserves the same exact full-register N=35 modular-permutation semantics;
  * exhaustively reuses the existing semantic validator before compilation;
  * compiles to an IBM backend target without submitting a QPU job;
  * records allocated logical qubits and actually touched compiled qubits;
  * records native CZ, compiled depth/size, reset/measure/control-flow counts;
  * reports same-scratch wide-vs-recycled comparisons and minimum successful
    scratch width.

Important boundary: the modular arithmetic remains small-N truth-table/full-
register synthesis. This is a qubit-recycling/resource experiment, not scalable
RSA arithmetic.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import QFTGate
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import ibm_shor35_generic_permutation_direct_transposition as direct
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-15-qubit-recycling-width-sweep-v1"
DEFAULT_OUT = Path("results/qubit_recycling/ibm_qubit_recycling_width_sweep.json")


def make_registers(phase_width: int, scratch_bits: int):
    phase_q = QuantumRegister(phase_width, "phase_q")
    work = QuantumRegister(direct.WORK_BITS, "work")
    scratch = (
        AncillaRegister(scratch_bits, "mcx_hls_scratch")
        if scratch_bits > 0
        else None
    )
    return phase_q, work, scratch


def build_recycled(phase_bits: int, scratch_bits: int, use_measure2: bool):
    phase_q, work, scratch = make_registers(1, scratch_bits)
    phase = ClassicalRegister(phase_bits, "phase")
    regs = [phase_q, work]
    if scratch is not None:
        regs.append(scratch)
    regs.append(phase)
    qc = QuantumCircuit(*regs, name=f"shor35_recycled_{phase_bits}b_s{scratch_bits}")

    anc = phase_q[0]
    qc.x(work[0])
    rounds = []
    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        multiplier = pow(direct.A, 1 << k, direct.N)
        meta = direct.append_direct_modular_permutation(qc, anc, work, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)
        qc.h(anc)
        ref.ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)
    return qc, rounds


def build_wide(phase_bits: int, scratch_bits: int):
    phase_q, work, scratch = make_registers(phase_bits, scratch_bits)
    phase = ClassicalRegister(phase_bits, "phase")
    regs = [phase_q, work]
    if scratch is not None:
        regs.append(scratch)
    regs.append(phase)
    qc = QuantumCircuit(*regs, name=f"shor35_wide_{phase_bits}b_s{scratch_bits}")

    qc.x(work[0])
    rounds = []
    for k in range(phase_bits):
        qc.h(phase_q[k])
        multiplier = pow(direct.A, 1 << k, direct.N)
        meta = direct.append_direct_modular_permutation(qc, phase_q[k], work, multiplier)
        meta["qpe_bit"] = k
        rounds.append(meta)
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc, rounds


def build(kind: str, phase_bits: int, scratch_bits: int, use_measure2: bool):
    semantic = direct.semantic_summary(phase_bits)
    if not semantic["pass"]:
        raise RuntimeError("full-register semantic self-test failed")
    if kind == "recycled":
        qc, rounds = build_recycled(phase_bits, scratch_bits, use_measure2)
    elif kind == "wide":
        qc, rounds = build_wide(phase_bits, scratch_bits)
    else:
        raise ValueError(kind)
    return qc, rounds, semantic


def touched_qubits(qc: QuantumCircuit) -> tuple[int, list[int]]:
    used = set()
    for entry in qc.data:
        for q in entry.qubits:
            used.add(int(qc.find_bit(q).index))
    return len(used), sorted(used)


def compile_one(qc, backend, profile: str, level: int, seed: int) -> dict:
    kwargs = {
        "backend": backend,
        "optimization_level": level,
        "seed_transpiler": seed,
        "qubits_initially_zero": True,
    }
    hls = direct.hls_for_profile(profile)
    if hls is not None:
        kwargs["hls_config"] = hls
    pm = generate_preset_pass_manager(**kwargs)
    t0 = time.perf_counter()
    compiled = pm.run(qc)
    elapsed = time.perf_counter() - t0
    ops = {str(k): int(v) for k, v in compiled.count_ops().items()}
    touched_count, touched_indices = touched_qubits(compiled)
    return {
        "compiled_depth": int(compiled.depth()),
        "compiled_size": int(compiled.size()),
        "native_cz": int(ops.get("cz", 0)),
        "compiled_reset": int(ops.get("reset", 0)),
        "compiled_measure": int(ops.get("measure", 0)),
        "compiled_measure_2": int(ops.get("measure_2", 0)),
        "compiled_if_else": int(ops.get("if_else", 0)),
        "compiled_ops": ops,
        "compiled_container_qubits": int(compiled.num_qubits),
        "compiled_touched_qubits": int(touched_count),
        "compiled_touched_qubit_indices": touched_indices,
        "compile_seconds": float(elapsed),
    }


def pareto_front(rows: list[dict]) -> list[dict]:
    good = [r for r in rows if r.get("success")]
    out = []
    for row in good:
        dominated = False
        for other in good:
            if other is row:
                continue
            no_worse = (
                other["logical_qubits"] <= row["logical_qubits"]
                and other["native_cz"] <= row["native_cz"]
                and other["compiled_depth"] <= row["compiled_depth"]
            )
            strictly_better = (
                other["logical_qubits"] < row["logical_qubits"]
                or other["native_cz"] < row["native_cz"]
                or other["compiled_depth"] < row["compiled_depth"]
            )
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            out.append(row)
    return sorted(out, key=lambda r: (r["logical_qubits"], r["native_cz"], r["compiled_depth"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-QPU qubit recycling / scratch-width sweep")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", nargs="+", type=int, default=[8])
    ap.add_argument("--scratch-bits", nargs="+", type=int, default=[0, 1, 2, 4])
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="both")
    ap.add_argument("--profile", default="1_clean_kg24")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seed", type=int, default=8776)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bits_list = sorted(set(int(x) for x in args.phase_bits))
    scratch_list = sorted(set(int(x) for x in args.scratch_bits))
    if not bits_list or min(bits_list) < 1:
        raise SystemExit("phase bits must be >= 1")
    if not scratch_list or min(scratch_list) < 0:
        raise SystemExit("scratch bits must be >= 0")

    kinds = ["recycled", "wide"] if args.kind == "both" else [args.kind]
    max_required = max(
        direct.WORK_BITS + s + (max(bits_list) if kind == "wide" else 1)
        for s in scratch_list
        for kind in kinds
    )

    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, max_required, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} qubits={backend.num_qubits} measure_2={use_measure2}")
    print("ZERO-QPU QUBIT-WIDTH SWEEP: no Sampler or QPU job is used.")
    print(
        f"N={direct.N} work_bits={direct.WORK_BITS} profile={args.profile} "
        f"phase_bits={bits_list} scratch_bits={scratch_list} kinds={kinds}"
    )

    result = {
        "experiment": "ibm_qubit_recycling_width_sweep_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": backend.name,
        "backend_num_qubits": int(backend.num_qubits),
        "N": int(direct.N),
        "base": int(direct.A),
        "work_bits": int(direct.WORK_BITS),
        "profile": args.profile,
        "optimization_level": int(args.optimization_level),
        "seed_transpiler": int(args.seed),
        "phase_bits": bits_list,
        "scratch_bits": scratch_list,
        "kinds": kinds,
        "scope_boundary": "exact full-register small-N permutation synthesis; qubit-width experiment, not scalable modular arithmetic",
        "rows": [],
    }

    for bits in bits_list:
        for scratch_bits in scratch_list:
            for kind in kinds:
                expected_width = direct.WORK_BITS + scratch_bits + (1 if kind == "recycled" else bits)
                print(
                    f"\n=== bits={bits} scratch={scratch_bits} kind={kind} "
                    f"logical_width={expected_width} ==="
                )
                try:
                    qc, rounds, semantic = build(kind, bits, scratch_bits, use_measure2)
                    if qc.num_qubits != expected_width:
                        raise AssertionError(
                            f"allocated width {qc.num_qubits} != expected {expected_width}"
                        )
                    row = {
                        "success": True,
                        "phase_bits": int(bits),
                        "scratch_bits": int(scratch_bits),
                        "kind": kind,
                        "phase_register_qubits": 1 if kind == "recycled" else int(bits),
                        "work_register_qubits": int(direct.WORK_BITS),
                        "logical_qubits": int(qc.num_qubits),
                        "phase_qubits_saved_vs_wide_formula": int(bits - 1) if kind == "recycled" else 0,
                        "high_level_depth": int(qc.depth()),
                        "high_level_size": int(qc.size()),
                        "high_level_ops": {str(k): int(v) for k, v in qc.count_ops().items()},
                        "total_direct_mcx": int(sum(int(r.get("direct_mcx", 0)) for r in rounds)),
                        "total_basis_change_cx": int(sum(int(r.get("basis_change_cx", 0)) for r in rounds)),
                        "round_multipliers": [int(r["multiplier"]) for r in rounds],
                        "semantic_pass": bool(semantic["pass"]),
                        "scratch_register_reused_across_all_rounds": bool(scratch_bits > 0),
                        "order_used_in_circuit_construction": False,
                        "orbit_encoding_used": False,
                    }
                    row.update(
                        compile_one(
                            qc,
                            backend,
                            args.profile,
                            args.optimization_level,
                            args.seed,
                        )
                    )
                except Exception as exc:
                    row = {
                        "success": False,
                        "phase_bits": int(bits),
                        "scratch_bits": int(scratch_bits),
                        "kind": kind,
                        "logical_qubits": int(expected_width),
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                result["rows"].append(row)
                print(json.dumps(row, indent=2, default=str))
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    good = [r for r in result["rows"] if r.get("success")]
    summaries = {}
    for bits in bits_list:
        summaries[str(bits)] = {}
        for kind in kinds:
            subset = [r for r in good if r["phase_bits"] == bits and r["kind"] == kind]
            if not subset:
                continue
            min_scratch = min(r["scratch_bits"] for r in subset)
            min_width_row = min(
                subset,
                key=lambda r: (r["logical_qubits"], r["native_cz"], r["compiled_depth"]),
            )
            best_native = min(
                subset,
                key=lambda r: (r["native_cz"], r["compiled_depth"], r["logical_qubits"]),
            )
            summaries[str(bits)][kind] = {
                "minimum_successful_scratch_bits": int(min_scratch),
                "minimum_width_row": min_width_row,
                "best_native_row": best_native,
                "pareto_front": pareto_front(subset),
            }

    comparisons = {}
    if set(kinds) == {"recycled", "wide"}:
        for bits in bits_list:
            for scratch_bits in scratch_list:
                r = next((x for x in good if x["phase_bits"] == bits and x["scratch_bits"] == scratch_bits and x["kind"] == "recycled"), None)
                w = next((x for x in good if x["phase_bits"] == bits and x["scratch_bits"] == scratch_bits and x["kind"] == "wide"), None)
                if r is None or w is None:
                    continue
                comparisons[f"{bits}b_s{scratch_bits}"] = {
                    "phase_bits": int(bits),
                    "scratch_bits": int(scratch_bits),
                    "wide_logical_qubits": int(w["logical_qubits"]),
                    "recycled_logical_qubits": int(r["logical_qubits"]),
                    "logical_qubits_saved": int(w["logical_qubits"] - r["logical_qubits"]),
                    "logical_qubit_reduction_fraction": float((w["logical_qubits"] - r["logical_qubits"]) / w["logical_qubits"]),
                    "wide_touched_compiled_qubits": int(w["compiled_touched_qubits"]),
                    "recycled_touched_compiled_qubits": int(r["compiled_touched_qubits"]),
                    "native_cz_ratio_recycled_over_wide": float(r["native_cz"] / w["native_cz"]) if w["native_cz"] else None,
                    "compiled_depth_ratio_recycled_over_wide": float(r["compiled_depth"] / w["compiled_depth"]) if w["compiled_depth"] else None,
                    "reset_overhead_recycled": int(r["compiled_reset"]),
                    "if_else_overhead_recycled": int(r["compiled_if_else"]),
                }

    result["summaries"] = summaries
    result["wide_vs_recycled"] = comparisons
    result["completed"] = True
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("\n===== MINIMUM-WIDTH SUMMARY =====")
    for bits, by_kind in summaries.items():
        for kind, summary in by_kind.items():
            row = summary["minimum_width_row"]
            print(
                f"bits={bits} kind={kind}: scratch={row['scratch_bits']} "
                f"logical={row['logical_qubits']} touched={row['compiled_touched_qubits']} "
                f"CZ={row['native_cz']} depth={row['compiled_depth']}"
            )
    if comparisons:
        print("\n===== WIDE VS RECYCLED =====")
        for key, c in comparisons.items():
            print(
                f"{key}: qubits {c['wide_logical_qubits']}->{c['recycled_logical_qubits']} "
                f"saved={c['logical_qubits_saved']} CZ_ratio={c['native_cz_ratio_recycled_over_wide']:.4f} "
                f"depth_ratio={c['compiled_depth_ratio_recycled_over_wide']:.4f}"
            )
    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
