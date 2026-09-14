#!/usr/bin/env python3
"""Calibration-aware, zero-QPU layout search for the generic N=35 direct path.

This optimizer is for the order/orbit-independent full-register construction in
`ibm_shor35_generic_permutation_direct_transposition.py`.  It does not change
the modular permutation or the direct-transposition synthesis.  It only searches
physical placement and routing choices for the already-validated recycled
circuit.

The logical qubit order is

    phase/MCM ancilla, work[0:6], mcx_hls_scratch[0:4]

for 11 simultaneous logical qubits.  Candidate 11-node connected patches are
built around low-error MCM sites.  Work-register positions are assigned with a
small interaction-distance search; the remaining four sites are available as
clean HLS scratch.  Every candidate is then compiled as the *actual* circuit and
ranked using native CZ count/depth and a calibration-weighted error proxy.

The calibration proxy is a ranking heuristic, NOT a predicted circuit fidelity.
This program NEVER submits a QPU job.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler.passes.synthesis import HLSConfig
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

import ibm_shor35_generic_permutation_direct_transposition as direct
import ibm_shor35_layout_optimizer as layout_ref
import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-direct-layout-optimizer-v1"
LOGICAL_QUBITS = 1 + direct.WORK_BITS + direct.SCRATCH_BITS


def safe_neglog_success(error):
    if error is None:
        return 0.0
    e = min(max(float(error), 0.0), 0.999999)
    return -math.log1p(-e)


def grow_region(und, edge_error, ancilla: int, size: int) -> list[int] | None:
    """Greedily grow a compact, calibration-aware connected physical patch."""
    region = [int(ancilla)]
    while len(region) < size:
        candidates = []
        seen = set()
        for u in region:
            for v in und.get(u, ()):
                if v in region or v in seen:
                    continue
                seen.add(v)
                touches = sum(1 for x in region if v in und.get(x, ()))
                # Prefer good links and nodes that connect to more of the patch.
                score = edge_error(u, v) - 0.00030 * touches
                candidates.append((score, int(v)))
        if not candidates:
            return None
        candidates.sort()
        region.append(candidates[0][1])
    return region


def logical_work_pair_weights(phase_bits: int) -> tuple[dict[tuple[int, int], int], int]:
    """Count direct-basis CNOT pressure between the six logical work bits."""
    weights: dict[tuple[int, int], int] = {}
    total_mcx = 0
    for k in range(phase_bits):
        multiplier = pow(direct.A, 1 << k, direct.N)
        perm = direct.sweep.base.modular_permutation(multiplier)
        trans, _ = direct.direct_transpositions(perm)
        total_mcx += len(trans)
        for u, v in trans:
            diff = u ^ v
            choice = direct.choose_target_bit(u, v)
            target = int(choice["target_bit"])
            for j in range(direct.WORK_BITS):
                if j == target or not direct.bit(diff, j):
                    continue
                key = tuple(sorted((target, j)))
                # Fold and unfold each contribute one CNOT.
                weights[key] = weights.get(key, 0) + 2
    return weights, total_mcx


def best_work_mappings(region, anc, dist, pair_weights, total_mcx, keep=2):
    """Return a few low-distance assignments of six work bits inside a patch."""
    others = [int(q) for q in region if int(q) != int(anc)]
    if len(others) != direct.WORK_BITS + direct.SCRATCH_BITS:
        raise ValueError("candidate patch has wrong size")

    pair_items = list(pair_weights.items())
    best = []

    # 10 choose 6 times 6! = 151,200 assignments per MCM site: small enough for
    # N=35 and gives much more placement diversity than one greedy assignment.
    for work_set in itertools.combinations(others, direct.WORK_BITS):
        scratch = [q for q in others if q not in work_set]
        scratch_pressure = 0.0
        for s in scratch:
            local = [dist(s, anc)] + [dist(s, w) for w in work_set]
            scratch_pressure += sum(local) / len(local)

        for work in itertools.permutations(work_set):
            # Every six-control MCX contains the phase ancilla plus all work
            # bits.  Add a uniform phase/work compactness pressure, then the
            # exact high-level basis-change CNOT interaction pressure.
            score = 0.20 * total_mcx * sum(dist(anc, w) for w in work)
            for (i, j), weight in pair_items:
                score += weight * dist(work[i], work[j])
            score += 0.05 * total_mcx * scratch_pressure

            row = (float(score), list(map(int, work)), list(map(int, scratch)))
            if len(best) < keep:
                best.append(row)
                best.sort(key=lambda x: (x[0], x[1], x[2]))
            elif row[0] < best[-1][0]:
                best[-1] = row
                best.sort(key=lambda x: (x[0], x[1], x[2]))
    return best


def candidate_layouts(backend, phase_bits: int, ancilla_pool: int, limit: int):
    und, dist, edge_error, mcm_error, mcm_duration = layout_ref.graph_helpers(backend)
    pair_weights, total_mcx = logical_work_pair_weights(phase_bits)

    ancillas = sorted(
        und,
        key=lambda q: (mcm_error(q), mcm_duration(q), int(q)),
    )[:ancilla_pool]

    plans = []
    for anc in ancillas:
        region = grow_region(und, edge_error, int(anc), LOGICAL_QUBITS)
        if region is None:
            continue

        local_errors = []
        for u in region:
            for v in und.get(u, ()):
                if v in region and u < v:
                    local_errors.append(edge_error(u, v))
        local_mean = sum(local_errors) / len(local_errors) if local_errors else 1.0

        for map_score, work, scratch in best_work_mappings(
            region, int(anc), dist, pair_weights, total_mcx, keep=2
        ):
            # Circuit register order is phase, six work, four scratch.
            initial_layout = [int(anc)] + work + scratch
            heuristic = (
                map_score
                + 500.0 * mcm_error(anc)
                + 40.0 * local_mean
                + 0.02 * (mcm_duration(anc) / 1e-6)
            )
            plans.append(
                {
                    "heuristic_score": float(heuristic),
                    "mapping_distance_score": float(map_score),
                    "region": list(map(int, region)),
                    "recycled_ancilla_physical": int(anc),
                    "work_physical": work,
                    "scratch_physical": scratch,
                    "initial_layout": initial_layout,
                    "mcm_error": float(mcm_error(anc)),
                    "mcm_duration_s": float(mcm_duration(anc)),
                    "local_mean_cz_error": float(local_mean),
                }
            )

    dedup = {}
    for plan in plans:
        key = tuple(plan["initial_layout"])
        if key not in dedup or plan["heuristic_score"] < dedup[key]["heuristic_score"]:
            dedup[key] = plan
    return sorted(dedup.values(), key=lambda p: p["heuristic_score"])[:limit]


def hls_config(profile: str):
    if profile in ("auto", "none"):
        return None
    return HLSConfig(mcx=[profile])


def compile_one(qc, backend, profile: str, level: int, seed: int, initial_layout=None):
    kwargs = {
        "backend": backend,
        "optimization_level": int(level),
        "seed_transpiler": int(seed),
        "qubits_initially_zero": True,
    }
    hls = hls_config(profile)
    if hls is not None:
        kwargs["hls_config"] = hls
    if initial_layout is not None:
        kwargs["initial_layout"] = list(initial_layout)

    pm = generate_preset_pass_manager(**kwargs)
    t0 = time.perf_counter()
    compiled = pm.run(qc)
    elapsed = time.perf_counter() - t0
    return compiled, elapsed


def cz_calibration_cost(compiled, backend):
    neglog = 0.0
    errors = []
    missing = 0
    count = 0
    for item in compiled.data:
        if item.operation.name != "cz":
            continue
        qids = tuple(compiled.find_bit(q).index for q in item.qubits)
        p = ref.inst_props(backend, "cz", qids)
        if p["error"] is None and len(qids) == 2:
            p = ref.inst_props(backend, "cz", tuple(reversed(qids)))
        e = p["error"]
        count += 1
        if e is None:
            missing += 1
            continue
        e = float(e)
        errors.append(e)
        neglog += safe_neglog_success(e)
    return {
        "cz_count_walked": count,
        "cz_calibration_missing": missing,
        "cz_neglog_success_proxy": float(neglog),
        "cz_mean_error_walked": (sum(errors) / len(errors)) if errors else None,
        "cz_max_error_walked": max(errors) if errors else None,
    }


def measurement_cost(compiled, backend):
    events = []
    neglog = 0.0
    for item in compiled.data:
        name = item.operation.name
        if name not in ("measure_2", "measure"):
            continue
        q = compiled.find_bit(item.qubits[0]).index
        # Prefer the actual instruction calibration, with normal measurement as
        # fallback in case a backend does not expose measure_2 error metadata.
        p = ref.inst_props(backend, name, (q,))
        if p["error"] is None:
            p = ref.inst_props(backend, "measure", (q,))
        e = p["error"]
        e = None if e is None else float(e)
        if e is not None:
            neglog += safe_neglog_success(e)
        events.append({"instruction": name, "physical_qubit": int(q), "error": e})
    return {
        "measurement_events": events,
        "measurement_neglog_success_proxy": float(neglog),
    }


def evaluate(qc, compiled, elapsed, backend, plan, seed, profile, level):
    stat = direct.sweep.stats(qc, compiled, elapsed)
    cz = cz_calibration_cost(compiled, backend)
    meas = measurement_cost(compiled, backend)
    try:
        final_layout = list(map(int, compiled.layout.final_index_layout(filter_ancillas=True)))
    except Exception:
        final_layout = None

    proxy = (
        cz["cz_neglog_success_proxy"]
        + meas["measurement_neglog_success_proxy"]
        + 0.00010 * stat["compiled_depth"]
        + 0.00001 * stat["compiled_size"]
    )
    return {
        "success": True,
        "profile": profile,
        "optimization_level": int(level),
        "seed_transpiler": int(seed),
        "plan": plan,
        "final_index_layout": final_layout,
        **stat,
        **cz,
        **meas,
        "calibration_ranking_proxy": float(proxy),
        "proxy_note": "Ranking heuristic only; not a predicted circuit fidelity.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU calibration-aware layout search for generic direct N=35 Shor."
    )
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=6)
    ap.add_argument("--profile", default="1_clean_kg24")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seeds", default="2026,8776,9401")
    ap.add_argument("--candidate-plans", type=int, default=10)
    ap.add_argument("--ancilla-pool", type=int, default=16)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/ibm_shor35_generic_permutation"),
    )
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if args.phase_bits < 1 or not seeds:
        raise SystemExit("phase bits must be >=1 and at least one seed is required")

    semantic = direct.semantic_summary(args.phase_bits)
    if not semantic["pass"]:
        raise SystemExit("Direct-transposition semantic self-test failed; refusing layout search")

    service = ref.ibm_base.make_service()
    backend = ref.ibm_base.select_backend(service, LOGICAL_QUBITS, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)
    qc, rounds = direct.build_recycled(args.phase_bits, use_measure2)

    print(f"Script revision: {SCRIPT_REVISION}")
    print(f"backend={backend.name} measure_2={use_measure2} phase_bits={args.phase_bits}")
    print(
        f"profile={args.profile} optimization_level={args.optimization_level} "
        f"logical_qubits={qc.num_qubits}"
    )
    print("NO QPU JOBS WILL BE SUBMITTED.")

    plans = candidate_layouts(
        backend, args.phase_bits, args.ancilla_pool, args.candidate_plans
    )
    print(f"candidate physical plans={len(plans)} seeds={seeds}")

    rows = []

    # Preserve the automatic-layout compiler result as a baseline in the same
    # calibration snapshot and profile.
    for seed in seeds:
        print(f"compile auto-layout seed={seed}")
        try:
            compiled, elapsed = compile_one(
                qc, backend, args.profile, args.optimization_level, seed, None
            )
            row = evaluate(
                qc,
                compiled,
                elapsed,
                backend,
                {"type": "auto_layout", "initial_layout": None},
                seed,
                args.profile,
                args.optimization_level,
            )
        except Exception as exc:
            row = {
                "success": False,
                "plan": {"type": "auto_layout", "initial_layout": None},
                "seed_transpiler": seed,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        rows.append(row)
        print(json.dumps(row, indent=2, default=str))

    for idx, plan in enumerate(plans):
        for seed in seeds:
            print(
                f"compile plan={idx} anc={plan['recycled_ancilla_physical']} seed={seed}"
            )
            try:
                compiled, elapsed = compile_one(
                    qc,
                    backend,
                    args.profile,
                    args.optimization_level,
                    seed,
                    plan["initial_layout"],
                )
                row = evaluate(
                    qc,
                    compiled,
                    elapsed,
                    backend,
                    {"type": "fixed_layout", "candidate_index": idx, **plan},
                    seed,
                    args.profile,
                    args.optimization_level,
                )
            except Exception as exc:
                row = {
                    "success": False,
                    "plan": {"type": "fixed_layout", "candidate_index": idx, **plan},
                    "seed_transpiler": seed,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            rows.append(row)
            print(json.dumps(row, indent=2, default=str))

    good = [r for r in rows if r.get("success")]
    if not good:
        raise SystemExit("No layout compilation succeeded")

    best_cz = min(
        good,
        key=lambda r: (r["cz"], r["compiled_depth"], r["calibration_ranking_proxy"]),
    )
    best_proxy = min(
        good,
        key=lambda r: (r["calibration_ranking_proxy"], r["cz"], r["compiled_depth"]),
    )
    top_proxy = sorted(
        good,
        key=lambda r: (r["calibration_ranking_proxy"], r["cz"], r["compiled_depth"]),
    )[: args.top]

    print("\n===== BEST BY NATIVE CZ =====")
    print(json.dumps(best_cz, indent=2, default=str))
    print("\n===== BEST BY CALIBRATION PROXY =====")
    print(json.dumps(best_proxy, indent=2, default=str))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": direct.N,
        "a": direct.A,
        "phase_bits": args.phase_bits,
        "profile": args.profile,
        "optimization_level": args.optimization_level,
        "seeds": seeds,
        "qpu_submitted": False,
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "semantic": semantic,
        "round_multipliers": [r["multiplier"] for r in rounds],
        "rows": rows,
        "best_by_native_cz": best_cz,
        "best_by_calibration_proxy": best_proxy,
        "top_by_calibration_proxy": top_proxy,
        "proxy_note": "Calibration-weighted ranking heuristic only; not a predicted circuit fidelity.",
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    path = args.outdir / f"generic_direct_layout_optimizer_{args.phase_bits}b_{backend.name}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
