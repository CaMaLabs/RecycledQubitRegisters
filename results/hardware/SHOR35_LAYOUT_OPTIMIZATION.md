# N=35 affine hardware-aware placement optimization

This is a **zero-QPU-cost** placement/routing search performed after the replicated eight-bit affine `N=35`, `a=2`, `r=12` hardware experiment. It does not alter the replicated baseline result.

The optimizer searches calibration-aware connected regions on `ibm_fez`, preserves the same four initial physical work-register qubits between wide and recycled circuits within each matched plan, uses one wide phase site as the recycled MCM ancilla, and transpiles the actual affine circuits across multiple seeds. Its score is a ranking proxy based on calibrated CZ error, measurement/MCM error, compiled CZ burden, depth, and size; it is **not** a predicted circuit fidelity.

## Recommended matched plan

Optimizer revision: `2026-09-14-shor35-layout-optimizer-v1`

Recommended seed: `8776`

- region: `[142,143,136,141,140,144,145,123,124,125,117,105]`
- shared initial work qubits: `[136,143,141,140]`
- recycled MCM ancilla: `142`
- wide phase sites: `[142,144,145,123,124,125,117,105]`

### Recycled

| Metric | Legacy plan, current calibration | Optimized matched plan | Change |
|---|---:|---:|---:|
| CZ gates | 175 | **160** | **-8.57%** |
| Depth | 607 | **572** | **-5.77%** |
| Circuit size | 782 | **728** | **-6.91%** |
| MCM error proxy | 0.43945% | **0.39063%** | **-11.11% relative** |
| Local mean CZ error | 0.25221% | **0.21741%** | **-13.80% relative** |

The compiled recycled circuit remains at 5 logical qubits.

### Wide

| Metric | Legacy plan, current calibration | Optimized matched plan | Change |
|---|---:|---:|---:|
| CZ gates | 357 | 362 | +1.40% |
| Depth | 832 | **746** | **-10.34%** |
| Circuit size | 1447 | 1453 | +0.41% |

The wide phase-site readout proxy improves substantially. The mean requested-site readout error falls from about **2.545%** to **1.039%** (about **59% lower**), while the worst site improves from about **8.41%** to **2.10%**. This is important because the previous matched region contained two unusually poor readout sites.

### Matched aggregate proxy

- balanced ranking proxy: `2.0067 -> 1.6980` (**15.38% lower**);
- combined CZ count: `532 -> 522` (**1.88% lower**);
- combined compiled depth: `1439 -> 1318` (**8.41% lower**).

The optimized plan therefore improves the recycled circuit directly while also giving the wide comparator cleaner readout conditions. This is desirable for a fair controlled hardware comparison rather than simply maximizing the recycled advantage.

## Required experimental order

1. Finish the strict direct-order noise-floor audit of the fresh unmodified replication result.
2. Freeze that replication before changing placement.
3. Recompile the optimizer-selected plan with `ibm_shor35_affine_plan_runner.py --transpile-only` and verify that its resource counts reproduce the optimizer result under the current calibration snapshot.
4. Only then submit a new matched QPU job using the optimized plan.

The optimized experiment is a new follow-up test. It must not replace or overwrite the replicated baseline data.
