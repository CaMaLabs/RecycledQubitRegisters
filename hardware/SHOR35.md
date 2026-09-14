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

```bash
python hardware/ibm_shor35_matched.py \
  --backend ibm_fez \
  --phase-bits 6 \
  --shots 512 \
  --transpile-only
```

No QPU job is submitted. Inspect width, depth, CZ count, selected region, and MCM calibration before running hardware.

## Matched hardware run

```bash
python hardware/ibm_shor35_matched.py \
  --backend ibm_fez \
  --phase-bits 6 \
  --shots 512 \
  --max-execution-time 120
```

The output reports factor recovery, Wilson intervals, Hellinger fidelity and total-variation distance to the exact finite-precision order-12 QPE distribution, plus matched wide/recycled resource counts.

## Replicate N=21 first

Before spending QPU time on `N=35`, repeat the successful `N=21` matched benchmark once more:

```bash
python hardware/ibm_shor21_matched.py \
  --backend ibm_fez \
  --phase-bits 6 \
  --shots 512 \
  --max-execution-time 90
```

That replication checks whether the previously observed `41.80%` recycled vs `25.59%` wide result persists under a new calibration snapshot.
