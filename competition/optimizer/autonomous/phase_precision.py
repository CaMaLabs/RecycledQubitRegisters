"""Exact 128-bit rotation merging and four-dimensional Walsh relations."""

from collections import defaultdict
from itertools import combinations
from .core import EIGHTH, TURN, PHASE, Gate, Proposal, cost, phase_ticks
from .structured import AFFINE

PHASE_OPS = AFFINE | set(PHASE) | {"Z_POW"}


def parity_network(mask, wires, pivot):
    return [Gate("CX", (wire, pivot)) for i, wire in enumerate(wires)
            if (mask >> i) & 1 and wire != pivot]


def phase_gates(wire, ticks, native):
    if native:
        return [Gate("Z_POW", (wire,), ticks)] if ticks else []
    names = ((), ("T",), ("S",), ("S", "T"), ("Z",),
             ("S_DAG", "T_DAG"), ("S_DAG",), ("T_DAG",))
    return [Gate(op, (wire,)) for op in names[ticks // EIGHTH]]


def phase_function(gates, budget, seed):
    """Prove zero phase error exactly with the common exhaustive checker.

    Constants from complemented parities cancel out of the comparison only
    because the constant is explicitly tracked. Retain the source if an exact
    rewrite would require introducing unsupported standalone global-phase syntax.
    """
    if any(gate.op not in PHASE_OPS for gate in gates):
        return None
    native = any(gate.op == "Z_POW" for gate in gates)
    wires = sorted({wire for gate in gates for wire in gate.q})
    basis = {wire: (1 << i, 0) for i, wire in enumerate(wires)}
    coefficients = defaultdict(int)
    sites = defaultdict(list)
    affine = []
    constant = 0
    for i, gate in enumerate(gates):
        if gate.op in AFFINE:
            affine.append(gate)
            a = gate.q[0]
            if gate.op == "X":
                mask, bias = basis[a]
                basis[a] = mask, bias ^ 1
            elif gate.op == "SWAP":
                a, b = gate.q
                basis[a], basis[b] = basis[b], basis[a]
            else:
                a, b = gate.q
                x, y = basis[a], basis[b]
                basis[b] = x[0] ^ y[0], x[1] ^ y[1]
        elif len(gate.q) != 1:
            # General controlled diagonal operations need a separate
            # multivariate expansion before moving the full phase polynomial.
            return None
        else:
            mask, bias = basis[gate.q[0]]
            ticks = phase_ticks(gate)
            sites[mask, bias].append(i)
            constant = (constant + bias * ticks) % TURN
            coefficients[mask] = (coefficients[mask] + (-ticks if bias else ticks)) % TURN

    # Prefer in-situ merges for sparse circuits to avoid routing overhead.
    edits = {}
    for indices in sites.values():
        values = [gates[i] for i in indices]
        ticks = sum(map(phase_ticks, values)) % TURN
        first = indices[0]
        if len(indices) == 1 and (values[0].op != "Z_POW" or ticks % (2 * EIGHTH)):
            continue
        edits.update({i: [] for i in indices})
        if ticks:
            edits[first] = phase_gates(gates[first].q[0], ticks, native)
    merged = [part for i, gate in enumerate(gates) for part in edits.get(i, [gate])]
    best = merged if cost(merged) < cost(gates) else list(gates)
    method = "in_situ_rotation_merge"

    if not constant and len(wires) >= 4:
        # In a rank-four binary subspace, all 15 nonzero parities sum
        # to either 0 or 8. Adding pi/4 to all therefore changes no phase.
        for axes in combinations(range(len(wires)), 4):
            masks = [sum(1 << axes[j] for j in range(4) if (i >> j) & 1)
                     for i in range(1, 16)]
            if sum(coefficients[m] % (2 * EIGHTH) == EIGHTH for m in masks) <= 7:
                continue
            updated = dict(coefficients)
            for mask in masks:
                updated[mask] = (updated[mask] + EIGHTH) % TURN
            candidate = []
            for mask, ticks in sorted(updated.items()):
                if not ticks:
                    continue
                pivot = wires[mask.bit_length() - 1]
                network = parity_network(mask, wires, pivot)
                candidate.extend(network + phase_gates(pivot, ticks, native) + network[::-1])
            candidate.extend(affine)
            if cost(candidate) < cost(best):
                best, method = candidate, "walsh_rank_four_null_relation"
    if cost(best) < cost(gates):
        return Proposal(best, {"method": method, "phase_error_turns": 0,
                               "precision": "Kickmix fixed 128-bit turns"})
    return None


def phase_predicate(gates, budget, seed):
    """Fold rotations on exactly equal predicates across nonlinear arithmetic."""
    from .core import REV

    native = any(gate.op == "Z_POW" for gate in gates)
    wires = sorted({wire for gate in gates for wire in gate.q})
    if len(wires) > 10 or any(gate.op not in (REV | PHASE_OPS) for gate in gates):
        return None
    if sum(gate.op in {"Z_POW", "T", "T_DAG", "S", "S_DAG", "Z"}
           for gate in gates) < 2:
        return None
    size = 1 << len(wires)
    all_bits = (1 << size) - 1
    values = {wire: sum(((x >> i) & 1) << x for x in range(size))
              for i, wire in enumerate(wires)}
    sites = defaultdict(list)
    for i, gate in enumerate(gates):
        if gate.op == "X":
            values[gate.q[0]] ^= all_bits
        elif gate.op == "CX":
            a, b = gate.q
            values[b] ^= values[a]
        elif gate.op == "CCX":
            a, b, c = gate.q
            values[c] ^= values[a] & values[b]
        elif gate.op == "SWAP":
            a, b = gate.q
            values[a], values[b] = values[b], values[a]
        elif gate.op == "CSWAP":
            c, a, b = gate.q
            delta = values[c] & (values[a] ^ values[b])
            values[a] ^= delta
            values[b] ^= delta
        elif len(gate.q) == 1:
            sites[values[gate.q[0]]].append(i)
        # CZ and CCZ change no Boolean wire value and stay in place.
    edits = {}
    for indices in sites.values():
        if len(indices) < 2:
            continue
        source = [gates[i] for i in indices]
        ticks = sum(map(phase_ticks, source)) % TURN
        replacement = phase_gates(source[0].q[0], ticks, native)
        if cost(replacement) < cost(source):
            edits.update({i: [] for i in indices})
            edits[indices[0]] = replacement
    if edits:
        result = [part for i, gate in enumerate(gates) for part in edits.get(i, [gate])]
        return Proposal(result, {"method": "exact_nonlinear_phase_predicates",
                                 "phase_error_turns": 0, "assignments": size})
    return None
