# Dark Star public-policy + classical-baseline holdout v2: frozen preregistration

Date: 2026-10-14  
Research lead: Chase Lunsford / CaMaLabs  
Status: **PREREGISTERED BEFORE RESOURCE SCORING**. Separate from earlier 96-row v1 holdout.

## Hypothesis and independent population

The v1 eligible 17-bit population favored ell=3 (aggregate trigger CCX T/B 0.7990), failed ell=5 trigger/control enrichment, and gave weak ell=7 results. We now test whether a **publicly selected policy** has useful expected CCX savings when cheap *classical factoring is attempted first* and successful factoring is verified with the actual public continued-fraction witness.

Frozen inclusion before seeing orders or resources:
- Squarefree semiprimes N = pq, distinct p < q, p,q >= 11, **131072 <= N <= 262143** (18-bit). No overlap with v1 range.
- ell in **(3,5,7)**, N not divisible by ell.
- **24** SHA-ranked semiprimes per group per ell: **144 selected rows** (72 trigger, 72 control), no resampling for lack of eligible survivors.
- Trigger: N % ell != 1; control: N % ell == 1. The control is **not** assumed to have no order reduction.
- N SHA salt `QRR-public-policy-classical-v2-pop-20261014-1905`.
- Base SHA salt `QRR-public-policy-classical-v2-base-20261014-1905`.
- Fixed first-coprime SHA-rotated base pool `(2,3,5,7,11,13,17,19,23,29,31)`. `b=pow(a,ell,N)`.
- Manifest SHA-256 is calculated on canonical JSON of the public preselected `[{ell,group,N,base,transformed_base}]` in ell=3,5,7; trigger-before-control; hash-ranking order, sorted JSON keys and compact separators. Store this manifest hash **before** oracle/order scoring.

## Policies

Compare per ell/group:
- **never-transform**: public base a throughout;
- **always-transform**: transformed base b, including control N;
- **trigger-only**: b iff N % ell != 1, otherwise a;
- **conservative ell=3**: b only when ell==3 and N % 3==2; otherwise a. This is a prespecified cross-ell conservative comparator, not post hoc winner selection.

Do **not** inspect hidden factors, lambda or order when selecting a policy. The transform may alter per-stage modular constants; all costs come from the existing polynomial analytic clean-ancilla arithmetic model.

## Classical-preprocessing gate (explicit fixed budget)

For every selected N, BEFORE quantum resource scoring:
1. trial division by all primes <= **43** (report modulus checks);
2. gcd(a,N); classical public power-of-two repeated-square/GCD chain for a, with max **N.bit_length()+1** squarings (checking x±1 at every step);
3. bounded public Pollard p-1 stage 1 and stage 2 for bases **(2,3)**, B1=**43**, B2=**79**; stage1 exponent M = product of largest powers p^k <=43, stage2 checks gcd((a^M)^q - 1,N) for each prime q in (43,79].

Use the same N-only prefilter for all policies. The transformed-b repeated-square/GCD guard is a separate PUBLIC classical opportunity: where it produces a factor, charge its public computation and label the row **classical-transformed**, not quantum speedup. For the conservative primary paired quantum endpoint require: common N-only prefilter unsolved, a-chain unsolved, b-chain unsolved, baseline and transform both factor-capable under validation. Report **all** screened-out rows and reasons; no replacement sampling.

Report operation ledgers: trial remainders, modular-multiplication equivalents from square-and-multiply, GCDs, transform exponent cost, and approximate classical preprocessing differences. **Never add classical counts to logical CCX as if units are commensurate.** The primary resource endpoint is conditional on having survived the classical guard, with a separate policy-wide unconditional ledger.

## Frozen ideal QPE and public success criterion

- Stages: `4,6,...,2*bit_length(N)`; four shots per stage, nearest-bin-only ideal QPE probability from validation order.
- Actual proposed stop accepts a convergent denominator d iff **public** `pow(base,d,N)==1`, d>1, d<=N, d even, and `gcd(base^(d/2) +/- 1,N)` yields a **nontrivial factor**; no r, p or q is provided to this online predicate.
- Compare this strictly factor-producing predicate against the earlier **validation-order-multiple-only** denominator scorer as a diagnostic. Never substitute the weaker scorer in a headline.
- Factors and true multiplicative order may be used **only** to synthesize exact ideal-QPE phase distribution and to audit order identity/witness preservation; no factoring oracle in public policy.
- For factor-incapable cases, per-shot factor-success is zero, so full-cap costs and no-success rates must remain visible. Cache probability by (N, base, order, phase bits) for performance but do not change scoring.

## Primary endpoint and decision rule

Primary **eligible paired** resource metric per ell/group: `sum(expected CCX policy)/sum(expected CCX never)` with trigger-only and always-transform policies, plus mean, median, improve/tie/worsen and phase-round decomposition. Also report `sum(expected CCX policy / success-by-cap)` over rows where both successes are positive as a restart-adjusted sensitivity check.

**Policy-level** endpoint over all N-only-classically-unsolved rows (including quantum-ineligible, with any transformed classical shortcuts represented as zero required quantum work and explicitly charged classical effort) must be reported separately; do not equate fewer CCX with better factor-success probability. Report success-by-cap and classical solve fraction alongside expected work.

Direction requires trigger-only ratio < 1 on ell=3 eligible trigger rows, reproducible factor-producing verification, and a greater aggregate resource effect on the trigger group than the always-transform control group. If excluded rows or success-rate differences reverse policy-level conclusions, mark overall improvement **not established**. For ell=5/7, do not alter the trigger rule even if it fails again. No fresh significance cutoff is fitted to results.

Secondary: deterministic nonparametric bootstrap **2000 resamples per eligible group**, seeded `202610141905` for 95% CI of aggregate ratio (resample rows within group), excluding groups with <2 eligible rows. Report ratio of summed costs, not mean of ratios. No cross-group pooled headline.

## Computational and safety limits

- **Zero QPU:** no IBM API import, credential access, Sampler/Estimator backend selection or submission. GitHub Actions uses repository code and standard Python only.
- Script has no network dependency. Hard cap **144 rows**, fail if incomplete; GitHub Actions job timeout **55 minutes**, write checkpoint after each row; partial checkpoints are not publishable conclusions.
- Report stages/costs under `hardware/dark_star_recycled_scalable_arithmetic_audit.py`, modeled `hardware/ibm_shor_generic_arithmetic_clean_mcx.py`. Do not use exponential truth-table permutation synthesis.
- Peak logical width compared independently: coherent arithmetic register and ancilla retained; wide cap = arithmetic width + 36 phase, recycled = arithmetic width + 1. The public transform does **not** change the coherent arithmetic width or Shor asymptotics.
- If costs are prohibitively high, keep preregistered rules and report an incomplete/timeout result rather than reducing sample or filtering expensive rows after looking.

The result is a **modeled logical resource** experiment, not real hardware advantage, exact Phoenix/Nighthawk data, runtime/fidelity, fault-tolerant surface-code cost, novel odd-power order identity or practical RSA attack.
