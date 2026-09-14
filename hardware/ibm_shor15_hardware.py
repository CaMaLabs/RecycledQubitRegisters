#!/usr/bin/env python3
"""End-to-end real-QPU toy Shor/order-finding test for N=15.

This is deliberately scoped to the canonical compiled demonstration N=15, a=2.
The modular multiplication is NOT an injected eigenphase: the circuit carries a
4-qubit modular work register initialized to |1> and applies controlled
multiplication-by-2 or multiplication-by-4 mod 15 using controlled SWAP gates.

Architectures:
  recycled: 1 recyclable phase ancilla + 4-qubit work register, with
            mid-circuit measurement/reset/classical feed-forward.
  wide:     m phase qubits + 4-qubit work register + inverse QFT.

Post-processing receives only measured phase-register bitstrings, N, and a.
It recovers a candidate order, verifies a^r mod N == 1, and attempts the usual
Shor gcd(a^(r/2) +/- 1, N) factor extraction.

Tested API target: qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

try:
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
    from qiskit.circuit.library import QFTGate
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    try:
        from qiskit_ibm_runtime.circuit import MidCircuitMeasure
    except Exception:
        MidCircuitMeasure = None
except Exception:
    print("Missing Qiskit dependencies.", file=sys.stderr)
    print('Install with: python -m pip install "qiskit~=2.5.2" "qiskit-ibm-runtime~=0.47.0"', file=sys.stderr)
    raise

SCRIPT_REVISION = "2026-09-13-shor15-hardware-v1"
N = 15
A = 2
WORK_BITS = 4


def make_service():
    instance = os.getenv("IBM_QUANTUM_INSTANCE")
    if instance:
        return QiskitRuntimeService(instance=instance)
    token = os.getenv("IBM_QUANTUM_API_KEY")
    if token:
        return QiskitRuntimeService(token=token, plans_preference=["open"], region="us-east")
    return QiskitRuntimeService(plans_preference=["open"], region="us-east")


def safe_usage(service):
    try:
        return service.usage()
    except Exception as exc:
        return {"unavailable": str(exc)}


def safe_metrics(job):
    try:
        return job.metrics()
    except Exception as exc:
        return {"unavailable": str(exc)}


def backend_has_measure2(backend):
    try:
        return "measure_2" in backend.supported_instructions
    except Exception:
        return False


def select_backend(service, min_qubits, backend_name=None):
    if backend_name:
        backend = service.backend(backend_name)
        status = backend.status()
        if not status.operational:
            raise SystemExit(f"Backend {backend_name} is not operational.")
        if backend.num_qubits < min_qubits:
            raise SystemExit(
                f"Backend {backend_name} has only {backend.num_qubits} qubits; "
                f"{min_qubits} are required."
            )
        return backend
    return service.least_busy(
        operational=True,
        simulator=False,
        dynamic_circuits=True,
        min_num_qubits=min_qubits,
    )


def mid_measure(qc, qubit, clbit, use_measure2):
    if use_measure2 and MidCircuitMeasure is not None:
        qc.append(MidCircuitMeasure(), [qubit], [clbit])
    else:
        qc.measure(qubit, clbit)


def multiplier_for_power(k: int) -> int:
    return pow(A, 1 << k, N)


def apply_controlled_modmul15(qc, control, work, multiplier: int):
    if multiplier == 1:
        return
    if multiplier == 2:
        qc.cswap(control, work[2], work[3])
        qc.cswap(control, work[1], work[2])
        qc.cswap(control, work[0], work[1])
        return
    if multiplier == 4:
        qc.cswap(control, work[1], work[3])
        qc.cswap(control, work[0], work[2])
        return
    raise ValueError(f"Unsupported compiled multiplier {multiplier}; expected 1, 2, or 4")


def build_recycled_shor15(phase_bits: int, use_measure2: bool = True):
    q = QuantumRegister(1 + WORK_BITS, "q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(q, phase, name=f"shor15_recycled_{phase_bits}b")
    anc = q[0]
    work = list(q[1:])
    qc.x(work[0])

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        apply_controlled_modmul15(qc, anc, work, multiplier_for_power(k))

        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)

        qc.h(anc)
        mid_measure(qc, anc, phase[dest], use_measure2)
    return qc


def build_wide_shor15(phase_bits: int):
    phase_q = QuantumRegister(phase_bits, "phase_q")
    work_q = QuantumRegister(WORK_BITS, "work_q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work_q, phase, name=f"shor15_wide_{phase_bits}b")
    qc.x(work_q[0])
    for k in range(phase_bits):
        qc.h(phase_q[k])
        apply_controlled_modmul15(qc, phase_q[k], work_q, multiplier_for_power(k))
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc


def _prime_divisors(n: int):
    out = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d = 3 if d == 2 else d + 2
    if n > 1:
        out.append(n)
    return out


def minimize_order(a: int, n: int, candidate: int) -> int:
    r = candidate
    for p in _prime_divisors(candidate):
        while r % p == 0 and pow(a, r // p, n) == 1:
            r //= p
    return r


def recover_from_phase_integer(y: int, phase_bits: int, tolerance_bins: float = 1.5):
    if y == 0:
        return None
    q = 1 << phase_bits
    frac = Fraction(y, q).limit_denominator(N)
    d = frac.denominator
    max_multiple = min(8, N // max(1, d))

    for multiple in range(1, max_multiple + 1):
        candidate = d * multiple
        if candidate <= 1 or pow(A, candidate, N) != 1:
            continue
        r = minimize_order(A, N, candidate)
        if r <= 1:
            continue

        phase = y / q
        nearest_s = min(range(1, r), key=lambda s: abs(phase - s / r))
        distance = abs(phase - nearest_s / r)
        if distance > tolerance_bins / q:
            continue

        if r % 2:
            continue
        x = pow(A, r // 2, N)
        if x in (1, N - 1):
            continue
        for g in (math.gcd(x - 1, N), math.gcd(x + 1, N)):
            if 1 < g < N and N % g == 0:
                factors = (min(g, N // g), max(g, N // g))
                return {
                    "denominator": d,
                    "order": r,
                    "nearest_s": nearest_s,
                    "phase_distance_bins": distance * q,
                    "factors": list(factors),
                }
    return None


def normalize_bitstring(s: str) -> str:
    return s.replace(" ", "")


def analyze_counts(counts, phase_bits: int):
    total = int(sum(counts.values()))
    rows = []
    good = 0
    recovered_factor_counts = {}
    for raw, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        bitstring = normalize_bitstring(raw)
        y = int(bitstring, 2)
        recovered = recover_from_phase_integer(y, phase_bits)
        informative = recovered is not None
        if informative:
            good += int(count)
            key = "x".join(map(str, recovered["factors"]))
            recovered_factor_counts[key] = recovered_factor_counts.get(key, 0) + int(count)
        rows.append({
            "bitstring": bitstring,
            "count": int(count),
            "probability": count / total,
            "y": y,
            "phase": y / (1 << phase_bits),
            "recoverable": informative,
            "recovery": recovered,
        })
    return {
        "shots": total,
        "factor_success_probability_per_shot": good / total if total else 0.0,
        "aggregate_factor_recovered": bool(recovered_factor_counts),
        "recovered_factor_counts": recovered_factor_counts,
        "top": rows[:16],
    }


def compile_circuit(circuit, backend, optimization_level=2):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=optimization_level,
        seed_transpiler=8776,
    )
    return pm.run(circuit)


def circuit_stats(original, compiled, kind):
    try:
        physical_layout = compiled.layout.final_index_layout(filter_ancillas=True)
    except Exception:
        physical_layout = None
    return {
        "kind": kind,
        "logical_qubits": original.num_qubits,
        "compiled_qubits": compiled.num_qubits,
        "physical_layout": physical_layout,
        "depth": compiled.depth(),
        "size": compiled.size(),
        "count_ops": {str(k): int(v) for k, v in compiled.count_ops().items()},
    }


def main():
    ap = argparse.ArgumentParser(description="Real-IBM toy Shor test: factor N=15 with a=2.")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--architecture", choices=["recycled", "wide", "compare"], default="recycled")
    ap.add_argument("--phase-bits", type=int, default=4)
    ap.add_argument("--shots", type=int, default=256)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=2)
    ap.add_argument("--max-execution-time", type=int, default=60)
    ap.add_argument("--transpile-only", action="store_true")
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor15"))
    args = ap.parse_args()

    if args.phase_bits < 2:
        raise SystemExit("Use at least 2 phase bits for N=15, a=2.")

    print("Script revision:", SCRIPT_REVISION)
    print(f"Problem: N={N}, a={A}, expected nontrivial factors=(3,5), true order=4")
    print("Architecture:", args.architecture, "| phase_bits=", args.phase_bits)

    service = make_service()
    before = safe_usage(service)
    print("Current account usage:")
    print(json.dumps(before, indent=2, default=str))

    min_qubits = WORK_BITS + (args.phase_bits if args.architecture in ("wide", "compare") else 1)
    backend = select_backend(service, min_qubits, args.backend)
    use_measure2 = backend_has_measure2(backend)
    print(f"Selected backend: {backend.name} | qubits={backend.num_qubits} | measure_2={use_measure2}")

    logical = []
    kinds = []
    if args.architecture in ("recycled", "compare"):
        logical.append(build_recycled_shor15(args.phase_bits, use_measure2))
        kinds.append("recycled")
    if args.architecture in ("wide", "compare"):
        logical.append(build_wide_shor15(args.phase_bits))
        kinds.append("wide")

    print("Transpiling actual modular-multiplication circuit(s)...")
    compiled = [compile_circuit(c, backend, args.optimization_level) for c in logical]
    stats = [circuit_stats(o, c, k) for o, c, k in zip(logical, compiled, kinds)]
    print(json.dumps({"transpiled_stats": stats}, indent=2, default=str))

    base_result = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": N,
        "a": A,
        "expected_factors": [3, 5],
        "true_order_for_validation_only": 4,
        "phase_bits": args.phase_bits,
        "shots": args.shots,
        "architecture": args.architecture,
        "measure_2_used": use_measure2,
        "account_usage_before": before,
        "transpiled_stats": stats,
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.transpile_only:
        path = args.outdir / f"ibm_shor15_transpile_{args.architecture}_{args.phase_bits}b.json"
        path.write_text(json.dumps(base_result, indent=2, default=str) + "\n")
        print("Transpile-only; no QPU job submitted.")
        print("Saved:", path.resolve())
        return 0

    sampler = SamplerV2(mode=backend, options={"max_execution_time": args.max_execution_time})
    print(f"Submitting {len(compiled)} circuit(s) x {args.shots} shots...")
    job = sampler.run(compiled, shots=args.shots)
    print("Job ID:", job.job_id())
    pubs = job.result()

    results = []
    for pub, kind in zip(pubs, kinds):
        counts = getattr(pub.data, "phase").get_counts()
        results.append({
            "kind": kind,
            "counts": counts,
            "analysis": analyze_counts(counts, args.phase_bits),
        })

    after = safe_usage(service)
    out = {
        **base_result,
        "job_id": job.job_id(),
        "metrics": safe_metrics(job),
        "results": results,
        "account_usage_after": after,
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"ibm_shor15_{args.architecture}_{args.phase_bits}b_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")

    print("\nRESULT")
    print(json.dumps(out, indent=2, default=str))
    print("\nSaved:", path.resolve())
    for item in results:
        ares = item["analysis"]
        print(
            f"{item['kind']}: aggregate_factor_recovered={ares['aggregate_factor_recovered']} "
            f"per_shot_factor_success={ares['factor_success_probability_per_shot']:.4f} "
            f"factor_counts={ares['recovered_factor_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
