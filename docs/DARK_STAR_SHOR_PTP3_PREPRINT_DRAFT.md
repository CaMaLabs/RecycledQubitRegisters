# Public residue-conditioned cube preconditioning for adaptive Shor order finding

**Draft status:** working manuscript. Results are repository-derived and zero-QPU unless explicitly identified otherwise. Novelty language is intentionally conservative pending a dedicated literature review.

## Abstract

Shor order finding samples the multiplicative order `r = ord_N(a)` of a public base `a` modulo an odd composite `N`. For any integer exponent `L`, the transformed public base `b = a^L mod N` has order

```text
ord_N(b) = r / gcd(r,L).
```

For odd `L`, the standard half-order Shor factor witness is preserved whenever the original order is even. This creates a simple possibility: use public information about `N` to choose an odd exponent that is likely to remove an odd factor from `r`, then perform adaptive or recycled phase estimation on the transformed base.

We study the specific public rule `L=3` when `N mod 3 = 2`, motivated by residue classes used in the Periodic Table of Primes (PTP) framework. For squarefree semiprimes not divisible by 3, `N mod 3 = 2` guarantees `3 | lambda(N)` but does not guarantee `3 | r` for a chosen base. We show analytically and by exact staged-QPE audits that this public condition strongly enriches cases in which `3 | r`, so cubing reduces the order by exactly a factor of 3 and an order-blind adaptive phase-estimation workflow can stop earlier.

Across a preregistered-style diverse-base independent holdout on a disjoint range (`8192..16383`), using one deterministic public base per `N`, order reduction occurred in `80/95 = 84.21%` of eligible trigger rows versus `31/97 = 31.96%` of controls (`N mod 3 = 1`). The absolute difference was `52.25` percentage points, risk ratio `2.635`, with an independent-N two-sided Fisher exact p-value `8.50e-14`. Aggregate exact staged phase-estimation work fell by `26.62%` in the trigger stratum versus `8.91%` in control. Earlier disjoint-range controls, an independent fixed-base holdout, and an exact mechanism decomposition showed the same qualitative effect. A compiled `N=209` zero-QPU IBM Fez-target preflight further showed a `43.36%` conditional and `44.88%` unconditional reduction in native-CZ execution proxy under the same staged policy.

These results do not constitute a measured hardware speedup, a scalable modular-arithmetic implementation, or an asymptotic improvement to Shor's algorithm. The cube order identity is elementary group theory. The contribution studied here is the public residue-conditioned selector and its measured effect on adaptive order-finding resource use.

## 1. Motivation

Conventional textbook presentations of Shor's algorithm allocate phase-estimation precision from `N`, not from the unknown order `r`. A smaller actual order therefore does not automatically shorten a fixed-width textbook circuit. This changes in an adaptive or recycled architecture that can:

1. begin with low phase precision;
2. measure and classically store phase information;
3. continued-fraction postprocess the observed estimate;
4. publicly verify a candidate denominator by modular exponentiation;
5. stop when a valid factor-producing order candidate is recovered;
6. otherwise increase precision and continue.

The RecycledQubitRegisters project already studies this kind of dynamic phase-register reuse. The question in this work is whether a public preprocessing rule can make such an adaptive workflow stop earlier without knowing `r` in advance.

## 2. Algebraic basis

Let `a` be coprime to `N`, and let

```text
r = ord_N(a).
```

For a positive integer `L`, define

```text
b = a^L mod N.
```

Then

```text
ord_N(b) = r / gcd(r,L).
```

For the specific cube transform `L=3`:

```text
ord_N(a^3) = r / gcd(r,3).
```

Therefore:

- if `3 | r`, cubing reduces the order exactly `r -> r/3`;
- if `3` does not divide `r`, cubing leaves the order unchanged.

### 2.1 Preservation of the Shor half-order witness

For odd `L`, let `d = gcd(r,L)`, which is also odd, and let `r_b = r/d`. If `r` is even,

```text
b^(r_b/2)
= a^(L r/(2d))
= (a^(r/2))^(L/d).
```

Because `L/d` is odd and `a^(r/2)` is an involution modulo `N`, the transformed half-order power equals the original half-order power. Thus standard factor extraction through

```text
gcd(a^(r/2) +/- 1, N)
```

is preserved under odd-power preconditioning on rows where the original Shor witness succeeds.

This preservation was exhaustively checked in the repository audits; no theorem violations were observed.

## 3. Why `N mod 3 = 2` is a public selector

Let `N = pq` be a squarefree semiprime with neither factor divisible by 3. Each prime is congruent to either `1` or `2` modulo 3.

If

```text
N mod 3 = 2,
```

then the factor residues must be `{1,2}`. Hence at least one of `p-1` or `q-1` is divisible by 3, so

```text
3 | lambda(N).
```

By contrast, if

```text
N mod 3 = 1,
```

then the hidden factor residues are either `(1,1)` or `(2,2)`. The `(1,1)` subgroup has `3 | lambda(N)`, while the `(2,2)` subgroup does not. Therefore `N mod 3 = 1` does not provide the same public guarantee.

The guarantee `3 | lambda(N)` is not equivalent to `3 | ord_N(a)` for every chosen base. It only changes the population from which the order is sampled. The empirical question is whether this enrichment is strong enough to matter for adaptive phase estimation.

## 4. Classical shortcut guardrail

A transformed base is not counted as quantum-relevant if the preprocessing already exposes a factor by inexpensive public arithmetic.

The audits test:

- `gcd(b-1,N)`;
- `gcd(b+1,N)`;
- a repeated-squaring chain `x_k = b^(2^k) mod N` with `gcd(x_k +/- 1,N)` checks.

This guardrail is important. For example, `N=35`, `a=2`, `L=3` gives `b=8`, but

```text
gcd(8-1,35) = 7,
```

so the transformed instance is already solved classically and cannot serve as evidence that quantum order finding was needed.

For practical factoring, such a classical shortcut is beneficial; it is excluded only when measuring genuinely quantum order-finding resource use.

## 5. Exact staged-QPE model

The primary simulation model is deliberately conservative and order-blind at decision time.

At each stage:

- phase precision starts at 4 bits and increases by 2 bits;
- each stage gets 4 ideal shots;
- only the nearest QPE bin is credited;
- non-nearest outcomes are discarded even when they might recover the order;
- a continued-fraction denominator must itself verify by public modular exponentiation;
- denominator multiples are not searched;
- if no verified factor-producing denominator is found, precision increases;
- stages are treated as independent reruns;
- the final cap is the textbook `2 * bit_length(N)` precision.

The hidden true order is used only to generate the exact ideal QPE distribution and to score validation metrics. It is not used to choose `L`, choose the transformed base, choose the stopping precision, or accept a candidate.

Exact expectation is computed by summing over every eigenphase numerator and using the truncated-geometric stopping distribution. There is no Monte Carlo noise in the principal holdouts.

The main algorithmic cost metric is cumulative phase-round execution. Hardware-targeted native-CZ and compiled-depth proxies are reported separately for the `N=209` case.

## 6. Results

### 6.1 Mechanism decomposition

A disjoint-range stratified audit applied the same cube transform to both public strata.

Among guarded, Shor-factor-capable rows:

| Group | rows | `3 | lambda` | `3 | r` | order reduced | mean phase-work ratio |
|---|---:|---:|---:|---:|---:|
| trigger `N mod 3 = 2` | 98 | 100% | 79.59% | 79.59% | 0.7030 |
| control `N mod 3 = 1` | 84 | 21.43% | 20.24% | 20.24% | 0.9250 |
| all rows with `3 | r` | 95 | 100% | 100% | 100% | 0.6273 |
| all rows with `3 not | r` | 87 | 24.14% | 0% | 0% | 1.0000 |

The hidden control decomposition is especially diagnostic:

- control factor-residue `(1,1)` rows: `3 | lambda` in 100%, order reduced in 94.44%;
- control factor-residue `(2,2)` rows: `3 | lambda` in 0%, order reduced in 0%, exact phase-work ratio 1.0.

This closes the mechanism chain under the tested model:

```text
public N mod 3 condition
    -> lambda(N) divisibility structure
    -> enrichment of 3 | r
    -> exact r -> r/3 under cubing
    -> earlier verified staged-QPE stopping.
```

### 6.2 Independent fixed-base holdout

A new disjoint range `2048..8191` used exactly one row per semiprime and fixed `a=2`.

| Metric | trigger | control |
|---|---:|---:|
| eligible independent N | 145 | 152 |
| order-reduced fraction | 72.41% | 33.55% |
| Wilson 95% interval | [64.63%, 79.04%] | [26.53%, 41.38%] |
| aggregate phase-work reduction | 25.24% | 9.99% |
| mean success-probability delta | +2.38 pp | +0.23 pp |

Independent-N contingency table:

```text
[[105,40],
 [51,101]]
```

The absolute reduction-rate difference was `38.86` percentage points, the risk ratio was `2.158`, and the two-sided Fisher exact p-value was `1.997e-11`.

### 6.3 Diverse-base independent holdout

The next disjoint range `8192..16383` removed the fixed-base objection.

Each stratum contributed 200 semiprimes selected by SHA-256 ranking of public `N`. Exactly one base per `N` was deterministically selected from

```text
2,3,5,7,11,13,17,19,23,29,31
```

using only public `N` and a fixed salt, cycling until coprime.

| Metric | trigger | control |
|---|---:|---:|
| selected semiprimes | 200 | 200 |
| factor-capable fraction | 71.5% | 76.5% |
| eligible quantum rows | 95 | 97 |
| guardrail retention of factor-capable | 66.43% | 63.40% |
| `3 | lambda` | 100% | 34.02% |
| `3 | r` | 84.21% | 31.96% |
| order-reduced fraction | 84.21% | 31.96% |
| Wilson 95% interval | [75.57%, 90.19%] | [23.52%, 41.77%] |
| aggregate phase-work reduction | 26.62% | 8.91% |
| mean stop-precision ratio | 0.8651 | 0.9455 |
| mean success-probability delta | +2.57 pp | +0.24 pp |

Independent-N contingency table:

```text
[[80,15],
 [31,66]]
```

The trigger-control order-reduction difference was `52.25` percentage points, risk ratio `2.635`, with two-sided Fisher exact `p = 8.50e-14`.

The factor-capable fraction difference was `-5.0` percentage points and guardrail-retention difference `+3.03` points, substantially smaller than the primary endpoint separation.

### 6.4 `N=209` compiled native-cost case study

`N=209 = 11 * 19`, `a=3` is a clean small example:

```text
N mod 3 = 2
L = 3
b = 27
validation order: 90 -> 30
```

The transformed base survives the public shortcut guardrail and preserves the factor witness.

An exact staged-QPE expectation using previously compiled IBM Fez-target circuits gave:

| Metric | baseline | transformed | reduction |
|---|---:|---:|---:|
| mean stop precision, successful sessions | 12.704 | 9.757 | 23.20% |
| mean phase rounds, successful sessions | 160.286 | 93.453 | 41.70% |
| mean native CZ executions, successful sessions | 4,323,714 | 2,449,131 | 43.36% |
| mean compiled-depth executions, successful sessions | 8,167,194 | 4,558,139 | 44.19% |
| unconditional phase rounds | 168.841 | 95.845 | 43.23% |
| unconditional native CZ executions | 4,556,983 | 2,511,963 | 44.88% |
| unconditional compiled depth | 8,606,190 | 4,675,046 | 45.68% |

A counterfactual decomposition of the Monte Carlo predecessor showed that most native-cost reduction came from earlier stopping rather than from a cheaper transformed circuit at equal stage widths.

This is a compiler-weighted resource proxy, not a QPU runtime or fidelity measurement.

## 7. Relation to PTP and to generic odd-power preprocessing

The cube transform is generic group theory. The PTP-related/public-residue contribution in this work is narrower:

- residue classes make a public statement about the possible hidden factor residues;
- for `N mod 3 = 2`, that statement guarantees `3 | lambda(N)`;
- this substantially enriches orders containing a factor 3;
- cubing then removes that factor whenever it is actually present.

Larger smooth odd exponents such as `105`, `1155`, or `15015` can remove more odd factors from an order, but they overlap much more directly with Pollard-`p-1`-style smooth-exponent preprocessing and produce more classical factor shortcuts. They should not be described as uniquely PTP-derived.

The PTP-specific result is therefore best described as a **public selector for when a generic odd-power transform is likely to help**.

## 8. Limitations

This work does not establish:

- an asymptotic improvement to Shor's algorithm;
- a reduction in fixed textbook QPE width;
- a scalable generic modular-arithmetic implementation;
- a measured QPU speedup;
- a hardware-fidelity advantage;
- a claim that every `N mod 3 = 2` base benefits;
- a novelty claim for the order identity or odd-power transform itself.

The exact staged model is idealized. It intentionally discards non-nearest QPE outcomes and restarts each stage, which is conservative in some respects, but it does not model hardware noise, latency, dynamic-circuit timing, or error accumulation.

The native-cost case study uses exact small-`N` full-register permutation synthesis rather than scalable arithmetic.

A dedicated literature review is required before asserting that the residue-conditioned selector or its use for adaptive Shor order finding is novel.

## 9. Reproducibility

Core scripts:

```text
hardware/dark_star_shor_constraint_audit.py
hardware/dark_star_shor_odd_power_precondition_audit.py
hardware/dark_star_shor_quantum_value_audit.py
hardware/dark_star_shor_adaptive_precision_bound_audit.py
hardware/dark_star_shor_staged_stopping_time_audit.py
hardware/ibm_shor209_public_cube_staged_cost_preflight.py
hardware/dark_star_shor_n209_native_cost_ablation.py
hardware/dark_star_shor_n209_exact_expected_cost.py
hardware/dark_star_shor_ptp3_exact_panel_audit.py
hardware/dark_star_shor_cube_stratified_control_audit.py
hardware/dark_star_shor_cube_mechanism_decomposition_audit.py
hardware/dark_star_shor_ptp3_independent_holdout_audit.py
hardware/dark_star_shor_ptp3_diverse_base_holdout_audit.py
```

Key result notes:

```text
docs/DARK_STAR_SHOR_QUANTUM_VALUE.md
docs/DARK_STAR_SHOR_N209_NATIVE_RESULT.md
docs/DARK_STAR_SHOR_PTP3_PANEL_RESULT.md
docs/DARK_STAR_SHOR_CUBE_STRATIFIED_RESULT.md
docs/DARK_STAR_SHOR_INDEPENDENT_HOLDOUT_RESULT.md
docs/DARK_STAR_SHOR_DIVERSE_BASE_HOLDOUT_RESULT.md
```

## 10. Provisional references / literature-review targets

The bibliography must be verified before external submission. At minimum the final manuscript should situate the result against:

- Shor's original polynomial-time factoring/order-finding algorithm;
- semiclassical and iterative phase estimation / semiclassical Fourier transform;
- adaptive Bayesian or iterative phase-estimation methods;
- Pollard `p-1` and other smoothness-based classical preprocessing;
- standard group-theoretic order identities;
- the Periodic Table of Primes papers that motivated the public residue selector.

A separate novelty audit should search specifically for prior proposals that replace a Shor base `a` with `a^L` using only public residue information to reduce expected adaptive-QPE precision or stopping cost.
