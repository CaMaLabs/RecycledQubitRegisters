# Dark Star scalable-resource population holdout preregistration

Date: 2026-10-14

## Motivation

The combined Dark Star + recycled-QPE scalable-arithmetic audit succeeded on
three previously selected scout cases:

- N=209, ell=3;
- N=713, ell=5;
- N=781, ell=7.

Those cases are useful mechanism probes but are not a population estimate.
The next falsification step is therefore a fresh, deterministic held-out
semiprime population whose members are selected without looking at their
multiplicative orders or resource outcomes.

No QPU service is contacted.

## Frozen population

Use squarefree semiprimes N=pq with distinct primes p<q and:

- 65,536 <= N <= 131,071;
- p,q >= 11;
- ell in {3,5,7};
- N not divisible by ell.

For each ell, split using public N only:

- **control:** N mod ell == 1;
- **trigger:** N mod ell not in {0,1}.

Select exactly 16 N values per group per ell by SHA-256 ranking with the fixed
salt:

`QRR-scalable-resource-population-holdout-v1-20261014`

This gives 96 selected semiprimes total before quantum-value guardrails.

## Public base rule

For each selected N, choose the first coprime base encountered by a deterministic
SHA-256-rotated traversal of the fixed pool:

`(2,3,5,7,11,13,17,19,23,29,31)`

The base-selection salt is:

`QRR-scalable-resource-population-base-v1-20261014`

The same odd-power transform is applied in both trigger and control groups:

`b = a^ell mod N`.

## Validation-only information

The hidden factors are used only after selection to compute lambda(N), the
validation order, Shor factor capability, and exact ideal staged-QPE scoring.
They are not used to choose N, choose a, choose ell, simplify any modular
multiplier, or remove phase rounds.

## Quantum-value guardrail

A row is eligible for the primary resource endpoint only when:

1. the baseline Shor half-order witness is factor-capable;
2. the transformed witness remains factor-capable;
3. neither baseline nor transformed public base yields a nontrivial factor
   under the existing repeated-squaring/GCD classical-shortcut audit.

All selected rows remain in the output, including ineligible rows.

## Frozen staged policy

Use the same conservative staged rule as the preceding audits:

- phase bits: 4,6,...,2*bit_length(N);
- four shots per stage;
- nearest-bin-only ideal QPE probability;
- strict continued-fraction verification semantics.

## Frozen arithmetic model

Use the analytic exact gate-count mirror in:

`hardware/dark_star_recycled_scalable_arithmetic_audit.py`

which corresponds to the generic reusable-clean-ancilla reversible modular
arithmetic in:

`hardware/ibm_shor_generic_arithmetic_clean_mcx.py`.

No full-register truth-table permutation synthesis is permitted in this
population result.

## Primary endpoints

For each ell and group, on **all eligible rows**:

1. aggregate expected arithmetic CCX ratio:
   sum(transformed expected CCX) / sum(baseline expected CCX);
2. median per-row expected CCX ratio;
3. fraction of eligible rows with expected CCX ratio < 1;
4. aggregate expected phase-round ratio.

The primary comparative question is whether the trigger group has a lower
aggregate CCX ratio than the control group for each ell.

This is an effect-size/resource holdout. No new significance threshold is
introduced after seeing outcomes.

## Secondary endpoints

Report:

- fraction of selected rows that remain eligible after guardrails;
- fraction of eligible rows whose order is reduced;
- median order-reduction factor;
- distribution of transformed/baseline CCX-per-phase-round ratios;
- combined baseline-wide versus transformed-recycled peak-width reduction;
- theorem/witness-preservation violations, which must be zero.

## Interpretation rules

A positive population result requires the aggregate transformed/baseline CCX
ratio to be below one in the trigger population, with the trigger effect
stronger than control.

If the CCX reduction disappears while phase-round work remains lower, inspect
whether transformed constants have systematically more expensive generic
arithmetic.

If both disappear, the selected scout result does not generalize to this
population and must be reported as such.

If the result is mixed across ell, report the heterogeneity rather than pooling
the primes into a single headline number.

## Claim boundary

Even a positive result remains:

- a logical reversible-arithmetic resource model;
- not a QPU runtime/fidelity measurement;
- not a surface-code physical resource estimate;
- not an asymptotic improvement to Shor;
- not a practical RSA-2048 attack.
