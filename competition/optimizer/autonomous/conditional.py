"""Exact rewrites of contiguous KMX operations with a shared read-only guard."""

from collections import defaultdict
import re

from .core import DIAG, Gate, Proposal, cost, parse

GUARD = re.compile(r"b[0-9]+", re.ASCII)


def parse_guarded(line):
    tokens = line.split()
    if len(tokens) < 4 or tokens[-2] != "if" or not GUARD.fullmatch(tokens[-1]):
        return None
    gate = parse(" ".join(tokens[:-2]))
    return (gate, tokens[-1]) if gate is not None else None


def parse_region(lines, guard=None):
    if guard is None:
        return [parse(line) for line in lines]
    gates = []
    for line in lines:
        parsed = parse_guarded(line)
        gates.append(parsed[0] if parsed and parsed[1] == guard else None)
    return gates


def render_region(gates, guard=None):
    if guard is None:
        return [gate.text() for gate in gates]
    return [gate.text().rstrip("\n") + f" if {guard}\n" for gate in gates]


def conditional_phase(gates, budget, seed):
    """Simplify commuting conditional diagonals with exact phase factoring."""
    if any(gate.op not in DIAG and gate.op != "Z_POW" for gate in gates):
        return None
    # Identical diagonal involutions cancel, including across other phases.
    pending = {}
    removed = set()
    for i, gate in enumerate(gates):
        if gate.op not in {"Z", "CZ", "CCZ"}:
            continue
        if gate in pending:
            removed.update((pending.pop(gate), i))
        else:
            pending[gate] = i
    reduced = [gate for i, gate in enumerate(gates) if i not in removed]

    # (-1)^(p*x) (-1)^(p*y) = (-1)^(p*(x xor y)).
    # Place the conjugation together so it preserves every other phase.
    supports = defaultdict(list)
    best = reduced
    strategy = "duplicate_diagonal"
    for i, gate in enumerate(reduced):
        if gate.op not in {"CCZ", "CZ"}:
            continue
        for target in gate.q:
            shared = tuple(q for q in gate.q if q != target)
            supports[(gate.op, shared)].append((i, target))
    for (opcode, shared), hits in supports.items():
        if len(hits) < 2:
            continue
        _, target = hits[0]
        positions = {i for i, _ in hits}
        basis = [Gate("CX", (other, target)) for _, other in hits[1:]]
        fused = basis + [Gate(opcode, tuple(sorted((*shared, target))))] + basis[::-1]
        candidate = fused + [gate for i, gate in enumerate(reduced) if i not in positions]
        if cost(candidate) < cost(best):
            best, strategy = candidate, "shared_diagonal_product"
    if cost(best) < cost(gates):
        return Proposal(best, {"architecture": strategy, "scope": "one unchanged classical bit"})
    return None
