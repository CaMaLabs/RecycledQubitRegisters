# VERIFIED RESULT: analytic ideal-QPE omitted-outcome bounds versus cumulative classical factoring, new 17–18-bit public survivors

**Research lead and originating line of research:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-14 PDT (GitHub completed 2026-10-15 UTC). **Scope:** classical numerical/analytic error bounds in an ideal phase-estimation model with a generic clean-ancilla logical Toffoli cost proxy. **NO QPU/IBM jobs, no physical-resource or practical factoring claim.**

## Research history and pre-existing verified successes/failures remain intact

Qubit-phase recycling reduces the number of *simultaneous* ideal phase qubits; Dark Star's odd-power transformation is separately known to reduce **order** when `gcd(r,ell)>1`, potentially improving early stopping in staged ideal QPE. Early hand-picked favorable scouts gave roughly 43–69% conditional logical CCX savings but do NOT imply general population savings. Earlier n17 population showed ell3 aggregate benefit but ell5 trigger enrichment failed and ell7 was weak. The separate [144-row n18 v2 public classical-first result](DARK_STAR_PUBLIC_POLICY_CLASSICAL_V2_RESULT.md) found 114/144 trivially classically solved, ell3 trigger **2 improved / 3 worsened** among five paired quantum-eligible cases, ell5 trigger enrichment FAILED, and ell7 negative. The [40-row B31 survivor multi-exponent holdout](DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_RESULT.md) found that a public 3/5/7 ladder offers **NO advantage** over always-cube on its strongest trigger strata, with a negative locked control majority. The [complete 10bit all-bin phase distribution](DARK_STAR_FULL_QPE_OUTCOME_HOLDOUT_RESULT.md) preserved cube logical CCX direction in **three** capable examples, but 8/12 were already classically factored and elementary trial division trivially factors all 10bit semiprimes. Those prior independently dated outcomes are not pooled or edited to fit this result.

## Frozen BEFORE outcomes, successful reproducibility and immutable receipts

- [Preregistered protocol](DARK_STAR_TAIL_BOUNDED_QPE_CLASSICAL_SURVIVOR_PREREG.md) committed **`6093fda1f1e6aba3c9b1081f90cf256a9cb66a6d`** before new specimen choices and new model runs.
- [Frozen numerical/model implementation](../hardware/dark_star_tail_bounded_qpe_classical_survivor.py) committed **`1de30c3d4b83ae3cf7342cd885882ffd29c2e7cf`**; no changes to sampling, math, scorer, tail window, benchmark endpoint or code after looking at outcomes.
- [Four independent GitHub Actions jobs, run **38677647156**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677647156), **4/4 SUCCESS**, two newly public-B31-unresolved semiprimes in each (17,18)bit×(N%3 trigger,control) cell, for **eight distinct N**. CPU-only NumPy; no QPU.
- [Independent original-artifact preservation GitHub Actions run **38677791142**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38677791142), **SUCCESS**. Original full receipts from all four jobs were validated for phase-tail positivity and tight bounds, same public base, correct cube, classical factor certification, order identity, all stages, unique Ns and zero-QPU. Four *unchanged* raw JSON receipts committed as `results/dark_star_ptp/dark_star_tail_bounded_n{17,18}_{trigger,control}.json`. The full publicly screened source N/a list and B31 operation ledger are preserved in each receipt; no positive-results-only sample filtering.

## Fresh sample and cumulative public classical baseline

Population: squarefree p≠q with p,q≥11; SHA-ranked public N in N17=65536..131071 or N18=131072..262143, public group N%3=2 (trigger) or 1 (control), with previous test Ns excluded by **public N identifier only**. Choose one deterministic first-coprime base a from SHA-rotated fixed public pool, independent of secret p/q or order. The first two survivors of publicly evaluated baseline power-of-two/GCD and stage1 Pollard p−1 B31 are sampled *per group*, not reselected for quantum performance.

| Cohort | Public Ns screened | Already factored by bounded B31 cascade | **B31 survivors evaluated** | Eventually factored by cumulative public rho | Still classically unresolved |
|---|---:|---:|---:|---:|---:|
| 17-bit trigger | 7 | 5 | 2 | 2 | **0** |
| 17-bit control | 3 | 1 | 2 | 2 | **0** |
| 18-bit trigger | 4 | 2 | 2 | 2 | **0** |
| 18-bit control | 7 | 5 | 2 | 2 | **0** |
| **Total** | **21** | **13** | **8** | **8** | **0** |

After B31 screening, apply B47 public p−1 stage1; then Pollard rho with two fixed public seeds and at most 512 iterations/seed; then full prime trial division if needed. **All 8** survivors were factored by public Pollard rho, before trial division was needed. A complete classical factoring approach can trivially factor these 17–18bit instances; ideal hypothetical QPE results below therefore offer **NO practical factoring value whatsoever**.

## Exact-head plus rigorous mathematical omitted-probability bound

For every validation eigenphase s/r and m-bit QPE measurement y, compute exact-argument geometric-sum probabilities
`P(y|s)=[sin(pi t/r)/(2^m sin(pi t/(r 2^m)))]²`, `t=s2^m−r(y0+j)`; removable 0/0 is 1. The public continued-fraction online acceptance predicate checks d≤N even, `pow(base,d,N)==1`, and obtains a proper public nontrivial gcd factor of N from `base^(d/2)±1`. True order/factors are reserved for the **ideal simulation eigenphase distribution** and identity validation, NOT used to choose public N, base, classical policy, CF acceptance, or which exponent to test.

At m≤12, evaluate all Q=2^m bitstrings with the previously validated exact full FFT of averaged eigenphase lag autocorrelation. At m>12, retain all 65 measurement bitstrings around the nearest phase bin (`j=-32,...,32`) **per eigenphase** and calculate their analytic mass. The omitted-outcome success probability is bounded between zero and that omitted mass. If `L` is total explicitly accepted head probability and `T` is exact unenumerated mass (in real arithmetic), then `L≤P_success≤min(1,L+T)`. The universal analytic bound `T≤1/(2·32-1)=1/63≈0.01587` follows from sinc-squared decay. The *observed numerical tail mass at the highest stages* is approximately **0.00311772**, tighter than that universal bound. No excluded successful outcomes are silently assigned zero without including their weight in the upper limit.

A fixed staged policy m=4,6,…,2bitlength(N) with four simulated shots/stage propagates [L,U] through product-of-failure survival; expected CCX lower evaluates stage execution at U and upper at L. The successful-session cost interval is [CCX_low/S_high, CCX_high/S_low], and the cube/plain interval is [cube_success_cost_low/plain_success_cost_high, cube_success_cost_high/plain_success_cost_low]. The **whole** cube/plain ratio interval must lie strictly below 1 for a cube model win or strictly above 1 for a cube model loss. Code/selftests validated omitted-mass coverage against truly exhaustive FFT on 9 independently enumerated predetermined tiny-N/phase-bin combinations; all jobs' analytic tail assertions passed. All sinusoidal probability computations and interval propagation use Python/NumPy floating arithmetic with explicit 1e−9 margins: these are **analytically rigorous omitted-tail inequalities in real arithmetic, not a formal directed-rounding proof of floating-point machine correctness.** No claim that the intervals include a formally certified machine-roundoff bound.

## Per-row results — all eight frozen B31 survivors, no hidden eligibility deletion

For the logical CCX per *successful factor-producing staged session with hypothetical restarts* ratio, below 1 favors cube `a³` over unchanged public base `a`, above 1 favors unchanged. Source: all four original CI JSON artifacts. **All eight were independently factored classically with public rho.**

| Bits | Public group | N | Validation order a→a³ | Conservative cube/plain modeled cost ratio | Outcome |
|---:|---|---:|---:|---:|---|
| 17 | trigger | 84479 | 10098→3366 | **[0.758107, 0.805213]** | Cube model win |
| 17 | trigger | 99851 | 4830→1610 | **[0.688894, 0.722965]** | Cube model win |
| 17 | control | 69721 | 616→616 | **[1.034223, 1.050892]** | Cube model loss |
| 17 | control | 114391 | 6264→2088 | **[0.760431, 0.798302]** | Cube model win |
| **18** | **trigger** | **195473** | 47817→15939 | **undefined: no factor-producing CF denominators** | **Factor-incapable** |
| **18** | **trigger** | **256043** | 20930→20930 | **undefined: no factor-producing CF denominators** | **Factor-incapable** |
| 18 | control | 235687 | 39060→13020 | **[0.768253, 0.846631]** | Cube model win |
| 18 | control | 186751 | 1404→468 | **[0.703023, 0.720285]** | Cube model win |

**Total 5 favorable, 1 unfavorable, 2 factor-incapable; NOT population evidence.** The registered PRIMARY heldout evaluation was the 18bit **trigger** group. Both of its two public classically unresolved (at B31) Ns **FAIL factor-producing coverage**, so the preferred primary trial is **NEGATIVE/inconclusive for relative successful-session cost**, even though an order reduction happens in one (195473: odd 47817→15939). This is a mechanistic limit: order reduction is not sufficient for Shor factor production.

For the two 18bit trigger Ns, the public set of d∈[2,N] even satisfying **both** pow(base,d,N)==1 and nontrivial factor gcd is **EMPTY for both a and a³**. Therefore the *true factor-producing success probability under the exact study acceptance predicate is identically ZERO at every phase bit depth*, regardless of what omitted QPE tail bitstrings would have been sampled. The source raw **generic tail bound** pipeline deliberately reports loose intervals [0,~0.139] for hypothetical omitted-factor success because it does not short-circuit on empty factor-denominator sets. Such intervals are conservative but can be tightened to **[0,0] by this independent public logical proof**, with no change to preregistered rows, CF criterion, or results. We report their ratio as *undefined*, not as an invented cube win/loss. This issue must not be mistaken for evidence that a factor was actually available in an unenumerated tail.

On the other six instances, direct public factor denominators were nonempty and ratio bands did not cross 1. 17bit trigger 2/2 cube wins; 17bit control 1 win/1 loss; 18bit control 2 wins. There are only 6 factor-capable comparisons, no valid across-width conclusion or meaningful adjusted statistical discovery. The 18bit trigger has no successful cases so cannot validate the hypothesis where strongest evidence was requested. The upper tails do not turn any of the six informative classifications ambiguous under this fixed W=32 test.

**Recycling is separate:** generic arithmetic coherent workspace 54 qubits for n17 and 57 for n18, with phase cap 34 or36. Wide/recycled logical peaks **88→55** (37.50%) at n17 and **93→58** (37.63%) at n18, attributable ONLY to dynamic phase-register reuse, not cube or public classical factoring. These logical widths are not physical fault-tolerant estimates or IBM native gate counts.

## Honest conclusion and next direction

**Milestone preserved:** an independently preregistered analytic **full-outcome omission probability bracket** now allows a computationally tractable, mathematically bounded model of complete ideal-QPE factor-producing work for 17–18bit Ns without enumerating up to 2^36 measurement outcomes. We proved/checked the interval construction, supplied exact FFT selftests, passed four independent CI jobs, preserved every public classical screening receipt and all eight independent classical factorizations. Within this toy ideal model, five cases favor cube and one opposes; two are provably factor-incapable. This extends the earlier 10bit full-outcome validation without claiming exact numerical full-bin probabilities at large m.

**Negative discovery retained:** the locked primary 18bit trigger cohort produces no usable success-adjusted endpoint; stronger public classical factoring removes the entire eight-case supposed quantum workload. Consequently **NO practical Shor/Dark Star quantum speedup or generic policy advantage is supported**. Prior v2 and other negative population tests are not displaced.

**Next gate:** adapt this analytically bounded model (including a public empty-denominator zero certificate and, ideally, outward-rounded machine-verified intervals) to a **larger public predeclared sample** at 20–24 bits where cheap public classical methods no longer saturate an arbitrary fixed budget, while still disclosing that these sizes are trivially factored by stronger classical algorithms. Treat physical QPU runtime/fidelity, classical cost, and logical CCX as separate resources; do not spend QPU money based on this result.
