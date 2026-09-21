# TCT model-derived one-round QPU pilot result

Date: 2026-09-21

## Scope

This records the first paired IBM Fez hardware pilot of the finite-codebook, model-derived TCT threshold predicate.

The experiment compared two circuits in the same QPU job, each with 1,024 shots:

1. `uniform_baseline`: Hadamards on the nine parameter qubits followed by measurement;
2. `one_round_grover`: one Grover round using the model-derived TCT threshold predicate followed by measurement.

The predicate was constructed from the reduced-order TCT loss formula, fixed-point threshold, and finite parameter codebooks. It was not constructed from the prelisted eight marked states.

This is not fusion validation and not an end-to-end quantum-advantage result.

## Frozen preflight

Backend: `ibm_fez`

Calibration last update before submission: `2026-09-21 06:12:58-07:00`

Frozen placement / compiler settings:

- patch: 10
- transpiler seed: 42
- shots per circuit: 1,024
- one Grover round only

Candidate preflight:

- CZ: 634
- depth: 1,659
- summed CZ error exposure (`sum p`): 1.295
- independent no-CZ-error product proxy: `log10 = -0.563`
- calibrated critical path: 51.2 us
- duration / median T1: 0.353
- duration / median T2: 0.373

Every preregistered submission guardrail passed.

## Hardware result

IBM Runtime job ID:

`daoje8gpqrnc739a3jn0`

Observed marked-state counts:

- uniform baseline: `17 / 1024 = 0.0166016`
- one-round Grover candidate: `19 / 1024 = 0.0185547`
- absolute difference: `0.0019531`
- candidate / baseline marked-fraction ratio: `1.11765`
- two-proportion z approximation: `0.3363`

Preregistered criterion for strong pilot evidence of amplification was candidate marked fraction greater than baseline with `z >= 3`.

That criterion was **not met**.

## Comparison with ideal behavior

The search register has 512 basis states and eight marked states.

Uniform ideal marked-state probability:

`8 / 512 = 0.015625`

One-round ideal Grover marked-state probability:

`0.134827`

Thus the ideal one-round amplification factor is about:

`0.134827 / 0.015625 = 8.63x`

The measured amplification factor was only:

`0.0185547 / 0.0166016 = 1.12x`

The baseline result is close to the uniform ideal value, whereas the candidate result is close to baseline and far below the ideal one-round value.

Approximate 95% Wilson intervals for the two measured marked fractions are:

- baseline: about 1.04% to 2.64%
- candidate: about 1.19% to 2.88%

These intervals overlap strongly.

## Interpretation

This hardware run does **not** demonstrate Grover amplification for the one-round model-derived TCT predicate on the tested Fez calibration and compiled circuit.

The negative result does not invalidate the model-derived Boolean predicate, whose ideal and compiler-level behavior were already verified separately. The next necessary distinction is whether:

1. the exact transpiled candidate still produces the expected 13.48% marked probability under ideal statevector evolution, in which case the hardware result is consistent with noise / execution effects erasing the interference; or
2. there is a compiler, layout, measurement-order, or state-decoding issue between the logical predicate and the submitted circuit.

A zero-QPU postmortem should therefore recompile the exact frozen patch/seed, reconstruct a compact ideal circuit from the transpiled native operations, recover the classical measurement map, and verify the marked-state probability and clean-ancilla return probability before any additional QPU spending.

## Boundaries

- This is one hardware job on one backend calibration snapshot.
- The two-proportion z statistic is a simple pilot statistic, not a complete noise model.
- `sum p` and independent no-error products are engineering proxies, not measured fidelity.
- No claim of fusion-physics validation.
- No claim of practical or asymptotic quantum advantage.
- No post-hoc change to the preregistered `z >= 3` pilot criterion.
