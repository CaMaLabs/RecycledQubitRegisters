# TCT grid-factored shift oracle — validation result

Date: 2026-09-19

## Scope

This records the zero-QPU validation of the grid-factored/shift TCT arithmetic oracle after the one-round compiler result of 7,126 CZ / depth 22,081 / width 25.

The validation checks the transformed arithmetic contract rather than only the final compiler statistics. The implementation preserves the frozen 8-state marked classification across all 320 valid parameter scenarios, represents the bias/boost event base as an exact four-bit multilinear polynomial, and uses controlled shifts for the event-rate multiplier.

## Validation result

```text
===== TCT GRID-FACTORED SHIFT ORACLE VALIDATION =====
classification_passed=True tested_scores=320 marked=8
base_polynomial_passed=True assignments=16 nonzero_monomials=9
headroom_passed=True max_shifted_base=23760 modulus=65536
full_width_shift_passed=True tested=64 max_probability_error=0.000e+00 failures=0
qft_adder_self_test=True all_passed=True
```

The validation establishes:

- exact reproduction of the frozen marked set over all 320 valid parameter scenarios;
- exact evaluation of the 16-point bias/boost base-event polynomial;
- sufficient 16-bit accumulator headroom for the maximum shifted event base;
- exact controlled-shift behavior at the actual 16-bit accumulator width for all 64 tested base/event-code combinations, with zero observed statevector probability error;
- passing QFT constant-adder primitive self-test.

## Interpretation

With these checks passing, the 7,126-CZ / 22,081-depth one-round circuit can be treated as the current trusted coherent-arithmetic baseline for this frozen reduced-order TCT search problem.

This remains classification-exact rather than pointwise numerically identical to the earlier rounded event-table encoding. The transformed encoding reported a maximum reconstructed-loss error of about 0.0316624 while retaining the same eight marked scenarios.

## Boundaries

- Zero QPU jobs.
- Reduced-order FAIR-MAST-seeded TCT objective only.
- Validation of the implemented transformed arithmetic and search classification, not fusion-physics validity.
- No end-to-end quantum-speedup claim.
- No fault-tolerance, calibration, timing, or hardware-error model included.
