# PREREGISTERED: public multi-exponent Dark Star selector on classically unresolved held-out semiprimes

**October 14, 2026 Pacific. Frozen BEFORE new sample/model run.** Research lead/original research direction Chase Lunsford (CaMaLabs); AI-assisted independent controlled test and audit. ZERO QPU work.

## Preserve verified wins and failures

Prior 17bit 96-row population (CI 38663133662): ell3 20.10% aggregate trigger CCX saving vs 13.09% control, ell5 trigger enrichment failed, ell7 weak. Recycled QPE independently shrank 88→55 modeled logical peak width (37.5%). Fresh 18bit 120-row public/no-transform selector (CI 38664537058): 85/120 classically factored at fixed bounded B31 processing, leaving 35 unresolved; strict *factor-producing continued-fraction* model, conditional trigger cohorts: ell3 selector/plain CCX-per-success ratio 0.76928 (7/8 comparable cases improved), ell5 0.79073 (4/7 improved, 3 worsened), ell7 1.02953 (1/1 worsened). The older ell5 failure is NOT overturned because comparison population/endpoints differ. Small cohorts and unadjusted paired sign statistics do not prove general advantage. Changed modular constants were slightly MORE expensive per phase round, with gains attributable to modeled earlier stopping, not intrinsic constant simplification.

## Frozen new sampling regime, with public survivor conditioning

Range 131072≤N≤262143 (18-bit), squarefree N=pq, p<q primes, each ≥11, from fully enumerated synthetic distinct-prime semiprime population. **New hash salts**: `QRR-public-multichoice-survivors-v1-20261014` for ranking and `QRR-public-multichoice-base-v1-20261014` for base rotation. Entire public semiprime frame is ranked by SHA256(salt,cohort,group,N), never by order, validation factorability, predicted resource cost or hidden factor size. Two cohorts `replication`, `holdout` and **two groups** defined by public N%3: `trigger` means N%3!=1, `control` means N%3==1. Exclude N divisible by 3 and N shared with the prior 120-sample holdout (as public N IDs; no reuse of previous results). Among each ranked cohort/group, scan public Ns in rank order until **TEN classically unresolved** semiprimes are found, recording EVERY examined N and public classical result (including factored and non-selected) and exact scan depth. This creates **40 intentionally classically-unresolved test instances** (10×2×2), not 40 random unfiltered keys. Any p,q are retained as **validation-only**, not passed to public selector or classical scorer. A scalar sample of surviving public Ns may be biased toward large hidden order due to the classical filter; report that conditioning rather than claiming unconditional population behavior. Hard cap 1500 publicly screened Ns per group/cohort, fail if insufficient; do not change protocol after outcomes. Selection order is deterministic and mutually disjoint across cohorts (holdout excludes replication-selected Ns and all prior 120 public Ns). New outcomes are interpreted primarily on LOCKED holdout and independently report replication.

Fixed base pool (2,3,5,7,11,13,17,19,23,29,31), rotated by SHA256(base_salt, cohort, group, N) and select first gcd-coprime a. The base is chosen before public factoring. This is **public computable**, not quantum validation or private-order information.

## Shared classical elimination, FIRST

For each ranked candidate N,a, execute deterministic **same fixed public classical cascade** BEFORE any quantum model or policy-specific choice:

1. gcd(a,N) (always coprime by base-selection construction).
2. existing power-of-two repeated-squaring / GCD chain on a with cap 2×bitlength(N)+2.
3. Pollard stage-one p−1 using base 2, prime-power exponents p^⌊log_p(31)⌋ for primes p≤31, terminal gcd(x−1,N). Stop as soon as proper factor found; increment public modular-pow and GCD counts for executed operations.

Record factor source (classical-only), counts and scan-depth. Separately run **stronger Pollard p−1 B47 diagnostic** on base2 for each *B31 survivor*, and report how many can also be classically factored at B47; do NOT retroactively exclude them because the frozen primary denominator is B31. This exposes whether simulated quantum need would evaporate under only a slightly stronger classical baseline. No private p,q in classical decisions, no occult factoring oracle. Quantum model is evaluated only for the 40 B31 survivors.

## Policies, all public

For each selected N and its one coprime base a, public candidates are `a`, `a^3 mod N`, `a^5 mod N`, `a^7 mod N`. Only AFTER all policy choices, hidden validation factors p,q compute true multiplicative orders to model ideal eigenphases.

Policies:
- `plain`: always a (no transform).
- `always3`: always a^3, with no guard.
- `ladder`: for frozen public residues choose first of (3,5,7) with N%ell not in (0,1); if none, choose plain.
- `cheap4`: pick candidate having minimum publicly computed *single* 4-phase-bit stage generic arithmetic `ccx` count via repo `stage_arithmetic_count(N,b,4)`, tie by ordered exponent (0,3,5,7). This is intentionally a hardware-only proxy, no presumed order benefit; include proxy count overhead in interpretation.
- `random4`: choose a uniformly public SHA256-derived index from the four candidates, distinct selector salt `QRR-public-multichoice-random-v1-20261014`, with no validation/order access.
- `oracle_min`: **NOT an executable selector**; POSTHOC only, choose minimum true model CCX per successful session among candidates that actually produce a factor, using validation-only orders, to estimate the hindsight ceiling; do not count as public algorithm.

Comparison includes `plain`, `always3`, `ladder`, `cheap4`, `random4` for **EVERY selected survivor** (including zero-success candidates). All receive same public N,a, classical processing, QPE stage plan, factor-producing CF denominator verification, and logical CCX resource model. If a transformed base yields a public classical factor via an additional GCD/power chain, report it diagnostically; do NOT cherry-pick or silently classify row as completed.

## Frozen ideal-QPE and exact public CF verification

Use existing `hardware/dark_star_public_selector_larger_holdout.py` methods `evaluated_policy(n,base,order,cache)` for modeled nearest-bin-only eigenphase probability at stages phase bits 4,6,...,36, four shots per stage, generically counted coherent modular arithmetic and recycled one-bit phase. For each phase bin y, **CF denominators d are accepted only when** even, 1<d≤N, pow(base,d,N)==1, and gcd(base^(d/2) ±1,N) yields a nontrivial public factor. No hidden factor/order checked inside success predicate. True order used ONLY to generate exact ideal eigenphases, not to select candidates. This is NOT full real-QPU probability across all y and not physical runtime or fault-tolerant overhead.

Record model success probability, expected CCX per attempted session, CCX per successful session with independent restarts (infinite if p_success=0), phase-round count, order identity. No drop for unsuccessful candidates, and never claim finite factoring resource when p_success=0. Report 18-bit architecture modeled logical wide→recycled peak 93→58 separately, independent of transform.

## Preregistered primary comparison (locked HOLDOUT only)

Across all 20 holdout survivor instances (10 public trigger, 10 control) and each stratum separately:
- coverage: number of selected cases with >0 factor-production success, for each policy; any coverage loss relative to `plain` disqualifies broad gain.
- on **paired both-success** rows, ratio of summed expected CCX per successful session of `ladder` divided by `plain`, and `ladder` divided by `always3` and `random4`; paired improved/tied/worsened counts, unadjusted paired exact sign p calculated as descriptive only.
- share of selected rows factorable by stronger B47 public classical diagnostic.
- number of rows in which ladder picked ell3/5/7/none and validation-only truly reduced order; no after-the-fact policy adjustments.

A **useful result requires**, separately in the heldout trigger and control strata, nondecreased factor-production coverage, an aggregate CCX-per-success ratio <1 versus plain, >50% strictly improved among comparable non-ties, and no adverse increase compared with the public uniform-random and always3 baselines on the same endpoint. Stronger B47 classical factorization may undermine any practical value and must be discussed. Hindsight oracle is an upper bound, not a competitor. Replication cohort is a separate descriptive consistency control; no pooling to disguise one failed stratum.

## Constraints and future validity

40 PUBLIC-B31-surviving keys (not a random sample of all semiprimes), 4 CI jobs cohort×N%3 stratum, zero QPU. Each job cap 25min. Preserve all public screened candidates and summaries in verified JSON. If model/CI limit prevents completion, report censoring and never call missing results failures or successes. No claim of asymptotic speedup, IBM native device fidelity/runtime, hardware calibration, full fault-tolerant physical costs, RSA2048 factoring, new number theory theorem, or generic advantage. This phase does NOT simulate exact full QPE distribution across all bins. Next gate only if evidence survives classical B47 and non-nearest-bin/full distribution controls.
