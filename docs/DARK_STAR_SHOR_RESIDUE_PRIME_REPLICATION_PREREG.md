# Preregistered replication gate: residue-conditioned ell=5/7 Shor preconditioning

Date: 2026-09-15

This note freezes the confirmatory design before the fresh `32768..65535` range is interpreted.

## Confirmatory hypotheses

For each `ell in {5,7}`, among squarefree semiprimes not divisible by `ell`, define:

```text
trigger: N mod ell not in {0,1}
control: N mod ell == 1
```

Choose exactly one deterministic public base per `N` from the fixed pool

```text
2,3,5,7,11,13,17,19,23,29,31
```

using SHA-256 salt

```text
QRR-residue-ell-replication-v1
```

and cycle publicly until the base is coprime to `N`.

Primary hypotheses:

```text
P(5 | ord_N(a) | trigger) > P(5 | ord_N(a) | control)
P(7 | ord_N(a) | trigger) > P(7 | ord_N(a) | control)
```

The two-sided Fisher exact tests are performed at the independent-`N` level and Holm-corrected across the two confirmatory hypotheses.

## Frozen population

```text
32768 <= N <= 65535
p,q >= 11
p < q
240 trigger + 240 control N values per ell
```

Within each public group, candidate `N` values are SHA-256 ranked before taking the first 240.

## Success gate

The replication is classified as a pass only if, for **both** `ell=5` and `ell=7`:

1. trigger order-divisibility fraction is greater than control;
2. Holm-adjusted two-sided Fisher `p < 0.05`;
3. no order-identity or odd-power Shor-witness preservation violation is detected.

The primary gate does not depend on the staged-QPE secondary endpoint.

## Secondary checks

The script also records:

- `ell | lambda(N)` to verify the proposed upstream residue mechanism;
- order-reduction rates among ordinary-Shor-factor-capable rows that survive the same baseline/transformed repeated-squaring/GCD classical-shortcut guardrail used in the previous studies;
- exact conservative staged-QPE work on 20 SHA-256-ranked eligible rows per group.

The stage model remains the existing nearest-bin-only exact scorer with public denominator verification semantics.

## Hardware candidate scout

A separate small-`N` scout searches `143..4095` only **after** the confirmatory design is fixed. It returns the smallest clean trigger case for each `ell` that:

- is ordinary-Shor-factor-capable;
- survives both public classical-shortcut checks;
- has the expected exact `ell`-fold order reduction.

This scout is explicitly validation-guided and must not be treated as confirmatory evidence. Its purpose is to identify manageable `ell=5` and `ell=7` cases for subsequent IBM-target compilation.

## Reproduce

```bash
cd RecycledQubitRegisters
git pull
python3 hardware/dark_star_shor_residue_prime_replication_audit.py
```

Expected ending block:

```text
===== ELL=5/7 INDEPENDENT REPLICATION =====
...
replication_pass=True|False
violations=0
```

The script exits `0` on a preregistered pass and `2` if the confirmatory gate fails.