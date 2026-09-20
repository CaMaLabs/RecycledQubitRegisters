# TCT Fez calibration-weighted mapping result

Date: 2026-09-20

## Scope

Zero-QPU comparison of four initial-mapping strategies on Fez patch 9, the best patch from the live-calibration sweep for the validated six-round 25-qubit grid-factored TCT coherent-arithmetic oracle.

Calibration snapshot:
- backend: `ibm_fez`
- last update: `2026-09-20 12:35:57-07:00`
- patch: 9
- patch CZ calibration coverage: 100%
- median patch CZ error: 0.00257844

The strategies were `qiskit_auto`, topology-fixed, calibration-fixed, and a hybrid topology+calibration fixed mapping. All runs used the same frozen circuit, patch, and current calibration metadata. No Sampler or QPU job was used.

## Result

| strategy | seed | CZ | depth | mean CZ error | summed CZ exposure | log10 no-error proxy | duration ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| qiskit_auto | 2026 | **131,730** | **255,545** | 0.00281859 | **371.293** | **-161.493** | **7.191** |
| topology_fixed | 8776 | 132,582 | 256,420 | 0.00285009 | 377.870 | -164.359 | 7.228 |
| calibration_fixed | 2026 | 132,300 | 256,184 | 0.00281419 | 372.317 | -161.939 | 7.204 |
| hybrid_fixed | 2026 | 132,507 | 256,546 | 0.00281973 | 373.634 | -162.510 | 7.232 |

The best strategy under the frozen calibration-weighted objective is `qiskit_auto`.

Relative to Qiskit auto, no custom fixed mapping improved summed CZ-error exposure:
- CZ ratio: 1.000 for the winner;
- depth ratio: 1.000;
- summed-CZ-exposure ratio: 1.000;
- duration ratio: 1.000.

## Interpretation

The preceding patch sweep showed that calibration-aware **patch selection** matters enormously: patch 9 reduced summed CZ exposure by about 26x relative to the topology-best patch 4 at only a modest CZ-count penalty.

This follow-up shows that, once patch 9 is selected, the tested calibration-weighted initial-layout heuristics do not improve on Qiskit's automatic layout/routing. The custom calibration-fixed and hybrid-fixed strategies are slightly worse after full transpilation.

Therefore the placement branch is sufficiently characterized for this stage:

1. retain calibration-aware physical-patch selection;
2. use Qiskit auto within the selected patch unless a materially different routing algorithm is tested;
3. do not tune these fixed-layout heuristics further on the same calibration snapshot;
4. return to circuit architecture, because the remaining hardware gap is dominated by roughly 132k routed CZ operations and about 7.2 ms coherent duration, not by a poor initial mapping.

## Next direction

Derive the low-loss phase predicate directly from the frozen reduced-order loss inequality and parameter codebooks, without taking the prelisted eight marked states as oracle input. The goal is a finite-codebook, model-derived threshold oracle that removes the 16-bit score accumulator and comparator while preserving the exact classification.

This is methodologically different from the earlier fixed-instance semantic/ESOP experiment: the predicate must be reconstructed from the loss formula, fixed-point threshold, and codebooks first; the frozen marked list is used only as an independent verification target.

## Boundaries

- Zero QPU jobs.
- Current calibration snapshot only; calibration drifts.
- Calibration-weighted error products are engineering proxies, not measured fidelity.
- The router itself remains topology-based; calibration influenced initial mapping and audit, not pulse synthesis.
- Reduced-order TCT objective only.
- No fusion-physics validation.
- No fault-tolerant resource estimate.
- No end-to-end quantum-speedup claim.
