# N=35 Marrakesh same-job layout A/B

This note records the same-job controls designed to separate physical-layout effects from backend/calibration drift for the frozen eight-bit affine `N=35`, `a=2`, `r=12` benchmark on `ibm_marrakesh`.

Each A/B job submitted four circuits together:

1. legacy recycled
2. legacy wide
3. optimized recycled
4. optimized wide

All circuits used the same mathematical problem, 512 shots, optimization level 3, and the same frozen optimizer JSON. The legacy and optimized pairs each preserved matched initial work-register placement within the pair.

Uniform eight-bit references:

- permissive factor recovery: `12.890625%`
- strict direct-order recovery: `2.34375%` (`12/512` expectation)
- Hellinger fidelity to ideal: `0.2348667`
- TV distance to ideal: `0.8257132`

## A/B run 1

| Circuit | Permissive | Strict direct-order | Hellinger | TV distance |
|---|---:|---:|---:|---:|
| Legacy recycled | 22.2656% (114/512) | 1.3672% (7/512) | 0.2606 | 0.7755 |
| Legacy wide | 13.4766% (69/512) | 1.3672% (7/512) | 0.1897 | 0.8441 |
| Optimized recycled | 33.9844% (174/512) | 3.7109% (19/512) | 0.3908 | 0.6281 |
| Optimized wide | 32.0313% (164/512) | 6.2500% (32/512) | 0.4688 | 0.6438 |

In run 1, optimized placement improved both architectures strongly. Recycled permissive recovery increased by `+11.72` percentage points and strict recovery by `+2.34` points. Wide permissive recovery increased by `+18.55` points and strict recovery by `+4.88` points.

Against the analytic uniform strict baseline, optimized recycled observed `19/512` (`p ≈ 0.0356`) and optimized wide observed `32/512` (`p ≈ 8.4e-7`) under a one-sided fixed-binomial shot-noise model.

## A/B run 2: exact same-job replication

Raw result:

`results/ibm_shor35_layout_ab/ibm_shor35_layout_ab_8b_20260914_082550.json`

| Circuit | Permissive | Strict direct-order | Hellinger | TV distance |
|---|---:|---:|---:|---:|
| Legacy recycled | 20.1172% (103/512) | 2.5391% (13/512) | 0.3093 | 0.7679 |
| Legacy wide | 14.2578% (73/512) | 3.3203% (17/512) | 0.2271 | 0.8132 |
| Optimized recycled | **41.9922% (215/512)** | **6.2500% (32/512)** | **0.5480** | **0.5224** |
| Optimized wide | 16.0156% (82/512) | 2.9297% (15/512) | 0.2487 | 0.8153 |

The second A/B job again shows a large placement effect for the recycled architecture under a single calibration window. Optimized recycled improved over legacy recycled by `+21.875` permissive percentage points and `+3.7109` strict points. Under a simple independent-binomial difference approximation these correspond to about `7.78` and `2.91` standard errors, respectively.

The wide architecture did not reproduce its run-1 placement gain in this calibration window: optimized wide improved permissive recovery by only `+1.76` points and strict recovery changed by `-0.39` points relative to legacy wide.

Within the optimized pair, recycled exceeded wide by `+25.98` permissive percentage points (`9.56` simple difference standard errors) and by `+3.32` strict points (`2.55` simple difference standard errors). Optimized recycled also had much better distribution-level agreement with the ideal reference: Hellinger `0.5480` versus `0.2487`, and TV distance `0.5224` versus `0.8153`.

Against the analytic uniform strict baseline, optimized recycled observed `32/512`, corresponding to a one-sided fixed-binomial tail `p ≈ 8.37e-7`. Optimized wide observed `15/512` (`p ≈ 0.226`). These p-values model shot noise only and do not account for calibration correlations, optimizer selection, or other systematics.

## Two-job descriptive summary

Because the A/B runs were separate QPU jobs, the following pooled values are descriptive rather than a single randomized experiment.

| Circuit | Permissive, two jobs | Strict, two jobs |
|---|---:|---:|
| Legacy recycled | 217/1024 = 21.1914% | 20/1024 = 1.9531% |
| Legacy wide | 142/1024 = 13.8672% | 24/1024 = 2.3438% |
| Optimized recycled | **389/1024 = 37.9883%** | **51/1024 = 4.9805%** |
| Optimized wide | 246/1024 = 24.0234% | 47/1024 = 4.5898% |

Relative to the analytic uniform strict expectation of `24/1024`, the pooled optimized strict counts are above the floor for both architectures. Under the same fixed-binomial shot-noise model, the descriptive tails are approximately `p = 7.6e-7` for optimized recycled and `p = 1.6e-5` for optimized wide. These should not be interpreted as full hardware significance because the two jobs can share calibration and temporal systematics.

## What now replicates

The strongest repeated observations are:

- the legacy recycled circuit has a reproducible broad advantage over legacy wide;
- optimized recycled is substantially better than legacy recycled in both same-job A/B experiments;
- optimized recycled clears the strict uniform floor in both A/B jobs and reaches `32/512` strict recovery in the replication;
- optimized wide is much more variable across calibration windows: it was excellent in run 1 but near its legacy comparator in run 2;
- therefore neither logical width nor nominal CZ count alone predicts the best hardware result.

The second A/B run does **not** support a universal claim that recycled always beats wide. Rather, the two-job pattern strengthens an architecture-by-placement-by-backend interpretation and suggests that the recycled architecture may be more robust to Marrakesh calibration variation than the wide circuit. That robustness interpretation remains a hypothesis requiring additional repeated jobs or a randomized/interleaved design.

The most defensible cross-backend conclusion is now:

> The compiled `N=35`, `a=2`, `r=12` order-finding signal reproduces on a second superconducting backend when hardware-aware placement is used. On Marrakesh, optimized recycled clears the strict uniform-output floor in repeated same-job A/B controls and shows a reproducible placement benefit, while optimized wide is substantially more calibration-sensitive. The recycled-versus-wide ranking is therefore backend- and calibration-dependent rather than universal.

This remains a compiled-orbit hardware benchmark and not a generic scalable Shor implementation.
