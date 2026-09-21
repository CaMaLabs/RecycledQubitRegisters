# TCT model-derived predicate — Fez calibration sweep result

Date: 2026-09-20

## Scope

This records the zero-QPU Fez routing/calibration sweep of the six-round, 10-qubit TCT threshold predicate derived from the reduced-order model formula, fixed-point threshold, and finite parameter codebooks.

The predicate construction does not use the frozen marked-state list to build the oracle. The model-derived Boolean predicate was previously verified over all 512 parameter-register basis states and only then compared with the frozen eight marked states as a regression check.

This remains a finite-codebook specialization of the reduced-order model, not a general reversible numerical evaluator, not fusion-physics validation, and not an end-to-end quantum-advantage result.

## Calibration snapshot

- backend: `ibm_fez`
- calibration last update: `2026-09-20 20:59:56-07:00`
- logical width: 10 qubits
- Grover rounds: 6
- candidate physical patches: 24
- transpiler seeds per patch: `8776, 2026, 9401, 42, 1337`
- fully connected reference: 1,194 CZ / depth 5,973 / size 8,055
- QPU jobs submitted: 0

## Best routed candidates

### Minimum CZ / minimum calibrated duration

Patch 19, seed 2026:

- CZ: 3,486
- depth: 8,950
- mean calibrated CZ error: 0.00521028
- summed CZ error exposure: 18.163
- independent no-CZ-error proxy: `log10(P) = -7.966`
- calibrated critical path: 253.9 us
- duration / median T1: 1.886

### Minimum calibration-weighted CZ exposure

Patch 10, seed 42:

- CZ: 3,774
- depth: 9,385
- mean calibrated CZ error: 0.00200349
- summed CZ error exposure: 7.561
- independent no-CZ-error proxy: `log10(P) = -3.287`
- corresponding independent no-CZ-error product: about `5.16e-4`
- calibrated critical path: 278.1 us
- duration / median T1: 2.406
- duration / median T2: 2.422

Patch 10 therefore accepts about 8.3% more routed CZ than patch 19 in exchange for a substantially lower calibrated two-qubit error exposure.

## Full sweep observations

Calibration strongly differentiates physical patches even for the same 10-qubit logical circuit. Several patches had current mean CZ errors at the percent-to-tens-of-percent level and correspondingly catastrophic independent-error proxies, while the best patches were near the low-per-mille regime.

The best six-round model-derived circuit is dramatically closer to hardware feasibility than the earlier 25-qubit coherent arithmetic circuit. The earlier arithmetic realization routed to roughly 120k–140k CZ with millisecond-scale duration and hundreds-to-thousands of summed CZ error exposure even on better calibrated patches. The model-derived specialization reduces the routed circuit to a few thousand CZ and a few hundred microseconds.

However, the six-round circuit is still not a clean raw-QPU target under this calibration. On the best exposure patch its independent no-CZ-error proxy is only about 5e-4 and the calibrated critical path exceeds two median coherence times. Those proxies are not a measured circuit fidelity, but they are sufficient to motivate reducing the number of Grover rounds before spending limited QPU runtime.

## Next experiment

Sweep Grover rounds 1 through 6 over the strongest physical patches from this frozen 24-patch set, using multiple transpiler seeds and the current Fez calibration. Report, separately:

1. ideal marked-state probability from Grover amplification;
2. routed CZ/depth;
3. current calibration-weighted CZ exposure;
4. calibrated critical-path duration relative to T1/T2; and
5. a clearly labeled heuristic product of ideal Grover success and independent no-CZ-error proxy for ranking only.

The purpose is to identify whether a shallow one- or two-round hardware experiment is scientifically worthwhile. The heuristic product must not be described as an actual noisy-hardware success probability.

## Boundaries

- Zero QPU execution in this study.
- Current calibration snapshot only; calibration drifts.
- Calibration products are engineering proxies, not measured fidelity.
- Correlated errors, leakage, crosstalk, coherent error, dynamical decoupling, pulse optimization, mitigation, and queue-time drift are not modeled.
- Finite-codebook model-derived predicate, not a general scalable objective evaluator.
- Reduced-order TCT model only; no fusion-physics validation.
- No end-to-end quantum-speedup claim.
