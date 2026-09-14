# IBM Fez affine-encoded Shor/order-finding result: N=35

This benchmark uses an affine 4-qubit encoding of the `N=35`, `a=2`, order-12 modular orbit. The affine basis preserves the same coherent twelve-state orbit while replacing the earlier high-order-MCX natural-label synthesis with low-cost controlled affine networks.

The encoded work orbit is

`4 -> 9 -> 14 -> 7 -> 8 -> 13 -> 6 -> 11 -> 12 -> 5 -> 10 -> 15 -> 4`,

corresponding in order to

`1 -> 2 -> 4 -> 8 -> 16 -> 32 -> 29 -> 23 -> 11 -> 22 -> 9 -> 18 -> 1 (mod 35)`.

This remains a compiled-orbit experiment, not a generic reversible modular multiplier.

## Resource improvement

The original natural-label six-bit recycled circuit compiled to depth 1209 with 388 CZ gates. The affine six-bit circuit reduced this to depth 466 and 137 CZ gates while remaining at five logical qubits.

In the first successful eight-bit calibration snapshot, optimization level 3 produced:

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 12 | **5** |
| Compiled depth | 788 | **607** |
| Circuit size | 1372 | **782** |
| CZ gates | 331 | **175** |

Thus the eight-bit recycled circuit used about 58.3% fewer simultaneous logical qubits, 23.0% less compiled depth, 43.0% smaller circuit size, and 47.1% fewer CZ gates than wide in that snapshot.

## Six-bit boundary run

The first affine hardware run used six phase bits and 512 shots per architecture. Its permissive factor-recovery metric was 44.34% recycled versus 43.75% wide, but the corresponding uniform-noise baseline was 42.1875%. The strict direct-order metric was 2.148% recycled and 3.125% wide, versus a 3.125% uniform baseline. Distribution metrics were also close to uniform.

Therefore the six-bit affine run did **not** demonstrate preserved order-12 information strongly enough to claim successful quantum factorization. It established that the synthesis bottleneck had been removed while the selected precision still gave poor signal discrimination.

## Eight-bit hardware run 1

The same affine `N=35`, `a=2`, `r=12` problem was then run at eight phase bits as a matched same-job comparison with 512 shots per architecture.

| Metric | Wide | Recycled |
|---|---:|---:|
| Factor-recovery metric | 12.50% | **40.23%** |
| Strict direct-order recovery | 2.34375% | **5.859375%** |
| Strict direct-order shots | 12/512 | **30/512** |
| Hellinger fidelity to ideal | 0.1951 | **0.5236** |
| Total-variation distance to ideal | 0.8448 | **0.5723** |
| Zero-phase probability | 0.586% | **3.516%** |

The recycled-minus-wide permissive factor-recovery difference was **+27.734375 percentage points**, about **10.61 standard errors** under the same independent-binomial approximation used elsewhere in this repository.

For a uniform random eight-bit distribution under the same order-12 reference and post-processing rules:

- permissive verified-multiple factor-recovery baseline = **12.890625%**;
- strict direct-order baseline = **2.34375%**;
- Hellinger fidelity to ideal = **0.23487**;
- total-variation distance to ideal = **0.82571**.

The recycled run 1 result was materially separated from uniform noise on every primary signal metric. The wide result was at the strict direct-order noise floor and close to the random permissive baseline.

For the recycled strict metric, 30 direct-order successes were observed where the uniform baseline predicts 12 on average. Under a simple fixed-baseline binomial model, the excess corresponds to a one-sided tail probability of approximately **6.4e-6**. This does not include calibration drift, routing systematics, or other hardware correlations, so it is a shot-noise significance estimate rather than a full experimental uncertainty model.

## Eight-bit replication run 2

The identical eight-bit affine benchmark was repeated on a later Fez calibration snapshot with the same benchmark code and high-level settings (`phase_bits=8`, 512 shots, optimization level 3).

| Metric | Wide | Recycled |
|---|---:|---:|
| Factor-recovery metric | 13.671875% | **45.5078125%** |
| Strict direct-order recovery | 2.9296875% | **7.03125%** |
| Strict direct-order shots | 15/512 | **36/512** |
| Hellinger fidelity to ideal | 0.1932 | **0.5394** |
| Total-variation distance to ideal | 0.8399 | **0.5489** |

The recycled-minus-wide permissive factor-recovery gap was **+31.8359375 percentage points**, about **11.91 standard errors** under the same independent-binomial comparison used by the runner.

Relative to uniform output, replication run 2 gave:

- recycled permissive recovery: **45.5078% vs 12.8906% uniform** (`+32.6172 pp`);
- recycled strict direct-order recovery: **7.03125% vs 2.34375% uniform** (`+4.6875 pp`);
- recycled Hellinger fidelity: **0.5394 vs 0.2349 uniform**;
- recycled TV distance: **0.5489 vs 0.8257 uniform**.

Wide remained close to the random baseline: permissive recovery was **13.6719%**, strict direct-order recovery was **2.9297%**, Hellinger fidelity was **0.1932**, and TV distance was **0.8399**.

For the recycled strict metric, 36 direct-order successes were observed where the uniform baseline predicts 12 on average. Under a simple fixed-baseline binomial shot-noise model, the exact one-sided probability of observing at least 36 such successes is approximately **9.73e-9**. This again does not model calibration drift, routing systematics, multiple-testing choices, or other hardware correlations.

The replication recovered about **45.27% of the ideal-minus-uniform permissive signal margin** and **37.11% of the ideal-minus-uniform strict direct-order margin**.

### Descriptive two-run consistency

Across the two separate hardware jobs, without treating them as one randomized experiment:

- recycled permissive recovery: `206/512 + 233/512 = 439/1024 = 42.87%`;
- wide permissive recovery: `64/512 + 70/512 = 134/1024 = 13.09%`;
- recycled strict direct-order recovery: `30/512 + 36/512 = 66/1024 = 6.45%`;
- wide strict direct-order recovery: `12/512 + 15/512 = 27/1024 = 2.64%`.

These pooled fractions are descriptive only because the two runs were taken under different calibration snapshots.

## Interpretation

The eight-bit result has now reproduced across two separate hardware jobs. In both runs the recycled implementation remained substantially above the random-output floor on permissive recovery, strict direct-order recovery, Hellinger fidelity, and total-variation distance. The matched wide implementation remained near the random-output floor.

A conservative summary is:

> In two matched IBM Fez runs on a compiled `N=35`, `a=2`, order-12 Shor instance, an affine-encoded recycled phase-register implementation repeatedly recovered identifiable order-12 information above random-output baselines while the matched wide implementation remained near the noise floor. Recycled strict direct-order recovery was 5.86% in the first run and 7.03% in the replication, versus a 2.34% uniform-output baseline. The implementation used five simultaneous logical qubits rather than twelve in the eight-bit comparison.

The progression is important:

1. natural-label `N=35` exposed a synthesis-depth wall;
2. affine recoding reduced the modular-work cost dramatically;
3. six-bit affine execution remained near the random-output floor because phase precision gave weak discrimination;
4. eight-bit affine execution recovered identifiable order-12 signal;
5. a second independent hardware job reproduced and strengthened the result.

This result should **not** be interpreted as scalability to cryptographic RSA. The modular work register is an exact compiled orbit representation specific to `N=35`, `a=2`. A general large-semiprime Shor implementation still requires scalable reversible modular arithmetic and fault-tolerant hardware.