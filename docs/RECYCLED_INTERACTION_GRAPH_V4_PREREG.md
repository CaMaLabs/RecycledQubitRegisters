# Recycled interaction-graph v4 challenger preregistration

Date: 2026-09-18

## Motivation

The frozen v3 weighted-interaction-distance predictor replicated strongly on Fez but failed to recover the global optimum on one independent square-lattice-proxy ensemble (patch seed 62026). The failure was not subtle: the best fixed patch appeared at ordinal predictor rank 20 and the best auto patch at rank 19, with roughly 4.94% fixed-CZ regret at top-5.

A post-hoc structural diagnostic of that failed square-lattice ensemble found that the two global-optimum patches (fixed p24 and auto p06) shared the same measured graph/routing fingerprint in the diagnostic output:

- 9 undirected edges
- cycle rank 2
- diameter 3
- mean pair distance 1.929
- 2 articulation points
- maximum degree 4
- weighted shortest-path multiplicity 1.286
- edge-load CV 0.388
- peak static edge load about 6069

By contrast, every minimum-distance-score patch shown in the diagnostic had:

- 10 undirected edges
- cycle rank 3
- diameter 4
- mean pair distance 1.929
- 0 articulation points
- maximum degree 4
- weighted shortest-path multiplicity 1.322
- edge-load CV 0.448
- peak static edge load about 5332

This does **not** support the earlier idea that greater route redundancy or lower peak congestion explains the outlier. The clearest simple discriminator is the smaller physical graph diameter.

The matching printed invariants for p06 and p24 do not by themselves prove graph isomorphism.

## Frozen challenger rule

Before inspecting a new patch seed, define the v4 candidate screen as the union of:

1. **minimum interaction-distance bucket**: every candidate patch whose frozen v1 weighted logical-interaction distance equals the minimum across the candidate ensemble; and
2. **minimum physical-diameter bucket**: every candidate patch whose unweighted induced physical-subgraph diameter equals the minimum across the candidate ensemble.

No coefficient is fitted. No weighted sum is introduced. No compiled CZ/depth result is used to choose the screened set.

The v3 logical mapping procedure remains unchanged. The challenger changes only which physical patches are retained for compilation.

## Primary falsification test

Run a fresh exhaustive 48-patch ensemble that was not used to formulate this rule. Using the exhaustive compilation only as ground truth, measure whether the preregistered union screen contains:

- the true global-best fixed-layout patch;
- the true global-best Qiskit-auto patch.

Report:

- size of the minimum-distance bucket;
- size of the minimum-diameter bucket;
- size of their union;
- compile-count reduction relative to 48-patch exhaustive search;
- fixed and auto global-optimum recall;
- fixed and auto CZ regret of the union screen;
- the corresponding baseline v3 minimum-distance-bucket recall/regret.

## Success criterion

A fresh-seed success requires the union screen to contain both the global-best fixed and global-best auto patches with zero CZ regret, while retaining a meaningful reduction in patch compilations.

One success does not establish universality. Repeated fresh-seed replication and cross-N/base testing remain required.

## Boundaries

- Zero QPU jobs.
- Nighthawk remains a 10x12 square-lattice topology proxy, not authenticated Phoenix performance.
- No calibration, fidelity, timing, or reset-speed claim.
- Exact small-N full-register permutation synthesis is non-scalable to RSA-sized modular arithmetic.
- This is a preregistered compiler/topology screening hypothesis, not a hardware-performance theorem.
