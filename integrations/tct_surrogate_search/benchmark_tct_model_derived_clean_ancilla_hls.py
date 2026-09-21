#!/usr/bin/env python3
"""Zero-QPU HLS clean-ancilla challenger for the one-round model-derived TCT predicate.

This compares the current 10-qubit one-round model-derived TCT circuit with
Qiskit MCX high-level-synthesis alternatives, including an 11-qubit version
that adds one extra clean helper qubit.  The extra qubit is intended to let the
transpiler use one-clean-ancilla MCX synthesis for expensive multi-controlled
operations such as the Grover diffuser.

Workflow:

1. Reconstruct the one-round predicate from the reduced-order formula,
   fixed-point threshold, and finite parameter codebooks.
2. Build a width-11 extension with one additional |0> helper qubit.
3. Verify the width-11 circuit has the same nine-bit parameter distribution as
   the width-10 circuit and that the extra helper remains |0> ideally.
4. Discover installed Qiskit MCX HLS plugins dynamically.
5. Compare fully-connected compiler baselines.
6. Route width-10 variants on the strongest source-sweep patches.
7. Sample fresh exact-width 11-qubit Fez patches for one-clean-ancilla HLS
   variants and audit current CZ exposure / critical-path duration.

Calibration products are engineering proxies, not measured fidelity.  No
Sampler is instantiated and no QPU job is submitted.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.transpiler.passes import HLSConfig
from qiskit.transpiler.passes.synthesis import high_level_synthesis_plugin_names
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARDWARE = ROOT / "hardware"
for p in (HERE, HARDWARE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import audit_tct_model_derived_qpu_pilot_postmortem as post
import benchmark_tct_model_derived_fez_calibration_sweep as sweep
import ibm_nighthawk_capacity_locked_recycling_benchmark as cap
import ibm_nighthawk_subgraph_ensemble_audit as ens
import ibm_nighthawk_topology_recycling_benchmark as topo
import ibm_qubit_recycling_width_sweep as width
import ibm_recycled_interaction_graph_mapper as mapper

REV = "2026-09-21-tct-model-derived-clean-ancilla-hls-v1"
DEFAULT_SOURCE = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_fez_one_round_fresh64_opt3.json"
)
DEFAULT_OUT = (
    ROOT / "results" / "tct_surrogate_search" /
    "tct_model_derived_clean_ancilla_hls.json"
)


def parse_int_list(text: str) -> list[int]:
    vals = [int(x.strip()) for x in text.split(",") if x.strip()]
    if not vals:
        raise ValueError("empty integer list")
    return vals


def extend_with_clean_helper(base: QuantumCircuit) -> QuantumCircuit:
    qc = QuantumCircuit(base.num_qubits + 1)
    qc.compose(base, qubits=list(range(base.num_qubits)), inplace=True)
    return qc


def ideal_parameter_distribution(qc: QuantumCircuit, parameter_bits: int = 9) -> list[float]:
    sv = Statevector.from_instruction(qc)
    return post.logical_parameter_distribution(sv, parameter_bits)


def max_abs_diff(a: list[float], b: list[float]) -> float:
    return max(abs(float(x) - float(y)) for x, y in zip(a, b)) if a else 0.0


def make_hls(method: str | None, clean: int = 0) -> HLSConfig | None:
    if method is None:
        return None
    options = {}
    if clean:
        options["num_clean_ancillas"] = int(clean)
    return HLSConfig(mcx=[(method, options)] if options else [method])


def compile_with_hls(
    circuit: QuantumCircuit,
    backend,
    level: int,
    seed: int,
    initial_layout,
    hls_config: HLSConfig | None,
):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=int(level),
        seed_transpiler=int(seed),
        initial_layout=initial_layout,
        hls_config=hls_config,
    )
    t0 = time.time()
    compiled = pm.run(circuit)
    elapsed = time.time() - t0
    stats = mapper.compiled_stats(circuit, compiled, elapsed)
    return compiled, stats


def best_by_exposure(rows: list[dict]) -> dict:
    return min(
        rows,
        key=lambda r: (
            math.inf if r.get("cz_sum_p") is None else float(r["cz_sum_p"]),
            int(r["native_cz"]),
            int(r["compiled_depth"]),
            int(r["seed_transpiler"]),
        ),
    )


def select_source_rows(source: dict, n: int) -> list[dict]:
    rows = [r for r in source.get("rows", []) if r.get("patch_nodes")]
    if not rows:
        raise RuntimeError("source sweep has no patch rows")
    rows = sorted(
        rows,
        key=lambda r: (
            math.inf if r.get("cz_sum_p") is None else float(r["cz_sum_p"]),
            int(r["native_cz"]),
            int(r["compiled_depth"]),
        ),
    )
    return rows[: max(1, int(n))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--source-sweep", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--top-source-patches", type=int, default=8)
    ap.add_argument("--candidate-11q-patches", type=int, default=32)
    ap.add_argument("--patch-seed", type=int, default=1618033)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--transpiler-seeds", default="8776,2026,9401,42,1337")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    seeds = parse_int_list(args.transpiler_seeds)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    source = json.loads(args.source_sweep.read_text(encoding="utf-8"))

    base10, oracle = sweep.build_model_derived_circuit(spec, 1)
    if base10.num_qubits != 10:
        raise RuntimeError(f"expected current model-derived width 10, got {base10.num_qubits}")
    plus11 = extend_with_clean_helper(base10)

    d10 = ideal_parameter_distribution(base10, 9)
    d11 = ideal_parameter_distribution(plus11, 9)
    dist_err = max_abs_diff(d10, d11)
    sv11 = Statevector.from_instruction(plus11)
    helper_p1 = post.qubit_one_probability(sv11, 10)
    original_anc_p1 = post.qubit_one_probability(sv11, 9)
    ideal_equivalent = dist_err <= 1e-12 and helper_p1 <= 1e-12 and original_anc_p1 <= 1e-12
    if not ideal_equivalent:
        raise AssertionError("width-11 clean-helper extension failed ideal equivalence")

    installed = sorted(high_level_synthesis_plugin_names("mcx"))
    requested = {
        "baseline_default_10q": {"width": 10, "circuit": base10, "method": None, "clean": 0},
        "noaux_hp24_10q": {"width": 10, "circuit": base10, "method": "noaux_hp24", "clean": 0},
        "noaux_v24_10q": {"width": 10, "circuit": base10, "method": "noaux_v24", "clean": 0},
        "default_one_clean_11q": {"width": 11, "circuit": plus11, "method": "default", "clean": 1},
        "one_clean_kg24_11q": {"width": 11, "circuit": plus11, "method": "1_clean_kg24", "clean": 1},
        "one_clean_b95_11q": {"width": 11, "circuit": plus11, "method": "1_clean_b95", "clean": 1},
    }
    variants = {}
    skipped = {}
    for name, cfg in requested.items():
        method = cfg["method"]
        if method is not None and method not in installed:
            skipped[name] = f"mcx plugin {method!r} not installed"
            continue
        variants[name] = cfg

    service = width.ref.ibm_base.make_service()
    fez = width.ref.ibm_base.select_backend(service, 11, args.backend)
    fez_full = topo.symmetric(topo.backend_coupling(fez), int(fez.num_qubits))

    result = {
        "experiment": "tct_model_derived_clean_ancilla_hls_v1",
        "script_revision": REV,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "zero_qpu": True,
        "qpu_jobs_submitted": 0,
        "source_spec": str(args.spec),
        "source_sweep": str(args.source_sweep),
        "backend": str(fez.name),
        "calibration_last_update": sweep.cal.calibration_timestamp(fez),
        "parameter_bits": 9,
        "marked_count": int(oracle["derived_marked_count"]),
        "ideal_width11_equivalent": bool(ideal_equivalent),
        "ideal_parameter_distribution_max_abs_error": float(dist_err),
        "width11_original_ancilla_p1": float(original_anc_p1),
        "width11_extra_helper_p1": float(helper_p1),
        "installed_mcx_hls_plugins": installed,
        "skipped_variants": skipped,
        "transpiler_seeds": seeds,
        "fully_connected": {},
        "rows": [],
        "best_by_variant": {},
        "claim_boundary": (
            "Zero-QPU compiler/calibration comparison of exact one-round finite-codebook TCT predicates. "
            "The width-11 variants add one clean helper solely as a synthesis resource. Calibration error products "
            "are engineering proxies, not measured fidelity. No fusion validation or quantum-advantage claim."
        ),
    }

    print("ZERO-QPU TCT MODEL-DERIVED CLEAN-ANCILLA HLS CHALLENGER")
    print(
        f"backend={fez.name} calibration_last_update={result['calibration_last_update']} "
        f"plugins={installed}"
    )
    print(
        f"ideal_width11_equivalent={ideal_equivalent} dist_max_error={dist_err:.3e} "
        f"original_ancilla_p1={original_anc_p1:.3e} helper_p1={helper_p1:.3e}"
    )
    if skipped:
        print("skipped_variants=" + json.dumps(skipped, sort_keys=True))

    # Fully-connected compiler screen for every available variant.
    print("\n===== FULLY CONNECTED HLS SCREEN =====")
    for name, cfg in variants.items():
        n = int(cfg["width"])
        probe = topo.generic(n, mapper.full_coupling(n))
        hls = make_hls(cfg["method"], int(cfg["clean"]))
        rows = []
        for seed in seeds:
            compiled, stats = compile_with_hls(
                cfg["circuit"], probe, args.optimization_level, seed,
                list(range(n)), hls
            )
            rows.append({
                "seed_transpiler": int(seed),
                "native_cz": int(stats["native_cz"]),
                "compiled_depth": int(stats["compiled_depth"]),
                "compiled_size": int(stats["compiled_size"]),
            })
        best_fc = min(rows, key=lambda r: (r["native_cz"], r["compiled_depth"], r["seed_transpiler"]))
        result["fully_connected"][name] = {"all": rows, "best": best_fc}
        print(
            f"{name}: width={n} seed={best_fc['seed_transpiler']} "
            f"CZ={best_fc['native_cz']} depth={best_fc['compiled_depth']} size={best_fc['compiled_size']}"
        )

    source10 = select_source_rows(source, args.top_source_patches)
    patches11 = ens.patch_ensemble(
        fez_full, 11, args.candidate_11q_patches, args.patch_seed
    )

    # Width-10 variants reuse the strongest already-sampled 10q physical patches.
    for name, cfg in variants.items():
        n = int(cfg["width"])
        if n == 10:
            patch_rows = [
                {
                    "patch_index": int(r["patch_index"]),
                    "nodes": [int(x) for x in r["patch_nodes"]],
                    "mode": "source_sweep",
                }
                for r in source10
            ]
        else:
            patch_rows = [
                {
                    "patch_index": int(p["patch_index"]),
                    "nodes": [int(x) for x in p["nodes"]],
                    "mode": str(p["mode"]),
                }
                for p in patches11
            ]

        hls = make_hls(cfg["method"], int(cfg["clean"]))
        per_variant = []
        print(f"\n===== ROUTED {name} =====")
        for patch in patch_rows:
            nodes = patch["nodes"]
            subcm = cap.relabeled_subgraph(fez_full, nodes)
            backend = topo.generic(n, subcm)
            candidates = []
            for seed in seeds:
                compiled, stats = compile_with_hls(
                    cfg["circuit"], backend, args.optimization_level, seed, None, hls
                )
                if int(stats["compiled_touched_qubits"]) > n:
                    raise AssertionError("exact-width capacity lock violated")
                row = sweep.summarize_candidate(compiled, stats, fez, nodes, seed)
                row.update({
                    "variant": name,
                    "logical_width": n,
                    "patch_index": int(patch["patch_index"]),
                    "patch_mode": patch["mode"],
                    "patch_nodes": nodes,
                    "hls_method": cfg["method"],
                    "requested_clean_ancillas": int(cfg["clean"]),
                })
                candidates.append(row)
            best = best_by_exposure(candidates)
            per_variant.append(best)
            result["rows"].append(best)
            print(
                f"patch={best['patch_index']:02d} seed={best['seed_transpiler']:6d} "
                f"CZ={best['native_cz']:4d} depth={best['compiled_depth']:5d} "
                f"sum_p={best['cz_sum_p']:.3f} log10_noerr={best['cz_log10_no_error_proxy']:.3f} "
                f"duration_us={1e6*best['critical_path_s']:.1f} "
                f"dur/T1={best['duration_over_median_t1']:.3f} "
                f"dur/T2={best['duration_over_median_t2']:.3f}"
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

        bestv = best_by_exposure(per_variant)
        result["best_by_variant"][name] = bestv

    global_best = best_by_exposure(list(result["best_by_variant"].values()))
    result["global_minimum_exposure"] = global_best
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")

    print("\n===== CLEAN-ANCILLA HLS SUMMARY =====")
    for name, row in result["best_by_variant"].items():
        print(
            f"{name}: width={row['logical_width']} patch={row['patch_index']} "
            f"seed={row['seed_transpiler']} CZ={row['native_cz']} depth={row['compiled_depth']} "
            f"sum_p={row['cz_sum_p']:.3f} duration_us={1e6*row['critical_path_s']:.1f} "
            f"dur/T1={row['duration_over_median_t1']:.3f} dur/T2={row['duration_over_median_t2']:.3f}"
        )
    print(
        f"global_minimum_exposure={global_best['variant']} width={global_best['logical_width']} "
        f"patch={global_best['patch_index']} seed={global_best['seed_transpiler']} "
        f"CZ={global_best['native_cz']} sum_p={global_best['cz_sum_p']:.3f} "
        f"duration_us={1e6*global_best['critical_path_s']:.1f}"
    )
    print(f"wrote {args.out}")
    print("NO QPU JOB SUBMITTED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
