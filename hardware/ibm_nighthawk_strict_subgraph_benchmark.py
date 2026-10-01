#!/usr/bin/env python3
"""Strict-width Fez-vs-Nighthawk topology proxy for recycled QPE.

This is the follow-up to ibm_nighthawk_topology_recycling_benchmark.py.  The
full-topology benchmark deliberately exposes the whole processor to Qiskit's
HLS/transpiler; on the Nighthawk square-lattice proxy that allowed the compiler
to borrow additional physical qubits, so every Nighthawk row failed the strict
width test.

Here each source circuit is compiled against a backend whose *entire physical
width equals the circuit's source width*.  The backend connectivity is a compact
connected subgraph selected deterministically from the full Fez heavy-hex map or
Nighthawk square-lattice proxy.  Therefore the compiler cannot borrow qubits
outside the declared source width.

No Sampler, Estimator, Runtime job, or QPU execution is performed.  Both sides
use the same normalized CZ basis.  This is a topology/compiler experiment only:
it is not a calibrated Phoenix prediction and it is not a scalable RSA resource
estimate.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap

import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

REV = "2026-10-01-strict-width-subgraph-v1"
OUT = Path(
    "results/qubit_recycling/ibm_fez_vs_nighthawk_strict_subgraph_recycling.json"
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
    degrees = [sum(v in ss for v in adj[u]) for u in nodes]
    edges = sum(degrees) // 2
    return {
        "num_qubits": len(nodes),
        "undirected_edges": edges,
        "degree_min": min(degrees) if degrees else 0,
        "degree_mean": statistics.fmean(degrees) if degrees else 0.0,
        "degree_max": max(degrees) if degrees else 0,
        "degree_histogram": {
            str(k): sum(d == k for d in degrees) for k in sorted(set(degrees))
        },
    }


def grow_candidate(adj: list[set[int]], start: int, k: int) -> list[int] | None:
    """Grow a compact connected k-node set from start.

    Prefer frontier nodes with many links into the selected set, then high full
    degree.  This tends to choose dense compact patches while remaining fully
    deterministic.
    """
    chosen = [start]
    selected = {start}
    while len(chosen) < k:
        frontier = set()
        for u in selected:
            frontier.update(adj[u] - selected)
        if not frontier:
            return None
        nxt = max(
            frontier,
            key=lambda v: (
                sum(x in selected for x in adj[v]),
                len(adj[v]),
                -v,
            ),
        )
        selected.add(nxt)
        chosen.append(nxt)
    return chosen


def compact_connected_subgraph(cm: CouplingMap, k: int) -> tuple[CouplingMap, dict]:
    if k < 1 or k > cm.size():
        raise ValueError(f"invalid requested subgraph width {k} for topology {cm.size()}")

    adj = adjacency(cm)
    best_nodes = None
    best_key = None

    # Try every possible starting node.  k <= 71 in the current experiment and
    # the source topologies are <= 156 qubits, so this search is inexpensive.
    for start in range(cm.size()):
        nodes = grow_candidate(adj, start, k)
        if nodes is None:
            continue
        st = induced_stats(adj, nodes)
        degs = sorted(
            (sum(v in set(nodes) for v in adj[u]) for u in nodes), reverse=True
        )
        key = (
            st["undirected_edges"],
            st["degree_min"],
            tuple(degs),
            tuple(-x for x in sorted(nodes)),
        )
        if best_key is None or key > best_key:
            best_key = key
            best_nodes = nodes

    if best_nodes is None:
        raise RuntimeError(f"could not find connected {k}-node subgraph")

    # Stable relabeling makes the capped backend exactly k qubits wide.
    nodes = sorted(best_nodes)
    relabel = {old: new for new, old in enumerate(nodes)}
    node_set = set(nodes)
    pairs = set()
    for u in nodes:
        for v in adj[u]:
            if v in node_set and u < v:
                pairs.add((relabel[u], relabel[v]))

    edges = [[x, y] for u, v in sorted(pairs) for x, y in ((u, v), (v, u))]
    sub = CouplingMap(edges)
    while sub.size() < k:
        sub.graph.add_node(None)
    if sub.size() != k:
        raise RuntimeError(f"capped coupling width {sub.size()} != requested {k}")

    meta = {
        "source_node_ids": nodes,
        "selection": "deterministic_compact_connected_greedy_best_of_all_starts",
        **induced_stats(adj, nodes),
    }
    return sub, meta


def generic(k: int, cm: CouplingMap) -> GenericBackendV2:
    return GenericBackendV2(
        num_qubits=k,
        basis_gates=BASIS,
        coupling_map=cm,
        control_flow=True,
        seed=8776,
        noise_info=False,
    )


def best(rows: list[dict], topology: str, kind: str, bits: int) -> dict | None:
    candidates = [
        r
        for r in rows
        if r.get("success")
        and r.get("strict_width_pass")
        and r["topology"] == topology
        and r["kind"] == kind
        and r["phase_bits"] == bits
    ]
    return (
        min(
            candidates,
            key=lambda r: (
                r["native_cz"],
                r["compiled_depth"],
                r["seed_transpiler"],
            ),
        )
        if candidates
        else None
    )


def div(a, b):
    return None if not b else float(a / b)


def compact(row: dict | None):
    if row is None:
        return None
    keys = (
        "topology",
        "kind",
        "phase_bits",
        "logical_qubits",
        "compiled_touched_qubits",
        "strict_width_pass",
        "seed_transpiler",
        "native_cz",
        "compiled_depth",
        "compiled_size",
        "compile_seconds",
    )
    return {k: row.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument(
        "--phase-bits", nargs="+", type=int, default=[4, 8, 12, 16, 20]
    )
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seeds", default="8776,2026,9401")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()

    bits = sorted(set(a.phase_bits))
    seeds = [int(x) for x in a.seeds.split(",") if x]
    if not bits or min(bits) < 1 or a.scratch_bits < 0 or not seeds:
        raise SystemExit("invalid arguments")

    service = width.ref.ibm_base.make_service()
    max_wide = direct.WORK_BITS + max(bits) + a.scratch_bits
    fez = width.ref.ibm_base.select_backend(service, max_wide, a.fez_backend)
    fcm = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    ncm, nsrc = topo.nighthawk_map(service)
    if max_wide > ncm.size():
        raise SystemExit(
            f"requested wide precision needs {max_wide} qubits, Nighthawk topology has {ncm.size()}"
        )

    full = {
        "fez_heavy_hex_topology": fcm,
        "nighthawk_square_lattice_topology": ncm,
    }
    full_meta = {
        "fez_heavy_hex_topology": {
            "source": "authenticated_ibm_fez_coupling_metadata",
            "backend_name": str(fez.name),
            **topo.topo_stats(fcm),
        },
        "nighthawk_square_lattice_topology": {
            "source": nsrc,
            **topo.topo_stats(ncm),
        },
    }

    print("ZERO-QPU STRICT SUBGRAPH BENCHMARK: no Sampler or QPU job is used.")
    print(
        f"Fez={fez.name} Nighthawk_source={nsrc['mode']} normalized_basis={BASIS}"
    )
    print(
        "Each compile backend is hard-capped to source logical width; compiler borrowing is impossible."
    )
    if nsrc["proxy"]:
        print("IMPORTANT: Nighthawk remains a 10x12 square-lattice PROXY, not exact Phoenix.")

    res = {
        "experiment": "ibm_fez_vs_nighthawk_strict_subgraph_recycling_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "N": direct.N,
        "base": direct.A,
        "work_bits": direct.WORK_BITS,
        "scratch_bits": a.scratch_bits,
        "phase_bits": bits,
        "profile": a.profile,
        "optimization_level": a.optimization_level,
        "seeds": seeds,
        "common_basis": BASIS,
        "full_topologies": full_meta,
        "strict_width_method": (
            "For every topology/kind/phase point, compile against a GenericBackendV2 whose "
            "num_qubits equals source circuit width and whose coupling map is a deterministic "
            "compact connected subgraph of that width. No out-of-budget physical qubit exists."
        ),
        "subgraph_selection": "deterministic compact connected greedy, best induced edge count over every start node",
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "scope_boundary": (
            "Topology-only compiler proxy with normalized CZ basis; no calibration, timing, "
            "reset-speed, or fidelity model. Square lattice is not asserted to be exact Phoenix. "
            "N=35 is exact small-N full-register synthesis, not scalable RSA arithmetic."
        ),
        "rows": [],
        "subgraphs": {},
    }

    backend_cache: dict[tuple[str, int], GenericBackendV2] = {}
    for tn, cm in full.items():
        res["subgraphs"][tn] = {}
        widths = {1 + direct.WORK_BITS + a.scratch_bits}
        widths.update(direct.WORK_BITS + m + a.scratch_bits for m in bits)
        for k in sorted(widths):
            sub, smeta = compact_connected_subgraph(cm, k)
            backend_cache[(tn, k)] = generic(k, sub)
            res["subgraphs"][tn][str(k)] = smeta

    for m in bits:
        if not direct.semantic_summary(m)["pass"]:
            raise RuntimeError(f"semantic failure at {m}")

        for kind in ("recycled", "wide"):
            qc, rounds, _ = width.build(kind, m, a.scratch_bits, use_measure2=False)
            logical = qc.num_qubits
            mcx = sum(int(r.get("direct_mcx", 0)) for r in rounds)
            print(
                f"\n===== bits={m} kind={kind} allocated={logical}q direct_mcx={mcx} ====="
            )

            for tn in full:
                b = backend_cache[(tn, logical)]
                for seed in seeds:
                    print(f"compile topology={tn} seed={seed}")
                    try:
                        st = width.compile_one(
                            qc, b, a.profile, a.optimization_level, seed
                        )
                        touched = int(st["compiled_touched_qubits"])
                        row = {
                            "success": True,
                            "topology": tn,
                            "kind": kind,
                            "phase_bits": m,
                            "logical_qubits": logical,
                            "backend_qubits": logical,
                            "seed_transpiler": seed,
                            "semantic_pass": True,
                            "total_direct_mcx": mcx,
                            "compiled_touched_qubits": touched,
                            "extra_physical_qubits_borrowed": max(0, touched - logical),
                            "strict_width_pass": touched <= logical,
                            "hard_width_cap": True,
                            "order_used_in_circuit_construction": False,
                            "orbit_encoding_used": False,
                            **{
                                k: v
                                for k, v in st.items()
                                if k != "compiled_touched_qubits"
                            },
                        }
                        print(
                            f"  -> touched={touched}/{logical} strict={row['strict_width_pass']} "
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
                            "seed_transpiler": seed,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                        print(f"  -> FAIL {type(exc).__name__}: {exc}")
                    res["rows"].append(row)
                    a.out.parent.mkdir(parents=True, exist_ok=True)
                    a.out.write_text(json.dumps(res, indent=2, default=str) + "\n")

    bst = {}
    cmp = {}
    for m in bits:
        key = str(m)
        bst[key] = {
            tn: {kind: best(res["rows"], tn, kind, m) for kind in ("recycled", "wide")}
            for tn in full
        }
        fr = bst[key]["fez_heavy_hex_topology"]["recycled"]
        fw = bst[key]["fez_heavy_hex_topology"]["wide"]
        nr = bst[key]["nighthawk_square_lattice_topology"]["recycled"]
        nw = bst[key]["nighthawk_square_lattice_topology"]["wide"]
        if all(x is not None for x in (fr, fw, nr, nw)):
            fcz = div(fr["native_cz"], fw["native_cz"])
            ncz = div(nr["native_cz"], nw["native_cz"])
            fd = div(fr["compiled_depth"], fw["compiled_depth"])
            nd = div(nr["compiled_depth"], nw["compiled_depth"])
            cmp[key] = {
                "phase_bits": m,
                "logical_width_recycled": fr["logical_qubits"],
                "logical_width_wide": fw["logical_qubits"],
                "logical_qubits_saved": fw["logical_qubits"] - fr["logical_qubits"],
                "fez_recycled_over_wide_cz_ratio": fcz,
                "nighthawk_recycled_over_wide_cz_ratio": ncz,
                "recycling_cz_ratio_nighthawk_over_fez": div(ncz, fcz),
                "fez_recycled_over_wide_depth_ratio": fd,
                "nighthawk_recycled_over_wide_depth_ratio": nd,
                "recycling_depth_ratio_nighthawk_over_fez": div(nd, fd),
                "recycled_nighthawk_over_fez_cz_ratio": div(
                    nr["native_cz"], fr["native_cz"]
                ),
                "recycled_nighthawk_over_fez_depth_ratio": div(
                    nr["compiled_depth"], fr["compiled_depth"]
                ),
                "wide_nighthawk_over_fez_cz_ratio": div(
                    nw["native_cz"], fw["native_cz"]
                ),
                "wide_nighthawk_over_fez_depth_ratio": div(
                    nw["compiled_depth"], fw["compiled_depth"]
                ),
            }

    res["best_strict"] = bst
    res["comparisons"] = cmp
    a.out.write_text(json.dumps(res, indent=2, default=str) + "\n")

    print("\n===== STRICT SUBGRAPH COMPARISON SUMMARY =====")
    for m in bits:
        c = cmp.get(str(m))
        if c is None:
            print(f"bits={m}: missing strict result")
            continue
        print(
            f"bits={m}: width {c['logical_width_wide']}->{c['logical_width_recycled']} "
            f"saved={c['logical_qubits_saved']} | "
            f"R/W CZ Fez={c['fez_recycled_over_wide_cz_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_recycled_over_wide_cz_ratio']:.4f} "
            f"amp={c['recycling_cz_ratio_nighthawk_over_fez']:.4f} | "
            f"R/W depth Fez={c['fez_recycled_over_wide_depth_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_recycled_over_wide_depth_ratio']:.4f} "
            f"amp={c['recycling_depth_ratio_nighthawk_over_fez']:.4f}"
        )

    print("\n===== BEST STRICT ROWS =====")
    for m in bits:
        for tn in full:
            for kind in ("recycled", "wide"):
                print(
                    f"bits={m} topology={tn} kind={kind} "
                    f"{json.dumps(compact(bst[str(m)][tn][kind]), sort_keys=True)}"
                )

    print(f"\nwrote {a.out}\nNO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
