# IBM Marrakesh cross-backend validation: affine N=35, a=2, r=12

This note records the cross-backend validation of the frozen eight-bit affine `N=35`, `a=2`, `r=12` benchmark on `ibm_marrakesh`.

The benchmark and post-processing were unchanged from the successful IBM Fez baseline. Two unoptimized Marrakesh runs were performed first, followed by a frozen backend-specific placement optimization and two optimized repeats.

## Unoptimized preflight

The affine encoding self-test passed. `ibm_marrakesh` supported `measure_2` dynamic execution.

The unoptimized Marrakesh transpile produced:

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Depth | 820 | **607** |
| Circuit size | 1347 | **782** |
| CZ gates | 329 | **175** |

The recycled resource counts therefore matched the original Fez baseline exactly, while the wide circuit remained in the same overall complexity range.

## Unoptimized run 1

Raw result:

`results/ibm_shor35_affine/ibm_shor35_affine_8b_20260914_054918.json`

512 shots per architecture.

| Metric | Wide | Recycled | Uniform |
|---|---:|---:|---:|
| Permissive factor recovery | 16.0156% | **25.0000%** | 12.8906% |
| Strict direct-order recovery | 2.5391% (13/512) | 1.1719% (6/512) | 2.34375% |
| Hellinger fidelity to ideal | 0.2230 | **0.2998** | 0.2349 |
| TV distance to ideal | 0.8276 | **0.7304** | 0.8257 |

Interpretation: recycled showed a broad/distribution-level advantage but failed the strict direct-order test. Wide strict was essentially at the random-output floor.

## Unoptimized run 2

Raw result:

`results/ibm_shor35_affine/ibm_shor35_affine_8b_20260914_055919.json`

512 shots per architecture.

| Metric | Wide | Recycled | Uniform |
|---|---:|---:|---:|
| Permissive factor recovery | 11.1328% | **22.2656%** | 12.8906% |
| Strict direct-order recovery | 1.3672% (7/512) | 1.5625% (8/512) | 2.34375% |
| Hellinger fidelity to ideal | 0.2051 | **0.2784** | 0.2349 |
| TV distance to ideal | 0.8467 | **0.7639** | 0.8257 |

Interpretation: the broad recycled advantage reproduced, while the strict direct-order signal again failed to clear the uniform-output floor for either architecture.

## Two-run unoptimized descriptive summary

Across the two unoptimized Marrakesh runs, recycled produced 242 permissive factor-recovering outcomes in 1024 shots (23.6328%), compared with 139/1024 (13.5742%) for wide and an analytic uniform expectation of 132/1024 (12.8906%).

For the strict metric, recycled produced 14/1024 (1.3672%) and wide 20/1024 (1.9531%), versus an analytic uniform expectation of 24/1024 (2.34375%). These pooled counts are descriptive only.

## Marrakesh-specific placement optimization

A zero-QPU calibration-aware search then selected a frozen matched region with:

- recycled: `160 CZ`, depth `572`, size `728`
- wide: `318 CZ`, depth `777`, size `1355`
- recycled MCM error proxy improved from `0.390625%` to `0.219727%`

The full optimizer record is in `results/hardware/SHOR35_MARRAKESH_LAYOUT_OPTIMIZATION.md`.

## Optimized run 1

| Metric | Wide | Recycled | Uniform |
|---|---:|---:|---:|
| Permissive factor recovery | 14.4531% | **23.2422%** | 12.8906% |
| Strict direct-order recovery | 2.1484% (11/512) | **3.1250% (16/512)** | 2.34375% |
| Hellinger fidelity to ideal | 0.1790 | **0.2954** | 0.2349 |
| TV distance to ideal | 0.8443 | **0.7555** | 0.8257 |

The recycled strict rate moved above uniform, but only weakly (`16/512` vs `12/512`; fixed-baseline one-sided `p ≈ 0.153`).

## Optimized run 2

| Metric | Wide | Recycled | Uniform |
|---|---:|---:|---:|
| Permissive factor recovery | 27.7344% | **28.3203%** | 12.8906% |
| Strict direct-order recovery | **4.2969% (22/512)** | **4.2969% (22/512)** | 2.34375% |
| Hellinger fidelity to ideal | **0.3924** | 0.3608 | 0.2349 |
| TV distance to ideal | 0.6990 | **0.6836** | 0.8257 |

In this repeat, both optimized circuits cleared the strict uniform floor and both moved substantially closer to the ideal distribution. The wide circuit equaled recycled on the strict metric and exceeded it in Hellinger fidelity, while recycled retained slightly better TV distance and permissive recovery.

## Two-run optimized descriptive summary

Across the two frozen optimized runs:

- recycled permissive: `264/1024 = 25.78125%`
- wide permissive: `216/1024 = 21.09375%`
- recycled strict: `38/1024 = 3.71094%`
- wide strict: `33/1024 = 3.22266%`
- uniform strict expectation: `24/1024 = 2.34375%`

The fixed uniform-binomial tail for recycled `38/1024` is approximately `p = 0.00453` (`~2.61 sigma`); for wide `33/1024`, `p ≈ 0.0447` (`~1.70 sigma`). These are shot-noise-only descriptive calculations and do not model temporal calibration correlations.

## Current conclusion

The Marrakesh cross-backend result is stronger than the initial two-run test but still does **not** establish a backend-independent recycled-specific strict advantage.

What is supported:

- recycled remains substantially narrower than wide;
- recycled broad/distribution signal was above uniform in every Marrakesh run;
- backend-specific optimized placement is associated with higher strict-order recovery than the earlier unoptimized runs;
- in the second optimized repeat, both recycled and wide improved strongly, showing that calibration state or region quality can affect both architectures.

What is not yet isolated:

- whether the optimized region itself caused the strict improvement, versus temporal backend drift;
- whether recycled has a strict advantage over wide on Marrakesh under the same instantaneous calibration state.

The next control is a four-circuit **same-job layout A/B**: legacy recycled, legacy wide, optimized recycled, optimized wide. This removes most calibration-window drift from the placement comparison.
