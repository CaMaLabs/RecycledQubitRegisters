#!/usr/bin/env python3
"""Audit fixed-instance Boolean compression of the exact TCT low-loss predicate.

This is deliberately separate from the coherent arithmetic oracle.  It reads the
same frozen fusion arithmetic specification, reconstructs the exact 8 marked
parameter assignments, and searches the full 9-bit Boolean cube space for
implicants that cover only marked states.  It then finds two disjoint exact
covers and compiles them against the direct eight-minterm table oracle.

This is a fixed-instance oracle-compression experiment, not a scalable surrogate
implementation.  Any gain here exploits the frozen 320-scenario truth table and
must not be presented as end-to-end quantum advantage.

No IBM service is opened and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "hardware"
if str(HARDWARE) not in sys.path:
    sys.path.insert(0, str(HARDWARE))

import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_recycled_interaction_graph_mapper as mapper
import benchmark_tct_reversible_arithmetic_oracle as arithmetic

DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_boolean_oracle_compression.json"
REV = "2026-09-18-tct-boolean-oracle-compression-v1"


def compose_state(row: dict, widths: dict[str, int]) -> int:
    """Compose the circuit's little-endian parameter-register basis state."""
    cursor = 0
    value = 0
    fields = (
        ("bias_code", "standing_bias"),
        ("boost_code", "boost_reduction"),
        ("false_code", "false_trigger_cost_multiplier"),
        ("event_code", "event_rate_multiplier"),
    )
    for row_key, width_key in fields:
        width = int(widths[width_key])
        value |= int(row[row_key]) << cursor
        cursor += width
    return value


def cube_states(cube: tuple[int, ...]) -> frozenset[int]:
    base = 0
    free = []
    for bit, v in enumerate(cube):
        if v < 0:
            free.append(bit)
        elif v:
            base |= 1 << bit
    out = []
    for mask in range(1 << len(free)):
        state = base
        for j, bit in enumerate(free):
            if (mask >> j) & 1:
                state |= 1 << bit
        out.append(state)
    return frozenset(out)


def valid_cubes(n: int, marked: frozenset[int]) -> list[dict]:
    """Enumerate every Boolean cube whose full support lies inside marked."""
    by_coverage: dict[frozenset[int], dict] = {}
    for cube in itertools.product((-1, 0, 1), repeat=n):
        if all(v < 0 for v in cube):
            continue
        covered = cube_states(cube)
        if not covered or not covered.issubset(marked):
            continue
        literals = sum(v >= 0 for v in cube)
        row = {
            "cube": cube,
            "covered": covered,
            "literals": literals,
        }
        prev = by_coverage.get(covered)
        if prev is None or (literals, cube) < (prev["literals"], prev["cube"]):
            by_coverage[covered] = row
    return list(by_coverage.values())


def exact_cover(cubes: list[dict], marked: list[int], mode: str) -> list[dict]:
    pos = {state: i for i, state in enumerate(marked)}
    candidates = []
    for row in cubes:
        cover_mask = 0
        for state in row["covered"]:
            cover_mask |= 1 << pos[state]
        lit = int(row["literals"])
        if mode == "cube_count":
            cost = (1, lit * lit, lit)
        elif mode == "literal_square":
            cost = (lit * lit, 1, lit)
        else:
            raise ValueError(mode)
        candidates.append((cover_mask, cost, row))

    full = (1 << len(marked)) - 1
    # dp[covered_mask] = (aggregate_cost_tuple, selected_rows)
    dp: dict[int, tuple[tuple[int, int, int], list[dict]]] = {0: ((0, 0, 0), [])}
    for mask in range(full + 1):
        if mask not in dp:
            continue
        cur_cost, cur_rows = dp[mask]
        for cover_mask, cost, row in candidates:
            if mask & cover_mask:
                continue  # enforce disjoint cubes so phase flips never cancel
            new_mask = mask | cover_mask
            new_cost = tuple(cur_cost[i] + cost[i] for i in range(3))
            prev = dp.get(new_mask)
            if prev is None or new_cost < prev[0]:
                dp[new_mask] = (new_cost, cur_rows + [row])
    if full not in dp:
        raise RuntimeError("no disjoint exact Boolean cover found")
    return dp[full][1]


def apply_cube_phase(qc: QuantumCircuit, qubits: list[int], cube: tuple[int, ...]) -> None:
    fixed = [i for i, v in enumerate(cube) if v >= 0]
    if not fixed:
        raise RuntimeError("all-don't-care cube is invalid for this predicate")
    zero_qubits = [qubits[i] for i in fixed if cube[i] == 0]
    active = [qubits[i] for i in fixed]
    for q in zero_qubits:
        qc.x(q)
    if len(active) == 1:
        qc.z(active[0])
    else:
        target = active[-1]
        qc.h(target)
        qc.mcx(active[:-1], target)
        qc.h(target)
    for q in reversed(zero_qubits):
        qc.x(q)


def apply_exact_state_phase(qc: QuantumCircuit, qubits: list[int], state: int) -> None:
    cube = tuple((state >> i) & 1 for i in range(len(qubits)))
    apply_cube_phase(qc, qubits, cube)


def diffuser(qc: QuantumCircuit, q: list[int]) -> None:
    qc.h(q)
    qc.x(q)
    qc.h(q[-1])
    qc.mcx(q[:-1], q[-1])
    qc.h(q[-1])
    qc.x(q)
    qc.h(q)


def build_round(n: int, marked: list[int], cover: list[dict] | None) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    q = list(range(n))
    qc.h(q)
    if cover is None:
        for state in marked:
            apply_exact_state_phase(qc, q, state)
    else:
        for row in cover:
            apply_cube_phase(qc, q, row["cube"])
    diffuser(qc, q)
    return qc


def compile_probe(qc: QuantumCircuit, level: int, seed: int, profile: str) -> dict:
    backend = topo.generic(qc.num_qubits, mapper.full_coupling(qc.num_qubits))
    compiled, elapsed = mapper.compile_circuit(
        qc, backend, profile, level, seed, list(range(qc.num_qubits))
    )
    pair_weights, meta = mapper.extract_two_qubit_interactions(compiled)
    stats = mapper.compiled_stats(qc, compiled, elapsed)
    return {
        "weighted_edge_count": int(meta["weighted_edge_count"]),
        "total_two_qubit_weight": float(meta["total_two_qubit_weight"]),
        "pair_weights": [
            {"i": int(i), "j": int(j), "weight": float(w)}
            for (i, j), w in sorted(pair_weights.items())
        ],
        **stats,
    }


def compact_cube(cube: tuple[int, ...]) -> str:
    # Print MSB first for readability; '-' means don't care.
    return "".join("-" if v < 0 else str(v) for v in reversed(cube))


def cover_summary(rows: list[dict]) -> dict:
    return {
        "cube_count": len(rows),
        "total_literals": sum(int(r["literals"]) for r in rows),
        "literal_square_sum": sum(int(r["literals"]) ** 2 for r in rows),
        "cubes": [
            {
                "pattern_msb_first": compact_cube(r["cube"]),
                "literals": int(r["literals"]),
                "covered_states": sorted(int(x) for x in r["covered"]),
            }
            for r in rows
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    enc = arithmetic.factorized_encoding(spec)
    if not enc["classification_exact"]:
        raise RuntimeError("factorized arithmetic encoding is not classification-exact")

    widths = spec["parameter_register_bits"]
    n = int(widths["total_parameter_bits"])
    rows = enc["rows"]
    marked_indices = [int(x) for x in spec["marked_indices"]]
    marked_states = sorted(compose_state(rows[i], widths) for i in marked_indices)
    marked_set = frozenset(marked_states)
    if len(marked_set) != len(marked_indices):
        raise RuntimeError("marked parameter assignments are not unique")

    cubes = valid_cubes(n, marked_set)
    cover_count = exact_cover(cubes, marked_states, "cube_count")
    cover_lit2 = exact_cover(cubes, marked_states, "literal_square")

    variants = {
        "direct_eight_minterm_table": None,
        "min_cube_count_cover": cover_count,
        "min_literal_square_cover": cover_lit2,
    }
    compiled = {}
    for name, cover in variants.items():
        qc = build_round(n, marked_states, cover)
        compiled[name] = compile_probe(
            qc, args.optimization_level, args.seed_transpiler, args.profile
        )

    best_name = min(
        compiled,
        key=lambda name: (
            compiled[name]["native_cz"],
            compiled[name]["compiled_depth"],
            name,
        ),
    )

    print("===== TCT BOOLEAN ORACLE COMPRESSION AUDIT =====")
    print(f"logical_width={n} marked={len(marked_states)} marked_states={marked_states}")
    for label, cover in (("min_cube_count", cover_count), ("min_literal_square", cover_lit2)):
        summary = cover_summary(cover)
        print(
            f"{label}: cubes={summary['cube_count']} total_literals={summary['total_literals']} "
            f"literal_square_sum={summary['literal_square_sum']}"
        )
        for row in summary["cubes"]:
            print(
                f"  cube={row['pattern_msb_first']} literals={row['literals']} "
                f"covers={row['covered_states']}"
            )

    print("\n===== BOOLEAN ORACLE COMPILER COMPARISON =====")
    for name, row in compiled.items():
        print(
            f"{name}: CZ={row['native_cz']} depth={row['compiled_depth']} "
            f"size={row['compiled_size']} weighted_edges={row['weighted_edge_count']} "
            f"total_2q_weight={row['total_two_qubit_weight']:.0f}"
        )
    base = compiled["direct_eight_minterm_table"]
    best = compiled[best_name]
    print(
        f"best={best_name} CZ_ratio_vs_direct={best['native_cz']/base['native_cz']:.6f} "
        f"depth_ratio_vs_direct={best['compiled_depth']/base['compiled_depth']:.6f}"
    )

    result = {
        "experiment": "tct_boolean_oracle_compression_v1",
        "script_revision": REV,
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "logical_width": n,
        "marked_states_parameter_encoding": marked_states,
        "valid_cube_count": len(cubes),
        "covers": {
            "min_cube_count": cover_summary(cover_count),
            "min_literal_square": cover_summary(cover_lit2),
        },
        "compiled": compiled,
        "best_compiled_variant": best_name,
        "claim_boundary": (
            "Fixed-instance Boolean synthesis of the frozen TCT marked predicate. "
            "This can exploit the known 320-scenario truth table and is not a scalable "
            "replacement for coherent surrogate evaluation. It is an oracle-compression "
            "audit and lower-cost compiler challenger only."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
