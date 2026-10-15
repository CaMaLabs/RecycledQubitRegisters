#!/usr/bin/env python3
"""Quantify mapping-optimization gain versus unique-placement sensitivity.

Inputs:
1. the current unique-placement robustness JSON; and
2. the independent placement-replication JSON.

The replication file is used only for its *fresh stochastic* optimized search
(patch_index > 0).  The unique-placement file supplies the placement
distribution.  This keeps the project distinction explicit:

- optimized search asks what the intended mapper can deliberately find;
- unique-placement medians/IQR ask how sensitive the architecture is to other
  valid mappings.

No QPU access is used.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


DEFAULT_UNIQUE = Path(
    "results/qubit_recycling/"
    "ibm_fez_vs_nighthawk_unique_placement_robustness.json"
)
DEFAULT_REPLICATION = Path(
    "results/qubit_recycling/ibm_nighthawk_placement_replication.json"
)
DEFAULT_OUT = Path(
    "results/qubit_recycling/ibm_mapping_optimization_gain.json"
)


def best(rows: list[dict]) -> dict | None:
    good = [r for r in rows if r.get("success")]
    if not good:
        return None
    return min(
        good,
        key=lambda r: (
            int(r["native_cz"]),
            int(r["compiled_depth"]),
            int(r.get("patch_index", 0)),
            int(r.get("seed_transpiler", 0)),
        ),
    )


def median(rows: list[dict], key: str):
    vals = [float(r[key]) for r in rows]
    return statistics.median(vals) if vals else None


def quartiles(rows: list[dict], key: str):
    vals = sorted(float(r[key]) for r in rows)
    if not vals:
        return {"q1": None, "median": None, "q3": None, "min": None, "max": None}
    if len(vals) == 1:
        q1 = q3 = vals[0]
    else:
        qs = statistics.quantiles(vals, n=4, method="inclusive")
        q1, q3 = qs[0], qs[2]
    return {
        "q1": q1,
        "median": statistics.median(vals),
        "q3": q3,
        "min": vals[0],
        "max": vals[-1],
    }


def ratio(a, b):
    return None if b in (None, 0) else float(a / b)


def gain(best_value, median_value):
    r = ratio(best_value, median_value)
    return None if r is None else 1.0 - r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unique", type=Path, default=DEFAULT_UNIQUE)
    ap.add_argument("--replication", type=Path, default=DEFAULT_REPLICATION)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    unique = json.loads(args.unique.read_text(encoding="utf-8"))
    repl = json.loads(args.replication.read_text(encoding="utf-8"))

    unique_rows = [
        r for r in unique.get("placement_best", [])
        if r.get("native_cz") is not None and r.get("compiled_depth") is not None
    ]
    fresh = [
        r for r in repl.get("rows", [])
        if r.get("success") and int(r.get("patch_index", 0)) > 0
    ]
    if not unique_rows:
        raise SystemExit("unique-placement file has no placement_best rows")
    if not fresh:
        raise SystemExit("replication file has no fresh stochastic successful rows")

    bits = sorted(
        set(int(r["phase_bits"]) for r in unique_rows)
        & set(int(r["phase_bits"]) for r in fresh)
    )
    topologies = sorted(
        set(str(r["topology"]) for r in unique_rows)
        & set(str(r["topology"]) for r in fresh)
    )
    if not bits or not topologies:
        raise SystemExit("no overlapping phase bits/topologies between inputs")

    out = {
        "experiment": "mapping_optimization_gain_v1",
        "unique_source": str(args.unique),
        "optimized_replication_source": str(args.replication),
        "optimized_definition": (
            "Best successful fresh stochastic replication placement, patch_index>0; "
            "lower native CZ then lower depth."
        ),
        "sensitivity_definition": (
            "Median and IQR over genuinely unique connected placements, after keeping "
            "the best transpiler seed for each placement."
        ),
        "rows": [],
        "architecture_comparisons": [],
        "scope_boundary": (
            "Zero-QPU compiler/topology comparison. Mapping optimization gain is not "
            "a hardware fidelity/runtime gain. Nighthawk remains the labeled square-"
            "lattice proxy unless exact hardware metadata was available in the source."
        ),
    }

    for m in bits:
        for topology in topologies:
            by_kind = {}
            for kind in ("recycled", "wide"):
                ur = [
                    r for r in unique_rows
                    if int(r["phase_bits"]) == m
                    and str(r["topology"]) == topology
                    and str(r["kind"]) == kind
                ]
                rr = [
                    r for r in fresh
                    if int(r["phase_bits"]) == m
                    and str(r["topology"]) == topology
                    and str(r["kind"]) == kind
                ]
                if not ur or not rr:
                    continue
                b = best(rr)
                cz_dist = quartiles(ur, "native_cz")
                depth_dist = quartiles(ur, "compiled_depth")
                row = {
                    "phase_bits": m,
                    "topology": topology,
                    "kind": kind,
                    "logical_qubits": int(ur[0]["logical_qubits"]),
                    "unique_placement_count": len(ur),
                    "optimized_best": {
                        "patch_index": int(b["patch_index"]),
                        "seed_transpiler": int(b["seed_transpiler"]),
                        "native_cz": int(b["native_cz"]),
                        "compiled_depth": int(b["compiled_depth"]),
                    },
                    "unique_native_cz": cz_dist,
                    "unique_compiled_depth": depth_dist,
                    "mapping_optimization_gain_cz": gain(
                        float(b["native_cz"]), cz_dist["median"]
                    ),
                    "mapping_optimization_gain_depth": gain(
                        float(b["compiled_depth"]), depth_dist["median"]
                    ),
                }
                out["rows"].append(row)
                by_kind[kind] = row

            if set(by_kind) == {"recycled", "wide"}:
                r = by_kind["recycled"]
                w = by_kind["wide"]
                out["architecture_comparisons"].append({
                    "phase_bits": m,
                    "topology": topology,
                    "width_wide": w["logical_qubits"],
                    "width_recycled": r["logical_qubits"],
                    "optimized_recycled_over_wide_cz": ratio(
                        r["optimized_best"]["native_cz"],
                        w["optimized_best"]["native_cz"],
                    ),
                    "unique_median_recycled_over_wide_cz": ratio(
                        r["unique_native_cz"]["median"],
                        w["unique_native_cz"]["median"],
                    ),
                    "optimized_recycled_over_wide_depth": ratio(
                        r["optimized_best"]["compiled_depth"],
                        w["optimized_best"]["compiled_depth"],
                    ),
                    "unique_median_recycled_over_wide_depth": ratio(
                        r["unique_compiled_depth"]["median"],
                        w["unique_compiled_depth"]["median"],
                    ),
                })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    print("===== MAPPING-OPTIMIZATION GAIN =====")
    for row in out["rows"]:
        print(
            f"bits={row['phase_bits']} topology={row['topology']} kind={row['kind']} "
            f"CZ best/median={row['optimized_best']['native_cz']}/"
            f"{row['unique_native_cz']['median']:.1f} "
            f"gain={100*row['mapping_optimization_gain_cz']:.2f}% | "
            f"depth best/median={row['optimized_best']['compiled_depth']}/"
            f"{row['unique_compiled_depth']['median']:.1f} "
            f"gain={100*row['mapping_optimization_gain_depth']:.2f}%"
        )

    print("\n===== ARCHITECTURE: OPTIMIZED VS UNIQUE-MEDIAN =====")
    for row in out["architecture_comparisons"]:
        print(
            f"bits={row['phase_bits']} topology={row['topology']} "
            f"width={row['width_wide']}->{row['width_recycled']} | "
            f"R/W CZ optimized={row['optimized_recycled_over_wide_cz']:.4f} "
            f"unique-median={row['unique_median_recycled_over_wide_cz']:.4f} | "
            f"R/W depth optimized={row['optimized_recycled_over_wide_depth']:.4f} "
            f"unique-median={row['unique_median_recycled_over_wide_depth']:.4f}"
        )

    print(f"\nwrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
