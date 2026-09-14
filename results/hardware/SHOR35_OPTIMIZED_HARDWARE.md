# Optimized IBM Fez affine N=35 hardware result

This follow-up experiment uses the same compiled affine `N=35`, `a=2`, `r=12` benchmark as the frozen eight-bit baseline, but replaces the original physical placement with the calibration-aware matched plan selected by `hardware/ibm_shor35_layout_optimizer.py`.

The optimizer search itself used no QPU time. The selected plan was independently recompiled with `hardware/ibm_shor35_affine_plan_runner.py --transpile-only` before hardware execution, and the transpiled resources reproduced the optimizer output exactly.

## Optimized matched resources

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Compiled depth | 746 | **572** |
| CZ gates | 362 | **160** |
| Circuit size | 1453 | **728** |

The selected plan keeps the same four initial physical work-register qubits between architectures and uses one of the wide phase sites as the recycled MCM ancilla.

## Hardware result

Matched same-job run, 512 shots per architecture:

| Metric | Wide | Recycled |
|---|---:|---:|
| Permissive factor recovery | 20.1172% | **53.7109%** |
| Strict direct-order recovery | 3.7109% (19/512) | **7.03125% (36/512)** |
| Hellinger fidelity to ideal | 0.2473 | **0.6441** |
| Total-variation distance to ideal | 0.7957 | **0.3947** |
| Zero-phase probability | 0.1953% | **7.03125%** |

The recycled-minus-wide permissive recovery difference was **+33.59375 percentage points**, about **11.88 standard errors** under the repository's simple independent-binomial shot-noise approximation.

## Uniform-noise audit

For uniform random 8-bit output under the same post-processing:

- permissive factor recovery = **12.890625%**;
- strict direct-order recovery = **2.34375%**;
- Hellinger fidelity to the exact order-12 ideal = **0.23487**;
- total-variation distance to the ideal = **0.82571**.

Recycled therefore clears the random-output baseline on all four primary signal metrics. Wide improves under the cleaner physical placement, as intended, but remains much closer to the uniform reference.

For recycled strict direct-order recovery, 36 successes were observed in 512 shots where the uniform model predicts 12 on average. Under a fixed-baseline binomial model this corresponds to about **7.0 standard deviations**, one-sided `p ≈ 9.7e-9`. This is a shot-noise-only significance estimate and does not account for calibration drift, hardware correlations, routing systematics, or placement-selection effects.

## Reproducibility progression

The strict recycled direct-order result across the three 8-bit hardware executions is:

- initial baseline: **30/512 = 5.8594%**;
- clean unmodified replication: **36/512 = 7.03125%**;
- optimized matched placement: **36/512 = 7.03125%**.

The corresponding broad distribution progression is:

| Run | Permissive recovery | Hellinger | TV distance |
|---|---:|---:|---:|
| Initial baseline | 40.23% | 0.5236 | 0.5723 |
| Clean replication | 45.51% | 0.5394 | 0.5489 |
| Optimized placement | **53.71%** | **0.6441** | **0.3947** |

Thus the calibration-aware placement improved overall distribution quality and permissive factor recovery while preserving the strict order-recovery signal established by the frozen baseline experiment.

## Scope

This remains an exact compiled-orbit implementation specific to `N=35`, `a=2`. It is evidence for dynamic phase-register recycling plus hardware-aware encoding/placement on this benchmark, not a claim that scalable reversible modular arithmetic or cryptographic RSA factorization has been solved.

See also:

- `results/hardware/SHOR35_AFFINE_HARDWARE.md`
- `results/hardware/SHOR35_LAYOUT_OPTIMIZATION.md`
- `results/hardware/shor35_affine_8b_run_history.csv`
