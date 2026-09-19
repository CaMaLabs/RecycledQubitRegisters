# TCT semantic-factored oracle v1 result

Date: 2026-09-18

## Scope

This records the zero-QPU fixed-instance Boolean/ESOP compiler result for the frozen 320-scenario FAIR-MAST-seeded TCT reduced-order search predicate.

This is **not** a scalable coherent surrogate implementation and is **not** an end-to-end quantum-advantage result. The scalable-formula baseline remains the 24-qubit reversible arithmetic oracle.

## Frozen search problem

- Valid scenarios: 320
- Marked scenarios: 8
- Parameter register: 9 qubits
- Marked basis states: `14, 15, 30, 31, 46, 47, 63, 79`
- Ideal Grover iterations: 6

## Semantic structure of the marked region

All eight marked parameter assignments share:

- `boost_reduction = 0.70`
- `event_rate_multiplier = 0.25`

The remaining marked region is:

- `standing_bias = 0.25` with `false_trigger_cost_multiplier` in `{0.0, 0.5, 1.0}`; or
- `standing_bias = 0.35` with all five swept false-trigger multipliers `{0.0, 0.5, 1.0, 2.0, 5.0}`.

At the bit level, every marked state shares the common constraints:

- `q1 = 1`
- `q2 = 1`
- `q3 = 1`
- `q7 = 0`
- `q8 = 0`

The remaining local bits are `[q0, q4, q5, q6]`. Their exact marked predicate has a three-term ESOP representation:

- `0---`
- `0110`
- `1001`

The ESOP is an XOR representation, not a disjoint OR cover.

## One-round fully connected compiler comparison

| Oracle realization | Width | CZ | Depth | Size | Weighted edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct eight minterms | 9 | 2,268 | 9,310 | 14,021 | 24 |
| Four disjoint cubes | 9 | 516 | 2,421 | 3,518 | 34 |
| Three-term ESOP direct | 9 | 790 | 3,286 | 4,918 | 26 |
| Four-cube shared-common-control | 10 | 202 | 1,053 | 1,381 | 23 |
| Three-term ESOP shared-common-control | 10 | **199** | **1,013** | **1,365** | **21** |

Best result: `three_term_esop_common_factored`.

Relative to the four-cube disjoint oracle:

- CZ ratio: `0.385659` -> **61.43% fewer CZ**
- depth ratio: `0.418422` -> **58.16% lower depth**

Relative to the original direct eight-minterm oracle:

- CZ ratio: `199 / 2268 = 0.087743` -> **91.23% fewer CZ**
- depth ratio: `1013 / 9310 = 0.108808` -> **89.12% lower depth**

The gain costs one clean ancilla, increasing width from 9 to 10 qubits.

## Relation to the arithmetic oracle

The coherent arithmetic oracle for the same reduced-order loss threshold compiled to 24 logical qubits, 272,126 CZ, and depth 1,083,704 for one round. The 199-CZ semantic oracle is dramatically cheaper, but this is not an apples-to-apples scalable result: the semantic oracle exploits the already-known frozen truth table and common structure of this specific instance.

The arithmetic oracle remains the correct baseline for claims about coherent evaluation of the loss formula itself.

## Verification status

The synthesis code exhaustively verifies the Boolean predicate representation over all `2^9 = 512` parameter-register states before compilation. A separate statevector-level validator should additionally check that the shared-common-control ancilla implementation returns the ancilla to `|0>` and applies exactly the intended phase on all 512 basis inputs before the six-round result is treated as final.

## Claim boundary

- Zero QPU jobs.
- Fully connected synthetic compile only in this result.
- Fixed-instance truth-table/ESOP synthesis.
- Not a scalable replacement for coherent surrogate evaluation.
- Not evidence of end-to-end quantum advantage.
- Not a fusion-physics validation.
