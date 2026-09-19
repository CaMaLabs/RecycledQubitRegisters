#!/usr/bin/env python3
"""Benchmark semantic/factored Boolean implementations of the frozen TCT predicate.

This is a zero-QPU, fixed-instance compiler experiment.  It starts from the same
classification-exact TCT arithmetic specification as the other search audits,
then compares several exact phase-oracle realizations of the 8 marked parameter
assignments:

1. direct eight-minterm marking;
2. the four-cube disjoint cover from the Boolean-compression audit;
3. a minimum-cube XOR/ESOP representation after factoring all parameter bits
   common to every marked state;
4. shared-common-control versions of the four-cube and ESOP predicates using one
   clean ancilla, so the common controls are computed only once per Grover round.

The ESOP representation is derived exhaustively from the local truth table; it
is not hard-coded from the observed answer.  Every candidate oracle is verified
against all 2^9 parameter-register basis states before compilation.

This remains fixed-instance truth-table synthesis, not a scalable coherent
surrogate evaluation and not evidence of end-to-end quantum advantage.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

from qiskit import QuantumCircuit

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_boolean_oracle_compression as audit
import benchmark_tct_reversible_arithmetic_oracle as arithmetic

DEFAULT_OUT = ROOT / "results" / "tct_surrogate_search" / "tct_semantic_factored_oracle.json"
REV = "2026-09-18-tct-semantic-factored-oracle-v1"


def cube_matches(cube: tuple[int, ...], state: int) -> bool:
    return all(v < 0 or ((state >> bit) & 1) == v for bit, v in enumerate(cube))


def common_constraints(marked: list[int], n: int) -> dict[int, int]:
    out = {}
    for bit in range(n):
        vals = {((state >> bit) & 1) for state in marked}
        if len(vals) == 1:
            out[bit] = next(iter(vals))
    return out


def local_state(state: int, local_bits: list[int]) -> int:
    out = 0
    for j, bit in enumerate(local_bits):
        out |= ((state >> bit) & 1) << j
    return out


def local_cube_mask(cube: tuple[int, ...]) -> int:
    mask = 0
    for state in range(1 << len(cube)):
        if cube_matches(cube, state):
            mask |= 1 << state
    return mask


def minimum_esop(local_marked: set[int], local_n: int) -> list[tuple[int, ...]]:
    """Minimum-cube generalized ESOP by 0/1 subset DP over all local cubes."""
    target = sum(1 << s for s in local_marked)
    cubes = []
    for cube in itertools.product((-1, 0, 1), repeat=local_n):
        mask = local_cube_mask(cube)
        if mask == 0:
            continue
        lits = sum(v >= 0 for v in cube)
        cubes.append((cube, mask, lits))

    # dp[truth_mask] = ((cube_count, literal_square_sum, literals), selected)
    dp: dict[int, tuple[tuple[int, int, int], list[tuple[int, ...]]]] = {
        0: ((0, 0, 0), [])
    }
    for cube, mask, lits in cubes:
        snapshot = list(dp.items())
        for cur, (cost, selected) in snapshot:
            nxt = cur ^ mask
            new_cost = (cost[0] + 1, cost[1] + lits * lits, cost[2] + lits)
            prev = dp.get(nxt)
            if prev is None or new_cost < prev[0]:
                dp[nxt] = (new_cost, selected + [cube])
    if target not in dp:
        raise RuntimeError("no ESOP representation found")
    return dp[target][1]


def merge_local_cube(
    local_cube: tuple[int, ...], local_bits: list[int], common: dict[int, int], n: int
) -> tuple[int, ...]:
    full = [-1] * n
    for bit, value in common.items():
        full[bit] = value
    for j, bit in enumerate(local_bits):
        full[bit] = local_cube[j]
    return tuple(full)


def strip_common_cube(
    full_cube: tuple[int, ...], local_bits: list[int], common: dict[int, int]
) -> tuple[int, ...]:
    for bit, value in common.items():
        if full_cube[bit] != value:
            raise RuntimeError("disjoint cover cube does not preserve frozen common constraint")
    return tuple(full_cube[bit] for bit in local_bits)


def verify_xor_cubes(cubes: list[tuple[int, ...]], marked: set[int], n: int) -> None:
    observed = set()
    for state in range(1 << n):
        parity = 0
        for cube in cubes:
            parity ^= int(cube_matches(cube, state))
        if parity:
            observed.add(state)
    if observed != marked:
        raise AssertionError(
            f"oracle truth-table verification failed: observed={sorted(observed)} expected={sorted(marked)}"
        )


def phase_on_active(qc: QuantumCircuit, active: list[int]) -> None:
    if not active:
        raise RuntimeError("empty active phase condition")
    if len(active) == 1:
        qc.z(active[0])
        return
    target = active[-1]
    qc.h(target)
    qc.mcx(active[:-1], target)
    qc.h(target)


def compute_common(qc: QuantumCircuit, params: list[int], anc: int, common: dict[int, int]) -> None:
    zeros = [params[bit] for bit, value in common.items() if value == 0]
    controls = [params[bit] for bit in sorted(common)]
    for q in zeros:
        qc.x(q)
    qc.mcx(controls, anc)
    for q in reversed(zeros):
        qc.x(q)


def apply_local_cube_with_common_anc(
    qc: QuantumCircuit,
    params: list[int],
    anc: int,
    local_bits: list[int],
    cube: tuple[int, ...],
) -> None:
    fixed = [(local_bits[j], v) for j, v in enumerate(cube) if v >= 0]
    zeros = [params[bit] for bit, value in fixed if value == 0]
    active = [anc] + [params[bit] for bit, _ in fixed]
    for q in zeros:
        qc.x(q)
    phase_on_active(qc, active)
    for q in reversed(zeros):
        qc.x(q)


def build_variant(
    n: int,
    marked: list[int],
    full_cubes: list[tuple[int, ...]] | None,
    rounds: int,
    factored: bool = False,
    local_cubes: list[tuple[int, ...]] | None = None,
    local_bits: list[int] | None = None,
    common: dict[int, int] | None = None,
) -> QuantumCircuit:
    total = n + (1 if factored else 0)
    qc = QuantumCircuit(total)
    params = list(range(n))
    qc.h(params)
    anc = n if factored else None

    for _ in range(rounds):
        if factored:
            assert anc is not None and local_cubes is not None and local_bits is not None and common is not None
            compute_common(qc, params, anc, common)
            for cube in local_cubes:
                apply_local_cube_with_common_anc(qc, params, anc, local_bits, cube)
            compute_common(qc, params, anc, common)  # uncompute
        elif full_cubes is None:
            for state in marked:
                audit.apply_exact_state_phase(qc, params, state)
        else:
            for cube in full_cubes:
                audit.apply_cube_phase(qc, params, cube)
        audit.diffuser(qc, params)
    return qc


def compile_probe(qc: QuantumCircuit, level: int, seed: int, profile: str) -> dict:
    return audit.compile_probe(qc, level, seed, profile)


def decode_marked(spec: dict, enc: dict) -> tuple[list[int], list[dict]]:
    widths = spec["parameter_register_bits"]
    rows = enc["rows"]
    marked_indices = [int(x) for x in spec["marked_indices"]]
    states = sorted(audit.compose_state(rows[i], widths) for i in marked_indices)
    decoded = []
    books = spec["parameter_codebooks"]
    lookup = {
        key: {int(row["code"]): float(row["value"]) for row in val}
        for key, val in books.items()
    }
    for i in marked_indices:
        row = rows[i]
        decoded.append(
            {
                "state": audit.compose_state(row, widths),
                "standing_bias": lookup["standing_bias"][int(row["bias_code"])],
                "boost_reduction": lookup["boost_reduction"][int(row["boost_code"])],
                "false_trigger_cost_multiplier": lookup["false_trigger_cost_multiplier"][int(row["false_code"])],
                "event_rate_multiplier": lookup["event_rate_multiplier"][int(row["event_code"])],
            }
        )
    return states, sorted(decoded, key=lambda x: x["state"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--grover-rounds", type=int, default=1)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--seed-transpiler", type=int, default=8776)
    ap.add_argument("--profile", default="auto")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if args.grover_rounds < 1:
        raise SystemExit("--grover-rounds must be >= 1")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    enc = arithmetic.factorized_encoding(spec)
    widths = spec["parameter_register_bits"]
    n = int(widths["total_parameter_bits"])
    marked, decoded = decode_marked(spec, enc)
    marked_set = set(marked)

    valid = audit.valid_cubes(n, frozenset(marked))
    disjoint_cover_rows = audit.exact_cover(valid, marked, "cube_count")
    disjoint_full = [tuple(row["cube"]) for row in disjoint_cover_rows]

    common = common_constraints(marked, n)
    local_bits = [bit for bit in range(n) if bit not in common]
    local_marked = {local_state(state, local_bits) for state in marked}
    esop_local = minimum_esop(local_marked, len(local_bits))
    esop_full = [merge_local_cube(cube, local_bits, common, n) for cube in esop_local]
    disjoint_local = [strip_common_cube(cube, local_bits, common) for cube in disjoint_full]

    verify_xor_cubes(disjoint_full, marked_set, n)
    verify_xor_cubes(esop_full, marked_set, n)

    variants = {
        "direct_eight_minterm": build_variant(n, marked, None, args.grover_rounds),
        "four_cube_disjoint": build_variant(n, marked, disjoint_full, args.grover_rounds),
        "three_term_esop_direct": build_variant(n, marked, esop_full, args.grover_rounds),
        "four_cube_common_factored": build_variant(
            n, marked, None, args.grover_rounds, True, disjoint_local, local_bits, common
        ),
        "three_term_esop_common_factored": build_variant(
            n, marked, None, args.grover_rounds, True, esop_local, local_bits, common
        ),
    }

    compiled = {
        name: compile_probe(qc, args.optimization_level, args.seed_transpiler, args.profile)
        for name, qc in variants.items()
    }
    best = min(compiled, key=lambda name: (compiled[name]["native_cz"], compiled[name]["compiled_depth"], name))

    print("===== TCT SEMANTIC FACTORED ORACLE =====")
    print(f"marked_states={marked}")
    print(f"common_constraints={{{', '.join(f'q{b}={v}' for b, v in sorted(common.items()))}}}")
    print(f"local_bits={local_bits} esop_terms={len(esop_local)}")
    for cube in esop_local:
        print("  local_esop=" + audit.compact_cube(cube))
    print("semantic_marked_rows=" + json.dumps(decoded, sort_keys=True))

    print("\n===== SEMANTIC ORACLE COMPILER COMPARISON =====")
    for name, row in compiled.items():
        print(
            f"{name}: width={variants[name].num_qubits} CZ={row['native_cz']} "
            f"depth={row['compiled_depth']} size={row['compiled_size']} "
            f"weighted_edges={row['weighted_edge_count']}"
        )
    baseline = compiled["four_cube_disjoint"]
    brow = compiled[best]
    print(
        f"best={best} CZ_ratio_vs_four_cube={brow['native_cz']/baseline['native_cz']:.6f} "
        f"depth_ratio_vs_four_cube={brow['compiled_depth']/baseline['compiled_depth']:.6f}"
    )

    result = {
        "experiment": "tct_semantic_factored_oracle_v1",
        "script_revision": REV,
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "grover_rounds": args.grover_rounds,
        "marked_states": marked,
        "decoded_marked_rows": decoded,
        "common_constraints": {str(k): int(v) for k, v in sorted(common.items())},
        "local_bits": local_bits,
        "disjoint_cover": [audit.compact_cube(c) for c in disjoint_full],
        "minimum_esop_local": [audit.compact_cube(c) for c in esop_local],
        "minimum_esop_full": [audit.compact_cube(c) for c in esop_full],
        "compiled": compiled,
        "best_variant": best,
        "claim_boundary": (
            "Fixed-instance Boolean/ESOP synthesis of a frozen TCT marked predicate. "
            "Shared-control and ESOP gains do not replace coherent surrogate evaluation "
            "and do not establish end-to-end quantum advantage or fusion validation."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
