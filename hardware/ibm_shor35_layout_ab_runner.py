#!/usr/bin/env python3
"""Same-job legacy-vs-optimized layout A/B for affine N=35 Shor.

This control submits four circuits in one SamplerV2 job:
  1. legacy recycled
  2. legacy wide
  3. optimized recycled
  4. optimized wide

The goal is to distinguish placement effects from backend/calibration drift after
separate Marrakesh runs showed substantial temporal variation.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2

import ibm_shor35_affine_matched as aff
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-shor35-layout-ab-v1"


def compile_with_seed(circuit, backend, level, layout, seed):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=int(level),
        seed_transpiler=int(seed),
        initial_layout=list(layout),
    )
    return pm.run(circuit)


def require_selection(search, key):
    if key not in search:
        raise SystemExit(f"Missing selection {key!r} in optimizer JSON")
    sel = search[key]
    if "plan" not in sel or "seed" not in sel:
        raise SystemExit(f"Selection {key!r} lacks plan/seed")
    return sel


def result_row(pub, kind, phase_bits):
    counts = getattr(pub.data, "phase").get_counts()
    return {
        "kind": kind,
        "counts": counts,
        "analysis": ref.analyze_counts(counts, phase_bits),
        "distribution": ref.distribution_metrics(counts, phase_bits),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Same-job legacy-vs-optimized placement A/B for affine Shor35."
    )
    ap.add_argument("--plan-file", type=Path, required=True)
    ap.add_argument("--backend", default="ibm_marrakesh")
    ap.add_argument("--shots", type=int, default=512)
    ap.add_argument("--max-execution-time", type=int, default=120)
    ap.add_argument("--transpile-only", action="store_true")
    ap.add_argument("--run", action="store_true", help="Actually submit the 4-circuit QPU job")
    ap.add_argument(
        "--outdir", type=Path, default=Path("results/ibm_shor35_layout_ab")
    )
    args = ap.parse_args()

    search = json.loads(args.plan_file.read_text())
    legacy = require_selection(search, "baseline_legacy_plan_seed8776")
    optimized = require_selection(search, "recommended_matched")

    phase_bits = int(search["phase_bits"])
    level = int(search["optimization_level"])

    test = aff.self_test_affine_encoding()
    if not test["pass"]:
        raise SystemExit("Affine encoding self-test failed")

    service = ref.ibm_base.make_service()
    before = ref.ibm_base.safe_usage(service)
    backend = ref.ibm_base.select_backend(
        service, aff.WORK_BITS + phase_bits, args.backend
    )
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    recycled = aff.build_recycled(phase_bits, use_measure2)
    wide = aff.build_wide(phase_bits)

    compiled = []
    stats = []
    specs = [
        ("legacy_recycled", recycled, legacy["plan"]["recycled_initial_layout"], legacy["seed"]),
        ("legacy_wide", wide, legacy["plan"]["wide_initial_layout"], legacy["seed"]),
        ("optimized_recycled", recycled, optimized["plan"]["recycled_initial_layout"], optimized["seed"]),
        ("optimized_wide", wide, optimized["plan"]["wide_initial_layout"], optimized["seed"]),
    ]

    for kind, circuit, layout, seed in specs:
        c = compile_with_seed(circuit, backend, level, layout, seed)
        compiled.append(c)
        base_kind = "recycled" if kind.endswith("recycled") else "wide"
        s = ref.stats(circuit, c, base_kind, layout)
        s["kind"] = kind
        s["seed_transpiler"] = int(seed)
        stats.append(s)

    print("Script revision:", SCRIPT_REVISION)
    print("Optimizer source:", args.plan_file)
    print("Backend:", backend.name)
    print("Phase bits:", phase_bits)
    print("Optimization level:", level)
    print("measure_2:", use_measure2)
    print("Transpiled A/B stats:")
    print(json.dumps(stats, indent=2, default=str))

    out_base = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "optimizer_source_file": str(args.plan_file),
        "optimizer_script_revision": search.get("script_revision"),
        "backend": backend.name,
        "N": aff.N,
        "a": aff.A,
        "true_order_for_validation_only": aff.ORDER,
        "phase_bits": phase_bits,
        "shots": args.shots,
        "optimization_level": level,
        "same_job": True,
        "layout_ab": True,
        "circuit_order": [x[0] for x in specs],
        "legacy_selection": legacy,
        "optimized_selection": optimized,
        "transpiled_stats": stats,
        "ideal_reference": ref.ideal_metrics(phase_bits),
        "account_usage_before": before,
        "scope_note": (
            "Same-job legacy-vs-optimized physical-layout A/B for the exact compiled "
            "affine N=35,a=2,r=12 orbit. This controls calibration-window drift but "
            "remains a compiled-orbit experiment, not a generic modular multiplier."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.transpile_only or not args.run:
        path = args.outdir / f"ibm_shor35_layout_ab_transpile_{phase_bits}b.json"
        path.write_text(json.dumps(out_base, indent=2, default=str) + "\n")
        print("No QPU job submitted. Add --run after reviewing this preflight.")
        print("Saved:", path.resolve())
        return

    print(f"Submitting same-job layout A/B: 4 circuits x {args.shots} shots...")
    sampler = SamplerV2(
        mode=backend, options={"max_execution_time": args.max_execution_time}
    )
    job = sampler.run(compiled, shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    results = [
        result_row(pub, kind, phase_bits)
        for pub, (kind, _, _, _) in zip(pubs, specs)
    ]

    legacy_pair = [results[0], results[1]]
    optimized_pair = [results[2], results[3]]
    out = {
        **out_base,
        "job_id": job.job_id(),
        "metrics": ref.ibm_base.safe_metrics(job),
        "results": results,
        "legacy_paired_comparison": ref.comparison(legacy_pair, phase_bits),
        "optimized_paired_comparison": ref.comparison(optimized_pair, phase_bits),
        "account_usage_after": ref.ibm_base.safe_usage(service),
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"ibm_shor35_layout_ab_{phase_bits}b_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")

    print("\nLEGACY PAIRED:")
    print(json.dumps(out["legacy_paired_comparison"], sort_keys=True))
    print("\nOPTIMIZED PAIRED:")
    print(json.dumps(out["optimized_paired_comparison"], sort_keys=True))
    print("\nSaved:", path.resolve())


if __name__ == "__main__":
    main()
