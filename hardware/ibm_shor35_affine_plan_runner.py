#!/usr/bin/env python3
"""Run affine N=35 Shor with a frozen optimizer-selected matched layout.

This script is intentionally separate from ibm_shor35_affine_matched.py so the
replicated baseline runner remains unchanged for provenance.

Workflow:
  1. Run ibm_shor35_layout_optimizer.py (zero QPU cost).
  2. Pass its JSON file here with --plan-file.
  3. Use --transpile-only to verify exact resource counts.
  4. Add --run only when ready to submit the matched QPU job.
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

SCRIPT_REVISION = "2026-09-14-shor35-affine-plan-runner-v1"


def compile_with_seed(circuit, backend, level, layout, seed):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=int(level),
        seed_transpiler=int(seed),
        initial_layout=list(layout),
    )
    return pm.run(circuit)


def load_selection(path: Path, key: str):
    data = json.loads(path.read_text())
    if key not in data:
        raise SystemExit(f"Selection {key!r} not present in {path}")
    sel = data[key]
    if "plan" not in sel or "seed" not in sel:
        raise SystemExit(f"Selection {key!r} lacks plan/seed")
    return data, sel


def main():
    ap = argparse.ArgumentParser(description="Run affine Shor35 with optimizer-selected layout.")
    ap.add_argument("--plan-file", type=Path, required=True)
    ap.add_argument(
        "--selection",
        default="recommended_matched",
        choices=["recommended_matched", "recommended_recycled_primary", "recommended_wide_primary"],
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--shots", type=int, default=512)
    ap.add_argument("--max-execution-time", type=int, default=120)
    ap.add_argument("--transpile-only", action="store_true")
    ap.add_argument("--run", action="store_true", help="Actually submit the QPU job")
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor35_optimized"))
    args = ap.parse_args()

    search, selected = load_selection(args.plan_file, args.selection)
    phase_bits = int(search["phase_bits"])
    level = int(search["optimization_level"])
    seed = int(selected["seed"])
    plan = selected["plan"]

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
    cr = compile_with_seed(
        recycled, backend, level, plan["recycled_initial_layout"], seed
    )
    cw = compile_with_seed(
        wide, backend, level, plan["wide_initial_layout"], seed
    )
    stats = [
        ref.stats(recycled, cr, "recycled", plan["recycled_initial_layout"]),
        ref.stats(wide, cw, "wide", plan["wide_initial_layout"]),
    ]

    print("Script revision:", SCRIPT_REVISION)
    print("Optimizer source:", args.plan_file)
    print("Selection:", args.selection)
    print("Backend:", backend.name)
    print("Phase bits:", phase_bits)
    print("Optimization level:", level)
    print("Transpiler seed:", seed)
    print("Selected matched plan:")
    print(json.dumps(plan, indent=2, default=str))
    print("Transpiled stats:")
    print(json.dumps(stats, indent=2, default=str))

    out_base = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "optimizer_source_file": str(args.plan_file),
        "optimizer_selection": args.selection,
        "optimizer_script_revision": search.get("script_revision"),
        "backend": backend.name,
        "N": aff.N,
        "a": aff.A,
        "true_order_for_validation_only": aff.ORDER,
        "phase_bits": phase_bits,
        "shots": args.shots,
        "optimization_level": level,
        "seed_transpiler": seed,
        "encoding": "affine_12_cycle_plus_4_cycle",
        "same_job": True,
        "same_initial_work_register": True,
        "selected_plan": plan,
        "transpiled_stats": stats,
        "ideal_reference": ref.ideal_metrics(phase_bits),
        "account_usage_before": before,
        "scope_note": (
            "Optimizer-selected physical placement for the exact compiled affine N=35,a=2 orbit. "
            "This remains a compiled-orbit experiment, not a generic modular multiplier."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.transpile_only or not args.run:
        path = args.outdir / f"ibm_shor35_affine_optimized_transpile_{phase_bits}b.json"
        path.write_text(json.dumps(out_base, indent=2, default=str) + "\n")
        print("No QPU job submitted. Use --run after reviewing this preflight.")
        print("Saved:", path.resolve())
        return

    print(f"Submitting optimized recycled + wide together: 2 circuits x {args.shots} shots...")
    sampler = SamplerV2(mode=backend, options={"max_execution_time": args.max_execution_time})
    job = sampler.run([cr, cw], shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    results = []
    for pub, kind in zip(pubs, ("recycled", "wide")):
        counts = getattr(pub.data, "phase").get_counts()
        results.append({
            "kind": kind,
            "counts": counts,
            "analysis": ref.analyze_counts(counts, phase_bits),
            "distribution": ref.distribution_metrics(counts, phase_bits),
        })

    out = {
        **out_base,
        "job_id": job.job_id(),
        "metrics": ref.ibm_base.safe_metrics(job),
        "results": results,
        "paired_comparison": ref.comparison(results, phase_bits),
        "account_usage_after": ref.ibm_base.safe_usage(service),
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"ibm_shor35_affine_optimized_{phase_bits}b_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nRESULT")
    print(json.dumps(out, indent=2, default=str))
    print("\nSaved:", path.resolve())
    print("PAIRED:", json.dumps(out["paired_comparison"], sort_keys=True))


if __name__ == "__main__":
    main()
