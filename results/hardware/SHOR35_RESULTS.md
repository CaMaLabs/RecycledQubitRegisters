# IBM Fez matched Shor/order-finding boundary result: N=35

This experiment extends the compiled-orbit hardware benchmark to `N=35`, `a=2`, whose multiplicative order is `r=12`.

The twelve-state orbit

`1 -> 2 -> 4 -> 8 -> 16 -> 32 -> 29 -> 23 -> 11 -> 22 -> 9 -> 18 -> 1 (mod 35)`

is encoded exactly in a 4-qubit coherent work register. This is a compiled orbit encoding, not a generic reversible modular multiplier.

## Matched same-job run

The level-3 transpiled circuits used the same initial physical work-register sites and were submitted together on `ibm_fez` with six phase bits and 512 shots each.

| Metric | Wide | Recycled |
|---|---:|---:|
| Logical qubits | 10 | **5** |
| Compiled depth | 1347 | **1209** |
| CZ gates | 457 | **388** |
| Factor-recovery metric | 41.60% | 41.99% |
| Wilson 95% interval | 37.41%-45.92% | 37.79%-46.31% |
| Hellinger fidelity to ideal | **0.5609** | 0.5562 |
| Total-variation distance to ideal | 0.6049 | **0.6001** |
| Zero-phase probability | 2.54% | 2.93% |

The recycled-minus-wide factor-recovery difference was only **+0.390625 percentage points**, about **0.13 standard errors**. There is no statistically meaningful accuracy separation at this depth.

## Critical uniform-noise baseline

The current post-processor allows verified multiples of continued-fraction denominators. At six phase bits for `N=35`, this accepts **27 of the 64 possible bitstrings** under a uniform distribution:

- uniform-noise factor-recovery baseline: **27/64 = 42.1875%**;
- observed recycled factor-recovery metric: **41.9922%**;
- observed wide factor-recovery metric: **41.6016%**.

Therefore the roughly 42% factor-recovery metric in this run is **not evidence of preserved quantum order information**. It is essentially the random-output acceptance rate of the permissive verified-multiple post-processor.

The distribution-level metrics support the same conclusion. For a uniform 6-bit distribution relative to the exact finite-precision order-12 reference:

- Hellinger fidelity = **0.5472**;
- total-variation distance = **0.6075**.

The hardware results are only marginally different from those noise-floor values:

- recycled: Hellinger **0.5562**, TV **0.6001**;
- wide: Hellinger **0.5609**, TV **0.6049**.

This run should therefore be reported as a **hardware/synthesis boundary result**, not as successful quantum factorization of 35.

## What remains valid

The resource comparison itself remains meaningful. Recycled used 5 versus 10 simultaneous logical qubits, depth 1209 versus 1347, and 388 versus 457 CZ gates. Thus register recycling still reduced width by 50% and CZ count by about 15%, but the compiled modular-orbit circuit had become deep enough that both architectures were close to the random-noise floor.

The immediately preceding `N=21`, `a=2`, `r=6` benchmark is qualitatively different: it reproduced on a second hardware run with recycled factor recovery near 42% versus about 27% wide, and its recycled distribution was materially closer to the exact order-6 reference. `N=35` marks the point where the present compiled-orbit synthesis no longer preserves enough structure for the existing factor-recovery metric to distinguish signal from uniform noise.

## Recommended next work

Do not increase `N` again with the current synthesis. Instead:

1. report a strict/direct continued-fraction recovery metric alongside the verified-multiple metric;
2. include an automatic uniform-noise baseline in every hardware result;
3. optimize the `+1 mod 12` and `+2 mod 12` controlled permutations to reduce multi-controlled-gate decomposition cost;
4. rerun `N=35` only after the entangling-gate count is materially lower.
