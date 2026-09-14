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

## Shor boundary

Shor does not search candidate factors directly. It estimates the multiplicative order `r` of a chosen base `a mod N`. Therefore a factor-residue sieve is not automatically a QPE reduction.

The audit measures mutual information and a held-out majority predictor for targets such as `3 | r`, `5 | r`, `7 | r`, `12 | r`, and analogous divisibility of `lambda(N)`. Train/test splitting is performed by semiprime `N`, so all bases for one number stay in the same fold and cannot leak into the held-out set.

A large in-sample mutual-information number is not accepted as evidence by itself. The useful quantity is whether a predictor based only on public `N mod M` improves held-out accuracy. This is intentionally conservative because large moduli create many sparse residue categories.

## Run

```bash
cd ~/Downloads/RecycledQubitRegisters
git pull --rebase
source ~/ibm-6c2q-venv/bin/activate

python hardware/dark_star_ptp_shor_audit.py
```

The default run uses:

- moduli `210 2310 30030`;
- 600 balanced semiprimes for the Fermat test;
- 2000 semiprimes for the order-information test;
- bases `2 3 5 7 11 13 17 19`;
- deterministic seed `8776`.

The receipt is written to:

```text
results/dark_star_ptp/dark_star_ptp_shor_audit.json
```

The final console blocks are:

```text
===== FERMAT MIDPOINT SUMMARY =====
===== SHOR ORDER INFORMATION SUMMARY =====
===== OVERALL =====
```

## Interpretation rules

A positive Dark Star result requires a reproducible reduction in expensive Fermat square tests or another concrete search cost, not merely a re-labelling of the same candidates.

A positive Shor result requires public residue information to improve held-out prediction of order structure enough to support an actual circuit/QPE reduction. Knowing factor residues after factorization, or using `lambda(N)`/`r` as a feature, does not count.

Any quoted Grover improvement in the JSON is only the ideal square root of the classical domain reduction and explicitly ignores the cost of implementing the modular predicate as a reversible oracle.
