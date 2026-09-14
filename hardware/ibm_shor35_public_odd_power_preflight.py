#!/usr/bin/env python3
"""Zero-QPU N=35 preflight for public odd-power Shor base preconditioning.

The previous Dark-Star/PTP constraint audit found an exact public condition:
for semiprimes coprime to 3, N mod 3 == 2 forces 3 | lambda(N).  This script
tests the factor-independent preprocessing rule

    b = a^3 mod N

for the existing generic full-register N=35 circuit.

For N=35 and seed base a=2 this gives b=8.  The constructor receives only N,
the transformed base b, and the QPE bit index.  It is not supplied the
multiplicative order or a reachable-orbit encoding.  The true order is computed
after construction only as a validation/reporting label.

This is a compiler-only experiment and NEVER submits a QPU job.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import ibm_shor35_generic_permutation_direct_transposition as direct
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-n35-public-odd-power-precondition-v1"


def brute_order(a: int, n: int) -> int:
    if math.gcd(a, n) != 1:
        raise ValueError("base must be coprime to N")
    x = 1
    for r in range(1, n * n + 1):
        x = (x * a) % n
        if x == 1:
            return r
    raise RuntimeError("order search bound unexpectedly exhausted")


def compact_stats(row: dict) -> dict:
    keys = (
        "logical_qubits",
        "compiled_qubits",
        "compiled_depth",
        "compiled_size",
        "cz",
        "measure",
        "measure_2",
        "reset",
        "if_else",
        "compile_seconds",
    )
    return {k: row.get(k) for k in keys}


def build_for_base(base_value: int, phase_bits: int, kind: str, use_measure2: bool):
    direct.A = int(base_value)
    semantic = direct.semantic_summary(phase_bits)
    if not semantic["pass"]:
        raise RuntimeError(f"semantic validation failed for base={base_value}")
    if kind == "recycled":
        qc, rounds = direct.build_recycled(phase_bits, use_measure2)
    elif kind == "wide":
        qc, rounds = direct.build_wide(phase_bits)
    else:
        raise ValueError(kind)
    return qc, rounds, semantic


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU N=35 public odd-power base-preconditioning preflight"
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--seed-base", type=int, default=2)
    ap.add_argument("--exponent", type=int, default=3)
    ap.add_argument("--phase-bits", nargs="+", type=int, default=[4, 6, 8])
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="recycled")
    ap.add_argument("--profile", default="1_clean_kg24")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seeds", default="2026,8776,9401")
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor35_generic_permutation"),
    )
    args = ap.parse_args()

    if args.exponent < 1 or args.exponent % 2 == 0:
        raise SystemExit("--exponent must be a positive odd integer")
    bits_list = sorted(set(args.phase_bits))
    if not bits_list or bits_list[0] < 1:
        raise SystemExit("phase bits must be >= 1")
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("provide at least one transpiler seed")

    n = direct.N
    seed_base = args.seed_base % n
    if math.gcd(seed_base, n) != 1:
        g = math.gcd(seed_base, n)
        raise SystemExit(f"seed base already exposes factor gcd={g}")
    transformed_base = pow(seed_base, args.exponent, n)

    kinds = ["recycled", "wide"] if args.kind == "both" else [args.kind]
    max_width = direct.WORK_BITS + direct.SCRATCH_BITS + (
        max(bits_list) if "wide" in kinds else 1
    )

    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, max_width, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    bases = []
    if not args.skip_baseline:
        bases.append(("baseline", seed_base))
    bases.append(("preconditioned", transformed_base))

    receipt = {
        "experiment": "n35_public_odd_power_precondition_preflight_v1",
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "backend": backend.name,
        "N": n,
        "seed_base": seed_base,
        "public_exponent": args.exponent,
        "transformed_base": transformed_base,
        "public_condition_N_mod_3_eq_2": n % 3 == 2,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "construction": "full_residue_permutation_from_N_and_transformed_base",
        "validation_orders": {
            "seed_base": brute_order(seed_base, n),
            "transformed_base": brute_order(transformed_base, n),
        },
        "profile": args.profile,
        "optimization_level": args.optimization_level,
        "seeds": seeds,
        "phase_bits": bits_list,
        "kinds": kinds,
        "rows": [],
    }

    print(f"backend={backend.name} measure_2={use_measure2}")
    print(
        f"N={n} seed_base={seed_base} odd_exponent={args.exponent} "
        f"transformed_base={transformed_base}"
    )
    print(
        "orders are validation-only: "
        f"{receipt['validation_orders']['seed_base']} -> "
        f"{receipt['validation_orders']['transformed_base']}"
    )
    print("PUBLIC-POWER PRECONDITION PATH: NO QPU JOBS WILL BE SUBMITTED.")

    for label, base_value in bases:
        for bits in bits_list:
            for kind in kinds:
                qc, rounds, semantic = build_for_base(
                    base_value, bits, kind, use_measure2
                )
                multipliers = [int(r.get("multiplier")) for r in rounds]
                direct_mcx = [
                    int(r.get("direct_mcx", r.get("high_level_mcx", 0)))
                    for r in rounds
                ]
                basis_cx = [int(r.get("basis_change_cx", 0)) for r in rounds]
                print(
                    f"\n=== {label} base={base_value} bits={bits} kind={kind} ==="
                )
                print(
                    json.dumps(
                        {
                            "logical_qubits": qc.num_qubits,
                            "round_multipliers": multipliers,
                            "direct_mcx_by_round": direct_mcx,
                            "basis_change_cx_by_round": basis_cx,
                            "semantic_pass": semantic["pass"],
                        },
                        indent=2,
                    )
                )

                for seed in seeds:
                    print(
                        f"compile label={label} bits={bits} kind={kind} "
                        f"profile={args.profile} level={args.optimization_level} seed={seed}"
                    )
                    try:
                        stats = direct.compile_one(
                            qc,
                            backend,
                            args.profile,
                            args.optimization_level,
                            seed,
                        )
                        row = {
                            "success": True,
                            "label": label,
                            "base": base_value,
                            "validation_order": brute_order(base_value, n),
                            "phase_bits": bits,
                            "kind": kind,
                            "profile": args.profile,
                            "optimization_level": args.optimization_level,
                            "seed_transpiler": seed,
                            "order_used_in_circuit_construction": False,
                            "orbit_encoding_used": False,
                            "round_multipliers": multipliers,
                            "direct_mcx_by_round": direct_mcx,
                            "basis_change_cx_by_round": basis_cx,
                            **stats,
                        }
                    except Exception as exc:
                        row = {
                            "success": False,
                            "label": label,
                            "base": base_value,
                            "phase_bits": bits,
                            "kind": kind,
                            "profile": args.profile,
                            "optimization_level": args.optimization_level,
                            "seed_transpiler": seed,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    receipt["rows"].append(row)
                    print(json.dumps(row, indent=2, default=str))

    successful = [r for r in receipt["rows"] if r.get("success")]
    best = {}
    for label, _ in bases:
        for bits in bits_list:
            for kind in kinds:
                group = [
                    r
                    for r in successful
                    if r["label"] == label
                    and r["phase_bits"] == bits
                    and r["kind"] == kind
                ]
                if not group:
                    continue
                key = f"{label}_{bits}b_{kind}"
                best[key] = min(
                    group,
                    key=lambda r: (
                        int(r.get("cz", 10**18)),
                        int(r.get("compiled_depth", 10**18)),
                        int(r.get("compiled_size", 10**18)),
                    ),
                )

    receipt["best"] = best
    comparisons = {}
    if not args.skip_baseline:
        for bits in bits_list:
            for kind in kinds:
                kb = f"baseline_{bits}b_{kind}"
                kp = f"preconditioned_{bits}b_{kind}"
                if kb not in best or kp not in best:
                    continue
                b0 = best[kb]
                b1 = best[kp]
                comparisons[f"{bits}b_{kind}"] = {
                    "baseline_cz": b0["cz"],
                    "preconditioned_cz": b1["cz"],
                    "cz_reduction_fraction": (
                        (b0["cz"] - b1["cz"]) / b0["cz"] if b0["cz"] else None
                    ),
                    "baseline_depth": b0["compiled_depth"],
                    "preconditioned_depth": b1["compiled_depth"],
                    "depth_reduction_fraction": (
                        (b0["compiled_depth"] - b1["compiled_depth"])
                        / b0["compiled_depth"]
                        if b0["compiled_depth"] else None
                    ),
                    "baseline_logical_qubits": b0["logical_qubits"],
                    "preconditioned_logical_qubits": b1["logical_qubits"],
                }
    receipt["comparisons"] = comparisons

    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = args.outdir / f"n35_public_odd_power_preflight_{stamp}.json"
    out.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")

    print("\n===== BEST PUBLIC-POWER PRECONDITION RESULTS =====")
    print(
        json.dumps(
            {
                k: compact_stats(v)
                | {"base": v["base"], "validation_order": v["validation_order"]}
                for k, v in best.items()
            },
            indent=2,
        )
    )
    print("\n===== PRECONDITION COMPARISON =====")
    print(json.dumps(comparisons, indent=2))
    print(f"\nsaved={out.resolve()}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
