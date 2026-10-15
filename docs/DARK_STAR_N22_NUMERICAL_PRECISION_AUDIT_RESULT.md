# VERIFIED: frozen-sample N22 full-outcome ideal-QPE numerical PRECISION audit — one conditional model win, not independent validation

**Research lead/original project:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-15 Pacific. No QPU or IBM runtime. Numerical/scientific assistant implementation.

## Immutable research history and interpretation guardrails

This is a **PREDECLARED METHODOLOGICAL AUDIT OF THE SAME FOUR 22-BIT SEMIPRIMES**, not independent replication, not another holdout, not a fitted exponent policy, and not QPU hardware evidence. The preceding frozen [fresh N22 all-outcome-head test](DARK_STAR_N22_FULL_OUTCOME_BOUNDED_RESULT.md) yielded 3 ratio comparisons spanning parity, one public-CF-factor-incapable case and **zero certified model wins** under a less precise 16,384-eigenphase and Hoeffding-constant method. It failed its preregistered **two-case trigger** primary success criterion. All four cases were factored classically by B47 or trial division; a public full CF denominator-certificate set construction can itself recover proper factors and is NOT free in a real quantum algorithm. All original raw trial results and CI failures remain unchanged. Earlier favorable scouts and n17/n18/n20/n22 mixed failed controls/selector tests remain preserved in `docs/RESEARCH_LOG.md`; the previous negative primary finding is **not erased** by a more precise after-the-fact method.

## Provenance, preregistration, verifiable receipts

- [Frozen precision-only protocol](DARK_STAR_N22_NUMERICAL_PRECISION_AUDIT_PREREG.md), committed `8c77ea5991b9990b7fab57ffda27fdf16e6383ef` **before the new numerical method was implemented/run**. It explicitly anticipated one dataset and disallowed treating a newly favorable row as independent discovery.
- Reuses exactly the **previously committed public-only sample** [`dark_star_n22_full_tail_public_manifest.json`](../results/dark_star_ptp/dark_star_n22_full_tail_public_manifest.json), committed `2788bbe9760b815513a5d4f3f1bafe3686a70e92` before the original study, SHA256 selected rows `d0cfd98eab0b92bc07c39a896e2e0039c3e065f6c6521c525dbefd676c2e49ff`. Original [trigger](../results/dark_star_ptp/dark_star_n22_full_tail_trigger.json) and [control](../results/dark_star_ptp/dark_star_n22_full_tail_control.json) JSON **not overwritten**.
- [Implementation](../hardware/dark_star_n22_numerical_precision_audit.py), commit `890cc65d0c19ec96b0befae1300517e0e1658130`; stages, samples, seed, union-budget and stop schedule frozen before results.
- [Primary numerical GitHub Actions **38730414791**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38730414791): **2/2 jobs SUCCESS** including original public sample and order identity verification, complete strict public-factor crosscheck, 2^18 FFT normalization, 131072 phase samples at sampled stages, interval arithmetic/coverage checks and no QPU.
- [Independent exact-original-receipt validation/preservation Actions **38730702345**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38730702345): **SUCCESS**, downloaded original trigger/control artifacts, separately verified all 4 identities/frozen bases, original denominators, classical proper factors, all phase stages and bound invariants, 3/3 narrower intervals and no QPU, then committed unmodified JSON at [trigger](../results/dark_star_ptp/dark_star_n22_precision_audit_trigger.json) and [control](../results/dark_star_ptp/dark_star_n22_precision_audit_control.json). Any result row can be recomputed from the public code and previous frozen manifest.

## Exact methodological change, not a changed population

Identical synthetic 22-bit prime-pair semiprime Ns and public bases: trigger N=3623549,a=3; trigger N=3351017,a=19; control N=3910213,a=2; control N=2895517,a=19. Plain a vs cube a³ mod N always fixed by public N/base, with public gcd/power2/Pollard p−1 B31 selection and independently reported stronger public B47/rho/trial factorization. Validation-only p/q/r compute ideal QPE eigendistribution, never select N/base, or declare proper public CF denominator factor. Strict public condition for each candidate d is even d≤N, pow(a,d,N)==1, and nontrivial gcd(a^(d/2)±1,N); slow original verifier agrees with Numba public-factor-certificate membership on exhaustive miniature bins.

Same 4-shot adaptive QPE stages m=4,6,...,44, same generic clean-ancilla logical CCX stage count, same repeated-session factor-production cost endpoint. Numeric refinement:

1. **All** 2^m measurement bitstrings analytically via previously verified uniform-eigenphase FFT through **m=18** inclusive rather than m=12; correct double-precision normalization and strict CF acceptance checked.
2. For m>18, still evaluate **all 65 centered measurement bins** per eigenphase (`j=-32,...,32`) and retain omitted-tail success uncertainty; mathematical ideal geometric probability mass omitted at most universal 1/63. **Explicitly estimate the observed omitted head mass** instead of automatically using the worst-case 1/63 at every sampled stage.
3. For true validation order r>131072, **131072** preregistered SHA-seeded nominal IID uniform phase samples, eight times the previous 16384, shared between the two bases for each (N,m); if r<=131072, enumerate every eigenphase with no sampling error.
4. For the bounded sampled per-eigenphase accepted head H_s∈[0,1] AND omitted tail T_s∈[0,1], use **two-sided empirical Bernstein** confidence half-width `eps=sqrt(2 V log(2/delta)/n)+7 log(2/delta)/(3(n-1))` using unbiased sample variance and fixed `delta=0.01/672`. The 672 union slots cover 4 Ns × 2 bases × 21 stages × 2 observables × 2 tails, giving a **nominal simultaneous 99% confidence under true independent uniform draws**, not formally proven coverage for a seeded pseudorandom generator. Reference: Andreas Maurer and Massimiliano Pontil, *Empirical Bernstein Bounds and Sample Variance Penalization* (2009), Theorem 4 / symmetric one-sided corollary, https://arxiv.org/abs/0907.3740 . With sampling, per-stage model factoring success lies in `[max(0,Hbar-eps_H), min(1,Hbar+eps_H+min(1/63,Tbar+eps_T))]`, under the stated assumptions. For exact eigenphase enumeration there is no phase sampling error, but floating numeric trigonometric error remains.
5. Propagate all stage intervals monotonically to model factor production by cap and generic CCX per attempted staged session, and success-normalize to hypothetical independent restarts. The cube/plain interval uses `cube_cost_low/plain_cost_high` to `cube_cost_high/plain_cost_low`, and can be certified favorable *under this model/confidence statement* only if upper endpoint is below 1. For empty strict public CF certificate set, exact factoring probability is 0 regardless of omitted-tail or sampling approximation.

**These are conditional MODEL confidence intervals, NOT deterministic formally directed-rounded interval arithmetic, not actual quantum observations and not a statistically meaningful general-population uncertainty interval.** Classical CF certificate enumeration is itself a strong factor-recovery calculation with costs disclosed in the JSON. Do not omit that major practical caveat.

## Original versus refined results — every one of four frozen cases

Ratio = modeled logical CCX per successful factor-producing staged ideal-QPE session with independent restarts after cube / unchanged base. <1 is favorable within the assumed resource model.

| Group | N | Original 99%-sampling + tail model cube/plain band | Refined variance-adaptive band | Old→new width | New status |
|---|---:|---|---|---:|---|
| **Trigger** | **3623549** | [0.357458,1.989375] | **[0.718747,0.857407]** | 1.631917→**0.138660** (11.77× narrower) | **conditional MODEL win** |
| Trigger | 3351017 | undefined; zero factor-producing certs | **undefined; zero factor-producing certs** | n/a | **factor-incapable, unchanged** |
| Control | 3910213 | [0.412419,2.489615] | **[0.923670,1.105982]** | 2.077196→**0.182312** (11.39× narrower) | INCONCLUSIVE |
| Control | 2895517 | [0.475893,2.136414] | **[0.942183,1.078764]** | 1.660521→**0.136581** (12.16× narrower) | INCONCLUSIVE |

Factor-success probability by QPE cap for N=3623549: baseline [0.924152,0.948456], cube [0.999113,0.999509] under refined model. Its conservative model ratio band entirely under one corresponds to **14.26%–28.13% less abstract CCX per model factor success** on **this selected, reused, classically solved instance**. The previous model result at same case was inconclusive; greater precision changes that methodological classification. It must not be portrayed as an independent discovery or a practical factorization result.

N=3351017 remains EXACTLY incapable of factor production under the specified CF acceptance rule for either base despite a cubic order shrink 836580→278860. Both controls preserve unchanged plain-vs-cube validation order and nearly matched success intervals, while their CCX ratio bands still cross one. No selective omission or denominator engineering.

## Frozen precision-method pass/fail and independent width

Preregistered methodological gate: at least **2/3** of previously factor-capable comparisons must have strictly narrower finite ratio bands and valid strict factor-producing CF/cost controls. **PASSED 3/3**, including the trigger and both controls. This is a *numerical-method* success, not a preregistered confirmation of quantum speedup. Factor-capability and classical factoring status are unchanged. The original broader primary 2-case trigger group success criterion remains NOT MET: only one comparable favorable model case; second has strictly zero factor capability. No meaningful population inference with four reused keys.

The analytic simultaneous logical width of generic n22 clean-ancilla arithmetic is 69 workspace, 113 conventional phase-wide peak versus **70 phase-recycled peak**, 43 fewer peak logical qubits (38.05%) attributable to phase-register reuse, **not** to cube transform or numerical estimator; there are no IBM native gates, fault-tolerant qubits or physically verified error/fidelity reductions here.

## Next direction

**Win recorded:** the dominant reason for previous inconclusiveness on three finite cases was estimator conservatism, and this independently audit-verified numerical protocol tightens widths by 11–12× without changing the inputs. One reused trigger key now has a conditional modeled cube advantage.

**Failure/limits recorded:** same four instances, no new population evidence, one still publicly factor-incapable, two still inconclusive, all classically factored, public classical certificate precomputation can itself factor and is not costed into any practical quantum advantage. Phase sampling statistical guarantees rely on independent ideal draws and are not certified for a deterministic PRNG; floating calculations do not have directed-rounding machine certificates. No new theorem, credible RSA public-key attack, asymptotic improvement or hardware speed gain.

**Best next falsification:** freeze a wholly NEW disjoint public sample **before** applying the same precision method to it, without changing W, sample count, alpha, selection group, or resource endpoint. Include *real classical factoring* and public certificate-work time as separate, noncommensurate baselines, and ideally independently derive deterministic stage-interval validation on a small mini-case. Don't pay for an IBM QPU experiment on this basis.
