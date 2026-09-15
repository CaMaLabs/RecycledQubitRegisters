# Strict 7-qubit no-auxiliary MCX result

Date: 2026-09-15
Backend target: `ibm_fez`
QPU jobs submitted: 0

## Question

Can Qiskit's zero-ancilla `noaux_hp24` MCX synthesis materially reduce the native cost of the strict seven-qubit recycled N=35 circuit without borrowing an eighth physical qubit?

## Result

Best strict seven-qubit result:

- profile: `noaux_hp24`
- optimization level: 3
- transpiler seed: 9401
- logical qubits: 7
- touched compiled qubits: 7
- native CZ: 45,750
- compiled depth: 116,470
- compiled size: 196,299

Previous best strict seven-qubit result:

- native CZ: 45,754
- compiled depth: 116,578

Improvement:

- CZ: 4 gates, or about 0.0087%
- depth: 108 layers, or about 0.0926%

`auto` and `default` produced the same best native result as `noaux_hp24`, while `noaux_v24` remained worse at this width.

## Interpretation

The strict seven-qubit architecture appears synthesis-limited rather than profile-selection-limited. The newer zero-ancilla MCX synthesis does not materially close the cost gap to the eight-qubit one-clean-ancilla circuit.

The current resource picture is therefore:

- 7 qubits: hard width floor for exact generic full-residue N=35 encoding plus one recycled phase qubit.
- 8 qubits: practical Pareto knee; one reusable clean ancilla cuts native CZ and depth dramatically.

The next experiment should stop optimizing MCX profiles and instead measure scaling with phase precision while holding the recycled physical width fixed at eight qubits.

## Scope boundary

This result uses exact small-N full-register permutation synthesis. It is a qubit-recycling/compiler resource experiment, not scalable modular arithmetic and not an RSA-scale resource estimate.
