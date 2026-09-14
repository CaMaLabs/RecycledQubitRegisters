# Dark Star / Periodic-Table-of-Primes / Shor audit

This experiment tests the part of the Dark Star idea that can be stated cleanly and falsifiably: whether the primorial residue structure in the Periodic Table of Primes / kernel-factor-pair follow-up work provides useful candidate pruning, and whether any of that public residue information materially helps Shor order finding.

The implementation is `hardware/dark_star_ptp_shor_audit.py`. It is pure Python and submits no QPU jobs.

## Questions

The audit separates three different claims that should not be conflated:

1. **Factor wheel pruning.** For `M = 210, 2310, 30030`, only `phi(M)` residues are coprime to the wheel primes.
2. **Fermat midpoint pruning.** For `N = x^2-y^2`, a candidate `x` can be rejected cheaply unless `x^2-N` is a quadratic residue modulo `M`.
3. **Shor order information.** The public feature `N mod M` is tested against divisibility properties of the true multiplicative order `r` and `lambda(N)` on held-out synthetic semiprimes.

The true factors, `lambda(N)`, and `r` are validation labels only. They are never supplied to the candidate filter or predictor.

## Exact residue expectations

For the square-free primorial moduli used here:

| M | phi(M) | wheel density | ordinary unordered kernel pairs | special kernel pairs | mean midpoint QR survival |
|---:|---:|---:|---:|---:|---:|
| 210 | 48 | 48/210 | 24 | 28 | 1/8 |
| 2310 | 480 | 480/2310 | 240 | 248 | 1/16 |
| 30030 | 5760 | 5760/30030 | 2880 | 2896 | 1/32 |

The `24/28` structure at `M=210` follows directly from pairing each admissible factor residue `p` with `q = N p^{-1} (mod M)`. The special count occurs when the residue equation has fixed points `p=q` modulo the wheel.

The midpoint result is stronger than ordinary wheel filtering as a necessary-condition test. Averaged over unit `N` residues, each additional odd prime in the square-free modulus halves the surviving midpoint residues. This means average residue survival of `1/8`, `1/16`, and `1/32` for the three moduli above.

These are reductions in candidate residues / expensive exact-square tests, not asymptotic factoring breakthroughs. The modular rejection test itself still has a cost.

## First completed run

The default deterministic run completed with:

- `600` balanced Fermat semiprimes;
- `2000` semiprimes in the Shor-order audit;
- `16000` valid `(N,a)` order rows;
- zero QPU use.

Observed reduction in **expensive exact-square tests**:

| M | Mean reduction | Median reduction | Asymptotic midpoint-residue reduction |
|---:|---:|---:|---:|
| 210 | 4.417x | 3.708x | 8x |
| 2310 | 5.829x | 4.000x | 16x |
| 30030 | 6.684x | 5.000x | 32x |

The finite-search reductions are lower than the residue-level asymptotic values because many sampled Fermat searches terminate after only a small number of candidate `x` values. The result is nevertheless positive: the midpoint predicate removes real exact-square work rather than merely relabeling candidates.

## Shor result from the first audit

The raw public feature `N mod M` was evaluated with train/test splitting by whole semiprime so bases from the same `N` could not leak across folds.

At `M=210`, the strongest held-out order result was `3 | r`:

```text
mutual information: 0.0787 bits
baseline accuracy:  0.6366
feature accuracy:   0.6793
accuracy gain:      +0.0427
```

Most other order-divisibility targets gave negligible or negative held-out accuracy gain. Increasing the modulus to `2310` or `30030` substantially increased *in-sample* mutual information, but held-out majority prediction generally worsened. This is consistent with sparse high-cardinality residue categories rather than a robust large Shor shortcut.

A particularly important caution is that majority accuracy is a coarse metric. Public residue information can change conditional probabilities without flipping the most common class. Therefore the first audit does **not** prove that all Shor-relevant information is absent; it shows that raw `N mod M` lookup is not a convincing route to QPE-width reduction.

## Shor boundary

Shor does not search candidate factors directly. It estimates the multiplicative order `r` of a chosen base `a mod N`. Therefore a factor-residue sieve is not automatically a QPE reduction.

A large in-sample mutual-information number is not accepted as evidence by itself. A positive Shor result requires an explicit, public-information constraint that generalizes and can be connected to reduced order ambiguity, post-processing work, or circuit/QPE resources.

## Exact kernel-constraint follow-up

The next audit is implemented in:

```text
hardware/dark_star_shor_constraint_audit.py
```

It does not use raw residue classes as a giant categorical predictor. Instead, for every kernel factor-residue pair consistent with public `N mod M`, it records which odd wheel primes must divide at least one of `p-1` or `q-1`, and therefore divide `lambda(N)`.

For each `N mod M`, it computes:

- **guaranteed lambda primes**: forced by every kernel pair;
- **possible lambda primes**: allowed by at least one kernel pair;
- the number of distinct small-prime support signatures of `lambda(N)` still consistent with the public residue;
- the empirical rate at which a guaranteed divisor of `lambda(N)` also divides the actual Shor order `r` for the tested bases.

This distinction matters because `r | lambda(N)`: a guaranteed factor of `lambda(N)` is **not** automatically a guaranteed factor of `r`.

There is also an exact limitation worth testing explicitly. For unit `N`, the residue pair `(1, N mod M)` is always kernel-consistent, so the lambda-support signature containing **all** wheel primes is always possible. Public `N mod M` can therefore force some small-prime divisors of `lambda(N)`, but it cannot simply rule every candidate divisor out by residue logic alone.

Run:

```bash
cd ~/Downloads/RecycledQubitRegisters
git pull --rebase
python hardware/dark_star_shor_constraint_audit.py
```

This is also completely classical and submits no QPU jobs.

The useful ending blocks are:

```text
===== EXACT KERNEL-CONSTRAINT THEORY =====
===== EMPIRICAL CONSTRAINT SUMMARY =====
===== OVERALL =====
```

## Original audit run

```bash
cd ~/Downloads/RecycledQubitRegisters
git pull --rebase
source ~/ibm-6c2q-venv/bin/activate
python hardware/dark_star_ptp_shor_audit.py
```

The first receipt is written to:

```text
results/dark_star_ptp/dark_star_ptp_shor_audit.json
```

The exact-constraint follow-up writes:

```text
results/dark_star_ptp/dark_star_shor_constraint_audit.json
```

## Interpretation rules

A positive Dark Star result requires a reproducible reduction in expensive Fermat square tests or another concrete search cost, not merely a re-labelling of the same candidates.

A positive Shor result requires public residue information to reduce genuine order ambiguity enough to support an actual post-processing or QPE/circuit reduction. Knowing factor residues after factorization, or using `lambda(N)`/`r` as an input feature, does not count.

Any quoted Grover improvement in the first audit is only the ideal square root of the classical domain reduction and explicitly ignores the cost of implementing the modular predicate as a reversible oracle.
