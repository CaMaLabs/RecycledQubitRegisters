#!/usr/bin/env python3
"""Zero-QPU unique-placement Fez-vs-Nighthawk topology benchmark.

This tightens the earlier placement-robustness study in two ways:
1) duplicate source-node sets are rejected explicitly;
2) connected placements are sampled with stochastic frontier growth rather than
   always choosing the highest-connectivity frontier node, increasing topology
   diversity while preserving connectedness.

The experiment focuses on 32, 48, and 64 phase bits, where the previous
placement-robust benchmark showed the clearest topology-dependent shift in the
recycled-vs-wide CZ ratio.

No Sampler, Estimator, Runtime job, or QPU execution is performed.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap

import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

REV = "2026-10-07-unique-placement-v1"
OUT = Path(
    "results/qubit_recycling/ibm_fez_vs_nighthawk_unique_placement_robustness.json"
)
BASIS = ["rz", "sx", "x", "cz"]


def adjacency(cm: CouplingMap) -> list[set[int]]:
    n = cm.size()
    out = [set() for _ in range(n)]
    for u, v in cm.get_edges():
        u, v = int(u), int(v)
        if u != v:
            out[u].add(v)
            out[v].add(u)
    return out


def induced_stats(adj: list[set[int]], nodes: list[int]) -> dict:
    ss = set(nodes)
    deg = [sum(v in ss for v in adj[u]) for u in nodes]
    return {
        "num_qubits": len(nodes),
        "undirected_edges": sum(deg) // 2,
        "degree_min": min(deg) if deg else 0,
        "degree_mean": statistics.fmean(deg) if deg else 0.0,
        "degree_max": max(deg) if deg else 0,
        "degree_sequence": sorted(deg, reverse=True),
    }


def weighted_choice(rng: random.Random, items: list[int], weights: list[float]) -> int:
    total = sum(weights)
    x = rng.random() * total
    acc = 0.0
    for item, w in zip(items, weights):
        acc += w
        if x <= acc:
            return item
    return items[-1]


def random_connected_nodes(
    adj: list[set[int]], k: int, seed: int
) -> list[int]:
    """Generate a connected k-node set with reproducible frontier sampling.

    Frontier vertices with more links into the selected set are preferred, but
    not deterministically forced. This intentionally creates a wider variety of
    connected shapes than the previous greedy sampler.
    """
    if k < 1 or k > len(adj):
        raise ValueError(f"invalid placement width {k}")

    rng = random.Random(seed)
    viable = [i for i, ns in enumerate(adj) if ns]
    if not viable:
        raise RuntimeError("topology has no connected vertices")

    start = rng.choice(viable)
    selected = {start}

    while len(selected) < k:
        frontier = sorted(
            {v for u in selected for v in adj[u] if v not in selected}
        )
        if not frontier:
            raise RuntimeError(
                f"placement growth stalled at {len(selected)} of {k}"
            )

        weights = []
        for v in frontier:
            internal = sum(x in selected for x in adj[v])
            full_degree = len(adj[v])
            # Prefer compact growth, but keep enough randomness to sample
            # different trees/patches rather than converging to one shape.
            weights.append((1.0 + 2.0 * internal) * (1.0 + 0.20 * full_degree))

        selected.add(weighted_choice(rng, frontier, weights))

    return sorted(selected)


def subgraph_for_nodes(
    adj: list[set[int]], nodes: list[int]
) -> tuple[CouplingMap, dict]:
    relabel = {old: new for new, old in enumerate(nodes)}
    ss = set(nodes)
    pairs = set()
    for u in nodes:
        for v in adj[u]:
            if v in ss and u < v:
                pairs.add((relabel[u], relabel[v]))

    edges = [[a, b] for u, v in sorted(pairs) for a, b in ((u, v), (v, u))]
    cm = CouplingMap(edges)
    while cm.size() < len(nodes):
        cm.graph.add_node(None)
    if cm.size() != len(nodes):
        raise RuntimeError("subgraph width mismatch")

    meta = {
        "source_node_ids": nodes,
        "selection": "unique_seeded_weighted_connected_frontier_growth",
        **induced_stats(adj, nodes),
    }
    return cm, meta


def generic(k: int, cm: CouplingMap) -> GenericBackendV2:
    return GenericBackendV2(
        num_qubits=k,
        basis_gates=BASIS,
        coupling_map=cm,
        control_flow=True,
        seed=8776,
        noise_info=False,
    )


def quantile(values: list[float], q: float) -> float:
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return float(xs[lo])
    f = pos - lo
    return float(xs[lo] * (1 - f) + xs[hi] * f)


def dist(values: list[float]) -> dict:
    return {
        "n": len(values),
        "min": min(values),
        "q1": quantile(values, 0.25),
        "median": statistics.median(values),
        "q3": quantile(values, 0.75),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def best_compile(rows: list[dict]) -> dict:
    good = [r for r in rows if r.get("success") and r.get("strict_width_pass")]
    if not good:
        raise RuntimeError("placement had no successful strict compile")
    return min(
        good,
        key=lambda r: (
            r["native_cz"],
            r["compiled_depth"],
            r["seed_transpiler"],
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--phase-bits", nargs="+", type=int, default=[32, 48, 64])
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--placements", type=int, default=12)
    ap.add_argument("--max-placement-attempts", type=int, default=2000)
    ap.add_argument("--placement-seed-base", type=int, default=10072026)
    ap.add_argument("--transpiler-seeds", default="2026,9401")
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    bits = sorted(set(a.phase_bits))
    tseeds = [int(x) for x in a.transpiler_seeds.split(",") if x]
    if (
        not bits
        or min(bits) < 1
        or a.scratch_bits < 0
        or a.placements < 2
        or a.max_placement_attempts < a.placements
        or not tseeds
    ):
        raise SystemExit("invalid arguments")

    service = width.ref.ibm_base.make_service()
    max_wide = direct.WORK_BITS + max(bits) + a.scratch_bits
    fez = width.ref.ibm_base.select_backend(service, max_wide, a.fez_backend)
    fcm = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    ncm, nsrc = topo.nighthawk_map(service)
    if max_wide > ncm.size():
        raise SystemExit(
            f"requested wide precision needs {max_wide} qubits, "
            f"Nighthawk topology has {ncm.size()}"
        )

    full = {
        "fez_heavy_hex_topology": fcm,
        "nighthawk_square_lattice_topology": ncm,
    }

    print("ZERO-QPU UNIQUE-PLACEMENT BENCHMARK: no Sampler or QPU job is used.")
    print(
        f"Fez={fez.name} Nighthawk_source={nsrc['mode']} normalized_basis={BASIS}"
    )
    print(
        f"phase_bits={bits} target_unique_placements={a.placements} "
        f"transpiler_seeds={tseeds}"
    )
    if nsrc["proxy"]:
        print(
            "IMPORTANT: Nighthawk side is still a 10x12 square-lattice PROXY, "
            "not exact Phoenix."
        )

    res = {
        "experiment": "ibm_fez_vs_nighthawk_unique_placement_robustness_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "N": direct.N,
        "base": direct.A,
        "work_bits": direct.WORK_BITS,
        "scratch_bits": a.scratch_bits,
        "phase_bits": bits,
        "target_unique_placements": a.placements,
        "max_placement_attempts": a.max_placement_attempts,
        "placement_seed_base": a.placement_seed_base,
        "transpiler_seeds": tseeds,
        "profile": a.profile,
        "optimization_level": a.optimization_level,
        "common_basis": BASIS,
        "full_topologies": {
            "fez_heavy_hex_topology": {
                "source": "authenticated_ibm_fez_coupling_metadata",
                "backend_name": str(fez.name),
                **topo.topo_stats(fcm),
            },
            "nighthawk_square_lattice_topology": {
                "source": nsrc,
                **topo.topo_stats(ncm),
            },
        },
        "strict_width_method": (
            "Every placement backend has exactly the source circuit width; "
            "out-of-budget qubit borrowing is impossible."
        ),
        "uniqueness_definition": (
            "Exact source-node-set uniqueness within each topology / architecture / "
            "phase-precision cell. Duplicate node sets are rejected before compilation."
        ),
        "scope_boundary": (
            "Topology/compiler proxy only; no calibration, timing, reset-speed, "
            "fidelity, or QPU data. Square lattice is not asserted to be exact Phoenix. "
            "N=35 full-register permutation synthesis is not scalable RSA arithmetic."
        ),
        "rows": [],
        "placement_best": [],
        "placement_generation": {},
        "summaries": {},
    }

    for m in bits:
        if not direct.semantic_summary(m)["pass"]:
            raise RuntimeError(f"semantic failure at {m}")

        for kind in ("recycled", "wide"):
            qc, rounds, _ = width.build(kind, m, a.scratch_bits, use_measure2=False)
            logical = qc.num_qubits
            mcx = sum(int(r.get("direct_mcx", 0)) for r in rounds)
            print(
                f"\n===== bits={m} kind={kind} allocated={logical}q "
                f"direct_mcx={mcx} ====="
            )

            for ti, (tn, cm) in enumerate(full.items()):
                adj = adjacency(cm)
                unique: dict[tuple[int, ...], tuple[int, dict]] = {}
                attempts = 0

                while len(unique) < a.placements and attempts < a.max_placement_attempts:
                    pseed = (
                        a.placement_seed_base
                        + 1000000 * ti
                        + 10000 * logical
                        + 101 * m
                        + attempts
                    )
                    nodes = random_connected_nodes(adj, logical, pseed)
                    key = tuple(nodes)
                    if key not in unique:
                        _, meta = subgraph_for_nodes(adj, nodes)
                        unique[key] = (pseed, meta)
                    attempts += 1

                gen_key = f"{m}:{kind}:{tn}"
                res["placement_generation"][gen_key] = {
                    "target_unique": a.placements,
                    "unique_obtained": len(unique),
                    "attempts": attempts,
                    "duplicate_attempts": attempts - len(unique),
                }

                print(
                    f"topology={tn} unique={len(unique)}/{a.placements} "
                    f"attempts={attempts} duplicates={attempts-len(unique)}"
                )
                if len(unique) < 2:
                    raise RuntimeError(
                        f"insufficient unique placements for {gen_key}: {len(unique)}"
                    )

                for pidx, (nodes_key, (pseed, pmeta)) in enumerate(unique.items()):
                    nodes = list(nodes_key)
                    sub, _ = subgraph_for_nodes(adj, nodes)
                    backend = generic(logical, sub)
                    prows = []

                    print(
                        f"placement topology={tn} index={pidx} seed={pseed} "
                        f"edges={pmeta['undirected_edges']} "
                        f"degree_seq={pmeta['degree_sequence']}"
                    )

                    for tseed in tseeds:
                        print(f"  compile seed={tseed}")
                        try:
                            st = width.compile_one(
                                qc, backend, a.profile, a.optimization_level, tseed
                            )
                            touched = int(st["compiled_touched_qubits"])
                            row = {
                                "success": True,
                                "topology": tn,
                                "kind": kind,
                                "phase_bits": m,
                                "logical_qubits": logical,
                                "backend_qubits": logical,
                                "placement_index": pidx,
                                "placement_seed": pseed,
                                "placement": pmeta,
                                "seed_transpiler": tseed,
                                "semantic_pass": True,
                                "total_direct_mcx": mcx,
                                "compiled_touched_qubits": touched,
                                "extra_physical_qubits_borrowed": max(
                                    0, touched - logical
                                ),
                                "strict_width_pass": touched <= logical,
                                **{
                                    k: v
                                    for k, v in st.items()
                                    if k != "compiled_touched_qubits"
                                },
                            }
                            print(
                                f"    -> touched={touched}/{logical} "
                                f"CZ={row['native_cz']} depth={row['compiled_depth']}"
                            )
                        except Exception as exc:
                            row = {
                                "success": False,
                                "topology": tn,
                                "kind": kind,
                                "phase_bits": m,
                                "logical_qubits": logical,
                                "backend_qubits": logical,
                                "placement_index": pidx,
                                "placement_seed": pseed,
                                "placement": pmeta,
                                "seed_transpiler": tseed,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            }
                            print(f"    -> FAIL {type(exc).__name__}: {exc}")

                        prows.append(row)
                        res["rows"].append(row)
                        a.out.parent.mkdir(parents=True, exist_ok=True)
                        a.out.write_text(json.dumps(res, indent=2, default=str) + "\n")

                    b = best_compile(prows)
                    res["placement_best"].append(
                        {
                            "topology": tn,
                            "kind": kind,
                            "phase_bits": m,
                            "logical_qubits": logical,
                            "placement_index": pidx,
                            "placement_seed": pseed,
                            "placement": pmeta,
                            "seed_transpiler": b["seed_transpiler"],
                            "native_cz": b["native_cz"],
                            "compiled_depth": b["compiled_depth"],
                            "compiled_size": b["compiled_size"],
                            "compile_seconds": b["compile_seconds"],
                        }
                    )

    summaries = {}
    for m in bits:
        mk = str(m)
        summaries[mk] = {}
        for tn in full:
            summaries[mk][tn] = {}
            for kind in ("recycled", "wide"):
                rows = [
                    r
                    for r in res["placement_best"]
                    if r["topology"] == tn
                    and r["kind"] == kind
                    and r["phase_bits"] == m
                ]
                summaries[mk][tn][kind] = {
                    "logical_qubits": rows[0]["logical_qubits"],
                    "placement_count": len(rows),
                    "native_cz": dist([r["native_cz"] for r in rows]),
                    "compiled_depth": dist([r["compiled_depth"] for r in rows]),
                    "compiled_size": dist([r["compiled_size"] for r in rows]),
                    "induced_edges": dist(
                        [r["placement"]["undirected_edges"] for r in rows]
                    ),
                }

        f = summaries[mk]["fez_heavy_hex_topology"]
        n = summaries[mk]["nighthawk_square_lattice_topology"]

        fcz = f["recycled"]["native_cz"]["median"] / f["wide"]["native_cz"]["median"]
        ncz = n["recycled"]["native_cz"]["median"] / n["wide"]["native_cz"]["median"]
        fd = (
            f["recycled"]["compiled_depth"]["median"]
            / f["wide"]["compiled_depth"]["median"]
        )
        nd = (
            n["recycled"]["compiled_depth"]["median"]
            / n["wide"]["compiled_depth"]["median"]
        )

        summaries[mk]["comparison"] = {
            "phase_bits": m,
            "logical_width_recycled": f["recycled"]["logical_qubits"],
            "logical_width_wide": f["wide"]["logical_qubits"],
            "logical_qubits_saved": (
                f["wide"]["logical_qubits"] - f["recycled"]["logical_qubits"]
            ),
            "fez_recycled_over_wide_cz_ratio_of_medians": fcz,
            "nighthawk_recycled_over_wide_cz_ratio_of_medians": ncz,
            "cz_advantage_amplification_nighthawk_over_fez": ncz / fcz,
            "fez_recycled_over_wide_depth_ratio_of_medians": fd,
            "nighthawk_recycled_over_wide_depth_ratio_of_medians": nd,
            "depth_advantage_amplification_nighthawk_over_fez": nd / fd,
        }

    res["summaries"] = summaries
    a.out.write_text(json.dumps(res, indent=2, default=str) + "\n")

    print("\n===== UNIQUE-PLACEMENT ROBUSTNESS SUMMARY =====")
    for m in bits:
        s = summaries[str(m)]
        c = s["comparison"]
        fr = s["fez_heavy_hex_topology"]["recycled"]
        fw = s["fez_heavy_hex_topology"]["wide"]
        nr = s["nighthawk_square_lattice_topology"]["recycled"]
        nw = s["nighthawk_square_lattice_topology"]["wide"]

        print(
            f"bits={m}: width {c['logical_width_wide']}->{c['logical_width_recycled']} "
            f"saved={c['logical_qubits_saved']} | "
            f"Fez CZ med R/W={c['fez_recycled_over_wide_cz_ratio_of_medians']:.4f} "
            f"(R {fr['native_cz']['q1']:.0f}/{fr['native_cz']['median']:.0f}/{fr['native_cz']['q3']:.0f}; "
            f"W {fw['native_cz']['q1']:.0f}/{fw['native_cz']['median']:.0f}/{fw['native_cz']['q3']:.0f}) | "
            f"Square CZ med R/W={c['nighthawk_recycled_over_wide_cz_ratio_of_medians']:.4f} "
            f"(R {nr['native_cz']['q1']:.0f}/{nr['native_cz']['median']:.0f}/{nr['native_cz']['q3']:.0f}; "
            f"W {nw['native_cz']['q1']:.0f}/{nw['native_cz']['median']:.0f}/{nw['native_cz']['q3']:.0f}) | "
            f"amp={c['cz_advantage_amplification_nighthawk_over_fez']:.4f}"
        )
        print(
            f"         depth med R/W Fez={c['fez_recycled_over_wide_depth_ratio_of_medians']:.4f} "
            f"Square={c['nighthawk_recycled_over_wide_depth_ratio_of_medians']:.4f} "
            f"amp={c['depth_advantage_amplification_nighthawk_over_fez']:.4f}"
        )

    print("\n===== UNIQUE PLACEMENT GENERATION =====")
    for k, v in sorted(res["placement_generation"].items()):
        print(
            f"{k}: unique={v['unique_obtained']}/{v['target_unique']} "
            f"attempts={v['attempts']} duplicates={v['duplicate_attempts']}"
        )

    print(f"\nwrote {a.out}\nNO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
