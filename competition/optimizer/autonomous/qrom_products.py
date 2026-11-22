"""Share already-computed products across Kickmix lookup and phase cleanup."""

import argparse
from itertools import combinations
import json
from pathlib import Path

from .core import sha
from .kickmix_trace import ONE, ZERO, Trace, load_program, physical_lines
from .qrom_banks import share_banks

MAX_TERMS = 32
MAX_SPAN_TERMS = 256
MAX_CLIFFORDS = 8


def pivot(row):
    return max(row, key=lambda term: tuple(sorted(term)))


def reduce_row(row, basis, mask=0):
    while row and len(row) <= MAX_SPAN_TERMS:
        reducer = basis.get(pivot(row))
        if reducer is None:
            break
        row ^= reducer[0]
        mask ^= reducer[1]
    return row, mask


def affine_witness(product, active_values, excluded):
    """Represent the product as a bounded parity of distinct live controls."""
    basis = {}
    usable = [(wire, value) for wire, value in active_values.items() if wire != excluded]
    for index, (_, value) in enumerate(usable):
        row, mask = reduce_row(value, basis, 1 << index)
        if row and len(row) <= MAX_SPAN_TERMS:
            basis[pivot(row)] = row, mask
    remainder, mask = reduce_row(product, basis)
    if remainder or mask.bit_count() > MAX_CLIFFORDS:
        return None
    return [wire for index, (wire, _) in enumerate(usable) if mask & (1 << index)]


def free_gate(instruction, trace, condition, wire_order):
    """Replace one Toffoli-class gate with a Clifford on every active branch."""
    if condition == ZERO:
        return [], "inactive_guard"
    opcode, wires = instruction.opcode, instruction.qubits
    if opcode == "CCX":
        pairs = [(wires[0], wires[1], wires[2])]
    else:
        pairs = [(a, b, next(wire for wire in wires if wire not in (a, b)))
                 for a, b in combinations(wires, 2)]

    proof, values = trace.proof, trace.qubits
    single_gate, two_gate = ("X", "CX") if opcode == "CCX" else ("Z", "CZ")
    active = {None: condition}
    active.update((wire, proof.both(condition, values[wire])) for wire in wire_order if wire in values)
    products = []
    for a, b, target in pairs:
        product = proof.both(values[a], values[b])
        guarded = proof.both(condition, product)
        if guarded == ZERO:
            return [], "zero_product"
        if guarded == condition:
            return [f"{single_gate} q{target}"], "unit_product"
        for wire in wire_order:
            if (wire != target or opcode == "CCZ") and active.get(wire) == guarded:
                gate = f"Z q{target}" if wire == target else f"{two_gate} q{wire} q{target}"
                method = "live_product" if values[wire] == product else "guarded_live_product"
                return [gate], method
        products.append((guarded, target))
    best = None
    for product, target in products:
        used = affine_witness(product, active, target if opcode == "CCX" else -1)
        if used is not None and (best is None or len(used) < len(best)):
            best = [f"{single_gate} q{target}" if wire is None or wire == target
                    else f"{two_gate} q{wire} q{target}" for wire in used]
    return (best, "affine_live_products") if best is not None else None


def optimize(source, max_terms=MAX_TERMS):
    text = source.decode("utf-8")
    program, inputs = load_program(text)
    if not inputs:
        raise ValueError("Declare the quantum input register with APPEND_TO_REGISTER")
    trace = Trace(inputs, max_terms)
    lines = physical_lines(text)
    wire_order = sorted(inputs | {wire for op in program for wire in op.qubits})
    edits = []
    unconditional = 0
    for instruction in program:
        condition = trace.guard(instruction)
        if condition is None:
            continue
        if instruction.opcode in {"CCX", "CCZ"}:
            match = free_gate(instruction, trace, condition, wire_order)
            if match is not None:
                replacement, reason = match
                if instruction.guard is not None:
                    replacement = [f"{gate} if b{instruction.guard}" for gate in replacement]
                line = instruction.line - 1
                original = lines[line]
                newline = "\r\n" if original.endswith("\r\n") else "\n"
                lines[line] = "".join(gate + newline for gate in replacement)
                unconditional += condition == ONE
                edits.append({"line": instruction.line, "before": original.strip(),
                              "after": replacement, "witness": reason,
                              "always_executed": condition == ONE})
        trace.apply(instruction, condition)
    trace.finish()
    after_affine = "".join(lines).encode("utf-8")
    candidate, banks = share_banks(after_affine, max_terms)
    removed = len(edits) + sum(len(bank["replaced_lines"]) - 2 for bank in banks)
    return candidate, {"source_sha256": sha(source), "candidate_sha256": sha(candidate),
                       "proof": {"status": "EXACT", "method": "symbolic_gf2_product_trace",
                                 "scope": "zero-initialized scratch and all input/measurement bits",
                                 "max_terms": max_terms},
                       "edits": edits, "banks": banks, "static_toffoli_removed": removed,
                       "always_executed_free_toffoli_removed": unconditional,
                       "official_score": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New candidate path")
    parser.add_argument("--report", type=Path, help="New JSON proof report path")
    args = parser.parse_args()
    try:
        candidate, report = optimize(args.source.read_bytes())
        with args.output.open("xb") as stream:
            stream.write(candidate)
        if args.report:
            with args.report.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2)
                stream.write("\n")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    if not args.report:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
