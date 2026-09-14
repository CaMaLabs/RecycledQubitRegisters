# IBM Fez affine-encoded Shor/order-finding result: N=35

This benchmark uses an affine 4-qubit encoding of the `N=35`, `a=2`, order-12 modular orbit. The affine basis preserves the same coherent twelve-state orbit while replacing the earlier high-order-MCX natural-label synthesis with low-cost controlled affine networks.

The encoded work orbit is

`4 -> 9 -> 14 -> 7 -> 8 -> 13 -> 6 -> 11 -> 12 -> 5 -> 10 -> 15 -> 4`,

corresponding in order to

`1 -> 2 -> 4 -> 8 -> 16 -> 32 -> 29 -> 23 -> 11 -> 22 -> 9 -> 18 -> 1 (mod 35)`.

This remains a compiled-orbit experiment, not a generic reversible modular multiplier.

## Resource improvement

The original natural-label six-bit recycled circuit compiled to depth 1209 with 388 CZ gates. The affine six-bit circuit reduced this to depth 466 and 137 CZ gates while remaining at five logical qubits.

At eight phase bits, optimization level 3 on `ibm_fez` produced:

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Compiled depth | 788 | **607** |
| Circuit size | 1372 | **782** |
| CZ gates | 331 | **175** |

Thus the eight-bit recycled circuit used about 58.3% fewer simultaneous logical qubits, 23.0% less compiled depth, 43.0% smaller circuit size, and 47.1% fewer CZ gates than wide.

## Six-bit boundary run

The first affine hardware run used six phase bits and 512 shots per architecture. Its permissive factor-recovery metric was 44.34% recycled versus 43.75% wide, but the corresponding uniform-noise baseline was 42.1875%. The strict direct-order metric was 2.148% recycled and 3.125% wide, versus a 3.125% uniform baseline. Distribution metrics were also close to uniform.

Therefore the six-bit affine run did **not** demonstrate preserved order-12 information strongly enough to claim successful quantum factorization. It established that the synthesis bottleneck had been removed while the selected precision still gave poor signal discrimination.

## Eight-bit hardware run

The same affine `N=35`, `a=2`, `r=12` problem was then run at eight phase bits, again as a matched same-job comparison with 512 shots per architecture.

| Metric | Wide | Recycled |
|---|---:|---:|
| Factor-recovery metric | 12.50% | **40.23%** |
| Wilson 95% interval | 9.91%-15.65% | **36.07%-44.54%** |
| Hellinger fidelity to ideal | 0.1951 | **0.5236** |
| Total-variation distance to ideal | 0.8448 | **0.5723** |
| Zero-phase probability | 0.586% | **3.516%** |

The recycled-minus-wide permissive factor-recovery difference was **+27.734375 percentage points**, about **10.61 standard errors** under the same independent-binomial approximation used elsewhere in this repository.

### Eight-bit noise-floor comparison

For a uniform random eight-bit distribution under the same order-12 reference and post-processing rules:

- permissive verified-multiple factor-recovery baseline = **12.890625%**;
- strict direct-order baseline = **2.34375%**;
- Hellinger fidelity to ideal = **0.23487**;
- total-variation distance to ideal = **0.82571**.

The recycled eight-bit distribution is therefore materially separated from uniform noise by the distribution-level metrics:

- Hellinger fidelity: **0.5236 recycled vs 0.2349 uniform**;
- TV distance: **0.5723 recycled vs 0.8257 uniform**;
- permissive factor recovery: **40.23% recycled vs 12.89% uniform**.

The wide result, by contrast, is close to the random permissive baseline and is worse than uniform on the Hellinger/TV comparison.

This is the first `N=35` affine hardware run in this series to show clear distribution-level order-12 structure above the random-output floor. The strict direct continued-fraction/order-recovery metric stored in the raw result JSON should still be audited before making the strongest possible factorization claim.

Run:

```bash
python hardware/analyze_shor_noise_floor.py \
  results/ibm_shor35_affine/ibm_shor35_affine_8b_20260913_200845.json
```

If the strict direct-order rate is also materially above its **2.34375%** uniform baseline, then the eight-bit affine run supports a conservative statement that the recycled hardware implementation recovered identifiable order-12 signal sufficient for nontrivial factor recovery on the compiled `N=35` instance.

## Interpretation

The progression is important:

1. natural-label `N=35` exposed a synthesis-depth wall;
2. affine recoding reduced the modular-work cost dramatically;
3. six-bit affine execution remained near the random-output floor because phase precision gave weak discrimination;
4. eight-bit affine execution retained manageable hardware cost while producing a recycled distribution clearly separated from uniform noise and from the matched wide circuit.

Do not interpret this as scalability to cryptographic RSA. The modular work register is an exact compiled orbit representation specific to `N=35`, `a=2`. A general large-semiprime Shor implementation still requires scalable reversible modular arithmetic and fault-tolerant hardware.
