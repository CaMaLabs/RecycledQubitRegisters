# Recycled interaction-graph mapper v3 holdout result

Date: 2026-09-17

## Scope

Zero-QPU holdout validation of the two-stage interaction-graph mapper:

1. rank exact-width physical patches using the v1 post-HLS weighted logical-interaction distance;
2. choose the logical-to-physical permutation inside each patch using the v2 congestion-aware mapper.

Run used a fresh patch seed (90421) and transpiler seeds 8776, 2026, and 9401. The circuit remained the exact small-N N=35 recycled-QPE path with 8 source logical qubits. The Nighthawk side remains a 10x12 square-lattice topology proxy, not authenticated Phoenix hardware.

## Interaction graph

The post-HLS probe contained 28 weighted logical edges with total native 2Q interaction weight 20,794. The largest pressures included:

- phase_recycled <-> scratch[0]: 2,378
- phase_recycled <-> work[0]: 2,218
- work[3] <-> work[5]: 2,088
- work[0] <-> scratch[0]: 1,810
- work[0] <-> work[3]: 1,352

## Holdout predictor result

| topology | validated / candidate patches | Spearman score vs CZ | Spearman score vs depth | best validated fixed predictor rank |
|---|---:|---:|---:|---:|
| Fez heavy-hex | 12 / 48 | 0.9161 | 0.9161 | 4 |
| Nighthawk square-lattice proxy | 12 / 48 | 0.9368 | 0.9219 | 5 |

This independently reproduces the core v1 finding: low post-HLS weighted interaction-distance scores strongly track lower compiled cost on a fresh patch ensemble.

## Fixed mapping versus Qiskit auto

### Fez

Best validated fixed:
- CZ: 54,495
- depth: 117,728
- predictor rank: 4

Best validated auto:
- CZ: 54,866
- depth: 117,167

Ratios:
- fixed / auto CZ = 0.993238
- fixed / auto depth = 1.004788

Thus the fixed map used about 0.68% fewer CZ but was about 0.48% deeper. It does not dominate auto-layout.

### Nighthawk square-lattice proxy

Best validated fixed:
- CZ: 42,896
- depth: 102,022
- predictor rank: 5

Best validated auto:
- CZ: 42,668
- depth: 102,599

Ratios:
- fixed / auto CZ = 1.005344
- fixed / auto depth = 0.994376

Thus the fixed map was about 0.53% worse in CZ but about 0.56% shallower. It does not dominate auto-layout.

## Interpretation

The two-stage design succeeds as a patch-ranking heuristic, but current evidence does not support the stronger claim that its in-patch logical permutation is uniformly better than Qiskit's automatic layout.

The best validated fixed patches appeared at predictor ranks 4 and 5. This is encouraging for top-k screening, but only 12 of the 48 candidate patches were compiled. Therefore the current run cannot establish true top-5/top-6 recall of the global optimum.

## Next falsification

Compile all 48 holdout patches for both fixed and automatic layout under the same three transpiler seeds. Then measure:

- rank of the true global best fixed patch;
- rank of the true global best auto patch;
- recall@1, @3, @5, @6, @10;
- regret of choosing predictor top-k instead of exhaustive search;
- compile-count reduction versus exhaustive search.

This is the correct test before claiming the predictor can replace brute-force patch compilation.

## Boundaries

- Zero QPU jobs.
- Nighthawk remains a topology proxy.
- No calibrated timing/fidelity claim.
- Exact small-N truth-table modular-permutation synthesis is non-scalable to RSA sizes.
- The current result supports patch prediction, not a generally superior mapper.
