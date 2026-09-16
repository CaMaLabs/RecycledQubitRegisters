#!/usr/bin/env python3
"""Zero-QPU subgraph-ensemble audit for recycled QPE topology robustness.

The capacity-locked Fez-vs-Nighthawk benchmark showed that an exact-width
Nighthawk-style square lattice can remove most of the routing penalty of the
8-qubit recycled construction.  That result used one deterministic dense
connected subgraph per topology/width.  This audit tests whether the conclusion
survives across multiple distinct exact-width connected patches.

For each requested phase precision and architecture (recycled/wide), we:
  * build the same exact N=35 full-register circuit used by prior audits;
  * generate multiple distinct connected exact-width subgraphs on Fez and on
    authenticated Phoenix metadata when available, otherwise the labeled
    10x12 Nighthawk square-lattice proxy;
  * compile against a backend whose capacity equals the source width, making
    extra qubit borrowing impossible;
  * choose the best requested transpiler seed within each patch;
  * summarize CZ/depth distributions across patches and compare median
    recycled/wide ratios between topologies.

No Sampler is instantiated and no QPU job is submitted.  This remains a
compiler/topology proxy, not a calibrated Phoenix performance prediction.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler import CouplingMap

import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

REV = "2026-09-16-subgraph-ensemble-v1"
OUT = Path("results/qubit_recycling/ibm_nighthawk_subgraph_ensemble_audit.json")


def div(a, b):
    return None if not b else float(a / b)


def random_connected_nodes(cm: CouplingMap, k: int, rng: random.Random) -> list[int]:
    """Grow a connected patch with a mild density bias and random tie-breaking."""
    n = cm.size()
    if k < 1 or k > n:
        raise ValueError(f"requested width {k} outside 1..{n}")
    adj = cap.adjacency(cm)
    full_degree = [len(x) for x in adj]

    # Favor non-leaf starts but keep placement stochastic.
    starts = [i for i, d in enumerate(full_degree) if d > 1] or list(range(n))
    start = int(rng.choice(starts))
    selected = [start]
    chosen = {start}

    while len(selected) < k:
        frontier = set()
        for u in selected:
            frontier.update(adj[u] - chosen)
        if not frontier:
            raise RuntimeError("connected growth stalled")

        scored = []
        for v in frontier:
            links_in = sum(u in chosen for u in adj[v])
            scored.append((links_in, full_degree[v], rng.random(), int(v)))
        scored.sort(reverse=True)

        # Randomize among the strongest few candidates.  This keeps patches
        # reasonably dense while sampling different placements/shapes.
        top = scored[: min(4, len(scored))]
        _, _, _, nxt = rng.choice(top)
        selected.append(int(nxt))
        chosen.add(int(nxt))

    return selected


def patch_ensemble(
    cm: CouplingMap,
    k: int,
    count: int,
    seed: int,
) -> list[dict]:
    """Return one deterministic dense patch plus distinct stochastic patches."""
    if count < 1:
        raise ValueError("count must be >= 1")

    patches: list[dict] = []
    seen: set[tuple[int, ...]] = set()

    dense_nodes, dense_stats = cap.greedy_connected_nodes(cm, k)
    key = tuple(sorted(dense_nodes))
    seen.add(key)
    patches.append({
        "patch_index": 0,
        "mode": "deterministic_dense",
        "nodes": dense_nodes,
        "stats": dense_stats,
    })

    attempt = 0
    while len(patches) < count and attempt < count * 500:
        rng = random.Random(seed + 104729 * attempt + 1009 * k)
        attempt += 1
        try:
            nodes = random_connected_nodes(cm, k, rng)
        except RuntimeError:
            continue
        key = tuple(sorted(nodes))
        if key in seen:
            continue
        seen.add(key)
        patches.append({
            "patch_index": len(patches),
            "mode": "stochastic_connected",
            "nodes": nodes,
            "stats": cap.induced_stats(cap.adjacency(cm), nodes),
        })

    if len(patches) < count:
        raise RuntimeError(
            f"generated only {len(patches)} unique width-{k} patches; requested {count}"
        )
    return patches


def summarize(values: list[float | int]) -> dict:
    vals = [float(x) for x in values]
    if not vals:
        return {}
    vals.sort()
    return {
        "count": len(vals),
        "min": min(vals),
        "median": statistics.median(vals),
        "mean": statistics.fmean(vals),
        "max": max(vals),
    }


def aggregate(rows: list[dict], topology: str, kind: str, bits: int) -> dict | None:
    subset = [
        r for r in rows
        if r.get("success")
        and r["topology"] == topology
        and r["kind"] == kind
        and r["phase_bits"] == bits
    ]
    if not subset:
        return None
    return {
        "topology": topology,
        "kind": kind,
        "phase_bits": bits,
        "logical_qubits": int(subset[0]["logical_qubits"]),
        "patch_count": len(subset),
        "native_cz": summarize([r["native_cz"] for r in subset]),
        "compiled_depth": summarize([r["compiled_depth"] for r in subset]),
        "compiled_size": summarize([r["compiled_size"] for r in subset]),
        "undirected_edges": summarize([r["patch_undirected_edges"] for r in subset]),
        "patch_mean_degree": summarize([r["patch_mean_degree"] for r in subset]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU exact-width topology subgraph ensemble audit"
    )
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--phase-bits", nargs="+", type=int, default=[8, 16, 32, 64])
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--subgraph-samples", type=int, default=8)
    ap.add_argument("--subgraph-seed", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--transpiler-seeds", default="2026")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    bits_list = sorted(set(int(x) for x in args.phase_bits))
    transpiler_seeds = [
        int(x.strip()) for x in args.transpiler_seeds.split(",") if x.strip()
    ]
    if (
        not bits_list
        or min(bits_list) < 1
        or args.scratch_bits < 0
        or args.subgraph_samples < 1
        or not transpiler_seeds
    ):
        raise SystemExit("invalid arguments")

    service = width.ref.ibm_base.make_service()
    max_width = direct.WORK_BITS + max(bits_list) + args.scratch_bits
    fez = width.ref.ibm_base.select_backend(service, max_width, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    night_full, night_src = topo.nighthawk_map(service)
    if max_width > night_full.size():
        raise SystemExit("requested wide precision exceeds Nighthawk width")

    topologies = {
        "fez_heavy_hex_topology": fez_full,
        "nighthawk_square_lattice_topology": night_full,
    }

    print("ZERO-QPU SUBGRAPH ENSEMBLE AUDIT: no Sampler or QPU job is used.")
    print(f"Fez={fez.name} Nighthawk_source={night_src['mode']}")
    if night_src.get("proxy"):
        print("IMPORTANT: Nighthawk side is a 10x12 square-lattice PROXY, not exact Phoenix.")
    print(
        f"phase_bits={bits_list} patches={args.subgraph_samples} "
        f"transpiler_seeds={transpiler_seeds}"
    )

    result = {
        "experiment": "ibm_nighthawk_subgraph_ensemble_audit_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "N": int(direct.N),
        "base": int(direct.A),
        "work_bits": int(direct.WORK_BITS),
        "scratch_bits": int(args.scratch_bits),
        "phase_bits": bits_list,
        "subgraph_samples": int(args.subgraph_samples),
        "subgraph_seed": int(args.subgraph_seed),
        "profile": args.profile,
        "optimization_level": int(args.optimization_level),
        "transpiler_seeds": transpiler_seeds,
        "nighthawk_source": night_src,
        "capacity_lock_definition": (
            "Every compile backend has exactly the source circuit width; extra qubit borrowing is impossible."
        ),
        "ensemble_definition": (
            "One deterministic dense connected patch plus distinct stochastic connected patches per topology/width."
        ),
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "scope_boundary": (
            "Topology-only compiler proxy; no calibration, timing, reset-speed or fidelity model. "
            "N=35 remains exact small-N full-register synthesis, not scalable RSA arithmetic."
        ),
        "rows": [],
    }

    patch_cache: dict[tuple[str, int], list[dict]] = {}

    for bits in bits_list:
        if not direct.semantic_summary(bits)["pass"]:
            raise RuntimeError(f"semantic failure at phase_bits={bits}")

        for kind in ("recycled", "wide"):
            qc, rounds, _ = width.build(kind, bits, args.scratch_bits, use_measure2=False)
            logical = int(qc.num_qubits)
            mcx = sum(int(r.get("direct_mcx", 0)) for r in rounds)
            print(f"\n===== bits={bits} kind={kind} width={logical}q direct_mcx={mcx} =====")

            for topology_name, full_cm in topologies.items():
                cache_key = (topology_name, logical)
                if cache_key not in patch_cache:
                    salt = args.subgraph_seed + (0 if topology_name.startswith("fez") else 1_000_003)
                    patch_cache[cache_key] = patch_ensemble(
                        full_cm, logical, args.subgraph_samples, salt
                    )

                for patch in patch_cache[cache_key]:
                    nodes = patch["nodes"]
                    stats = patch["stats"]
                    subcm = cap.relabeled_subgraph(full_cm, nodes)
                    backend = topo.generic(logical, subcm)

                    seed_rows = []
                    for transpiler_seed in transpiler_seeds:
                        try:
                            st = width.compile_one(
                                qc,
                                backend,
                                args.profile,
                                args.optimization_level,
                                transpiler_seed,
                            )
                            touched = int(st["compiled_touched_qubits"])
                            if touched > logical:
                                raise AssertionError(
                                    f"capacity lock violated: touched {touched} > {logical}"
                                )
                            seed_rows.append({
                                "success": True,
                                "topology": topology_name,
                                "kind": kind,
                                "phase_bits": bits,
                                "logical_qubits": logical,
                                "patch_index": int(patch["patch_index"]),
                                "patch_mode": patch["mode"],
                                "patch_nodes": [int(x) for x in nodes],
                                "patch_undirected_edges": int(stats["undirected_edges"]),
                                "patch_mean_degree": float(stats["degree_mean"]),
                                "seed_transpiler": int(transpiler_seed),
                                "total_direct_mcx": int(mcx),
                                "semantic_pass": True,
                                "compiled_touched_qubits": touched,
                                **{k: v for k, v in st.items() if k != "compiled_touched_qubits"},
                            })
                        except Exception as exc:
                            seed_rows.append({
                                "success": False,
                                "topology": topology_name,
                                "kind": kind,
                                "phase_bits": bits,
                                "logical_qubits": logical,
                                "patch_index": int(patch["patch_index"]),
                                "patch_mode": patch["mode"],
                                "seed_transpiler": int(transpiler_seed),
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            })

                    good = [r for r in seed_rows if r.get("success")]
                    if not good:
                        result["rows"].append(seed_rows[0])
                        print(
                            f"topology={topology_name} patch={patch['patch_index']} FAIL"
                        )
                    else:
                        best_row = min(
                            good,
                            key=lambda r: (
                                r["native_cz"], r["compiled_depth"], r["seed_transpiler"]
                            ),
                        )
                        result["rows"].append(best_row)
                        print(
                            f"topology={topology_name} patch={patch['patch_index']} "
                            f"edges={stats['undirected_edges']} mean_degree={stats['degree_mean']:.3f} "
                            f"CZ={best_row['native_cz']} depth={best_row['compiled_depth']}"
                        )

                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    aggregates = {}
    comparisons = {}
    for bits in bits_list:
        key = str(bits)
        aggregates[key] = {}
        for topology_name in topologies:
            aggregates[key][topology_name] = {}
            for kind in ("recycled", "wide"):
                aggregates[key][topology_name][kind] = aggregate(
                    result["rows"], topology_name, kind, bits
                )

        fr = aggregates[key]["fez_heavy_hex_topology"]["recycled"]
        fw = aggregates[key]["fez_heavy_hex_topology"]["wide"]
        nr = aggregates[key]["nighthawk_square_lattice_topology"]["recycled"]
        nw = aggregates[key]["nighthawk_square_lattice_topology"]["wide"]
        if all(x is not None for x in (fr, fw, nr, nw)):
            fcz = div(fr["native_cz"]["median"], fw["native_cz"]["median"])
            ncz = div(nr["native_cz"]["median"], nw["native_cz"]["median"])
            fd = div(fr["compiled_depth"]["median"], fw["compiled_depth"]["median"])
            nd = div(nr["compiled_depth"]["median"], nw["compiled_depth"]["median"])
            comparisons[key] = {
                "phase_bits": bits,
                "recycled_width": int(fr["logical_qubits"]),
                "wide_width": int(fw["logical_qubits"]),
                "qubits_saved": int(fw["logical_qubits"] - fr["logical_qubits"]),
                "fez_median_recycled_over_wide_cz_ratio": fcz,
                "nighthawk_median_recycled_over_wide_cz_ratio": ncz,
                "relative_median_cz_ratio_nighthawk_over_fez": div(ncz, fcz),
                "fez_median_recycled_over_wide_depth_ratio": fd,
                "nighthawk_median_recycled_over_wide_depth_ratio": nd,
                "relative_median_depth_ratio_nighthawk_over_fez": div(nd, fd),
                "recycled_nighthawk_over_fez_median_cz_ratio": div(
                    nr["native_cz"]["median"], fr["native_cz"]["median"]
                ),
                "wide_nighthawk_over_fez_median_cz_ratio": div(
                    nw["native_cz"]["median"], fw["native_cz"]["median"]
                ),
            }

    result["aggregates"] = aggregates
    result["comparisons"] = comparisons
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    print("\n===== SUBGRAPH ENSEMBLE SUMMARY =====")
    for bits in bits_list:
        c = comparisons.get(str(bits))
        if not c:
            print(f"bits={bits}: missing aggregate")
            continue
        print(
            f"bits={bits}: width {c['wide_width']}->{c['recycled_width']} saved={c['qubits_saved']} | "
            f"median R/W CZ Fez={c['fez_median_recycled_over_wide_cz_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_median_recycled_over_wide_cz_ratio']:.4f} "
            f"relative={c['relative_median_cz_ratio_nighthawk_over_fez']:.4f} | "
            f"median R/W depth Fez={c['fez_median_recycled_over_wide_depth_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_median_recycled_over_wide_depth_ratio']:.4f} "
            f"relative={c['relative_median_depth_ratio_nighthawk_over_fez']:.4f}"
        )

    print("\n===== DISTRIBUTION DETAIL =====")
    for bits in bits_list:
        for topology_name in topologies:
            for kind in ("recycled", "wide"):
                a = aggregates[str(bits)][topology_name][kind]
                print(
                    f"bits={bits} topology={topology_name} kind={kind} "
                    f"CZ={json.dumps(a['native_cz'], sort_keys=True)} "
                    f"depth={json.dumps(a['compiled_depth'], sort_keys=True)}"
                )

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
