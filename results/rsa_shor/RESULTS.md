# End-to-end simulated RSA/Shor results

These runs use only **self-generated toy RSA-like semiprimes**. The factorization path receives `N` and QPE measurement samples; the hidden factors are used only for scoring. Lucky `gcd(a,N)` factors are rejected so the benchmark specifically exercises order finding.

## What was tested

Pipeline:

`N -> choose coprime a -> modular-order QPE samples -> continued fractions -> repeated-sample LCM -> gcd(a^(r/2) +/- 1, N) -> recover p,q -> reconstruct d -> decrypt ciphertext`

Two simulator levels are included:

1. `simulation/rsa_shor_end_to_end.py`: compact exact-functional Shor simulator. It internally computes the cyclic order of modular multiplication only so it can sample the exact ideal QPE statistics efficiently. The factoring code does not receive that order directly.
2. `simulation/rsa_shor_statevector.py`: explicit toy-size validation. The recycled implementation evolves the modular work-register statevector and a single ancilla through controlled modular-multiplication permutations, mid-circuit measurement/reset, and feed-forward. The wide implementation constructs the exact post-modular-exponentiation state in block-sparse form and applies the inverse QFT.

Neither script is a practical RSA-breaking tool, and the compact simulator is not a gate-count-accurate fault-tolerant modular-arithmetic model.

## Single-shot sanity challenge

One coprime base, one QPE sample, 200 fresh keys per size:

| N bits | Factor + decrypt success | gcd shortcuts | Wide modeled width* | Recycled modeled width* |
|---:|---:|---:|---:|---:|
| 16 | 26.0% | 0% | 48 | 17 |
| 20 | 27.5% | 0% | 60 | 21 |

This intentionally produces failures, confirming that the benchmark is not trivially recovering the hidden factors through post-processing.

## Repeated Shor samples

Four QPE shots per base, up to four coprime bases, 100 fresh keys per size:

| N bits | Factor success | Decrypt success | Median QPE shots | Wide modeled width* | Recycled modeled width* |
|---:|---:|---:|---:|---:|---:|
| 16 | 97% | 97% | 3 | 48 | 17 |
| 20 | 100% | 100% | 2 | 60 | 21 |

## Broad compact-simulator sweep

Eight QPE shots per base, up to 16 coprime bases, 20 trials per size:

| N bits | Trials | Factor success | Decrypt success | Median QPE shots | Width reduction* |
|---:|---:|---:|---:|---:|---:|
| 10 | 20 | 100% | 100% | 5 | 2.73x |
| 12 | 20 | 100% | 100% | 3 | 2.77x |
| 14 | 20 | 100% | 100% | 2 | 2.80x |
| 16 | 20 | 100% | 100% | 3 | 2.82x |
| 18 | 20 | 100% | 100% | 2 | 2.84x |
| 20 | 20 | 100% | 100% | 2 | 2.86x |

## Explicit work-register statevector validation

The explicit simulator uses the actual reversible modular-multiplication permutation on the work register and simulates the recycled phase ancilla through measurement, reset, and feed-forward.

| N bits | Trials | Distinct-modulus note | Wide factor/decrypt | Recycled factor/decrypt | Wide width* | Recycled width* | Dense-wide statevector equivalent |
|---:|---:|---|---:|---:|---:|---:|---:|
| 8 | 30 | balanced 4+4-bit primes force `N=143=11x13`; trials vary bases/samples, not modulus | 30/30 | 30/30 | 24 | 9 | 256 MiB |
| 9 | 10 | multiple generated moduli (`299`, `319`, `341`, `377`, `403`) | 10/10 | 10/10 | 27 | 10 | 2048 MiB |

For the 9-bit run, the median QPE-shot counts were 2.5 wide and 3.0 recycled. The dense 27-qubit complex128 statevector equivalent is 2 GiB; the block-sparse wide implementation avoids materializing all of it simultaneously, while the recycled trajectory evolves only the modular work register plus one phase ancilla.

`U_a` is represented explicitly as a reversible permutation on the work register:

`|y> -> |a*y mod N>` for `y < N`, with basis states `y >= N` left unchanged.

## Interpretation

The ideal wide and recycled QPE algorithms have the same mathematical measurement distribution; therefore this simulation does **not** claim an ideal accuracy advantage for recycling. The demonstrated benefit here is reduced simultaneous phase-register width while preserving end-to-end factoring semantics.

The separate IBM Fez experiments in `results/hardware/` provide the real-hardware evidence that, on that backend and workload, the recycled phase register can also outperform the wider phase circuit under noise.

\* Width counts the `n`-qubit modular work register plus either `m=2n` phase qubits (wide) or one recyclable phase qubit. Reversible modular-arithmetic ancillas are excluded equally from both sides; a full fault-tolerant implementation would require additional ancillas and much larger gate counts.
