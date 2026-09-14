#!/usr/bin/env python3
"""Generic reversible modular-arithmetic core for Shor order finding.

This module deliberately does *not* use the multiplicative order or a compiled
orbit encoding when constructing the quantum circuit.  For a supplied modulus
N and coprime base a it builds controlled multiplication by

    y -> a*y mod N,   for 0 <= y < N,
    y -> y,           for y >= N,

using reversible modular addition over the full n=ceil(log2(N)) residue
register.  The construction is intended as the bridge between the project's
small orbit-compiled demonstrations and a general arithmetic implementation of
Shor order finding.

Arithmetic construction
-----------------------
A clean modular constant adder for valid residues x < N uses one flag:

  flag ^= [x >= N-k]
  x += k                 (mod 2^n)
  if flag: x -= N        (mod 2^n)
  flag ^= [x < k]

The last comparison uncomputes the flag because, after x -> (x+k) mod N,
the wrap flag is exactly [result < k].  Addition modulo 2^n is represented by
Qiskit's ModularAdderGate and comparisons by IntegerComparatorGate.  These are
high-level arithmetic operations which Qiskit's HLS stage can lower using
polynomial ripple-carry/two's-complement methods when clean ancillas are
available.

Controlled constant multiplication uses a compute/swap/uncompute construction:

  acc <- a*y mod N
  swap(work, acc)
  acc <- acc - a^{-1}*work mod N

which returns the accumulator to |0>.  A separate validity flag guarantees
that basis states y >= N are left unchanged, so the full work-register action
is a permutation rather than only a valid-subspace map.

The phase-register layer can then be either conventional wide QPE or iterative
QPE with one measured/reset/recycled phase qubit.

This is general reversible arithmetic for small N, not an efficient
fault-tolerant implementation.  The present design intentionally favors clear
semantics, clean ancillas, exhaustive classical validation, and direct Qiskit
HLS compatibility over asymptotically optimized constant-addition circuits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Sequence

from qiskit import AncillaRegister, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import IntegerComparatorGate, ModularAdderGate, QFTGate, SwapGate


@dataclass(frozen=True)
class ArithmeticResources:
    modulus: int
    base: int
    work_bits: int
    phase_bits: int
    accumulator_qubits: int
    constant_qubits: int
    modular_flag_qubits: int
    validity_flag_qubits: int
    hls_scratch_qubits: int
    arithmetic_qubits_excluding_phase: int
    recycled_logical_qubits: int
    wide_logical_qubits: int


def work_bits_for_modulus(n: int) -> int:
    if n < 3:
        raise ValueError("N must be >= 3")
    return n.bit_length()


def validate_problem(n: int, a: int) -> None:
    if n < 3:
        raise ValueError("N must be >= 3")
    if not (1 < a < n):
        raise ValueError("base a must satisfy 1 < a < N")
    if math.gcd(a, n) != 1:
        raise ValueError("base a must be coprime to N for reversible multiplication")


def arithmetic_resources(n: int, a: int, phase_bits: int) -> ArithmeticResources:
    validate_problem(n, a)
    if phase_bits < 1:
        raise ValueError("phase_bits must be >= 1")
    w = work_bits_for_modulus(n)
    # Dedicated idle scratch qubits allow Qiskit's default HLS to choose the
    # O(n) two's-complement comparator instead of the no-ancilla exponential
    # comparator when the transpiler can prove the qubits are clean.
    scratch = max(0, w - 1)
    arithmetic = w + w + w + 1 + 1 + scratch
    return ArithmeticResources(
        modulus=n,
        base=a,
        work_bits=w,
        phase_bits=phase_bits,
        accumulator_qubits=w,
        constant_qubits=w,
        modular_flag_qubits=1,
        validity_flag_qubits=1,
        hls_scratch_qubits=scratch,
        arithmetic_qubits_excluding_phase=arithmetic,
        recycled_logical_qubits=arithmetic + 1,
        wide_logical_qubits=arithmetic + phase_bits,
    )


def _controlled(operation, control_count: int):
    if control_count == 0:
        return operation
    # Qiskit >=2.3 recommends annotated controls so HLS can lower the inner
    # arithmetic operation before/while handling the control modifier.
    return operation.control(control_count, annotated=True)


def _toggle_constant(qc: QuantumCircuit, reg: Sequence, value: int) -> None:
    for i, q in enumerate(reg):
        if (value >> i) & 1:
            qc.x(q)


def append_compare(
    qc: QuantumCircuit,
    controls: Sequence,
    state: Sequence,
    flag,
    value: int,
    *,
    geq: bool,
) -> None:
    gate = IntegerComparatorGate(len(state), int(value), geq=geq)
    op = _controlled(gate, len(controls))
    qc.append(op, list(controls) + list(state) + [flag])


def append_mod2n_add(
    qc: QuantumCircuit,
    controls: Sequence,
    addend: Sequence,
    target: Sequence,
) -> None:
    if len(addend) != len(target):
        raise ValueError("addend and target registers must have equal width")
    gate = ModularAdderGate(len(target))
    op = _controlled(gate, len(controls))
    qc.append(op, list(controls) + list(addend) + list(target))


def append_controlled_modadd_constant(
    qc: QuantumCircuit,
    *,
    target: Sequence,
    constant: Sequence,
    flag,
    controls: Sequence,
    addend: int,
    modulus: int,
) -> None:
    """Apply target <- target + addend (mod modulus) when all controls are 1.

    Preconditions on active branches: 0 <= target < modulus.  The flag and
    constant registers must enter in |0> and are returned to |0>.
    """
    width = len(target)
    if len(constant) != width:
        raise ValueError("constant register width mismatch")
    if modulus >= (1 << width):
        raise ValueError("target register too small for modulus")

    k = int(addend) % modulus
    if k == 0:
        return

    # On a valid input x<N, wrap occurs exactly when x >= N-k.
    append_compare(qc, controls, target, flag, modulus - k, geq=True)

    _toggle_constant(qc, constant, k)
    append_mod2n_add(qc, controls, constant, target)
    _toggle_constant(qc, constant, k)

    # The flag already implies that every external control was active, so the
    # conditional subtraction only needs the flag itself as a control.
    minus_modulus = (-modulus) % (1 << width)
    _toggle_constant(qc, constant, minus_modulus)
    append_mod2n_add(qc, [flag], constant, target)
    _toggle_constant(qc, constant, minus_modulus)

    # After modular addition, wrap == [result < k].  Recomputing that predicate
    # XORs the flag back to zero without retaining garbage.
    append_compare(qc, controls, target, flag, k, geq=False)


def _controlled_swap(qc: QuantumCircuit, controls: Sequence, a, b) -> None:
    if not controls:
        qc.swap(a, b)
        return
    op = _controlled(SwapGate(), len(controls))
    qc.append(op, list(controls) + [a, b])


def append_controlled_modmul_constant(
    qc: QuantumCircuit,
    *,
    control,
    work: Sequence,
    accumulator: Sequence,
    constant: Sequence,
    mod_flag,
    valid_flag,
    multiplier: int,
    modulus: int,
) -> None:
    """Apply controlled in-place multiplication by a classical constant mod N.

    For work basis values below N this applies y -> multiplier*y mod N when the
    external control is 1.  Values y>=N are explicitly left unchanged.  All
    arithmetic ancillas are returned to zero.
    """
    width = len(work)
    if len(accumulator) != width or len(constant) != width:
        raise ValueError("work/accumulator/constant widths must match")
    m = int(multiplier) % modulus
    if math.gcd(m, modulus) != 1:
        raise ValueError("multiplier must be invertible modulo N")

    # valid_flag <- [work < N].  The predicate is preserved by multiplication
    # on valid residues and invalid states are otherwise untouched, so the same
    # comparator cleanly uncomputes the flag at the end.
    append_compare(qc, [], work, valid_flag, modulus, geq=False)

    # acc <- m * work mod N, active only for control=valid=1.
    for i, source_bit in enumerate(work):
        k = (m * (1 << i)) % modulus
        append_controlled_modadd_constant(
            qc,
            target=accumulator,
            constant=constant,
            flag=mod_flag,
            controls=[control, valid_flag, source_bit],
            addend=k,
            modulus=modulus,
        )

    # work <- m*work, accumulator <- old work.
    for wq, aq in zip(work, accumulator):
        _controlled_swap(qc, [control, valid_flag], wq, aq)

    # Clear accumulator using m^{-1} * new_work == old_work.
    m_inv = pow(m, -1, modulus)
    for i, source_bit in enumerate(work):
        k = (-(m_inv * (1 << i))) % modulus
        append_controlled_modadd_constant(
            qc,
            target=accumulator,
            constant=constant,
            flag=mod_flag,
            controls=[control, valid_flag, source_bit],
            addend=k,
            modulus=modulus,
        )

    append_compare(qc, [], work, valid_flag, modulus, geq=False)


def _make_arithmetic_registers(n: int):
    work = QuantumRegister(n, "work")
    acc = AncillaRegister(n, "acc")
    const = AncillaRegister(n, "const")
    mod_flag = AncillaRegister(1, "mod_flag")
    valid = AncillaRegister(1, "valid")
    scratch = AncillaRegister(max(0, n - 1), "hls_scratch")
    return work, acc, const, mod_flag, valid, scratch


def initialize_work_one(qc: QuantumCircuit, work: Sequence) -> None:
    qc.x(work[0])


def build_wide_order_finder(n: int, a: int, phase_bits: int) -> QuantumCircuit:
    validate_problem(n, a)
    width = work_bits_for_modulus(n)
    phase_q = QuantumRegister(phase_bits, "phase_q")
    work, acc, const, mod_flag, valid, scratch = _make_arithmetic_registers(width)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(
        phase_q, work, acc, const, mod_flag, valid, scratch, phase,
        name=f"shor_generic_wide_N{n}_a{a}_{phase_bits}b",
    )
    initialize_work_one(qc, work)

    for k in range(phase_bits):
        qc.h(phase_q[k])
        multiplier = pow(a, 1 << k, n)
        append_controlled_modmul_constant(
            qc,
            control=phase_q[k],
            work=list(work),
            accumulator=list(acc),
            constant=list(const),
            mod_flag=mod_flag[0],
            valid_flag=valid[0],
            multiplier=multiplier,
            modulus=n,
        )

    qc.append(QFTGate(phase_bits).inverse(), list(phase_q))
    qc.measure(list(phase_q), list(phase))
    return qc


def build_recycled_order_finder(
    n: int,
    a: int,
    phase_bits: int,
    *,
    mid_measure: Callable[[QuantumCircuit, object, object], None] | None = None,
) -> QuantumCircuit:
    validate_problem(n, a)
    width = work_bits_for_modulus(n)
    phase_q = QuantumRegister(1, "phase_q")
    work, acc, const, mod_flag, valid, scratch = _make_arithmetic_registers(width)
    phase = ClassicalRegister(phase_bits, "phase")
    qc = QuantumCircuit(
        phase_q, work, acc, const, mod_flag, valid, scratch, phase,
        name=f"shor_generic_recycled_N{n}_a{a}_{phase_bits}b",
    )
    anc = phase_q[0]
    initialize_work_one(qc, work)

    for k in range(phase_bits - 1, -1, -1):
        dest = phase_bits - 1 - k
        qc.reset(anc)
        qc.h(anc)
        multiplier = pow(a, 1 << k, n)
        append_controlled_modmul_constant(
            qc,
            control=anc,
            work=list(work),
            accumulator=list(acc),
            constant=list(const),
            mod_flag=mod_flag[0],
            valid_flag=valid[0],
            multiplier=multiplier,
            modulus=n,
        )
        for j in range(k + 1, phase_bits):
            prior_c = phase_bits - 1 - j
            angle = -2.0 * math.pi / (2 ** (j - k + 1))
            with qc.if_test((phase[prior_c], 1)):
                qc.p(angle, anc)
        qc.h(anc)
        if mid_measure is None:
            qc.measure(anc, phase[dest])
        else:
            mid_measure(qc, anc, phase[dest])
    return qc


def _classical_modadd(x: int, k: int, modulus: int, width: int, active: bool) -> tuple[int, int]:
    """Mirror the reversible modular-adder logic for exhaustive self-tests."""
    flag = 0
    k %= modulus
    if not active or k == 0:
        return x, flag
    if x >= modulus:
        raise ValueError("_classical_modadd expects a valid residue")
    if x >= modulus - k:
        flag ^= 1
    x = (x + k) % (1 << width)
    if flag:
        x = (x - modulus) % (1 << width)
    if x < k:
        flag ^= 1
    return x, flag


def _classical_controlled_modmul(y: int, multiplier: int, modulus: int, width: int, control: bool) -> tuple[int, int]:
    if not control or y >= modulus:
        return y, 0
    acc = 0
    for i in range(width):
        if (y >> i) & 1:
            acc, flag = _classical_modadd(acc, multiplier * (1 << i), modulus, width, True)
            if flag:
                raise AssertionError("mod-add flag did not clean")
    y, acc = acc, y
    inv = pow(multiplier, -1, modulus)
    for i in range(width):
        if (y >> i) & 1:
            acc, flag = _classical_modadd(acc, -(inv * (1 << i)), modulus, width, True)
            if flag:
                raise AssertionError("mod-add flag did not clean")
    return y, acc


def semantic_self_test(n: int, a: int, phase_bits: int) -> dict:
    validate_problem(n, a)
    width = work_bits_for_modulus(n)
    full_width = 1 << width

    modadd_cases = 0
    for k in range(1, n):
        for x in range(n):
            got, flag = _classical_modadd(x, k, n, width, True)
            if got != (x + k) % n or flag != 0:
                raise AssertionError(
                    f"modadd failed N={n} x={x} k={k}: got={got}, flag={flag}"
                )
            modadd_cases += 1

    powers = []
    modmul_cases = 0
    for bit in range(phase_bits):
        multiplier = pow(a, 1 << bit, n)
        if math.gcd(multiplier, n) != 1:
            raise AssertionError("QPE multiplier unexpectedly non-invertible")
        for control in (False, True):
            for y in range(full_width):
                got, acc = _classical_controlled_modmul(y, multiplier, n, width, control)
                expected = (multiplier * y) % n if control and y < n else y
                if got != expected or acc != 0:
                    raise AssertionError(
                        "modmul failed "
                        f"bit={bit} m={multiplier} c={int(control)} y={y}: "
                        f"got={got}, acc={acc}, expected={expected}"
                    )
                modmul_cases += 1
        powers.append({"bit": bit, "multiplier": multiplier, "inverse": pow(multiplier, -1, n)})

    resources = arithmetic_resources(n, a, phase_bits)
    return {
        "pass": True,
        "N": n,
        "a": a,
        "work_bits": width,
        "phase_bits": phase_bits,
        "order_used_in_circuit_construction": False,
        "modadd_cases": modadd_cases,
        "controlled_modmul_cases": modmul_cases,
        "powers": powers,
        "resources": asdict(resources),
        "full_register_semantics": (
            "multiply modulo N for y<N; identity for y>=N; arithmetic ancillas clean"
        ),
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Build/test generic reversible modular arithmetic for Shor.")
    ap.add_argument("--N", type=int, default=35)
    ap.add_argument("--a", type=int, default=2)
    ap.add_argument("--phase-bits", type=int, default=8)
    ap.add_argument("--build", choices=["none", "recycled", "wide", "both"], default="none")
    args = ap.parse_args()

    report = semantic_self_test(args.N, args.a, args.phase_bits)
    print(json.dumps(report, indent=2))
    if args.build in ("recycled", "both"):
        c = build_recycled_order_finder(args.N, args.a, args.phase_bits)
        print("recycled:", {"qubits": c.num_qubits, "depth_high_level": c.depth(), "size_high_level": c.size()})
    if args.build in ("wide", "both"):
        c = build_wide_order_finder(args.N, args.a, args.phase_bits)
        print("wide:", {"qubits": c.num_qubits, "depth_high_level": c.depth(), "size_high_level": c.size()})
