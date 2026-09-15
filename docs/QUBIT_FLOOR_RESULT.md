# Qubit-floor result for the N=35 recycled-register path

This result returns the project to its original objective: minimizing simultaneously active qubits while preserving the exact generic full-residue modular semantics used by the current N=35 validation path.

## Result

At eight phase bits, the recycled construction was compiled to the IBM Fez target under a strict-width rule: a candidate only counts if the compiled circuit touches no more physical qubits than were allocated logically.

The best strict seven-qubit result was:

```text
scratch ancillas:       0
allocated logical:      7
touched physical:       7
native CZ:              45,754
compiled depth:         116,578
compiled size:          196,289
profile:                auto
optimization level:     3
transpiler seed:        9401
```

The best strict eight-qubit result was:

```text
scratch ancillas:       1
allocated logical:      8
touched physical:       8
native CZ:              14,390
compiled depth:         31,158
compiled size:          58,682
profile:                auto
optimization level:     3
transpiler seed:        2026
```

Adding one reusable clean ancilla therefore changed the strict recycled circuit by:

```text
CZ ratio 8q / 7q:       0.314508
CZ reduction:           68.55%
depth ratio 8q / 7q:    0.267272
depth reduction:        73.27%
```

This identifies two distinct operating points:

- **7 qubits:** architectural width floor of the current exact full-residue representation.
- **8 qubits:** current practical Pareto knee because one reusable clean ancilla reduces native two-qubit-gate and depth cost dramatically.

## Why seven qubits is the current architectural floor

The current construction represents all N=35 residue states generically and exactly in the work register. An injective binary encoding of 35 distinct values requires at least

```text
ceil(log2(35)) = 6
```

work qubits, because five qubits provide only 32 computational-basis states.

Iterative/recycled QPE requires one phase/control qubit. Therefore, under the present assumptions,

```text
6 work + 1 recycled phase = 7 qubits
```

is a lower bound before optional scratch workspace.

Going below seven qubits would require changing at least one assumption, for example using an orbit-specific/restricted encoding, non-binary hardware, or a different algorithmic representation. Those are separate experiments and would not be the same generic full-residue construction.

## Comparison with the earlier wide construction

At eight phase bits, the recycled construction saves seven phase qubits relative to the wide QPE form. In the one-clean-ancilla comparison, the recycled circuit used eight logical/touched qubits while the wide source circuit allocated fifteen logical qubits and its compilation touched seventeen physical qubits.

Thus register recycling reduced both the source-level width and the actually active mapped-hardware footprint.

## Claim boundary

This is a compiler/resource result for the exact small-N full-register permutation implementation. It is not a QPU runtime/fidelity result and it is not a scalable RSA modular-arithmetic resource estimate.
