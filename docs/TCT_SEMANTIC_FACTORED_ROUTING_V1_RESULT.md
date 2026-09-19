# TCT semantic-factored oracle — sparse-topology routing result

Date: 2026-09-19

## Scope

This records the zero-QPU sparse-topology routing benchmark of the exhaustively statevector-validated, six-round, 10-qubit TCT semantic-factored ESOP oracle.

The circuit is a fixed-instance Boolean/ESOP implementation of the frozen 8-state TCT marked predicate. It is not a scalable coherent evaluation of the FAIR-MAST-seeded surrogate, not an end-to-end quantum-speedup result, and not fusion-physics validation.

The Nighthawk/Phoenix side remains explicitly a **10x12 square-lattice proxy**, not authenticated Phoenix hardware topology.

## Validated fully connected baseline

- logical width: 10 qubits (9 parameter bits + 1 clean ancilla)
- Grover rounds: 6
- CZ: 1,194
- depth: 5,973
- size: 8,055
- weighted interaction edges: 21
- total two-qubit weight: 1,194

The underlying oracle had already passed exact statevector validation on all 512 parameter-register basis states with zero failures.

## Screened routing run

Candidate patches per topology: 24.

### Fez heavy-hex topology

- selected patches: 6 / 24
- nominal compile reduction: 75.00%
- minimum predictor score: 2,220
- minimum sampled diameter: 6

Best among the selected patches:

| Layout mode | Patch | Predictor rank | Diameter | CZ | Depth | CZ / full | Depth / full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| interaction-fixed | 21 | 1 | 6 | **3,177** | 7,283 | 2.661x | 1.219x |
| Qiskit auto | 3 | 4 | 7 | 3,181 | **7,175** | 2.664x | 1.201x |

The two placement modes are effectively tied in CZ on the selected Fez set: fixed uses only 4 fewer CZ, while Qiskit auto is 108 depth layers shallower.

Important screen caveat: patch 21 is the rank-1 interaction-distance patch and is therefore a genuine screen-selected fixed-layout winner. Patch 3 has predictor rank 4 and diameter 7 while the sampled minimum diameter is 6, so it entered through the random-control portion rather than the deterministic interaction-distance/minimum-diameter screen. Therefore the screen is **not yet validated for the Qiskit-auto Fez optimum**.

### 10x12 square-lattice proxy

- selected patches: 8 / 24
- nominal compile reduction: 66.67%
- minimum predictor score: 1,656
- minimum sampled diameter: 4

Best among the selected patches:

| Layout mode | Patch | Predictor rank | Diameter | CZ | Depth | CZ / full | Depth / full |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| interaction-fixed | 21 | 2 | 4 | 2,311 | 5,946 | 1.936x | 0.995x |
| Qiskit auto | 21 | 2 | 4 | **2,250** | **5,933** | 1.884x | 0.993x |

Patch 21 lies in the minimum-diameter bucket, so the deterministic screen contains the best selected result for both layout modes on this proxy sample. This still does not establish global recall without exhaustive compilation of all 24 sampled patches.

The depth ratios slightly below 1.0 on the square-lattice proxy should not be interpreted as sparse hardware being physically faster than a fully connected machine. These are transpiled circuit-depth metrics, and different topology/layout constraints can lead the compiler to different decompositions and cancellations.

## Compression survives routing

The previous six-round direct eight-minterm routing benchmark gave:

- Fez best auto: 26,391 CZ, depth 72,300
- square-lattice proxy best auto: 24,213 CZ, depth 66,734

The semantic-factored routed results reduce those to:

### Fez, Qiskit auto

- CZ: 26,391 -> 3,181 = **87.95% reduction**
- depth: 72,300 -> 7,175 = **90.08% reduction**

### Square-lattice proxy, Qiskit auto

- CZ: 24,213 -> 2,250 = **90.71% reduction**
- depth: 66,734 -> 5,933 = **91.11% reduction**

Thus the fixed-instance semantic/ESOP compression benefit survives sparse routing by roughly an order of magnitude relative to the earlier direct marked-state oracle.

## Current interpretation

1. The fixed TCT marked predicate has strong exploitable Boolean structure.
2. Shared common-control factoring plus a three-term local ESOP remains effective after sparse-topology routing.
3. Fez routing roughly multiplies CZ by 2.66x over the fully connected baseline, but depth by only about 1.20x.
4. The square-lattice proxy roughly multiplies CZ by 1.88x while compiled depth remains essentially unchanged.
5. The current interaction-distance/minimum-diameter screen cannot yet be credited with global optimum recall because the run was non-exhaustive, and the best selected Fez Qiskit-auto patch came from the random-control subset.

## Next validation

Run the same 24-patch seed exhaustively, with the same three transpiler seeds, for both layout modes and both topologies. This is still zero-QPU and is small enough to be practical for a 10-qubit circuit.

The exhaustive run will answer:

- whether the deterministic screen recalled the true best sampled fixed-layout and Qiskit-auto patches;
- the actual CZ/depth regret of screening;
- predictor rank of the true optima;
- whether patch 3 is genuinely the best Fez auto patch or only the best among the six selected patches.

Only after that should screening efficiency/recall claims be made for this TCT semantic-factored workload.

## Boundaries

- Zero QPU jobs.
- Fez uses authenticated hardware connectivity for compiler/topology analysis only; no calibration/fidelity/timing claim.
- Nighthawk/Phoenix is a 10x12 square-lattice proxy.
- Fixed-instance truth-table/semantic Boolean synthesis only.
- No scalable coherent-surrogate claim.
- No end-to-end quantum-advantage claim.
- No fusion-physics validation.
