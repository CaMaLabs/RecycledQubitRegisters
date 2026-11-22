#!/usr/bin/env python3
"""Read-only fixed-order width screen for Kickmix with zero-initialized scratch."""

import argparse
import hashlib
import json
import re
from pathlib import Path

TOKEN = re.compile(r"[qbr][0-9]+\Z", re.ASCII)
ANGLE = re.compile(r"[+-]?[0-9]+\.[0-9]+\Z", re.ASCII)
QUANTUM = {
    "X": "q", "CX": "qq", "CCX": "qqq", "SWAP": "qq", "CSWAP": "qqq",
    "Z": "q", "CZ": "qq", "CCZ": "qqq", "Z_POW": "qa", "NEG": "",
    "R": "q", "HMR": "qb",
}
CLASSICAL = {"BIT_INVERT": "b", "BIT_STORE0": "b", "BIT_STORE1": "b"}
ZERO = frozenset()
ONE = frozenset((frozenset(),))


class BooleanProof:
    """Bound ANF growth by replacing large subexpressions with opaque symbols.

    A symbol denotes its original Boolean expression. Dropping relationships
    between symbols can hide zeros but cannot introduce false zeros.
    """

    def __init__(self, max_terms):
        self.max_terms = max_terms
        self.atoms = {}
        self.opaque = 0

    def atom(self, key):
        if key not in self.atoms:
            self.atoms[key] = len(self.atoms)
            if key[0] == "opaque":
                self.opaque += 1
        return frozenset((frozenset((self.atoms[key],)),))

    def xor(self, a, b):
        result = a ^ b
        if len(result) > self.max_terms:
            return self.atom(("opaque", "xor", frozenset((a, b))))
        return result

    def both(self, a, b):
        if not a or not b:
            return ZERO
        if a == ONE or a == b:
            return b
        if b == ONE:
            return a
        if len(a) * len(b) > self.max_terms:
            return self.atom(("opaque", "and", frozenset((a, b))))
        result = set()
        for x in a:
            for y in b:
                term = x | y
                if term in result:
                    result.remove(term)
                else:
                    result.add(term)
        return frozenset(result)

    def select(self, guard, old, new):
        if guard == ONE:
            return new
        if guard == ZERO:
            return old
        return self.xor(old, self.both(guard, self.xor(old, new)))


def is_id(token, kind):
    return token.startswith(kind) and TOKEN.fullmatch(token) is not None


def load_program(text):
    program = []
    pinned = set()
    for number, line in enumerate(text.splitlines(), 1):
        body = line.split("#", 1)[0].strip()
        if not body:
            continue
        opcode, *tokens = body.split()
        if opcode == "APPEND_TO_REGISTER":
            if (len(tokens) != 2 or not (is_id(tokens[0], "q") or is_id(tokens[0], "b"))
                    or not is_id(tokens[1], "r")):
                raise ValueError(f"Invalid register operand on line {number}")
            if tokens[0][0] == "q":
                pinned.add(int(tokens[0][1:]))
            continue
        if opcode in {"REGISTER", "INFO_TAG"}:
            continue
        guard = None
        if len(tokens) >= 2 and tokens[-2] == "if" and is_id(tokens[-1], "b"):
            guard = int(tokens[-1][1:])
            tokens = tokens[:-2]
        if opcode == "PUSH_CONDITION" and guard is not None and not tokens:
            program.append((number, opcode, (), None, guard))
            continue
        if opcode == "POP_CONDITION" and guard is None and not tokens:
            program.append((number, opcode, (), None, None))
            continue
        signature = (QUANTUM | CLASSICAL).get(opcode)
        if signature is None or len(signature) != len(tokens) or any(
            (ANGLE.fullmatch(token) is None if kind == "a" else not is_id(token, kind))
            for token, kind in zip(tokens, signature)
        ):
            raise ValueError(f"Unsupported instruction on line {number}: {opcode}")
        qubits = tuple(int(token[1:]) for token, kind in zip(tokens, signature) if kind == "q")
        if len(qubits) != len(set(qubits)):
            raise ValueError(f"Repeated qubit operands on line {number}")
        bit = next((int(token[1:]) for token, kind in zip(tokens, signature) if kind == "b"), None)
        program.append((number, opcode, qubits, bit, guard))
    return program, pinned


def width_screen(text, max_terms=32):
    """Compare lifetime peaks with HMR alone and with all proved zero returns."""
    if max_terms < 1:
        raise ValueError("max_terms must be positive")
    program, pinned = load_program(text)
    source_ids = pinned | {q for _, _, qs, _, _ in program for q in qs}
    proof = BooleanProof(max_terms)
    bits = {}
    qubit = {q: proof.atom(("input", q)) for q in pinned}
    captured_guards = [ONE]
    hmr_live, symbolic_live = set(pinned), set(pinned)
    hmr_peak = symbolic_peak = len(pinned)
    hmr_peak_lines = symbolic_peak_lines = 0
    hmr_first_peak = symbolic_first_peak = None
    other_zero_releases = 0
    decisive_zero_wires = set()

    def bit_value(index):
        if index not in bits:
            bits[index] = proof.atom(("initial_bit", index))
        return bits[index]

    for line, opcode, qs, written_bit, inline_guard in program:
        if opcode == "PUSH_CONDITION":
            captured_guards.append(proof.both(captured_guards[-1], bit_value(inline_guard)))
            continue
        if opcode == "POP_CONDITION":
            if len(captured_guards) == 1:
                raise ValueError(f"Unmatched POP_CONDITION on line {line}")
            captured_guards.pop()
            continue
        condition = captured_guards[-1]
        if inline_guard is not None:
            condition = proof.both(condition, bit_value(inline_guard))
        hmr_live.update(qs)
        symbolic_live.update(qs)
        if len(hmr_live) > hmr_peak:
            hmr_peak, hmr_peak_lines, hmr_first_peak = len(hmr_live), 0, line
        if len(symbolic_live) > symbolic_peak:
            symbolic_peak, symbolic_peak_lines, symbolic_first_peak = len(symbolic_live), 0, line
        hmr_peak_lines += bool(qs) and len(hmr_live) == hmr_peak
        symbolic_peak_lines += bool(qs) and len(symbolic_live) == symbolic_peak

        for q in qs:
            qubit.setdefault(q, ZERO)
        if opcode in {"X", "CX", "CCX"}:
            target = qs[-1]
            toggle = condition
            for control in qs[:-1]:
                toggle = proof.both(toggle, qubit[control])
            qubit[target] = proof.xor(qubit[target], toggle)
        elif opcode in {"SWAP", "CSWAP"}:
            a, b = qs[-2:]
            if opcode == "CSWAP":
                condition = proof.both(condition, qubit[qs[0]])
            delta = proof.both(condition, proof.xor(qubit[a], qubit[b]))
            qubit[a] = proof.xor(qubit[a], delta)
            qubit[b] = proof.xor(qubit[b], delta)
        elif opcode in {"R", "HMR"}:
            target = qs[0]
            qubit[target] = proof.select(condition, qubit[target], ZERO)
            if opcode == "HMR":
                bits[written_bit] = proof.select(
                    condition, bit_value(written_bit), proof.atom(("measurement", line)))
                if inline_guard is None and len(captured_guards) == 1 and target not in pinned:
                    hmr_live.remove(target)
        elif opcode in CLASSICAL:
            current = bit_value(written_bit)
            if opcode == "BIT_INVERT":
                bits[written_bit] = proof.xor(current, condition)
            else:
                bits[written_bit] = proof.select(
                    condition, current, ONE if opcode == "BIT_STORE1" else ZERO)

        for q in qs:
            if q not in pinned and qubit[q] == ZERO:
                symbolic_live.remove(q)
                if q in hmr_live:
                    other_zero_releases += 1
                    decisive_zero_wires.add(q)

    if len(captured_guards) != 1:
        raise ValueError("Unterminated condition stack")

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
        "opaque_boolean_expressions": proof.opaque,
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
