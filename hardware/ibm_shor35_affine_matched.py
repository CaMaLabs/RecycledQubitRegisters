#!/usr/bin/env python3
"""Matched IBM hardware benchmark for N=35 using a low-cost affine orbit encoding.

The earlier natural-label encoding represented exponent labels 0..11 literally
and implemented +1 mod 12 with high-order MCX gates.  This version conjugates
the same 12-state modular orbit into a 12-cycle of a 4-bit affine permutation.
The remaining four computational states form a disjoint 4-cycle and are never
populated by the algorithm.

On the encoded modular orbit, multiplication by 2 mod 35 is exactly one step of
that 12-cycle.  Its powers needed by QPE admit CNOT/X-only work-register
networks.  Adding the phase control therefore promotes CNOT -> CCX and X -> CX,
avoiding the previous 4/5-controlled gates.

This remains a compiled orbit encoding, not a generic modular multiplier.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import ibm_shor35_matched as ref
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import QFTGate
from qiskit_ibm_runtime import SamplerV2

SCRIPT_REVISION = "2026-09-13-shor35-affine-v1"
N = 35
A = 2
ORDER = 12
WORK_BITS = 4

# The affine map F has cycles:
#   0 -> 1 -> 2 -> 3 -> 0
#   4 -> 9 -> 14 -> 7 -> 8 -> 13 -> 6 -> 11 -> 12 -> 5 -> 10 -> 15 -> 4
# We encode modular exponent k in the second cycle at AFFINE_ORBIT[k].
AFFINE_ORBIT = [4, 9, 14, 7, 8, 13, 6, 11, 12, 5, 10, 15]
UNUSED_CYCLE = [0, 1, 2, 3]
MODULAR_ORBIT = [pow(A, k, N) for k in range(ORDER)]

# Exact affine power networks.  Each tuple is
#   (work-register CNOTs in execution order, final X translations).
# For F itself: rows=(1,3,8,12), b=1.
# Minimal CNOT counts for F^1,F^2,F^4,F^8 are 3,2,2,2 respectively.
POWER_NETWORKS = {
    1: ([(0, 1), (2, 3), (3, 2)], [0]),
    2: ([(3, 2), (2, 3)], [1]),
    4: ([(2, 3), (3, 2)], []),
    8: ([(3, 2), (2, 3)], []),
}


def delta_for_power(k: int) -> int:
    return (1 << k) % ORDER


def apply_controlled_affine_power(qc, control, work, delta: int):
    delta %= ORDER
    if delta not in POWER_NETWORKS:
        raise ValueError(f"Unsupported affine power {delta}; expected 1,2,4,8")
    cnots, xbits = POWER_NETWORKS[delta]
    for c, t in cnots:
        qc.ccx(control, work[c], work[t])
    for t in xbits:
        qc.cx(control, work[t])


def _apply_network_to_int(x: int, delta: int) -> int:
    cnots, xbits = POWER_NETWORKS[delta]
    v = x
    for c, t in cnots:
        if (v >> c) & 1:
            v ^= 1 << t
    for t in xbits:
        v ^= 1 << t
    return v


def self_test_affine_encoding() -> dict:
    details = {}
    full_cycles = [UNUSED_CYCLE, AFFINE_ORBIT]
    for delta in (1, 2, 4, 8):
        expected = [None] * 16
        for cyc in full_cycles:
            L = len(cyc)
            for i, x in enumerate(cyc):
                expected[x] = cyc[(i + delta) % L]
        got = [_apply_network_to_int(x, delta) for x in range(16)]
        details[str(delta)] = {
            "got": got,
            "expected": expected,
            "pass": got == expected,
            "cnot_count": len(POWER_NETWORKS[delta][0]),
            "x_count": len(POWER_NETWORKS[delta][1]),
        }

    modular_ok = MODULAR_ORBIT == ref.ORBIT
    details["encoding"] = {
        "encoded_basis_states": AFFINE_ORBIT,
        "modular_orbit": MODULAR_ORBIT,
        "expected_modular_orbit": ref.ORBIT,
        "pass": modular_ok,
    }
    details["six_round_controlled_gate_budget"] = {
        "phase_power_sequence": [delta_for_power(k) for k in range(6)],
        "ccx": sum(len(POWER_NETWORKS[delta_for_power(k)][0]) for k in range(6)),
        "cx": sum(len(POWER_NETWORKS[delta_for_power(k)][1]) for k in range(6)),
    }
    details["pass"] = all(v.get("pass", True) for v in details.values())
    return details


def initialize_work(qc, work):
    # Exponent label 0 / modular state |1> is encoded as integer 4 = 0100.
    qc.x(work[2])


def build_recycled(phase_bits: int, use_measure2: bool):
    q = QuantumRegister(1 + WORK_BITS, "q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(q, phase, name=f"shor35_affine_recycled_{phase_bits}b")
    anc = q[0]
    work = list(q[1:])
    initialize_work(qc, work)

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        apply_controlled_affine_power(qc, anc, work, delta_for_power(k))
        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)
        qc.h(anc)
        ref.ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)
    return qc


def build_wide(phase_bits: int):
    phase_q = QuantumRegister(phase_bits, "phase_q")
    work_q = QuantumRegister(WORK_BITS, "work_q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work_q, phase, name=f"shor35_affine_wide_{phase_bits}b")
    initialize_work(qc, list(work_q))
    for k in range(phase_bits):
        qc.h(phase_q[k])
        apply_controlled_affine_power(qc, phase_q[k], list(work_q), delta_for_power(k))
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc


def main():
    ap = argparse.ArgumentParser(description="Affine-encoded matched N=35 Shor hardware test.")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=6)
    ap.add_argument("--shots", type=int, default=512)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--max-execution-time", type=int, default=120)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--transpile-only", action="store_true")
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor35_affine"))
    args = ap.parse_args()

    test = self_test_affine_encoding()
    print("Affine encoding self-test:", "PASS" if test["pass"] else "FAIL")
    print(json.dumps(test, indent=2))
    if not test["pass"]:
        raise SystemExit("Affine encoding self-test failed.")
    if args.self_test:
        print("Ideal finite-precision reference:")
        print(json.dumps(ref.ideal_metrics(args.phase_bits), indent=2))
        return
    if args.phase_bits < 4:
        raise SystemExit("Use at least 4 phase bits; 6 is recommended.")

    service = ref.ibm_base.make_service()
    before = ref.ibm_base.safe_usage(service)
    backend = ref.ibm_base.select_backend(service, WORK_BITS + args.phase_bits, args.backend)
    use_measure2 = ref.ibm_base.backend_has_measure2(backend)
    plan = ref.choose_shared_plan(backend, args.phase_bits)

    print("Script revision:", SCRIPT_REVISION)
    print(f"Problem: N={N}, a={A}, order={ORDER}, phase_bits={args.phase_bits}")
    print("Affine work orbit:", AFFINE_ORBIT)
    print("Modular orbit:", MODULAR_ORBIT)
    print(f"Backend: {backend.name} | measure_2={use_measure2}")
    print("Account usage:")
    print(json.dumps(before, indent=2, default=str))
    print("Ideal finite-precision reference:")
    print(json.dumps(ref.ideal_metrics(args.phase_bits), indent=2))
    print("Shared-work plan:")
    print(json.dumps(plan, indent=2, default=str))

    recycled = build_recycled(args.phase_bits, use_measure2)
    wide = build_wide(args.phase_bits)
    compiled_recycled = ref.compile_with_layout(
        recycled, backend, args.optimization_level, plan["recycled_initial_layout"]
    )
    compiled_wide = ref.compile_with_layout(
        wide, backend, args.optimization_level, plan["wide_initial_layout"]
    )
    compiled = [compiled_recycled, compiled_wide]
    kinds = ["recycled", "wide"]
    transpiled_stats = [
        ref.stats(recycled, compiled_recycled, "recycled", plan["recycled_initial_layout"]),
        ref.stats(wide, compiled_wide, "wide", plan["wide_initial_layout"]),
    ]
    print("Transpiled stats:")
    print(json.dumps(transpiled_stats, indent=2, default=str))

    out_base = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": N,
        "a": A,
        "true_order_for_validation_only": ORDER,
        "phase_bits": args.phase_bits,
        "shots": args.shots,
        "encoding": "affine_12_cycle_plus_4_cycle",
        "affine_orbit": AFFINE_ORBIT,
        "modular_orbit": MODULAR_ORBIT,
        "self_test": test,
        "same_job": True,
        "same_initial_work_register": True,
        "ideal_reference": ref.ideal_metrics(args.phase_bits),
        "shared_layout_plan": plan,
        "transpiled_stats": transpiled_stats,
        "account_usage_before": before,
        "scope_note": (
            "Exact compiled affine encoding of the 12-state a=2 mod35 orbit. "
            "The other four computational states form a disjoint 4-cycle. "
            "This is not a generic modular multiplier."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.transpile_only:
        path = args.outdir / f"ibm_shor35_affine_transpile_{args.phase_bits}b.json"
        path.write_text(json.dumps(out_base, indent=2, default=str) + "\n")
        print("Transpile-only; no QPU job submitted.")
        print("Saved:", path.resolve())
        return

    print(f"Submitting recycled + wide together: 2 circuits x {args.shots} shots...")
    sampler = SamplerV2(mode=backend, options={"max_execution_time": args.max_execution_time})
    job = sampler.run(compiled, shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    results = []
    for pub, kind in zip(pubs, kinds):
        counts = getattr(pub.data, "phase").get_counts()
        results.append({
            "kind": kind,
            "counts": counts,
            "analysis": ref.analyze_counts(counts, args.phase_bits),
            "distribution": ref.distribution_metrics(counts, args.phase_bits),
        })

    out = {
        **out_base,
        "job_id": job.job_id(),
        "metrics": ref.ibm_base.safe_metrics(job),
        "results": results,
        "paired_comparison": ref.comparison(results, args.phase_bits),
        "account_usage_after": ref.ibm_base.safe_usage(service),
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"ibm_shor35_affine_{args.phase_bits}b_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nRESULT")
    print(json.dumps(out, indent=2, default=str))
    print("\nSaved:", path.resolve())
    print("PAIRED:", json.dumps(out["paired_comparison"], sort_keys=True))


if __name__ == "__main__":
    main()
