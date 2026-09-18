# Recycled interaction-graph mapper v3 independent replication result

Date: 2026-09-18

## Scope

Two independent exhaustive 48-patch replications of the frozen v3 interaction-graph patch predictor were run at N=35, 32 phase bits, with transpiler seeds 8776, 2026, and 9401. No predictor weights were retuned. No QPU job was submitted.

The Fez side uses authenticated Fez heavy-hex connectivity metadata. The Nighthawk side remains the explicitly labeled 10x12 square-lattice topology proxy, not exact Phoenix hardware.

## Replication summary

### Fez heavy-hex

Global-best fixed predictor ranks across the two independent patch seeds:

- rank 7
- rank 3

Global-best Qiskit-auto predictor ranks:

- rank 6
- rank 5

Minimum-score bucket sizes:

- 7 patches
- 5 patches

Minimum-score bucket recall:

- fixed global optimum: 2/2 = 1.000
- auto global optimum: 2/2 = 1.000

Ordinal screening summary:

| k | fixed recall | auto recall | worst fixed CZ regret | compile reduction |
|---:|---:|---:|---:|---:|
| 1 | 0.000 | 0.000 | 1.042% | 97.92% |
| 3 | 0.500 | 0.000 | 0.599% | 93.75% |
| 5 | 0.500 | 0.500 | 0.121% | 89.58% |
| 6 | 0.500 | 1.000 | 0.121% | 87.50% |
| 10 | 1.000 | 1.000 | 0.000% | 79.17% |

The minimum-score-bucket rule therefore replicated cleanly on Fez in both independent ensembles.

### Nighthawk square-lattice proxy

Global-best fixed predictor ranks:

- rank 2
- rank 20

Global-best Qiskit-auto predictor ranks:

- rank 5
- rank 19

Minimum-score bucket sizes:

- 6 patches
- 8 patches

Minimum-score bucket recall:

- fixed global optimum: 1/2 = 0.500
- auto global optimum: 1/2 = 0.500

Ordinal screening summary:

| k | fixed recall | auto recall | worst fixed CZ regret | compile reduction |
|---:|---:|---:|---:|---:|
| 1 | 0.000 | 0.000 | 5.243% | 97.92% |
| 3 | 0.500 | 0.000 | 4.938% | 93.75% |
| 5 | 0.500 | 0.500 | 4.938% | 89.58% |
| 6 | 0.500 | 0.500 | 4.938% | 87.50% |
| 10 | 0.500 | 0.500 | 4.830% | 79.17% |

The universal minimum-score-bucket hypothesis is therefore falsified on the square-lattice proxy.

## Seed-62026 failure case

Despite strong global predictor correlation, the second square-lattice replication contained a materially better patch outside the low-score bucket:

- predictor Spearman(score, CZ): 0.9314
- predictor Spearman(score, depth): 0.9154
- predicted top-1 fixed: rank 1, score 30,118, CZ 43,140, depth 102,796
- global-best fixed: rank 20, score 31,290, CZ 40,991, depth 103,058
- global-best auto: rank 19, score 31,290, CZ 40,740, depth 102,487

Thus the globally best patch had a *worse* v1 weighted-distance score but about 5% fewer CZ than the top-ranked patch.

This is evidence that weighted shortest-path distance alone is insufficient to identify all high-quality square-lattice patches, even when it ranks the overall population well.

## Supported conclusion

The post-HLS weighted interaction-distance score remains a strong **population-level patch-quality predictor** in the tested model. It also replicated as a reliable minimum-score-bucket screen on Fez heavy-hex.

However, the stronger topology-independent claim is not supported. On one independent square-lattice replication, the true global optimum occurred at ordinal ranks 19-20 and outside the minimum-score bucket, with roughly 5% CZ improvement over the top-ranked patch.

The current evidence therefore supports:

- strong monotonic patch-quality prediction on both topology models;
- a replicated minimum-score-bucket screening rule on Fez;
- no universal minimum-score-bucket or top-5 guarantee on the square-lattice proxy.

## Next diagnostic

Do not retune the predictor on seed 62026. Instead compare the failing square-lattice optimum against the minimum-score bucket using topology features that were not represented by scalar weighted distance:

- degree sequence and high-degree-node placement;
- cycle rank / redundant routes;
- graph diameter and mean shortest-path distance;
- articulation structure;
- shortest-path multiplicity / routing flexibility;
- static edge-load concentration under the frozen logical interaction graph;
- v2 congestion-aware score of the actual compiled mapping.

If a stable structural discriminator emerges, preregister it and test it on new patch seeds before changing the production screening rule.

## Boundaries

- Zero QPU jobs.
- Nighthawk result is from a 10x12 square-lattice proxy, not exact Phoenix.
- No calibration, timing, reset-speed, fidelity, or hardware-performance claim.
- Exact small-N full-register permutation synthesis remains non-scalable to RSA sizes.
- This is a compiler/topology result, not an asymptotic Shor improvement.
