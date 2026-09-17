# Recycled interaction-graph mapper v2 result

Date: 2026-09-17

## Scope

Zero-QPU compiler/topology experiment using `hardware/ibm_recycled_interaction_graph_mapper_v2.py` on the exact small-N N=35 recycled QPE construction at 32 phase bits, 8 logical qubits, and one scratch qubit.

The interaction graph is extracted after HLS/basis translation on an exact-width fully connected synthetic target. Candidate exact-width connected patches are then scored and validated on Fez heavy-hex connectivity and the clearly labeled 10x12 Nighthawk square-lattice proxy. No QPU job is submitted.

## Interaction graph

The post-HLS probe produced 28 weighted logical edges with total two-qubit weight 20,794. The strongest interactions were:

- phase_recycled <-> scratch[0]: 2,378
- phase_recycled <-> work[0]: 2,218
- work[3] <-> work[5]: 2,088
- work[0] <-> scratch[0]: 1,810
- work[0] <-> work[3]: 1,352

This confirms that the recycled phase qubit, scratch qubit, and a subset of work-register qubits dominate routing pressure.

## Predictor behavior

### Fez heavy-hex

- validated patches: 12 / 48
- Spearman(score, CZ): 0.7239
- Spearman(score, depth): 0.7239
- best fixed mapping: 54,997 CZ, depth 117,441
- best Qiskit auto: 54,973 CZ, depth 118,122
- fixed / auto CZ ratio: 1.00044
- fixed / auto depth ratio: 0.99423

The richer congestion-aware score reduced the strong v1 Fez rank correlation (~0.933) and did not beat Qiskit auto on CZ, although it slightly reduced depth.

### Nighthawk square-lattice proxy

- validated patches: 12 / 48
- Spearman(score, CZ): 0.7774
- Spearman(score, depth): 0.7421
- predicted top-1 patch: patch 0, 46,640 CZ, depth 104,799
- best fixed mapping: patch 4, 42,833 CZ, depth 102,576
- best Qiskit auto: patch 4, 42,967 CZ, depth 102,808
- fixed / auto CZ ratio: 0.99688
- fixed / auto depth ratio: 0.99774

On patch 4, the interaction-aware fixed logical permutation beat Qiskit auto by approximately 0.31% in CZ and 0.23% in depth. This is the first direct evidence in this mapper series that the custom logical permutation can add value beyond patch selection alone.

However, the richer v2 score ranked the best Nighthawk fixed patch only fourth and ranked a substantially worse deterministic dense patch first. Therefore the v2 congestion objective is not supported as a better global patch-ranking metric.

## Interpretation

The v1 and v2 results together separate two roles:

1. **Patch selection:** simple weighted interaction distance is the better validated global predictor, especially on Fez.
2. **Logical mapping inside a chosen patch:** congestion/degree/routing-flexibility information can improve the logical-to-physical assignment, as demonstrated on the Nighthawk proxy patch 4.

The supported next design is therefore a two-stage compiler heuristic rather than further coefficient tuning:

- rank physical patches with the v1 minimum weighted-distance score;
- inside each selected patch, choose the logical permutation with the v2 congestion-aware reranker;
- validate on fresh patch seeds and multiple transpiler seeds.

## Claim boundary

- Zero-QPU only.
- Nighthawk remains a topology proxy, not authenticated Phoenix performance.
- The 0.31% CZ and 0.23% depth improvement is a compiler result on one validated proxy patch, not a hardware speedup or fidelity claim.
- Exact N=35 full-register permutation synthesis remains non-scalable to RSA-sized modular arithmetic.
