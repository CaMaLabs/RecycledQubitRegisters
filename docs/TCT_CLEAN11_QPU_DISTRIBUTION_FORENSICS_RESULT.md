# TCT clean11 QPU distribution forensics result

Date: 2026-09-22

## Scope

This records the zero-QPU distribution-level follow-up to the second IBM Fez clean11 hardware pilot (`dapeger18flc739m5050`). The hardware pilot used the exact replayed 252-CZ route and a matched-output uniform baseline on the same nine measured physical qubits.

This analysis is descriptive. It does not fit or identify a unique hardware noise model.

## Hardware recap

- baseline marked: `22 / 1024 = 0.021484`
- clean11 candidate marked: `9 / 1024 = 0.008789`
- candidate minus baseline: `-0.012695`
- two-proportion z approximation: `-2.3527`
- ideal one-round marked probability: `0.134826660`
- ideal-binomial lower-tail probability for 9 or fewer marked hits: `7.422e-51` (`log10 = -50.129`)

The preregistered positive-amplification criterion was not met. The observed candidate is decisively incompatible with ideal one-round behavior, but the negative candidate-minus-baseline difference was not itself preregistered as an anti-amplification significance test.

## Distribution structure

The marked set shares five necessary bit constraints: `q1=1`, `q2=1`, `q3=1`, `q7=0`, and `q8=0`.

Observed probability of satisfying all five common constraints:

- baseline: `0.032227`
- candidate: `0.022461`
- exact uniform expectation: `0.031250`

Thus the baseline is close to the uniform expectation, while the candidate under-populates the common marked subspace.

The candidate-minus-baseline one-bit marginal shifts were:

`[+0.046875, -0.041016, -0.030273, -0.071289, -0.014648, +0.017578, -0.037109, +0.014648, +0.005859]`

For all five common marked constraints, the observed marginal shift is in the direction *away* from satisfying that constraint:

- `q1=1`: `P(1)` decreases
- `q2=1`: `P(1)` decreases
- `q3=1`: `P(1)` decreases
- `q7=0`: `P(1)` increases
- `q8=0`: `P(1)` increases

This directional pattern is notable but the bit marginals are correlated and should not be treated as five independent statistical tests.

## Distance from the marked set

Nearest-marked Hamming-distance mass:

- baseline: `[0.021484, 0.093750, 0.213867, 0.304688, 0.223633, 0.115234, 0.025391, 0.001953, 0, 0]`
- candidate: `[0.008789, 0.079102, 0.219727, 0.297852, 0.236328, 0.128906, 0.024414, 0.004883, 0, 0]`

The exact-marked plus distance-1 neighborhood drops from `0.115234` to `0.087891`. The displaced mass reappears mainly at larger Hamming distances rather than simply concentrating in adjacent marked states.

## Interpretation

A simple convex mixture of the ideal Grover distribution with the uniform distribution cannot explain the observed marked fraction: such a depolarizing interpolation can only move the ideal marked probability (`0.134826660`) toward the uniform value (`0.015625`), whereas the observed candidate (`0.008789`) lies below uniform. Therefore the second-run failure is not well described as mere global uniformization.

The distribution also shows structured bit-direction changes away from the common marked constraints. This is consistent with a circuit-specific coherent or non-unital distortion, correlated gate errors, crosstalk, or another structured hardware effect, but the data do not identify which mechanism is responsible.

## Boundaries

- 1,024 shots over 512 states make full-distribution TV/JS statistics sampling-noise sensitive.
- The common-bit and Hamming-shell aggregates are more interpretable than individual-state frequencies but still finite-shot observations.
- The calibration `sum_p` and independent no-error product are engineering proxies, not fidelity models.
- No fusion-physics validation or end-to-end quantum-advantage claim follows from this hardware experiment.
- No further QPU run is justified until the physical-qubit / route structure is compared against the observed marginal displacement.
