#!/usr/bin/env python3
"""Matched same-job IBM Quantum compiled-orbit Shor test for N=35, a=2.

This extends the N=21 hardware benchmark to a 12-state multiplicative orbit.
The coherent modular orbit of 2 mod 35 is encoded by labels 0..11 in a 4-qubit
work register. Labels 12..15 are fixed. Multiplication by 2 mod 35 is +1 mod 12
on the encoded orbit; U^(2^k) is +2^k mod 12.

This is an exact compiled orbit encoding, not a generic 6-qubit modular
multiplier and not a large-RSA resource claim.

Wide and recycled circuits are submitted in the same SamplerV2 job, start from
the same physical work-register sites, and use one shared physical neighborhood.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import ibm_shor15_hardware as ibm_base
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import MCXGate, QFTGate
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import SamplerV2

SCRIPT_REVISION = "2026-09-13-shor35-matched-v1"
N = 35
A = 2
TRUE_ORDER_FOR_VALIDATION_ONLY = 12
WORK_BITS = 4
ORBIT = [1, 2, 4, 8, 16, 32, 29, 23, 11, 22, 9, 18]


def delta_for_power(k: int) -> int:
    return (1 << k) % TRUE_ORDER_FOR_VALIDATION_ONLY


def append_mcx(qc, controls, target):
    controls = list(controls)
    if len(controls) == 1:
        qc.cx(controls[0], target)
    elif len(controls) == 2:
        qc.ccx(controls[0], controls[1], target)
    else:
        qc.append(MCXGate(len(controls)), controls + [target])


def apply_controlled_shift_mod12(qc, control, work, delta: int):
    """Exact controlled +delta mod 12 on |0>..|11>; |12>..|15> fixed."""
    w0, w1, w2, w3 = work
    delta %= 12
    if delta == 0:
        return
    if delta == 1:
        append_mcx(qc, [control, w2, w3], w0)
        append_mcx(qc, [control, w0, w2, w3], w1)
        append_mcx(qc, [control, w0, w1, w3], w2)
        append_mcx(qc, [control, w0, w1, w2], w3)
        append_mcx(qc, [control, w0, w1], w2)
        append_mcx(qc, [control, w0], w1)
        append_mcx(qc, [control], w0)
        return
    if delta == 2:
        append_mcx(qc, [control, w1], w3)
        append_mcx(qc, [control, w1, w3], w2)
        append_mcx(qc, [control, w1, w2], w3)
        append_mcx(qc, [control, w2, w3], w1)
        append_mcx(qc, [control], w1)
        return
    if delta == 4:
        append_mcx(qc, [control], w3)
        append_mcx(qc, [control, w3], w2)
        append_mcx(qc, [control, w2], w3)
        return
    if delta == 8:
        append_mcx(qc, [control], w2)
        append_mcx(qc, [control, w2], w3)
        append_mcx(qc, [control, w3], w2)
        return
    raise ValueError(f"Unsupported mod-12 shift {delta}; expected 0,1,2,4,8")


def _uncontrolled_map_for_delta(delta: int) -> list[int]:
    return [((x + delta) % 12) if x < 12 else x for x in range(16)]


def _apply_uncontrolled_gate_sequence(delta: int, x: int) -> int:
    def bit(v, i):
        return (v >> i) & 1

    def flip(v, t):
        return v ^ (1 << t)

    def mcx(v, controls, target):
        return flip(v, target) if all(bit(v, c) for c in controls) else v

    v = x
    if delta == 1:
        for controls, target in [
            ((2, 3), 0),
            ((0, 2, 3), 1),
            ((0, 1, 3), 2),
            ((0, 1, 2), 3),
            ((0, 1), 2),
            ((0,), 1),
            ((), 0),
        ]:
            v = flip(v, target) if not controls else mcx(v, controls, target)
    elif delta == 2:
        for controls, target in [
            ((1,), 3),
            ((1, 3), 2),
            ((1, 2), 3),
            ((2, 3), 1),
            ((), 1),
        ]:
            v = flip(v, target) if not controls else mcx(v, controls, target)
    elif delta == 4:
        for controls, target in [((), 3), ((3,), 2), ((2,), 3)]:
            v = flip(v, target) if not controls else mcx(v, controls, target)
    elif delta == 8:
        for controls, target in [((), 2), ((2,), 3), ((3,), 2)]:
            v = flip(v, target) if not controls else mcx(v, controls, target)
    elif delta != 0:
        raise ValueError(delta)
    return v


def self_test_compiled_orbit() -> dict:
    details = {}
    for delta in (1, 2, 4, 8):
        got = [_apply_uncontrolled_gate_sequence(delta, x) for x in range(16)]
        expected = _uncontrolled_map_for_delta(delta)
        details[str(delta)] = {"got": got, "expected": expected, "pass": got == expected}
    orbit_check = [pow(A, k, N) for k in range(TRUE_ORDER_FOR_VALIDATION_ONLY)]
    details["orbit"] = {
        "computed": orbit_check,
        "expected": ORBIT,
        "pass": orbit_check == ORBIT and pow(A, TRUE_ORDER_FOR_VALIDATION_ONLY, N) == 1,
    }
    details["pass"] = all(v["pass"] for v in details.values())
    return details


def build_recycled(phase_bits: int, use_measure2: bool):
    q = QuantumRegister(1 + WORK_BITS, "q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(q, phase, name=f"shor35_recycled_{phase_bits}b")
    anc = q[0]
    work = list(q[1:])

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        apply_controlled_shift_mod12(qc, anc, work, delta_for_power(k))

        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)

        qc.h(anc)
        ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)
    return qc


def build_wide(phase_bits: int):
    phase_q = QuantumRegister(phase_bits, "phase_q")
    work_q = QuantumRegister(WORK_BITS, "work_q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work_q, phase, name=f"shor35_wide_{phase_bits}b")

    for k in range(phase_bits):
        qc.h(phase_q[k])
        apply_controlled_shift_mod12(qc, phase_q[k], list(work_q), delta_for_power(k))

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


def convergent_denominators(num: int, den: int):
    coeffs = []
    n, d = num, den
    while d:
        q, rem = divmod(n, d)
        coeffs.append(q)
        n, d = d, rem
    p_nm2, p_nm1 = 0, 1
    q_nm2, q_nm1 = 1, 0
    for coeff in coeffs:
        p = coeff * p_nm1 + p_nm2
        q = coeff * q_nm1 + q_nm2
        if q:
            yield q
        p_nm2, p_nm1 = p_nm1, p
        q_nm2, q_nm1 = q_nm1, q


def recover_from_phase_integer(y: int, phase_bits: int, tolerance_bins: float = 1.5):
    if y == 0:
        return None
    q = 1 << phase_bits
    denoms = []
    for d in convergent_denominators(y, q):
        if 1 < d <= N and d not in denoms:
            denoms.append(d)

    for d in denoms:
        max_multiple = min(24, N // d)
        for multiple in range(1, max_multiple + 1):
            candidate = d * multiple
            if candidate <= 1 or pow(A, candidate, N) != 1:
                continue
            r = minimize_order(A, N, candidate)
            if r <= 1 or r % 2:
                continue
            phase = y / q
            nearest_s = min(range(1, r), key=lambda s: abs(phase - s / r))
            distance = abs(phase - nearest_s / r)
            if distance > tolerance_bins / q:
                continue
            x = pow(A, r // 2, N)
            if x in (1, N - 1):
                continue
            found = []
            for g in (math.gcd(x - 1, N), math.gcd(x + 1, N)):
                if 1 < g < N and N % g == 0:
                    factors = (min(g, N // g), max(g, N // g))
                    if factors not in found:
                        found.append(factors)
            if found:
                return {
                    "continued_fraction_denominator": d,
                    "denominator_multiple": multiple,
                    "recovery_mode": "direct" if multiple == 1 else "verified_multiple",
                    "order": r,
                    "nearest_s": nearest_s,
                    "phase_distance_bins": distance * q,
                    "factors": list(found[0]),
                }
    return None


def analyze_counts(counts, phase_bits: int):
    total = int(sum(counts.values()))
    rows = []
    good = 0
    direct = 0
    factor_counts = {}
    for raw, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        bitstring = raw.replace(" ", "")
        y = int(bitstring, 2)
        rec = recover_from_phase_integer(y, phase_bits)
        if rec:
            good += int(count)
            if rec["recovery_mode"] == "direct":
                direct += int(count)
            key = "x".join(map(str, rec["factors"]))
            factor_counts[key] = factor_counts.get(key, 0) + int(count)
        rows.append({
            "bitstring": bitstring,
            "count": int(count),
            "probability": count / total,
            "y": y,
            "phase": y / (1 << phase_bits),
            "recoverable": rec is not None,
            "recovery": rec,
        })
    return {
        "shots": total,
        "factor_success_probability_per_shot": good / total if total else 0.0,
        "direct_order_factor_probability_per_shot": direct / total if total else 0.0,
        "aggregate_factor_recovered": bool(factor_counts),
        "recovered_factor_counts": factor_counts,
        "top": rows[:32],
    }


def ideal_order_distribution(phase_bits: int, order: int = TRUE_ORDER_FOR_VALIDATION_ONLY):
    q = 1 << phase_bits
    probs = [0.0] * q
    for s in range(order):
        phi = s / order
        for y in range(q):
            delta = phi - y / q
            if abs(delta - round(delta)) < 1e-15:
                p = 1.0
            else:
                num = math.sin(math.pi * q * delta)
                den = math.sin(math.pi * delta)
                p = (num / (q * den)) ** 2
            probs[y] += p / order
    norm = sum(probs)
    return [p / norm for p in probs]


def ideal_metrics(phase_bits: int):
    probs = ideal_order_distribution(phase_bits)
    recoverable = sum(p for y, p in enumerate(probs) if recover_from_phase_integer(y, phase_bits))
    return {
        "ideal_factor_recovery_under_same_postprocessor": recoverable,
        "zero_phase_probability": probs[0],
        "top": [
            {"y": y, "bitstring": format(y, f"0{phase_bits}b"), "probability": p}
            for y, p in sorted(enumerate(probs), key=lambda kv: kv[1], reverse=True)[:20]
        ],
    }


def distribution_metrics(counts, phase_bits: int):
    q = 1 << phase_bits
    n = sum(counts.values())
    obs = [0.0] * q
    for raw, count in counts.items():
        obs[int(raw.replace(" ", ""), 2)] += count / n
    ideal = ideal_order_distribution(phase_bits)
    tv = 0.5 * sum(abs(a - b) for a, b in zip(obs, ideal))
    affinity = sum(math.sqrt(a * b) for a, b in zip(obs, ideal))
    return {
        "total_variation_distance_to_ideal": tv,
        "hellinger_fidelity_to_ideal": affinity * affinity,
        "zero_phase_probability": obs[0],
    }


def inst_props(backend, name, qubits):
    try:
        p = backend.target[name][tuple(qubits)]
        return {
            "duration_s": None if p.duration is None else float(p.duration),
            "error": None if p.error is None else float(p.error),
        }
    except Exception:
        return {"duration_s": None, "error": None}


def cz_graph(backend):
    edges = set()
    for qargs in backend.target["cz"].keys():
        if qargs is not None and len(qargs) == 2:
            a, b = map(int, qargs)
            edges.add((a, b))
    und = {}
    for a, b in edges:
        und.setdefault(a, set()).add(b)
        und.setdefault(b, set()).add(a)
    return edges, und


def choose_shared_plan(backend, phase_bits: int):
    region_size = phase_bits + WORK_BITS
    _, und = cz_graph(backend)
    if not und:
        raise RuntimeError("No CZ graph exposed by backend.")
    dist_cache = {}

    def dist(a, b):
        if (a, b) in dist_cache:
            return dist_cache[a, b]
        q = deque([(a, 0)])
        seen = {a}
        while q:
            u, d = q.popleft()
            if u == b:
                dist_cache[a, b] = dist_cache[b, a] = d
                return d
            for v in und.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    q.append((v, d + 1))
        return 999

    def edge_error(a, b):
        vals = []
        for pair in ((a, b), (b, a)):
            p = inst_props(backend, "cz", pair)
            if p["error"] is not None:
                vals.append(p["error"])
        return min(vals) if vals else 1.0

    def mcm_error(q):
        p = inst_props(backend, "measure_2", (q,))
        if p["error"] is not None:
            return p["error"]
        p = inst_props(backend, "measure", (q,))
        return p["error"] if p["error"] is not None else 1.0

    def mcm_duration(q):
        p = inst_props(backend, "measure_2", (q,))
        if p["duration_s"] is not None:
            return p["duration_s"]
        p = inst_props(backend, "measure", (q,))
        return p["duration_s"] if p["duration_s"] is not None else 1.0

    candidates = []
    work_pairs = tuple(itertools.combinations(range(WORK_BITS), 2))
    ancillas = sorted(und, key=lambda q: (mcm_error(q), mcm_duration(q)))[:32]

    for anc in ancillas:
        region = [anc]
        while len(region) < region_size:
            frontier = []
            seen_v = set()
            for u in region:
                for v in und.get(u, ()):
                    if v in region or v in seen_v:
                        continue
                    seen_v.add(v)
                    frontier.append((edge_error(u, v), v))
            if not frontier:
                break
            frontier.sort()
            region.append(frontier[0][1])
        if len(region) != region_size:
            continue

        others = [q for q in region if q != anc]
        best = None
        for work_tuple in itertools.permutations(others, WORK_BITS):
            work = list(work_tuple)
            work_cost = sum(dist(work[i], work[j]) for i, j in work_pairs)
            leftover = [q for q in others if q not in work]
            leftover.sort(key=lambda q: sum(dist(q, w) for w in work))
            phases = [anc] + leftover
            if len(phases) != phase_bits:
                continue
            control_cost = sum(dist(p, w) for p in phases for w in work)
            qft_cost = sum(
                dist(phases[i], phases[j])
                for i in range(phase_bits)
                for j in range(i + 1, phase_bits)
            )
            local = work_cost + 0.22 * control_cost + 0.05 * qft_cost
            if best is None or local < best[0]:
                best = (local, work, phases)

        if best is None:
            continue
        local_errors = []
        for u in region:
            for v in und.get(u, ()):
                if v in region and u < v:
                    local_errors.append(edge_error(u, v))
        local_mean = sum(local_errors) / len(local_errors) if local_errors else 1.0
        score = (
            best[0]
            + 400.0 * mcm_error(anc)
            + 30.0 * local_mean
            + 0.02 * (mcm_duration(anc) / 1e-6)
        )
        candidates.append((score, anc, region, best[1], best[2], local_mean))

    if not candidates:
        raise RuntimeError(f"Could not find shared {region_size}-qubit region.")
    candidates.sort(key=lambda x: x[0])
    score, anc, region, work, phases, local_mean = candidates[0]
    return {
        "score": score,
        "region": region,
        "phase_bits": phase_bits,
        "shared_initial_work_physical": work,
        "recycled_ancilla_physical": anc,
        "wide_phase_physical": phases,
        "recycled_initial_layout": [anc] + work,
        "wide_initial_layout": phases + work,
        "ancilla_measure_2": inst_props(backend, "measure_2", (anc,)),
        "ancilla_measure": inst_props(backend, "measure", (anc,)),
        "local_mean_cz_error": local_mean,
    }


def compile_with_layout(circuit, backend, level, layout):
    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=level,
        seed_transpiler=8776,
        initial_layout=layout,
    )
    return pm.run(circuit)


def stats(original, compiled, kind, requested_layout):
    try:
        final_layout = compiled.layout.final_index_layout(filter_ancillas=True)
    except Exception:
        final_layout = None
    return {
        "kind": kind,
        "logical_qubits": original.num_qubits,
        "compiled_qubits": compiled.num_qubits,
        "requested_initial_layout": requested_layout,
        "physical_layout_after_transpile": final_layout,
        "depth": compiled.depth(),
        "size": compiled.size(),
        "count_ops": {str(k): int(v) for k, v in compiled.count_ops().items()},
    }


def wilson(k, n, z=1.959963984540054):
    p = k / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [center - half, center + half]


def comparison(results, phase_bits: int):
    by = {r["kind"]: r for r in results}
    w, r = by["wide"], by["recycled"]
    wa, ra = w["analysis"], r["analysis"]
    nw, nr = wa["shots"], ra["shots"]
    kw = round(wa["factor_success_probability_per_shot"] * nw)
    kr = round(ra["factor_success_probability_per_shot"] * nr)
    pw, pr = kw / nw, kr / nr
    se = math.sqrt(pw * (1 - pw) / nw + pr * (1 - pr) / nr)
    return {
        "wide_factor_success": pw,
        "recycled_factor_success": pr,
        "recycled_minus_wide": pr - pw,
        "difference_standard_errors": (pr - pw) / se if se else None,
        "wide_wilson95": wilson(kw, nw),
        "recycled_wilson95": wilson(kr, nr),
        "wide_distribution": distribution_metrics(w["counts"], phase_bits),
        "recycled_distribution": distribution_metrics(r["counts"], phase_bits),
        "ideal_reference": ideal_metrics(phase_bits),
    }


def main():
    ap = argparse.ArgumentParser(description="Matched real-QPU compiled Shor test: N=35, a=2, r=12.")
    ap.add_argument("--backend", default="ibm_fez")
    ap.add_argument("--phase-bits", type=int, default=6)
    ap.add_argument("--shots", type=int, default=512)
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=2)
    ap.add_argument("--max-execution-time", type=int, default=120)
    ap.add_argument("--transpile-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor35"))
    args = ap.parse_args()

    self_test = self_test_compiled_orbit()
    if not self_test["pass"]:
        raise SystemExit(f"Compiled orbit self-test failed: {self_test}")
    print("Compiled orbit self-test: PASS")
    print(json.dumps(self_test, indent=2))

    if args.self_test:
        print("Ideal reference:")
        print(json.dumps(ideal_metrics(args.phase_bits), indent=2))
        return

    if args.phase_bits < 5:
        raise SystemExit("Use at least 5 phase bits for the r=12 N=35 test; 6 is recommended.")

    wide_qubits = WORK_BITS + args.phase_bits
    service = ibm_base.make_service()
    before = ibm_base.safe_usage(service)
    backend = ibm_base.select_backend(service, wide_qubits, args.backend)
    use_measure2 = ibm_base.backend_has_measure2(backend)

    print("Script revision:", SCRIPT_REVISION)
    print(f"Problem: N={N}, a={A}, validation order={TRUE_ORDER_FOR_VALIDATION_ONLY}, phase_bits={args.phase_bits}")
    print("Orbit encoding:", dict(enumerate(ORBIT)))
    print(f"Backend: {backend.name} | measure_2={use_measure2}")
    print("Account usage:")
    print(json.dumps(before, indent=2, default=str))
    print("Ideal finite-precision reference:")
    print(json.dumps(ideal_metrics(args.phase_bits), indent=2))

    plan = choose_shared_plan(backend, args.phase_bits)
    print("Shared-work plan:")
    print(json.dumps(plan, indent=2, default=str))

    recycled = build_recycled(args.phase_bits, use_measure2)
    wide = build_wide(args.phase_bits)
    compiled_recycled = compile_with_layout(
        recycled, backend, args.optimization_level, plan["recycled_initial_layout"]
    )
    compiled_wide = compile_with_layout(
        wide, backend, args.optimization_level, plan["wide_initial_layout"]
    )
    compiled = [compiled_recycled, compiled_wide]
    kinds = ["recycled", "wide"]
    transpiled_stats = [
        stats(recycled, compiled_recycled, "recycled", plan["recycled_initial_layout"]),
        stats(wide, compiled_wide, "wide", plan["wide_initial_layout"]),
    ]
    print("Transpiled stats:")
    print(json.dumps(transpiled_stats, indent=2, default=str))

    out_base = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend.name,
        "N": N,
        "a": A,
        "true_order_for_validation_only": TRUE_ORDER_FOR_VALIDATION_ONLY,
        "phase_bits": args.phase_bits,
        "shots": args.shots,
        "same_job": True,
        "same_initial_work_register": True,
        "compiled_orbit_encoding": dict(enumerate(ORBIT)),
        "compiled_orbit_self_test": self_test,
        "ideal_reference": ideal_metrics(args.phase_bits),
        "shared_layout_plan": plan,
        "transpiled_stats": transpiled_stats,
        "account_usage_before": before,
        "scope_note": (
            "This is an exact compiled 12-state orbit encoding for N=35,a=2, not a "
            "generic 6-qubit modular multiplier. Same initial physical work sites are "
            "requested for both architectures; transpilation may route states later."
        ),
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.transpile_only:
        path = args.outdir / f"ibm_shor35_matched_transpile_{args.phase_bits}b.json"
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
            "analysis": analyze_counts(counts, args.phase_bits),
            "distribution": distribution_metrics(counts, args.phase_bits),
        })

    out = {
        **out_base,
        "job_id": job.job_id(),
        "metrics": ibm_base.safe_metrics(job),
        "results": results,
        "paired_comparison": comparison(results, args.phase_bits),
        "account_usage_after": ibm_base.safe_usage(service),
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = args.outdir / f"ibm_shor35_matched_{args.phase_bits}b_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nRESULT")
    print(json.dumps(out, indent=2, default=str))
    print("\nSaved:", path.resolve())
    print("PAIRED:", json.dumps(out["paired_comparison"], sort_keys=True))


if __name__ == "__main__":
    main()
