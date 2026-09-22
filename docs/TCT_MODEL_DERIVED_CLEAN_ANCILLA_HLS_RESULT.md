# TCT model-derived clean-ancilla HLS result

Date: 2026-09-22

## Scope

This records the zero-QPU high-level-synthesis comparison for the one-round, finite-codebook, model-derived TCT threshold predicate.

The comparison tested the existing 10-qubit implementation against Qiskit MCX synthesis alternatives, including an 11-qubit extension with one additional clean helper qubit. The helper is only a synthesis resource; the nine-bit parameter distribution is unchanged.

This is a compiler/calibration engineering result, not fusion validation and not an end-to-end quantum-advantage result.

## Semantic check

The 11-qubit extension was verified ideally before routing:

- parameter-distribution max absolute error versus the 10-qubit circuit: `2.776e-17`
- original oracle ancilla `P(1)`: `1.657e-31`
- added helper `P(1)`: `0.0`
- `ideal_width11_equivalent=True`

Thus the extra qubit does not change the intended one-round marked-state distribution under ideal evolution.

## Fully connected screen

Best fully connected results at optimization level 3:

- baseline default 10q: `199 CZ`, depth `757`
- noaux HP24 10q: `523 CZ`, depth `1581`
- noaux V24 10q: `563 CZ`, depth `1651`
- default one-clean 11q: `124 CZ`, depth `525`
- one-clean KG24 11q: `124 CZ`, depth `525`
- one-clean B95 11q: `273 CZ`, depth `963`

The identical default-one-clean and explicit `1_clean_kg24` results show that, for this circuit and Qiskit version, the default HLS path is selecting the same effective one-clean synthesis as KG24.

## Best routed results

Calibration snapshot: `ibm_fez`, last update `2026-09-22 07:00:30-07:00`.

Best 10-qubit default candidate in this snapshot:

- patch 29, seed 42
- `478 CZ`
- depth `1194`
- summed CZ error exposure (`sum p`): `1.081`
- critical path: `36.7 us`
- duration / median T1: `0.248`
- duration / median T2: `0.366`

Best 11-qubit default/KG24 one-clean candidate:

- patch 6, seed 42
- `252 CZ`
- depth `706`
- summed CZ error exposure (`sum p`): `0.681`
- independent no-CZ-error proxy: `log10 = -0.296`
- critical path: `21.1 us`
- duration / median T1: `0.144`
- duration / median T2: `0.207`

The independent no-CZ-error product corresponding to `log10=-0.296` is about 0.506. This remains an engineering proxy, not predicted circuit fidelity.

## Improvement

Relative to the best 10-qubit default candidate in the same calibration snapshot, the clean-ancilla 11-qubit circuit has approximately:

- 47% fewer routed CZ gates (`478 -> 252`)
- 37% lower CZ error exposure (`1.081 -> 0.681`)
- 42% shorter calibrated critical path (`36.7 us -> 21.1 us`)
- substantially lower coherence-time ratios (`T1: 0.248 -> 0.144`, `T2: 0.366 -> 0.207`)

Relative to the first submitted Fez pilot (`634 CZ`, `sum p=1.295`, `51.2 us`), the new candidate has approximately:

- 60% fewer CZ gates
- 47% lower CZ exposure
- 59% shorter calibrated critical path

This crosses the previously stated zero-QPU target of `sum p < 0.8` before considering another QPU attempt.

## Negative alternatives

The no-auxiliary HP24 and V24 methods were substantially worse than the default 10-qubit synthesis after routing. The one-clean B95 implementation was also much worse than the default/KG24 one-clean path.

## Interpretation

The extra clean helper qubit materially changes the hardware-feasibility picture. It reduces both routed gate count and calibrated exposure enough to justify preparing a second guarded hardware pilot, provided a fresh preflight on the actual Fez backend reproduces conservative limits.

Any second pilot should remain paired with a uniform baseline in the same job, preserve the existing marked-state definition and statistical criterion, and refuse submission if live calibration or actual-backend compilation drifts materially from this candidate.

## Boundaries

- The calibration error products are not measured fidelity or success probability.
- The result is tied to this finite codebook, frozen threshold, compiler version, sampled Fez patches, and calibration snapshot.
- Adding one clean helper is a synthesis optimization, not a new search algorithm.
- No claim of fusion-physics validation.
- No claim of practical or asymptotic quantum advantage.
- No QPU job was submitted by this HLS study.
