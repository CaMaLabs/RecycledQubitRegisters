#!/usr/bin/env python3
"""Zero-QPU-cost placement/routing search for affine N=35 Shor benchmarks.

The replicated 8-bit N=35 result established the unmodified baseline.  This
script starts the *next* experiment: search physical placement and transpiler
seed choices without submitting a QPU job.

Design goals:
- preserve the fair matched comparison: wide and recycled start with the same
  four physical work-register sites;
- use one of the wide phase sites as the recycled MCM ancilla;
- search multiple calibration-aware candidate patches;
- transpile the *actual* affine circuits at the requested optimization level;
- rank candidates using measured CZ calibration, MCM calibration, compiled CZ
  burden, depth, and size;
- report both a balanced matched recommendation and a recycled-primary
  recommendation.

The calibration score is a ranking proxy, NOT a predicted circuit fidelity.
No QPU job is submitted by this program.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import ibm_shor35_affine_matched as aff
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-shor35-layout-optimizer-v1"


def safe_neglog_success(error):
    if error is None:
        return 0.0
    e = min(max(float(error), 0.0), 0.999999)
    return -math.log1p(-e)


def graph_helpers(backend):
    _, und = ref.cz_graph(backend)
    if not und:
        raise RuntimeError("Backend exposes no CZ connectivity graph")

    dist_cache = {}

    def dist(a, b):
        key = (int(a), int(b))
        if key in dist_cache:
            return dist_cache[key]
        q = deque([(int(a), 0)])
        seen = {int(a)}
        while q:
            u, d = q.popleft()
            if u == int(b):
                dist_cache[(a, b)] = dist_cache[(b, a)] = d
                return d
            for v in und.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    q.append((v, d + 1))
        return 999

    def edge_error(a, b):
        vals = []
        for pair in ((a, b), (b, a)):
            p = ref.inst_props(backend, "cz", pair)
            if p["error"] is not None:
                vals.append(float(p["error"]))
        return min(vals) if vals else 1.0

    def mcm_error(q):
        p = ref.inst_props(backend, "measure_2", (q,))
        if p["error"] is not None:
            return float(p["error"])
        p = ref.inst_props(backend, "measure", (q,))
        return float(p["error"]) if p["error"] is not None else 1.0

    def mcm_duration(q):
        p = ref.inst_props(backend, "measure_2", (q,))
        if p["duration_s"] is not None:
            return float(p["duration_s"])
        p = ref.inst_props(backend, "measure", (q,))
        return float(p["duration_s"]) if p["duration_s"] is not None else 1.0

    return und, dist, edge_error, mcm_error, mcm_duration


def affine_work_weights(phase_bits: int):
    """Interaction frequency among the four encoded work bits."""
    weights = {}
    for k in range(phase_bits):
        delta = aff.delta_for_power(k)
        cnots, _ = aff.POWER_NETWORKS[delta]
        for c, t in cnots:
            key = tuple(sorted((int(c), int(t))))
            weights[key] = weights.get(key, 0) + 1
    return weights


def enumerate_candidate_plans(backend, phase_bits: int, ancilla_pool: int, limit: int):
    region_size = phase_bits + aff.WORK_BITS
    und, dist, edge_error, mcm_error, mcm_duration = graph_helpers(backend)
    work_weights = affine_work_weights(phase_bits)

    ancillas = sorted(und, key=lambda q: (mcm_error(q), mcm_duration(q)))[:ancilla_pool]
    candidates = []

    for anc in ancillas:
        # Build a compact calibration-aware connected patch around this MCM site.
        region = [anc]
        while len(region) < region_size:
            frontier = []
            seen = set()
            for u in region:
                for v in und.get(u, ()):
                    if v in region or v in seen:
                        continue
                    seen.add(v)
                    # Prefer good edge calibration and nodes that touch more of
                    # the existing patch (helps later CCX/QFT routing).
                    touches = sum(1 for x in region if v in und.get(x, ()))
                    frontier.append((edge_error(u, v) - 0.00025 * touches, v))
            if not frontier:
                break
            frontier.sort()
            region.append(frontier[0][1])
        if len(region) != region_size:
            continue

        others = [q for q in region if q != anc]
        best_work = None
        # Exact search over ordered 4-tuples.  At 8 phase bits this is only
        # 11P4 = 7920 choices per candidate ancilla.
        for work_tuple in itertools.permutations(others, aff.WORK_BITS):
            work = list(work_tuple)
            weighted_work_distance = 0.0
            for (i, j), weight in work_weights.items():
                weighted_work_distance += weight * dist(work[i], work[j])

            # Recycled ancilla controls every affine round; keep it close to
            # the most-used work bits.
            anc_control = 0.0
            for k in range(phase_bits):
                delta = aff.delta_for_power(k)
                cnots, xbits = aff.POWER_NETWORKS[delta]
                touched = set(itertools.chain.from_iterable(cnots)) | set(xbits)
                anc_control += sum(dist(anc, work[i]) for i in touched)

            local = weighted_work_distance + 0.35 * anc_control
            if best_work is None or local < best_work[0]:
                best_work = (local, work)

        if best_work is None:
            continue
        _, work = best_work
        leftover = [q for q in others if q not in work]

        # Assign wide phase sites to phase indices.  The ancilla is included
        # as one of the wide phase sites, preserving the matched-region design.
        phase_sites = [anc] + leftover
        # Greedy assignment by actual affine control demand for each k.
        remaining = set(phase_sites)
        phases = [None] * phase_bits
        phase_order = sorted(
            range(phase_bits),
            key=lambda k: -len(aff.POWER_NETWORKS[aff.delta_for_power(k)][0]),
        )
        for k in phase_order:
            delta = aff.delta_for_power(k)
            cnots, xbits = aff.POWER_NETWORKS[delta]
            touched = set(itertools.chain.from_iterable(cnots)) | set(xbits)
            site = min(
                remaining,
                key=lambda p: sum(dist(p, work[i]) for i in touched),
            )
            phases[k] = site
            remaining.remove(site)

        local_errors = []
        for u in region:
            for v in und.get(u, ()):
                if v in region and u < v:
                    local_errors.append(edge_error(u, v))
        local_mean = sum(local_errors) / len(local_errors) if local_errors else 1.0

        heuristic = (
            best_work[0]
            + 400.0 * mcm_error(anc)
            + 30.0 * local_mean
            + 0.02 * (mcm_duration(anc) / 1e-6)
        )
        candidates.append({
            "heuristic_score": float(heuristic),
            "region": list(map(int, region)),
            "phase_bits": int(phase_bits),
            "shared_initial_work_physical": list(map(int, work)),
            "recycled_ancilla_physical": int(anc),
            "wide_phase_physical": list(map(int, phases)),
            "recycled_initial_layout": [int(anc)] + list(map(int, work)),
            "wide_initial_layout": list(map(int, phases)) + list(map(int, work)),
            "ancilla_measure_2": ref.inst_props(backend, "measure_2", (anc,)),
            "ancilla_measure": ref.inst_props(backend, "measure", (anc,)),
            "local_mean_cz_error": float(local_mean),
        })

    # Ensure the legacy plan is present as a baseline candidate.
    baseline = ref.choose_shared_plan(backend, phase_bits)
    baseline = {**baseline, "heuristic_score": float(baseline.get("score", 0.0))}
    candidates.append(baseline)

    # Deduplicate identical requested layouts and keep best heuristic instance.
    dedup = {}
    for p in candidates:
        key = (tuple(p["recycled_initial_layout"]), tuple(p["wide_initial_layout"]))
        if key not in dedup or p["heuristic_score"] < dedup[key]["heuristic_score"]:
            dedup[key] = p
    out = sorted(dedup.values(), key=lambda p: p["heuristic_score"])
    return out[:limit], baseline


def compile_with_seed(circuit, backend, level: int, layout, seed: int):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=level,
        seed_transpiler=int(seed),
        initial_layout=list(layout),
    )
    return pm.run(circuit)


def cz_calibration_cost(compiled, backend):
    neglog = 0.0
    count = 0
    errors = []
    for item in compiled.data:
        op = item.operation
        if op.name != "cz":
            continue
        qids = tuple(compiled.find_bit(q).index for q in item.qubits)
        p = ref.inst_props(backend, "cz", qids)
        if p["error"] is None and len(qids) == 2:
            p = ref.inst_props(backend, "cz", tuple(reversed(qids)))
        e = p["error"]
        if e is not None:
            e = float(e)
            errors.append(e)
            neglog += safe_neglog_success(e)
        count += 1
    return {
        "cz_count_walked": count,
        "cz_neglog_success_proxy": neglog,
        "cz_mean_error_walked": (sum(errors) / len(errors)) if errors else None,
        "cz_max_error_walked": max(errors) if errors else None,
    }


def measure_error(backend, q, prefer_measure2=False):
    names = ("measure_2", "measure") if prefer_measure2 else ("measure", "measure_2")
    for name in names:
        p = ref.inst_props(backend, name, (int(q),))
        if p["error"] is not None:
            return float(p["error"])
    return None


def evaluate_one(plan, seed, recycled, wide, backend, level, phase_bits):
    cr = compile_with_seed(recycled, backend, level, plan["recycled_initial_layout"], seed)
    cw = compile_with_seed(wide, backend, level, plan["wide_initial_layout"], seed)
    sr = ref.stats(recycled, cr, "recycled", plan["recycled_initial_layout"])
    sw = ref.stats(wide, cw, "wide", plan["wide_initial_layout"])
    zr = cz_calibration_cost(cr, backend)
    zw = cz_calibration_cost(cw, backend)

    mcm_e = measure_error(backend, plan["recycled_ancilla_physical"], prefer_measure2=True)
    mcm_loss = phase_bits * safe_neglog_success(mcm_e)

    # Wide readout proxy uses its requested final phase sites.  Routing can move
    # states, so this is deliberately labeled as an initial-layout proxy.
    wide_measure_errors = [measure_error(backend, q, False) for q in plan["wide_phase_physical"]]
    wide_measure_loss = sum(safe_neglog_success(e) for e in wide_measure_errors)

    r_ops = sr["count_ops"]
    w_ops = sw["count_ops"]
    r_cz = int(r_ops.get("cz", 0))
    w_cz = int(w_ops.get("cz", 0))

    # Calibration-weighted ranking proxy.  CZ and measurement error are the
    # physically meaningful terms; small depth/size penalties break close ties.
    r_proxy = (
        zr["cz_neglog_success_proxy"]
        + mcm_loss
        + 0.00020 * sr["depth"]
        + 0.00002 * sr["size"]
    )
    w_proxy = (
        zw["cz_neglog_success_proxy"]
        + wide_measure_loss
        + 0.00020 * sw["depth"]
        + 0.00002 * sw["size"]
    )
    balanced = r_proxy + w_proxy + 0.15 * max(r_proxy, w_proxy)

    return {
        "seed": int(seed),
        "plan": plan,
        "recycled": {**sr, **zr, "ranking_proxy_cost": r_proxy, "mcm_error_proxy": mcm_e},
        "wide": {**sw, **zw, "ranking_proxy_cost": w_proxy, "readout_errors_proxy": wide_measure_errors},
        "balanced_proxy_cost": balanced,
        "total_cz": r_cz + w_cz,
        "total_depth": sr["depth"] + sw["depth"],
        "total_size": sr["size"] + sw["size"],
    }


def compact_result(row):
    return {
        "seed": row["seed"],
        "balanced_proxy_cost": row["balanced_proxy_cost"],
        "total_cz": row["total_cz"],
        "total_depth": row["total_depth"],
        "plan": row["plan"],
        "recycled": row["recycled"],
        "wide": row["wide"],
    }


def main():
    ap = argparse.ArgumentParser(description="Calibration-aware layout search for affine N=35 Shor.")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=8)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--candidate-plans", type=int, default=12)
    ap.add_argument("--ancilla-pool", type=int, default=32)
    ap.add_argument("--seeds", default="8776,20260914,314159")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor35_optimizer"))
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if not seeds:
        raise SystemExit("Provide at least one transpiler seed")

    test = aff.self_test_affine_encoding()
    if not test["pass"]:
        raise SystemExit("Affine self-test failed; refusing placement optimization")

    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(
        service, aff.WORK_BITS + args.phase_bits, args.backend
    )
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)
    recycled = aff.build_recycled(args.phase_bits, use_measure2)
    wide = aff.build_wide(args.phase_bits)

    plans, baseline_plan = enumerate_candidate_plans(
        backend, args.phase_bits, args.ancilla_pool, args.candidate_plans
    )

    print(f"Script revision: {SCRIPT_REVISION}")
    print(f"Backend: {backend.name} | phase_bits={args.phase_bits} | measure_2={use_measure2}")
    print(f"Candidate matched plans: {len(plans)} | seeds per plan: {len(seeds)}")
    print("No QPU job will be submitted.")

    rows = []
    for i, plan in enumerate(plans, 1):
        print(f"[{i}/{len(plans)}] ancilla={plan['recycled_ancilla_physical']} work={plan['shared_initial_work_physical']}")
        for seed in seeds:
            row = evaluate_one(
                plan, seed, recycled, wide, backend,
                args.optimization_level, args.phase_bits,
            )
            rows.append(row)
            print(
                f"  seed={seed} rCZ={row['recycled']['count_ops'].get('cz',0)} "
                f"wCZ={row['wide']['count_ops'].get('cz',0)} "
                f"rD={row['recycled']['depth']} wD={row['wide']['depth']} "
                f"score={row['balanced_proxy_cost']:.6f}"
            )

    if not rows:
        raise SystemExit("No candidate transpiles completed")

    matched = min(rows, key=lambda r: (r["balanced_proxy_cost"], r["total_cz"], r["total_depth"]))
    recycled_best = min(
        rows,
        key=lambda r: (
            r["recycled"]["ranking_proxy_cost"],
            r["recycled"]["count_ops"].get("cz", 0),
            r["recycled"]["depth"],
        ),
    )
    wide_best = min(
        rows,
        key=lambda r: (
            r["wide"]["ranking_proxy_cost"],
            r["wide"]["count_ops"].get("cz", 0),
            r["wide"]["depth"],
        ),
    )
    top = sorted(rows, key=lambda r: (r["balanced_proxy_cost"], r["total_cz"]))[:args.top]

    # Compile the legacy heuristic plan with the historical seed for an explicit
    # apples-to-apples zero-QPU baseline in the same calibration snapshot.
    baseline_eval = evaluate_one(
        baseline_plan, 8776, recycled, wide, backend,
        args.optimization_level, args.phase_bits,
    )

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "phase_bits": args.phase_bits,
        "optimization_level": args.optimization_level,
        "seeds": seeds,
        "candidate_plan_count": len(plans),
        "ranking_note": (
            "Calibration-weighted placement/transpile ranking proxy only; not a predicted fidelity. "
            "All searches are zero-QPU-cost and preserve the same initial four work qubits across wide/recycled within each matched plan."
        ),
        "baseline_legacy_plan_seed8776": compact_result(baseline_eval),
        "recommended_matched": compact_result(matched),
        "recommended_recycled_primary": compact_result(recycled_best),
        "recommended_wide_primary": compact_result(wide_best),
        "top_matched": [compact_result(r) for r in top],
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"shor35_layout_search_{args.phase_bits}b_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")

    print("\nRECOMMENDED MATCHED PLAN")
    print(json.dumps(out["recommended_matched"], indent=2, default=str))
    print("\nLEGACY BASELINE IN CURRENT CALIBRATION")
    print(json.dumps(out["baseline_legacy_plan_seed8776"], indent=2, default=str))
    print("\nSaved:", path.resolve())
    print("PLAN_FILE:", path)


if __name__ == "__main__":
    main()
