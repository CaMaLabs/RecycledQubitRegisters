#!/usr/bin/env python3
"""Zero-QPU generic Shor preflight using explicit arithmetic decompositions.

This is a compatibility fallback for Qiskit 2.5.x HLS interactions involving
controlled ``IntegerComparatorGate`` / ``ModularAdderGate`` operations.  The
mathematical circuit is unchanged.  Before calling the normal IBM preflight we
replace the two abstract arithmetic appenders with explicit, deterministic
circuit implementations:

* integer comparison: ``IntegerComparator`` two's-complement circuit, using the
  existing ``hls_scratch`` register explicitly;
* addition modulo 2^n: ``DraperQFTAdder(kind='fixed')``;
* controls are materialized eagerly (``annotated=False``) so the backend
  pass manager never has to recursively HLS-synthesize a controlled abstract
  arithmetic gate.

No Sampler is constructed here or in the delegated preflight; this remains a
strictly zero-QPU compiler/resource test.
"""
from __future__ import annotations

from typing import Sequence

from qiskit import QuantumCircuit
from qiskit.circuit.library import DraperQFTAdder, IntegerComparator

import generic_modarith_shor as gm


def _eager_control(operation, control_count: int):
    if control_count == 0:
        return operation
    return operation.control(control_count, annotated=False)


def _scratch_qubits(qc: QuantumCircuit, width: int):
    """Return the dedicated clean comparator scratch register in circuit order."""
    for reg in qc.qregs:
        if reg.name == "hls_scratch":
            scratch = list(reg)
            if len(scratch) != max(0, width - 1):
                raise RuntimeError(
                    f"hls_scratch width mismatch: got {len(scratch)}, expected {width - 1}"
                )
            return scratch
    if width <= 1:
        return []
    raise RuntimeError("generic modular arithmetic circuit has no hls_scratch register")


def append_compare_explicit(
    qc: QuantumCircuit,
    controls: Sequence,
    state: Sequence,
    flag,
    value: int,
    *,
    geq: bool,
) -> None:
    """Append an explicit two's-complement comparator and optional controls."""
    width = len(state)
    scratch = _scratch_qubits(qc, width)

    # IntegerComparator is the eager BlueprintCircuit variant.  For n state
    # qubits it owns n state + 1 result + (n-1) clean ancillary qubits, in that
    # order.  Its internal construction uses the two's-complement comparator.
    base = IntegerComparator(width, int(value), geq=geq).to_gate()
    op = _eager_control(base, len(controls))
    qc.append(
        op,
        list(controls) + list(state) + [flag] + scratch,
    )


def append_mod2n_add_explicit(
    qc: QuantumCircuit,
    controls: Sequence,
    addend: Sequence,
    target: Sequence,
) -> None:
    """Append explicit QFT addition modulo 2^n, with optional eager controls."""
    if len(addend) != len(target):
        raise ValueError("addend and target registers must have equal width")
    base = DraperQFTAdder(len(target), kind="fixed").to_gate()
    op = _eager_control(base, len(controls))
    qc.append(op, list(controls) + list(addend) + list(target))


# Patch the builders before importing/delegating to the normal preflight.  The
# semantic self-test remains gm's independent classical reference and is not
# altered by these replacements.
gm._controlled = _eager_control
gm.append_compare = append_compare_explicit
gm.append_mod2n_add = append_mod2n_add_explicit

import ibm_shor35_generic_modarith_preflight as preflight  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(preflight.main())
