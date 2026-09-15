# Independent-N holdout: PTP-conditioned cube preconditioning

Date: 2026-09-14

## Design

This holdout used one public base `a=2` per distinct squarefree semiprime in the disjoint range `2048..8191`.

The same transform `a -> a^3 mod N` was applied to both public residue strata:

- trigger: `N mod 3 == 2`;
- control: `N mod 3 == 1`.

The main comparison retained rows where ordinary Shor half-order factor extraction was validation-successful and where neither the baseline nor transformed base was already solved by the public gcd/repeated-squaring classical shortcut guardrail. Hidden factors and orders were validation labels only. There was no Monte Carlo sampling and no IBM/QPU access.

## Independent-N result

| Metric | trigger | control |
|---|---:|---:|
| semiprimes | 304 | 306 |
| factor-capable rows | 219 | 223 |
| paired quantum guardrail rows | 145 | 152 |
| `3 | lambda(N)` fraction | 100.0% | 36.18% |
| `3 | r` fraction | 72.41% | 33.55% |
| order-reduced rows | 105 | 51 |
| order-reduced fraction | 72.41% | 33.55% |
| Wilson 95% interval | [64.63%, 79.04%] | [26.53%, 41.38%] |
| aggregate phase-work reduction | 25.24% | 9.99% |
| mean success-probability delta | +2.38 pp | +0.23 pp |

The independent-N contingency table is `[[105,40],[51,101]]`.

- absolute order-reduction-rate difference: `+38.86` percentage points;
- risk ratio: `2.158`;
- two-sided Fisher exact p-value: `1.997e-11`.

Because there is one row per distinct N, this test does not have the shared-N clustering caveat of the earlier multi-base panel.

## Selection/attrition sanity check

The factor-capable fractions are close: `219/304 = 72.0%` in the trigger stratum and `223/306 = 72.9%` in control.

The public-guardrail retention among factor-capable rows is also close: `145/219 = 66.2%` trigger versus `152/223 = 68.2%` control.

That does not prove the conditioning is irrelevant, but it argues against a large trigger/control separation being created merely by grossly different attrition rates.

## Interpretation

This is a strong independent replication of the selector effect:

> For the tested semiprime population, the public condition `N mod 3 == 2` substantially enriches cases in which cubing a public Shor base removes a factor 3 from its order, which in turn reduces exact order-blind staged-QPE work.

The generic identity is still `ord_N(a^3)=r/gcd(r,3)`. The PTP-derived/public-residue contribution is the selector: `N mod 3 == 2` guarantees `3 | lambda(N)` for the semiprime class and therefore enriches, but does not guarantee, `3 | r` for a chosen base.

This remains an ideal staged-QPE resource result, not a measured hardware speedup, fidelity result, or asymptotic-complexity improvement to Shor.

## Next robustness gate

The remaining obvious objection is base specificity: this holdout fixes `a=2`.

The next audit uses one deterministic public base per N, selected from a fixed small-prime pool by SHA-256 of public N, in a new disjoint range. It keeps one independent row per N and reports attrition balance as well as the same exact phase-work endpoint.

Run:

```bash
python hardware/dark_star_shor_ptp3_diverse_base_holdout_audit.py
```

Useful block:

```text
===== PTP3 DIVERSE-BASE INDEPENDENT HOLDOUT SUMMARY =====
```
