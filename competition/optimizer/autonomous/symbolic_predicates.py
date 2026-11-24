"""K195: bounded exact symbolic predicate equality, with dirty ancillas.

Track each wire as a truth-table Boolean function of all input wires. Two
single-wire phase sites can be merged when their predicate truth tables match
AND their physical target wire matches. The latter restriction makes the
in-place edit valid without synthesizing an alternative predicate network.
"""
from collections import defaultdict
from .core import Gate, Proposal, TURN, REV, PHASE, phase_ticks, prove, cost

SINGLE = {"Z_POW", "Z", "S", "S_DAG", "T", "T_DAG"}


def symbolic_predicate_share(gates, budget, seed):
    wires = sorted({w for g in gates for w in g.q})
    if not wires or len(wires) > budget.get("max_wires", 10):
        return None
    if any(g.op not in REV | set(PHASE) | {"Z_POW"} for g in gates):
        return None
    size = 1 << len(wires)
    all_ones = (1 << size) - 1
    values = {w: sum(((x >> i) & 1) << x for x in range(size))
              for i, w in enumerate(wires)}
    sites = defaultdict(list)
    for i, g in enumerate(gates):
        q = g.q
        if g.op == "X":
            values[q[0]] ^= all_ones
        elif g.op == "CX":
            values[q[1]] ^= values[q[0]]
        elif g.op == "CCX":
            values[q[2]] ^= values[q[0]] & values[q[1]]
        elif g.op == "SWAP":
            values[q[0]], values[q[1]] = values[q[1]], values[q[0]]
        elif g.op == "CSWAP":
            delta = values[q[0]] & (values[q[1]] ^ values[q[2]])
            values[q[1]] ^= delta
            values[q[2]] ^= delta
        elif g.op in SINGLE:
            sites[(q[0], values[q[0]])].append(i)
    for indices in sites.values():
        if len(indices) < 2:
            continue
        first = indices[0]
        # Pairwise merging permits reducing local cost without creating a
        # new non-Clifford rotation when the sum is Clifford or zero.
        for j in indices[1:]:
            ticks = (phase_ticks(gates[first]) + phase_ticks(gates[j])) % TURN
            replacement = [] if ticks == 0 else [Gate("Z_POW", gates[first].q, ticks)]
            candidate = gates[:first] + replacement + gates[first+1:j] + gates[j+1:]
            if len(candidate) >= len(gates) or cost(candidate) > cost(gates):
                continue
            proof = prove(gates, candidate, max_wires=10)
            if proof["status"] == "EXACT":
                return Proposal(candidate, {
                    "method": "symbolic_boolean_predicate_equality",
                    "merged_sites": [first, j],
                    "basis_states": size,
                    "proof": proof,
                })
    return None
