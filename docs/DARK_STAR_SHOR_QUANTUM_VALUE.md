# Dark Star / PTP Shor quantum-value boundary

Date: 2026-09-14

The Dark-Star/PTP investigation now has three distinct results that should not be conflated.

## 1. Classical midpoint pruning is real

The Fermat-midpoint audit measured reductions in expensive exact-square tests of approximately:

- `M=210`: 4.42x mean;
- `M=2310`: 5.83x mean;
- `M=30030`: 6.68x mean.

The residue-level mean survival fractions are `1/8`, `1/16`, and `1/32` respectively. These are necessary-condition filters, not asymptotic factoring breakthroughs.

## 2. Public kernel constraints on Shor order structure are narrow

The exact kernel-constraint audit found that, for the tested primorial wheels, public `N mod M` reduces the small-prime support-signature space of `lambda(N)` by only about `1.5x` on average.

The only exact small-prime guarantee produced by these wheel classes is:

- `3 | lambda(N)` for half of admissible unit residues.

Empirically, the guarantee covered about `50.7%` of the tested semiprimes with `100%` precision. In those cases the sampled Shor order had `3 | r` about `75.86%` of the time, versus a `60.94%` baseline, a `+14.92` percentage-point lift. This is useful predictive information but is not a deterministic statement that `3 | r`.

Increasing the wheel from 210 to 2310 or 30030 did not produce new exact guarantees for 5, 7, 11, or 13.

## 3. Odd-power base preconditioning often shortens genuinely quantum-relevant orders

For odd public exponent `L`, define `b = a^L mod N`. Then

```text
ord_N(b) = ord_N(a) / gcd(ord_N(a), L)
```

and, when the original order is even, the Shor half-order witness is preserved. The project verified this identity with no theorem violations across the audit.

A stricter classical-shortcut guardrail was then applied: `gcd(b±1,N)` and the public repeated-squaring chain `b^(2^k) mod N` were checked before a row was allowed to count as quantum-relevant.

The 16,000-row audit produced:

| Policy | Classical shortcut rate on baseline Shor-success rows | Quantum-remaining success rows | Fraction of remaining rows with shorter order | Mean reduction among shortened rows |
|---|---:|---:|---:|---:|
| `L=3` all N | 5.12% | 11,157 | 61.24% | 3.00x |
| PTP conditional `L=3` only when `N mod 3 = 2` | 3.89% | 11,302 | 39.82% | 3.00x |
| `L=105` | 12.32% | 10,310 | 81.68% | 15.26x |
| `L=1155` | 18.38% | 9,598 | 83.24% | 24.44x |
| `L=15015` | 22.84% | 9,073 | 84.24% | 39.36x |

This establishes a real tradeoff. Larger smooth odd exponents create more classical Pollard-p-1-like factor discoveries, but among cases that remain genuinely quantum-relevant they also strip substantial odd content from the order.

For quantum-demonstration purposes, the `L=105` policy currently gives the largest count of successful rows that both survive the classical guardrail and have a reduced order. Larger exponents give a stronger reduction on the surviving subset.

The large-exponent policies should not be described as uniquely PTP-derived; they are generic smooth odd-power preconditioning and overlap conceptually with classical p-1 methods. The PTP-specific result is the public residue-conditioned `L=3` rule and the exact `3 | lambda(N)` guarantee behind it.

## N=35 guardrail

For the current N=35, a=2 example, public cube preconditioning gives `b=8`, but

```text
gcd(8-1, 35) = 7
```

immediately factors the instance. Therefore a base-8 N=35 QPU run would be a compiler/hardware exercise, not evidence that quantum order finding was required.

## Next gate: adaptive precision

A smaller actual order does **not** automatically reduce the fixed textbook Shor phase register, because a conventional circuit is still sized from `N` rather than the unknown `r`.

The next zero-QPU audit is:

```bash
python hardware/dark_star_shor_adaptive_precision_bound_audit.py
```

It measures the conservative continued-fraction precision proxy

```text
m_cf(r) = ceil(log2(2*r^2))
```

before and after public preconditioning, after excluding classical-shortcut cases. The true order is used only as a validation label. The public stopping rule is to increase phase precision only when continued-fraction candidates fail direct modular verification.

The audit also includes an `N=209`, `a=3` example. The public `N mod 3 = 2` rule transforms the base to 27, reduces the validation order from 90 to 30, preserves the Shor factor witness, and survives the same public repeated-squaring/GCD shortcut guardrail. This makes it a better small candidate than N=35 for a future preconditioning-aware quantum demonstration, although its larger work register makes the current truth-table/permutation synthesis more expensive.
