# Diverse-base independent holdout: public residue-conditioned cube preconditioning

Date: 2026-09-15

## Design

This holdout was intended to remove the remaining obvious fixed-base objection after the `a=2` independent-N holdout.

Default design:

- disjoint numeric range: `8192..16383`;
- one statistically independent row per semiprime `N`;
- 200 selected semiprimes in each public residue stratum;
- deterministic SHA-256 ranking of public `N` within each stratum;
- one deterministic public base per `N`, chosen from the fixed pool
  `2,3,5,7,11,13,17,19,23,29,31` using SHA-256 of public `N` and a fixed salt, cycling publicly until the base is coprime to `N`;
- identical transform in both strata: `b = a^3 mod N`;
- hidden factors, `lambda(N)`, and multiplicative orders used only as validation labels;
- exact staged-QPE expectation, no Monte Carlo, no IBM/QPU access.

The primary comparison retains rows for which ordinary Shor factor extraction is validation-successful and neither baseline nor transformed base is already solved by the public classical shortcut guardrail.

## Result

| Metric | trigger `N mod 3 = 2` | control `N mod 3 = 1` |
|---|---:|---:|
| selected semiprimes | 200 | 200 |
| factor-capable rows | 143 | 153 |
| factor-capable fraction | 71.5% | 76.5% |
| paired quantum guardrail rows | 95 | 97 |
| guardrail retention among factor-capable | 66.43% | 63.40% |
| `3 | lambda(N)` fraction | 100.0% | 34.02% |
| `3 | r` fraction | 84.21% | 31.96% |
| order-reduced rows | 80 | 31 |
| order-reduced fraction | 84.21% | 31.96% |
| Wilson 95% interval | [75.57%, 90.19%] | [23.52%, 41.77%] |
| aggregate phase-work reduction | 26.62% | 8.91% |
| mean conditional stop-precision ratio | 0.8651 | 0.9455 |
| mean success-probability delta | +2.57 pp | +0.24 pp |

Independent-N contingency table:

```text
[[80, 15],
 [31, 66]]
```

Comparison:

- absolute order-reduction-rate difference: `+52.25` percentage points;
- risk ratio: `2.635`;
- two-sided Fisher exact p-value: `8.50e-14`;
- aggregate phase-work-reduction difference: `+17.71` percentage points.

The factor-capable fraction differed by `-5.0` percentage points (trigger minus control), while guardrail retention among factor-capable rows differed by `+3.03` points. These differences are much smaller than the `+52.25` point primary-endpoint separation.

## Mechanistic interpretation

For squarefree semiprimes not divisible by 3:

- `N mod 3 == 2` forces factor residues `{1,2}` modulo 3, hence at least one prime factor is `1 mod 3` and therefore `3 | lambda(N)`;
- `N mod 3 == 1` mixes hidden `(1,1)` and `(2,2)` factor-residue classes and does not provide the same public guarantee;
- for a chosen base with order `r`, `ord_N(a^3) = r / gcd(r,3)`;
- therefore cubing reduces the order exactly threefold when `3 | r`, and leaves it unchanged when `3` does not divide `r`;
- the earlier mechanism audit verified that exact chain with no theorem violations and found phase-work ratio exactly `1.0` whenever `3` did not divide `r` under the exact staged model.

This holdout shows that the selector effect survives diverse, deterministic public bases rather than being peculiar to `a=2`.

## What is supported now

The strongest current statement is:

> For the tested semiprime populations, the public condition `N mod 3 == 2` acts as a reproducible selector for cases in which cubing a public Shor base removes a factor 3 from its order. Under an exact order-blind staged-QPE model, this substantially reduces expected phase-estimation work without using the hidden order to choose the transform.

## Boundary

This is not a measured hardware speedup, not a hardware-fidelity result, and not an asymptotic improvement to Shor's algorithm. The staged-QPE model is idealized and conservative; native-gate confirmation has so far been performed only for the small `N=209` compiled example.

The cube identity itself is elementary group theory and should not be claimed as novel. The potentially publishable contribution is the public residue-conditioned selector, its adaptive-QPE resource consequence, and the controlled empirical/analytic validation. A dedicated literature review is required before making a novelty claim.

## Reproduce

```bash
python hardware/dark_star_shor_ptp3_diverse_base_holdout_audit.py
```

Expected ending block:

```text
===== PTP3 DIVERSE-BASE INDEPENDENT HOLDOUT SUMMARY =====
===== OVERALL =====
```
