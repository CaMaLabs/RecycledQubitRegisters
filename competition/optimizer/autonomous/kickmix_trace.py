"""Conservative symbolic value trace for phased classical Kickmix circuits."""

import re
from typing import NamedTuple

TOKEN = re.compile(r"[qbr][0-9]+\Z", re.ASCII)
ANGLE = re.compile(r"[+-]?[0-9]+\.[0-9]+\Z", re.ASCII)
QUANTUM = {
    "X": "q", "CX": "qq", "CCX": "qqq", "SWAP": "qq", "CSWAP": "qqq",
    "Z": "q", "CZ": "qq", "CCZ": "qqq", "Z_POW": "qa", "NEG": "",
    "R": "q", "HMR": "qb",
}
CLASSICAL = {"BIT_INVERT": "b", "BIT_STORE0": "b", "BIT_STORE1": "b"}
SIGNATURES = QUANTUM | CLASSICAL
ZERO = frozenset()
ONE = frozenset((frozenset(),))


class Instruction(NamedTuple):
    line: int
    opcode: str
    qubits: tuple
    bit: int | None
    guard: int | None


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


def physical_lines(text):
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def load_program(text):
    program = []
    pinned = set()
    for number, line in enumerate(physical_lines(text), 1):
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
            program.append(Instruction(number, opcode, (), None, guard))
            continue
        if opcode == "POP_CONDITION" and guard is None and not tokens:
            program.append(Instruction(number, opcode, (), None, None))
            continue
        signature = SIGNATURES.get(opcode)
        if signature is None or len(signature) != len(tokens) or any(
            (ANGLE.fullmatch(token) is None if kind == "a" else not is_id(token, kind))
            for token, kind in zip(tokens, signature)
        ):
            raise ValueError(f"Unsupported instruction on line {number}: {opcode}")
        qubits = tuple(int(token[1:]) for token, kind in zip(tokens, signature) if kind == "q")
        if len(qubits) != len(set(qubits)):
            raise ValueError(f"Repeated qubit operands on line {number}")
        bit = next((int(token[1:]) for token, kind in zip(tokens, signature) if kind == "b"), None)
        program.append(Instruction(number, opcode, qubits, bit, guard))
    return program, pinned


class Trace:
    """Follow basis trajectories with zero scratch and arbitrary input bits and HMR outcomes."""

    def __init__(self, pinned, max_terms):
        if max_terms < 1:
            raise ValueError("max_terms must be positive")
        self.proof = BooleanProof(max_terms)
        self.qubits = {q: self.proof.atom(("input", q)) for q in sorted(pinned)}
        self.bits = {}
        self.guards = [ONE]
        self.captured_bits = []
        self.measurements = set()

    def bit_value(self, bit):
        if bit not in self.bits:
            self.bits[bit] = self.proof.atom(("initial_bit", bit))
        return self.bits[bit]

    def guard(self, instruction):
        condition = self.guards[-1]
        if instruction.opcode == "PUSH_CONDITION":
            captured = self.bit_value(instruction.guard)
            self.captured_bits.append(captured)
            self.guards.append(self.proof.both(condition, captured))
            return None
        if instruction.opcode == "POP_CONDITION":
            if len(self.guards) == 1:
                raise ValueError(f"Unmatched POP_CONDITION on line {instruction.line}")
            self.guards.pop()
            self.captured_bits.pop()
            return None
        if instruction.guard is not None:
            condition = self.proof.both(condition, self.bit_value(instruction.guard))
        for wire in instruction.qubits:
            self.qubits.setdefault(wire, ZERO)
        return condition

    def apply(self, instruction, condition):
        opcode, qs, bit = instruction.opcode, instruction.qubits, instruction.bit
        proof, qubit = self.proof, self.qubits
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
                measurement = proof.atom(("measurement", instruction.line))
                self.measurements.update(next(iter(measurement)))
                self.bits[bit] = proof.select(
                    condition, self.bit_value(bit), measurement)
        elif opcode in CLASSICAL:
            current = self.bit_value(bit)
            if opcode == "BIT_INVERT":
                self.bits[bit] = proof.xor(current, condition)
            else:
                self.bits[bit] = proof.select(condition, current, ONE if opcode == "BIT_STORE1" else ZERO)

    def finish(self):
        if len(self.guards) != 1:
            raise ValueError("Unterminated condition stack")
