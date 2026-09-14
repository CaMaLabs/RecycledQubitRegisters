# IBM Marrakesh cross-backend validation: affine N=35, a=2, r=12

This note records the first cross-backend validation of the frozen eight-bit affine `N=35`, `a=2`, `r=12` benchmark on `ibm_marrakesh`.

The benchmark and post-processing were unchanged from the successful IBM Fez baseline. No Marrakesh-specific placement optimization was applied in these two runs. The goal was to test whether the Fez result transferred to a second superconducting backend before introducing a backend-specific optimizer.

## Preflight

The affine encoding self-test passed. `ibm_marrakesh` supported `measure_2` dynamic execution.

The unoptimized Marrakesh transpile produced:

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Depth | 820 | **607** |
| Circuit size | 1347 | **782** |
| CZ gates | 329 | **175** |

The recycled resource counts therefore matched the original Fez baseline exactly, while the wide circuit remained in the same overall complexity range.

## Run 1

Raw result:

`results/ibm_shor35_affine/ibm_shor35_affine_8b_20260914_054918.json`

512 shots per architecture.

| Metric | Wide | Recycled | Uniform |
|---|---:|---:|---:|
| Permissive factor recovery | 16.0156% | **25.0000%** | 12.8906% |
| Strict direct-order recovery | 2.5391% (13/512) | 1.1719% (6/512) | 2.34375% |
| Hellinger fidelity to ideal | 0.2230 | **0.2998** | 0.2349 |
| TV distance to ideal | 0.8276 | **0.7304** | 0.8257 |

The recycled-minus-wide permissive gap was +8.9844 percentage points, about 3.58 standard errors under the simple independent-binomial approximation used elsewhere in the repository.

Interpretation: recycled showed a broad/distribution-level advantage but failed the strict direct-order test. The wide strict result was essentially at the random-output floor.

## Run 2

Raw result:

`results/ibm_shor35_affine/ibm_shor35_affine_8b_20260914_055919.json`

512 shots per architecture.

| Metric | Wide | Recycled | Uniform |
|---|---:|---:|---:|
| Permissive factor recovery | 11.1328% | **22.2656%** | 12.8906% |
| Strict direct-order recovery | 1.3672% (7/512) | 1.5625% (8/512) | 2.34375% |
| Hellinger fidelity to ideal | 0.2051 | **0.2784** | 0.2349 |
| TV distance to ideal | 0.8467 | **0.7639** | 0.8257 |

The recycled-minus-wide permissive gap was +11.1328 percentage points, about 4.83 standard errors under the same simple approximation.

Interpretation: the broad recycled advantage reproduced, while the strict direct-order signal again failed to clear the uniform-output floor for either architecture.

## Two-run descriptive summary

Across the two unoptimized Marrakesh runs, recycled produced 242 permissive factor-recovering outcomes in 1024 shots (23.6328%), compared with 139/1024 (13.5742%) for wide and an analytic uniform expectation of 132/1024 (12.8906%).

For the strict metric, recycled produced 14/1024 (1.3672%) and wide 20/1024 (1.9531%), versus an analytic uniform expectation of 24/1024 (2.34375%). These pooled counts are descriptive only; the hardware shots are not assumed to be independent across jobs or calibration intervals.

## Conclusion

The unoptimized cross-backend test is **mixed** rather than a strict replication of Fez.

What reproduced on Marrakesh:

- the recycled architecture remained substantially narrower than wide;
- recycled permissive factor recovery exceeded the uniform baseline in both runs;
- recycled output was closer to the exact ideal than uniform output by Hellinger fidelity and TV distance in both runs;
- recycled outperformed the matched wide circuit on the broad factor-recovery metric in both runs.

What did not reproduce:

- strict direct-order `r=12` recovery did not clear the uniform-output floor in either Marrakesh run.

Therefore the project should not claim that strict `r=12` recovery is already backend-independent. The next test is a zero-QPU Marrakesh-specific placement/routing optimization followed, if the preflight is favorable, by an optimized matched hardware run. This will test whether the Fez/Marrakesh difference is primarily calibration/topology dependent rather than intrinsic to the recycled architecture.
