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

## Adaptive precision bound result

A smaller actual order does **not** automatically reduce the fixed textbook Shor phase register, because a conventional circuit is still sized from `N` rather than the unknown `r`.

The zero-QPU adaptive-bound audit used the conservative sufficient-precision proxy

```text
m_cf(r) = ceil(log2(2*r^2))
```

with the true order used only as a validation label. After the same classical-shortcut guardrail, the mean available precision reductions were:

| Policy | Mean proxy bits saved over quantum-remaining rows | Mean saved on reduced-order subset | Mean fractional saving on reduced-order subset |
|---|---:|---:|---:|
| `L=3` all N | 1.94 | 3.17 | 9.39% |
| PTP conditional `L=3` | 1.26 | 3.17 | 9.02% |
| `L=105` | 4.94 | 6.05 | 17.48% |
| `L=1155` | 5.55 | 6.66 | 19.03% |
| `L=15015` | 6.09 | 7.23 | 20.48% |

The transformed orders also increased the conservative full-order single-shot lower bound by roughly 13-29% depending on policy. These are available precision-bound reductions, not measured runtime speedups. `fixed_textbook_qpe_width_changed_by_policy` remains false for every policy.

The `N=209, a=3` example survives the public classical shortcut guardrail. The PTP rule `L=3 when N mod 3 = 2` transforms the base to `27`, reduces the validation order `90 -> 30`, preserves the Shor factor witness, and lowers the sufficient-precision proxy `14 -> 11` bits.

## Staged public stopping-time result

The explicit staged-QPE audit used a public stop rule: increase phase precision only when strict continued-fraction candidates fail direct modular verification. The hidden order was used only to generate ideal QPE samples and score the result.

For `N=209, a=3 -> 27`, the baseline stopped at `12.64` mean phase bits and the PTP-transformed run stopped at `9.73`, while mean cumulative phase-round executions fell from `157.58` to `92.83`. Across the broader paired audit, the PTP conditional policy saved `1.29` phase bits on average and reduced cumulative phase-round work by about `5.1%`.

The simulation deliberately credits only the nearest QPE bin and treats every precision stage as an independent rerun, so this is conservative in several respects. It remains an ideal simulation, not a hardware timing result.

## N=209 compiled native-cost result

The next zero-QPU preflight compiled complete 8-bit full-residue modular-permutation circuits for both the baseline base `3` and the public transformed base `27` on the `ibm_fez` target. The construction uses only public `N`, base, and powers `a^(2^k) mod N`; factors and order are validation labels only. This remains truth-table/full-register reversible synthesis for small `N`, not scalable modular arithmetic.

Over 2,000 deterministic staged sessions:

| Metric | Baseline | PTP conditional |
|---|---:|---:|
| Success rate | 92.60% | 98.65% |
| Mean stop precision | 12.64 bits | 9.73 bits |
| Mean cumulative phase-round executions | 157.58 | 92.83 |
| Mean compiled native CZ executions | 4,250,225 | 2,432,939 |
| Mean compiled-depth executions | 8,029,348 | 4,527,823 |

On the `1,827` paired sessions where both workflows succeeded, the transformed policy:

- saved `2.90` phase bits on average;
- stopped at lower precision in `78.43%` of pairs;
- reduced cumulative phase-round execution to `0.6471x` baseline;
- reduced compiled CZ execution to `0.6292x` baseline, a `37.08%` reduction;
- reduced compiled-depth execution to `0.6194x` baseline, a `38.06%` reduction.

This is the strongest result in the Dark-Star/PTP Shor thread so far: a public, order-independent preprocessing rule leads to earlier adaptive stopping and lower compiled native execution cost in this small-instance, idealized workflow.

It is still **not** a hardware speedup measurement, a fidelity prediction, or an asymptotic factoring improvement. The QPE outcomes are idealized and the modular unitary is synthesized by a small-`N` full-register truth-table method.

## Next gate: counterfactual cost ablation

The current `37.08%` CZ reduction mixes two mechanisms: earlier stopping and different per-stage compiled circuit costs for base `27` versus base `3`. The next zero-QPU audit replays the same deterministic sessions in four counterfactual worlds:

```text
BB = baseline stopping + baseline circuit costs
BT = baseline stopping + transformed circuit costs
TB = transformed stopping + baseline circuit costs
TT = transformed stopping + transformed circuit costs
```

Run:

```bash
python hardware/dark_star_shor_n209_native_cost_ablation.py
```

The key block is:

```text
===== N209 COUNTERFACTUAL NATIVE-COST ABLATION =====
```

`TB/BB` isolates the stopping-pattern contribution, `BT/BB` isolates the per-stage compiler-cost contribution on the baseline schedule, and `TT/BB` reproduces the combined result. This decomposition should be completed before treating the N=209 result as a separate publication claim.
