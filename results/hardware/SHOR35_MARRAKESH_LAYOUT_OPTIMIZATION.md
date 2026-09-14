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

The optimizer therefore found a materially cleaner Marrakesh matched region, especially for the recycled MCM ancilla, while also modestly improving the wide comparator. This is sufficient to justify a follow-up optimized Marrakesh hardware run.

The optimizer ranking is a placement-selection proxy only and is not a predicted fidelity. The two prior unoptimized Marrakesh runs remain preserved as negative/mixed cross-backend controls and must not be replaced by the optimized result.
