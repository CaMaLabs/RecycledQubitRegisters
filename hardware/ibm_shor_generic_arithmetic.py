#!/usr/bin/env python3
"""Generic reversible modular-arithmetic Shor/QPE preflight.

This is the bridge from the orbit-compiled N=35 experiments to a substantially
more general Shor implementation.  The circuit constructor uses only N, a, and
the requested phase precision.  It does NOT use the multiplicative order when
building the quantum circuit.

The modular work unitary is synthesized from reversible arithmetic:

    |y>|0> -> |y>|c*y mod N>

followed by a controlled swap and reversible uncomputation with c^{-1} mod N.
Each modular product is built from controlled constant modular additions.  The
constant-adder primitive is an exact reversible increment network on an n+1 bit
accumulator; modular reduction uses a clean flag qubit.

The implementation is deliberately conservative and auditable rather than
claimed to be asymptotically optimal.  It is generic in N and a (subject to
coprimality and available hardware), and it never hard-codes an orbit or order.

V1 is PRE-FLIGHT ONLY: it performs exhaustive classical network self-tests,
builds wide/recycled QPE circuits, and optionally transpiles them for an IBM
backend.  It never submits a QPU job.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import MCXGate, QFTGate
from qiskit.transpiler import generate_preset_pass_manager

import ibm_shor35_matched as ref

SCRIPT_REVISION = "2026-09-14-generic-modarith-v1"


def append_mcx(qc: QuantumCircuit, controls, target) -> None:
    """Append X with zero or more positive controls."""
    controls = list(controls)
    if not controls:
        qc.x(target)
    elif len(controls) == 1:
        qc.cx(controls[0], target)
    elif len(controls) == 2:
        qc.ccx(controls[0], controls[1], target)
    else:
        qc.append(MCXGate(len(controls)), controls + [target])


def add_constant_mod_2m(qc: QuantumCircuit, register, constant: int, controls=()) -> None:
    """Add a classical constant modulo 2**m to a little-endian register.

    A +2**k increment is implemented from high bit to low bit.  Adding all set
    powers of two gives an exact constant adder.  External controls are added to
    every X/MCX, so the whole operation is coherently controllable.
    """
    reg = list(register)
    controls = list(controls)
    m = len(reg)
    modulus = 1 << m
    constant %= modulus

    for k in range(m):
        if not ((constant >> k) & 1):
            continue
        for i in range(m - 1, k, -1):
            append_mcx(qc, controls + reg[k:i], reg[i])
        append_mcx(qc, controls, reg[k])


def add_constant_mod_n(
    qc: QuantumCircuit,
    accumulator,
    flag,
    constant: int,
    modulus_n: int,
    controls=(),
) -> None:
    """Add constant modulo N on the valid residue subspace 0 <= x < N.

    The accumulator has n+1 bits where n=ceil(log2(N)); its high bit therefore
    serves as the two's-complement sign bit during subtraction.  The flag is
    returned clean to |0>.  When the external controls are false the operation
    is exactly identity.
    """
    acc = list(accumulator)
    controls = list(controls)
    n = (modulus_n - 1).bit_length()
    if len(acc) != n + 1:
        raise ValueError(f"Accumulator must have n+1={n + 1} bits for N={modulus_n}")

    a = constant % modulus_n
    if a == 0:
        return

    # x <- x + a
    add_constant_mod_2m(qc, acc, a, controls)
    # x <- x + a - N.  If negative, the high bit is 1.
    add_constant_mod_2m(qc, acc, -modulus_n, controls)
    append_mcx(qc, controls + [acc[-1]], flag)

    # Restore N only on the underflow branch.
    add_constant_mod_2m(qc, acc, modulus_n, controls + [flag])

    # Uncompute the flag.  After subtracting a from the corrected result,
    # the sign bit is the logical NOT of the underflow flag on the valid domain.
    add_constant_mod_2m(qc, acc, -a, controls)
    append_mcx(qc, controls, flag)
    append_mcx(qc, controls + [acc[-1]], flag)
    add_constant_mod_2m(qc, acc, a, controls)


def apply_controlled_modmul(
    qc: QuantumCircuit,
    control,
    work,
    accumulator,
    flag,
    multiplier: int,
    modulus_n: int,
) -> None:
    """Controlled in-place multiplication |y> -> |c*y mod N> for y < N.

    The accumulator and flag must enter in |0> and are returned to |0>.  The
    unitary is constructed only from reversible modular additions, controlled
    swaps, and their inverse arithmetic.  No multiplicative order is used.
    """
    work = list(work)
    acc = list(accumulator)
    n = len(work)
    c = multiplier % modulus_n
    if math.gcd(c, modulus_n) != 1:
        raise ValueError(f"multiplier {c} is not invertible modulo N={modulus_n}")

    # Out-of-place product in acc: acc += c * y (mod N).
    for i, source_bit in enumerate(work):
        term = (c * (1 << i)) % modulus_n
        add_constant_mod_n(qc, acc, flag, term, modulus_n, controls=[control, source_bit])

    # Move the product into work only when the phase/control qubit is 1.
    for i in range(n):
        qc.cswap(control, work[i], acc[i])

    # Active branch now has work=c*y and acc=y.  Erase acc using c^{-1}*work.
    c_inv = pow(c, -1, modulus_n)
    for i, source_bit in enumerate(work):
        term = (c_inv * (1 << i)) % modulus_n
        add_constant_mod_n(qc, acc, flag, -term, modulus_n, controls=[control, source_bit])


def initialize_work_one(qc: QuantumCircuit, work) -> None:
    qc.x(list(work)[0])


def round_multiplier(a: int, n: int, k: int) -> int:
    """Classically precompute a^(2^k) mod N; standard Shor compilation."""
    return pow(a, 1 << k, n)


def build_recycled(n: int, a: int, phase_bits: int, use_measure2: bool) -> QuantumCircuit:
    work_bits = (n - 1).bit_length()
    acc_bits = work_bits + 1
    q = QuantumRegister(1 + work_bits + acc_bits + 1, "q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(q, phase, name=f"shor_generic_recycled_N{n}_{phase_bits}b")

    anc = q[0]
    work = list(q[1 : 1 + work_bits])
    acc_start = 1 + work_bits
    acc = list(q[acc_start : acc_start + acc_bits])
    flag = q[-1]
    initialize_work_one(qc, work)

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        apply_controlled_modmul(qc, anc, work, acc, flag, round_multiplier(a, n, k), n)

        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)

        qc.h(anc)
        ref.ibm_base.mid_measure(qc, anc, phase[dest], use_measure2)
    return qc


def build_wide(n: int, a: int, phase_bits: int) -> QuantumCircuit:
    work_bits = (n - 1).bit_length()
    acc_bits = work_bits + 1
    phase_q = QuantumRegister(phase_bits, "phase_q")
    work_q = QuantumRegister(work_bits, "work_q")
    acc_q = QuantumRegister(acc_bits, "acc_q")
    flag_q = QuantumRegister(1, "flag_q")
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(phase_q, work_q, acc_q, flag_q, phase, name=f"shor_generic_wide_N{n}_{phase_bits}b")
    initialize_work_one(qc, work_q)

    for k in range(phase_bits):
        qc.h(phase_q[k])
        apply_controlled_modmul(
            qc,
            phase_q[k],
            list(work_q),
            list(acc_q),
            flag_q[0],
            round_multiplier(a, n, k),
            n,
        )

    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc


def _classical_add_mod_2m_network(x: int, m: int, constant: int, active: bool = True) -> int:
    bits = [(x >> i) & 1 for i in range(m)]
    c = constant % (1 << m)
    for k in range(m):
        if not ((c >> k) & 1):
            continue
        for i in range(m - 1, k, -1):
            if active and all(bits[j] for j in range(k, i)):
                bits[i] ^= 1
        if active:
            bits[k] ^= 1
    return sum(bit << i for i, bit in enumerate(bits))


def _classical_mod_add_network(x: int, constant: int, n: int, active: bool = True) -> tuple[int, int]:
    bits = (n - 1).bit_length()
    m = bits + 1
    M = 1 << m
    flag = 0
    a = constant % n
    if not active or a == 0:
        return x, flag

    x = (x + a) % M
    x = (x - n) % M
    if (x >> (m - 1)) & 1:
        flag ^= 1
    if flag:
        x = (x + n) % M
    x = (x - a) % M
    flag ^= 1
    if (x >> (m - 1)) & 1:
        flag ^= 1
    x = (x + a) % M
    return x, flag


def _classical_modmul_network(y: int, c: int, n: int, active: bool = True) -> tuple[int, int, int]:
    """High-level mirror of the reversible multiply/uncompute construction."""
    if not active:
        return y, 0, 0
    work_bits = (n - 1).bit_length()
    acc = 0
    flag = 0
    for i in range(work_bits):
        if (y >> i) & 1:
            acc, flag = _classical_mod_add_network(acc, c * (1 << i), n, True)
            if flag:
                return -1, acc, flag
    work, acc = acc, y
    inv = pow(c, -1, n)
    for i in range(work_bits):
        if (work >> i) & 1:
            acc, flag = _classical_mod_add_network(acc, -(inv * (1 << i)), n, True)
            if flag:
                return -1, acc, flag
    return work, acc, flag


def multiplicative_order(a: int, n: int) -> int:
    """Classical validation helper.  Never used by the circuit constructor."""
    if math.gcd(a, n) != 1:
        raise ValueError("multiplicative order requires gcd(a, N)=1")
    x = 1
    for r in range(1, n + 1):
        x = (x * a) % n
        if x == 1:
            return r
    raise RuntimeError("order not found within N steps")


def exhaustive_self_test(n: int, a: int, phase_bits: int) -> dict:
    work_bits = (n - 1).bit_length()
    m = work_bits + 1
    add2m_ok = True
    add2m_failure = None
    for c in range(1 << m):
        for x in range(1 << m):
            got = _classical_add_mod_2m_network(x, m, c, True)
            want = (x + c) % (1 << m)
            if got != want:
                add2m_ok = False
                add2m_failure = {"x": x, "constant": c, "got": got, "want": want}
                break
        if not add2m_ok:
            break

    modadd_ok = True
    modadd_failure = None
    for c in range(n):
        for x in range(n):
            got, flag = _classical_mod_add_network(x, c, n, True)
            want = (x + c) % n
            if got != want or flag != 0:
                modadd_ok = False
                modadd_failure = {"x": x, "constant": c, "got": got, "want": want, "flag": flag}
                break
        if not modadd_ok:
            break

    multipliers = [round_multiplier(a, n, k) for k in range(phase_bits)]
    modmul_rows = []
    modmul_ok = True
    for k, c in enumerate(multipliers):
        row_ok = True
        failure = None
        if math.gcd(c, n) != 1:
            row_ok = False
            failure = {"reason": "noninvertible multiplier", "multiplier": c}
        else:
            for y in range(n):
                got, acc, flag = _classical_modmul_network(y, c, n, True)
                want = (c * y) % n
                inactive = _classical_modmul_network(y, c, n, False)
                if got != want or acc != 0 or flag != 0 or inactive != (y, 0, 0):
                    row_ok = False
                    failure = {
                        "y": y,
                        "got": got,
                        "want": want,
                        "acc": acc,
                        "flag": flag,
                        "inactive": inactive,
                    }
                    break
        modmul_rows.append({"k": k, "multiplier": c, "pass": row_ok, "failure": failure})
        modmul_ok &= row_ok

    order = multiplicative_order(a, n)
    return {
        "N": n,
        "a": a,
        "work_bits": work_bits,
        "accumulator_bits": m,
        "phase_bits": phase_bits,
        "validation_order_not_used_by_circuit": order,
        "round_multipliers": multipliers,
        "constant_adder_mod_2m": {"pass": add2m_ok, "failure": add2m_failure},
        "constant_modular_adder": {"pass": modadd_ok, "failure": modadd_failure},
        "controlled_modular_multipliers": {"pass": modmul_ok, "rounds": modmul_rows},
        "pass": add2m_ok and modadd_ok and modmul_ok,
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


def compiled_stats(original: QuantumCircuit, compiled: QuantumCircuit) -> dict:
    ops = compiled.count_ops()
    return {
        "name": original.name,
        "logical_qubits": original.num_qubits,
        "compiled_qubits": compiled.num_qubits,
        "depth": compiled.depth(),
        "size": compiled.size(),
        "cz": int(ops.get("cz", 0)),
        "cx": int(ops.get("cx", 0)),
        "ecr": int(ops.get("ecr", 0)),
        "measure": int(ops.get("measure", 0)),
        "measure_2": int(ops.get("measure_2", 0)),
        "reset": int(ops.get("reset", 0)),
        "if_else": int(ops.get("if_else", 0)),
        "ops": {str(k): int(v) for k, v in ops.items()},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Generic reversible modular-arithmetic Shor/QPE preflight; never submits QPU jobs.")
    ap.add_argument("--N", type=int, default=35)
    ap.add_argument("--a", type=int, default=2)
    ap.add_argument("--phase-bits", type=int, default=8)
    ap.add_argument("--backend", default=None, help="IBM backend for zero-QPU transpilation, e.g. ibm_fez")
    ap.add_argument("--optimization-level", type=int, choices=[0, 1, 2, 3], default=3)
    ap.add_argument("--kind", choices=["recycled", "wide", "both"], default="both")
    ap.add_argument("--self-test-only", action="store_true")
    ap.add_argument("--outdir", type=Path, default=Path("results/ibm_shor_generic_arithmetic"))
    args = ap.parse_args()

    if args.N < 3:
        raise SystemExit("N must be >= 3")
    if args.N % 2 == 0:
        raise SystemExit(f"N={args.N} is even; classical precheck already gives factor 2")
    g = math.gcd(args.a, args.N)
    if g != 1:
        raise SystemExit(f"gcd(a,N)={g}; Shor classical precheck already found a factor")
    if not (1 < args.a < args.N):
        raise SystemExit("Require 1 < a < N")
    if args.phase_bits < 2:
        raise SystemExit("Use at least 2 phase bits")

    test = exhaustive_self_test(args.N, args.a, args.phase_bits)
    print("Generic arithmetic self-test:", "PASS" if test["pass"] else "FAIL")
    print(json.dumps(test, indent=2))
    if not test["pass"]:
        raise SystemExit("Generic arithmetic self-test failed")

    if args.self_test_only:
        return

    # Building the circuits uses only N, a, and phase_bits.  The validation order
    # above is not passed to either constructor.
    use_measure2 = False
    backend = None
    service = None
    if args.backend:
        service = ref.ibm_base.make_service()
        needed = args.phase_bits + 2 * (args.N - 1).bit_length() + 2
        backend = ref.ibm_base.select_backend(service, needed, args.backend)
        use_measure2 = ref.ibm_base.backend_has_measure2(backend)

    circuits = []
    if args.kind in ("recycled", "both"):
        circuits.append(("recycled", build_recycled(args.N, args.a, args.phase_bits, use_measure2)))
    if args.kind in ("wide", "both"):
        circuits.append(("wide", build_wide(args.N, args.a, args.phase_bits)))

    abstract = {kind: circuit_stats(qc) for kind, qc in circuits}
    print("Abstract circuit stats:")
    print(json.dumps(abstract, indent=2))

    out = {
        "script_revision": SCRIPT_REVISION,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "N": args.N,
        "a": args.a,
        "phase_bits": args.phase_bits,
        "validation_order_not_used_by_circuit": test["validation_order_not_used_by_circuit"],
        "construction": "generic_reversible_constant_modular_addition_multiplier",
        "scope_note": (
            "Circuit construction uses N and a but not the multiplicative order or a precompiled modular orbit. "
            "The arithmetic is generic and reversible but intentionally not claimed to be asymptotically optimal."
        ),
        "self_test": test,
        "abstract_stats": abstract,
        "backend": None if backend is None else backend.name,
        "measure_2": use_measure2,
        "qpu_submitted": False,
    }

    if backend is not None:
        compiled_rows = {}
        for kind, qc in circuits:
            print(f"Transpiling {kind} for {backend.name} at optimization level {args.optimization_level}...")
            pm = generate_preset_pass_manager(
                backend=backend,
                optimization_level=args.optimization_level,
                seed_transpiler=8776,
            )
            compiled = pm.run(qc)
            compiled_rows[kind] = compiled_stats(qc, compiled)
            print(kind, json.dumps(compiled_rows[kind], indent=2))
        out["compiled_stats"] = compiled_rows
        if service is not None:
            out["account_usage"] = ref.ibm_base.safe_usage(service)

    args.outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "local" if backend is None else backend.name
    path = args.outdir / f"generic_modarith_N{args.N}_a{args.a}_{args.phase_bits}b_{suffix}_{stamp}.json"
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print("Saved:", path.resolve())
    print("No QPU job was submitted.")


if __name__ == "__main__":
    main()
