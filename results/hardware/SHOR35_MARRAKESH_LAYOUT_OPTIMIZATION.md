# N=35 affine Marrakesh layout optimization

After two unoptimized `ibm_marrakesh` runs preserved a broad recycled advantage but failed to reproduce the strict direct-order `r=12` signal, a zero-QPU calibration-aware placement search was performed for the same frozen eight-bit affine `N=35`, `a=2` benchmark.

Optimizer revision: `2026-09-14-shor35-layout-optimizer-v1`

Plan file produced locally:

`results/ibm_shor35_optimizer/shor35_layout_search_8b_20260914_060307.json`

## Recommended matched plan

Transpiler seed: `8776`

Shared initial work qubits: `[17, 7, 5, 4]`  
Recycled ancilla: `6`  
Wide phase sites: `[6, 3, 2, 16, 1, 23, 27, 28]`

### Recycled

| Metric | Legacy Marrakesh plan | Optimized plan | Change |
|---|---:|---:|---:|
| CZ gates | 175 | **160** | **-8.57%** |
| Depth | 607 | **572** | **-5.77%** |
| Circuit size | 782 | **728** | **-6.91%** |
| MCM error proxy | 0.390625% | **0.219727%** | **-43.75% relative** |
| Local mean CZ error | 0.245464% | **0.223474%** | **-8.96% relative** |

### Wide

| Metric | Legacy Marrakesh plan | Optimized plan | Change |
|---|---:|---:|---:|
| CZ gates | 329 | **318** | **-3.34%** |
| Depth | 820 | **777** | **-5.24%** |
| Circuit size | 1347 | 1355 | +0.59% |

The mean requested wide phase-site readout-error proxy improves from about **2.805%** to **1.851%** (about **34.0% lower**). The worst requested phase readout site improves from about **9.30%** to **5.02%**.

### Aggregate ranking proxy

- balanced proxy: `1.866814 -> 1.753902` (**6.05% lower**)
- combined CZ count: `504 -> 478` (**5.16% lower**)
- combined depth: `1427 -> 1349` (**5.47% lower**)

The optimizer therefore found a materially cleaner Marrakesh matched region, especially for the recycled MCM ancilla, while also modestly improving the wide comparator.

## Optimized Marrakesh hardware run 1

The optimized plan was recompiled independently before execution and reproduced the expected resource counts exactly: recycled `160 CZ / depth 572 / size 728`, wide `318 CZ / depth 777 / size 1355`.

With 512 shots per architecture, the first optimized matched hardware run produced:

| Metric | Wide | Recycled |
|---|---:|---:|
| Permissive factor recovery | 14.4531% | **23.2422%** |
| Strict direct-order recovery | 2.1484% (11/512) | **3.1250% (16/512)** |
| Hellinger fidelity to ideal | 0.1790 | **0.2954** |
| TV distance to ideal | 0.8443 | **0.7555** |

The uniform eight-bit references are 12.890625% permissive recovery, 2.34375% strict direct-order recovery, Hellinger 0.23487, and TV distance 0.82571.

The optimized recycled run therefore remained clearly above uniform on the broad/distribution metrics and, unlike the two prior unoptimized Marrakesh runs, moved the strict direct-order rate slightly above the uniform floor: `16/512 = 3.125%` versus `12/512 = 2.34375%` expected from uniform output.

However, this strict excess is small. Under the same fixed-baseline binomial model used elsewhere in the project, `16` or more strict successes out of 512 at the uniform probability has one-sided `p ≈ 0.153` (about `1.17 sigma`). This run alone is not sufficient to claim a strict cross-backend replication.

## Optimized Marrakesh hardware run 2

The same frozen optimized plan was then repeated without changing the mathematical circuit, placement, transpiler seed, phase width, or shot count.

| Metric | Wide | Recycled | Uniform |
|---|---:|---:|---:|
| Permissive factor recovery | 27.7344% (142/512) | **28.3203% (145/512)** | 12.8906% |
| Strict direct-order recovery | **4.2969% (22/512)** | **4.2969% (22/512)** | 2.34375% |
| Hellinger fidelity to ideal | **0.3924** | 0.3608 | 0.2349 |
| TV distance to ideal | 0.6990 | **0.6836** | 0.8257 |

The second optimized run therefore reproduced strict-above-uniform behavior for the recycled circuit and, importantly, also showed the same strict rate for the wide comparator. Under the fixed uniform-binomial reference, `22/512` corresponds to one-sided `p ≈ 0.00549` (about `2.54 sigma`) for either architecture considered in isolation. This is still a shot-noise-only calculation and is not a complete hardware uncertainty model.

The fact that wide improved just as strongly in this repeat means the second run cannot be interpreted as evidence that the optimizer specifically restored strict recovery through recycling. A favorable calibration interval or broader physical-region effect is a plausible explanation and must be controlled directly.

## Two-run optimized descriptive summary

Across the two frozen optimized Marrakesh runs:

- recycled permissive recovery: `264/1024 = 25.78125%`
- wide permissive recovery: `216/1024 = 21.09375%`
- recycled strict recovery: `38/1024 = 3.71094%`
- wide strict recovery: `33/1024 = 3.22266%`
- analytic uniform strict expectation: `24/1024 = 2.34375%`

For the recycled pooled strict count, the fixed-baseline binomial tail is approximately `p = 0.00453` (`~2.61 sigma`). For wide it is approximately `p = 0.0447` (`~1.70 sigma`). These pooled numbers are descriptive only because the runs were separate jobs and hardware calibration/temporal correlations are not modeled by an iid binomial assumption.

For comparison, the two unoptimized Marrakesh runs produced recycled strict counts of only `6/512` and `8/512`, while the optimized runs produced `16/512` and `22/512`. Wide also improved from unoptimized `13/512` and `7/512` to optimized `11/512` and `22/512`.

## Interpretation and next control

The optimized placement is associated with stronger strict-order recovery on Marrakesh, but the second repeat shows that the improvement is not uniquely recycled: the wide comparator improved substantially as well. The clean next experiment is therefore a **same-job layout A/B** containing all four circuits in one hardware submission:

1. legacy recycled,
2. legacy wide,
3. optimized recycled,
4. optimized wide.

Running all four in one job minimizes calibration-window drift and directly tests whether the optimized physical region improves either architecture relative to its legacy placement under the same backend state.

The optimizer ranking is a placement-selection proxy only and is not a predicted fidelity. The two prior unoptimized Marrakesh runs remain preserved as negative/mixed cross-backend controls and are not replaced by the optimized results.
