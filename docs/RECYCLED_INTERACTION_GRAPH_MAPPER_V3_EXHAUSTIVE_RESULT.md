# Recycled interaction-graph mapper v3 exhaustive holdout result

Date: 2026-09-17

## Result

The exhaustive holdout compiled all 48 candidate patches on both topology models and confirmed that the v3 post-HLS interaction-distance predictor places the true global-best patch inside the top five predictions for both topologies.

The circuit is the exact small-N N=35 recycled-QPE path at 32 phase bits with 8 source logical qubits. No QPU job was submitted.

## Interaction graph

The post-HLS probe contained 28 weighted logical edges and total native two-qubit interaction weight 20,794.

Largest interaction pressures included:

- phase_recycled <-> scratch[0]: 2,378
- phase_recycled <-> work[0]: 2,218
- work[3] <-> work[5]: 2,088
- work[0] <-> scratch[0]: 1,810
- work[0] <-> work[3]: 1,352

## Exhaustive predictor validation

| topology | compiled patches | Spearman score vs CZ | Spearman score vs depth | global-best fixed predictor rank | global-best auto predictor rank |
|---|---:|---:|---:|---:|---:|
| Fez heavy-hex | 48 / 48 | 0.9833 | 0.9496 | 4 | 4 |
| Nighthawk square-lattice proxy | 48 / 48 | 0.9656 | 0.9096 | 5 | 5 |

Thus a top-5 patch screen would have included the true global-best physical patch for both the custom fixed mapper and Qiskit's automatic layout in this holdout.

Top-5 screening requires compiling 5 rather than 48 patches, a 43/48 = 89.58% reduction in patch-search compilation count.

## Top-1 regret

The predictor's top-ranked patch was good but not globally optimal.

### Fez

- predictor top-1 fixed: 55,198 CZ, depth 118,230
- global-best fixed: 54,495 CZ, depth 117,728
- top-1 CZ regret: about 1.29%
- top-1 depth regret: about 0.43%

### Nighthawk square-lattice proxy

- predictor top-1 fixed: 43,066 CZ, depth 102,649
- global-best fixed: 42,896 CZ, depth 102,022
- top-1 CZ regret: about 0.40%
- top-1 depth regret: about 0.61%

Top-5 regret was zero for the measured primary CZ optimum on both topology models because the global-best fixed patch appeared at ranks 4 and 5.

## Fixed mapping versus Qiskit auto

The in-patch custom mapping still does not uniformly dominate Qiskit auto.

Fez:
- fixed / auto CZ = 0.993238: about 0.68% fewer CZ
- fixed / auto depth = 1.004788: about 0.48% deeper

Nighthawk square-lattice proxy:
- fixed / auto CZ = 1.005344: about 0.53% more CZ
- fixed / auto depth = 0.994376: about 0.56% shallower

Therefore the supported compiler claim is the patch predictor, not a generally superior logical mapper.

## Supported conclusion

For this N=35, 32-phase-bit, exact-width recycled-QPE holdout, minimum post-HLS weighted logical-interaction distance is a strong predictor of compiled patch quality. Exhaustive validation showed that the true global-best patch occurred within the top five predicted patches on both tested topology models, while the rank correlation between predictor score and compiled CZ remained above 0.96.

This supports using the predictor as a patch-screening heuristic that can substantially reduce placement-search compilation work in the tested model.

## Next falsification

Replicate exhaustive top-k recall on independent patch seeds and then across the fixed-width cross-N/base matrix. Report:

- global-best predictor rank;
- recall@1, @3, @5, @6, @10;
- top-k CZ/depth regret;
- screening compile-count reduction;
- whether the same k remains sufficient across N/base/work-register width.

Do not tune predictor weights on the replication seeds.

## Boundaries

- Zero QPU jobs.
- Nighthawk is still a 10x12 square-lattice topology proxy, not exact Phoenix.
- No calibration, timing, reset-speed, fidelity, or QPU-performance claim.
- Exact small-N truth-table/full-register modular-permutation synthesis remains non-scalable to RSA sizes.
- The result establishes patch-quality prediction in this compiler/topology model, not a universal placement theorem.
