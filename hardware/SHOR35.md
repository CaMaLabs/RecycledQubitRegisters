# Real IBM QPU compiled Shor test: N=35

`ibm_shor35_matched.py` extends the matched register-recycling hardware benchmark to `N=35`, `a=2`.

## Why N=35

For `a=2 mod 35`, the order is `r=12`:

`2^12 mod 35 = 1`.

Once `r=12` is recovered,

- `gcd(2^6 - 1, 35) = gcd(63,35) = 7`
- `gcd(2^6 + 1, 35) = gcd(65,35) = 5`

so the factors are `(5,7)`.

This is a harder order-finding problem than the `N=21`, `r=6` test because the orbit doubles from six to twelve states.

## Compiled orbit encoding

The multiplicative orbit is

`1, 2, 4, 8, 16, 32, 29, 23, 11, 22, 9, 18`.

These twelve states are encoded as labels `0..11` in a 4-qubit coherent work register. Computational states `12..15` are left fixed. Multiplication by 2 modulo 35 becomes `+1 mod 12` on the encoded orbit, so `U^(2^k)` becomes a controlled shift by `2^k mod 12`.

This is an exact compiled orbit encoding. It is **not** a generic reversible 6-qubit modular multiplier and should not be interpreted as evidence that cryptographic RSA sizes are tractable.

## Architectures

With `m` phase bits:

- wide: `m` phase qubits + 4 work qubits;
- recycled: 1 reusable phase qubit + 4 work qubits.

Both circuits are submitted in the same IBM job and start from the same physical work-register sites. The transpiler may route logical states later in the circuit.

## Self-test

```bash
python hardware/ibm_shor35_matched.py \
  --phase-bits 6 \
  --self-test
```

The script exhaustively verifies the compiled `+1`, `+2`, `+4`, and `+8 mod 12` work-register permutations on all 16 computational basis states.

## Transpile-only preflight

The September 13/14, 2026 Fez preflight passed the exact orbit self-test. At optimization level 2, the recycled circuit compiled to depth 1217 with 394 CZ gates, while wide compiled to depth 1347 with 457 CZ gates. Optimization level 3 reduced recycled slightly to depth 1209 and 388 CZ gates; the wide circuit remained at depth 1347 and 457 CZ gates.

At six phase bits this is a 10-qubit wide circuit versus a 5-qubit recycled circuit. The level-3 preflight therefore gives a 50% simultaneous logical-width reduction, about a 10.2% depth reduction, and about a 15.1% CZ reduction. The selected Fez region reported a local mean CZ error of about 0.2558% and a recycled-ancilla `measure_2` error of about 0.2686% at preflight time.

Use optimization level 3 for the hardware run:

```bash
python hardware/ibm_shor35_matched.py \
  --backend ibm_fez \
  --phase-bits 6 \
  --shots 512 \
  --optimization-level 3 \
  --transpile-only
```

No QPU job is submitted in preflight mode.

## Matched hardware run

```bash
python hardware/ibm_shor35_matched.py \
  --backend ibm_fez \
  --phase-bits 6 \
  --shots 512 \
  --optimization-level 3 \
  --max-execution-time 120
```

The output reports factor recovery, Wilson intervals, Hellinger fidelity and total-variation distance to the exact finite-precision order-12 QPE distribution, plus matched wide/recycled resource counts.

### Observed result

At 512 shots each, recycled measured **41.99%** factor recovery and wide measured **41.60%**. The difference was only **+0.39 percentage points**, about **0.13 standard errors**. Distribution quality was also nearly identical: Hellinger fidelity was 0.5562 recycled vs 0.5609 wide, and TV distance was 0.6001 recycled vs 0.6049 wide.

However, this run sits at the post-processor's random-noise floor. Under a uniform 6-bit distribution, the verified-multiple recovery rule accepts **27 of 64 possible bitstrings = 42.1875%**. A uniform distribution also has Hellinger fidelity **0.5472** and TV distance **0.6075** to the exact finite-precision order-12 reference.

Therefore the ~42% hardware factor-recovery metric is **not evidence of preserved quantum order information** in this run. Both wide and recycled outputs are only marginally distinguishable from uniform noise under these metrics. The meaningful result is the surviving resource reduction—5 vs 10 logical qubits and 388 vs 457 CZ gates—not a factoring-performance advantage.

Treat `N=35` as the current **hardware/synthesis boundary** for this compiled-orbit implementation. Do not increase `N` again without reducing the entangling-gate burden and tightening the post-processing metric.

See `results/hardware/SHOR35_RESULTS.md` and `results/hardware/shor35_matched_compare.csv`.

## Replicated N=21 control

The successful `N=21`, `a=2`, `r=6` matched benchmark was repeated before the `N=35` attempt. The replication again favored recycled: 41.99% factor recovery versus 26.95% wide, a +15.04 percentage-point difference at about 5.13 standard errors. The recycled distribution also remained closer to the ideal order-6 QPE reference (Hellinger fidelity 0.6566 vs 0.5382; TV distance 0.4753 vs 0.6051).

That replication supports treating the earlier `N=21` advantage as reproducible rather than a single favorable calibration snapshot.
