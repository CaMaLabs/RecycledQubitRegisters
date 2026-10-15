# PREREGISTERED: Dark Star public selector vs no transform, bounded classical factoring, explicit continued fractions

**Frozen before execution / outcomes:** October 14, 2026, Pacific. **Research direction and attribution:** Chase Lunsford (CaMaLabs). AI-assisted test design and implementation. Logical quantum resource modeling only; **no IBM QPU jobs**.

## Preserve earlier evidence and its limits

[Completed frozen n17 semiprime holdout](DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_RESULT.md): 96 selected, 51 eligible for its validation-only witness/shortcut test, in trigger vs control cells by ell3/5/7. Trigger expected model CCX savings **20.10%, 9.35%, 2.88%** versus control **13.09%, 15.52%, 1.64%**. Thus ell3 passes directional trigger criterion; ell5 FAILS; ell7 weak directional pass despite 6/9 eligible trigger cases worsening. Per-round modular arithmetic CCX is slightly MORE expensive after the transformation: savings are from earlier ideal-model stopping only. Separately, recycling 17-bit model peak 88->55 logical qubits, not a Dark Star arithmetic improvement. The three earlier handpicked scout results 43%-69% are not population means. The odd-power order identity is known mathematics, not a new quantum algorithm.

## Locked fresh instances; NO eligibility cherry-picking

Use distinct-prime semiprimes p<q, **2^17 <= N < 2^18** (131072..262143), p,q>=11, ell in **(3,5,7)**, ell does not divide N. For each ell group by **public N only**: trigger N%ell != 1; control N%ell==1. Select **20 per group per ell** (40×3=**120** public sample rows) BEFORE computing hidden multiplicative order/outcomes. For each ell/group choose the 20 smallest SHA256 integer rank `"QRR-public-selector-population-v2-20261014"|ell|group|N`; tie ascending N. Deterministically select the first coprime a in a cyclic rotation of the existing fixed public base pool `(2,3,5,7,11,13,17,19,23,29,31)` using SHA256 salt `"QRR-public-selector-base-v2-20261014"|ell|N`. Do not reuse previous population selection salts or outcomes to choose N/base. Three independent CI jobs by ell; no prespecified cross-ell pooled improvement headline.

## Three policies, all fully public

Compute public candidate `b=a^ell mod N` for every row, without knowing order. On the SAME originally chosen a, compare:

- **plain**: always use a.
- **unconditional**: always use b.
- **public_selector**: use b when `N%ell != 1` (trigger) and b!=a, otherwise use a (no transform option).

No selector uses p/q, lambda(N), order, validation success probability, prior held-out labels, quantum resource model prediction, or oracle certificates. Avoid claiming this simple residue policy is optimal. The paired **primary endpoint is public_selector vs plain** in the frozen trigger and control strata separately; unconditional is a control to show whether simply transforming every base is better or worse.

## Bounded, COMMON public classical factor preprocessing BEFORE policies

On each public N, run in this exact order and stop if a nontrivial factor is found: (1) gcd(a,N) (expected 1 for selected coprime bases); (2) existing bounded repeated squaring/GCD on baseline a with cap 2*bitlength(N)+2; (3) **Pollard p-1 stage one** on fixed public base 2 with `B=31`: perform prime-power repeated modular exponentiation `x=pow(x,p^floor(log_p B),N)` for primes<=31 in increasing order, then `gcd(x-1,N)`; an initial gcd(2,N) is permitted. No secret factor/order enters any operation, and any found factor must divide N. Record individual cost counters for public gcds, modular squarings/pow calls, p-1 exponents and results. This bounded classical baseline is deliberately limited and NOT a complete factoring algorithm. All three quantum policy comparisons use exactly the SAME classical unresolved subset, chosen before hidden order validation. Classical successes have no modeled quantum execution and must be disclosed; no claimed quantum gain by excluding them without reporting denominator.

For added diagnostic only, run the existing power-of-two/GCD shortcut check on b **without suppressing the row or reclassifying public-selector quantum costs**, and report if it finds a classical factor. This is important because transformed-base classical shortcuts may explain apparent quantum wins and would in practice be used. Distinguish combined deployment from raw quantum-only accounting; do not claim a full optimized classical/quantum hybrid pipeline.

## Explicit factor-producing continued-fraction success evaluator

Keep frozen staged schedule phase bits `4,6,...,2*bit_length(N)`, 4 shots per stage, ideal nearest-bin-only QPE **probability model** (not noisy hardware and NOT the full phase-outcome distribution). The validation factors p,q may be used ONLY after selecting N, base, policies, classical status, for exact validation multiplicative order and to enumerate ideal eigenphases. Replace the previous `d % r_validation_only == 0` success shortcut in this study by a genuinely public **factor-producing** function at a sampled nearest phase bin y:

1. enumerate ordinary continued-fraction denominators d of `y/2^m`, with `1<d<=N`;
2. for each d check **public** `pow(base,d,N)==1` and even d;
3. compute `x=pow(base,d//2,N)`, evaluate public gcd(x-1,N), gcd(x+1,N), accept ONLY if one yields a proper nontrivial factor of N.

Cache the verdict for repeated (N,base,m,y) within a row. Do not consult the hidden order or factor labels in the verdict itself. The ideal nearest-bin probabilities may use the hidden order for **simulation only**, as in previous audits. Explicit CF can be more conservative than prior theorem-equivalent denominator multiple shortcut, especially for even multiples of the true order. Report how often old and new ideal success disagree if computationally cheap; do not substitute old results for new. This is still nearest-bin-only ideal QPE, not experimental end-to-end Shor.

Use existing analytic CCX and peak-width model from `hardware/dark_star_recycled_scalable_arithmetic_audit.py`, but custom exact-CF `per_shot_stage_success`, and preserve staged early stop, conditional reach, expected rounds, and resource counts. For any nonclassically-factored row, compute model for all three bases including factor-incapable cases; if model success=0, mark cost-per-success infinite rather than hiding the case. Do not use witness eligibility filters in new population primary denominator.

## Preregistered metrics and decision conditions

For each ell/group over **ALL 20 selected rows**, disclose classical-factor successes, remaining unresolved, and then among unresolved: fraction with actual factor-producing success probability >0 for each policy, mean/median per-attempt success probability, expected CCX per attempted staged session, expected CCX per successful session with independent restarts (`CCX / p_success`; infinity if p=0). For public-selector vs plain, count paired improvements, ties and worsenings in CCX-per-success when **both** methods have positive success; report how many rows are noncomparable because either p=0, *no favorable conditioning without denominators*. Report aggregate quantum CCX for attempted sessions across all unresolved cases and conditional both-success cohort separately; any observed improved resource sum alone is NOT evidence of useful factoring if success declines. Report changed decisions among trigger/control, and exact order reduction validation only. Disclose n18 clean-ancilla arithmetic workspace and phase recycling width separately.

**Primary success criterion:** on LOCKED trigger cohort, selector must (i) have no lower success-coverage than plain, (ii) show lower aggregate modeled CCX-per-success on rows with both positive success, (iii) have a majority of comparable paired rows strictly improving and not just a few high-cost wins, and (iv) pass the common classical-preprocessing accounting. If any ell fails, say it fails. No posthoc statistical significance threshold, no pooled 3-ell claim, no cherry-picked subgroup. Secondary: same controls on all-control rows, unconditional policy, possible b-specific classical shortcuts. If the public residue selector is no better than the plain base, record the failure and investigate public predictors under NEW seeds later.

## Claim boundary and execution constraints

All instances at most 18-bit N, in-silico ideal model with polynomial generic reversible arithmetic; not an actual QPU runtime, fidelity, IBM topology-mapping, fault-tolerant surface-code cost, asymptotic advantage over Shor, or RSA-scale capability. No actual factoring by QPU. Four shots/stage cap; zero QPU service calls. Preserve every selected row, validation-only factors clearly labeled, JSON output and reproducible commits. Three GitHub Actions jobs by ell, no more than 20min each; fail loudly on worker exception, missing rows or theorem/witness algebra violations. Never quietly resample or change public selector, threshold, salts, denominator, or sample count after seeing outputs.
