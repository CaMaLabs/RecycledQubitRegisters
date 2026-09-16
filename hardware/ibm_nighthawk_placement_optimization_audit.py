#!/usr/bin/env python3
"""Zero-QPU placement-optimization audit for recycled vs wide QPE.

The subgraph-ensemble audit showed that the exact-width 8-qubit recycled circuit
is substantially more placement-sensitive than the wide circuit.  This follow-up
searches a larger ensemble of connected exact-width patches on Fez and on the
Nighthawk topology source (authenticated Phoenix metadata when available,
otherwise the clearly labeled 10x12 square-lattice proxy), compiles every patch,
and compares the best placement found for recycled and wide circuits.

Every compile backend has exactly the source-circuit width, so HLS/routing cannot
borrow extra physical qubits.  No Sampler is instantiated and no QPU job is
submitted.  This remains a compiler/topology proxy, not calibrated hardware
performance and not scalable RSA modular arithmetic.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_shor35_generic_permutation_direct_transposition as direct

REV = "2026-09-16-placement-optimization-v1"
OUT = Path("results/qubit_recycling/ibm_nighthawk_placement_optimization_audit.json")


def div(a, b):
    return None if not b else float(a / b)


def summary(vals):
    xs = sorted(float(x) for x in vals)
    if not xs:
        return None
    return {
        "count": len(xs),
        "min": min(xs),
        "median": statistics.median(xs),
        "mean": statistics.fmean(xs),
        "max": max(xs),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zero-QPU exact-width placement optimization audit"
    )
    ap.add_argument("--fez-backend", default="ibm_fez")
    ap.add_argument("--phase-bits", nargs="+", type=int, default=[16, 32, 64])
    ap.add_argument("--scratch-bits", type=int, default=1)
    ap.add_argument("--subgraph-samples", type=int, default=16)
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

    print("ZERO-QPU PLACEMENT OPTIMIZATION AUDIT: no Sampler or QPU job is used.")
    print(f"Fez={fez.name} Nighthawk_source={night_src['mode']}")
    if night_src.get("proxy"):
        print("IMPORTANT: Nighthawk side is a 10x12 square-lattice PROXY, not exact Phoenix.")
    print(
        f"phase_bits={bits_list} patches={args.subgraph_samples} "
        f"transpiler_seeds={transpiler_seeds}"
    )

    result = {
        "experiment": "ibm_nighthawk_placement_optimization_audit_v1",
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
            "Every compile backend has exactly the source-circuit width; extra qubit borrowing is impossible."
        ),
        "scope_boundary": (
            "Topology/compiler placement proxy only; no calibration, timing, reset-speed, "
            "fidelity, or QPU execution. N=35 remains exact small-N full-register synthesis."
        ),
        "rows": [],
    }

    patch_cache = {}

    for bits in bits_list:
        if not direct.semantic_summary(bits)["pass"]:
            raise RuntimeError(f"semantic validation failed at phase_bits={bits}")

        for kind in ("recycled", "wide"):
            qc, rounds, _ = width.build(kind, bits, args.scratch_bits, use_measure2=False)
            logical = int(qc.num_qubits)
            mcx = sum(int(r.get("direct_mcx", 0)) for r in rounds)
            print(f"\n===== bits={bits} kind={kind} width={logical}q direct_mcx={mcx} =====")

            for topology_name, full_cm in topologies.items():
                cache_key = (topology_name, logical)
                if cache_key not in patch_cache:
                    salt = args.subgraph_seed + (
                        0 if topology_name.startswith("fez") else 1_000_003
                    )
                    patch_cache[cache_key] = ens.patch_ensemble(
                        full_cm, logical, args.subgraph_samples, salt
                    )

                for patch in patch_cache[cache_key]:
                    nodes = patch["nodes"]
                    stats = patch["stats"]
                    subcm = cap.relabeled_subgraph(full_cm, nodes)
                    backend = topo.generic(logical, subcm)
                    good = []

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
                            good.append({
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
                                "compiled_touched_qubits": touched,
                                **{k: v for k, v in st.items() if k != "compiled_touched_qubits"},
                            })
                        except Exception as exc:
                            result["rows"].append({
                                "success": False,
                                "topology": topology_name,
                                "kind": kind,
                                "phase_bits": bits,
                                "logical_qubits": logical,
                                "patch_index": int(patch["patch_index"]),
                                "seed_transpiler": int(transpiler_seed),
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            })

                    if good:
                        best_seed = min(
                            good,
                            key=lambda r: (
                                r["native_cz"],
                                r["compiled_depth"],
                                r["seed_transpiler"],
                            ),
                        )
                        result["rows"].append(best_seed)
                        print(
                            f"topology={topology_name} patch={patch['patch_index']} "
                            f"edges={stats['undirected_edges']} deg={stats['degree_mean']:.3f} "
                            f"CZ={best_seed['native_cz']} depth={best_seed['compiled_depth']}"
                        )

                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    optimized = {}
    comparisons = {}
    for bits in bits_list:
        key = str(bits)
        optimized[key] = {}
        for topology_name in topologies:
            optimized[key][topology_name] = {}
            for kind in ("recycled", "wide"):
                rows = [
                    r for r in result["rows"]
                    if r.get("success")
                    and r["phase_bits"] == bits
                    and r["topology"] == topology_name
                    and r["kind"] == kind
                ]
                if not rows:
                    optimized[key][topology_name][kind] = None
                    continue
                best_row = min(
                    rows,
                    key=lambda r: (
                        r["native_cz"],
                        r["compiled_depth"],
                        r["patch_index"],
                    ),
                )
                optimized[key][topology_name][kind] = {
                    "best": best_row,
                    "cz_distribution": summary([r["native_cz"] for r in rows]),
                    "depth_distribution": summary([r["compiled_depth"] for r in rows]),
                }

        fr = optimized[key]["fez_heavy_hex_topology"]["recycled"]
        fw = optimized[key]["fez_heavy_hex_topology"]["wide"]
        nr = optimized[key]["nighthawk_square_lattice_topology"]["recycled"]
        nw = optimized[key]["nighthawk_square_lattice_topology"]["wide"]
        if all(x is not None for x in (fr, fw, nr, nw)):
            frb, fwb, nrb, nwb = fr["best"], fw["best"], nr["best"], nw["best"]
            comparisons[key] = {
                "phase_bits": bits,
                "recycled_width": int(frb["logical_qubits"]),
                "wide_width": int(fwb["logical_qubits"]),
                "qubits_saved": int(fwb["logical_qubits"] - frb["logical_qubits"]),
                "fez_best_recycled_over_wide_cz_ratio": div(frb["native_cz"], fwb["native_cz"]),
                "nighthawk_best_recycled_over_wide_cz_ratio": div(nrb["native_cz"], nwb["native_cz"]),
                "fez_best_recycled_over_wide_depth_ratio": div(frb["compiled_depth"], fwb["compiled_depth"]),
                "nighthawk_best_recycled_over_wide_depth_ratio": div(nrb["compiled_depth"], nwb["compiled_depth"]),
                "recycled_nighthawk_over_fez_best_cz_ratio": div(nrb["native_cz"], frb["native_cz"]),
                "wide_nighthawk_over_fez_best_cz_ratio": div(nwb["native_cz"], fwb["native_cz"]),
            }

    result["optimized"] = optimized
    result["comparisons"] = comparisons
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n")

    print("\n===== PLACEMENT-OPTIMIZED SUMMARY =====")
    for bits in bits_list:
        c = comparisons.get(str(bits))
        if not c:
            print(f"bits={bits}: missing result")
            continue
        print(
            f"bits={bits}: width {c['wide_width']}->{c['recycled_width']} "
            f"saved={c['qubits_saved']} | "
            f"best R/W CZ Fez={c['fez_best_recycled_over_wide_cz_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_best_recycled_over_wide_cz_ratio']:.4f} | "
            f"best R/W depth Fez={c['fez_best_recycled_over_wide_depth_ratio']:.4f} "
            f"Nighthawk={c['nighthawk_best_recycled_over_wide_depth_ratio']:.4f}"
        )

    print("\n===== BEST PLACEMENTS =====")
    for bits in bits_list:
        for topology_name in topologies:
            for kind in ("recycled", "wide"):
                obj = optimized[str(bits)][topology_name][kind]
                if obj is None:
                    print(f"bits={bits} topology={topology_name} kind={kind} null")
                    continue
                b = obj["best"]
                print(
                    f"bits={bits} topology={topology_name} kind={kind} "
                    f"patch={b['patch_index']} edges={b['patch_undirected_edges']} "
                    f"mean_degree={b['patch_mean_degree']:.3f} "
                    f"CZ={b['native_cz']} depth={b['compiled_depth']}"
                )

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
