# Recycled Qubit Register architecture

## Core idea

Treat physical qubits as scarce, recyclable register resources rather than assuming every logical phase/control bit must remain quantum for the duration of a workload.

A hybrid word can be thought of as classical storage plus a small quantum working set, for example `6C2Q`. The classical portion retains measured state and control metadata. The quantum portion is allocated only where coherence, interference, or entanglement is currently useful.

## Execution cycle

1. Load or prepare the quantum working state.
2. Execute the quantum operation that benefits from coherence.
3. Mid-circuit measure selected quantum state into classical storage.
4. Apply low-latency classical feedback.
5. Reset/reuse the physical qubit for the next logical quantum position.
6. Keep quantum state coherent only when recycling would destroy information needed later.

## First benchmark: iterative QPE

Quantum phase estimation is a natural benchmark because its phase register can be implemented either as a conventional wide register or iteratively with a recycled ancilla and classical feed-forward. The repository compares those forms on simulation and IBM hardware.

The benchmark does not assert novelty for iterative or semiclassical QPE itself. The research question is broader: when should a heterogeneous architecture dynamically trade quantum width for measurement/reset/feed-forward cycles, and can a scheduler make that trade profitably on current hardware?

## Shor decomposition and width accounting

For Shor-like order finding, only the phase/control register is recycled. The modular-arithmetic work register and its reversible-arithmetic ancillas remain quantum.

The early width model intentionally excluded arithmetic ancillas equally from both architectures:

- wide: `n` work + `m` phase qubits,
- recycled: `n` work + 1 recycled phase qubit,
- with `m = 2n`, this is `3n` versus `n+1`.

The gate-level benchmark in `simulation/rsa_gate_level_modmul.py` adds a concrete clean-ancilla MCX construction. In that deliberately generic synthesis, a controlled adjacent basis-state swap uses `n-2` reusable clean ancillas. The corresponding simultaneous width is therefore:

- wide: `n + 2n + (n-2) = 4n-2`,
- recycled: `n + 1 + (n-2) = 2n-1`.

That model gives an exact **2x total-width reduction** for the tested 6-9-bit toy-RSA cases. This is the more conservative architecture-level comparison when those arithmetic ancillas are included.

The modular arithmetic itself is not made cheaper merely by recycling the phase register; its Toffoli burden is shared. The principal saving is that the full `2n`-qubit phase register does not have to remain live at once, and the inverse-QFT quantum-quantum interaction network is replaced by measurement/reset plus classical feed-forward.

The current gate synthesis is an exact but generic basis-permutation decomposition, not a state-of-the-art optimized modular multiplier. Different reversible arithmetic constructions can change both ancilla requirements and gate counts, so the scheduler should treat arithmetic implementation as another resource-model choice rather than assuming `n-2` ancillas universally.

## Scheduler objective

A future scheduler can optimize over:

- simultaneous quantum width,
- arithmetic-ancilla demand,
- expected two-qubit gate error,
- mid-circuit measurement error and duration,
- reset latency,
- local versus host feedback latency,
- required coherent lifetime,
- entanglement width / graph structure,
- backend and physical-qubit calibration,
- queue/runtime cost.

The simulation experiments include a learned resource router and entanglement-width stress tests to expose where a narrow recycled register succeeds and where it fails.

## Boundary conditions

Qubit recycling is not equivalent to increasing Hilbert-space dimension. Two qubits still carry a two-qubit coherent state at any instant. Recycling is useful only when the algorithm permits quantum information to be measured, compressed into classical state, or otherwise discarded before the same physical qubit is reused.

For Shor-like algorithms, recycling can reduce the phase/control-register width, but the modular-arithmetic work register and its ancillas remain.
