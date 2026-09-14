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

## Optimized Marrakesh hardware run

The optimized plan was recompiled independently before execution and reproduced the expected resource counts exactly: recycled `160 CZ / depth 572 / size 728`, wide `318 CZ / depth 777 / size 1355`.

With 512 shots per architecture, the optimized matched hardware run produced:

| Metric | Wide | Recycled |
|---|---:|---:|
| Permissive factor recovery | 14.4531% | **23.2422%** |
| Strict direct-order recovery | 2.1484% (11/512) | **3.1250% (16/512)** |
| Hellinger fidelity to ideal | 0.1790 | **0.2954** |
| TV distance to ideal | 0.8443 | **0.7555** |

The uniform eight-bit references are 12.890625% permissive recovery, 2.34375% strict direct-order recovery, Hellinger 0.23487, and TV distance 0.82571.

The optimized recycled run therefore remained clearly above uniform on the broad/distribution metrics and, unlike the two prior unoptimized Marrakesh runs, moved the strict direct-order rate slightly above the uniform floor: `16/512 = 3.125%` versus `12/512 = 2.34375%` expected from uniform output.

However, this strict excess is small. Under the same fixed-baseline binomial model used elsewhere in the project, `16` or more strict successes out of 512 at the uniform probability has one-sided `p ≈ 0.153` (about `1.17 sigma`). This is not sufficient to claim a strict cross-backend replication.

The two unoptimized Marrakesh recycled strict results were `6/512` and `8/512`; the optimized run produced `16/512`. This is suggestive that physical placement may improve the narrow strict-order metric on Marrakesh, but it requires an independent repeat of the same frozen optimized plan before drawing that conclusion.

The optimizer ranking is a placement-selection proxy only and is not a predicted fidelity. The two prior unoptimized Marrakesh runs remain preserved as negative/mixed cross-backend controls and are not replaced by the optimized result.
