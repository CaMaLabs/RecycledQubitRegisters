#!/usr/bin/env python3
"""Zero-QPU phase-synthesis challenger for the one-round model-derived TCT predicate.

This test keeps the same reduced-order formula, fixed threshold, parameter
codebooks, derived marked predicate, shared common-control ancilla, and Grover
round count.  It changes only how conditional phase reflections are expressed:

* `mcx_h`: the existing H-MCX-H construction;
* `mcphase`: native Qiskit MCPhaseGate(pi) expressions for the local phase terms
  and the 9-parameter diffuser.  The shared common condition is still computed
  and uncomputed with the same reversible MCX network.

Both variants are ideal-statevector checked for equivalence before routing.  The
script then recompiles both on the strongest patches from a prior one-round Fez
sweep under the current authenticated calibration, across multiple transpiler
seeds.  Calibration products are engineering proxies, not measured fidelity.
No Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.circuit.library import MCPhaseGate
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import benchmark_tct_model_derived_threshold_predicate as model
import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import benchmark_tct_semantic_factored_oracle as semantic
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-21-tct-model-derived-phase-synthesis-v1"
DEFAULT_SOURCE = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_fez_one_round_fresh64_opt3.json"
)
DEFAULT_OUT = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_phase_synthesis.json"
)


def parse_int_list(text: str) -> list[int]:
    out = [int(x.strip()) for x in text.split(",") if x.strip()]
    if not out:
        raise ValueError("empty integer list")
    return out


def derive_predicate(spec: dict):
    n = int(spec["parameter_register_bits"]["total_parameter_bits"])
    rows = model.enumerate_model_rows(spec)
    feasibility = model.feasibility_by_parameter(spec, rows)
    marked_rows = model.derived_marked_rows(spec, rows)
    model_states = model.state_set_from_rows(spec, marked_rows)
    common = model.common_constraints_from_necessary_sets(spec, feasibility)
    observed_common = semantic.common_constraints(sorted(model_states), n)
    if common != observed_common:
        raise AssertionError("necessary-code and model-state common constraints disagree")
    local_bits = [bit for bit in range(n) if bit not in common]
    local_marked = {semantic.local_state(state, local_bits) for state in model_states}
    esop_local = semantic.minimum_esop(local_marked, len(local_bits))
    esop_full = [
        semantic.merge_local_cube(cube, local_bits, common, n)
        for cube in esop_local
    ]
    model.verify_formula_predicate_all_basis(spec, esop_full, model_states)
    return n, model_states, common, local_bits, esop_local


def phase_mcphase(qc: QuantumCircuit, active: list[int]) -> None:
    if not active:
        raise RuntimeError("empty phase condition")
    if len(active) == 1:
        qc.z(active[0])
        return
    qc.append(MCPhaseGate(math.pi, num_ctrl_qubits=len(active) - 1), active)


def apply_local_cube_mcphase(
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
    phase_mcphase(qc, active)
    for q in reversed(zeros):
        qc.x(q)


def diffuser_mcphase(qc: QuantumCircuit, params: list[int]) -> None:
    qc.h(params)
    qc.x(params)
    phase_mcphase(qc, params)
    qc.x(params)
    qc.h(params)


def build_mcphase_variant(
    n: int,
    rounds: int,
    common: dict[int, int],
    local_bits: list[int],
    esop_local: list[tuple[int, ...]],
) -> QuantumCircuit:
    qc = QuantumCircuit(n + 1)
    params = list(range(n))
    anc = n
    qc.h(params)
    for _ in range(rounds):
        semantic.compute_common(qc, params, anc, common)
        for cube in esop_local:
            apply_local_cube_mcphase(qc, params, anc, local_bits, cube)
        semantic.compute_common(qc, params, anc, common)
        diffuser_mcphase(qc, params)
    return qc


def selected_patch_rows(source: dict, top_exposure: int) -> list[dict]:
    rows = [r for r in source.get("rows", []) if r.get("patch_nodes")]
    if not rows:
        raise RuntimeError("source sweep has no patch rows")
    by_exp = sorted(
        rows,
        key=lambda r: (
            math.inf if r.get("cz_sum_p") is None else float(r["cz_sum_p"]),
            int(r["native_cz"]),
            int(r["compiled_depth"]),
        ),
    )
    chosen = by_exp[: max(1, int(top_exposure))]
    chosen += [
        min(rows, key=lambda r: (int(r["native_cz"]), int(r["compiled_depth"]))),
        min(rows, key=lambda r: float(r["critical_path_s"])),
    ]
    dedup = {int(r["patch_index"]): r for r in chosen}
    return [dedup[i] for i in sorted(dedup)]


def candidate_key(row: dict):
    return (
        math.inf if row.get("cz_sum_p") is None else float(row["cz_sum_p"]),
        int(row["native_cz"]),
        int(row["compiled_depth"]),
        int(row["seed_transpiler"]),
    )


def compile_variant_on_patch(qc, fez, fez_full, source_row: dict, seeds: list[int], level: int):
    logical = int(qc.num_qubits)
    nodes = [int(x) for x in source_row["patch_nodes"]]
    if len(nodes) != logical:
        raise RuntimeError(
            f"patch {source_row['patch_index']} width={len(nodes)} but circuit width={logical}"
        )
    subcm = cap.relabeled_subgraph(fez_full, nodes)
    backend = topo.generic(logical, subcm)
    candidates = []
    for seed in seeds:
        compiled, elapsed = mapper.compile_circuit(
            qc, backend, "auto", level, seed, None
        )
        stats = mapper.compiled_stats(qc, compiled, elapsed)
        if int(stats["compiled_touched_qubits"]) > logical:
            raise AssertionError("exact-width capacity lock violated")
        row = sweep.summarize_candidate(compiled, stats, fez, nodes, seed)
        row.update({
            "patch_index": int(source_row["patch_index"]),
            "patch_nodes": nodes,
        })
        candidates.append(row)
    return min(candidates, key=candidate_key)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--source-sweep", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--grover-rounds", type=int, default=1)
    ap.add_argument("--top-exposure-patches", type=int, default=8)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--transpiler-seeds", default="8776,2026,9401,42,1337,271828,118021")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.grover_rounds != 1:
        raise SystemExit("this challenger is intentionally preregistered for one Grover round")
    seeds = parse_int_list(args.transpiler_seeds)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    source = json.loads(args.source_sweep.read_text(encoding="utf-8"))

    n, model_states, common, local_bits, esop_local = derive_predicate(spec)
    current = semantic.build_variant(
        n, sorted(model_states), None, 1,
        factored=True,
        local_cubes=esop_local,
        local_bits=local_bits,
        common=common,
    )
    challenger = build_mcphase_variant(n, 1, common, local_bits, esop_local)
    if current.num_qubits != challenger.num_qubits:
        raise AssertionError("variant widths differ")

    sv_current = Statevector.from_instruction(current)
    sv_challenger = Statevector.from_instruction(challenger)
    ideal_equivalent = bool(sv_current.equiv(sv_challenger))
    if not ideal_equivalent:
        raise AssertionError("MCPhase challenger is not ideal-statevector equivalent to current circuit")

    logical = int(current.num_qubits)
    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, logical, args.backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))
    patch_rows = selected_patch_rows(source, args.top_exposure_patches)

    variants = {"mcx_h": current, "mcphase": challenger}
    result = {
        "experiment": "tct_model_derived_phase_synthesis_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "source_sweep": str(args.source_sweep),
        "backend": str(fez.name),
        "calibration_last_update": sweep.cal.calibration_timestamp(fez),
        "grover_rounds": 1,
        "logical_width": logical,
        "derived_marked_states": sorted(int(x) for x in model_states),
        "common_constraints": {str(k): int(v) for k, v in sorted(common.items())},
        "local_bits": [int(x) for x in local_bits],
        "local_esop": [semantic.audit.compact_cube(c) for c in esop_local],
        "ideal_statevector_equivalent": ideal_equivalent,
        "selected_patch_indices": [int(r["patch_index"]) for r in patch_rows],
        "transpiler_seeds": seeds,
        "optimization_level": int(args.optimization_level),
        "rows": [],
        "best": {},
        "claim_boundary": (
            "Zero-QPU compiler/calibration comparison of two exactly equivalent phase-synthesis "
            "expressions for the same finite-codebook model-derived predicate. Calibration products "
            "are engineering proxies, not measured fidelity. No fusion-validation or quantum-advantage claim."
        ),
    }

    print("ZERO-QPU TCT MODEL-DERIVED PHASE-SYNTHESIS CHALLENGER")
    print(
        f"backend={fez.name} calibration_last_update={result['calibration_last_update']} "
        f"width={logical} patches={result['selected_patch_indices']} seeds={seeds}"
    )
    print(f"ideal_statevector_equivalent={ideal_equivalent}")

    for name, qc in variants.items():
        vrows = []
        for source_row in patch_rows:
            best = compile_variant_on_patch(
                qc, fez, fez_full, source_row, seeds, args.optimization_level
            )
            best["variant"] = name
            result["rows"].append(best)
            vrows.append(best)
            print(
                f"variant={name:7s} patch={best['patch_index']:02d} seed={best['seed_transpiler']:6d} "
                f"CZ={best['native_cz']:4d} depth={best['compiled_depth']:5d} "
                f"sum_p={best['cz_sum_p']:.3f} log10_noerr={best['cz_log10_no_error_proxy']:.3f} "
                f"duration_us={1e6*best['critical_path_s']:.1f} "
                f"dur/T1={best['duration_over_median_t1']:.3f} "
                f"dur/T2={best['duration_over_median_t2']:.3f}"
            )
        result["best"][name] = min(vrows, key=candidate_key)

    a = result["best"]["mcx_h"]
    b = result["best"]["mcphase"]
    print("\n===== PHASE-SYNTHESIS SUMMARY =====")
    print(
        f"mcx_h:   patch={a['patch_index']} seed={a['seed_transpiler']} CZ={a['native_cz']} "
        f"depth={a['compiled_depth']} sum_p={a['cz_sum_p']:.3f} "
        f"duration_us={1e6*a['critical_path_s']:.1f}"
    )
    print(
        f"mcphase: patch={b['patch_index']} seed={b['seed_transpiler']} CZ={b['native_cz']} "
        f"depth={b['compiled_depth']} sum_p={b['cz_sum_p']:.3f} "
        f"duration_us={1e6*b['critical_path_s']:.1f}"
    )
    print(
        f"mcphase_CZ_ratio={b['native_cz']/a['native_cz']:.6f} "
        f"mcphase_sum_p_ratio={b['cz_sum_p']/a['cz_sum_p']:.6f} "
        f"mcphase_duration_ratio={b['critical_path_s']/a['critical_path_s']:.6f}"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
