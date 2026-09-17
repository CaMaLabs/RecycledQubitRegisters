# Recycled-register cross-N generalization result

Date: 2026-09-16

## Scope

Zero-QPU compiler/topology study using the corrected `ibm_recycled_cross_n_generalization_audit_v2.py` entry point. The experiment keeps exact full-register modular-permutation semantics and compares one-qubit recycled QPE against conventional wide QPE under exact-width placement ensembles. No hidden multiplicative order or reachable-orbit encoding is used in circuit construction.

Cases:
- N=21, a=2, work register = 5 qubits
- N=35, a=2, work register = 6 qubits
- N=77, a=2, work register = 7 qubits
- phase precision = 16 and 32 bits
- 8 exact-width connected placement patches
- transpiler seed 2026
- Fez heavy-hex topology and the labeled 10x12 Nighthawk square-lattice proxy

The Nighthawk side is still a topology proxy, not authenticated Phoenix metadata or a calibrated hardware prediction.

## Best-placement result

Every tested case/topology/precision combination had both best-placement CZ ratio < 1 and best-placement depth ratio < 1 for recycled versus wide.

| N | work | phase bits | topology | width wide -> recycled | best R/W CZ | best R/W depth |
|---:|---:|---:|---|---:|---:|---:|
| 21 | 5 | 16 | Fez | 22 -> 7 | 0.8671 | 0.9562 |
| 21 | 5 | 16 | Nighthawk proxy | 22 -> 7 | 0.9896 | 0.9989 |
| 21 | 5 | 32 | Fez | 38 -> 7 | 0.8157 | 0.9773 |
| 21 | 5 | 32 | Nighthawk proxy | 38 -> 7 | 0.9347 | 0.9781 |
| 35 | 6 | 16 | Fez | 23 -> 8 | 0.9325 | 0.9733 |
| 35 | 6 | 16 | Nighthawk proxy | 23 -> 8 | 0.8985 | 0.9758 |
| 35 | 6 | 32 | Fez | 39 -> 8 | 0.9094 | 0.9735 |
| 35 | 6 | 32 | Nighthawk proxy | 39 -> 8 | 0.8808 | 0.9953 |
| 77 | 7 | 16 | Fez | 24 -> 9 | 0.9840 | 0.9971 |
| 77 | 7 | 16 | Nighthawk proxy | 24 -> 9 | 0.9857 | 0.9947 |
| 77 | 7 | 32 | Fez | 40 -> 9 | 0.9659 | 0.9927 |
| 77 | 7 | 32 | Nighthawk proxy | 40 -> 9 | 0.9765 | 0.9978 |

At 32 phase bits, the width reductions are:
- N=21: 38 -> 7, saving 31 qubits
- N=35: 39 -> 8, saving 31 qubits
- N=77: 40 -> 9, saving 31 qubits

Best-placement CZ reductions at 32 bits are approximately:
- N=21: 18.43% on Fez, 6.53% on Nighthawk proxy
- N=35: 9.06% on Fez, 11.92% on Nighthawk proxy
- N=77: 3.41% on Fez, 2.35% on Nighthawk proxy

## Median behavior

The median placement result is mixed and should be kept separate from the placement-aware claim. Several median CZ/depth ratios remain above 1, especially for N=35 and N=77 at lower precision. Therefore this experiment does not support the statement that arbitrary recycled placements are universally cheaper.

The supported statement is narrower:

> Across three small odd composites with 5-, 6-, and 7-qubit work registers, placement-aware recycled QPE reproduced a substantially narrower implementation whose best exact-width placement also matched or reduced compiled CZ count and depth relative to best wide placements in every tested case.

## Interpretation

This weakens the hypothesis that the earlier result was peculiar to N=35. The effect persists across different work-register widths and different full-register permutation structures.

However, the best-placement advantage becomes much smaller in the N=77 / 7-work-qubit case. This may indicate sensitivity to work-register width, permutation complexity, MCX routing structure, or the specific base/permutation family. The current sample is too small to distinguish those explanations.

## Next falsification

Hold work-register width fixed while varying both N and public base a. This separates register-width effects from specific modular-permutation structure. A useful matrix is:

- 5 work qubits: (21,2), (21,5), (25,2)
- 6 work qubits: (35,2), (35,3), (39,2)
- 7 work qubits: (77,2), (77,3), (85,2)

Start at 32 phase bits with a modest placement ensemble, then independently replicate any apparent pattern with a fresh patch seed and multiple transpiler seeds.

## Boundaries

- Zero-QPU only; no runtime/fidelity claim.
- Nighthawk remains a square-lattice topology proxy because the current account cannot access `ibm_phoenix` metadata.
- Exact small-N full-register permutation synthesis remains non-scalable to RSA-sized modular arithmetic.
- This is not an asymptotic speedup claim and not an RSA-breaking result.
