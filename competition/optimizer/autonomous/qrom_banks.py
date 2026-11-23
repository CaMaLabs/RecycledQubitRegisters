"""Bounded product-bank synthesis for mixed QROM writes and phase cleanup."""

from bisect import bisect_left
from collections import defaultdict
from fractions import Fraction
from itertools import combinations

from .kickmix_trace import ONE, ZERO, Trace, load_program, physical_lines

MAX_SPAN = 2048


def expected_active(trace, guard, condition):
    """Lower bound execution probability using exact affine HMR guard rank."""
    if condition in (ONE, ZERO):
        return Fraction(condition == ONE)
    constraints = list(trace.captured_bits)
    if guard is not None:
        constraints.append(trace.bit_value(guard))
    basis = {}
    for expression in constraints:
        atoms = set()
        for term in expression:
            if len(term) > 1 or (term and not term <= trace.measurements):
                return Fraction(0)
            atoms.update(term)
        mask = sum(1 << atom for atom in atoms)
        rhs = frozenset() not in expression
        while mask:
            key = mask.bit_length()
            if key not in basis:
                basis[key] = mask, rhs
                break
            row, offset = basis[key]
            mask ^= row
            rhs ^= offset
        if not mask and rhs:
            return Fraction(0)
    return Fraction(1, 1 << len(basis))


def scope_ranges(program):
    """Find whole top-level scopes suitable for unguarded bank placement."""
    spans = [(index, index + 1) for index in range(len(program))]
    depth = 0
    for index, instruction in enumerate(program):
        if instruction.opcode == "PUSH_CONDITION":
            if depth == 0:
                start = index
            depth += 1
        elif instruction.opcode == "POP_CONDITION":
            depth -= 1
            if depth == 0:
                spans[start:index + 1] = [(start, index + 1)] * (index + 1 - start)
    return spans


def written_wires(instruction):
    if instruction.opcode in {"X", "CX", "CCX", "R", "HMR"}:
        return instruction.qubits[-1:]
    if instruction.opcode in {"SWAP", "CSWAP"}:
        return instruction.qubits[-2:]
    return ()


def untouched(positions, start, end):
    index = bisect_left(positions, start)
    return index == len(positions) or positions[index] >= end


def bank_options(program, pinned, max_terms):
    trace = Trace(pinned, max_terms)
    spans = scope_ranges(program)
    all_wires = {wire for op in program for wire in op.qubits}
    scratch = sorted(all_wires - pinned)
    declared_clean = {}
    touches, writes, groups = defaultdict(list), defaultdict(list), defaultdict(list)
    for index, instruction in enumerate(program):
        if spans[index][0] == index:
            declared_clean[index] = sum(1 << i for i, wire in enumerate(scratch)
                                        if trace.qubits.get(wire, ZERO) == ZERO)
        condition = trace.guard(instruction)
        if condition is None:
            continue
        for wire in instruction.qubits:
            touches[wire].append(index)
        if instruction.opcode in {"CCX", "CCZ"}:
            probability = expected_active(trace, instruction.guard, condition)
            if probability:
                pairs = [tuple(sorted(instruction.qubits[:2]))] if instruction.opcode == "CCX" else combinations(sorted(instruction.qubits), 2)
                for pair in pairs:
                    groups[(pair, len(writes[pair[0]]), len(writes[pair[1]]))].append((index, probability))
        for wire in written_wires(instruction):
            writes[wire].append(index)
        trace.apply(instruction, condition)
    trace.finish()

    options = []
    for (pair, _, _), hits in groups.items():
        if sum(probability for _, probability in hits) <= 2:
            continue
        # Retain the widest profitable prefix for each feasible start.
        for offset, (first, _) in enumerate(hits):
            if len(hits) - offset < 3:
                break
            start = spans[first][0]
            selected = []
            gain = Fraction(-2)
            best = None
            for index, probability in hits[offset:]:
                end = spans[index][1]
                if end - start > MAX_SPAN:
                    break
                if not all(untouched(writes[wire], start, end) for wire in pair):
                    break
                bank = next((wire for i, wire in enumerate(scratch)
                             if declared_clean[start] >> i & 1 and wire not in pair
                             and untouched(touches[wire], start, end)), None)
                if bank is None:
                    break
                selected.append(index)
                gain += probability
                if gain > 0:
                    best = gain, start, end, pair, bank, len(selected)
            if best is not None:
                gain, start, end, pair, bank, count = best
                options.append((gain, start, end, pair, bank, tuple(selected[:count])))
    options.sort(key=lambda option: (option[0], -(option[2] - option[1])), reverse=True)
    chosen = []
    for option in options:
        _, start, end, *_ = option
        if all(end <= prior[1] or start >= prior[2] for prior in chosen):
            chosen.append(option)
    return chosen


def share_banks(source, max_terms):
    text = source.decode("utf-8")
    program, pinned = load_program(text)
    lines = physical_lines(text)
    reports = []
    for gain, start, end, pair, bank, indices in bank_options(program, pinned, max_terms):
        begin, last = program[start].line - 1, program[end - 1].line - 1
        head = f"CCX q{pair[0]} q{pair[1]} q{bank}\n"
        for index in indices:
            instruction = program[index]
            target = next(wire for wire in instruction.qubits if wire not in pair)
            opcode = "CX" if instruction.opcode == "CCX" else "CZ"
            guard = f" if b{instruction.guard}" if instruction.guard is not None else ""
            lines[instruction.line - 1] = f"{opcode} q{bank} q{target}{guard}\n"
        lines[begin] = head + lines[begin]
        lines[last] = lines[last].rstrip("\r\n") + "\n" + head
        reports.append({"start_line": begin + 1, "end_line": last + 1,
                        "controls": list(pair), "bank": bank,
                        "replaced_lines": [program[index].line for index in indices],
                        "net_expected_toffoli_saving_lower_bound": str(gain)})
    return "".join(lines).encode("utf-8"), reports
