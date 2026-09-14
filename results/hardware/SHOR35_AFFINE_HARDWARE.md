# IBM Fez affine-encoded Shor/order-finding result: N=35

This run used the affine 4-qubit encoding of the `N=35`, `a=2`, order-12 modular orbit. The affine encoding preserves the same 12-state coherent orbit while dramatically reducing the controlled modular-power synthesis cost relative to the earlier natural-label encoding.

## Transpiled resources

At six phase bits and optimization level 3 on `ibm_fez`:

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 10 | **5** |
| Compiled depth | 583 | **466** |
| Circuit size | 889 | **603** |
| CZ gates | 212 | **137** |

Relative to the previous natural-label `N=35` recycled circuit (`depth=1209`, `CZ=388`), the affine recycled circuit reduced depth by about 61.5% and CZ count by about 64.7%.

## Hardware result

Matched same-job run, 512 shots per architecture:

| Metric | Wide | Recycled |
|---|---:|---:|
| Factor-recovery metric | 43.75% | **44.34%** |
| Strict direct-order recovery | **3.125%** | 2.148% |
| Wilson 95% interval | 39.52%-48.08% | **40.09%-48.67%** |
| Hellinger fidelity to ideal | 0.4695 | **0.5309** |
| Total-variation distance to ideal | 0.6771 | **0.6124** |
| Zero-phase probability | 1.95% | 4.69% |

The recycled-minus-wide factor-recovery difference was only **+0.5859375 percentage points**, about **0.19 standard errors**, so there is no meaningful direct accuracy separation between the two architectures in this run.

## Uniform-noise audit

For a uniform random six-bit distribution under the current `N=35` post-processing rules:

- permissive verified-multiple factor-recovery baseline = **42.1875%**;
- strict direct-order recovery baseline = **3.125%**;
- Hellinger fidelity to the exact order-12 reference = **0.5472**;
- total-variation distance to the exact order-12 reference = **0.6075**.

Observed values were:

- recycled permissive factor recovery = **44.3359%** (`+2.1484 pp` above uniform);
- wide permissive factor recovery = **43.75%** (`+1.5625 pp` above uniform);
- recycled strict direct-order recovery = **2.1484%**, below the **3.125%** uniform baseline;
- wide strict direct-order recovery = **3.125%**, exactly equal to the uniform baseline;
- recycled Hellinger/TV = **0.5309 / 0.6124**;
- wide Hellinger/TV = **0.4695 / 0.6771**.

Therefore this run does **not** demonstrate preserved order-12 information strongly enough to claim successful quantum factorization of `35`. The affine encoding is a major synthesis/resource improvement, but the measured phase distribution remains at or near the random-output floor under the strict metric.

## Interpretation

The important positive result is architectural: the exact same order-12 orbit problem was recoded into an affine basis that cut the recycled circuit from 388 to 137 CZ gates and from depth 1209 to 466 while retaining five simultaneous logical qubits. The negative result is equally important: that resource reduction alone did not recover a statistically identifiable order-12 signal on this Fez run.

This separates two bottlenecks that were previously confounded:

1. the original natural-label synthesis was unnecessarily expensive;
2. after fixing that synthesis cost, hardware noise/routing/dynamic-circuit effects still dominate enough to erase the strict order signal.

Do not move to a larger modulus from this result. The next experiments should improve phase-estimation discriminability and/or physical mapping while preserving the affine modular-work encoding.
