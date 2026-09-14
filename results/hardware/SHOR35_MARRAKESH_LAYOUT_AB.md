# N=35 Marrakesh same-job layout A/B

This note records the same-job control designed to separate physical-layout effects from backend/calibration drift for the frozen eight-bit affine `N=35`, `a=2`, `r=12` benchmark on `ibm_marrakesh`.

The four circuits were submitted in one QPU job:

1. legacy recycled
2. legacy wide
3. optimized recycled
4. optimized wide

All circuits used the same mathematical problem, 512 shots, optimization level 3, and the same frozen optimizer JSON. The legacy and optimized pairs each preserved matched initial work-register placement within the pair.

## Results

Uniform eight-bit references:

- permissive factor recovery: `12.890625%`
- strict direct-order recovery: `2.34375%` (`12/512` expectation)
- Hellinger fidelity to ideal: `0.2348667`
- TV distance to ideal: `0.8257132`

| Circuit | Permissive | Strict direct-order | Hellinger | TV distance |
|---|---:|---:|---:|---:|
| Legacy recycled | 22.2656% (114/512) | 1.3672% (7/512) | 0.2606 | 0.7755 |
| Legacy wide | 13.4766% (69/512) | 1.3672% (7/512) | 0.1897 | 0.8441 |
| Optimized recycled | 33.9844% (174/512) | 3.7109% (19/512) | 0.3908 | 0.6281 |
| Optimized wide | 32.0313% (164/512) | 6.2500% (32/512) | 0.4688 | 0.6438 |

## What the control establishes

The same-job A/B strongly supports a **placement/calibration effect** on Marrakesh.

For recycled, optimized placement increased permissive recovery from `22.27%` to `33.98%` and strict direct-order recovery from `7/512` to `19/512`.

For wide, optimized placement increased permissive recovery from `13.48%` to `32.03%` and strict direct-order recovery from `7/512` to `32/512`.

Because all four circuits were executed in the same job, these differences cannot be explained solely by calibration-window drift between separate jobs.

Under a simple independent-binomial difference approximation, the permissive optimized-minus-legacy changes are about `4.21` standard errors for recycled and `7.26` for wide. The strict changes are about `2.39` and `4.12` standard errors, respectively. These are descriptive shot-noise-only comparisons, not a complete hardware uncertainty model.

Against the analytic uniform strict baseline, optimized recycled observed `19/512`, with one-sided fixed-baseline binomial tail `p ≈ 0.0356`. Optimized wide observed `32/512`, with one-sided fixed-baseline binomial tail `p ≈ 8.4e-7`. These p-values model shot noise only and do not account for calibration correlations, optimizer selection, or other systematics.

## Architectural interpretation

This control does **not** show that recycling is universally superior to the wide circuit on Marrakesh. In fact, after optimized placement, the two architectures are close on permissive recovery, while optimized wide is stronger on the strict direct-order metric and Hellinger fidelity. Recycled retains a slightly smaller TV distance to the ideal distribution.

The result therefore points to an interaction among **architecture, physical placement, and backend calibration/topology** rather than a backend-independent ranking of recycled over wide.

A notable consequence is that lower nominal resource count alone is not sufficient to predict experimental order-recovery quality. The optimized recycled circuit still uses far fewer simultaneous logical qubits and substantially fewer CZ gates, yet optimized wide can outperform it on the strict metric when placed on a favorable Marrakesh region.

The most defensible cross-backend conclusion is now:

> The `N=35`, `a=2`, `r=12` order-finding signal is reproducible on a second superconducting backend when hardware-aware placement is used, but the recycled-versus-wide advantage is backend- and placement-dependent. On Marrakesh, recycling is more robust than wide under the legacy placement, while optimized placement improves both architectures and can make wide competitive or superior on strict direct-order recovery.

This remains a compiled-orbit hardware benchmark and not a generic scalable Shor implementation.
