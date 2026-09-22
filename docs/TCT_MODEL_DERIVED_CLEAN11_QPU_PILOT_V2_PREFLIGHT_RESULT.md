# TCT model-derived clean11 QPU pilot v2 preflight result

Date: 2026-09-22

## Scope

This records the route-replay preflight for the second IBM Fez hardware pilot of the finite-codebook, model-derived TCT threshold predicate.

The purpose of v2 is to preserve the exact patch-local routing solution selected by the zero-QPU clean-ancilla HLS sweep, then lift that already-native circuit onto the corresponding physical `ibm_fez` qubits without rerouting on the full device.

This is not fusion validation and not an end-to-end quantum-advantage result.

## Frozen candidate

- backend: `ibm_fez`
- calibration last update: `2026-09-22 07:00:30-07:00`
- variant: `default_one_clean_11q`
- patch index: 6
- transpiler seed: 42
- shots per circuit: 1024
- one Grover round
- logical width: 11 qubits (nine parameter qubits, original predicate ancilla, one clean HLS helper)

## Exact route replay

Source route:

- CZ: 252
- depth: 706
- size: 1198

Replayed patch-local route:

- CZ: 252
- depth: 706
- size: 1198

Exact compile-stat reproduction: `True`.

The lifted circuit uses only native operations supported by the authenticated Fez target.

Final measured physical output qubits:

`[97, 106, 87, 108, 110, 118, 129, 109, 105]`

The uniform baseline measures the same nine physical outputs.

## Candidate calibration audit

- CZ: 252
- depth: 706
- summed CZ error exposure (`sum p`): 0.681
- independent no-CZ-error product proxy: `log10 = -0.296`
- calibrated critical path: 22.8 us
- duration / median T1: 0.155
- duration / median T2: 0.223

Calibration error products are engineering proxies, not predicted hardware fidelity.

## Semantic audit

Uniform ideal marked fraction:

`0.015625000`

Transpiled candidate ideal marked fraction:

`0.134826660`

Maximum probability on either unmeasured clean ancilla after ideal native-circuit evolution:

`1.423e-29`

The baseline and candidate measurement maps are complete, the exact transpiled candidate preserves the expected one-round marked-state amplification under ideal evolution, and both unmeasured ancillas return to `|0>` to numerical precision.

## Preregistered guardrails

All pre-submission guardrails passed:

- route exactly reproduced;
- lifted native operations supported by Fez;
- baseline and candidate remain on the frozen physical patch;
- candidate and baseline use the same output physical qubits;
- CZ <= 325;
- CZ sum-p <= 0.8;
- critical-path duration <= 30 us;
- duration / median T1 <= 0.3;
- duration / median T2 <= 0.3;
- complete duration calibration;
- logical and transpiled clean ancillas return to zero;
- transpiled baseline matches uniform ideal probability;
- transpiled candidate matches expected one-round ideal probability;
- complete measurement maps.

`all_guardrails_pass=True`

## Preregistered interpretation

The paired hardware job will compare a uniform baseline with the one-round clean11 candidate in the same job at equal shot count.

Strong pilot evidence of hardware amplification remains:

- candidate marked fraction greater than measured baseline; and
- two-proportion `z >= 3`.

This criterion is frozen before submission and will not be changed after seeing hardware data.

If the second hardware candidate again collapses near the uniform baseline despite this materially shorter, lower-exposure implementation, that will strengthen the evidence that current hardware noise/execution effects erase the Grover interference for this circuit family. It will still not establish a complete microscopic noise diagnosis.

## Comparison with first hardware pilot

First submitted one-round pilot:

- CZ: 634
- sum-p: 1.295
- duration: 51.2 us
- duration/T1: 0.353
- duration/T2: 0.373

V2 clean11 candidate:

- CZ: 252
- sum-p: 0.681
- duration: 22.8 us
- duration/T1: 0.155
- duration/T2: 0.223

Thus the second candidate is materially smaller and shorter than the first failed hardware circuit while preserving the same ideal marked-state amplification target.
