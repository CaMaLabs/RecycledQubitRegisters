# TCT semantic-factored oracle — exhaustive statevector validation

Date: 2026-09-18

## Scope

This records the zero-QPU exhaustive statevector validation of the two shared-common-control fixed-instance TCT phase-oracle implementations.

The validation tests the actual gate constructions, not only their synthesized Boolean expressions. Every one of the 512 basis states of the 9-qubit parameter register is tested with the clean ancilla initialized to `|0>`.

## Frozen marked set

Marked parameter-register basis states:

`[14, 15, 30, 31, 46, 47, 63, 79]`

Logical parameter bits: 9.

## Results

### Four-cube common-factored oracle

- passed: `True`
- states tested: 512
- failures: 0
- maximum phase error: `1.244e-14`
- maximum leakage: `2.487e-14`

### Three-term ESOP common-factored oracle

- passed: `True`
- states tested: 512
- failures: 0
- maximum phase error: `1.711e-14`
- maximum leakage: `3.419e-14`

For every basis state, the validator checks that:

1. the intended minus phase is applied iff the parameter state is one of the eight marked states;
2. no amplitude leaks to a different parameter state beyond numerical tolerance; and
3. the clean ancilla returns to `|0>`.

The observed residual errors are at numerical floating-point/statevector tolerance scale.

## Interpretation

The six-round semantic-factored compiler result can now be treated as a logically validated fixed-instance oracle construction. In particular, the best `three_term_esop_common_factored` circuit is not merely a compiler optimization of an unchecked Boolean expression; its shared-ancilla implementation has been exhaustively checked over the complete 9-bit input space.

This validation does not change the methodological boundary: the oracle exploits structure in a frozen TCT truth table. It is not a scalable coherent implementation of the FAIR-MAST-seeded reduced-order loss formula, does not establish end-to-end quantum advantage, and does not validate fusion physics.

## Next step

Route the validated six-round, 10-qubit semantic-factored ESOP circuit onto exact-width physical patches drawn from IBM Fez heavy-hex topology and the explicitly labeled 10x12 square-lattice Nighthawk/Phoenix proxy. Compare interaction-fixed and Qiskit-auto layout without submitting a QPU job.
