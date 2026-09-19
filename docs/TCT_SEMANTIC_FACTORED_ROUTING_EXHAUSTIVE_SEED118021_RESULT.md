# TCT semantic-factored routing — exhaustive seed 118021 result

Date: 2026-09-19

## Scope

This records the zero-QPU exhaustive 24-patch routing audit of the exhaustively statevector-validated, six-round, 10-qubit semantic/ESOP TCT oracle.

The benchmark uses authenticated IBM Fez heavy-hex connectivity and the explicitly labeled 10x12 square-lattice Nighthawk/Phoenix proxy. The semantic oracle is fixed-instance Boolean/ESOP synthesis of the frozen TCT marked-state predicate; it is not a scalable coherent surrogate and is not evidence of end-to-end quantum speedup or fusion-physics validity.

## Fully connected baseline

- CZ: 1,194
- depth: 5,973
- size: 8,055
- weighted interaction edges: 21

## Exhaustive routing minima

### Fez heavy-hex

Interaction-fixed:
- global best patch: 21
- predictor rank: 1
- diameter: 6
- CZ: 3,177
- depth: 7,283
- CZ / fully connected: 2.661
- depth / fully connected: 1.219

Qiskit auto:
- global minimum CZ: 3,181
- attained on patches 3 and 16
- best depth among those: 7,175
- predictor ranks: 4 and 7
- diameter: 7
- CZ / fully connected: 2.664
- depth / fully connected: 1.201

The deterministic screen core (minimum interaction-distance bucket union minimum-diameter bucket) contains patches 21 and 8. For Qiskit auto, its best result is patch 21 at 3,194 CZ / 7,177 depth. Relative to the global Qiskit-auto optimum of 3,181 / 7,175, deterministic-core regret is therefore only 13 CZ (0.409%) and 2 depth layers (0.028%), but it does not achieve exact optimum recall.

The earlier screened run selected six patches total, including random controls. Random-control patch 3 happened to attain the global Qiskit-auto optimum, so the full screened-with-controls policy achieved zero regret and exact optimum recall while compiling 6/24 patches, a 75% patch-compilation reduction. That success should not be attributed solely to the deterministic predictor.

For interaction-fixed placement, patch 21 is both predictor rank 1 and the global exhaustive optimum, so the deterministic screen has exact optimum recall and zero regret for that mode.

### 10x12 square-lattice proxy

Interaction-fixed:
- global best patch: 21
- predictor rank: 2
- diameter: 4
- CZ: 2,311
- depth: 5,946
- CZ / fully connected: 1.936
- depth / fully connected: 0.995

Qiskit auto:
- global best patch: 21
- predictor rank: 2
- diameter: 4
- CZ: 2,250
- depth: 5,933
- CZ / fully connected: 1.884
- depth / fully connected: 0.993

The deterministic screen core includes all diameter-4 patches (10, 21, 14, 20), so it contains patch 21. Therefore deterministic screening has exact optimum recall and zero regret for both interaction-fixed and Qiskit-auto modes on this proxy seed.

The earlier screened run compiled 8/24 patches, a 66.67% patch-compilation reduction, while retaining the global optimum in both layout modes.

## Compression survives routing

Compared with the earlier direct eight-minterm six-round routed oracle:

- Fez Qiskit-auto: 26,391 CZ / 72,300 depth -> 3,181 / 7,175
  - CZ reduction: 87.95%
  - depth reduction: 90.08%
- square-lattice proxy Qiskit-auto: 24,213 CZ / 66,734 depth -> 2,250 / 5,933
  - CZ reduction: 90.71%
  - depth reduction: 91.11%

Thus the semantic factoring/ESOP savings survive sparse-topology routing by a wide margin.

## Interpretation

This exhaustive audit establishes the actual global best among the 24 sampled patches for seed 118021. It supports three separate conclusions:

1. The validated semantic/ESOP oracle remains far smaller than direct minterm marking after sparse routing.
2. The frozen deterministic screen is exact on Fez interaction-fixed placement and on both proxy layout modes for this seed.
3. For Fez Qiskit-auto, the deterministic core misses the exact optimum by only 13 CZ; the full screened-with-random-controls policy happened to recover the optimum.

The Fez Qiskit-auto miss should not be post-hoc tuned on this same holdout. The next rigorous step is replication on fresh patch seeds using the existing frozen screen rule before changing the heuristic.

## Boundaries

- Zero QPU jobs.
- Exhaustive only over the 24 sampled patches for this seed, not every possible physical subgraph.
- Nighthawk/Phoenix side remains a 10x12 square-lattice proxy.
- Fixed-instance Boolean/ESOP oracle only.
- No claim of scalable coherent surrogate evaluation.
- No end-to-end quantum-speedup claim.
- No fusion-physics validation.
