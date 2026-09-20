# TCT grid-factored shift oracle — Fez calibration-aware feasibility result

Date: 2026-09-20

## Scope

This records a zero-QPU calibration-aware engineering audit of the validated six-round, 25-qubit grid-factored TCT coherent-arithmetic oracle on the best sampled Fez Qiskit-auto routing patch from the exhaustive seed-314159 routing study.

The audit rebuilt the same circuit, reconstructed Fez patch 4, recompiled with seed 8776, mapped local patch qubits back onto the authenticated `ibm_fez` physical qubits, and read current `Target` instruction errors/durations plus qubit T1/T2 metadata. No Sampler or QPU job was used.

Calibration snapshot:

- backend: `ibm_fez`
- calibration last update: `2026-09-20 12:35:57-07:00`
- patch: 4
- transpiler seed: 8776
- logical width: 25
- Grover rounds: 6
- routed reference: 121,320 CZ / depth 247,438
- calibration-audit recompile: 121,320 CZ / depth 247,438
- exact compiler reproduction: yes

## CZ calibration exposure

- CZ count: 121,320
- calibration coverage: 100%
- mean current target-reported CZ error over executed CZ operations: 0.0797549071
- sum of per-operation CZ error probabilities: 9,675.87
- independent-gate no-error product proxy: `log10 = -135371.463`

The independent-gate product is not a physical fidelity prediction. It ignores correlated noise, coherent cancellation, crosstalk structure, leakage, mitigation, dynamical decoupling, and drift. Its useful role here is only to show that the gate-error exposure is overwhelmingly large under the current calibration.

## All calibrated gate exposure

- calibrated non-measure gate operations: 514,768
- error-property coverage: 100%
- sum of target-reported per-operation error probabilities: 9,788.26
- independent-gate no-error proxy: `log10 = -135420.292`

The difference from the CZ-only exposure is small relative to the total, so the entangling-gate burden dominates the simple error-exposure proxy.

## Timing and coherence context

- calibrated critical-path duration: 0.0070124 s = 7.0124 ms
- duration-property coverage: 100%
- median T1 on the physical patch: 0.000115921 s = 115.9 us
- median T2 on the physical patch: 0.0000921098 s = 92.1 us
- circuit duration / median T1: 60.49
- circuit duration / median T2: 76.13

This is an especially strong feasibility boundary because it does not depend on multiplying thousands of nominal gate-error probabilities. The scheduled critical path is tens of coherence times long on the current patch.

## Final nine-parameter-bit readout context

Final physical parameter qubits:

`[106, 104, 117, 107, 105, 116, 121, 122, 100]`

- mean readout error: 0.0106201
- independent all-nine-correct readout proxy: `log10 = -0.0417555`
- corresponding product probability: about 0.9083

Readout is therefore not the dominant bottleneck in this audit. The dominant barriers are coherent circuit duration and two-qubit gate exposure.

## Interpretation

The routed coherent-arithmetic oracle is not a sensible raw-QPU target on this Fez calibration. The result should not be interpreted as a claim that the algorithm is mathematically invalid; it is a hardware-feasibility result for this circuit realization and calibration snapshot.

The correct next step is not to spend limited QPU runtime. Instead, audit all sampled Fez patches under the same live calibration to determine whether the topology-optimal patch happens to occupy unusually poor calibrated edges. If another patch materially improves calibration-weighted exposure, that can motivate a calibration-aware placement objective. If all sampled patches remain far outside coherence/error budgets, the conclusion is that deeper circuit-architecture reduction or fault-tolerant treatment is required rather than placement tuning.

## Boundaries

- Zero QPU jobs.
- Current calibration snapshot only; calibration values drift.
- `InstructionProperties.error` values are engineering metadata, not an end-to-end circuit fidelity model.
- Independent error products are deliberately labeled proxies.
- No crosstalk, leakage, coherent-error, DD, pulse-level, mitigation, or correlated-noise model.
- Reduced-order TCT objective only.
- No fusion-physics validation.
- No end-to-end quantum-speedup claim.
