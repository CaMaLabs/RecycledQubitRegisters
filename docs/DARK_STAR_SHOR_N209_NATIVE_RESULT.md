# N=209 Dark-Star/PTP-conditioned adaptive Shor resource result

Date: 2026-09-14

This note records the strongest zero-QPU result so far from the Dark-Star / Periodic-Table-of-Primes / Shor investigation.

## Public rule and guardrail

Instance:

- `N = 209`
- seed base `a = 3`
- public rule: use `L = 3` when `N mod 3 == 2`
- transformed base: `b = a^3 mod N = 27`

The rule uses only public `N` and the chosen base. The factors and multiplicative order are validation labels only.

The transformed base survives the public classical shortcut guardrail: the tested `gcd(b ± 1, N)` and repeated-squaring `gcd(b^(2^k) ± 1, N)` chain do not expose a factor before quantum order finding.

Validation labels give order `90 -> 30`, with the Shor half-order factor witness preserved.

## Order-blind staged stopping

The staged workflow begins at low phase precision, continued-fraction postprocesses each ideal QPE sample, accepts only a denominator that itself verifies by public modular exponentiation, and increases precision only if nothing verifies. The hidden order is not supplied to the stopping rule.

In the 2,000-session N=209 probe:

| Metric | baseline | PTP-conditioned cube |
|---|---:|---:|
| success rate | 92.60% | 98.65% |
| mean stop precision | 12.639 bits | 9.728 bits |
| median stop precision | 12 bits | 10 bits |
| mean cumulative phase-round executions | 157.584 | 92.832 |

For 1,827 sessions where both workflows succeeded, the transformed workflow saved `2.900` phase bits on average, stopped at lower precision in `78.43%` of pairs, and used `0.6471x` the cumulative phase-round work.

## Compiled native-cost result

The same staged sessions were weighted by IBM Fez-target compiled circuits. The modular unitary for each stage was generated over the full 8-bit work register from public `N` and the appropriate `base^(2^k) mod N`, with invalid states fixed. No known order or orbit was supplied to circuit construction.

Successful-session means:

| Metric | baseline | PTP-conditioned cube |
|---|---:|---:|
| native CZ executions | 4,250,225 | 2,432,939 |
| compiled-depth executions | 8,029,348 | 4,527,823 |
| circuit shots executed | 19.499 | 13.700 |

On the 1,827 paired successful sessions:

- native CZ ratio transformed/baseline: `0.62917`;
- native CZ reduction: `37.08%`;
- compiled-depth execution ratio: `0.61939`;
- compiled-depth execution reduction: `38.06%`.

These are compiled execution-cost proxies, not measured QPU runtime or fidelity.

## Counterfactual ablation

A four-way cost ablation separated earlier stopping from per-stage circuit-cost differences:

- `BB`: baseline stopping + baseline circuits;
- `BT`: baseline stopping + transformed circuits;
- `TB`: transformed stopping + baseline circuits;
- `TT`: transformed stopping + transformed circuits.

Results:

| Effect | CZ ratio | CZ reduction | depth ratio | depth reduction |
|---|---:|---:|---:|---:|
| stopping only `TB/BB` | 0.64897 | 35.10% | 0.64734 | 35.27% |
| circuit only on baseline schedule `BT/BB` | 0.97320 | 2.68% | 0.95709 | 4.29% |
| circuit only on transformed schedule `TT/TB` | 0.96742 | 3.26% | 0.95665 | 4.33% |
| combined `TT/BB` | 0.62917 | 37.08% | 0.61939 | 38.06% |

Therefore the dominant effect is **earlier order-blind adaptive stopping**, not merely a lucky cheaper compiled base-27 circuit. About 35.1 percentage points of the 37.1% CZ reduction appear in the stopping-only counterfactual.

The per-stage transformed/base CZ ratio is near unity (`~0.95-1.00`) across 4-16 phase bits, which is consistent with the same conclusion.

## Interpretation boundary

This is evidence for a public classical preprocessing rule producing lower adaptive-QPE resource use on a concrete semiprime without knowing the order in advance.

It is **not**:

- a measured QPU speedup;
- a hardware-fidelity result;
- an asymptotic improvement to Shor's complexity;
- a scalable modular-arithmetic implementation.

The current modular-unitary synthesis is exact full-register reversible truth-table/permutation synthesis for small `N`.

## Next gate: exact expectation, no Monte Carlo

The paired simulation uses deterministic Monte Carlo streams. Before treating the N=209 effect as a write-up-quality result, remove sampling noise entirely.

Run:

```bash
python hardware/dark_star_shor_n209_exact_expected_cost.py
```

This analytically sums the conservative nearest-bin success probability over every eigenphase numerator at each staged precision, computes the exact truncated-geometric stopping distribution, and weights it by the existing compiled CZ/depth receipt. It contacts no IBM service and submits no QPU job.

Useful ending blocks:

```text
===== EXACT N209 EXPECTED-COST SUMMARY =====
===== EXACT N209 COST RATIO =====
===== OVERALL =====
```

If the exact expectation reproduces the approximate 35-40% native-cost reduction, the next requirement is replication across a panel of distinct semiprimes rather than further tuning the N=209 instance.
