# TCT model-derived clean11 QPU pilot v2 result

Date: 2026-09-22

## Scope

This records the second IBM Fez hardware pilot of the finite-codebook, model-derived TCT threshold predicate. The pilot used the exact patch-local 11-qubit clean-ancilla route selected by the zero-QPU HLS study and lifted that native route onto the authenticated Fez physical qubits without rerouting.

This is a marked-state amplification experiment only. It is not fusion validation and not an end-to-end quantum-advantage result.

## Frozen preflight

Backend: `ibm_fez`

Calibration last update: `2026-09-22 07:00:30-07:00`

Frozen implementation:

- variant: `default_one_clean_11q`
- patch: 6
- transpiler seed: 42
- shots per circuit: 1,024
- source route exactly reproduced: `252 CZ / depth 706 / size 1198`
- candidate CZ error exposure (`sum p`): `0.681`
- independent no-CZ-error proxy: `log10 = -0.296`
- calibrated critical path: `22.8 us`
- duration / median T1: `0.155`
- duration / median T2: `0.223`
- ideal transpiled marked-state probability: `0.134826660`
- maximum ideal unmeasured-ancilla `P(1)`: `1.423e-29`
- baseline and candidate used the same nine output physical qubits

Every preregistered guardrail passed before submission.

## Hardware result

IBM Runtime job ID:

`dapeger18flc739m5050`

Observed marked-state counts:

- matched-output uniform baseline: `22 / 1024 = 0.0214844`
- one-round clean11 candidate: `9 / 1024 = 0.0087891`
- absolute candidate-minus-baseline difference: `-0.0126953`
- candidate / baseline marked-fraction ratio: `0.4091`
- two-proportion z approximation: `-2.3527`

The preregistered strong-amplification criterion was candidate marked fraction greater than baseline with `z >= 3`.

That criterion was **not met**. The observed direction was opposite the intended amplification.

## Comparison with ideal behavior

Uniform ideal marked-state probability:

`8 / 512 = 0.015625`

One-round ideal Grover marked-state probability:

`0.134826660`

Thus the ideal candidate should produce about `138` marked shots out of 1,024 on average. The hardware candidate produced only `9`.

Under an ideal binomial model with `p = 0.134826660`, the probability of observing 9 or fewer marked shots in 1,024 trials is approximately `7.4e-51`. This is only a descriptive incompatibility-with-ideal calculation; it is not a hardware noise model.

The baseline value, `22/1024`, is above but still statistically plausible under the uniform `p=1/64` model (one-sided probability of 22 or more is about `0.088`).

## Interpretation

The second hardware run again failed to show Grover marked-state amplification. It did so despite a substantially smaller and shorter circuit than the first pilot and despite exact ideal-transpiled semantic verification before submission.

This run removes several previously plausible implementation explanations:

- the selected patch-local route was reproduced exactly;
- the lifted native operations were supported by Fez;
- the candidate stayed on the frozen physical patch;
- the baseline and candidate used the same nine measured physical qubits;
- measurement mapping was complete;
- the exact lifted candidate preserved the intended `0.134826660` marked probability under ideal statevector evolution;
- both unmeasured ancillas returned to `|0>` ideally.

Therefore the result is consistent with hardware execution errors disrupting the coherent amplitude-amplification interference. The data do **not** identify a unique physical mechanism: coherent over/under-rotation, two-qubit gate error, crosstalk, leakage, phase drift, decoherence, and other effects remain possible.

The calibration `sum p` and independent no-error product were engineering proxies and clearly did not predict usable Grover interference in this run.

## Decision boundary

Do not submit another Grover QPU job merely by relaxing the existing guardrails. Before additional hardware spending, analyze the full saved state-count distributions and seek a substantially different physical implementation or a much larger structural gate reduction.

## Claim boundaries

- One job, one backend calibration snapshot.
- No claim that the observed suppression is caused by a specific hardware error mechanism.
- No fusion-physics validation.
- No practical or asymptotic quantum-advantage claim.
- No post-hoc change to the preregistered positive-amplification criterion.
