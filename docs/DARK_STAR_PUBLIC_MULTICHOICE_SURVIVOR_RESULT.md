# VERIFIED: fresh public multi-exponent selection on 40 classically unresolved toy semiprimes

**Research lead and originating method:** Chase Lunsford / CaMaLabs. AI-assisted preregistration, implementation, independent strict-public controls, GitHub Actions validation and analysis. **October 14, 2026 Pacific (October 15 UTC GitHub receipts). ZERO QPU jobs.**

## Original verified milestones must remain in the record

* Recycled phase-register arithmetic width is independent of Dark Star odd-power choices. The prior 17-bit generic arithmetic model gives conventional-wide/recycled peak logical width **88→55 (37.5%)**; the present 18-bit model **93→58 (37.63%)**. Neither is a physical surface-code/QPU gain.
* Three favorable scout semiprimes gave ideal staged-QPE + generic arithmetic cost reductions 43–69%, but the [preregistered 96-case 17-bit population](DARK_STAR_SCALABLE_RESOURCE_POPULATION_HOLDOUT_RESULT.md) **did not generalize uniformly**: ell3 trigger 20.10% vs control 13.09% savings, ell5 trigger **FAILED** to beat control, ell7 directional aggregate pass with most cases worsening. Order reduction is a known identity, not novel quantum math.
* The fresh [120-case 18-bit public/no-transform study](DARK_STAR_PUBLIC_SELECTOR_LARGER_HOLDOUT_RESULT.md) had **85/120 publicly classically factored** at B31, leaving 35 simulated quantum candidates. On *differently conditioned* both-factor-capable trigger subsets ell3 public selector/plain **0.7693** CCX-per-success (7/8 improve), ell5 **0.7907** (4/7 improve, 3 worse), ell7 **1.0295** (1/1 worse). These are NOT hardware speedups, statistically conclusive discoveries, or directly comparable pooled denominators with the 17-bit run.

## Frozen new protocol, independent locked receipts

- Preregistered **BEFORE NEW SAMPLE OUTCOMES**: [DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_PREREG.md](DARK_STAR_PUBLIC_MULTICHOICE_SURVIVOR_PREREG.md), commit `7d66007e106ef4e4ff84b0f9b50c4af58ffeeacd`.
- Strict-public implementation: [hardware/dark_star_public_multichoice_survivor_holdout.py](../hardware/dark_star_public_multichoice_survivor_holdout.py), commit `aaa732d035b27b5579436101ed2f4bbb62445acc`; [four independent CI jobs](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38667303027) registered by workflow commit `a0be3333b64e498bf91c7372819f30aebb74217d`, **4/4 SUCCESS**. All four actual logs' summary and validation lines were inspected; all 40 survived cases have complete 5-policy data, and zero QPU calls.
- Original immutable artifacts were independently downloaded and strict-row-validated in [successful receipt-preservation CI 38667614971](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38667614971). All **four JSON files** are committed under `results/dark_star_ptp/dark_star_public_multichoice_{replication,holdout}_{trigger,control}.json`. Every screened classical row, every selected survivor and all comparator receipts retained.
- New public SHA-256 ranking salt `QRR-public-multichoice-survivors-v1-20261014`, public base salt `QRR-public-multichoice-base-v1-20261014`, random-control salt `QRR-public-multichoice-random-v1-20261014`. Preexisting 120 sample N IDs are excluded. Locked holdout-selected N exclude the replication-selected N; 40 **distinct** public selected Ns verified. Two cohorts replication/locked holdout × two N%3 strata (trigger means N%3!=1 and N%3 !=0, control N%3==1), **10 publicly classically unresolved 18-bit semiprimes per cell**. The semiprime frame is synthetic with hidden p,q used ONLY after public selection; private factors/orders do not determine scan order, chosen base, survivor status, exponent or public arithmetic cost proxy. This **conditions on survival of a PUBLIC classical procedure**, so it does not estimate unconditional random-semiprime gain.

## Honest classical filter: 200 publicly screened; only 40 survive

Frozen public procedure on each ranked candidate is gcd(a,N), bounded power-two/GCD chain (cap 2×bit_length+2), and stage-one Pollard p−1 from base2 with B31. Stop at first public nontrivial factor. **No order/factor oracle enters the classical decision.**

| Cohort | Public N%3 group | Screened public semiprimes | Factored before model | B31 survivors selected | B47 additionally factorizable (diagnostic only) |
|---|---|---:|---:|---:|---:|
| Replication | Trigger | 56 | 46 | 10 | 2 |
| Replication | Control | 29 | 19 | 10 | 1 |
| **Locked holdout** | Trigger | 53 | 43 | 10 | 0 |
| **Locked holdout** | Control | 62 | 52 | 10 | 1 |
| **TOTAL** | | **200** | **160 (80%)** | **40 (20%)** | **4/40** |

The 40 quantum-modeled rows are deliberately enriched for public-classically-unresolved moduli, not a random sample of all 18-bit semiprimes. Only **27/40** have strictly positive model factor-production success under the compared policies; all other zero-success rows remain present in the receipts. B47 is a *counterfactual public classical baseline* and was NOT used to remove or pick rows. No classical operation counts are converted to physical quantum CCX time or energy.

## Fully public choices and proper factor-producing modeled outcome

For each public base a, compare four candidate bases a, a³, a⁵, a⁷ (mod N). Choices are **plain** (always a), **always3** (always a³), **ladder** (first ell among 3→5→7 such that N%ell not in {0,1}, else plain), **cheap4** (smallest public generic 4-phase-bit CCX count; exponents tie-broken 0,3,5,7), and **random4** (one publicly seeded uniform deterministic choice per N). All policies share the same classically surviving N,a, and the identical validation/ideal-QPE and generic reusable-clean-ancilla arithmetic model. The `oracle_best` value exists as POSTHOC validation-only hindsight benchmark, **not** a real public policy and not counted in primary.

The model retains four shots per stage, phase widths 4,6,…,36, ideal **nearest-bin-only** QPE probabilities generated using validation multiplicative order and *explicit public factor-producing continued fraction acceptance* (candidate d even, a^d=1 mod N, and proper public gcd(a^(d/2)±1,N)). No private factor/order used inside CF acceptance, but a true-order **simulator** is needed to generate the ideal phase distribution. The modeled resource is expected logical CCX per **successful** factor-producing *session with hypothetical independent restarts*; rows with zero success have undefined/infinite successful-session cost, never secretly filtered from coverage counts.

## Locked and replication results: multi-exponent ladder vs simpler baselines

Among only both-success-positive paired rows, ratio = sum of ladder modeled CCX per successful factor-producing session / sum of comparator's same measure. Ratios below one represent a logical model cost reduction, NOT wall-clock speedup. Counts include all compared positive-success pairs; differing successful subsets elsewhere are tracked.

| Cohort | N%3 group | Both-success ladder/plain | Ladder/plain ratio | Improve/tie/worsen | Ladder/always3 | Ladder/random4 |
|---|---|---:|---:|---|---:|---:|
| Replication | Trigger | **5/10** | **0.770799** | **5/0/0** | **1.000000** | **0.806831** |
| Replication | Control | **6/10** | **0.810945** | **3/0/3** | **0.847509** | **0.866596** |
| **Locked holdout** | **Trigger** | **9/10** | **0.776382** | **8/0/1** | **1.000000** | **0.853009** |
| **Locked holdout** | **Control** | **7/10** | **0.870264** | **3/0/4** | **0.922722** | **0.937131** |

**Decisive guardrail: the registered broad multi-choice claim FAILS.** In **both trigger cohorts**, the `ladder` deterministically chose **ell3 on all 10 selected Ns** and had EXACTLY identical result to the simpler **always3** policy (ratio 1, all successful pairs tied), so **NO additional multi-exponent selector advantage** is established. The locked **control** cohort had only **3/7** strictly better but **4/7** worse than no transform, failing the preregistered >50% improved-row requirement even though its aggregate weighted ratio is <1. There is no valid across-strata general public-selector win. The locked trigger cohort had 8 wins /1 loss vs plain (unadjusted two-sided paired sign p **0.0390625**, **not** multiple-comparisons-corrected nor a preregistered significance gate); replication trigger had 5/0 (p **0.0625**). Other comparisons against random/always3 do not establish broad superiority. Individual cohorts are small; no pooled positive headline.

**Cheap generic gate-cost proxy fails as an order-saving predictor:** `cheap4` chose **plain in 39/40 cases**, a^7 in 1; on locked holdout it tied plain on all comparable successful cases and did not recover any distinct order-driven savings. This is consistent with earlier resource decomposition: transformed modular constants are not intrinsically cheaper per phase round.

**Random policy caveat:** one deterministic public hash draw per N, not expectation over many independent random selectors. The ladder/random4 weighted ratio looks numerically favorable in both heldout groups, but the locked control paired tally is **2 improving, 2 ties, 3 worsening** for ladder vs random; no robust geometric selector superiority can be inferred.

### Validation-only order mechanism diagnostics

On selected ten keys/cell, `ladder` actually shortened validation multiplicative order in **9/10 replication trigger**, **5/10 replication control**, **8/10 holdout trigger**, **4/10 holdout control**. In locked trigger, the 8 improving positive-success rows corresponded to shortened orders; one unchanged-order case worsened. Lower order is NOT known without factoring or otherwise finding order, and is never fed into policy selection. Identity `ord_N(a^ell)=ord_N(a)/gcd(ord_N(a),ell)` held for every selected case, a known number-theoretic fact, not a new discovery.

## Independent peak logical width and actual claim boundary

For generic 18-bit clean-ancilla modular arithmetic in this model, arithmetic workspace **57** logical qubits. Matched full wide/recycled staged QPE cap: **93→58** peak logical qubits, **37.63% fewer** via phase recycling alone. Neither multi-exponent selection nor shorter order reduces this fixed peak-cap bound. No fault-tolerant resource, hardware compilation, device fidelity, physical-qubit, classical-vs-quantum wall-clock or energy cost, RSA-scale factoring or asymptotic Shor speedup is supported.

## Record the wins and choose the next falsification

**Preserve:** fully independent preregistration and blind public selection, successful four-job CI, all 40 distinct public-classical B31 survivors plus all 160 classically solved screened cases, validated strict public CF factoring and zero-QPU evidence. Original single-cube Dark Star mechanism repeats with **23%-ish** ideal logical CCX-per-success reductions in its new *conditional* trigger survivor panels (5/5 replication, 8/9 holdout improved), even after stronger controlled scrutiny. But `ladder` provides **no extra benefit** versus always3 in those strongest panels. Locked control misses majority improvement and B47 already classically factors four more apparent quantum-needed cases. We must NOT describe this as a new practical public multi-exponent policy improvement or experimental hardware advantage.

**Single next best test:** since the public residue rule did not outperform unconditional cube on new trigger cases and only 27/40 keys can produce factors in the nearest-bin model, prioritize (1) a genuinely **factor-producing full-outcome-QPE vs nearest-bin** comparison on *new* small polynomial/arithmetic instances and (2) classical preprocessing rival methods, with explicit total classical operation accounting, before moving to greater-bit RSA scale or spending IBM QPU time. Any learned public predictor should use separate discovery vs **new locked holdout**, not tune these reused 40 keys.
