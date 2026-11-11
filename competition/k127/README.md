# K127: Boolean predicate phase factoring

Hypothesis: nonadjacent Z_POW operations might act on the same Boolean function even when source wires and gate neighborhoods differ. Exact angle combination could reduce the verifier rotation count.

The read-only screen tracks reversible Boolean dataflow, classical bit stores/inverts, conditional measurement resets, and NEG phase operations against the pinned e7eb baseline. The completed XOR/AND expression DAG found 48 distinct normalized predicates at 48 Z_POW sites. All 41 non-Clifford rotations remain; no candidate was emitted.

The reduced ordered BDD follow-up used q21..q0 input order followed by measurement outcomes. It exceeded the 10,000,000-node cap. See results/bdd_equivalence_attempt.json. This is inconclusive and does not prove absence of all equivalent predicates.

Reproduce the completed screen:
    cd ~/quantum-a26-mission
    $HOME/.venvs/kaggle-k001/bin/python competition/k127/k127_symbolic_phase_predicates.py --baseline /home/ubuntu/quantum-a26-check/competition/k098/results/helios_immutable.kmx --output competition/k127/results/dag_phase_predicates.json

No official verifier was run because no candidate was produced.
