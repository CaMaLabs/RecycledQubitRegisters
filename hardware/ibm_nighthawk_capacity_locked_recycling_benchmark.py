#!/usr/bin/env python3
"""Zero-QPU capacity-locked Fez-vs-Nighthawk topology benchmark.

This fixes a limitation in `ibm_nighthawk_topology_recycling_benchmark.py`:
when compiling against the full 120-qubit square-lattice proxy, Qiskit/HLS may
borrow extra backend qubits. That makes every Nighthawk-proxy row fail the
strict-width criterion even though the raw topology result is informative.

Here each source circuit is compiled against an exact-width connected induced
subgraph of each topology. Therefore the backend itself contains exactly the
same number of physical qubits as the source circuit: 8 for recycled, and
7+phase_bits for wide. Extra borrowing is impossible by construction.

The Nighthawk side still uses authenticated ibm_phoenix coupling metadata when
available; otherwise it uses the clearly labeled 10x12 public square-lattice
proxy from the preceding benchmark. This is a topology/compiler proxy only:
no calibration, timing, reset-speed or fidelity prediction is made.

No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler import CouplingMap

import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

REV = "2026-09-16-capacity-locked-topology-v1"
OUT = Path("results/qubit_recycling/ibm_fez_vs_nighthawk_capacity_locked.json")


def adjacency(cm: CouplingMap) -> list[set[int]]:
    n = cm.size()
    adj = [set() for _ in range(n)]
    for u, v in cm.get_edges():
        u, v = int(u), int(v)
        if u == v:
            continue
        adj[u].add(v)
        adj[v].add(u)
    return adj


def induced_stats(adj: list[set[int]], nodes: list[int]) -> dict:
    s = set(nodes)
    degrees = [sum(v in s for v in adj[u]) for u in nodes]
    edges = sum(degrees) // 2
    return {
        "selected_original_nodes": [int(x) for x in nodes],
        "num_qubits": len(nodes),
        "undirected_edges": int(edges),
        "degree_min": int(min(degrees)),
        "degree_mean": float(statistics.fmean(degrees)),
        "degree_max": int(max(degrees)),
        "degree_histogram": {
            str(k): int(sum(d == k for d in degrees)) for k in sorted(set(degrees))
        },
    }


def greedy_connected_nodes(cm: CouplingMap, k: int) -> tuple[list[int], dict]:
    """Choose a deterministic dense connected k-node subgraph.

    We grow a connected set from every possible start. At each step choose a
    frontier node maximizing links into the selected set, then full-graph
    degree. Finally choose the candidate with most internal edges, then highest
    minimum/mean internal degree. This is topology-only and circuit-independent.
    """
    n = cm.size()
    if k < 1 or k > n:
        raise ValueError(f"requested subgraph width {k} outside 1..{n}")
    adj = adjacency(cm)
    full_deg = [len(x) for x in adj]
    candidates = []
    for start in range(n):
        selected = [start]
        chosen = {start}
        while len(selected) < k:
            frontier = set()
            for u in selected:
                frontier.update(adj[u] - chosen)
            if not frontier:
                break
            nxt = max(
                frontier,
                key=lambda v: (
                    sum(u in chosen for u in adj[v]),
                    full_deg[v],
                    -v,
                ),
            )
            selected.append(int(nxt))
            chosen.add(int(nxt))
        if len(selected) != k:
            continue
        st = induced_stats(adj, selected)
        score = (
            st["undirected_edges"],
            st["degree_min"],
            st["degree_mean"],
            -min(selected),
        )
        candidates.append((score, selected, st))
    if not candidates:
        raise RuntimeError(f"could not find connected {k}-node subgraph")
    _, nodes, st = max(candidates, key=lambda x: x[0])
    return nodes, st


def relabeled_subgraph(cm: CouplingMap, nodes: list[int]) -> CouplingMap:
    pos = {old: new for new, old in enumerate(nodes)}
    s = set(nodes)
    undirected = set()
    for u, v in cm.get_edges():
        u, v = int(u), int(v)
        if u == v or u not in s or v not in s:
            continue
        a, b = sorted((pos[u], pos[v]))
        undirected.add((a, b))
    edges = [[x, y] for a, b in sorted(undirected) for x, y in ((a, b), (b, a))]
    sub = CouplingMap(edges)
    while sub.size() < len(nodes):
        sub.graph.add_node(None)
    if sub.size() != len(nodes):
        raise RuntimeError("subgraph relabel width mismatch")
    return sub


def compact(r: dict | None) -> dict | None:
    if r is None:
        return None
    keys = (
        "topology", "kind", "phase_bits", "logical_qubits",
        "compiled_touched_qubits", "seed_transpiler", "native_cz",
        "compiled_depth", "compiled_size", "compile_seconds",
    )
    return {k: r.get(k) for k in keys}


def best(rows: list[dict], topology: str, kind: str, bits: int) -> dict | None:
    subset = [
        r for r in rows
        if r.get("success")
        and r["topology"] == topology
        and r["kind"] == kind
        and r["phase_bits"] == bits
    ]
    return min(
        subset,
        key=lambda r: (r["native_cz"], r["compiled_depth"], r["seed_transpiler"]),
    ) if subset else None


def div(a, b):
    return None if not b else float(a / b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--phase-bits", nargs="+", type=int,
                    default=[4, 8, 12, 16, 20, 24, 32, 40, 48, 64])
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--seeds", default="8776,2026,9401")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    bits_list = sorted(set(int(x) for x in args.phase_bits))
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    if not bits_list or min(bits_list) < 1 or args.scratch_bits < 0 or not seeds:
        raise SystemExit("invalid arguments")

    service = width.ref.ibm_base.make_service()
    max_width = direct.WORK_BITS + max(bits_list) + args.scratch_bits
    fez = width.ref.ibm_base.select_backend(service, max_width, args.fez_backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    night_full, night_src = topo.nighthawk_map(service)
    if max_width > night_full.size():
        raise SystemExit("requested wide precision exceeds Nighthawk width")

    topology_full = {
        "fez_heavy_hex_topology": fez_full,
        "nighthawk_square_lattice_topology": night_full,
    }
    topology_sources = {
        "fez_heavy_hex_topology": {
            "source": "authenticated_ibm_fez_coupling_metadata",
            "backend_name": str(fez.name),
            "proxy": False,
        },
        "nighthawk_square_lattice_topology": {
            "source": night_src,
        },
    }

    print("ZERO-QPU CAPACITY-LOCKED TOPOLOGY BENCHMARK: no Sampler or QPU job is used.")
    print(f"Fez={fez.name} Nighthawk_source={night_src['mode']}")
    if night_src.get("proxy"):
        print("IMPORTANT: Nighthawk side is a 10x12 square-lattice PROXY, not exact Phoenix.")
    print("Each compile target has exactly the source-circuit width; extra qubit borrowing is impossible.")

    result = {
        "experiment": "ibm_fez_vs_nighthawk_capacity_locked_v1",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "N": int(direct.N),
        "base": int(direct.A),
        "work_bits": int(direct.WORK_BITS),
        "scratch_bits": int(args.scratch_bits),
        "phase_bits": bits_list,
        "profile": args.profile,
        "optimization_level": int(args.optimization_level),
        "seeds": seeds,
        "topology_sources": topology_sources,
        "capacity_lock_definition": (
            "Each topology is reduced to a deterministic connected induced subgraph "
            "whose physical width equals the source circuit's logical width."
        ),
        "subgraphs": {},
        "rows": [],
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
        "scope_boundary": (
            "Topology-only compiler proxy with exact-width capacity lock; no calibration, "
            "timing, reset-speed or fidelity model. N=35 remains exact small-N full-register "
            "synthesis, not scalable RSA arithmetic."
        ),
    }

    for bits in bits_list:
        if not direct.semantic_summary(bits)["pass"]:
            raise RuntimeError(f"semantic failure at phase_bits={bits}")
        for kind in ("recycled", "wide"):
            qc, rounds, _ = width.build(kind, bits, args.scratch_bits, use_measure2=False)
            logical = int(qc.num_qubits)
            mcx = sum(int(r.get("direct_mcx", 0)) for r in rounds)
            print(f"\n===== bits={bits} kind={kind} allocated={logical}q direct_mcx={mcx} =====")

            for topology_name, full_cm in topology_full.items():
                nodes, substats = greedy_connected_nodes(full_cm, logical)
                subcm = relabeled_subgraph(full_cm, nodes)
                backend = topo.generic(logical, subcm)
                subkey = f"{bits}:{kind}:{topology_name}"
                result["subgraphs"][subkey] = {
                    **substats,
                    "source_width": logical,
                    "topology": topology_name,
                    "kind": kind,
                    "phase_bits": bits,
                }
                print(
                    f"topology={topology_name} exact_width={logical} "
                    f"edges={substats['undirected_edges']} mean_degree={substats['degree_mean']:.3f}"
                )

                for seed in seeds:
                    print(f"compile topology={topology_name} seed={seed}")
                    try:
                        st = width.compile_one(
                            qc, backend, args.profile, args.optimization_level, seed
                        )
                        touched = int(st["compiled_touched_qubits"])
                        row = {
                            "success": True,
                            "topology": topology_name,
                            "kind": kind,
                            "phase_bits": bits,
                            "logical_qubits": logical,
                            "backend_capacity_qubits": logical,
                            "seed_transpiler": seed,
                            "semantic_pass": True,
                            "total_direct_mcx": mcx,
                            "compiled_touched_qubits": touched,
                            "capacity_lock_pass": touched <= logical,
                            "order_used_in_circuit_construction": False,
                            "orbit_encoding_used": False,
                            **{k: v for k, v in st.items() if k != "compiled_touched_qubits"},
                        }
                        print(
                            f"  -> touched={touched}/{logical} CZ={row['native_cz']} "
                            f"depth={row['compiled_depth']}"
                        )
                    except Exception as exc:
                        row = {
                            "success": False,
                            "topology": topology_name,
                            "kind": kind,
                            "phase_bits": bits,
                            "logical_qubits": logical,
                            "backend_capacity_qubits": logical,
                            "seed_transpiler": seed,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                        print(f"  -> FAIL {type(exc).__name__}: {exc}")
                    result["rows"].append(row)
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    best_rows = {}
    comparisons = {}
    for bits in bits_list:
        key = str(bits)
        best_rows[key] = {}
        for topology_name in topology_full:
            best_rows[key][topology_name] = {}
            for kind in ("recycled", "wide"):
                best_rows[key][topology_name][kind] = best(
                    result["rows"], topology_name, kind, bits
                )

        fr = best_rows[key]["fez_heavy_hex_topology"]["recycled"]
        fw = best_rows[key]["fez_heavy_hex_topology"]["wide"]
        nr = best_rows[key]["nighthawk_square_lattice_topology"]["recycled"]
        nw = best_rows[key]["nighthawk_square_lattice_topology"]["wide"]
        if all(x is not None for x in (fr, fw, nr, nw)):
            fcz = div(fr["native_cz"], fw["native_cz"])
            ncz = div(nr["native_cz"], nw["native_cz"])
            fd = div(fr["compiled_depth"], fw["compiled_depth"])
            nd = div(nr["compiled_depth"], nw["compiled_depth"])
            comparisons[key] = {
                "phase_bits": bits,
                "logical_width_recycled": int(fr["logical_qubits"]),
                "logical_width_wide": int(fw["logical_qubits"]),
                "logical_qubits_saved": int(fw["logical_qubits"] - fr["logical_qubits"]),
                "fez_recycled_over_wide_cz_ratio": fcz,
                "nighthawk_recycled_over_wide_cz_ratio": ncz,
                "relative_recycling_cz_ratio_nighthawk_over_fez": div(ncz, fcz),
                "fez_recycled_over_wide_depth_ratio": fd,
                "nighthawk_recycled_over_wide_depth_ratio": nd,
                "relative_recycling_depth_ratio_nighthawk_over_fez": div(nd, fd),
                "recycled_nighthawk_over_fez_cz_ratio": div(nr["native_cz"], fr["native_cz"]),
                "wide_nighthawk_over_fez_cz_ratio": div(nw["native_cz"], fw["native_cz"]),
                "recycled_nighthawk_over_fez_depth_ratio": div(nr["compiled_depth"], fr["compiled_depth"]),
                "wide_nighthawk_over_fez_depth_ratio": div(nw["compiled_depth"], fw["compiled_depth"]),
            }

    result["best"] = best_rows
    result["comparisons"] = comparisons
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    print("\n===== CAPACITY-LOCKED TOPOLOGY SUMMARY =====")
    for bits in bits_list:
        c = comparisons.get(str(bits))
        if not c:
            print(f"bits={bits}: missing result")
            continue
        print(
            f"bits={bits}: width {c['logical_width_wide']}->{c['logical_width_recycled']} "
            f"saved={c['logical_qubits_saved']} | "
            f"R/W CZ Fez={c['fez_recycled_over_wide_cz_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_recycled_over_wide_cz_ratio']:.4f} "
            f"relative={c['relative_recycling_cz_ratio_nighthawk_over_fez']:.4f} | "
            f"R/W depth Fez={c['fez_recycled_over_wide_depth_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_recycled_over_wide_depth_ratio']:.4f} "
            f"relative={c['relative_recycling_depth_ratio_nighthawk_over_fez']:.4f}"
        )

    print("\n===== BEST CAPACITY-LOCKED ROWS =====")
    for bits in bits_list:
        for topology_name in topology_full:
            for kind in ("recycled", "wide"):
                print(
                    f"bits={bits} topology={topology_name} kind={kind} "
                    f"{json.dumps(compact(best_rows[str(bits)][topology_name][kind]), sort_keys=True)}"
                )

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
