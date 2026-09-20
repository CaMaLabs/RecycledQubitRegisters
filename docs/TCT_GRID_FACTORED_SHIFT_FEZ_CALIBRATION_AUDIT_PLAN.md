# TCT grid-factored shift Fez calibration-aware audit plan

Date: 2026-09-20

## Frozen input

Use the validated six-round, 25-qubit grid-factored coherent-arithmetic oracle and the exhaustive seed-314159 routing artifact. The Fez sampled optimum for Qiskit automatic layout is patch 4 at 121,320 CZ and depth 247,438.

This audit does not change the arithmetic encoding, Grover round count, routing patch, or placement objective. It reads current IBM Fez calibration metadata only after the routing choice has been frozen.

## Measurements

The audit rebuilds the same exact-width patch and compiler seed recorded in the exhaustive routing JSON, maps the compiled local wires back to the patch's real Fez physical-qubit IDs, and records:

- current calibrated CZ error and duration on every used physical edge;
- per-gate calibrated error exposure where Target metadata is available;
- `sum(p)` as the expected count of independent per-operation error events;
- `sum(log(1-p))`, reported as `log10` of an independent no-error product proxy;
- an ASAP critical-path duration from calibrated instruction durations;
- T1/T2 statistics for the 25 physical qubits and circuit-duration/coherence ratios;
- final nine parameter-bit readout error, when Qiskit's final layout can be recovered.

The compile is checked against the frozen routing result. A mismatch is reported rather than silently treated as the same circuit.

## Interpretation boundaries

The independent error product is not a circuit-success or fidelity prediction. It ignores correlated noise, coherent error, crosstalk, leakage, calibration drift during execution, pulse-level scheduling, dynamical decoupling, mitigation and fault tolerance.

The duration is a calibrated-gate ASAP estimate, not a guaranteed wall-clock execution time.

This is a zero-QPU metadata/compiler analysis. No Sampler is instantiated and no QPU job is submitted.

The TCT objective remains the frozen reduced-order, classification-exact transformed arithmetic proxy. This audit is not fusion-physics validation and is not evidence of end-to-end quantum advantage.
