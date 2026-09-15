# PTP-conditioned cube preconditioning: exact cross-semiprime panel

Date: 2026-09-14

This note records the first exact cross-semiprime replication of the public PTP-conditioned cube rule used in the Dark-Star/Shor investigation.

## Predeclared policy

For semiprimes in the fixed numeric panel with public `N mod 3 == 2`, and fixed public seed bases `2,3,5,7`, apply

```text
b = a^3 mod N
```

No hidden factor or multiplicative order is used to select `N`, `a`, or the transform. Factors and orders are validation labels only.

The same public classical-shortcut guardrail is applied before a row counts as quantum-relevant. The staged-QPE expectation is exact under the conservative nearest-bin-only model; there is no Monte Carlo sampling and no QPU use.

## Result

Default panel:

- 10 public-trigger semiprimes;
- 40 valid `(N,a)` rows;
- 32 rows where baseline Shor factor extraction is validation-capable;
- 13 paired rows that also survive the public classical shortcut guardrail;
- 5 distinct semiprimes represented after that guardrail.

Among the 13 paired quantum rows:

- 12/13 (`92.31%`) had the order reduced by the cube transform;
- every reduced order changed by exactly `3x`, as required by `ord(a^3)=ord(a)/gcd(ord(a),3)`;
- `92.31%` of rows used less unconditional staged phase-round work;
- aggregate transformed/baseline phase-round ratio was `0.58317`, i.e. a `41.68%` reduction;
- mean conditional stopping precision ratio was `0.78405`;
- mean transformed-minus-baseline success-probability change was `+0.04383`;
- all 5 represented semiprimes had mean transformed/baseline phase-round ratio below 1.

Per-semiprime mean phase-round ratios were:

| N | paired rows | mean transformed/baseline phase-round ratio | fraction rows improved |
|---:|---:|---:|---:|
| 209 | 1 | 0.56767 | 1.000 |
| 341 | 3 | 0.60323 | 0.667 |
| 407 | 4 | 0.61052 | 1.000 |
| 437 | 3 | 0.61285 | 1.000 |
| 473 | 2 | 0.53367 | 1.000 |

## Interpretation

This is positive replication: the N=209 result is not the only semiprime in the first panel where public cube preconditioning reduces exact order-blind staged-QPE work.

The result is still too small to establish broad generality. Only 13 paired quantum rows across 5 distinct semiprimes survive all validation and shortcut filters. The next control must answer whether the *PTP trigger itself* adds value over generic cube preconditioning.

## Next control: trigger versus non-trigger stratum

The follow-up script is:

```bash
python hardware/dark_star_shor_cube_stratified_control_audit.py
```

Its default range `512..2047` is disjoint from the first panel. It applies the same cube transform to both:

- trigger stratum: `N mod 3 == 2`, where the public residue condition guarantees `3 | lambda(N)`;
- control stratum: `N mod 3 == 1`, where that guarantee does not follow from `N mod 3` alone.

The comparison is exact, zero-QPU, and uses the same staged stopping and classical-shortcut guardrails.

The decisive question is not merely whether cubing helps. It is whether the trigger stratum has a higher order-reduction rate and lower staged phase-work ratio than the non-trigger control. If not, the main result should be framed as generic odd-power base preconditioning rather than a PTP-specific advantage.

## Boundary

These results do not establish a hardware speedup, hardware fidelity gain, or asymptotic improvement to Shor. They concern exact ideal staged stopping under public verification, with factors/orders used only as validation labels.
