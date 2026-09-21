# TCT model-derived Grover round-count feasibility result

Date: 2026-09-21

## Scope

Zero-QPU calibration-aware round-count sweep for the 10-qubit finite-codebook TCT threshold predicate derived from the reduced-order loss formula, fixed-point threshold, and parameter codebooks. The oracle construction does not use the frozen marked-state list; the marked list is used only as a regression target in the model-derived predicate validation.

Backend calibration snapshot:

- backend: `ibm_fez`
- calibration last update: `2026-09-21 04:16:33-07:00`
- logical width: 10 qubits
- parameter bits: 9
- search states: 512
- marked states: 8
- uniform marked fraction: 8/512 = 0.015625
- evaluated physical patches: 7, 9, 10, 12, 13, 19, 22
- transpiler seeds: 8776, 2026, 9401, 42, 1337
- QPU jobs submitted: 0

## Result

| Grover rounds | ideal marked probability | best patch | seed | CZ | depth | sum p(CZ) | log10 no-CZ-error proxy | calibrated duration | duration / median T1 | duration / median T2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.134827 | 10 | 42 | 571 | 1,529 | 1.118 | -0.486 | 43.9 us | 0.302 | 0.320 |
| 2 | 0.343895 | 10 | 1337 | 1,175 | 3,015 | 2.361 | -1.026 | 86.9 us | 0.599 | 0.634 |
| 3 | 0.591380 | 10 | 9401 | 1,815 | 4,578 | 3.568 | -1.551 | 131.9 us | 0.909 | 0.962 |
| 4 | 0.816377 | 10 | 9401 | 2,479 | 6,249 | 4.950 | -2.152 | 181.0 us | 1.247 | 1.319 |
| 5 | 0.963515 | 10 | 1337 | 3,155 | 7,897 | 6.300 | -2.739 | 234.7 us | 1.617 | 1.711 |
| 6 | 0.996586 | 10 | 42 | 3,774 | 9,385 | 7.561 | -3.287 | 278.1 us | 1.916 | 2.028 |

The intentionally simple ranking heuristic `ideal_Grover_success * independent_no_CZ_error_proxy` selected one Grover round. It is not a noisy-hardware success-probability estimate.

## Interpretation

One round is the first candidate in this study that is short relative to the current patch coherence context: about 0.30 median T1 and 0.32 median T2. It also reduces the routed entangling-gate count to 571 CZ while increasing the ideal marked-state probability from 1.5625% to 13.4827%, an ideal amplification factor of about 8.63.

Two rounds raise the ideal marked probability further, but approximately double the CZ burden and duration. Three rounds are still below one median T1/T2 on this snapshot, but the calibration-weighted CZ exposure is already substantially larger. Four through six rounds extend beyond the median coherence times and are less attractive for a first raw-hardware test.

This does not establish that the one-round circuit will produce a 13.5% marked fraction on hardware. The independent-gate product ignores coherent and correlated errors, crosstalk, leakage, relaxation structure, drift, measurement error, pulse scheduling, and mitigation. The result only supports choosing one round as the least-implausible hardware pilot among the tested round counts.

## Next step

Prepare a guarded two-circuit pilot on the same physical patch:

1. uniform 9-parameter-bit baseline, and
2. one-round model-derived Grover circuit.

Compile and calibration-audit both immediately before submission. The pilot should refuse to submit if the candidate leaves the frozen 10-qubit patch or if current calibration exceeds preregistered guardrails. QPU submission should remain disabled by default and require an explicit `--run` flag.

## Boundaries

- Finite-codebook model-derived threshold specialization, not a general reversible numerical evaluator.
- Reduced-order TCT objective only; not fusion-physics validation.
- Calibration products are engineering proxies, not measured circuit fidelity.
- Ranking heuristic is not predicted noisy-hardware success.
- No QPU job was submitted for this result.
- No end-to-end quantum-speedup claim.