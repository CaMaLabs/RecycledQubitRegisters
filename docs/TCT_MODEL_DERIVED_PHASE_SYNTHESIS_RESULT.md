# TCT model-derived phase-synthesis challenger result

Date: 2026-09-21

## Scope

This records a zero-QPU compiler/calibration comparison of two exactly equivalent one-round realizations of the finite-codebook, model-derived TCT threshold predicate on IBM Fez connectivity:

- `mcx_h`: the existing `H -> MCX -> H` phase-reflection construction;
- `mcphase`: an explicit `MCPhaseGate(pi)` construction.

The statevector equivalence check passed before routing. This remains a compiler/hardware-mapping study of the frozen reduced-order predicate. It is not fusion validation and not an end-to-end quantum-advantage result.

## Calibration snapshot

Backend: `ibm_fez`

Calibration last update: `2026-09-21 08:43:57-07:00`

Logical width: 10 qubits

Patches compared: `[6, 7, 14, 17, 29, 31, 36, 47]`

Transpiler seeds: `[8776, 2026, 9401, 42, 1337, 271828, 118021]`

Optimization level: 3

## Best results

### Existing MCX/H construction

Best by CZ-error exposure:

- patch: 36
- transpiler seed: 2026
- CZ: 462
- depth: 1,173
- summed CZ error exposure (`sum p`): 1.102
- independent no-CZ-error proxy: `log10 = -0.479`
- calibrated critical path: 36.0 us
- duration / median T1: 0.249
- duration / median T2: 0.470

### Explicit MCPhase construction

Best by CZ-error exposure:

- patch: 31
- transpiler seed: 271828
- CZ: 897
- depth: 2,623
- summed CZ error exposure (`sum p`): 2.031
- calibrated critical path: 77.0 us

## Relative cost

Against the best `mcx_h` result, the best `mcphase` result had:

- CZ ratio: `1.941558`
- summed CZ exposure ratio: `1.843506`
- duration ratio: `2.141157`

Thus the explicit multi-controlled-phase construction is decisively worse on the tested Fez topology/calibration and should not replace the current MCX/H realization.

## Interpretation

The 462-CZ MCX/H circuit remains the strongest one-round implementation found so far. The result suggests that simply replacing `H -> MCX -> H` with a generic `MCPhaseGate(pi)` does not address the dominant physical cost.

The next synthesis question is whether a small logical-width increase can lower the multi-controlled-X cost. Qiskit exposes MCX-specific high-level-synthesis plugins that can exploit clean ancillary qubits, including one-clean-ancilla constructions. A zero-QPU challenger should therefore compare the current 10-qubit implementation with an 11-qubit circuit containing one additional clean helper qubit, while verifying exact statevector equivalence before routing.

## Boundaries

- Statevector equivalence establishes ideal logical equivalence only.
- `sum p` and independent no-error products are engineering proxies, not measured circuit fidelity.
- Best placement means best among the sampled patches/seeds in this experiment.
- No QPU job was submitted.
- No fusion-physics validation claim.
- No practical or asymptotic quantum-advantage claim.
