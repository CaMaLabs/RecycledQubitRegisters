#!/usr/bin/env python3
"""Analyze an independent placement-replication JSON, excluding patch 0.

The placement optimizer always includes patch 0 as the deterministic dense patch.
That patch is shared across discovery and replication runs, so this analyzer treats
only stochastic patches (patch_index > 0) as the primary independent replication
set.  It reports both best-of-fresh-placement and median fresh-placement recycled
versus wide ratios for each topology and phase precision.

Input is produced by `ibm_nighthawk_placement_optimization_audit.py` with a fresh
`--subgraph-seed` and a distinct output path.  No QPU access is used here.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def div(a: float, b: float):
    return None if not b else float(a / b)


def best(rows: list[dict]) -> dict | None:
    good = [r for r in rows if r.get("success")]
    return min(
        good,
        key=lambda r: (r["native_cz"], r["compiled_depth"], r.get("patch_index", 0)),
    ) if good else None


def med(rows: list[dict], key: str):
    vals = [float(r[key]) for r in rows if r.get("success")]
    return statistics.median(vals) if vals else None


def compact(r: dict | None):
    if r is None:
        return None
    keys = (
        "topology", "kind", "phase_bits", "logical_qubits", "patch_index",
        "patch_undirected_edges", "patch_mean_degree", "seed_transpiler",
        "native_cz", "compiled_depth", "compiled_size",
    )
    return {k: r.get(k) for k in keys}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=Path("results/qubit_recycling/ibm_nighthawk_placement_replication.json"),
    )
    args = ap.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    rows = [
        r for r in data.get("rows", [])
        if r.get("success") and int(r.get("patch_index", 0)) > 0
    ]
    if not rows:
        raise SystemExit("no successful stochastic replication rows found")

    bits_list = sorted({int(r["phase_bits"]) for r in rows})
    topologies = sorted({str(r["topology"]) for r in rows})

    print("PRIMARY REPLICATION SET: stochastic patches only (patch_index > 0)")
    print(f"input={args.input}")

    print("\n===== FRESH-ONLY REPLICATION SUMMARY =====")
    for bits in bits_list:
        print(f"bits={bits}")
        for topology in topologies:
            rr = [r for r in rows if r["phase_bits"] == bits and r["topology"] == topology and r["kind"] == "recycled"]
            ww = [r for r in rows if r["phase_bits"] == bits and r["topology"] == topology and r["kind"] == "wide"]
            rb, wb = best(rr), best(ww)
            if rb is None or wb is None:
                print(f"  topology={topology}: missing result")
                continue
            best_cz = div(rb["native_cz"], wb["native_cz"])
            best_depth = div(rb["compiled_depth"], wb["compiled_depth"])
            med_cz = div(med(rr, "native_cz"), med(ww, "native_cz"))
            med_depth = div(med(rr, "compiled_depth"), med(ww, "compiled_depth"))
            print(
                f"  topology={topology} width={wb['logical_qubits']}->{rb['logical_qubits']} "
                f"best_R/W_CZ={best_cz:.4f} best_R/W_depth={best_depth:.4f} "
                f"median_R/W_CZ={med_cz:.4f} median_R/W_depth={med_depth:.4f}"
            )

    print("\n===== FRESH-ONLY BEST PLACEMENTS =====")
    for bits in bits_list:
        for topology in topologies:
            for kind in ("recycled", "wide"):
                subset = [
                    r for r in rows
                    if r["phase_bits"] == bits and r["topology"] == topology and r["kind"] == kind
                ]
                print(
                    f"bits={bits} topology={topology} kind={kind} "
                    f"{json.dumps(compact(best(subset)), sort_keys=True)}"
                )

    print("\nInterpretation rule: best-of-fresh-placement ratios test whether placement-aware search can reproduce the discovery advantage; median ratios describe typical fresh stochastic placement behavior. This remains a compiler/topology proxy, not a calibrated QPU result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
