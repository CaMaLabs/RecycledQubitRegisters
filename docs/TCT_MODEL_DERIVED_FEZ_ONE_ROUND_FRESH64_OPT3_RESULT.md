# TCT model-derived one-round Fez fresh-64 optimization result

Date: 2026-09-21

## Scope

Zero-QPU routing/calibration sweep of the one-round, 10-qubit model-derived TCT threshold predicate on authenticated `ibm_fez` connectivity, using 64 sampled connected patches, optimization level 3, patch seed `8675309`, and transpiler seeds `8776,2026,9401,42,1337`.

This follows the negative paired QPU pilot and its ideal semantic postmortem. It is a compiler/calibration engineering study only; it is not fusion validation and not a hardware success-probability estimate.

## Result

Best sampled CZ / calibration exposure candidate:

- patch: 36
- transpiler seed: 2026
- CZ: 462
- depth: 1173
- summed calibrated CZ error exposure (`sum p`): 1.102
- independent no-CZ-error proxy: `log10 = -0.479`
- calibrated critical path: 36.0 us
- duration / median T1: 0.249
- duration / median T2: 0.470

Minimum-duration sampled candidate:

- patch: 14
- seed: 9401
- CZ: 475
- critical path: 33.9 us
- `sum p`: 1.235

## Comparison with submitted pilot

The submitted one-round pilot used a 634-CZ circuit with depth 1659, `sum p = 1.295`, and a 51.2 us calibrated critical path. The fresh patch-36 result therefore materially reduces routed gate count, depth, and duration, and modestly reduces calibration-weighted CZ exposure.

However, it does not meet the stronger post-pilot target of roughly `<450` CZ and `sum p < 0.8`. In addition, patch 36 has a worse duration/T2 ratio than the submitted patch despite its shorter absolute duration, reflecting poorer T2 on that physical region.

## Decision

Do not submit another QPU job from this routing result alone. Further broad patch hunting is likely to have diminishing returns. The next zero-QPU step should challenge the logical phase synthesis itself, especially the multi-controlled phase construction used in the model-derived oracle and 9-parameter diffuser, while preserving the exact same finite-codebook predicate and ideal semantics.

## Boundaries

- Best values are among this sampled 64-patch ensemble, not a global Fez optimum.
- Calibration metadata changes over time.
- `sum p` and independent products are engineering proxies, not measured fidelity or success probability.
- No QPU job submitted.
