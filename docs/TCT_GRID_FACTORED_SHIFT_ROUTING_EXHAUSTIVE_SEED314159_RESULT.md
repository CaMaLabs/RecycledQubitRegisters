# TCT grid-factored shift routing — exhaustive seed 314159 result

Date: 2026-09-20

## Scope

This records the zero-QPU exhaustive routing audit of the validated six-round, 25-qubit grid-factored TCT coherent-arithmetic oracle over the same 12 sampled exact-width physical patches used by the screened seed-314159 run.

The oracle remains a classification-exact transformed arithmetic implementation of the frozen reduced-order TCT objective. It is not a fusion-physics validation, a fault-tolerant resource estimate, or an end-to-end quantum-speedup result.

The IBM Fez side uses authenticated heavy-hex connectivity. The Nighthawk/Phoenix side is explicitly a 10x12 square-lattice proxy, not exact Phoenix connectivity.

## Validated fully connected baseline

- logical width: 25 qubits
- parameter bits: 9
- accumulator bits: 16
- Grover rounds: 6
- marked states: 8
- CZ: 42,756
- depth: 132,481
- size: 263,193
- weighted interaction edges: 273

## Exhaustive sampled-patch results

### Fez heavy-hex

Interaction-fixed global sampled optimum:
- patch: 3
- predictor rank: 2
- diameter: 13
- CZ: 124,194
- depth: 247,046
- CZ / fully connected: 2.905
- depth / fully connected: 1.865

Qiskit-auto global sampled optimum:
- patch: 4
- predictor rank: 1
- diameter: 13
- CZ: 121,320
- depth: 247,438
- CZ / fully connected: 2.837
- depth / fully connected: 1.868

### 10x12 square-lattice proxy

Interaction-fixed global sampled optimum:
- patch: 0
- predictor rank: 3
- diameter: 8
- CZ: 97,722
- depth: 225,316
- CZ / fully connected: 2.286
- depth / fully connected: 1.701

Qiskit-auto global sampled optimum:
- patch: 8
- predictor rank: 1
- diameter: 7
- CZ: 97,026
- depth: 226,426
- CZ / fully connected: 2.269
- depth / fully connected: 1.709

These are exhaustive only over the 12 sampled patches for this frozen seed, not every possible 25-qubit physical subgraph.

## Screen recall versus exhaustive sampled optimum

The earlier frozen screened run selected Fez patches `2,4,7,10,11` and proxy patches `2,8,9`.

### Fez interaction-fixed

- screened best: patch 4, 125,391 CZ / 248,496 depth
- exhaustive sampled best: patch 3, 124,194 CZ / 247,046 depth
- CZ regret: 1,197 = 0.964%
- depth regret: 1,450 = 0.587%
- exact optimum recall: no

### Fez Qiskit-auto

- screened best: patch 4, 121,320 CZ / 247,438 depth
- exhaustive sampled best: patch 4, 121,320 CZ / 247,438 depth
- CZ regret: 0
- depth regret: 0
- exact optimum recall: yes

### Proxy interaction-fixed

- screened best: patch 8, 97,737 CZ / 228,205 depth
- exhaustive sampled best: patch 0, 97,722 CZ / 225,316 depth
- CZ regret: 15 = 0.015%
- depth regret: 2,889 = 1.282%
- exact optimum recall: no

### Proxy Qiskit-auto

- screened best: patch 8, 97,026 CZ / 226,426 depth
- exhaustive sampled best: patch 8, 97,026 CZ / 226,426 depth
- CZ regret: 0
- depth regret: 0
- exact optimum recall: yes

Thus the screen achieved exact sampled-optimum recall in 2/4 topology/layout cases. In the two misses, CZ regret remained below 1%: 0.964% on Fez fixed and 0.015% on proxy fixed.

The interaction predictor's rank-1 patch was the global sampled optimum for both Qiskit-auto cases. For interaction-fixed placement, the global sampled optima were predictor ranks 2 and 3.

## Interpretation

The exhaustive audit confirms that the screened routing result did not hide a large missed optimum. Sparse routing overhead for the validated coherent arithmetic oracle remains moderate rather than order-of-magnitude:

- Fez best sampled auto: 2.837x CZ and 1.868x depth over fully connected;
- proxy best sampled auto: 2.269x CZ and 1.709x depth over fully connected.

The frozen screen is useful but should not be described as universally exact. On this seed it traded substantial compile reduction for less than 1% CZ regret in every topology/layout case.

Do not tune the screening rule on seed 314159. The routing methodology is sufficiently characterized for this stage; the stronger next scientific question is hardware/error-aware feasibility rather than further patch-search optimization.

## Boundaries

- Zero QPU jobs.
- Exhaustive only over 12 sampled patches.
- Fez topology is connectivity-only; this result does not include calibration-weighted fidelity, gate durations, dynamical decoupling, reset/readout, or device noise.
- Nighthawk/Phoenix side is a 10x12 square-lattice proxy.
- Reduced-order TCT objective only.
- Classification-exact transformed arithmetic, not pointwise-exact reproduction of every original floating loss.
- No fault-tolerant resource estimate.
- No end-to-end quantum-speedup claim.
- No fusion-physics validation.
