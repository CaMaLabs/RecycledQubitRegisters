# Recycled interaction-graph mapper v1 result

Date: 2026-09-17

## Scope

Zero-QPU compiler/topology predictor validation for the exact N=35 recycled-QPE path. The v1 mapper compiled the exact-width recycled circuit once on a fully connected synthetic backend, extracted native post-HLS two-qubit interactions as a weighted logical graph, scored many exact-width hardware patches by weighted shortest-path distance, and compiled only selected predicted/control patches on Fez heavy-hex and the labeled Nighthawk square-lattice proxy.

No Sampler or QPU job was used.

## Learned interaction graph

At 32 phase bits with one reusable scratch qubit:

- logical width: 8 qubits
- weighted logical edges: 28
- total native two-qubit interaction weight: 20,794

Highest-weight interactions included:

- phase_recycled <-> scratch[0]: 2,378
- phase_recycled <-> work[0]: 2,218
- work[3] <-> work[5]: 2,088
- work[0] <-> scratch[0]: 1,810
- work[0] <-> work[3]: 1,352
- phase_recycled <-> work[3]: 1,168

The post-HLS logical graph is therefore dense, but strongly nonuniform.

## Predictor validation

### Fez heavy-hex

- validated patches: 12 / 48
- Spearman(score, CZ): 0.9331
- Spearman(score, depth): 0.9331
- predicted-top1 fixed layout: 55,027 CZ, depth 117,867
- best validated fixed layout: 54,997 CZ, depth 117,441
- best validated Qiskit auto layout: 54,973 CZ, depth 118,122
- best fixed / best auto CZ ratio: 1.00044
- best fixed / best auto depth ratio: 0.99423

### Nighthawk square-lattice proxy

- validated patches: 12 / 48
- Spearman(score, CZ): 0.7704
- Spearman(score, depth): 0.9275
- predicted-top1 fixed layout: 43,360 CZ, depth 102,366
- best validated fixed layout: 43,221 CZ, depth 103,986
- best validated Qiskit auto layout: 42,894 CZ, depth 102,309
- best fixed / best auto CZ ratio: 1.00762
- best fixed / best auto depth ratio: 1.01639

## Interpretation

The v1 weighted-distance predictor is strongly informative: its ranking correlates closely with compiled CZ/depth, especially on Fez. This shows that the post-HLS logical interaction graph contains real placement information and can reduce the number of patches requiring full compilation.

However, v1 did not beat the best Qiskit automatic layout. It also produced many tied predictor scores (for example several Fez patches at score 36,340), indicating that weighted shortest-path distance alone lacks enough resolution to choose the best logical permutation within similarly shaped patches.

The supported conclusion is therefore:

> Post-HLS interaction pressure is a strong predictor of good recycled-register placements, but static weighted distance alone is insufficient to outperform the best automatic layout.

## v2 follow-up

`hardware/ibm_recycled_interaction_graph_mapper_v2.py` adds fixed, preregistered corrections for:

- physical-degree matching of high-pressure logical qubits,
- multiplicity of equal-length routing paths,
- expected physical-edge congestion,
- peak edge pressure.

It retains exact 8-qubit permutation search but evaluates the richer score only on a broad shortlist of distance-good mappings.

## Boundaries

- Zero-QPU compiler/topology study only.
- Nighthawk side remains a square-lattice topology proxy unless authenticated Phoenix metadata is available.
- N=35 full-register permutation synthesis remains a small-N construction and is not scalable RSA modular arithmetic.
- Predictor correlation is not a hardware-fidelity claim.
