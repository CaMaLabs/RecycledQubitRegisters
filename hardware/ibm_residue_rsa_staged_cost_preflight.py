#!/usr/bin/env python3
"""Zero-QPU IBM-target native-cost preflight for residue-conditioned RSA scout cases.

This generalizes the validated N=209 full-register compiler to the two clean
post-replication scout cases:
  N=713, ell=5,  a=19 -> b=563, order 330 -> 66
  N=781, ell=7,  a=29 -> b=380, order  70 -> 10

It compiles recycled dynamic QPE circuits for each staged precision to an IBM
backend target but never invokes Sampler and never submits a QPU job.

Important boundary: the modular unitary remains exact truth-table/full-register
synthesis for small N. It is a hardware-facing cost probe, not scalable RSA
modular arithmetic.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import dark_star_ptp_shor_audit as base
import dark_star_shor_odd_power_precondition_audit as pre
import dark_star_shor_quantum_value_audit as qvalue
import dark_star_shor_staged_stopping_time_audit as staged
import dark_star_shor_residue_prime_panel_audit as panel
import ibm_shor15_hardware as ibm_base
import ibm_shor209_public_cube_staged_cost_preflight as legacy

SCRIPT_REVISION = "2026-09-15-residue-rsa-ibm-native-cost-v1"

CASES = {
    "713": {
        "N": 713,
        "p_validation_only": 23,
        "q_validation_only": 31,
        "ell": 5,
        "base": 19,
        "expected_transformed_base": 563,
        "expected_order": 330,
        "expected_transformed_order": 66,
    },
    "781": {
        "N": 781,
        "p_validation_only": 11,
        "q_validation_only": 71,
        "ell": 7,
        "base": 29,
        "expected_transformed_base": 380,
        "expected_order": 70,
        "expected_transformed_order": 10,
    },
}


def patch_legacy_modulus(n: int) -> None:
    legacy.N = int(n)
    legacy.WORK_BITS = int(n).bit_length()
    legacy.WORK_DIM = 1 << legacy.WORK_BITS


def validation_case(case_key: str) -> dict:
    cfg = dict(CASES[case_key])
    n = cfg["N"]
    p = cfg["p_validation_only"]
    q = cfg["q_validation_only"]
    ell = cfg["ell"]
    a = cfg["base"]
    b = pow(a, ell, n)
    lam = base.lcm(p - 1, q - 1)
    r0 = base.multiplicative_order_from_lambda(a, n, lam)
    r1 = base.multiplicative_order_from_lambda(b, n, lam)

    if b != cfg["expected_transformed_base"]:
        raise AssertionError(f"N={n}: transformed base {b} != expected {cfg['expected_transformed_base']}")
    if r0 != cfg["expected_order"] or r1 != cfg["expected_transformed_order"]:
        raise AssertionError(f"N={n}: order mismatch {r0}->{r1}")
    if r1 != r0 // math.gcd(r0, ell):
        raise AssertionError(f"N={n}: odd-power order identity failed")

    w0 = pre.factor_witness(a, r0, n)
    w1 = pre.factor_witness(b, r1, n)
    if not w0["factor_success"] or not w1["factor_success"]:
        raise AssertionError(f"N={n}: scout case is not factor-capable")

    s0 = qvalue.power2_chain_shortcut(a, n)
    s1 = qvalue.power2_chain_shortcut(b, n)
    if s0["factor_found"] or s1["factor_found"]:
        raise AssertionError(f"N={n}: scout case fails public classical-shortcut guardrail")

    return {
        **cfg,
        "transformed_base": b,
        "lambda_validation_only": lam,
        "baseline_order_validation_only": int(r0),
        "transformed_order_validation_only": int(r1),
        "order_reduction_factor": float(r0 / r1),
        "baseline_factor_witness": w0,
        "transformed_factor_witness": w1,
        "baseline_classical_shortcut": s0,
        "transformed_classical_shortcut": s1,
    }


def expected_stage_shots(p: float, max_shots: int) -> float:
    if p <= 0.0:
        return float(max_shots)
    q = 1.0 - p
    return float((1.0 - q ** max_shots) / p)


def exact_native_expectation(*, n: int, order: int, stage_bits: list[int], shots_per_stage: int, compile_table: dict) -> dict:
    reach = 1.0
    total_cz = 0.0
    total_depth = 0.0
    total_shots = 0.0
    total_phase_rounds = 0.0
    stage_rows = []

    for m in stage_bits:
        p = panel.fast_per_shot_stage_success(n, order, m)
        fail_stage = (1.0 - p) ** shots_per_stage
        exp_exec = reach * expected_stage_shots(p, shots_per_stage)
        best = compile_table[str(m)]["best"]
        cz = int(best["cz"])
        depth = int(best["compiled_depth"])

        total_cz += exp_exec * cz
        total_depth += exp_exec * depth
        total_shots += exp_exec
        total_phase_rounds += exp_exec * m
        stage_rows.append({
            "phase_bits": int(m),
            "reach_probability": float(reach),
            "per_shot_success_probability": float(p),
            "expected_stage_executions_unconditional": float(exp_exec),
            "stage_stop_probability": float(reach * (1.0 - fail_stage)),
            "native_cz_per_execution": cz,
            "compiled_depth_per_execution": depth,
            "expected_native_cz_contribution": float(exp_exec * cz),
            "expected_compiled_depth_contribution": float(exp_exec * depth),
        })
        reach *= fail_stage

    success = 1.0 - reach
    return {
        "success_probability_by_cap": float(success),
        "failure_probability_by_cap": float(reach),
        "expected_circuit_executions_per_attempted_session": float(total_shots),
        "expected_phase_rounds_per_attempted_session": float(total_phase_rounds),
        "expected_native_cz_per_attempted_session": float(total_cz),
        "expected_compiled_depth_per_attempted_session": float(total_depth),
        "expected_native_cz_per_success_with_session_restarts": float(total_cz / success) if success else None,
        "expected_compiled_depth_per_success_with_session_restarts": float(total_depth / success) if success else None,
        "stages": stage_rows,
    }


def compile_table_incremental(*, label: str, public_base: int, stage_bits: list[int], backend, use_measure2: bool, profile: str, level: int, seeds: list[int], result: dict, out_path: Path) -> dict:
    table = result.setdefault("compile_tables", {}).setdefault(label, {})
    for m in stage_bits:
        key = str(m)
        if key in table and table[key].get("best"):
            print(f"resume: {label} bits={m} already compiled")
            continue

        print(f"build {label}: base={public_base} phase_bits={m}")
        qc, rounds = legacy.build_recycled(public_base, m, use_measure2)
        abstract = {
            "phase_bits": int(m),
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

        compiled = []
        for seed in seeds:
            print(f"compile {label}: bits={m} seed={seed}")
            row = legacy.compile_one(qc, backend, profile, level, seed)
            compiled.append(row)
            print(f"  -> cz={row['cz']} depth={row['compiled_depth']} size={row['compiled_size']} seconds={row['compile_seconds']:.2f}")
        best = min(compiled, key=lambda r: (r["cz"], r["compiled_depth"], r["seed_transpiler"]))
        table[key] = {"abstract": abstract, "compiled": compiled, "best": best}

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"checkpointed {out_path}")

    return table


def run_case(case_key: str, *, backend, use_measure2: bool, profile: str, level: int, seeds: list[int], start_bits: int, step_bits: int, shots_per_stage: int, outdir: Path) -> dict:
    case = validation_case(case_key)
    n = case["N"]
    a = case["base"]
    b = case["transformed_base"]
    r0 = case["baseline_order_validation_only"]
    r1 = case["transformed_order_validation_only"]

    patch_legacy_modulus(n)
    stage_bits = staged.stage_schedule(n, start_bits, step_bits)
    if stage_bits[-1] != 2 * n.bit_length():
        raise AssertionError("stage schedule did not end at textbook 2n-bit cap")

    out_path = outdir / f"ibm_residue_rsa_N{n}_staged_cost_preflight.json"
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text(encoding="utf-8"))
            if result.get("N") != n or result.get("backend") != backend.name:
                result = {}
        except Exception:
            result = {}
    else:
        result = {}

    result.update({
        "experiment": "ibm_residue_rsa_staged_native_cost_preflight_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "backend": backend.name,
        "backend_num_qubits": int(backend.num_qubits),
        "measure_2_used": bool(use_measure2),
        "profile": profile,
        "optimization_level": int(level),
        "seeds": list(seeds),
        "N": n,
        "ell": case["ell"],
        "N_mod_ell": n % case["ell"],
        "seed_base": a,
        "transformed_base": b,
        "baseline_order_validation_only": r0,
        "transformed_order_validation_only": r1,
        "order_reduction_factor": case["order_reduction_factor"],
        "stage_bits": stage_bits,
        "shots_per_stage": int(shots_per_stage),
        "work_bits": int(n.bit_length()),
        "scratch_bits": int(legacy.SCRATCH_BITS),
        "logical_qubits": int(1 + n.bit_length() + legacy.SCRATCH_BITS),
        "factor_used_in_circuit_construction": False,
        "order_used_in_circuit_construction": False,
        "scalability_boundary": "exact truth-table/full-register reversible synthesis for small N; not scalable modular arithmetic and not an RSA-2048 resource estimate",
        "validation": case,
    })

    print(f"\n===== N={n} ell={case['ell']} IBM-TARGET PREFLIGHT =====\nbase {a}->{b}; order {r0}->{r1}; stages={stage_bits}; logical_qubits={result['logical_qubits']}")

    baseline_table = compile_table_incremental(
        label="baseline", public_base=a, stage_bits=stage_bits, backend=backend,
        use_measure2=use_measure2, profile=profile, level=level, seeds=seeds,
        result=result, out_path=out_path,
    )
    transformed_label = f"residue_conditioned_ell_{case['ell']}"
    transformed_table = compile_table_incremental(
        label=transformed_label, public_base=b, stage_bits=stage_bits, backend=backend,
        use_measure2=use_measure2, profile=profile, level=level, seeds=seeds,
        result=result, out_path=out_path,
    )

    eb = exact_native_expectation(n=n, order=r0, stage_bits=stage_bits, shots_per_stage=shots_per_stage, compile_table=baseline_table)
    et = exact_native_expectation(n=n, order=r1, stage_bits=stage_bits, shots_per_stage=shots_per_stage, compile_table=transformed_table)

    stage_ratios = {}
    for m in stage_bits:
        bb = result["compile_tables"]["baseline"][str(m)]["best"]
        tt = result["compile_tables"][transformed_label][str(m)]["best"]
        stage_ratios[str(m)] = {
            "baseline_cz": int(bb["cz"]),
            "transformed_cz": int(tt["cz"]),
            "cz_ratio_transformed_over_baseline": float(tt["cz"] / bb["cz"]) if bb["cz"] else None,
            "baseline_depth": int(bb["compiled_depth"]),
            "transformed_depth": int(tt["compiled_depth"]),
            "depth_ratio_transformed_over_baseline": float(tt["compiled_depth"] / bb["compiled_depth"]) if bb["compiled_depth"] else None,
        }

    cz_ratio = et["expected_native_cz_per_attempted_session"] / eb["expected_native_cz_per_attempted_session"]
    depth_ratio = et["expected_compiled_depth_per_attempted_session"] / eb["expected_compiled_depth_per_attempted_session"]
    phase_ratio = et["expected_phase_rounds_per_attempted_session"] / eb["expected_phase_rounds_per_attempted_session"]

    result["exact_native_expectation"] = {
        "baseline": eb,
        transformed_label: et,
        "comparison": {
            "phase_round_ratio_transformed_over_baseline": float(phase_ratio),
            "phase_round_reduction_fraction": float(1.0 - phase_ratio),
            "native_cz_ratio_transformed_over_baseline": float(cz_ratio),
            "native_cz_reduction_fraction": float(1.0 - cz_ratio),
            "compiled_depth_ratio_transformed_over_baseline": float(depth_ratio),
            "compiled_depth_reduction_fraction": float(1.0 - depth_ratio),
        },
    }
    result["stage_cost_ratios"] = stage_ratios
    result["completed"] = True
    out_path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    comp = result["exact_native_expectation"]["comparison"]
    print("\n===== NATIVE-COST SUMMARY =====")
    print(f"N={n} ell={case['ell']} phase ratio={comp['phase_round_ratio_transformed_over_baseline']:.4f} (reduction={100*comp['phase_round_reduction_fraction']:.2f}%)")
    print(f"native CZ ratio={comp['native_cz_ratio_transformed_over_baseline']:.4f} (reduction={100*comp['native_cz_reduction_fraction']:.2f}%)")
    print(f"compiled-depth ratio={comp['compiled_depth_ratio_transformed_over_baseline']:.4f} (reduction={100*comp['compiled_depth_reduction_fraction']:.2f}%)")
    print(f"success by cap baseline/transformed={eb['success_probability_by_cap']:.6f}/{et['success_probability_by_cap']:.6f}")
    print(f"wrote {out_path}")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Zero-QPU IBM-target cost preflight for N=713/N=781 residue-RSA cases")
    ap.add_argument("--case", choices=["713", "781", "all"], default="713")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--profile", default="1_clean_kg24")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seeds", default="8776")
    ap.add_argument("--start-bits", type=int, default=4)
    ap.add_argument("--step-bits", type=int, default=2)
    ap.add_argument("--shots-per-stage", type=int, default=4)
    ap.add_argument("--outdir", type=Path, default=Path("results/dark_star_ptp"))
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("provide at least one transpiler seed")

    service = ibm_base.make_service()
    max_required = max(1 + CASES[k]["N"].bit_length() + legacy.SCRATCH_BITS for k in ("713", "781"))
    backend = ibm_base.select_backend(service, max_required, args.backend)
    use_measure2 = ibm_base.backend_has_measure2(backend)

    print(f"backend={backend.name} qubits={backend.num_qubits} measure_2={use_measure2}")
    print("ZERO-QPU PREFLIGHT: no Sampler call exists in this script; no QPU job will be submitted.")

    keys = ["713", "781"] if args.case == "all" else [args.case]
    summaries = {}
    for key in keys:
        result = run_case(
            key, backend=backend, use_measure2=use_measure2, profile=args.profile,
            level=args.optimization_level, seeds=seeds, start_bits=args.start_bits,
            step_bits=args.step_bits, shots_per_stage=args.shots_per_stage, outdir=args.outdir,
        )
        summaries[key] = result["exact_native_expectation"]["comparison"]

    print("\n===== OVERALL =====")
    print(json.dumps({"zero_qpu": True, "backend": backend.name, "cases": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
