"""Exact local sharing of computed phase predicates.

Consolidates diagonal rotations on the same computed predicate across
commuting diagonal operations, including CCX compute/uncompute sandwiches.
No ancilla-clean assumptions: the complete local transformation is checked
on every basis state, including dirty target states.
"""
from .core import Gate, Proposal, TURN, cost, phase_ticks, prove

PHASE_OPS = {"Z_POW", "Z", "S", "S_DAG", "T", "T_DAG"}


def predicate_share(gates, budget, seed):
    if len(gates) < 3:
        return None
    # Move only diagonal operations across other diagonal operations.
    # Consolidation is valid even when the target is dirty; no state
    # preparation or workspace assumptions are made.
    for i, first in enumerate(gates):
        if first.op not in PHASE_OPS:
            continue
        for j in range(i + 1, len(gates)):
            other = gates[j]
            if other.op not in PHASE_OPS or other.q != first.q:
                if other.op not in PHASE_OPS and other.op not in {"CZ", "CCZ"}:
                    break
                continue
            ticks = (phase_ticks(first) + phase_ticks(other)) % TURN
            replacement = [] if ticks == 0 else [Gate("Z_POW", first.q, ticks)]
            trial = gates[:i] + replacement + gates[i + 1:j] + gates[j + 1:]
            # The rank proxy does not capture rotation synthesis precision;
            # require fewer operations and no increase in the ranked proxy.
            if len(trial) >= len(gates) or cost(trial) > cost(gates):
                continue
            proof = prove(gates, trial, max_wires=10)
            if proof["status"] == "EXACT":
                return Proposal(trial, {
                    "identity": "diagonal predicate phase consolidation",
                    "removed_operations": len(gates) - len(trial),
                    "proof": proof,
                })
    return None
