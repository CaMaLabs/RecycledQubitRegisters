# Exact mechanism behind the PTP-conditioned cube selector

Date: 2026-09-14

This note records the mechanism decomposition following the disjoint-range stratified control.

## Exact trigger/control mechanism

The public transform is

```text
b = a^3 mod N
```

with the generic group identity

```text
ord_N(b) = r / gcd(r, 3),   r = ord_N(a).
```

For the trigger class `N mod 3 == 2`, the public residue alone guarantees `3 | lambda(N)` for the squarefree semiprimes under study.  It does not guarantee `3 | r` for every base, but it enriches that event strongly.

The mechanism audit over the quantum-relevant guarded rows found:

| population | rows | `3 | lambda` | `3 | r` | order reduced | mean phase-work ratio |
|---|---:|---:|---:|---:|---:|
| trigger `N mod 3 = 2` | 98 | 100% | 79.59% | 79.59% | 0.7030 |
| control `N mod 3 = 1` | 84 | 21.43% | 20.24% | 20.24% | 0.9250 |
| hidden control factor residues `(1,1)` | 18 | 100% | 94.44% | 94.44% | 0.6500 |
| hidden control factor residues `(2,2)` | 66 | 0% | 0% | 0% | 1.0000 |

Across both public strata:

- every row with `3 | r` had a 3x order reduction and lower exact staged phase work;
- every row with `3 not | r` kept the same order and had exact phase-work ratio `1.0`;
- there were no theorem violations.

This closes the main mechanism chain:

```text
public N mod 3 condition
        ↓
constraint on hidden factor residues
        ↓
public guarantee / non-guarantee of 3 | lambda(N)
        ↓
strong enrichment / depletion of 3 | ord_N(a)
        ↓
a -> a^3 removes one factor 3 exactly when present
        ↓
smaller order
        ↓
earlier strict order-blind adaptive-QPE stopping
        ↓
lower phase-estimation work
```

The hidden `(1,1)` control subgroup is especially informative: it behaves as strongly as, or more strongly than, the trigger group, but `N mod 3 == 1` alone cannot distinguish `(1,1)` from `(2,2)`.  Thus the useful role of the public trigger is **selection**: it identifies a class for which `3 | lambda(N)` is guaranteed from public information alone.

## Statistical control

In the preceding multi-base stratified control, order reduction occurred in `78/98` trigger rows versus `17/84` controls, a `+59.35` percentage-point difference and risk ratio about `3.93x`.  The row-level Fisher exact p-value is about `4.1e-16`, but multiple base rows share each `N`, so that number should be treated as descriptive support rather than a fully independent-sample test.

## Next gate: independent-N holdout

The next audit removes the shared-`N` dependence entirely by using exactly one fixed public base (`a=2`) for each distinct semiprime in a new disjoint range `2048..8191`.

Run:

```bash
python hardware/dark_star_shor_ptp3_independent_holdout_audit.py
```

The audit:

- uses one row per distinct `N`;
- applies the same `a=2 -> 8` cube transform to trigger and control strata;
- keeps the same public classical-shortcut guardrail;
- computes exact staged-QPE expectations, with no Monte Carlo;
- reports an independent-`N` Fisher exact test and Wilson intervals.

Useful ending block:

```text
===== PTP3 INDEPENDENT-N HOLDOUT SUMMARY =====
```

If this holdout reproduces the trigger/control separation, the PTP-conditioned cube selector will have an exact algebraic mechanism, two disjoint numerical replications, and an independent-`N` statistical confirmation.

## Boundary

The result is an adaptive-QPE resource reduction mechanism.  It is not a measured hardware speedup, not a fidelity claim, and not an asymptotic improvement to Shor's algorithm.  The native-cost demonstration to date uses small-N full-register permutation synthesis rather than scalable modular arithmetic.
