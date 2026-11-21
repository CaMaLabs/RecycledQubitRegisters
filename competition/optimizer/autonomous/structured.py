"""Circuit-only adaptations of identity screening and Fourier parity sparsity."""

import time
from collections import defaultdict

from .core import Gate, PHASE, Proposal, cost, signature

AFFINE = {"X", "CX", "SWAP"}
PHASE_REGION = AFFINE | set(PHASE)


def identity_screen(gates, budget, seed):
    """Find a complete identity subblock, including phase on every basis input."""
    deadline = time.monotonic() + budget["seconds"]
    tested = 0
    best = None
    best_cost = cost(gates)
    for length in range(len(gates), 1, -1):
        for start in range(len(gates) - length + 1):
            if time.monotonic() >= deadline or tested >= budget["max_states"]:
                return best
            end = start + length
            trial = gates[:start] + gates[end:]
            if cost(trial) >= best_cost:
                continue
            block = gates[start:end]
            wires = sorted({wire for gate in block for wire in gate.q})
            tested += 1
            if all(out == index and phase == 0 for index, (out, phase)
                   in enumerate(signature(block, wires))):
                best_cost = cost(trial)
                best = Proposal(trial, {"identity_interval": [start, end], "checks": tested})
                if not trial:
                    return best
    return best


def parity_spectrum(gates, budget, seed):
    """Combine equal affine Walsh characters in the phase exponent modulo eight."""
    linear = {}
    groups = defaultdict(list)
    for index, gate in enumerate(gates):
        if gate.op not in PHASE_REGION:
            return None
        for wire in gate.q:
            if wire not in linear:
                linear[wire] = (frozenset((wire,)), 0)
        if gate.op == "X":
            mask, bias = linear[gate.q[0]]
            linear[gate.q[0]] = (mask, bias ^ 1)
        elif gate.op == "CX":
            a, b = gate.q
            left, left_bias = linear[a]
            right, right_bias = linear[b]
            linear[b] = (left ^ right, left_bias ^ right_bias)
        elif gate.op == "SWAP":
            a, b = gate.q
            linear[a], linear[b] = linear[b], linear[a]
        elif len(gate.q) == 1:
            groups[linear[gate.q[0]]].append(index)

    sequences = ((), ("T",), ("S",), ("S", "T"), ("Z",),
                 ("S_DAG", "T_DAG"), ("S_DAG",), ("T_DAG",))
    edits = {}
    for indices in groups.values():
        if len(indices) < 2:
            continue
        first = indices[0]
        originals = [gates[i] for i in indices]
        residue = sum(PHASE[gate.op] for gate in originals) % 8
        replacement = [Gate(op, gates[first].q) for op in sequences[residue]]
        if cost(replacement) < cost(originals):
            edits.update({index: [] for index in indices})
            edits[first] = replacement
    if edits:
        result = [part for i, gate in enumerate(gates) for part in edits.get(i, [gate])]
        return Proposal(result, {"grouped_phase_sites": len(edits), "modulus": 8})
    return None
