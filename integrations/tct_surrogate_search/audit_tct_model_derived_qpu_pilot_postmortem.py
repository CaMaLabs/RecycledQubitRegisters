#!/usr/bin/env python3
"""Zero-QPU semantic postmortem for the one-round model-derived TCT QPU pilot.

The first paired hardware pilot showed no statistically meaningful marked-state
amplification.  Before attributing that negative result to hardware noise, this
audit checks the compiler / layout / measurement semantics of the submitted
candidate path.

It:

1. reloads the frozen pilot result and feasibility selection;
2. reconstructs the one-round model-derived TCT circuit;
3. recompiles the same physical Fez patch with the same transpiler seed;
4. compares compile statistics with the recorded hardware-run compile;
5. reconstructs a compact ideal circuit from the native transpiled operations;
6. recovers the transpiled physical-qubit -> classical-bit measurement map;
7. statevector-checks the marked-state probability and clean-ancilla return;
8. summarizes the hardware baseline/candidate confidence intervals.

No Sampler is instantiated and no QPU job is submitted.  A passing postmortem
establishes semantic/compiler consistency for a reproduced transpilation; it
does not prove a complete physical noise diagnosis and does not turn calibration
metadata into a fidelity model.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import run_tct_model_derived_one_round_qpu_pilot as pilot
import ibm_qubit_recycling_width_sweep as width

REV = "2026-09-21-tct-model-derived-qpu-pilot-postmortem-v1"
DEFAULT_FEASIBILITY = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_round_feasibility.json"
)
DEFAULT_RESULT_DIR = ROOT / "results" / "tct_surrogate_search" / "qpu_pilot"
DEFAULT_OUT = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_qpu_pilot_postmortem.json"
)


def latest_hardware_result(directory: Path) -> Path:
    paths = sorted(
        p for p in directory.glob("tct_model_derived_one_round_qpu_pilot_*.json")
        if "preflight" not in p.name
    )
    if not paths:
        raise RuntimeError(f"no hardware pilot result found in {directory}")
    return paths[-1]


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (math.nan, math.nan)
    p = k / n
    zz = z * z
    den = 1.0 + zz / n
    center = (p + zz / (2.0 * n)) / den
    half = z * math.sqrt(p * (1.0 - p) / n + zz / (4.0 * n * n)) / den
    return center - half, center + half


def parameter_distribution_from_statevector(
    sv: Statevector,
    classical_to_local_qubit: dict[int, int],
    parameter_bits: int,
) -> list[float]:
    expected = set(range(parameter_bits))
    if set(classical_to_local_qubit) != expected:
        raise RuntimeError(
            f"measurement map classical bits={sorted(classical_to_local_qubit)} expected={sorted(expected)}"
        )
    out = [0.0] * (1 << parameter_bits)
    for basis, amp in enumerate(sv.data):
        p = float(abs(complex(amp)) ** 2)
        if p <= 0.0:
            continue
        state = 0
        for cbit in range(parameter_bits):
            q = int(classical_to_local_qubit[cbit])
            state |= ((basis >> q) & 1) << cbit
        out[state] += p
    return out


def logical_parameter_distribution(sv: Statevector, parameter_bits: int) -> list[float]:
    return parameter_distribution_from_statevector(
        sv, {i: i for i in range(parameter_bits)}, parameter_bits
    )


def marked_probability(dist: list[float], marked: set[int]) -> float:
    return sum(float(dist[s]) for s in marked)


def qubit_one_probability(sv: Statevector, q: int) -> float:
    return sum(
        float(abs(complex(amp)) ** 2)
        for basis, amp in enumerate(sv.data)
        if (basis >> int(q)) & 1
    )


def compact_native_circuit(compiled, parameter_bits: int):
    """Compact physical native operations onto only their touched qubits.

    Measurements are removed for ideal statevector evolution, but their mapping
    from physical qubits to classical parameter bits is preserved separately.
    Delay and barrier instructions are ideal identities and are omitted.
    """
    touched = set()
    measurement_physical: dict[int, int] = {}

    for item in compiled.data:
        name = str(item.operation.name)
        physical = [int(compiled.find_bit(q).index) for q in item.qubits]
        touched.update(physical)
        if name == "measure":
            if len(physical) != 1 or len(item.clbits) != 1:
                raise RuntimeError("unexpected multi-qubit/multi-classical measurement")
            cidx = int(compiled.find_bit(item.clbits[0]).index)
            if cidx in measurement_physical and measurement_physical[cidx] != physical[0]:
                raise RuntimeError(f"classical bit {cidx} measured from multiple physical qubits")
            measurement_physical[cidx] = physical[0]

    active = sorted(touched)
    p2l = {p: i for i, p in enumerate(active)}
    compact = QuantumCircuit(len(active))
    compact.global_phase = compiled.global_phase

    for item in compiled.data:
        name = str(item.operation.name)
        if name in {"measure", "barrier", "delay"}:
            continue
        if item.clbits:
            raise RuntimeError(f"cannot idealize classically-conditioned operation {name}")
        physical = [int(compiled.find_bit(q).index) for q in item.qubits]
        compact.append(item.operation, [p2l[p] for p in physical])

    classical_to_local = {
        int(c): int(p2l[p]) for c, p in measurement_physical.items()
        if int(c) < parameter_bits
    }
    measured_physical = set(measurement_physical.values())
    unmeasured_physical = [p for p in active if p not in measured_physical]
    unmeasured_local = [p2l[p] for p in unmeasured_physical]

    return compact, {
        "active_physical_qubits": active,
        "classical_to_physical_measurement": {
            str(c): int(p) for c, p in sorted(measurement_physical.items())
        },
        "classical_to_local_measurement": {
            str(c): int(q) for c, q in sorted(classical_to_local.items())
        },
        "unmeasured_physical_qubits": unmeasured_physical,
        "unmeasured_local_qubits": unmeasured_local,
    }, classical_to_local


def stats_exact_match(recorded: dict, reproduced: dict) -> bool:
    keys = ("native_cz", "compiled_depth", "compiled_size")
    return all(int(recorded.get(k, -1)) == int(reproduced.get(k, -2)) for k in keys)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--feasibility", type=Path, default=DEFAULT_FEASIBILITY)
    ap.add_argument("--result", type=Path, default=None)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=1)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    result_path = args.result or latest_hardware_result(DEFAULT_RESULT_DIR)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    feas = json.loads(args.feasibility.read_text(encoding="utf-8"))
    hw = json.loads(result_path.read_text(encoding="utf-8"))

    if hw.get("experiment") != "tct_model_derived_one_round_qpu_pilot_v1":
        raise RuntimeError("unexpected hardware result artifact")
    if not hw.get("qpu_job_submitted"):
        raise RuntimeError("selected artifact is not a submitted hardware result")
    if int(hw.get("rounds", -1)) != 1:
        raise RuntimeError("postmortem is restricted to the one-round pilot")

    patch_nodes = [int(x) for x in hw["patch_nodes"]]
    seed = int(hw["seed_transpiler"])
    parameter_bits = int(hw["parameter_bits"])
    marked = {int(x) for x in hw["derived_marked_states"]}

    candidate_unmeasured, oracle = sweep.build_model_derived_circuit(spec, 1)
    candidate = pilot.add_param_measurements(candidate_unmeasured, parameter_bits)
    baseline = pilot.build_uniform_baseline(candidate_unmeasured.num_qubits, parameter_bits)

    # Logical model-derived circuit before hardware transpilation.
    logical_sv = Statevector.from_instruction(candidate_unmeasured)
    logical_dist = logical_parameter_distribution(logical_sv, parameter_bits)
    logical_marked = marked_probability(logical_dist, marked)
    logical_ancilla_p1 = qubit_one_probability(logical_sv, candidate_unmeasured.num_qubits - 1)

    service = width.ref.ibm_base.make_service()
    backend = width.ref.ibm_base.select_backend(service, candidate.num_qubits, args.backend)
    compiled_baseline = pilot.compile_physical(
        baseline, backend, patch_nodes, seed, args.optimization_level
    )
    compiled_candidate = pilot.compile_physical(
        candidate, backend, patch_nodes, seed, args.optimization_level
    )
    baseline_stats = pilot.compile_stats(baseline, compiled_baseline)
    candidate_stats = pilot.compile_stats(candidate, compiled_candidate)

    compact_base, base_map_meta, base_c2l = compact_native_circuit(
        compiled_baseline, parameter_bits
    )
    compact_cand, cand_map_meta, cand_c2l = compact_native_circuit(
        compiled_candidate, parameter_bits
    )
    base_sv = Statevector.from_instruction(compact_base)
    cand_sv = Statevector.from_instruction(compact_cand)
    base_dist = parameter_distribution_from_statevector(base_sv, base_c2l, parameter_bits)
    cand_dist = parameter_distribution_from_statevector(cand_sv, cand_c2l, parameter_bits)
    base_marked = marked_probability(base_dist, marked)
    cand_marked = marked_probability(cand_dist, marked)

    cand_ancilla_probs = [
        qubit_one_probability(cand_sv, q)
        for q in cand_map_meta["unmeasured_local_qubits"]
    ]
    max_cand_ancilla_p1 = max(cand_ancilla_probs) if cand_ancilla_probs else 0.0

    ideal_uniform = len(marked) / (1 << parameter_bits)
    selected = feas["ranking_heuristic_best_round"]["maximum_ranking_heuristic"]
    expected_one_round = float(selected["ideal_grover_success"])

    recorded_stats = hw.get("candidate_stats", {})
    compile_reproduction = stats_exact_match(recorded_stats, candidate_stats)
    checks = {
        "logical_model_probability_matches_expected": abs(logical_marked - expected_one_round) <= 1e-10,
        "logical_clean_ancilla_returns_zero": logical_ancilla_p1 <= 1e-10,
        "transpiled_baseline_probability_matches_uniform": abs(base_marked - ideal_uniform) <= 1e-10,
        "transpiled_candidate_probability_matches_expected": abs(cand_marked - expected_one_round) <= 1e-9,
        "transpiled_unmeasured_ancilla_returns_zero": max_cand_ancilla_p1 <= 1e-9,
        "candidate_compile_stats_exactly_reproduced": compile_reproduction,
        "candidate_measurement_map_complete": set(cand_c2l) == set(range(parameter_bits)),
        "baseline_measurement_map_complete": set(base_c2l) == set(range(parameter_bits)),
    }
    semantic_checks_pass = all(bool(v) for k, v in checks.items() if k != "candidate_compile_stats_exactly_reproduced")

    hwres = hw["hardware_results"]
    b = hwres["uniform_baseline"]
    c = hwres["one_round_grover"]
    bn = int(b["shots"]); cn = int(c["shots"])
    bh = int(b["marked_hits"]); ch = int(c["marked_hits"])
    blo, bhi = wilson_interval(bh, bn)
    clo, chi = wilson_interval(ch, cn)
    observed_ratio = None if bh == 0 else (ch / cn) / (bh / bn)
    ideal_ratio = expected_one_round / ideal_uniform
    ideal_excess = expected_one_round - ideal_uniform
    observed_excess = (ch / cn) - (bh / bn)

    result = {
        "experiment": "tct_model_derived_qpu_pilot_postmortem_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "source_feasibility": str(args.feasibility),
        "source_hardware_result": str(result_path),
        "hardware_job_id": hw.get("job_id"),
        "backend": str(backend.name),
        "current_calibration_last_update": pilot.cal.calibration_timestamp(backend),
        "frozen_patch_nodes": patch_nodes,
        "seed_transpiler": seed,
        "recorded_candidate_stats": recorded_stats,
        "reproduced_candidate_stats": candidate_stats,
        "reproduced_baseline_stats": baseline_stats,
        "compile_stats_exactly_reproduced": compile_reproduction,
        "ideal_checks": {
            "uniform_marked_probability": ideal_uniform,
            "expected_one_round_marked_probability": expected_one_round,
            "logical_model_marked_probability": logical_marked,
            "logical_clean_ancilla_p1": logical_ancilla_p1,
            "transpiled_baseline_marked_probability": base_marked,
            "transpiled_candidate_marked_probability": cand_marked,
            "transpiled_max_unmeasured_qubit_p1": max_cand_ancilla_p1,
            "checks": checks,
            "semantic_checks_pass": semantic_checks_pass,
        },
        "baseline_compact_mapping": base_map_meta,
        "candidate_compact_mapping": cand_map_meta,
        "hardware_summary": {
            "baseline_hits": bh,
            "baseline_shots": bn,
            "baseline_fraction": bh / bn,
            "baseline_wilson95": [blo, bhi],
            "candidate_hits": ch,
            "candidate_shots": cn,
            "candidate_fraction": ch / cn,
            "candidate_wilson95": [clo, chi],
            "difference": (ch / cn) - (bh / bn),
            "observed_candidate_over_baseline": observed_ratio,
            "ideal_candidate_over_baseline": ideal_ratio,
            "observed_excess_fraction_of_ideal_excess": None if ideal_excess == 0 else observed_excess / ideal_excess,
            "two_proportion_z_approx": hwres.get("two_proportion_z_approx"),
        },
        "interpretation_boundary": (
            "If semantic checks pass and compile stats reproduce, the reproduced native circuit preserves the intended "
            "one-round marked-state amplification under ideal evolution. That supports, but does not by itself prove, "
            "a hardware/noise explanation for the negative pilot. If compile stats do not reproduce, the current "
            "recompile is not identical to the submitted circuit and only the logical semantic check is conclusive."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("ZERO-QPU TCT ONE-ROUND QPU PILOT POSTMORTEM")
    print(f"hardware_job_id={hw.get('job_id')} result={result_path}")
    print(
        f"recorded_candidate: CZ={recorded_stats.get('native_cz')} depth={recorded_stats.get('compiled_depth')} "
        f"size={recorded_stats.get('compiled_size')}"
    )
    print(
        f"reproduced_candidate: CZ={candidate_stats['native_cz']} depth={candidate_stats['compiled_depth']} "
        f"size={candidate_stats['compiled_size']} exact_stats={compile_reproduction}"
    )
    print("\n===== IDEAL SEMANTIC CHECK =====")
    print(
        f"uniform_expected={ideal_uniform:.9f} transpiled_baseline={base_marked:.9f}"
    )
    print(
        f"one_round_expected={expected_one_round:.9f} logical_model={logical_marked:.9f} "
        f"transpiled_candidate={cand_marked:.9f}"
    )
    print(
        f"logical_ancilla_p1={logical_ancilla_p1:.3e} "
        f"transpiled_max_unmeasured_p1={max_cand_ancilla_p1:.3e}"
    )
    print("checks=" + json.dumps(checks, sort_keys=True))
    print(f"semantic_checks_pass={semantic_checks_pass}")

    print("\n===== HARDWARE RESULT CONTEXT =====")
    print(
        f"baseline={bh}/{bn}={bh/bn:.6f} Wilson95=[{blo:.6f},{bhi:.6f}]"
    )
    print(
        f"candidate={ch}/{cn}={ch/cn:.6f} Wilson95=[{clo:.6f},{chi:.6f}]"
    )
    print(
        f"observed_ratio={observed_ratio:.6f} ideal_ratio={ideal_ratio:.6f} "
        f"z={hwres.get('two_proportion_z_approx')}"
    )
    if semantic_checks_pass and compile_reproduction:
        print("POSTMORTEM_CLASSIFICATION=IDEAL_TRANSPILED_SEMANTICS_PASS_HARDWARE_AMPLIFICATION_NOT_OBSERVED")
    elif semantic_checks_pass:
        print("POSTMORTEM_CLASSIFICATION=LOGICAL_SEMANTICS_PASS_RECOMPILE_NOT_EXACT")
    else:
        print("POSTMORTEM_CLASSIFICATION=SEMANTIC_OR_MAPPING_DISCREPANCY_FOUND")
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
