# VERIFIED FRESH N25 post-B47/rho64 public survivors: 8/8 classically unsolved under fixed screening, 0 bounded cubic adaptive-model wins, 4 inconclusive / 4 factor-incapable; ZERO QPU

**Research lead and originating program: Chase Lunsford / CaMaLabs.** **Date: 2026-10-28.** **Status:** independently frozen public selection, independently run 8/8 CPU-only source-model shards, original source results preserved and reaudited without rerunning phase sampling. **NO IBM QPU jobs, Open Plan/free minutes, paid Runtime or IBM SDK connection.** These are **ideal simulated phase measurements** and *source-level reversible modular-arithmetic CCX structural estimates* for 25-bit classically tractable N=pq, NOT physical quantum computing or hardware native CZ.

## Why repeat, and what was prospectively different?

The previous [original N25 online CF + arithmetic experiment](DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_RESULT.md) sampled eight B31 survivors but 7/8 were subsequently solved by a stronger *public* B47/p−1 +64-step rho +trial≤97 budget, leaving essentially no relevant quantum task under that prescribed classical prefilter. Its original frozen outcome **0 bounded cubic wins, 0 bounded losses, 6 inconclusive, 2 undefined** remains untouched. [Prior secondary exact changed-order break-even](DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_RESULT.md) found 3 factor-capable cubic order reducers with *higher* fixed-workload structural source CCX (up to ~1.3%), but was unable to establish their factor-success ratios. These results do **not** measure a useful factoring advantage from cubing.

Our new [pre-scoring preregistration](DARK_STAR_N25_POST_B47RHO_FRESH_COHORT_PREREG.md) was committed as **`aac41888337b7c2fb07b4c9855d14feba757f79b`** before the new selection and before any validation order or ideal-QPE model. It freezes **the full original 24-stage, four-shot/stage, 4,096-sample/stage model, conservative 65-bin+tail bounds and original public on-demand continued-fraction/GCD verifier** rather than choosing an advantageous precision after seeing data. Exactly **8 NEW hash-ranked N25 public semiprimes**, four per N mod3 group, selected only if they survive **BOTH** already-published B31 and stronger executed B47/rho64/trial97 filters. Exclude all eight old N. No ranking, public base selection or inclusion criterion uses hidden p,q, validation-only multiplicative order, QPE outcomes, factor witness or source-gate cost.

This is a **new public-only classically-nontrivial-under-fixed-budget cohort**, not a stronger hardness claim: these small 25-bit semiprimes are easily factored using standard classical programs outside the deliberately limited screen.

## FIRST: separate public-only SHA-freeze, before scoring

[Public selector](../hardware/dark_star_n25_post_b47rho_public_manifest.py) generated the prior 80,200 unique 25-bit synthetic semiprime N frame, discarded the private construction p/q identities and ranked the public N with `QRR-N25-B47RHO64-FRESH-POP-20261028|group|N`. Chose public coprime a by independent public SHA rotation `QRR-N25-B47RHO64-FRESH-BASE-20261028|group|N` from `(2,3,5,7,11,13,17,19,23,29,31)`. Applied original metered `mc.classical_cascade(N,a)` (B31, public power2), then, for each survivor, the same executed classical `Pollard p−1 B47`, two attempts of Floyd rho up to 64 iterations each, and trial prime≤97. Explicit cap **≤1,200** screenings/group; success reached after **137 screened G1** and **85 screened G2** candidates, four nonfactorable-under-filter each. All real public screening ledgers—including cases solved and operation counts—are archived in the original public-only manifest.

The separate [manifest GitHub Actions freeze **40657776029**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40657776029) **SUCCESS** and committed the complete [manifest](../results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_manifest.json) to main **BEFORE any scorer/QPE job was created**. Freeze SHA256 of canonical selected rows:

`e46425355e422ff32d167920d7ddc80ada0ed8733c73048912133db6f79526d2`

| NEW public N | Base a | Public cube a³ mod N | Group / original hash-ranked position | Public pre-QPE classical result |
|---:|---:|---:|---|---|
| 18,291,577 | 19 | 6,859 | G1 rank3 | Unsolved under B31+B47/rho64 |
| 32,028,229 | 19 | 6,859 | G1 rank31 | Unsolved under B31+B47/rho64 |
| 32,170,573 | 19 | 6,859 | G1 rank67 | Unsolved under B31+B47/rho64 |
| 32,536,033 | 19 | 6,859 | G1 rank137 | Unsolved under B31+B47/rho64 |
| 21,546,281 | 19 | 6,859 | G2 rank2 | Unsolved under B31+B47/rho64 |
| 21,667,697 | 29 | 24,389 | G2 rank50 | Unsolved under B31+B47/rho64 |
| 28,445,861 | 19 | 6,859 | G2 rank75 | Unsolved under B31+B47/rho64 |
| 33,112,721 | 19 | 6,859 | G2 rank85 | Unsolved under B31+B47/rho64 |

**Cohort limitation:** Public hash/survival selection yielded **base19 in seven of eight** rows (base29 one); this is a severe concentration, despite the original publicly defined 11-base pool. Do **not** claim diverse-base or population-wide generality from this sample. Selection is still prospective from the published public policy and not conditioned on validation-only order or QPE outcome. New N identity overlap **ZERO** with the original eight N25 cases and also **ZERO** with a separately preregistered concurrent **four-case fixed-m50 N25 cohort** (different population salt).

## SECOND: full original 24-stage source model on all eight frozen public cases

[Scorer wrapper](../hardware/dark_star_n25_post_b47rho_fresh_score.py) reads that immutable SHA and invokes the *unchanged original* [N25 online CF/arithmetic source](../hardware/dark_star_n25_online_qpe_arithmetic.py), changing **only** the scoped frozen manifest/SHA, independent new phase SHA salt and report destination. It explicitly enforces original exact modeling conditions: 24 phase widths **m=4,6,…,50**, **4096 pseudo-IID ideal eigenphases per public arm per width**, **4 modeled shots per stage**, matched shared uniform phase/bin draws for a vs a³, original 65-bin centered QPE sinc² head and explicit nonzero tail omission upper bounds, original empirical Bernstein H/T confidence envelopes, **family1536 and alpha0.01**, and original sequential expected arithmetic source CCX and phase-cost success intervals. This is a probabilistic model with pseudorandom and float assumptions, **not a mathematical proof of physical quantum sampling probabilities**.

**Crucial correctness separation:** for each selected public N, only *after* the public manifest had been archived, validation-only p,q and multiplicative order r are computed to draw synthetic ideal eigenphases and verify **r(a³)=r(a)/gcd(r(a),3)** and the half-power factor-witness identity. The on-demand public factor verifier receives **only N, public a, the *simulated measured* y and Q=2^m**, computes continued-fraction candidates d (1<d≤N), tests even orders with pow(a,d,N), and GCD(a^(d/2)±1,N), with exact separate counts for all denominators, modular powers and GCD operations. NO private factors/order enter candidate selection or verifier, and NO giant O(N) factor-producing-denominator precomputation occurs. Each original shard repeated the existing **1,680** toy input verifier equivalence selftests. Structural costs use `stage_arithmetic_count(N,base,m)` from the existing public *logical source gate-count model*, **NOT Qiskit compiled native gates or hardware fidelity**.

[Original **eight CPU-only source shard jobs + original merge Actions 40658075317**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658075317) **9/9 SUCCESS**, all original per-row JSONs preserved without rerunning samples by the independent merged audit, stored at:

- [merged original all-eight model and full stage arrays](../results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_all8.json)
- [eight complete original source sample receipts](../results/dark_star_ptp/) `dark_star_n25_post_b47rho_fresh_index00.json` through `index07.json`.

A **separate** [independent original-artifact SHA+math audit Actions **40658465772**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658465772) **SUCCESS**. It downloaded **all eight ORIGINAL uploaded shard artifacts**, byte-compared each with the committed untouched source receipt, SHA256-stamped the original bytes, independently reconstructed the original interval-ratio classifier from raw values (without running QPE), checked all **384 original arm×N×stage** arrays (8 cases×2 bases×24 widths), sample counts/omitted-tail and interval structure, online verifier operation sums, original manifest hash/no-prior-cohort overlap, actual public filter, order-cubic identity, no-QPU counters, and independent N identity nonoverlap with the separate concurrent four-case cohort. Its [independent audit receipt](../results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_original_audit.json) is preserved. No additional sampled results were introduced in the audit.

## Full eight-case outcomes, including zeros and invalid factor routes

The preregistered ORIGINAL 24-stage expected source-CCX-per-factor interval classifier does **not** find a bounded win or loss for any of the eight.

| New N / public a | Validation-only order plain → cubic | Factor-capable under strict fixed-base verifier? | Bounded source-cost model classification |
|---|---|---|---|
| 18,291,577 / 19 | 1,523,583 → 507,861 | No | Factor-incapable / undefined |
| 32,028,229 / 19 | 8,004,115 → 8,004,115 | No | Factor-incapable / undefined |
| 32,170,573 / 19 | 8,039,800 → 8,039,800 | Yes | Inconclusive |
| 32,536,033 / 19 | 5,420,718 → 1,806,906 | Yes | Inconclusive |
| 21,546,281 / 19 | 10,768,482 → 3,589,494 | Yes | Inconclusive |
| 21,667,697 / 29 | 5,414,589 → 1,804,863 | No | Factor-incapable / undefined |
| 28,445,861 / 19 | 7,108,731 → 2,369,577 | No | Factor-incapable / undefined |
| 33,112,721 / 19 | 16,550,106 → 5,516,702 | Yes | Inconclusive |

The four factor-incapable rows are **not cryptographic factoring impossibility**: they are incapable under the specific fixed a / strict even-order+nontrivial-square-root verifier (validation-only witness false). Another base or ordinary classical factoring can succeed. In three of the four factor-capable rows, cubic *does* reduce true validation-only order by factor3; however the resulting **modeled expected CCX per factor** interval overlaps unity. Three example original upper/lower cube/plain model ratios: N32,536,033 `[0.3780,2.1772]`; N21,546,281 `[0.3565,2.2599]`; N33,112,721 `[0.3321,2.2042]`. Lower bounds below 1 alone do **not** establish a win; upper bounds all exceed 1. The fourth factor-capable same-order row N32,170,573 is also inconclusive `[0.4070,2.5433]`.

| Immutable original comparison/status | Previous B31-only eight cases | NEW B31 + B47/rho64 public survivors |
|---|---:|---:|
| Number selected | 8 | 8 |
| Actually unsolved by fixed stronger public budget before model | **1/8** | **8/8** |
| Model bounded cubic wins | 0 | **0** |
| Model bounded cubic losses | 0 | **0** |
| Model inconclusive | 6 | **4** |
| Factor-incapable/undefined | 2 | **4** |
| Original frozen ≥3 bounded wins primary model gate | FAIL | **FAIL** |
| Actual IBM QPU jobs / paid Runtime | 0 | **0** |

The prospective public budget improvement is real and separately verified: all eight require additional work *relative to this deliberately narrow published classical budget*. It does not rescue the all-base cubing claim. **0 bounded cubic gains under this 24-stage model** is the correct outcome.

### Relation to a separately run positive, fixed-precision four-case study

A separate, contemporaneous, independently preregistered **four-case** N25 study [`DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_RESULT.md`](DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_RESULT.md) also froze **B31+B47/rho64 public survivors**, but with **DIFFERENT public N**, a DIFFERENT SHA population, and a DIFFERENT estimand: one fixed **50-bit** phase precision, **16,384 simulated samples per arm** and nominal Hoeffding + bounded omitted-tail per-attempt success, not the original adaptive 24-stage 4-shot/step modeled per-factor source-CXX envelope. That separate experiment reports **2/4 nominal bounded cubic model wins**, both order-reducing. Its valid *fixed-width* result is **not contradictory** to our 0/8 *adaptive 24-stage expected-cost envelope* result, and the two outcomes MUST NOT be pooled or called a replicated hardware success: cases, acceptance criteria, precision, sample budget and model uncertainty differ. Both experiments are **CPU-only ideal QPE source cost simulations with zero QPU jobs**, not practical quantum factoring evidence.

## Scientific interpretation and future experiment gate

**Verified prospective evidence:** We can prospectively freeze a truly fresh, fixed-classical-filter survivor cohort without hidden p/q/order selection and run independently tested public on-demand CF/GCD ideal QPE with explicit source-CCX and online CPU-work accounting. All eight complete results are independently preserved, including four factor-incapable cases. This eliminates the previous cohort's issue of most cases being already solved by the fixed stronger *public* filter.

**Unresolved:** The model's broad early-stopping expected-cost intervals cannot certify cube improvement; all public 25-bit moduli are classically easy outside the fixed budget; selection happened to concentrate at a=19; source-count model scales to tens of millions of CCX per stage at high m and is not actual device native CZ or scalable fault-tolerant circuit cost. No practical quantum hardware advantage is supported.

**Best next empirical test:** preregister an *independent larger, base-diversified public cohort* with the same B31+B47rho budget, then compare **same-matched fixed-width m50 on-demand CF/GCD per-success ratios** and **full adaptive expected-cost envelopes** on EACH identical public N in a common experimental design. Account for public CPU verifier time and source CCX without adding incompatible units. Lock all primary labels before simulation. Only after that and realistic actual circuit resource feasibility should any new QPU request be contemplated; no automatic IBM Open/paid hardware submissions. Preserve all successes and negative controls in CaMaLabs with Chase Lunsford credited as research lead.
