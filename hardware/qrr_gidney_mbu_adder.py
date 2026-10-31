#!/usr/bin/env python3
"""Pinned external Gidney adder adapter; no QPU, account, or network calls.

Upstream is not vendored. MX is destructive X measurement: this adapter adds
physical reset immediately after measurement so reused clean wires return |0>.
The sparse exact branch checks include relative phase, not just truth tables.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

UPSTREAM_COMMIT = "52618a2dac958af834519a4c88fb8c1ac0dfb9c6"
UPSTREAM_URL = "https://github.com/Strilanc/classical-quantum-adder"


def load_upstream(root):
    root = Path(root).resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if head != UPSTREAM_COMMIT:
        raise ValueError(f"Unpinned upstream commit: {head}")
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"],
                               cwd=root, text=True).strip():
        raise ValueError("Upstream checkout has modifications or untracked files")
    hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((root / "src/constadd").rglob("*.py"))}
    existing = sys.modules.get("constadd")
    if existing is not None and not Path(existing.__file__).resolve().is_relative_to(root):
        raise ValueError("A different constadd module is already loaded")
    sys.path.insert(0, str(root / "src"))
    return dict(url=UPSTREAM_URL, commit=head, source_sha256=hashes)


@lru_cache(maxsize=None)
def make_adder(n, value, controlled=True, variant="clean3"):
    from constadd.circuit import CircuitBuilder, Qubit
    from constadd._add_3_clean import circuit_to_iadd_using_3_clean_qubits
    from constadd._add_n_dirty_2_clean import circuit_to_iadd_using_linear_dirty_qubits_2_clean_qubits
    if n < 1 or variant not in ("clean3", "dirty2"):
        raise ValueError("Invalid adder specification")
    value = int(value) % (1 << n)
    target = Qubit("target").range(n)
    clean = Qubit("clean").range(3 if variant == "clean3" else 2)
    dirty = Qubit("dirty").range(max(0, n - 2)) if variant == "dirty2" else []
    control = [Qubit("control")] if controlled else []
    builder = CircuitBuilder()
    for register in (target, clean, dirty, control):
        builder.input(register)
    offset = [(control[0] if controlled else True) if value >> i & 1 else False
              for i in range(n)]
    if variant == "clean3":
        circuit = circuit_to_iadd_using_3_clean_qubits(
            Q_target=target, offset=offset, carry_in=False, Q_clean3=clean)
    else:
        circuit = circuit_to_iadd_using_linear_dirty_qubits_2_clean_qubits(
            Q_target=target, offset=offset, carry_in=False, Q_dirty=dirty, Q_clean2=clean)
    builder.ops.append(circuit)
    circuit = builder.to_circuit().with_resolved_anon()
    # Resolution changes anonymous measurement keys, not the named registers.
    return circuit, target, clean, dirty, control


def canonical_controls(controls):
    """RREF of affine equations p=1, preserving their AND exactly.

    Replacing row a by a XOR b XOR 1 while retaining b preserves a=b=1.
    This supplies distinct quantum pivots even when one public quantum control
    appears in multiple offset bits. Upstream pick_pivots rejects some of these.
    No extra quantum workspace is allocated.
    """
    rows = list(controls)
    qubits = sorted({q for row in rows for q in row.qubits})
    pivot = 0
    for q in qubits:
        hit = next((i for i in range(pivot, len(rows)) if q in rows[i].qubits), None)
        if hit is None:
            continue
        rows[pivot], rows[hit] = rows[hit], rows[pivot]
        for i in range(len(rows)):
            if i != pivot and q in rows[i].qubits:
                rows[i] = rows[i] ^ rows[pivot] ^ True
        pivot += 1
    return tuple(row for row in rows if row.fixed_value() is not True)


def lower_ops(circuit):
    from constadd.circuit import Op
    result = []
    for op in circuit.iter_flat_ops():
        if op.kind in ("X", "ZIF"):
            controls = canonical_controls(op.controls)
            if any(p.fixed_value() is False for p in controls):
                continue
            op = Op(op.kind, target=op.target, controls=controls)
            result.extend(op.iter_decomposed())
        else:
            result.append(op)
    return result


def encode_ops(ops, qubits, bits):
    qindex = {q: i for i, q in enumerate(qubits)}
    bindex = {b: i for i, b in enumerate(bits)}
    return [(op.kind, None if op.target is None else qindex[op.target],
             None if op.out is None else bindex[op.out],
             tuple((sum(1 << qindex[q] for q in p.qubits),
                    sum(1 << bindex[b] for b in p.bits), int(p.const)) for p in op.controls))
            for op in ops if op.kind not in ("INPUT", "BARRIER")]


def interpret_branch(encoded, state, transcript):
    """Exact signed computational path, normalized branch amplitude omitted.

    Destructive MX maps |z> to (-1)^(z*m)/sqrt(2), deletes that wire, then
    prepares |0>. Every allowed reset is checked to erase zero. If every input
    has the ideal output and the same sign for a fixed transcript, the Kraus
    operator is a scalar times the ideal isometry on arbitrary entangled input.
    """
    record = 0
    measurement = 0
    sign = 0
    for kind, target, out, controls in encoded:
        enabled = all(((state & qm).bit_count() ^ (record & bm).bit_count() ^ c) & 1
                      for qm, bm, c in controls)
        if kind == "X":
            if enabled:
                state ^= 1 << target
        elif kind == "ZIF":
            sign ^= enabled
        elif kind == "MX":
            m = (transcript >> measurement) & 1
            sign ^= ((state >> target) & 1) & m
            state &= ~(1 << target)
            record |= m << out
            measurement += 1
        elif kind == "RZ":
            if state >> target & 1:
                raise AssertionError("Reset would erase input-dependent quantum data")
        else:
            raise ValueError(kind)
    return state, int(sign), measurement


def exact_branch_proof(n, value, variant="clean3", controlled=True, omit_phase=False):
    circuit, target, clean, dirty, control = make_adder(n, value, controlled, variant)
    qubits = target + control + dirty + clean
    bits = sorted(circuit.all_bits())
    original = list(circuit.iter_flat_ops())
    if omit_phase:
        original = [op for op in original if op.kind != "ZIF"]
    lowered = lower_ops(circuit) if not omit_phase else original
    encoders = [encode_ops(ops, qubits, bits) for ops in (original, lowered)]
    measurements = sum(op.kind == "MX" for op in original)
    if measurements > 12:
        raise ValueError("Exhaustive measurement-branch limit exceeded")
    input_width = n + len(control) + len(dirty)
    paths = 0
    branch_global_signs = set()
    for transcript in range(1 << measurements):
        branch_sign = None
        for state in range(1 << input_width):
            enabled = (state >> n & 1) if controlled else 1
            expected = (state & ~((1 << n)-1)) | (((state & ((1 << n)-1)) +
                                                  enabled * value) % (1 << n))
            for encoded in encoders:
                final, sign, m = interpret_branch(encoded, state, transcript)
                assert final == expected, (n, value, variant, state, transcript, "output")
                assert m == measurements
                if branch_sign is None:
                    branch_sign = sign
                assert sign == branch_sign, (n, value, variant, state, transcript, "phase")
            paths += 1
        branch_global_signs.add(branch_sign)
    return dict(n=n, value=value, variant=variant, controlled=controlled,
                input_basis_states=1 << input_width, measurement_bits=measurements,
                transcripts=1 << measurements, input_transcript_paths=paths,
                original_and_lowered_streams_checked=True, clean_restored=True, dirty_restored=True,
                branch_relative_phase_exact=True, branch_global_signs=sorted(branch_global_signs))


def append_adder(qc, target, value, controls, clean, *, prefix="mbu"):
    """Emit the pinned 3-clean circuit into Qiskit, including reset and feedback."""
    from qiskit import ClassicalRegister
    from qiskit.circuit.classical import expr
    if len(controls) > 1 or len(clean) < 3:
        raise ValueError("Adapter requires zero or one control and three clean wires")
    value = int(value) % (1 << len(target))
    circuit, t, c, dirty, ctrl = make_adder(len(target), value, bool(controls))
    qmap = dict(zip(t + c + ctrl, list(target) + list(clean[:3]) + list(controls)))
    if len(set(qmap.values())) != len(qmap):
        raise ValueError("Target, control, and clean workspace must be disjoint")
    bits = sorted(circuit.all_bits())
    bmap = {}
    if bits:
        register = ClassicalRegister(len(bits), f"{prefix}_{len(qc.cregs)}")
        qc.add_register(register)
        bmap = dict(zip(bits, register))

    def emit(op):
        quantum = [qmap[q] for p in op.controls for q in p.qubits]
        classical = [bmap[b] for p in op.controls for b in p.bits]
        if any(p.fixed_value() is False for p in op.controls):
            return
        assert all(len(p.qubits) + len(p.bits) + int(p.const) <= 1 for p in op.controls)

        def gate():
            if op.kind == "X":
                dest = qmap[op.target]
                if not quantum:
                    qc.x(dest)
                elif len(quantum) == 1:
                    qc.cx(quantum[0], dest)
                elif len(quantum) == 2:
                    qc.ccx(*quantum, dest)
                else:
                    raise ValueError("Unexpected high-arity X")
            elif quantum:
                if len(quantum) == 1:
                    qc.z(quantum[0])
                elif len(quantum) == 2:
                    qc.cz(*quantum)
                elif len(quantum) == 3:
                    qc.ccz(*quantum)
                else:
                    raise ValueError("Unexpected high-arity phase")
            # A purely classical phase is global within an outcome branch.

        if not classical:
            gate()
        else:
            condition = expr.lift(classical[0])
            for bit in classical[1:]:
                condition = expr.logic_and(condition, bit)
            with qc.if_test(condition):
                gate()

    for op in lower_ops(circuit):
        if op.kind in ("X", "ZIF"):
            emit(op)
        elif op.kind == "MX":
            qc.h(qmap[op.target])
            qc.measure(qmap[op.target], bmap[op.out])
            qc.reset(qmap[op.target])
        elif op.kind == "RZ":
            # Upstream prepares a clean wire, initially or after destructive MX.
            # Both are already |0> in this adapter; MX emitted the reset above.
            pass
        elif op.kind not in ("INPUT", "BARRIER"):
            raise ValueError(op.kind)
    return len(bits)


def sparse_qiskit_branch(qc, amplitudes, transcript):
    """Independent sparse statevector check of actual emitted Qiskit operations."""
    import cmath
    from qiskit.circuit.classical import expr
    record = {}
    cursor = 0

    def condition(value):
        if isinstance(value, tuple):
            return record.get(value[0], 0) == value[1]
        if isinstance(value, expr.Var):
            return bool(record.get(value.var, 0))
        if isinstance(value, expr.Binary) and value.op == expr.Binary.Op.LOGIC_AND:
            return condition(value.left) and condition(value.right)
        raise ValueError(f"Unsupported classical expression {value}")

    def execute(block, qmap, cmap, state):
        nonlocal cursor
        for instruction in block.data:
            op = instruction.operation
            qs = [qmap[q] for q in instruction.qubits]
            cs = [cmap[b] for b in instruction.clbits]
            if op.name == "if_else":
                # Rebind block-local classical operands to the enclosing bits.
                inner = op.blocks[0] if condition(op.condition) else (op.blocks[1] if len(op.blocks)>1 else None)
                if inner is not None:
                    state = execute(inner, dict(zip(inner.qubits, qs)),
                                    dict(zip(inner.clbits, cs)), state)
                continue
            if op.name in ("x", "cx", "ccx"):
                mask = sum(1 << p for p in qs[:-1])
                state = {(x ^ (1 << qs[-1]) if x & mask == mask else x): a
                         for x, a in state.items()}
            elif op.name in ("z", "cz", "ccz"):
                mask = sum(1 << p for p in qs)
                state = {x: (-a if x & mask == mask else a) for x, a in state.items()}
            elif op.name == "h":
                out = {}
                p = qs[0]
                for x, a in state.items():
                    lo, hi = x & ~(1 << p), x | (1 << p)
                    out[lo] = out.get(lo, 0) + a / 2**0.5
                    out[hi] = out.get(hi, 0) + (-a if x >> p & 1 else a) / 2**0.5
                state = {x:a for x,a in out.items() if abs(a)>1e-14}
            elif op.name == "measure":
                outcome = transcript >> cursor & 1
                cursor += 1
                record[cs[0]] = outcome
                state = {x:a for x,a in state.items() if (x >> qs[0] & 1) == outcome}
            elif op.name == "reset":
                values = {x >> qs[0] & 1 for x in state}
                if len(values) > 1:
                    raise AssertionError("Reset would discard coherence")
                state = {x & ~(1 << qs[0]):a for x,a in state.items()}
            else:
                raise ValueError(op.name)
        if block.global_phase:
            state = {x:a*cmath.exp(1j*float(block.global_phase)) for x,a in state.items()}
        return state

    state = execute(qc, {q:i for i,q in enumerate(qc.qubits)}, {b:b for b in qc.clbits}, amplitudes)
    return state, cursor
