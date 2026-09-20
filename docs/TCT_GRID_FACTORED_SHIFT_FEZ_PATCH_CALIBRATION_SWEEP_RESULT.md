# TCT grid-factored shift Fez patch-calibration sweep

Date: 2026-09-20

## Scope

Zero-QPU calibration-aware sweep over the same 12 frozen 25-qubit Fez patches used by the exhaustive six-round routing study for the validated grid-factored TCT coherent-arithmetic oracle.

The circuit remains a classification-exact transformed implementation of the frozen reduced-order TCT objective. This is an engineering feasibility audit, not fusion-physics validation, not a hardware-fidelity guarantee, and not an end-to-end quantum-speedup result.

Calibration snapshot:
- backend: `ibm_fez`
- backend calibration last update: `2026-09-20 12:35:57-07:00`
- six Grover rounds
- logical width: 25 qubits
- parameter bits: 9
- accumulator bits: 16

## Key result

Topology-only placement and calibration-aware placement strongly disagree.

The topology-optimal Fez Qiskit-auto patch from the exhaustive routing study was patch 4:
- CZ: 121,320
- depth: 247,438
- mean current CZ error on used operations: 0.0797549
- summed CZ error exposure `sum p`: 9,675.865
- independent-gate no-CZ-error proxy: `log10(P) = -135371.463`
- calibrated critical-path duration: about 7.012 ms
- duration / patch median T1: about 60.49

The best patch under the current calibration was patch 9:
- CZ: 130,998
- mean current CZ error on used operations: 0.00283453
- summed CZ error exposure `sum p`: 371.318
- independent-gate no-CZ-error proxy: `log10(P) = -161.506`
- calibrated critical-path duration: about 7.183 ms
- duration / patch median T1: about 54.29

Thus patch 9 spends about 7.98% more CZ than patch 4 but reduces summed CZ-error exposure by about 26.06x.

This is strong evidence that topology-only CZ/depth minimization is not an adequate physical-placement objective for this circuit when current calibration metadata are available.

## Full patch sweep

| patch | predictor rank | CZ | mean CZ error | summed CZ exposure | log10 no-error proxy | duration ms | duration/T1 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 9 | 136,068 | 0.00773251 | 1,052.147 | -460.631 | 6.926 | 47.29 |
| 1 | 4 | 123,732 | 0.00703591 | 870.568 | -383.149 | 6.836 | 55.30 |
| 2 | 8 | 133,011 | 0.0112449 | 1,495.699 | -9,712.055 | 6.973 | 64.35 |
| 3 | 2 | 123,588 | 0.0337861 | 4,175.562 | -49,389.609 | 6.829 | 53.36 |
| 4 | 1 | 121,320 | 0.0797549 | 9,675.865 | -135,371.463 | 7.012 | 60.49 |
| 5 | 11 | 136,749 | 0.0327741 | 4,481.825 | -62,119.018 | 7.193 | 62.60 |
| 6 | 12 | 138,027 | 0.00482462 | 665.928 | -290.102 | 7.217 | 59.80 |
| 7 | 3 | 124,614 | 0.0234084 | 2,917.018 | -31,044.059 | 6.943 | 57.96 |
| 8 | 10 | 135,534 | 0.0821024 | 11,127.672 | -158,229.237 | 7.364 | 58.56 |
| 9 | 6 | 130,998 | 0.00283453 | 371.318 | -161.506 | 7.183 | 54.29 |
| 10 | 7 | 131,076 | 0.00385136 | 504.821 | -219.823 | 7.178 | 55.07 |
| 11 | 5 | 125,943 | 0.104578 | 13,170.849 | -189,414.155 | 7.004 | 53.79 |

## Interpretation

Calibration-aware patch selection is a meaningful lever. The best current-calibration patch changes from patch 4 to patch 9, and the error-exposure reduction is much larger than the modest CZ-count penalty.

However, even patch 9 remains far outside plausible raw-NISQ execution for the full six-round coherent arithmetic circuit. Under the simple independent-gate proxy, hundreds of expected CZ error events remain, and the calibrated critical path is tens of median coherence times.

Therefore:
1. do not spend limited QPU runtime on the full six-round arithmetic circuit in its current form;
2. use calibration-aware placement rather than topology-only placement for future physical mapping; and
3. continue circuit-level reduction of CZ count and coherent duration, because placement alone cannot close the remaining gap.

## Next experiment

Optimize the logical-to-local mapping inside the best current-calibration patch using a calibration-weighted shortest-path objective based on current Fez CZ error metadata, then recompile and audit the resulting physical circuit against the same calibration snapshot.

This tests whether the current patch-9 Qiskit-auto mapping leaves additional calibration-aware gains on the table.

## Boundaries

- Zero QPU jobs.
- Current calibration snapshot only; calibration drifts.
- `sum p` and the independent-gate no-error product are engineering proxies, not measured circuit fidelity.
- Correlated error, crosstalk, leakage, dynamical decoupling, pulse-level optimization, mitigation, and drift during queue/execution are not modeled.
- Reduced-order TCT objective only.
- No fusion-physics validation.
- No fault-tolerant resource estimate.
- No end-to-end quantum-speedup claim.
