# TCT model-derived one-round QPU pilot preflight

Date: 2026-09-21

## Scope

This records the final zero-QPU preflight for a paired IBM Fez hardware pilot of the finite-codebook, model-derived TCT threshold predicate.

The planned hardware comparison is:

1. `uniform_baseline`: Hadamards on the nine parameter qubits followed by measurement.
2. `one_round_grover`: one Grover round using the model-derived TCT threshold predicate followed by measurement.

Both circuits are compiled onto the same frozen physical patch and submitted in the same Sampler job if and only if all preregistered guardrails pass.

This is not fusion-physics validation and cannot establish end-to-end quantum advantage. It is a hardware test of marked-state amplification for this frozen reduced-order finite-codebook search problem.

## Frozen candidate

- backend: `ibm_fez`
- calibration last update: `2026-09-21 06:12:58-07:00`
- patch index: 10
- transpiler seed: 42
- shots per circuit: 1024
- Grover rounds: 1

### Uniform baseline

- CZ: 0
- compiled depth: 4
- touched physical qubits: `[136, 140, 141, 142, 143, 144, 145, 146, 147]`

### One-round candidate

- CZ: 634
- compiled depth: 1,659
- summed current CZ-error exposure `sum p`: 1.295
- independent no-CZ-error proxy: `log10(P) = -0.563`
- calibrated critical-path duration: 51.2 us
- duration / patch median T1: 0.353
- duration / patch median T2: 0.373

The independent-gate product is an engineering proxy only; it is not a predicted circuit fidelity or hardware success probability.

## Guardrails

All preregistered guardrails passed:

- one Grover round only: PASS
- candidate stays on frozen patch: PASS
- baseline stays on frozen patch: PASS
- CZ <= 750: PASS
- summed CZ exposure <= 1.5: PASS
- duration calibration complete: PASS
- duration / median T1 <= 0.5: PASS
- duration / median T2 <= 0.5: PASS

`all_guardrails_pass=True`

## Pre-registered hardware interpretation

The primary measured quantity is the fraction of shots landing in the eight model-derived marked parameter states.

The paired job must be interpreted against the measured uniform baseline from the same job rather than against the ideal 1/64 baseline alone.

Primary evidence of hardware amplification requires:

1. the one-round candidate marked fraction is greater than the paired baseline marked fraction; and
2. the reported two-proportion z statistic is positive and large enough to make ordinary shot noise an implausible explanation. A nominal `z >= 3` will be treated as strong pilot evidence of amplification, while smaller positive values will be reported as suggestive/inconclusive rather than re-thresholded post hoc.

The ideal references are:

- uniform marked fraction: 8 / 512 = 0.015625
- one-round ideal Grover marked fraction: about 0.134827
- ideal amplification over uniform: about 8.63x

A hardware result need not approach the ideal 13.48% to demonstrate amplification; the primary comparison is candidate versus the same-job measured baseline.

## Claim boundaries

- This tests marked-state amplification on hardware for a finite-codebook model-derived predicate.
- It does not validate TCT plasma physics.
- It does not establish an end-to-end speedup over classical evaluation.
- It does not turn the model-specialized predicate into a general reversible numerical objective evaluator.
- Calibration/error products are engineering proxies, not measured fidelity.
