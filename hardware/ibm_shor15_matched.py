#!/usr/bin/env python3
"""Matched same-job IBM Fez comparison for toy Shor N=15, a=2.

Wide and recycled circuits:
  * run in the same SamplerV2 job,
  * start with the exact same four physical work qubits,
  * use one shared 8-qubit physical neighborhood,
  * record calibration/layout/resource metadata.

The transpiler may still route logical states within/around the selected region;
the fairness guarantee is identical initial work-qubit placement, not that every
logical work state remains on one physical site throughout the circuit.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import ibm_shor15_hardware as base
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2

SCRIPT_REVISION = "2026-09-13-shor15-matched-v1"


def inst_props(backend, name, qubits):
    try:
        p = backend.target[name][tuple(qubits)]
        return {
            "duration_s": None if p.duration is None else float(p.duration),
            "error": None if p.error is None else float(p.error),
        }
    except Exception:
        return {"duration_s": None, "error": None}


def cz_graph(backend):
    edges = set()
    for qargs in backend.target["cz"].keys():
        if qargs is not None and len(qargs) == 2:
            a, b = map(int, qargs)
            edges.add((a, b))
    und = {}
    for a, b in edges:
        und.setdefault(a, set()).add(b)
        und.setdefault(b, set()).add(a)
    return edges, und


def choose_shared_plan(backend):
    _, und = cz_graph(backend)
    if not und:
        raise RuntimeError("No CZ graph exposed by backend.")

    dist_cache = {}

    def dist(a, b):
        if (a, b) in dist_cache:
            return dist_cache[a, b]
        q = deque([(a, 0)])
        seen = {a}
        while q:
            u, d = q.popleft()
            if u == b:
                dist_cache[a, b] = dist_cache[b, a] = d
                return d
            for v in und.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    q.append((v, d + 1))
        return 999

    def edge_error(a, b):
        vals = []
        for pair in ((a, b), (b, a)):
            p = inst_props(backend, "cz", pair)
            if p["error"] is not None:
                vals.append(p["error"])
        return min(vals) if vals else 1.0

    def mcm_error(q):
        p = inst_props(backend, "measure_2", (q,))
        if p["error"] is not None:
            return p["error"]
        p = inst_props(backend, "measure", (q,))
        return p["error"] if p["error"] is not None else 1.0

    def mcm_duration(q):
        p = inst_props(backend, "measure_2", (q,))
        if p["duration_s"] is not None:
            return p["duration_s"]
        p = inst_props(backend, "measure", (q,))
        return p["duration_s"] if p["duration_s"] is not None else 1.0

    candidates = []
    work_pairs = ((0, 1), (1, 2), (2, 3), (0, 2), (1, 3))

    for anc in sorted(und):
        region = [anc]
        while len(region) < 8:
            frontier = []
            for u in region:
                for v in und.get(u, ()):
                    if v not in region:
                        frontier.append((edge_error(u, v), v))
            if not frontier:
                break
            frontier.sort()
            region.append(next(v for _, v in frontier if v not in region))
        if len(region) != 8:
            continue

        others = [q for q in region if q != anc]
        best = None
        for work_tuple in itertools.permutations(others, 4):
            work = list(work_tuple)
            work_cost = sum(dist(work[i], work[j]) for i, j in work_pairs)
            leftover = [q for q in others if q not in work]
            leftover.sort(key=lambda q: sum(dist(q, w) for w in work))
            phases = [anc] + leftover
            control_cost = (
                sum(dist(phases[0], w) for w in work)
                + sum(dist(phases[1], w) for w in work)
            )
            qft_cost = sum(
                dist(phases[i], phases[j])
                for i in range(4) for j in range(i + 1, 4)
            )
            local = work_cost + 0.35 * control_cost + 0.15 * qft_cost
            if best is None or local < best[0]:
                best = (local, work, phases)

        local_errors = []
        for u in region:
            for v in und.get(u, ()):
                if v in region and u < v:
                    local_errors.append(edge_error(u, v))
        local_mean = sum(local_errors) / len(local_errors) if local_errors else 1.0

        score = (
            best[0]
            + 400.0 * mcm_error(anc)
            + 30.0 * local_mean
            + 0.02 * (mcm_duration(anc) / 1e-6)
        )
        candidates.append((score, anc, region, best[1], best[2], local_mean))

    if not candidates:
        raise RuntimeError("Could not find shared 8-qubit region.")
    candidates.sort(key=lambda x: x[0])
    score, anc, region, work, phases, local_mean = candidates[0]

    return {
        "score": score,
        "region": region,
        "shared_initial_work_physical": work,
        "recycled_ancilla_physical": anc,
        "wide_phase_physical": phases,
        "recycled_initial_layout": [anc] + work,
        "wide_initial_layout": phases + work,
        "ancilla_measure_2": inst_props(backend, "measure_2", (anc,)),
        "ancilla_measure": inst_props(backend, "measure", (anc,)),
        "local_mean_cz_error": local_mean,
    }


def compile_with_layout(circuit, backend, level, layout):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=level,
        seed_transpiler=8776,
        initial_layout=layout,
    )
    return pm.run(circuit)


def stats(original, compiled, kind, requested_layout):
    try:
        final_layout = compiled.layout.final_index_layout(filter_ancillas=True)
    except Exception:
        final_layout = None
    return {
        "kind": kind,
        "logical_qubits": original.num_qubits,
        "compiled_qubits": compiled.num_qubits,
        "requested_initial_layout": requested_layout,
        "physical_layout_after_transpile": final_layout,
        "depth": compiled.depth(),
        "size": compiled.size(),
        "count_ops": {str(k): int(v) for k, v in compiled.count_ops().items()},
    }


def wilson(k, n, z=1.959963984540054):
    p = k / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [center - half, center + half]


def peak_metrics(counts, phase_bits):
    total = sum(counts.values())
    q = 1 << phase_bits
    peaks = {int(round(k * q / 4)) % q for k in range(4)}
    on_peak = zero = 0
    for raw, count in counts.items():
        y = int(raw.replace(" ", ""), 2)
        if y in peaks:
            on_peak += count
        if y == 0:
            zero += count
    return {
        "ideal_peak_probability": on_peak / total,
        "zero_peak_probability": zero / total,
        "off_peak_probability": 1.0 - on_peak / total,
    }


def comparison(results):
    by = {r["kind"]: r for r in results}
    w, r = by["wide"], by["recycled"]
    wa, ra = w["analysis"], r["analysis"]
    nw, nr = wa["shots"], ra["shots"]
    kw = round(wa["factor_success_probability_per_shot"] * nw)
    kr = round(ra["factor_success_probability_per_shot"] * nr)
    pw, pr = kw / nw, kr / nr
    se = math.sqrt(pw * (1 - pw) / nw + pr * (1 - pr) / nr)
    return {
        "wide_factor_success": pw,
        "recycled_factor_success": pr,
        "recycled_minus_wide": pr - pw,
        "difference_standard_errors": (pr - pw) / se if se else None,
        "wide_wilson95": wilson(kw, nw),
        "recycled_wilson95": wilson(kr, nr),
        "wide_spectrum": peak_metrics(w["counts"], 4),
        "recycled_spectrum": peak_metrics(r["counts"], 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--shots", type=int, default=512)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=2)
    ap.add_argument("--max-execution-time", type=int, default=60)
    ap.add_argument("--transpile-only", action="store_true")
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor15"))
    args = ap.parse_args()

    service = base.make_service()
    before = base.safe_usage(service)
    backend = base.select_backend(service, 8, args.backend)
    use_measure2 = base.backend_has_measure2(backend)

    print("Script revision:", SCRIPT_REVISION)
    print("Problem: N=15, a=2, phase_bits=4")
    print(f"Backend: {backend.name} | measure_2={use_measure2}")
    print("Account usage:")
    print(json.dumps(before, indent=2, default=str))

    plan = choose_shared_plan(backend)
    print("Shared-work plan:")
    print(json.dumps(plan, indent=2, default=str))

    recycled = base.build_recycled_shor15(4, use_measure2)
    wide = base.build_wide_shor15(4)
    compiled_recycled = compile_with_layout(
        recycled, backend, args.optimization_level, plan["recycled_initial_layout"]
    )
    compiled_wide = compile_with_layout(
        wide, backend, args.optimization_level, plan["wide_initial_layout"]
    )

    compiled = [compiled_recycled, compiled_wide]
    kinds = ["recycled", "wide"]
    transpiled_stats = [
        stats(recycled, compiled_recycled, "recycled", plan["recycled_initial_layout"]),
        stats(wide, compiled_wide, "wide", plan["wide_initial_layout"]),
    ]
    print("Transpiled stats:")
    print(json.dumps(transpiled_stats, indent=2, default=str))

    out_base = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": 15,
        "a": 2,
        "phase_bits": 4,
        "shots": args.shots,
        "same_job": True,
        "same_initial_work_quartet": True,
        "shared_layout_plan": plan,
        "transpiled_stats": transpiled_stats,
        "account_usage_before": before,
        "note": (
            "Same initial physical work quartet is enforced. The transpiler may "
            "route logical states during execution, so this is not a claim that "
            "logical work states remain pinned to fixed physical sites."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.transpile_only:
        path = args.outdir / "ibm_shor15_matched_transpile.json"
        path.write_text(json.dumps(out_base, indent=2, default=str) + "\n")
        print("Transpile-only; no QPU job submitted.")
        print("Saved:", path.resolve())
        return

    print(f"Submitting recycled + wide together: 2 circuits x {args.shots} shots...")
    sampler = SamplerV2(mode=backend, options={"max_execution_time": args.max_execution_time})
    job = sampler.run(compiled, shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    results = []
    for pub, kind in zip(pubs, kinds):
        counts = getattr(pub.data, "phase").get_counts()
        results.append({
            "kind": kind,
            "counts": counts,
            "analysis": base.analyze_counts(counts, 4),
        })

    out = {
        **out_base,
        "job_id": job.job_id(),
        "metrics": base.safe_metrics(job),
        "results": results,
        "paired_comparison": comparison(results),
        "account_usage_after": base.safe_usage(service),
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"ibm_shor15_matched_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")

    print("\nRESULT")
    print(json.dumps(out, indent=2, default=str))
    print("\nSaved:", path.resolve())
    print("PAIRED:", json.dumps(out["paired_comparison"], sort_keys=True))


if __name__ == "__main__":
    main()
