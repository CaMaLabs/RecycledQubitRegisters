# Recycled interaction-graph mapper v3 exhaustive holdout result

Date: 2026-09-17

## Result

The exhaustive holdout compiled all 48 candidate patches on both topology models and confirmed that the v3 post-HLS interaction-distance predictor places the true global-best patch inside the minimum predictor-score bucket for both topologies.

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

| topology | compiled patches | Spearman score vs CZ | Spearman score vs depth | global-best fixed ordinal rank | global-best auto ordinal rank |
|---|---:|---:|---:|---:|---:|
| Fez heavy-hex | 48 / 48 | 0.9833 | 0.9496 | 4 | 4 |
| Nighthawk square-lattice proxy | 48 / 48 | 0.9656 | 0.9096 | 5 | 5 |

Ordinal top-5 screening recovered the global-best physical patch in both cases, with zero measured CZ regret at k=5.

## Minimum-score bucket result

The score-aware analysis resolves the ordinal tie caveat.

### Fez heavy-hex

- global-best fixed score: 36,340
- global-best auto score: 36,340
- dense score rank: 1
- minimum-score bucket size: 6 patches
- true global-best fixed patch in minimum bucket: yes
- true global-best auto patch in minimum bucket: yes
- exhaustive search: 48 patches
- score-bucket screen: 6 patches
- patch-search compilation reduction: 42/48 = **87.50%**

### Nighthawk square-lattice proxy

- global-best fixed score: 30,118
- global-best auto score: 30,118
- dense score rank: 1
- minimum-score bucket size: 8 patches
- true global-best fixed patch in minimum bucket: yes
- true global-best auto patch in minimum bucket: yes
- exhaustive search: 48 patches
- score-bucket screen: 8 patches
- patch-search compilation reduction: 40/48 = **83.33%**

This gives a cleaner deterministic screening rule than ordinal top-k: compile all patches tied for the minimum weighted-distance score.

## Exact top-k recall and regret

### Fez heavy-hex

| k | fixed recall | auto recall | fixed CZ regret | compile reduction |
|---:|:---:|:---:|---:|---:|
| 1 | no | no | 1.290% | 97.92% |
| 3 | no | no | 0.773% | 93.75% |
| 5 | yes | yes | 0.000% | 89.58% |
| 6 | yes | yes | 0.000% | 87.50% |
| 10 | yes | yes | 0.000% | 79.17% |

### Nighthawk square-lattice proxy

| k | fixed recall | auto recall | fixed CZ regret | compile reduction |
|---:|:---:|:---:|---:|---:|
| 1 | no | no | 0.396% | 97.92% |
| 3 | no | no | 0.396% | 93.75% |
| 5 | yes | yes | 0.000% | 89.58% |
| 6 | yes | yes | 0.000% | 87.50% |
| 10 | yes | yes | 0.000% | 79.17% |

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

For this N=35, 32-phase-bit, exact-width recycled-QPE holdout, minimum post-HLS weighted logical-interaction distance is a strong predictor of compiled patch quality. Exhaustive validation showed that the true global-best patch belongs to the **minimum predictor-score bucket** on both tested topology models, while Spearman correlation between predictor score and compiled CZ remained above 0.96.

A deterministic minimum-score-bucket screen would have reduced the patch-search compilation count by 87.5% on Fez and 83.3% on the square-lattice proxy while retaining the global-best patch in this holdout.

## Next falsification

Replicate exhaustive minimum-score-bucket recall on independent patch seeds and then across the fixed-width cross-N/base matrix. Report:

- whether the global-best fixed patch lies in the minimum-score bucket;
- whether the global-best auto patch lies in the minimum-score bucket;
- minimum-score bucket size;
- score-bucket compile reduction;
- ordinal recall@1, @3, @5, @6, @10 and regret;
- whether the same score rule survives changes in N/base/work-register width.

Do not tune predictor weights on replication seeds.

## Boundaries

- Zero QPU jobs.
- Nighthawk is still a 10x12 square-lattice topology proxy, not exact Phoenix.
- No calibration, timing, reset-speed, fidelity, or QPU-performance claim.
- Exact small-N truth-table/full-register modular-permutation synthesis remains non-scalable to RSA sizes.
- The result establishes patch-quality prediction in this compiler/topology model, not a universal placement theorem.
