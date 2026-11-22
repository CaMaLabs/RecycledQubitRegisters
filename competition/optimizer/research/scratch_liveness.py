#!/usr/bin/env python3
"""Read-only fixed-order width screen for Kickmix with zero-initialized scratch."""

import argparse
import hashlib
import json
from pathlib import Path

from competition.optimizer.autonomous.kickmix_trace import ZERO, Trace, load_program


def width_screen(text, max_terms=32):
    """Compare lifetime peaks with HMR alone and with all proved zero returns."""
    program, pinned = load_program(text)
    source_ids = pinned | {q for instruction in program for q in instruction.qubits}
    trace = Trace(pinned, max_terms)
    hmr_live, symbolic_live = set(pinned), set(pinned)
    hmr_peak = symbolic_peak = len(pinned)
    hmr_peak_lines = symbolic_peak_lines = 0
    hmr_first_peak = symbolic_first_peak = None
    other_zero_releases = 0
    decisive_zero_wires = set()

    for instruction in program:
        condition = trace.guard(instruction)
        if condition is None:
            continue
        line, opcode, qs, _, inline_guard = instruction
        hmr_live.update(qs)
        symbolic_live.update(qs)
        if len(hmr_live) > hmr_peak:
            hmr_peak, hmr_peak_lines, hmr_first_peak = len(hmr_live), 0, line
        if len(symbolic_live) > symbolic_peak:
            symbolic_peak, symbolic_peak_lines, symbolic_first_peak = len(symbolic_live), 0, line
        hmr_peak_lines += bool(qs) and len(hmr_live) == hmr_peak
        symbolic_peak_lines += bool(qs) and len(symbolic_live) == symbolic_peak

        trace.apply(instruction, condition)
        if opcode == "HMR" and inline_guard is None and len(trace.guards) == 1:
            hmr_live.difference_update(q for q in qs if q not in pinned)

        for q in qs:
            if q not in pinned and trace.qubits[q] == ZERO:
                symbolic_live.remove(q)
                if q in hmr_live:
                    other_zero_releases += 1
                    decisive_zero_wires.add(q)

    trace.finish()

    return {
        "source_width": max(source_ids, default=-1) + 1,
        "pinned_register_qubits": sorted(pinned),
        "fixed_order_hmr_peak": hmr_peak,
        "fixed_order_hmr_peak_first_line": hmr_first_peak,
        "fixed_order_hmr_peak_lines": hmr_peak_lines,
        "fixed_order_symbolic_peak": symbolic_peak,
        "fixed_order_symbolic_peak_first_line": symbolic_first_peak,
        "fixed_order_symbolic_peak_lines": symbolic_peak_lines,
        "other_zero_releases": other_zero_releases,
        "wires_with_other_zero_release": sorted(decisive_zero_wires),
        "opaque_boolean_expressions": trace.proof.opaque,
        "max_terms": max_terms,
        "officially_verified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--max-terms", type=int, default=32)
    args = parser.parse_args()
    source = args.source.read_bytes()
    try:
        report = width_screen(source.decode("utf-8"), args.max_terms)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({"source_sha256": hashlib.sha256(source).hexdigest(), **report}, indent=2))


if __name__ == "__main__":
    main()
