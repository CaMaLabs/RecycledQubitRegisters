# PTP-conditioned cube control result

Date: 2026-09-14

This note records the disjoint-range control experiment comparing the same cube transform `a -> a^3 mod N` in two public residue strata.

## Experimental design

Default range: `512..2047`, fixed public bases `2,3,5,7`.

- trigger stratum: `N mod 3 == 2`;
- control stratum: `N mod 3 == 1`.

The same cube transform is applied to both groups. Hidden factors and multiplicative orders are validation labels only. The analysis keeps ordinary-Shor-factor-capable rows that also survive the same public classical shortcut guardrail on both baseline and transformed bases.

For semiprimes not divisible by 3, the trigger has an exact algebraic meaning: `N mod 3 == 2` forces the two prime-factor residues modulo 3 to be `{1,2}`, hence at least one factor is `1 mod 3` and therefore `3 | lambda(N)`. `N mod 3 == 1` does not give the same public guarantee.

## Result

| Metric | trigger `N mod 3=2` | control `N mod 3=1` |
|---|---:|---:|
| paired quantum guardrail rows | 98 | 84 |
| distinct N | 43 | 39 |
| order-reduced rows | 78 | 17 |
| order-reduced fraction | 79.59% | 20.24% |
| aggregate phase-round ratio | 0.68260 | 0.94227 |
| aggregate phase-round reduction | 31.74% | 5.77% |
| mean conditional stop-precision ratio | 0.84357 | 0.95943 |
| mean success-probability delta | +0.03124 | +0.00096 |
| fraction of distinct N with mean phase ratio < 1 | 97.67% | 28.21% |

The order-reduction-rate difference is `+59.35` percentage points. The trigger/control risk ratio for observing a 3x order reduction is about `3.93x`. A row-level two-sided Fisher exact test on `[[78,20],[17,67]]` gives `p ~= 4.1e-16`; however, multiple base rows share the same `N`, so that p-value should be treated as descriptive support rather than as the only inferential claim.

## Interpretation

The control strongly argues that the public residue condition is doing useful selection rather than cubing every base being equally effective.

The mechanism should be framed carefully:

1. The generic group identity is `ord_N(a^3) = r/gcd(r,3)`.
2. The PTP-derived public condition `N mod 3 == 2` guarantees `3 | lambda(N)` for the semiprime class under study.
3. That guarantee does **not** imply `3 | r` for every base, but it strongly enriches the probability that the chosen base order contains a factor 3.
4. When `3 | r`, cubing removes exactly one factor 3 from the order and the adaptive staged-QPE workflow can stop earlier.
5. When `3` does not divide `r`, cubing preserves the order; under the exact uniform-eigenphase staged model the expected phase-work distribution should be unchanged.

So the strongest current phrasing is:

> The PTP residue condition acts as a public selector for a generic odd-power order-reduction transform. It substantially enriches cases in which cubing removes a factor 3 from the Shor order and thereby reduces adaptive phase-estimation work.

This is stronger and more precise than attributing the cube identity itself to PTP.

## Boundary

This remains an exact idealized staged-QPE resource result after a public classical-shortcut guardrail. It is not a hardware runtime/fidelity measurement and not an asymptotic-complexity improvement to Shor.

## Next mechanism check

Run:

```bash
python hardware/dark_star_shor_cube_mechanism_decomposition_audit.py
```

This decomposes the control receipt by hidden validation-only factor residues modulo 3, verifies the exact `3|lambda -> 3|r -> order reduction` chain, and checks that rows with `3 not | r` have unchanged exact phase-work expectation.
