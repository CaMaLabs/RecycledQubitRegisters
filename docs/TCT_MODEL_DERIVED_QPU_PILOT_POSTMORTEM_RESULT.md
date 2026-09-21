# TCT model-derived one-round QPU pilot postmortem

Date: 2026-09-21

## Scope

This records the zero-QPU semantic/compiler postmortem for IBM Runtime job `daoje8gpqrnc739a3jn0`, the first paired hardware pilot of the finite-codebook, model-derived TCT threshold predicate.

The hardware pilot had shown no statistically meaningful amplification:

- uniform baseline: `17 / 1024 = 0.016602`
- one-round candidate: `19 / 1024 = 0.018555`
- measured ratio: `1.117647`
- two-proportion z approximation: `0.3363`

The purpose of this postmortem was to distinguish a compiler/layout/measurement semantic problem from a hardware-execution/noise failure.

## Exact compile reproduction

Recorded submitted candidate:

- CZ: `634`
- depth: `1659`
- size: `2640`

Reproduced candidate using the same frozen patch and transpiler seed:

- CZ: `634`
- depth: `1659`
- size: `2640`

`exact_stats=True`

Thus the postmortem reproduced the recorded compiled-circuit resource counts exactly.

## Ideal semantic checks

Search space: 512 parameter states.

Marked states: 8.

Uniform marked-state probability:

`0.015625000`

One-round ideal Grover marked-state probability:

`0.134826660`

Observed under ideal statevector evolution:

- transpiled baseline: `0.015625000`
- logical model-derived one-round circuit: `0.134826660`
- reproduced transpiled one-round candidate: `0.134826660`

Ancilla cleanup:

- logical ancilla `P(1) = 1.658e-31`
- maximum unmeasured transpiled-qubit `P(1) = 1.023e-29`

All semantic checks passed:

- baseline measurement map complete;
- candidate measurement map complete;
- logical model probability matches expected;
- logical clean ancilla returns to zero;
- transpiled baseline probability matches uniform;
- transpiled candidate probability matches one-round ideal;
- transpiled unmeasured ancilla returns to zero;
- candidate compile statistics exactly reproduced.

`semantic_checks_pass=True`

## Hardware comparison

Hardware baseline:

`17 / 1024 = 0.016602`

Wilson 95% interval:

`[0.010391, 0.026426]`

Hardware candidate:

`19 / 1024 = 0.018555`

Wilson 95% interval:

`[0.011910, 0.028798]`

Measured candidate/baseline ratio:

`1.117647`

Ideal candidate/baseline ratio:

`8.628906`

The observed excess marked fraction was only about 1.64% of the ideal one-round excess over baseline.

Under the ideal one-round probability (`p = 0.134826660`), 1024 shots would have an expectation of about 138 marked outcomes. The observed 19 marked outcomes are therefore dramatically inconsistent with ideal circuit behavior. This comparison is descriptive of the hardware result; it is not a complete physical noise model.

## Classification

`IDEAL_TRANSPILED_SEMANTICS_PASS_HARDWARE_AMPLIFICATION_NOT_OBSERVED`

The reproduced native circuit preserves the intended one-round marked-state amplification under ideal evolution, the measurement mapping is complete, the ancilla returns cleanly, and the compiler statistics reproduce exactly. Therefore the negative hardware result is not explained by a logical-oracle bug, bit-order bug, measurement-map bug, or failure to reproduce the submitted compile.

The evidence is consistent with hardware/execution effects erasing the Grover interference on this Fez run. This postmortem does not identify a unique physical mechanism: coherent error, correlated error, crosstalk, leakage, decoherence, calibration drift, gate-dependent phase error, and other execution effects are not individually resolved by this audit.

## Next engineering direction

Do not repeat the same 634-CZ QPU circuit immediately.

The next useful work should remain zero-QPU and target a substantially smaller one-round physical circuit. A fresh one-round-only Fez placement/synthesis search should be performed rather than reusing patches selected from the six-round study. The target should be to reduce routed CZ count and calibrated exposure materially below the submitted `634 CZ / sum_p ~= 1.295 / 51.2 us` implementation before another hardware run is considered.

## Boundaries

- Zero QPU jobs submitted by the postmortem.
- This result validates ideal semantics of a reproduced transpilation; it does not prove a complete physical noise diagnosis.
- Calibration products remain engineering proxies, not measured circuit fidelity.
- Finite-codebook reduced-order TCT threshold predicate only.
- No fusion-physics validation.
- No practical or asymptotic quantum-advantage claim.
