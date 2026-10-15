# VERIFIED: complete ideal-QPE outcome distribution versus nearest-bin Dark Star cube — limited positive mechanism check

**Study freeze/execution:** October 14, 2026 Pacific (GitHub UTC October 15). **Research direction:** Chase Lunsford / CaMaLabs; AI-assisted formal math, implementation, conservative audit and CI preservation. **Zero QPU jobs or IBM service calls.** Tiny 10-bit semiprime **ideal-QPE simulator + generic reversible arithmetic logical CCX**, NOT a practical quantum or hardware speedup.

## The research history and previous wins are preserved

- Dynamic/iterative recycled QPE uses fewer simultaneous logical phase qubits independently of odd-power preprocessing. The generic modular arithmetic model gives **wide/recycled peak 93→58** qubits at 18bit and **53→34** at the present 10bit cap; no physical-code overhead or actual hardware fidelity is represented.
- Dark Star's known identity `ord_N(a³)=ord_N(a)/gcd(ord_N(a),3)` causes earlier expected staged ideal-QPE stopping when the order has a factor 3. Three favorable hand-selected scout semiprimes showed 43–69% modeled cost reductions, which are **not population means**; transformed modular multiplication can cost MORE CCX per phase round.
- Fresh n17 population [result](DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_RESULT.md): ell3 directional trigger benefit, **ell5 trigger enrichment FAIL**, ell7 narrow/weak.
- New n18 [120-case public-selector result](DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_RESULT.md): 85/120 already factored by public B31 classical preprocessing, ell3 modest conditional gain, ell5 fragile differently defined gain, **ell7 fail**.
- Latest n18 B31-survivor [40-key multi-choice result](DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_RESULT.md) (CI 38667303027): public classical B31 factored 160/200 screened, leaving 40 B31 survivors. Locked trigger cube/plain ratio 0.7764 under the old *nearest-bin-only* model, but `ladder` matched unconditional cube on ALL trigger keys and locked control failed majority criterion. **No novel general selector established**. These separate experiments have different populations/selection/metrics: do not pool their numeric ratios.

The next preregistered question was narrowly whether the cube mechanism survives **an ideal QPE measurement distribution over every possible m-bit bitstring**, instead of the nearest-outcome-only approximation.

## Frozen provenance and all receipts

- [Prerecorded protocol](DARK_STAR_FULL_QPE_OUTCOME_HOLDOUT_PREREG.md), commit **`27a6097a5336205254c1c3d32afbda2a8d528a65`**, created BEFORE this new selected-N experiment.
- [Independent implementation](../hardware/dark_star_full_qpe_outcome_holdout.py), commit **`1d65cfc45648b771e513e809193a69af3fe1fe2a`**. Only NumPy CPU FFT and existing Python arithmetic; no QPU/IBM.
- Initial CI [38669418119](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669418119) **FAILED on an external validation script variable-name collision**: it assigned `x=base['modes'][mode]` and subsequently tried `x['summary']`; actual numerical jobs emitted full results and passed their internal arithmetic assertions. It was **NOT** a failing phase model or a scientifically negative outcome. Explicit fix was **validation-only**, commit **`78b3a49adc8b4e392b04461663f1eb39f916fc52`**, NO changes to sampling, seed, solver, QPE model, or data.
- [Corrected original scientific run 38669467890](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669467890): **4/4 jobs SUCCESS**, exactly 12 new 10bit selected instances (3×2 groups×2 independent cohorts), all complete, zero errors/timeouts in corrected run; extensive small-Q direct-eigenphase and fast-vs-slow CF factor verifier selftests, sum-of-probability normalization, per-bin full≥nearest checks.
- [Separate immutable-artifact validation/preservation run 38669565271](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38669565271): SUCCESS; downloaded all four original run artifacts, validated 12 distinct N, per-stage complete Q-bin mass, correctness of original public cube, zero-QPU status, and paired summaries; preserved original unmodified JSON receipts at `results/dark_star_ptp/dark_star_full_qpe_{replication,locked_holdout}_{trigger,control}.json`.

Locked population: 512≤N≤1023, distinct-prime semiprimes p≠q≥11, SHA256 rank by new preregistered public salt, first coprime base from independently rotated fixed public pool, 3 per each replication/locked_holdout × N%3 trigger/control stratum. No selecting by order, hidden factor, modeled savings, public classical survival or previously seen results. The locked holdout excludes all replication-selected N. **All twelve selected, including classical wins and factor-incapable cases, remain in exact receipts.** True p,q and validation order used only AFTER public selection/base decision, to simulate ideal eigenphases and to audit known cube order identity; not to verify CF factor success, screen or select.

## Complete quantum phase distribution versus prior nearest-bin estimator

For order r (validation-only eigenphase mixture) and Q=2^m, the averaged exact ideal-QPE phase histogram is

`P(y)=(1/r)Σ_{s=0}^{r-1}|(1/Q)Σ_{k=0}^{Q-1} exp[2πi k(s/r−y/Q)]|²`, all y from 0 through Q−1.

Compute all bins efficiently, **not** by peak-window truncation or Monte Carlo, using the exact autocorrelation Fourier formula

`C[k]=((Q−k) 1_{r|k} + k 1_{r|(Q−k)})/Q²`; `P(y)=Re FFT(C)[y]`.

The code verified this identity by direct geometric-sum eigenphase enumeration for Q=8,16,32 and multiple r including r>Q, and checked nonnegative mass (floating tolerance) and sum(P)=1 for EVERY evaluated stage. The actual full stages are m=4,6,…,20 (at cap Q=1,048,576), full enumeration with no missing tails. This is still an **ideal uniform eigenphase mixture, exact distribution in that model**, not a noisy QPU measurement.

Crucially, a phase y is only scored as factoring success when **public** continued-fraction candidate d (1<d≤N, even) satisfies pow(a,d,N)=1 AND gcd(a^(d/2)±1,N) yields a proper nontrivial factor. Fast public precomputation of *all acceptable d* was compared exhaustively on miniature cases to the original slow factor-producing CF predicate. Validation-order oracle is NEVER consulted inside y→factor verdict.

The **nearest** comparator calls the earlier frozen factor-producing nearest-bin-only scorer, omitting all nonnearest mass (not renormalized). Every per-stage and cumulative exact full factor-production probability is at least the nearest-bin value within numerical tolerance, as mathematically required. All QPE-mode paired comparisons use the identical generic reversible modular-arithmetic logical CCX construction and adaptive stopping schedule.

## Actual full population, predeclared classical baseline first

All 12 selected Ns undergo public gcd, power-of-two/GCD and Pollard p−1 stage-one **B7** as a common primary classical filter, before any QPE simulation. B31/B47 standalone Pollard p−1 diagnostics were precommitted but NOT used to remove a case or select it for success. Their outcomes are NOT monotone in B when one prime-power exponent simultaneously kills both residue orders: for some samples B7 discovers a factor but separate B31 fails; thus a practical stronger classical policy must **try several B values cumulatively**, not replace B7 with B31 and presume dominance.

| Cohort | Public N%3 | Selected | B7-classically factored | B7-unresolved | Joint positive modeled factor success |
|---|---|---:|---:|---:|---:|
| Replication | trigger | 3 | **2** | 1 | 1 |
| Replication | control | 3 | **3** | 0 | 0 |
| LOCKED holdout | trigger | 3 | **1** | 2 | 1 |
| LOCKED holdout | control | 3 | **2** | 1 | 1 |
| **Total** | | **12** | **8** | **4** | **3** |

Classical first-factor sources: **six** stage-one B7 Pollard and **two** repeated-squaring/GCD (verify exact count in the archived row receipts if reporting any aggregate source figure). The B31/B47 standalone checks found **zero ADDITIONAL** proper factors among the four surviving rows, but that is NOT evidence against other cheap classical algorithms. At this 10bit scale, **trial division through √N≤32 factors every tested semiprime trivially**, so there is absolutely **no practical quantum factoring value** in this experiment.

Of four B7-unresolved rows, **N=533** has zero proper factor-production success under both bases and BOTH QPE probability models despite cube reducing order 30→10. This is a genuinely retained **negative**: order shrinkage alone cannot make a factor-incapable half-order witness capable. Thus any positive cost-per-success endpoint is defined on only THREE jointly capable examples.

## Full-distribution result — no pooling to claim population gain

For classically-unresolved cases that have positive modeled factor-producing success for both the original a and transformed a³, ratio is cube/plain of expected generic logical CCX per successfully factor-producing staged session under independent restarts. Lower is favorable. These are tiny precommitted strata, and a ratio of one positive case is **not statistical population evidence**.

| Cohort | N%3 | Joint positive cases | Full all-bin cube/plain | Previous nearest-bin-only cube/plain | Full-model paired result |
|---|---|---:|---:|---:|---|
| Replication | trigger | 1 | **0.527462** (47.25% less) | 0.509030 (49.10% less) | 1 improved, 0 worse |
| Replication | control | **0** | **not evaluable** | not evaluable | all 3 classically solved |
| **LOCKED holdout** | trigger | **1** | **0.535706** (46.43% less) | 0.516915 (48.31% less) | 1 improved, 0 worse |
| **LOCKED holdout** | control | **1** | **0.539765** (46.02% less) | 0.548352 (45.16% less) | 1 improved, 0 worse |

**What survived:** for N=899 (replication trigger; true order validation 420→140), N=923 (holdout trigger 420→140), and N=559 (holdout control 84→28), actual complete ideal-QPE distribution still produces lower modeled successful-session CCX after the cube. The full-outcome model increased modeled factor-production probability compared with nearest for each policy (e.g. N=923 plain 0.885519→**0.922027**, cube 0.996322→**0.998965**). The cube advantage ratio **weakens** slightly on the two trigger comparisons, and **strengthens** slightly on the only holdout control example. All validation order identities passed.

**What did NOT survive as a strong general claim:** There is **NO majority of strictly improved cases over the full locked trigger/selected N set** if factoring-incapable and classically factored rows are honestly retained; only 1/3 locked trigger selected rows is jointly quantized-factor-capable. The preregistered narrow directional gate—nonempty comparable cases, majority improvement **among comparable cases**, and no coverage loss—technically passes 1/1 on locked trigger; it cannot establish a population result with only one comparable row. The three positive cases were not selected according to performance, but they are tiny and conditioned on public classical survival and success capability.

The 10bit arithmetic model uses 33 coherent workspace logical qubits, peak **53 wide versus 34 phase recycled**, a separate **35.85% lower simultaneous logical width due to phase-register recycling alone**, not cube preconditioning. These are model-width bounds not actual physical qubit counts.

## Next hard falsification and interpretation

This phase answers the methodological challenge: **the previous nearest-bin-only approximation did not artificially manufacture the direction of the cube's savings in the three tested capable instances.** Its precise magnitude shifts with the neglected tails, but a relative reduction remains. However these samples are intentionally tiny to allow exact all-bin enumeration; *8/12 classically factor with a weak B7 baseline* and simple trial division can factor every N here. These results offer **no evidence of a practical quantum factoring advantage or novel RSA attack**, and no full-size QPE distribution scaling claim.

**Next worthwhile gate:** use the exact FFT all-bin probability method to validate a rigorously bounded **tail-aware factor-producing estimator** on fresh 17–18bit samples, where enumerating 2^36 bins is infeasible. Precommit an explicit tail-error upper bound and verify it against the truly exhaustive tiny-N benchmark in an independent split before using it on larger numbers. Include *cumulative* public classical tests (Pollard p−1 at several B, elementary trial division or Pollard rho) and record all classical costs. Stop using toy models as potential practical factoring comparisons when the classical baseline can trivially factor all cases. Do not spend real IBM QPU time based on this model-only result.
