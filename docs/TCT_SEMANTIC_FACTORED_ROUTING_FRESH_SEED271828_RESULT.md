# TCT semantic-factored routing — fresh seed 271828 result

Date: 2026-09-19

## Scope

This records the preregistered fresh-seed, zero-QPU exhaustive 24-patch routing audit of the exhaustively statevector-validated, six-round, 10-qubit semantic/ESOP TCT oracle.

The benchmark uses authenticated IBM Fez heavy-hex connectivity and the explicitly labeled 10x12 square-lattice Nighthawk/Phoenix proxy. The semantic oracle is fixed-instance Boolean/ESOP synthesis of the frozen TCT marked-state predicate; it is not a scalable coherent surrogate and is not evidence of end-to-end quantum speedup or fusion-physics validity.

The screen rule was frozen before observing this seed:

1. deterministic core = minimum interaction-distance bucket union minimum physical-diameter bucket;
2. add four random controls using the benchmark's frozen seeded-control rule.

Patch seed: `271828`.

## Fully connected baseline

- CZ: 1,194
- depth: 5,973
- size: 8,055
- weighted interaction edges: 21

## Exhaustive global minima

### Fez heavy-hex

Interaction-fixed:
- global best patch: 6
- predictor rank: 1
- diameter: 6
- CZ: 3,177
- depth: 7,283
- CZ / fully connected: 2.661
- depth / fully connected: 1.219

Qiskit auto:
- global best patch: 6
- predictor rank: 1
- diameter: 6
- CZ: 3,177
- depth: 7,229
- CZ / fully connected: 2.661
- depth / fully connected: 1.210

The deterministic core contains all diameter-6 patches plus the minimum-score patch, so it includes patch 6. Therefore deterministic screening has exact optimum recall and zero CZ regret for both Fez layout modes on this fresh seed.

The deterministic Fez core contains patches `6, 3, 4, 7, 15, 12, 22, 23`. The frozen random-control draw for this topology/seed is `19, 11, 8, 21`, so the full screened policy would compile 12/24 patches, a 50% patch-compilation reduction, while retaining the exact global optimum in both layout modes.

### 10x12 square-lattice proxy

Interaction-fixed:
- global best patch: 1
- predictor rank: 1
- diameter: 4
- CZ: 2,389
- depth: 6,133
- CZ / fully connected: 2.001
- depth / fully connected: 1.027

Qiskit auto:
- global best patch: 16
- predictor rank: 12
- diameter: 5
- CZ: 2,342
- depth: 6,030
- CZ / fully connected: 1.961
- depth / fully connected: 1.010

The deterministic core is patch 1 only, because it is both the minimum predictor-score patch and the only diameter-4 patch.

For interaction-fixed placement, patch 1 is the global optimum, so deterministic screening has exact optimum recall and zero regret.

For Qiskit auto, deterministic screening would use patch 1 at 2,363 CZ / 6,047 depth versus the global patch-16 optimum at 2,342 / 6,030. Deterministic-core regret is therefore:

- CZ: `2363 - 2342 = 21`, or **0.897%**;
- depth: `6047 - 6030 = 17`, or **0.282%**.

The frozen random-control draw for this topology/seed is `20, 16, 4, 21`, which includes global-optimum patch 16. Therefore the full screen+controls policy would select 5/24 patches, a 79.17% patch-compilation reduction, and recover exact optimum recall and zero CZ regret for both proxy layout modes.

## Cross-seed interpretation

Across exhaustive seeds 118021 and 271828, the frozen deterministic screen is exact in 6 of the 8 topology/layout cases:

- seed 118021:
  - Fez fixed: exact;
  - Fez auto: 0.409% CZ regret;
  - proxy fixed: exact;
  - proxy auto: exact.
- seed 271828:
  - Fez fixed: exact;
  - Fez auto: exact;
  - proxy fixed: exact;
  - proxy auto: 0.897% CZ regret.

Thus the two deterministic misses are both below 1% CZ regret, but exact recall is not universal.

With the preregistered four-random-control augmentation, the full screen+controls policy attains exact optimum recall and zero CZ regret in all 8 topology/layout cases across these two seeds. This is encouraging but remains a small sample and should not be promoted as a universal guarantee.

## Interpretation

This fresh holdout replicates the core result without changing the screening rule: the interaction-distance/diameter screen usually identifies the globally best sampled patch and, when it misses, the observed CZ regret remains below 1% on the tested seeds.

The random-control augmentation again recovers the exact optimum, but that fact should be interpreted as evidence for maintaining controls rather than as proof that four controls will always guarantee recall.

Do not tune the screen on seed 271828. A stronger next step is additional preregistered fresh seeds or a larger cross-seed batch using the same frozen rule.

## Boundaries

- Zero QPU jobs.
- Exhaustive only over the 24 sampled patches for this seed, not every possible physical subgraph.
- Nighthawk/Phoenix side remains a 10x12 square-lattice proxy.
- Fixed-instance Boolean/ESOP oracle only.
- No scalable coherent-surrogate claim.
- No end-to-end quantum-speedup claim.
- No fusion-physics validation.
