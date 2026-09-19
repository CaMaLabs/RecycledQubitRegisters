# TCT semantic-factored routing — fresh seed 271828 result

Date: 2026-09-19

## Scope

This records the preregistered fresh-seed, zero-QPU exhaustive 24-patch routing audit of the exhaustively statevector-validated, six-round, 10-qubit semantic/ESOP TCT oracle.

The benchmark uses authenticated IBM Fez heavy-hex connectivity and the explicitly labeled 10x12 square-lattice Nighthawk/Phoenix proxy. The semantic oracle is fixed-instance Boolean/ESOP synthesis of the frozen TCT marked-state predicate; it is not a scalable coherent surrogate and is not evidence of end-to-end quantum speedup or fusion-physics validity.

The screen rule was frozen before observing this seed:

1. deterministic core = minimum interaction-distance bucket union minimum physical-diameter bucket;
2. add four random controls using the benchmark's frozen seeded-control rule.

Patch seed: `271828`.

The authoritative screen-recall/regret values below are taken from `analyze_tct_routing_screen_recall.py` applied to the exhaustive JSON artifact.

## Fully connected baseline

- CZ: 1,194
- depth: 5,973
- size: 8,055
- weighted interaction edges: 21

## Exhaustive global minima and frozen-screen recall

### Fez heavy-hex

Deterministic screen set:

`[3, 4, 6, 7, 12, 15, 22, 23]`

Full screen+controls set:

`[3, 4, 6, 7, 8, 11, 12, 15, 19, 21, 22, 23]`

This compiles 12/24 patches, a **50.00% patch-compilation reduction**.

Interaction-fixed:
- global best patch: 6
- predictor rank: 1
- CZ: 3,177
- depth: 7,283
- deterministic result: patch 6, 3,177 / 7,283
- deterministic regret: **0 CZ (0.000%)**, **0 depth (0.000%)**
- full-screen regret: **0**

Qiskit auto:
- global best patch: 6
- predictor rank: 1
- CZ: 3,177
- depth: 7,229
- deterministic result: patch 6, 3,177 / 7,229
- deterministic regret: **0 CZ (0.000%)**, **0 depth (0.000%)**
- full-screen regret: **0**

Thus the frozen deterministic screen itself has exact optimum recall for both Fez layout modes on this fresh seed.

### 10x12 square-lattice proxy

Deterministic screen set:

`[1, 9, 12]`

Full screen+controls set:

`[0, 1, 8, 9, 12, 16, 17]`

This compiles 7/24 patches, a **70.83% patch-compilation reduction**.

Interaction-fixed:
- global best patch: 1
- predictor rank: 1
- CZ: 2,389
- depth: 6,133
- deterministic result: patch 1, 2,389 / 6,133
- deterministic regret: **0 CZ (0.000%)**, **0 depth (0.000%)**
- full-screen regret: **0**

Qiskit auto:
- global best patch: 16
- predictor rank: 12
- CZ: 2,342
- depth: 6,030
- deterministic best: patch 12, predictor rank 3, 2,351 / 6,154
- deterministic CZ regret: `2351 - 2342 = 9`, or **0.384%**
- deterministic depth regret: `6154 - 6030 = 124`, or **2.056%**
- full-screen best: patch 16, 2,342 / 6,030
- full-screen regret: **0**

The frozen random-control augmentation therefore recovers the exact proxy/Qiskit-auto optimum on this fresh seed while retaining a 70.83% patch-compilation reduction.

## Cross-seed interpretation

Across exhaustive seeds 118021 and 271828, the frozen deterministic screen is exact in 6 of the 8 topology/layout cases:

- seed 118021:
  - Fez fixed: exact;
  - Fez auto: 0.409% CZ regret and 0.028% depth regret;
  - proxy fixed: exact;
  - proxy auto: exact.
- seed 271828:
  - Fez fixed: exact;
  - Fez auto: exact;
  - proxy fixed: exact;
  - proxy auto: 0.384% CZ regret and 2.056% depth regret.

Thus both deterministic misses remain below **0.5% CZ regret**, although depth regret is not uniformly tiny.

With the preregistered four-random-control augmentation, the full screen+controls policy attains exact optimum recall and zero CZ regret in all **8/8** topology/layout cases across these two seeds. This is encouraging but remains a small sample and should not be promoted as a universal guarantee.

## Interpretation

This fresh holdout replicates the core result without changing the screening rule: the interaction-distance/diameter screen usually identifies the globally best sampled patch and, when it misses, observed CZ regret remains small on the tested seeds.

The random-control augmentation again recovers the exact optimum, but that fact should be interpreted as evidence for retaining controls rather than as proof that four controls always guarantee recall.

Do not tune the screen on seed 271828. A stronger next step is additional preregistered fresh seeds or a larger cross-seed batch using the same frozen rule.

## Boundaries

- Zero QPU jobs.
- Exhaustive only over the 24 sampled patches for this seed, not every possible physical subgraph.
- Nighthawk/Phoenix side remains a 10x12 square-lattice proxy.
- Fixed-instance Boolean/ESOP oracle only.
- No scalable coherent-surrogate claim.
- No end-to-end quantum-speedup claim.
- No fusion-physics validation.
