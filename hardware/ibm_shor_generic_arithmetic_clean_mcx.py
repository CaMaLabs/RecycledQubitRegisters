#!/usr/bin/env python3
"""Generic reversible modular arithmetic using explicit clean-ancilla MCX chains.

This is a synthesis variant of ``ibm_shor_generic_arithmetic.py``.  It keeps the
same order-agnostic Shor semantics, but replaces Qiskit's no-ancilla MCX
lowering with an explicit linear Toffoli chain using reusable clean ancillas.

For k controls (k >= 2), the MCX construction uses k-2 clean ancillas and
2k-3 Toffolis.  The scratch register is reused by every MCX and is returned to
|0> after each call.

Circuit construction uses only N, a and the requested phase precision.  The
multiplicative order and a compiled modular orbit are not inputs to synthesis.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import QFTGate
from qiskit.transpiler import generate_preset_pass_manager

import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-direct-clean-mcx-v1"


def max_mcx_controls(acc_bits: int) -> int:
    # The largest carry MCX appears inside the conditional +N restoration:
    # external [phase, source, flag] controls plus up to acc_bits-1 lower bits.
    return 3 + max(0, acc_bits - 1)


def scratch_qubits_for_accumulator(acc_bits: int) -> int:
    return max(0, max_mcx_controls(acc_bits) - 2)


def append_mcx_clean(qc: QuantumCircuit, controls, target, scratch) -> None:
    """Append a positive-control X using reusable clean ancillas.

    Scratch qubits must enter in |0>.  They are restored to |0> exactly.
    """
    controls = list(controls)
    scratch = list(scratch)
    k = len(controls)
    if k == 0:
        qc.x(target)
        return
    if k == 1:
        qc.cx(controls[0], target)
        return
    if k == 2:
        qc.ccx(controls[0], controls[1], target)
        return
    needed = k - 2
    if len(scratch) < needed:
        raise ValueError(f"MCX with {k} controls needs {needed} clean scratch qubits")

    a = scratch[:needed]
    qc.ccx(controls[0], controls[1], a[0])
    for i in range(2, k - 1):
        qc.ccx(a[i - 2], controls[i], a[i - 1])
    qc.ccx(a[k - 3], controls[k - 1], target)
    for i in range(k - 2, 1, -1):
        qc.ccx(a[i - 2], controls[i], a[i - 1])
    qc.ccx(controls[0], controls[1], a[0])


def add_constant_mod_2m(qc, register, constant: int, controls=(), scratch=()) -> None:
    reg = list(register)
    controls = list(controls)
    m = len(reg)
    constant %= 1 << m
    for k in range(m):
        if not ((constant >> k) & 1):
            continue
        for i in range(m - 1, k, -1):
            append_mcx_clean(qc, controls + reg[k:i], reg[i], scratch)
        append_mcx_clean(qc, controls, reg[k], scratch)


def add_constant_mod_n(
    qc,
    accumulator,
    flag,
    constant: int,
    modulus_n: int,
    controls=(),
    scratch=(),
) -> None:
    acc = list(accumulator)
    controls = list(controls)
    n = (modulus_n - 1).bit_length()
    if len(acc) != n + 1:
        raise ValueError(f"Accumulator must have n+1={n + 1} bits for N={modulus_n}")
    a = constant % modulus_n
    if a == 0:
        return

    add_constant_mod_2m(qc, acc, a, controls, scratch)
    add_constant_mod_2m(qc, acc, -modulus_n, controls, scratch)
    append_mcx_clean(qc, controls + [acc[-1]], flag, scratch)
    add_constant_mod_2m(qc, acc, modulus_n, controls + [flag], scratch)
    add_constant_mod_2m(qc, acc, -a, controls, scratch)
    append_mcx_clean(qc, controls, flag, scratch)
    append_mcx_clean(qc, controls + [acc[-1]], flag, scratch)
    add_constant_mod_2m(qc, acc, a, controls, scratch)


def apply_controlled_modmul(
    qc,
    control,
    work,
    accumulator,
    flag,
    scratch,
    multiplier: int,
    modulus_n: int,
) -> None:
    work = list(work)
    acc = list(accumulator)
    c = multiplier % modulus_n
    if math.gcd(c, modulus_n) != 1:
        raise ValueError(f"multiplier {c} is not invertible modulo N={modulus_n}")

    for i, source_bit in enumerate(work):
        term = (c * (1 << i)) % modulus_n
        add_constant_mod_n(
            qc, acc, flag, term, modulus_n,
            controls=[control, source_bit], scratch=scratch,
        )

    for i in range(len(work)):
        qc.cswap(control, work[i], acc[i])

    c_inv = pow(c, -1, modulus_n)
    for i, source_bit in enumerate(work):
        term = (c_inv * (1 << i)) % modulus_n
        add_constant_mod_n(
            qc, acc, flag, -term, modulus_n,
            controls=[control, source_bit], scratch=scratch,
        )


def round_multiplier(a: int, n: int, k: int) -> int:
    return pow(a, 1 << k, n)


def initialize_work_one(qc, work) -> None:
    qc.x(list(work)[0])


def make_registers(phase_qubits: int, n: int):
    work_bits = (n - 1).bit_length()
    acc_bits = work_bits + 1
    scratch_bits = scratch_qubits_for_accumulator(acc_bits)
    phase_q = QuantumRegister(phase_qubits, "phase_q")
    work = QuantumRegister(work_bits, "work")
    acc = QuantumRegister(acc_bits, "acc")
    flag = QuantumRegister(1, "flag")
    scratch = QuantumRegister(scratch_bits, "scratch")
    return phase_q, work, acc, flag, scratch


def build_recycled(n: int, a: int, phase_bits: int, use_measure2: bool) -> QuantumCircuit:
    phase_q, work, acc, flag, scratch = make_registers(1, n)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work, acc, flag, scratch, phase,
                        name=f"shor_generic_cleanmcx_recycled_N{n}_{phase_bits}b")
    anc = phase_q[0]
    initialize_work_one(qc, work)

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        apply_controlled_modmul(
            qc, anc, list(work), list(acc), flag[0], list(scratch),
            round_multiplier(a, n, k), n,
        )
        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)
        qc.h(anc)
        ref.ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)
    return qc


def build_wide(n: int, a: int, phase_bits: int) -> QuantumCircuit:
    phase_q, work, acc, flag, scratch = make_registers(phase_bits, n)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work, acc, flag, scratch, phase,
                        name=f"shor_generic_cleanmcx_wide_N{n}_{phase_bits}b")
    initialize_work_one(qc, work)

    for k in range(phase_bits):
        qc.h(phase_q[k])
        apply_controlled_modmul(
            qc, phase_q[k], list(work), list(acc), flag[0], list(scratch),
            round_multiplier(a, n, k), n,
        )
    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc


def _simulate_clean_mcx(controls, target_value: int) -> tuple[int, list[int]]:
    k = len(controls)
    if k == 0:
        return target_value ^ 1, []
    if k == 1:
        return target_value ^ controls[0], []
    if k == 2:
        return target_value ^ (controls[0] & controls[1]), []
    a = [0] * (k - 2)
    a[0] ^= controls[0] & controls[1]
    for i in range(2, k - 1):
        a[i - 1] ^= a[i - 2] & controls[i]
    target_value ^= a[k - 3] & controls[k - 1]
    for i in range(k - 2, 1, -1):
        a[i - 1] ^= a[i - 2] & controls[i]
    a[0] ^= controls[0] & controls[1]
    return target_value, a


def validate_clean_mcx(max_controls: int) -> dict:
    checked = 0
    for k in range(max_controls + 1):
        for pattern in range(1 << k):
            controls = [(pattern >> i) & 1 for i in range(k)]
            expected = int(all(controls)) if k else 1
            for target in (0, 1):
                got, scratch = _simulate_clean_mcx(controls, target)
                if got != (target ^ expected) or any(scratch):
                    return {"pass": False, "controls": k, "pattern": pattern, "target": target}
                checked += 1
    return {"pass": True, "checked_cases": checked, "max_controls": max_controls}


def resource_model(n: int, phase_bits: int) -> dict:
    work_bits = (n - 1).bit_length()
    acc_bits = work_bits + 1
    scratch_bits = scratch_qubits_for_accumulator(acc_bits)
    arithmetic = work_bits + acc_bits + 1 + scratch_bits
    return {
        "work_bits": work_bits,
        "accumulator_bits": acc_bits,
        "flag_bits": 1,
        "clean_mcx_scratch_bits": scratch_bits,
        "arithmetic_qubits_excluding_phase": arithmetic,
        "recycled_logical_qubits": arithmetic + 1,
        "wide_logical_qubits": arithmetic + phase_bits,
        "max_mcx_controls": max_mcx_controls(acc_bits),
        "order_used_in_circuit_construction": False,
        "orbit_encoding_used": False,
    }


def circuit_stats(qc: QuantumCircuit) -> dict:
    return {
        "name": qc.name,
        "logical_qubits": qc.num_qubits,
        "classical_bits": qc.num_clbits,
        "depth_abstract": qc.depth(),
        "size_abstract": qc.size(),
        "ops_abstract": {str(k): int(v) for k, v in qc.count_ops().items()},
    }


def compiled_stats(original, compiled) -> dict:
    ops = compiled.count_ops()
    return {
        "name": original.name,
        "logical_qubits": original.num_qubits,
        "compiled_qubits": compiled.num_qubits,
        "depth": compiled.depth(),
        "size": compiled.size(),
        "cz": int(ops.get("cz", 0)),
        "measure": int(ops.get("measure", 0)),
        "measure_2": int(ops.get("measure_2", 0)),
        "reset": int(ops.get("reset", 0)),
        "if_else": int(ops.get("if_else", 0)),
        "ops": {str(k): int(v) for k, v in ops.items()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Clean-ancilla linear-MCX generic Shor preflight; no QPU jobs.")
    ap.add_argument("--N", type=int, default=35)
    ap.add_argument("--a", type=int, default=2)
    ap.add_argument("--phase-bits", type=int, default=1)
    ap.add_argument("--backend", default=None)
    ap.add_argument("--optimization-level", type=int, choices=[0,1,2,3], default=1)
    ap.add_argument("--kind", choices=["recycled","wide","both"], default="both")
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor_generic_arithmetic"))
    args = ap.parse_args()

    if math.gcd(args.a, args.N) != 1:
        raise SystemExit("a must be coprime to N")
    resources = resource_model(args.N, args.phase_bits)
    mcx_test = validate_clean_mcx(resources["max_mcx_controls"])
    print("Clean-MCX self-test:", "PASS" if mcx_test["pass"] else "FAIL")
    print(json.dumps(mcx_test, indent=2))
    if not mcx_test["pass"]:
        raise SystemExit("clean MCX validation failed")

    # Reuse the already-validated arithmetic semantics from the baseline module.
    import ibm_shor_generic_arithmetic as baseline
    semantic = baseline.exhaustive_self_test(args.N, args.a, max(1, args.phase_bits))
    print("Generic arithmetic semantic self-test:", "PASS" if semantic["pass"] else "FAIL")
    if not semantic["pass"]:
        raise SystemExit("baseline arithmetic semantics failed")
    print(json.dumps(resources, indent=2))

    backend = None
    use_measure2 = False
    if args.backend:
        service = ref.ibm_base.make_service()
        required = resources["wide_logical_qubits"] if args.kind in ("wide","both") else resources["recycled_logical_qubits"]
        backend = ref.ibm_base.select_backend(service, required, args.backend)
        use_measure2 = ref.ibm_base.backend_has_measure2(backend)
        print(f"backend={backend.name} measure_2={use_measure2}")

    circuits = []
    if args.kind in ("recycled","both"):
        circuits.append(("recycled", build_recycled(args.N, args.a, args.phase_bits, use_measure2)))
    if args.kind in ("wide","both"):
        circuits.append(("wide", build_wide(args.N, args.a, args.phase_bits)))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "N": args.N,
        "a": args.a,
        "phase_bits": args.phase_bits,
        "qpu_submitted": False,
        "construction": "generic_reversible_modular_arithmetic_explicit_clean_ancilla_linear_mcx",
        "mcx_self_test": mcx_test,
        "semantic_self_test": semantic,
        "resources": resources,
        "abstract_stats": {},
        "compiled_stats": {},
    }

    for kind, qc in circuits:
        print(f"\n=== {kind} abstract ===")
        ast = circuit_stats(qc)
        out["abstract_stats"][kind] = ast
        print(json.dumps(ast, indent=2))
        if backend is not None:
            pm = generate_preset_pass_manager(
                backend=backend,
                optimization_level=args.optimization_level,
                seed_transpiler=8776,
            )
            import time
            t0 = time.perf_counter()
            compiled = pm.run(qc)
            elapsed = time.perf_counter() - t0
            row = compiled_stats(qc, compiled)
            row["compile_seconds"] = elapsed
            out["compiled_stats"][kind] = row
            print(f"=== {kind} compiled ===")
            print(json.dumps(row, indent=2))

    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "local" if backend is None else backend.name
    path = args.outdir / f"generic_cleanmcx_N{args.N}_a{args.a}_{args.phase_bits}b_{suffix}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("\nNO QPU JOB SUBMITTED.")
    print("Saved:", path.resolve())


if __name__ == "__main__":
    main()
