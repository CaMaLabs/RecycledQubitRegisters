# K128: complementary phase predicates

This follows K127 with a narrower identity. For phase terms on f and not-f, the combined exponent is a constant plus one residual phase. The constant can be represented without a rotation only when it is 0 or 1 half-turn modulo 2, allowing a no-cost global NEG when needed.

The exact predicate screen found no complementary pair among the 48 Z_POW sites on the pinned baseline. No candidate was emitted and no verifier run was needed.

Reproduce with the existing kaggle-k001 venv by invoking k128_complement_phase_factor.py with the pinned baseline and a fresh result path.
