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
| Wilson 95% interval | 39.52%-48.08% | **40.09%-48.67%** |
| Hellinger fidelity to ideal | 0.4695 | **0.5309** |
| Total-variation distance to ideal | 0.6771 | **0.6124** |
| Zero-phase probability | 1.95% | 4.69% |

The recycled-minus-wide factor-recovery difference was only **+0.5859375 percentage points**, about **0.19 standard errors**, so there is no meaningful direct accuracy separation between the two architectures in this run.

## Uniform-noise context

For a uniform random six-bit distribution under the current `N=35` verified-multiple post-processor:

- factor-recovery baseline = **42.1875%**;
- Hellinger fidelity to the exact order-12 reference = **0.5472**;
- total-variation distance to the exact order-12 reference = **0.6075**.

The affine recycled result is only slightly above the uniform factor-recovery baseline (**44.34% vs 42.19%**) and is slightly *worse* than uniform on both Hellinger fidelity (**0.5309 vs 0.5472**) and TV distance (**0.6124 vs 0.6075**). The wide result is farther from ideal still.

Therefore this run should **not** yet be described as successful preserved order finding for `N=35`. The affine encoding is a major resource improvement, but the measured phase distribution is still near the random-output floor by distribution-level metrics.

The strict direct continued-fraction/order metric stored in the result JSON should be audited before making any stronger claim:

```bash
python hardware/analyze_shor_noise_floor.py \
  results/ibm_shor35_affine/ibm_shor35_affine_6b_20260913_200052.json
```

If the direct-order metric remains near the uniform baseline, the affine rewrite has solved the synthesis bottleneck but not yet recovered an identifiable order-12 signal on hardware.
