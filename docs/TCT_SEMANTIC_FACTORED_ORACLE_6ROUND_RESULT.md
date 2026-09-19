# TCT semantic-factored oracle — six-round compiler result

Date: 2026-09-18

## Scope

This records the zero-QPU six-round compile of the frozen TCT marked-state predicate after semantic common-control factoring and exact ESOP synthesis.

The result is a fixed-instance Boolean-oracle compiler result. It is not a scalable replacement for coherent evaluation of the FAIR-MAST-seeded TCT reduced-order surrogate and is not evidence of end-to-end quantum advantage or fusion-physics validity.

## Frozen search problem

- Valid scenarios: 320
- Marked scenarios: 8
- Parameter register: 9 qubits
- Best semantic-factored implementation: 10 qubits including one clean ancilla
- Idealized Grover rounds: 6

Marked basis states:

`[14, 15, 30, 31, 46, 47, 63, 79]`

Common parameter-bit constraints:

`q1=1, q2=1, q3=1, q7=0, q8=0`

Remaining local bits:

`[0, 4, 5, 6]`

Minimum local ESOP terms:

- `0---`
- `0110`
- `1001`

## Six-round compiler comparison

| Variant | Width | CZ | Depth | Size | Weighted edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| direct eight-minterm | 9 | 13,608 | 55,830 | 83,996 | 24 |
| four-cube disjoint | 9 | 3,096 | 14,511 | 20,978 | 34 |
| three-term ESOP direct | 9 | 4,740 | 19,666 | 29,378 | 26 |
| four-cube common-factored | 10 | 1,212 | 6,213 | 8,151 | 23 |
| three-term ESOP common-factored | 10 | **1,194** | **5,973** | **8,055** | **21** |

The best compiled variant is `three_term_esop_common_factored`.

## Improvement

Relative to the direct eight-minterm six-round oracle:

- CZ ratio: `1194 / 13608 = 0.0877425`
- CZ reduction: **91.23%**
- Depth ratio: `5973 / 55830 = 0.1069855`
- Depth reduction: **89.30%**

Relative to the four-cube disjoint six-round oracle:

- CZ ratio: `0.385659`
- CZ reduction: **61.43%**
- Depth ratio: `0.411619`
- Depth reduction: **58.84%**

## Scaling from one round

One-round best semantic-factored result:

- CZ: 199
- Depth: 1,013

Six rounds:

- CZ: 1,194 = exactly 6 x 199
- Naive 6x depth: 6,078
- Observed depth: 5,973

Thus CZ scales exactly linearly across six repeated rounds, while compiled depth is about 1.73% lower than naive linear scaling.

## Comparison with coherent arithmetic baseline

The classification-exact reversible arithmetic oracle used:

- width: 24 qubits
- CZ: 272,126 per one Grover round
- depth: 1,083,704 per one Grover round

A naive six-round projection is therefore about 1,632,756 CZ and 6,502,224 depth before sparse-topology routing.

The six-round semantic-factored fixed-instance oracle is roughly 1,367x smaller in CZ than that naive six-round arithmetic projection. This contrast is informative but intentionally not an apples-to-apples scalability comparison: the semantic-factored oracle exploits the already known frozen truth table, whereas the arithmetic oracle coherently evaluates the reduced-order objective.

## Interpretation

The TCT low-loss predicate has substantial internal Boolean structure. Factoring the five parameter-bit constraints shared by every marked assignment, then synthesizing the remaining four-bit local predicate as a three-term ESOP and computing the common condition once with one clean ancilla, gives a large compiler reduction.

This supports a practical compiler lesson: when a frozen optimization instance has a highly structured marked set, semantic predicate factoring can dominate direct minterm or disjoint-cube marking.

It does **not** establish that arbitrary or dynamically evaluated TCT search problems admit this compact oracle, nor does it overcome the large cost measured for coherent arithmetic evaluation of the actual TCT loss formula.

## Next validation

Before treating the semantic-factored circuit as the trusted fixed-instance oracle, independently statevector-check the actual shared-ancilla implementation over all 512 parameter-register basis states and verify:

1. the intended phase is applied iff the state is one of the eight marked states;
2. no amplitude leaks to another parameter state;
3. the clean ancilla returns to `|0>`.

If that passes, the next useful compiler experiment is sparse-topology routing of the six-round 10-qubit circuit on Fez and the square-lattice proxy. No QPU execution is needed.

## Boundaries

- Zero QPU jobs.
- Fixed-instance Boolean/ESOP synthesis only.
- No claim of scalable coherent surrogate evaluation.
- No end-to-end quantum speedup claim.
- No fusion-physics validation.
- Nighthawk/Phoenix results, if later tested, must remain explicitly labeled as the 10x12 square-lattice proxy unless exact hardware topology is authenticated.
