# Held-out residue-prime selector panel: ell = 3, 5, 7

Date: 2026-09-15

## Question

Does the public residue-conditioned order-preconditioning mechanism seen for

```text
N mod 3 == 2
b = a^3 mod N
```

generalize beyond the special modulus 3 case?

The answer from this experiment is **yes as a probabilistic enrichment mechanism,
but no as a deterministic guarantee**.

`ell=3` is special: for a semiprime not divisible by 3, `N mod 3 == 2` forces one hidden prime factor to be `1 mod 3`, so `3 | lambda(N)`.

For every odd prime `ell >= 5`, no condition using only a single nonzero value of `N mod ell` can force one hidden factor to be `1 mod ell`. For any public product residue `rho`, there is a factor-residue pair `(x, rho/x)` with neither component equal to 1.

However, the public residue still changes the prior probability. Under uniform prime residues in `F_ell^*`:

```text
P(ell | lambda(N) | N mod ell != 1) ~= 2/(ell-1)
P(ell | lambda(N) | N mod ell == 1) ~= 1/(ell-1)
```

so the public trigger should approximately double the chance that `ell` divides `lambda(N)`.

## Preregistered-style design

Default held-out range:

```text
16384 <= N <= 32767
```

For each `ell in {3,5,7}`:

- squarefree semiprimes with neither factor equal to `ell`;
- 160 trigger and 160 control `N` values;
- trigger: `N mod ell` is nonzero and not 1;
- control: `N mod ell == 1`;
- SHA-256 ranking of public `N` with a fixed salt;
- exactly one deterministic public base per `N`, selected from
  `2,3,5,7,11,13,17,19,23,29,31` and cycled until coprime;
- identical transform in both groups: `b = a^ell mod N`;
- hidden factors, `lambda(N)`, and orders used only as validation labels;
- same classical repeated-squaring/GCD shortcut guardrail as the earlier audits;
- primary endpoint: fraction of independent `N` rows with `ell | ord_N(a)`;
- Fisher exact tests at the independent-`N` level;
- Holm correction over the three primary selector hypotheses;
- secondary exact staged-QPE audit on 12 deterministic eligible rows per group.

No QPU access and no Monte Carlo were used.

## Primary result: the order enrichment generalizes

| `ell` | trigger `ell | r` | control `ell | r` | difference | risk ratio | Fisher p | Holm-adjusted p |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 131/160 = **81.88%** | 67/160 = **41.88%** | +40.00 pp | 1.955 | `1.54e-13` | `4.62e-13` |
| 5 | 72/160 = **45.00%** | 47/160 = **29.38%** | +15.63 pp | 1.532 | `5.40e-3` | `5.40e-3` |
| 7 | 45/160 = **28.13%** | 20/160 = **12.50%** | +15.63 pp | 2.250 | `7.68e-4` | `1.54e-3` |

All three primary comparisons remain significant after correcting across `ell=3,5,7`.

This is the key result: the public residue is not merely correlated with `lambda(N)` structure; the enrichment propagates into the multiplicative order of a deterministic public Shor base for 3, 5, and 7 in the held-out population.

## Mechanism check: `ell | lambda(N)`

The hidden validation labels show the expected upstream mechanism.

| `ell` | theoretical trigger prior | theoretical control prior | observed trigger | observed control | Fisher p |
|---:|---:|---:|---:|---:|---:|
| 3 | 100% | 50% | **100.00%** | 43.75% | `4.33e-16` |
| 5 | 50% | 25% | **50.00%** | 30.63% | `6.03e-4` |
| 7 | 33.33% | 16.67% | **31.88%** | 12.50% | `4.42e-5` |

The observed values track the residue-pair prediction closely enough to support the proposed mechanism rather than an unexplained empirical classifier.

The mechanism chain is therefore:

```text
public N mod ell group
    -> changed probability that ell | lambda(N)
    -> changed probability that ell | ord_N(a)
    -> exact ord_N(a^ell) = ord_N(a)/ell when ell | ord_N(a)
    -> smaller adaptive order-finding problem on those rows
```

The first arrow is deterministic only for the `ell=3` trigger. For 5 and 7 it is probabilistic.

## Quantum-value guardrail population

After conditioning on rows where ordinary Shor factor extraction succeeds and neither the baseline nor transformed base is already solved by the public repeated-squaring/GCD shortcut:

| `ell` | trigger eligible rows | control eligible rows | trigger order reduced | control order reduced | Fisher p |
|---:|---:|---:|---:|---:|---:|
| 3 | 76 | 83 | **62/76 = 81.58%** | 32/83 = 38.55% | `2.85e-8` |
| 5 | 83 | 81 | **33/83 = 39.76%** | 12/81 = 14.81% | `4.19e-4` |
| 7 | 99 | 90 | **25/99 = 25.25%** | 6/90 = 6.67% | `6.61e-4` |

The separation survives the same guardrail used in the earlier `ell=3` work.

## Exact staged-QPE secondary subset

A deterministic SHA-256-ranked subset of 12 eligible rows per group was passed through the same conservative nearest-bin-only staged-QPE model. This is intentionally a secondary directional check, not the main statistical endpoint.

| `ell` | trigger aggregate phase-work ratio | trigger reduction | control aggregate ratio | control reduction |
|---:|---:|---:|---:|---:|
| 3 | `0.7581` | **24.19%** | `0.8560` | 14.40% |
| 5 | `0.8122` | **18.78%** | `0.9460` | 5.40% |
| 7 | `0.8514` | **14.86%** | `1.0000` | 0.00% |

Rows in the staged subset with lower phase work:

```text
ell=3: trigger 11/12, control 6/12
ell=5: trigger  6/12, control 2/12
ell=7: trigger  4/12, control 0/12
```

The small staged subset is not individually powered for significance. Its role is to confirm that the generalized order enrichment points in the expected resource direction under the already-established adaptive stopping model.

## Fast exact scorer validation

The panel includes a faster theorem-equivalent scorer for the staged model. On rows already known to have a factor-producing Shor order, a continued-fraction denominator verifies `a^d = 1 mod N` exactly when the true validation order divides `d`; minimization then returns the same factor-producing order.

A local reference comparison over more than 100,000 nearest-bin acceptance cases found zero mismatches against the existing strict public modular-verification implementation. The repository script can rerun this check with:

```bash
python hardware/dark_star_shor_residue_prime_panel_audit.py --verify-fast-equivalence
```

This use of the validation order is only a simulation-speed optimization. The public operational stopping rule remains modular verification of a measured continued-fraction denominator.

## Interpretation

The strongest supported statement is now broader than the original cube result:

> Public residue information can act as a selector for the odd-prime content of multiplicative orders used in Shor order finding. For `ell=3`, the trigger gives an exact `ell | lambda(N)` guarantee; for `ell=5` and `ell=7`, the selector is probabilistic but still produces statistically significant independent-`N` enrichment of `ell | ord_N(a)` in a held-out deterministic-base panel. Applying the matched odd-power transform `a -> a^ell mod N` converts that enrichment into exact order reduction on the affected rows and lower expected adaptive phase-estimation work in the tested secondary sample.

What this does **not** establish:

- an asymptotic improvement to Shor's algorithm;
- a reduction in fixed textbook-QPE width;
- a measured QPU runtime or fidelity improvement;
- a deterministic factor-residue guarantee for `ell=5` or `ell=7`;
- novelty of `ord(a^L) = ord(a)/gcd(ord(a),L)`;
- that an arbitrary large smooth exponent is a uniquely quantum or PTP-derived construction.

## Why this matters for the manuscript

Before this panel, the cleanest criticism was that `N mod 3 == 2` might be a one-off algebraic accident. That criticism is now substantially weaker.

The deterministic part **is** special to 3, but the broader residue-to-order-distribution mechanism survives at 5 and 7. This suggests the publishable object is not simply "cube the base when `N mod 3 == 2`". A better framing is a family of **public residue-conditioned odd-prime order preconditioners**, with `ell=3` as the strongest exact-selector member.

The next serious gate should be a preregistered out-of-range replication of the 5 and 7 effects, followed by a hardware-targeted compiled-cost case for one clean `ell=5` and one clean `ell=7` example that survive the classical shortcut guardrail.

## Reproduce

```bash
cd RecycledQubitRegisters
git pull
python hardware/dark_star_shor_residue_prime_panel_audit.py
```

Optional reference-equivalence validation:

```bash
python hardware/dark_star_shor_residue_prime_panel_audit.py --verify-fast-equivalence
```

Expected output begins with progress blocks for `ell=3`, `ell=5`, and `ell=7`, then ends with:

```text
===== RESIDUE-PRIME SELECTOR PANEL =====
...
violations=0
```
