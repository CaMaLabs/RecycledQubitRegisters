#!/usr/bin/env python3
"""Guarded IBM Fez pilot v2 for the 11q clean-ancilla one-round TCT predicate.

This revision exists because the first clean11 preflight correctly refused QPU
submission: the HLS sweep selected a 252-CZ route on an exact-width relabeled
11-qubit patch backend, while the first pilot runner re-transpiled the circuit
against the full Fez backend with ``initial_layout=patch_nodes``.  That is a
different routing problem and produced 367 CZ / sum_p 1.011.

V2 does NOT loosen the preregistered hardware guardrails.  Instead it replays the
exact compilation method that selected the source candidate:

1. rebuild the model-derived one-round width-11 clean-helper circuit;
2. reconstruct the selected Fez patch as the same exact-width relabeled generic
   backend used by the HLS sweep;
3. compile with the frozen HLS method / transpiler seed and require exact source
   CZ/depth/size reproduction;
4. recover the final local wires carrying the nine parameter bits;
5. lift the already-native local circuit onto the corresponding real Fez physical
   qubits without re-routing or re-synthesizing it;
6. verify every lifted native instruction is supported by the authenticated Fez
   Target on that physical qarg tuple;
7. append measurements after routing, statevector-check the lifted native circuit,
   and audit the live Fez calibration / coherence guardrails;
8. submit only when ``--run`` is explicitly supplied and every guardrail passes.

The paired baseline uses native SX gates on the *same physical output qubits* as
the candidate.  SX|0> has exactly uniform computational-basis probabilities, so
this gives the same 8/512 ideal marked fraction while matching candidate readout
qubits and avoiding a second routing problem.

Calibration products remain engineering proxies, not predicted fidelity.  This
is a finite-codebook Grover amplification pilot, not fusion validation and not an
end-to-end quantum-advantage claim.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime import SamplerV2

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_model_derived_qpu_pilot_postmortem as post
import benchmark_tct_model_derived_clean_ancilla_hls as hls
import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import run_tct_model_derived_one_round_qpu_pilot as pilot

REV = "2026-09-22-tct-model-derived-clean11-qpu-pilot-v2-route-replay"
DEFAULT_HLS = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_clean_ancilla_hls.json"
)
DEFAULT_OUTDIR = (
    ROOT / "results" / "tct_surrogate_search" / "qpu_pilot_clean11_v2"
)


def semantic_audit(compiled, parameter_bits: int, marked: set[int], expected: float) -> dict:
    compact, meta, c2l = post.compact_native_circuit(compiled, parameter_bits)
    sv = Statevector.from_instruction(compact)
    dist = post.parameter_distribution_from_statevector(sv, c2l, parameter_bits)
    marked_p = post.marked_probability(dist, marked)
    ancilla_probs = [
        post.qubit_one_probability(sv, q)
        for q in meta["unmeasured_local_qubits"]
    ]
    return {
        "marked_probability": float(marked_p),
        "expected_marked_probability": float(expected),
        "marked_probability_abs_error": abs(float(marked_p) - float(expected)),
        "max_unmeasured_qubit_p1": max(ancilla_probs) if ancilla_probs else 0.0,
        "measurement_map_complete": set(c2l) == set(range(parameter_bits)),
        "mapping": meta,
    }


def final_local_parameter_qubits(compiled, parameter_bits: int) -> list[int]:
    layout = getattr(compiled, "layout", None)
    if layout is None:
        raise RuntimeError("local compiled circuit has no layout metadata")
    final_local = list(layout.final_index_layout(filter_ancillas=True))
    if len(final_local) < parameter_bits:
        raise RuntimeError(
            f"final local layout has {len(final_local)} entries, need {parameter_bits}"
        )
    out = [int(final_local[i]) for i in range(parameter_bits)]
    if len(set(out)) != parameter_bits:
        raise RuntimeError(f"non-unique final parameter wires: {out}")
    return out


def target_supports(backend, name: str, qargs: tuple[int, ...]) -> bool:
    if name == "barrier":
        return True
    try:
        return bool(
            backend.target.instruction_supported(
                operation_name=str(name), qargs=tuple(int(q) for q in qargs)
            )
        )
    except Exception:
        try:
            _prop, _used, found = pilot.cal.target_instruction_properties(
                backend, str(name), tuple(int(q) for q in qargs)
            )
            return bool(found) or str(name) == "rz"
        except Exception:
            return False


def lift_local_native_to_fez(
    local_compiled,
    backend,
    patch_nodes: list[int],
    final_param_local: list[int],
    parameter_bits: int,
) -> tuple[QuantumCircuit, dict]:
    """Lift a routed exact-width local native circuit to real Fez qubit indices."""
    if int(local_compiled.num_qubits) != len(patch_nodes):
        raise RuntimeError(
            f"local width {local_compiled.num_qubits} != patch width {len(patch_nodes)}"
        )

    out = QuantumCircuit(int(backend.num_qubits))
    creg = ClassicalRegister(parameter_bits, "params")
    out.add_register(creg)
    out.global_phase = local_compiled.global_phase
    unsupported = []
    lifted_operation_count = 0

    for item in local_compiled.data:
        name = str(item.operation.name)
        if name in {"measure", "barrier", "delay"}:
            # The source HLS screen compiles an unmeasured, unscheduled circuit;
            # these are therefore not expected to carry unitary semantics here.
            continue
        if item.clbits:
            raise RuntimeError(f"unexpected classical operands in local native op {name}")
        local_q = [int(local_compiled.find_bit(q).index) for q in item.qubits]
        physical_q = [int(patch_nodes[i]) for i in local_q]
        qargs = tuple(physical_q)
        if not target_supports(backend, name, qargs):
            unsupported.append({"name": name, "physical_qubits": physical_q})
        out.append(item.operation, [out.qubits[q] for q in physical_q])
        lifted_operation_count += 1

    output_physical = [int(patch_nodes[q]) for q in final_param_local]
    for cbit, pq in enumerate(output_physical):
        if not target_supports(backend, "measure", (pq,)):
            unsupported.append({"name": "measure", "physical_qubits": [pq]})
        out.measure(pq, creg[cbit])

    return out, {
        "output_parameter_local_qubits": final_param_local,
        "output_parameter_physical_qubits": output_physical,
        "unsupported_native_operations": unsupported,
        "all_native_operations_supported": not unsupported,
        "lifted_unitary_operation_count": lifted_operation_count,
    }


def build_matched_uniform_baseline(backend, output_physical: list[int]) -> QuantumCircuit:
    """Uniform baseline on exactly the candidate's physical readout qubits."""
    qc = QuantumCircuit(int(backend.num_qubits))
    creg = ClassicalRegister(len(output_physical), "params")
    qc.add_register(creg)
    for i, pq in enumerate(output_physical):
        # SX|0> has |0|^2=|1|^2=1/2, hence the product distribution is uniform.
        if not target_supports(backend, "sx", (int(pq),)):
            raise RuntimeError(f"Fez Target does not support sx on physical qubit {pq}")
        qc.sx(int(pq))
        qc.measure(int(pq), creg[i])
    return qc


def simple_stats(circuit) -> dict:
    ops = circuit.count_ops()
    return {
        "native_cz": int(ops.get("cz", 0)),
        "compiled_depth": int(circuit.depth()),
        "compiled_size": int(circuit.size()),
        "compiled_touched_qubits": len(pilot.physical_touched_qubits(circuit)),
    }


def source_stats_match(selected: dict, local_stats: dict) -> tuple[bool, dict]:
    keys = ("native_cz", "compiled_depth", "compiled_size")
    detail = {
        key: {
            "source": int(selected.get(key, -1)),
            "replayed": int(local_stats.get(key, -2)),
            "match": int(selected.get(key, -1)) == int(local_stats.get(key, -2)),
        }
        for key in keys
    }
    return all(row["match"] for row in detail.values()), detail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--hls-result", type=Path, default=DEFAULT_HLS)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--max-execution-time", type=int, default=120)
    ap.add_argument("--max-cz", type=int, default=325)
    ap.add_argument("--max-cz-sum-p", type=float, default=0.8)
    ap.add_argument("--max-duration-us", type=float, default=30.0)
    ap.add_argument("--max-duration-over-t1", type=float, default=0.3)
    ap.add_argument("--max-duration-over-t2", type=float, default=0.3)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    if args.shots < 1:
        raise SystemExit("--shots must be positive")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    src = json.loads(args.hls_result.read_text(encoding="utf-8"))
    if src.get("experiment") != "tct_model_derived_clean_ancilla_hls_v1":
        raise RuntimeError("unexpected HLS result artifact")
    if not src.get("ideal_width11_equivalent"):
        raise RuntimeError("source HLS artifact did not pass width-11 ideal equivalence")

    selected = src.get("global_minimum_exposure")
    if not selected:
        raise RuntimeError("HLS result has no global_minimum_exposure")
    if int(selected.get("logical_width", -1)) != 11:
        raise RuntimeError("global minimum-exposure candidate is not width 11")
    if selected.get("variant") not in {"default_one_clean_11q", "one_clean_kg24_11q"}:
        raise RuntimeError(f"unexpected selected variant {selected.get('variant')!r}")

    patch_nodes = [int(x) for x in selected["patch_nodes"]]
    patch_index = int(selected["patch_index"])
    seed = int(selected["seed_transpiler"])
    method = selected.get("hls_method")
    clean = int(selected.get("requested_clean_ancillas", 1))

    base10, oracle = sweep.build_model_derived_circuit(spec, 1)
    candidate_unmeasured = hls.extend_with_clean_helper(base10)
    if candidate_unmeasured.num_qubits != 11:
        raise AssertionError("clean-helper candidate is not width 11")
    parameter_bits = int(oracle["parameter_bits"])
    marked = {int(x) for x in oracle["derived_marked_states"]}

    ideal_uniform = len(marked) / (1 << parameter_bits)
    logical_sv = Statevector.from_instruction(candidate_unmeasured)
    logical_dist = post.logical_parameter_distribution(logical_sv, parameter_bits)
    ideal_grover = post.marked_probability(logical_dist, marked)
    logical_unmeasured = [
        post.qubit_one_probability(logical_sv, q)
        for q in range(parameter_bits, candidate_unmeasured.num_qubits)
    ]
    logical_max_unmeasured_p1 = max(logical_unmeasured) if logical_unmeasured else 0.0

    service = width.ref.ibm_base.make_service()
    usage_before = width.ref.ibm_base.safe_usage(service)
    backend = width.ref.ibm_base.select_backend(service, 11, args.backend)

    # Recreate exactly the source sweep's routing problem: exact-width relabeled patch.
    fez_full = topo.symmetric(topo.backend_coupling(backend), int(backend.num_qubits))
    subcm = cap.relabeled_subgraph(fez_full, patch_nodes)
    patch_backend = topo.generic(11, subcm)
    hls_cfg = hls.make_hls(method, clean)
    local_compiled, local_stats_raw = hls.compile_with_hls(
        candidate_unmeasured,
        patch_backend,
        args.optimization_level,
        seed,
        None,
        hls_cfg,
    )
    local_stats = {
        "native_cz": int(local_stats_raw["native_cz"]),
        "compiled_depth": int(local_stats_raw["compiled_depth"]),
        "compiled_size": int(local_stats_raw["compiled_size"]),
        "compiled_touched_qubits": int(local_stats_raw["compiled_touched_qubits"]),
    }
    exact_source_reproduction, source_match_detail = source_stats_match(selected, local_stats)

    final_param_local = final_local_parameter_qubits(local_compiled, parameter_bits)
    compiled_candidate, lift_meta = lift_local_native_to_fez(
        local_compiled, backend, patch_nodes, final_param_local, parameter_bits
    )
    compiled_baseline = build_matched_uniform_baseline(
        backend, lift_meta["output_parameter_physical_qubits"]
    )

    baseline_stats = simple_stats(compiled_baseline)
    candidate_stats = simple_stats(compiled_candidate)
    touched_baseline = pilot.physical_touched_qubits(compiled_baseline)
    touched_candidate = pilot.physical_touched_qubits(compiled_candidate)
    patch_set = set(patch_nodes)

    audit = pilot.calibration_audit(compiled_candidate, backend, patch_nodes)
    base_sem = semantic_audit(compiled_baseline, parameter_bits, marked, ideal_uniform)
    cand_sem = semantic_audit(compiled_candidate, parameter_bits, marked, ideal_grover)

    guardrails = {
        "width11_clean_helper": candidate_unmeasured.num_qubits == 11 and clean >= 1,
        "source_patch_route_exactly_reproduced": bool(exact_source_reproduction),
        "lifted_native_operations_supported_by_fez": bool(lift_meta["all_native_operations_supported"]),
        "candidate_stays_on_frozen_patch": set(touched_candidate).issubset(patch_set),
        "baseline_stays_on_frozen_patch": set(touched_baseline).issubset(patch_set),
        "candidate_output_qubits_match_baseline": (
            set(touched_baseline) == set(lift_meta["output_parameter_physical_qubits"])
        ),
        "cz_at_most_limit": candidate_stats["native_cz"] <= args.max_cz,
        "cz_sum_p_at_most_limit": (
            audit["cz_sum_p"] is not None and float(audit["cz_sum_p"]) <= args.max_cz_sum_p
        ),
        "duration_us_at_most_limit": float(audit["duration_us"]) <= args.max_duration_us,
        "duration_over_t1_at_most_limit": (
            audit["duration_over_median_t1"] is not None
            and float(audit["duration_over_median_t1"]) <= args.max_duration_over_t1
        ),
        "duration_over_t2_at_most_limit": (
            audit["duration_over_median_t2"] is not None
            and float(audit["duration_over_median_t2"]) <= args.max_duration_over_t2
        ),
        "duration_calibration_complete": (
            float(audit.get("duration_coverage") or 0.0) >= 0.999999
            and not audit.get("missing_duration_counts")
        ),
        "logical_clean_ancillas_return_zero": logical_max_unmeasured_p1 <= 1e-10,
        "transpiled_baseline_probability_matches_uniform": base_sem["marked_probability_abs_error"] <= 1e-10,
        "transpiled_candidate_probability_matches_expected": cand_sem["marked_probability_abs_error"] <= 1e-9,
        "transpiled_clean_ancillas_return_zero": cand_sem["max_unmeasured_qubit_p1"] <= 1e-9,
        "baseline_measurement_map_complete": bool(base_sem["measurement_map_complete"]),
        "candidate_measurement_map_complete": bool(cand_sem["measurement_map_complete"]),
    }
    all_guardrails_pass = all(bool(v) for v in guardrails.values())

    out = {
        "experiment": "tct_model_derived_clean11_qpu_pilot_v2_route_replay",
        "script_revision": REV,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_spec": str(args.spec),
        "source_hls_result": str(args.hls_result),
        "backend": str(backend.name),
        "calibration_last_update": pilot.cal.calibration_timestamp(backend),
        "variant": selected["variant"],
        "hls_method": method,
        "requested_clean_ancillas": clean,
        "patch_index": patch_index,
        "patch_nodes": patch_nodes,
        "seed_transpiler": seed,
        "shots_per_circuit": int(args.shots),
        "parameter_bits": parameter_bits,
        "derived_marked_states": sorted(marked),
        "ideal_uniform_marked_fraction": ideal_uniform,
        "ideal_grover_marked_fraction": ideal_grover,
        "logical_max_unmeasured_qubit_p1": logical_max_unmeasured_p1,
        "source_selected_stats": {
            "native_cz": int(selected["native_cz"]),
            "compiled_depth": int(selected["compiled_depth"]),
            "compiled_size": int(selected["compiled_size"]),
            "cz_sum_p": selected.get("cz_sum_p"),
            "critical_path_s": selected.get("critical_path_s"),
        },
        "replayed_local_stats": local_stats,
        "source_route_match_detail": source_match_detail,
        "source_patch_route_exactly_reproduced": exact_source_reproduction,
        "lift_metadata": lift_meta,
        "baseline_stats": baseline_stats,
        "candidate_stats": candidate_stats,
        "baseline_touched_physical_qubits": touched_baseline,
        "candidate_touched_physical_qubits": touched_candidate,
        "candidate_calibration_audit": audit,
        "baseline_semantic_audit": base_sem,
        "candidate_semantic_audit": cand_sem,
        "guardrail_limits": {
            "max_cz": args.max_cz,
            "max_cz_sum_p": args.max_cz_sum_p,
            "max_duration_us": args.max_duration_us,
            "max_duration_over_t1": args.max_duration_over_t1,
            "max_duration_over_t2": args.max_duration_over_t2,
        },
        "guardrails": guardrails,
        "all_guardrails_pass": all_guardrails_pass,
        "account_usage_before": usage_before,
        "qpu_job_submitted": False,
        "preregistered_interpretation": {
            "strong_amplification_evidence": "candidate marked fraction > baseline and two-proportion z >= 3",
            "same_job_pairing": True,
            "same_physical_output_qubits": True,
            "no_posthoc_threshold_change": True,
        },
        "claim_boundary": (
            "Route-replay second hardware pilot of the finite-codebook model-derived TCT threshold predicate. "
            "The selected local native route is lifted without re-routing and is checked against the live Fez Target. "
            "This tests marked-state amplification only; it is not fusion validation or end-to-end quantum advantage."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    preflight_path = args.outdir / "tct_model_derived_clean11_qpu_pilot_v2_preflight.json"
    preflight_path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print("TCT MODEL-DERIVED CLEAN11 QPU PILOT V2 ROUTE-REPLAY PREFLIGHT")
    print(
        f"backend={backend.name} calibration_last_update={out['calibration_last_update']} "
        f"variant={selected['variant']} patch={patch_index} seed={seed} shots={args.shots}"
    )
    print(
        f"source_route: CZ={selected['native_cz']} depth={selected['compiled_depth']} size={selected['compiled_size']} | "
        f"replayed_local: CZ={local_stats['native_cz']} depth={local_stats['compiled_depth']} "
        f"size={local_stats['compiled_size']} exact={exact_source_reproduction}"
    )
    print(
        f"output_physical={lift_meta['output_parameter_physical_qubits']} "
        f"native_supported={lift_meta['all_native_operations_supported']}"
    )
    print(
        f"baseline: CZ={baseline_stats['native_cz']} depth={baseline_stats['compiled_depth']} "
        f"touched={touched_baseline} ideal_marked={base_sem['marked_probability']:.9f}"
    )
    print(
        f"candidate: CZ={candidate_stats['native_cz']} depth={candidate_stats['compiled_depth']} "
        f"sum_p_CZ={audit['cz_sum_p']:.3f} log10_noerr={audit['cz_log10_no_error_proxy']:.3f} "
        f"duration_us={audit['duration_us']:.1f} "
        f"dur/T1={audit['duration_over_median_t1']:.3f} "
        f"dur/T2={audit['duration_over_median_t2']:.3f} "
        f"ideal_marked={cand_sem['marked_probability']:.9f} "
        f"max_unmeasured_p1={cand_sem['max_unmeasured_qubit_p1']:.3e}"
    )
    print("guardrails=" + json.dumps(guardrails, sort_keys=True))
    print(f"all_guardrails_pass={all_guardrails_pass}")
    print(f"saved preflight {preflight_path.resolve()}")

    if not args.run:
        print("NO QPU JOB SUBMITTED. Add --run only after reviewing this preflight.")
        return 0
    if not all_guardrails_pass:
        raise SystemExit("REFUSING QPU SUBMISSION: one or more preregistered guardrails failed")

    print(f"Submitting matched-output baseline + lifted clean11 candidate: 2 circuits x {args.shots} shots")
    sampler = SamplerV2(mode=backend, options={"max_execution_time": args.max_execution_time})
    job = sampler.run([compiled_baseline, compiled_candidate], shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    baseline_counts = pubs[0].data.params.get_counts()
    candidate_counts = pubs[1].data.params.get_counts()
    b = pilot.parse_counts(baseline_counts, marked, args.shots)
    c = pilot.parse_counts(candidate_counts, marked, args.shots)
    z = pilot.two_proportion_z(b["marked_hits"], args.shots, c["marked_hits"], args.shots)

    out.update({
        "qpu_job_submitted": True,
        "job_id": job.job_id(),
        "job_metrics": width.ref.ibm_base.safe_metrics(job),
        "account_usage_after": width.ref.ibm_base.safe_usage(service),
        "hardware_results": {
            "uniform_matched_output_baseline": b,
            "one_round_clean11_route_replay": c,
            "marked_fraction_difference": c["marked_fraction"] - b["marked_fraction"],
            "marked_fraction_ratio": None if b["marked_fraction"] == 0 else c["marked_fraction"] / b["marked_fraction"],
            "two_proportion_z_approx": z,
        },
    })
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = args.outdir / f"tct_model_derived_clean11_qpu_pilot_v2_{stamp}.json"
    result_path.write_text(json.dumps(out, indent=2, default=str) + "\n", encoding="utf-8")

    print("RESULT")
    print(
        f"baseline marked={b['marked_hits']}/{args.shots}={b['marked_fraction']:.6f} | "
        f"candidate marked={c['marked_hits']}/{args.shots}={c['marked_fraction']:.6f} | "
        f"difference={c['marked_fraction'] - b['marked_fraction']:.6f} | z~{z}"
    )
    print(f"saved {result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
