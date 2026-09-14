# N=35 affine hardware-aware placement optimization

This experiment follows the replicated eight-bit affine `N=35`, `a=2`, `r=12` hardware result. The placement search itself used **zero QPU time** and did not alter the frozen replicated baseline.

The optimizer searches calibration-aware connected regions on `ibm_fez`, preserves the same four initial physical work-register qubits between wide and recycled circuits within each matched plan, uses one wide phase site as the recycled MCM ancilla, and transpiles the actual affine circuits across multiple deterministic seeds. Its score is a ranking proxy based on calibrated CZ error, measurement/MCM error, compiled CZ burden, depth, and size; it is **not** a predicted circuit fidelity.

## Recommended matched plan

Optimizer revision: `2026-09-14-shor35-layout-optimizer-v1`

Recommended seed: `8776`

- region: `[142,143,136,141,140,144,145,123,124,125,117,105]`
- shared initial work qubits: `[136,143,141,140]`
- recycled MCM ancilla: `142`
- wide phase sites: `[142,144,145,123,124,125,117,105]`

### Recycled compile

| Metric | Legacy plan, current calibration | Optimized matched plan | Change |
|---|---:|---:|---:|
| CZ gates | 175 | **160** | **-8.57%** |
| Depth | 607 | **572** | **-5.77%** |
| Circuit size | 782 | **728** | **-6.91%** |
| MCM error proxy | 0.43945% | **0.39063%** | **-11.11% relative** |
| Local mean CZ error | 0.25221% | **0.21741%** | **-13.80% relative** |

The compiled recycled circuit remains at 5 logical qubits.

### Wide compile

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

## Hardware result

After the zero-QPU search and an independent transpile-only reproduction of the selected plan, the optimized matched plan was submitted as one IBM Fez job with 512 shots per architecture.

| Metric | Wide optimized | Recycled optimized |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| CZ gates | 362 | **160** |
| Compiled depth | 746 | **572** |
| Permissive factor recovery | 20.1172% | **53.7109%** |
| Strict direct-order recovery | 3.7109% (19/512) | **7.03125% (36/512)** |
| Hellinger fidelity to ideal | 0.2473 | **0.6441** |
| Total-variation distance to ideal | 0.7957 | **0.3947** |
| Zero-phase probability | 0.1953% | **7.03125%** |

The recycled-minus-wide permissive recovery gap was **+33.59375 percentage points**, about **11.88 standard errors** under the repository's simple independent-binomial shot-noise approximation.

### Noise-floor audit

The analytic uniform eight-bit baselines are:

- permissive factor recovery: **12.890625%**;
- strict direct-order recovery: **2.34375%**;
- Hellinger fidelity to the exact order-12 ideal: **0.23487**;
- total-variation distance to the exact order-12 ideal: **0.82571**.

The optimized recycled result therefore remains clearly above random output on both recovery metrics and on both distribution metrics:

- permissive: **53.71% vs 12.89% uniform**;
- strict direct order: **7.03% vs 2.34% uniform**;
- Hellinger: **0.644 vs 0.235 uniform**;
- TV: **0.395 vs 0.826 uniform**.

The optimized wide circuit improves relative to the prior wide placement, as intended for a fairer comparison, but remains much closer to the random reference: **20.12% permissive**, **3.71% strict**, Hellinger **0.247**, TV **0.796**.

For the recycled strict metric, 36 direct-order successes were observed in 512 shots where the uniform model predicts 12 on average. Under a simple fixed-baseline binomial model this corresponds to about **7.0 standard deviations** and a one-sided tail probability of approximately **9.7e-9**. This is a shot-noise-only statistic; it does not model calibration drift, temporal correlations, routing systematics, or selection effects from choosing a placement using calibration data.

## Relation to the frozen baseline

The unmodified 8-bit benchmark produced the following recycled strict-direct results across its first two hardware executions:

- first run: **30/512 = 5.8594%**;
- clean replication: **36/512 = 7.03125%**.

The optimized-layout follow-up again produced **36/512 = 7.03125%**. Thus the hardware-aware placement materially improved the broad distribution quality and permissive factor-recovery rate while preserving, rather than trading away, the strict order-recovery signal.

The corresponding recycled permissive/Hellinger/TV progression was:

- first run: **40.23% / 0.5236 / 0.5723**;
- clean replication: **45.51% / 0.5394 / 0.5489**;
- optimized placement: **53.71% / 0.6441 / 0.3947**.

These runs span different calibration snapshots and the optimized run uses a different physical plan, so pooled shot statistics should be treated as descriptive rather than as one randomized experiment.

## Interpretation

This experiment supports a broader hardware/software co-design result beyond phase-register recycling alone: for this compiled `N=35`, `a=2`, order-12 benchmark, selecting a calibration-aware physical region and routing configuration improved the measured phase distribution substantially while retaining the reduced-width recycled architecture.

It remains a compiled-orbit experiment, not a generic scalable modular multiplier, and should not be interpreted as evidence that cryptographic RSA sizes are tractable on current hardware.
