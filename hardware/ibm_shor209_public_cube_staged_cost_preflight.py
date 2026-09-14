#!/usr/bin/env python3
"""Zero-QPU native-cost preflight for the N=209 public-cube Dark-Star/Shor probe.

This follows `dark_star_shor_staged_stopping_time_audit.py`.  The staged audit
showed that a public PTP-conditioned cube rule can stop at lower ideal phase
precision without being given the order.  This script asks the next question:

    Does that lower stopping precision translate into lower *compiled native
    circuit execution cost* for the recycled full-register modular-unitary path?

Instance
--------
N = 209, seed base a = 3.  Because N mod 3 == 2, the public PTP rule uses
L = 3 and therefore b = a^3 mod N = 27.  The choice of L and b uses only public
N and a.  The true factors/order are never supplied to circuit construction.

Circuit semantics
-----------------
For each QPE round k, the work-register unitary is generated over the complete
8-bit register from the public multiplier

    m_k = base^(2^k) mod N

with semantics

    y < N   -> m_k*y mod N
    y >= N  -> y.

Each full-register permutation is decomposed into exact cycle transpositions.
Each arbitrary basis-state transposition uses the direct-transposition identity:
one phase-controlled pattern MCX plus reversible CNOT basis folding.  This is
truth-table/full-register synthesis for a small N, not scalable modular
arithmetic.

The script compiles recycled dynamic circuits at the staged precisions
4,6,...,16 to an IBM backend target but NEVER invokes Sampler or submits a QPU
job.  It then replays the same conservative ideal staged stopping simulation and
weights each attempted shot by the native CZ count of the compiled circuit for
that precision.

The hidden true order is used only inside the ideal simulator to draw the QPE
phase distribution and score stopping behavior, exactly as in the preceding
audit.  It is not used to select L, synthesize a multiplier, skip a round, or
choose a stage.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import MCXGate
from qiskit.transpiler.passes.synthesis import HLSConfig
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue
import dark_star_shor_staged_stopping_time_audit as staged
import ibm_shor15_hardware as ibm_base

SCRIPT_REVISION = "2026-09-14-n209-public-cube-staged-native-cost-v1"
N = 209
SEED_BASE = 3
WORK_BITS = N.bit_length()  # 8
WORK_DIM = 1 << WORK_BITS
SCRATCH_BITS = 4
DEFAULT_STAGE_BITS = (4, 6, 8, 10, 12, 14, 16)


def bit(value: int, index: int) -> int:
    return (value >> index) & 1


def modular_permutation(multiplier: int) -> list[int]:
    m = int(multiplier) % N
    if math.gcd(m, N) != 1:
        raise ValueError(f"multiplier {m} is not invertible mod {N}")
    return [(m * y) % N if y < N else y for y in range(WORK_DIM)]


def permutation_cycles(perm: list[int]) -> list[list[int]]:
    seen = [False] * len(perm)
    out = []
    for start in range(len(perm)):
        if seen[start]:
            continue
        cyc = []
        x = start
        while not seen[x]:
            seen[x] = True
            cyc.append(x)
            x = perm[x]
        if len(cyc) > 1:
            out.append(cyc)
    return out


def apply_transpositions(x: int, transpositions: list[tuple[int, int]]) -> int:
    y = int(x)
    for u, v in transpositions:
        if y == u:
            y = v
        elif y == v:
            y = u
    return y


def star_transpositions(cycle: list[int], pivot_index: int) -> list[tuple[int, int]]:
    rotated = cycle[pivot_index:] + cycle[:pivot_index]
    pivot = rotated[0]
    trans = [(pivot, other) for other in rotated[1:]]
    expected = {cycle[i]: cycle[(i + 1) % len(cycle)] for i in range(len(cycle))}
    got = {x: apply_transpositions(x, trans) for x in cycle}
    if got != expected:
        raise AssertionError("star transposition factorization failed")
    return trans


def apply_linear_fold(value: int, target_bit: int, diff: int) -> int:
    out = int(value)
    if bit(out, target_bit):
        for j in range(WORK_BITS):
            if j != target_bit and bit(diff, j):
                out ^= 1 << j
    return out


def choose_target_bit(u: int, v: int) -> dict:
    diff = u ^ v
    if diff == 0:
        raise ValueError("transposition endpoints must differ")
    rows = []
    for target in range(WORK_BITS):
        if not bit(diff, target):
            continue
        u2 = apply_linear_fold(u, target, diff)
        v2 = apply_linear_fold(v, target, diff)
        if u2 ^ v2 != 1 << target:
            raise AssertionError("basis fold did not make endpoints adjacent")
        zero_masks = sum(
            bit(u2, j) == 0 for j in range(WORK_BITS) if j != target
        )
        rows.append(
            {
                "target_bit": target,
                "transformed_u": u2,
                "transformed_v": v2,
                "zero_mask_count": int(zero_masks),
            }
        )
    return min(rows, key=lambda r: (r["zero_mask_count"], r["target_bit"]))


def cycle_transpositions_min_hamming(cycle: list[int]) -> list[tuple[int, int]]:
    candidates = []
    for pivot_index in range(len(cycle)):
        trans = star_transpositions(cycle, pivot_index)
        basis_cx = sum(2 * ((u ^ v).bit_count() - 1) for u, v in trans)
        pattern_x = sum(2 * choose_target_bit(u, v)["zero_mask_count"] for u, v in trans)
        candidates.append((basis_cx, pattern_x, cycle[pivot_index], trans))
    return min(candidates, key=lambda r: (r[0], r[1], r[2]))[3]


def direct_transpositions(perm: list[int]) -> tuple[list[tuple[int, int]], dict]:
    trans: list[tuple[int, int]] = []
    cycles = permutation_cycles(perm)
    for cycle in cycles:
        trans.extend(cycle_transpositions_min_hamming(cycle))

    for x, expected in enumerate(perm):
        got = apply_transpositions(x, trans)
        if got != expected:
            raise AssertionError(
                f"full-register transposition validation failed x={x}: {got}!={expected}"
            )

    basis_cx = sum(2 * ((u ^ v).bit_count() - 1) for u, v in trans)
    pattern_x = sum(2 * choose_target_bit(u, v)["zero_mask_count"] for u, v in trans)
    return trans, {
        "cycle_count": len(cycles),
        "cycle_lengths": [len(c) for c in cycles],
        "basis_transpositions": len(trans),
        "direct_mcx": len(trans),
        "basis_change_cx": basis_cx,
        "pattern_x": pattern_x,
        "full_register_validation": True,
    }


def append_direct_controlled_transposition(qc, control, work, u: int, v: int) -> None:
    diff = u ^ v
    choice = choose_target_bit(u, v)
    target = int(choice["target_bit"])
    u2 = int(choice["transformed_u"])

    folded = [j for j in range(WORK_BITS) if j != target and bit(diff, j)]
    for j in folded:
        qc.cx(work[target], work[j])

    masked = []
    pattern_controls = []
    for j in range(WORK_BITS):
        if j == target:
            continue
        pattern_controls.append(work[j])
        if bit(u2, j) == 0:
            qc.x(work[j])
            masked.append(work[j])

    qc.append(
        MCXGate(1 + len(pattern_controls)),
        [control] + pattern_controls + [work[target]],
    )

    for q in reversed(masked):
        qc.x(q)
    for j in reversed(folded):
        qc.cx(work[target], work[j])


def append_modular_permutation(qc, control, work, multiplier: int) -> dict:
    perm = modular_permutation(multiplier)
    trans, meta = direct_transpositions(perm)
    for u, v in trans:
        append_direct_controlled_transposition(qc, control, work, u, v)
    return {
        **meta,
        "multiplier": int(multiplier),
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
    }


def build_recycled(a: int, phase_bits: int, use_measure2: bool):
    phase_q = QuantumRegister(1, "phase_q")
    work = QuantumRegister(WORK_BITS, "work")
    scratch = AncillaRegister(SCRATCH_BITS, "mcx_hls_scratch")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(
        phase_q,
        work,
        scratch,
        phase,
        name=f"shor209_direct_recycled_a{a}_{phase_bits}b",
    )
    anc = phase_q[0]
    qc.x(work[0])  # |1>
    rounds = []

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        multiplier = pow(a, 1 << k, N)
        if multiplier == 1:
            meta = {
                "multiplier": 1,
                "qpe_bit": k,
                "identity_round": True,
                "direct_mcx": 0,
                "basis_change_cx": 0,
                "full_register_validation": True,
            }
        else:
            meta = append_modular_permutation(qc, anc, list(work), multiplier)
            meta["qpe_bit"] = k
            meta["identity_round"] = False
        rounds.append(meta)

        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)
        qc.h(anc)
        ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)

    return qc, rounds


def compile_one(qc, backend, profile: str, level: int, seed: int) -> dict:
    hls = HLSConfig(mcx=[profile])
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=level,
        seed_transpiler=seed,
        qubits_initially_zero=True,
        hls_config=hls,
    )
    t0 = time.perf_counter()
    compiled = pm.run(qc)
    elapsed = time.perf_counter() - t0
    ops = {str(k): int(v) for k, v in compiled.count_ops().items()}
    return {
        "seed_transpiler": seed,
        "compiled_qubits": int(compiled.num_qubits),
        "compiled_depth": int(compiled.depth()),
        "compiled_size": int(compiled.size()),
        "cz": int(ops.get("cz", 0)),
        "measure": int(ops.get("measure", 0)),
        "measure_2": int(ops.get("measure_2", 0)),
        "reset": int(ops.get("reset", 0)),
        "if_else": int(ops.get("if_else", 0)),
        "compiled_ops": ops,
        "compile_seconds": elapsed,
    }


def stage_compile_table(a: int, stage_bits: list[int], backend, use_measure2: bool, profile: str, level: int, seeds: list[int]) -> dict:
    out = {}
    for m in stage_bits:
        print(f"build base={a} phase_bits={m}")
        qc, rounds = build_recycled(a, m, use_measure2)
        abstract = {
            "phase_bits": m,
            "logical_qubits": int(qc.num_qubits),
            "high_level_depth": int(qc.depth()),
            "high_level_size": int(qc.size()),
            "high_level_ops": {str(k): int(v) for k, v in qc.count_ops().items()},
            "total_direct_mcx": sum(int(r.get("direct_mcx", 0)) for r in rounds),
            "total_basis_change_cx": sum(int(r.get("basis_change_cx", 0)) for r in rounds),
            "identity_rounds": sum(bool(r.get("identity_round", False)) for r in rounds),
            "round_multipliers": [int(r["multiplier"]) for r in rounds],
            "all_rounds_validated": all(bool(r.get("full_register_validation", False)) for r in rounds),
        }
        compiled_rows = []
        for seed in seeds:
            print(f"compile base={a} bits={m} seed={seed}")
            row = compile_one(qc, backend, profile, level, seed)
            compiled_rows.append(row)
            print(json.dumps(row, indent=2))
        best = min(compiled_rows, key=lambda r: (r["cz"], r["compiled_depth"], r["seed_transpiler"]))
        out[str(m)] = {"abstract": abstract, "compiled": compiled_rows, "best": best}
    return out


def session_native_cost(session: dict, stage_bits: list[int], stage_table: dict, shots_per_stage: int) -> dict:
    by_bits = {int(k): v for k, v in stage_table.items()}
    total_cz = 0
    total_depth_executions = 0
    total_shots = 0

    if session["success"]:
        stop_idx = int(session["stage_index"])
        stop_shots = int(session["shot_in_stop_stage"])
        for idx, m in enumerate(stage_bits[: stop_idx + 1]):
            shots = stop_shots if idx == stop_idx else shots_per_stage
            total_shots += shots
            best = by_bits[m]["best"]
            total_cz += shots * int(best["cz"])
            total_depth_executions += shots * int(best["compiled_depth"])
    else:
        for m in stage_bits:
            total_shots += shots_per_stage
            best = by_bits[m]["best"]
            total_cz += shots_per_stage * int(best["cz"])
            total_depth_executions += shots_per_stage * int(best["compiled_depth"])

    return {
        "native_cz_executions": total_cz,
        "compiled_depth_executions": total_depth_executions,
        "circuit_shots_executed": total_shots,
    }


def replay_n209(policy: str, a: int, true_order: int, stage_bits: list[int], stage_table: dict, shots_per_stage: int, replicates: int) -> list[dict]:
    sessions = []
    for rep in range(replicates):
        rng = staged.deterministic_rng("n209", policy, rep)
        s = staged.simulate_session(
            N,
            a,
            true_order,
            start_bits=stage_bits[0],
            step_bits=stage_bits[1] - stage_bits[0],
            shots_per_stage=shots_per_stage,
            rng=rng,
        )
        s = {**s, **session_native_cost(s, stage_bits, stage_table, shots_per_stage)}
        sessions.append(s)
    return sessions


def summarize_sessions(sessions: list[dict]) -> dict:
    success = [s for s in sessions if s["success"]]
    def avg(key):
        vals = [float(s[key]) for s in success if s.get(key) is not None]
        return mean(vals) if vals else None
    def med(key):
        vals = [float(s[key]) for s in success if s.get(key) is not None]
        return median(vals) if vals else None
    return {
        "sessions": len(sessions),
        "success_sessions": len(success),
        "success_rate": len(success) / len(sessions) if sessions else None,
        "mean_stop_precision_bits": avg("stop_precision_bits"),
        "median_stop_precision_bits": med("stop_precision_bits"),
        "mean_cumulative_phase_round_executions": avg("cumulative_phase_round_executions"),
        "mean_native_cz_executions": avg("native_cz_executions"),
        "median_native_cz_executions": med("native_cz_executions"),
        "mean_compiled_depth_executions": avg("compiled_depth_executions"),
        "mean_circuit_shots_executed": avg("circuit_shots_executed"),
    }


def paired_summary(baseline: list[dict], transformed: list[dict]) -> dict:
    pairs = [(b, t) for b, t in zip(baseline, transformed) if b["success"] and t["success"]]
    if not pairs:
        return {"paired_success_sessions": 0}
    bit_saved = [b["stop_precision_bits"] - t["stop_precision_bits"] for b, t in pairs]
    round_ratio = [t["cumulative_phase_round_executions"] / b["cumulative_phase_round_executions"] for b, t in pairs]
    cz_ratio = [t["native_cz_executions"] / b["native_cz_executions"] for b, t in pairs if b["native_cz_executions"]]
    depth_ratio = [t["compiled_depth_executions"] / b["compiled_depth_executions"] for b, t in pairs if b["compiled_depth_executions"]]
    return {
        "paired_success_sessions": len(pairs),
        "mean_stop_precision_bits_saved": mean(bit_saved),
        "median_stop_precision_bits_saved": median(bit_saved),
        "fraction_transformed_stops_lower": sum(x > 0 for x in bit_saved) / len(bit_saved),
        "mean_phase_round_ratio_transformed_over_baseline": mean(round_ratio),
        "mean_native_cz_ratio_transformed_over_baseline": mean(cz_ratio),
        "mean_native_cz_reduction_fraction": 1.0 - mean(cz_ratio),
        "mean_compiled_depth_execution_ratio_transformed_over_baseline": mean(depth_ratio),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-QPU N209 staged native-cost preflight")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--profile", default="1_clean_kg24")
    ap.add_argument("--optimization-level", type=int, default=3)
    ap.add_argument("--seeds", default="2026,8776,9401")
    ap.add_argument("--stage-bits", nargs="+", type=int, default=list(DEFAULT_STAGE_BITS))
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--replicates", type=int, default=2000)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("results/dark_star_ptp/ibm_shor209_public_cube_staged_cost_preflight.json"),
    )
    args = ap.parse_args()

    stage_bits = sorted(set(int(x) for x in args.stage_bits))
    if len(stage_bits) < 2:
        raise SystemExit("at least two stage precisions are required")
    step = stage_bits[1] - stage_bits[0]
    if any(stage_bits[i + 1] - stage_bits[i] != step for i in range(len(stage_bits) - 1)):
        raise SystemExit("stage-bits must be evenly spaced for the staged simulator")
    if stage_bits[-1] != 2 * N.bit_length():
        raise SystemExit(f"final stage must equal textbook cap {2 * N.bit_length()} bits")
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]

    public_L = 3 if N % 3 == 2 else 1
    transformed_base = pow(SEED_BASE, public_L, N)
    if qvalue.power2_chain_shortcut(transformed_base, N)["factor_found"]:
        raise SystemExit("public transformed N209 base unexpectedly triggers classical shortcut")

    # Validation labels only; not used in construction or compilation.
    p, q = 11, 19
    lam = base.lcm(p - 1, q - 1)
    r0 = base.multiplicative_order_from_lambda(SEED_BASE, N, lam)
    r1 = base.multiplicative_order_from_lambda(transformed_base, N, lam)

    service = ibm_base.make_service()
    required = 1 + WORK_BITS + SCRATCH_BITS
    backend = ibm_base.select_backend(service, required, args.backend)
    use_measure2 = ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} measure_2={use_measure2}")
    print("N209 STAGED NATIVE-COST PREFLIGHT: NO QPU JOBS WILL BE SUBMITTED.")

    compile_tables = {
        "baseline": stage_compile_table(
            SEED_BASE, stage_bits, backend, use_measure2,
            args.profile, args.optimization_level, seeds,
        ),
        "ptp3_conditional": stage_compile_table(
            transformed_base, stage_bits, backend, use_measure2,
            args.profile, args.optimization_level, seeds,
        ),
    }

    baseline_sessions = replay_n209(
        "baseline", SEED_BASE, r0, stage_bits, compile_tables["baseline"],
        args.shots_per_stage, args.replicates,
    )
    transformed_sessions = replay_n209(
        "ptp3_conditional", transformed_base, r1,
        stage_bits, compile_tables["ptp3_conditional"],
        args.shots_per_stage, args.replicates,
    )

    summary = {
        "baseline": summarize_sessions(baseline_sessions),
        "ptp3_conditional": summarize_sessions(transformed_sessions),
    }
    paired = paired_summary(baseline_sessions, transformed_sessions)

    result = {
        "experiment": "ibm_shor209_public_cube_staged_native_cost_preflight_v1",
        "script_revision": SCRIPT_REVISION,
        "zero_qpu": True,
        "backend": backend.name,
        "N": N,
        "seed_base": SEED_BASE,
        "public_rule": "L=3 when N mod 3 == 2",
        "public_exponent": public_L,
        "transformed_base": transformed_base,
        "baseline_order_validation_only": r0,
        "transformed_order_validation_only": r1,
        "order_used_in_circuit_construction": False,
        "factor_used_in_circuit_construction": False,
        "construction": "full_8bit_residue_permutation_from_N_and_public_base",
        "scalability_boundary": "truth-table/full-register reversible synthesis for small N; not scalable modular arithmetic",
        "stage_bits": stage_bits,
        "shots_per_stage": args.shots_per_stage,
        "replicates": args.replicates,
        "profile": args.profile,
        "optimization_level": args.optimization_level,
        "seeds": seeds,
        "compile_tables": compile_tables,
        "summary": summary,
        "paired": paired,
        "simulation_boundary": (
            "Ideal nearest-bin-only conservative staged stopping simulation; compiled native CZ counts are execution-cost proxies, not hardware-fidelity predictions."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    compact_compile = {}
    for policy, table in compile_tables.items():
        compact_compile[policy] = {
            m: {
                "cz": row["best"]["cz"],
                "depth": row["best"]["compiled_depth"],
                "seed": row["best"]["seed_transpiler"],
                "direct_mcx": row["abstract"]["total_direct_mcx"],
                "basis_change_cx": row["abstract"]["total_basis_change_cx"],
            }
            for m, row in table.items()
        }

    print("\n===== N209 STAGE COMPILE SUMMARY =====")
    print(json.dumps(compact_compile, indent=2))
    print("\n===== N209 STAGED NATIVE-COST SUMMARY =====")
    print(json.dumps(summary, indent=2))
    print("\n===== N209 PAIRED NATIVE-COST RESULT =====")
    print(json.dumps(paired, indent=2))
    print("\n===== OVERALL =====")
    print(json.dumps({
        "pass": True,
        "zero_qpu": True,
        "saved": str(args.out.resolve()),
    }, indent=2))
    print("\nNO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
