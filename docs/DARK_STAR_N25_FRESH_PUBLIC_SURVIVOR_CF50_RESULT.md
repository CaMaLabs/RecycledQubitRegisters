# VERIFIED — Fresh public N25 fixed-m50 ideal QPE online CF/GCD: 2/4 bounded cubic SOURCE-CCX-per-factor model wins; ZERO QPU

**Research lead / original program: Chase Lunsford / CaMaLabs.** **Date:** 2026-10-28. **Status:** Newly frozen public cohort, 4/4 original independent CPU-only model computations SUCCESS, separate original receipt audit/preservation SUCCESS. This is **not** a real quantum processor experiment, compiled N25 circuit, four-phase/Shor hardware factoring run, cryptographic factoring result or speedup. **ZERO IBM QPU jobs, ZERO free Open Plan runtime, ZERO paid runtime.** Only ideal **simulated** phase measurements at 50 control bits and source *structural* CCX cost estimates, not Fez native CZ.

## Previous research and why the new test was necessary

The prior independently preserved [original N25 online CF + public source arithmetic model](DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_RESULT.md) took eight semiprimes selected under B31, then found 7/8 classically solved under a further public fixed B47/rho64/prime97 budget; in its 24-stage, 4-model-shots/stage, 4096 nominal phase samples/stage design the preregistered evidence was **0 bounded cubic wins, 0 losses, 6 inconclusive, 2 undefined**. Later [exact order and prefix cost audits](DARK_STAR_N25_CHANGED_ORDER_BREAK_EVEN_RESULT.md) found **three** factor-capable, order-reducing cases where the cubic base costs between 0.75% and 1.32% MORE source CCX under a fixed 96-shot workload, but could **not determine** if a higher per-shot factor success probability offset this modest gate penalty. Their exact original cohort SHA was `66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7`; every original result remains unchanged.

This experiment is a **separately preregistered NEW cohort**, not remeasuring or post-selecting those eight. The [frozen protocol](DARK_STAR_N25_FRESH_PUBLIC_SURVIVOR_CF50_PROTOCOL.md) was committed as `fc7e4a4eb641a31932b3a375aacb44409b9669d6` BEFORE case selection, order inspection or QPE scoring, freezing public SHA population/base salts, group counts, exact fixed classical budgets, sample count, one fixed width, error limits, cost metric and win criterion.

## First frozen artifact — public selection BEFORE factors/orders/QPE

[Deterministic public screening code](../hardware/dark_star_n25_fresh_cf50_public_manifest.py) generates distinct squarefree N=pq semiprimes in `2^24..2^25`, with public frame p,q in the construction ONLY (selection is based on public N and hashes). It excludes ALL eight previous N, SHA-ranks candidate N in two groups (`N mod3 = 1`, `=2`) with public salt `QRR-N25-CF50-FRESH-POP-20261028`, chooses a coprime a by a *separate* public hash rotation among 11 fixed bases, and accepts only candidates **actually NOT factored** by a fixed public B31 prefilter *and* the recorded `Pollard p−1 B47, Floyd rho64 (seeds2/3), prime trial≤97` budget. Exactly **two survivors per group**, max first200 public candidates/group, no reselection or hidden order/witness criterion. The public selector cannot observe which bases change order, produce factors under the future QPE verifier, or have a favorable source CCX.

It screened **25** G1 public candidates (10 solved at B31, 13 more at B47/rho64, 2 unsolved) and **2** G2 candidates (2 unsolved). Every attempted N, base, public rank, real classical operation counts and CPU accounting is stored in the **original separate public manifest** [`dark_star_n25_fresh_cf50_manifest.json`](../results/dark_star_ptp/dark_star_n25_fresh_cf50_manifest.json). New selected public manifest SHA:

`a136789dcdcbb32730f293973805f8edacf5d684d8350c2e51c665db0099d629`

The separate [public-only manifest freeze GitHub Actions **40657655151**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40657655151) **SUCCESS**, persisted full public candidate ledger and selected SHA in main before the scoring script or QPE workflow ran. These are "not solved under this deliberately limited budget", **NOT** "difficult for classical factoring"; N25 integer factoring remains trivial with practical classical algorithms.

| Public fresh N | Public base a | Cube b=a³ modN | Public group | Original ranked location | Fixed classical filter |
|---:|---:|---:|---|---:|---|
| 19,774,537 | 29 | 24,389 | G1, N mod3=1 | 19 | Unsovled under fixed B31+B47/rho64/trial97 |
| 28,467,259 | 31 | 29,791 | G1, N mod3=1 | 25 | Unsovled under fixed B31+B47/rho64/trial97 |
| 29,915,783 | 29 | 24,389 | G2, N mod3=2 | 1 | Unsovled under fixed B31+B47/rho64/trial97 |
| 24,556,361 | 23 | 12,167 | G2, N mod3=2 | 2 | Unsovled under fixed B31+B47/rho64/trial97 |

## Second phase — genuinely measured ideal head success rates, not hypothetical break-even ratios

[The separate frozen four-arm scoring source](../hardware/dark_star_n25_fresh_cf50_success.py) reads and verifies the *already committed* manifest/SHA; only then determines p,q, public a/cube orders for ideal phase simulation and validates `ord(a³)=ord(a)/gcd(ord(a),3)`. Those factors/orders are **validation/sampling ONLY** and are NEVER passed to the measured-y **public** continued-fraction/GCD factor verifier `online_factor_cf(y,Q,a,N)`, which tests denominators on demand and separately counts denominator checks, modular exponentiations and GCDs. A short-case independent direct verifier equivalence selftest passes **1680 cases per shard**.

One fixed public precision `m=50` with `Q=2^50`; **16,384** paired ideal pseudo-IID phase/bin draws for **each arm of each four N** (=**131,072** individual ideal simulated phase outcomes total). The public deterministic independent sample seed is `QRR-N25-CF50-FRESH-PHASE-20261028|N|50`. Both arms couple the uniform phase-index and QPE bin-draw streams but use their own validation-only true orders; this is honest correlated sampling, not equivalent orders or an extra source oracle.

The original ideal QPE model's **65 centered sinc² probability bins** are sampled; all omitted probability tail is explicitly bounded by **1/63** in total. A conservative nominal **simultaneous 99% Hoeffding family** over **4×2=8 arms** uses `epsilon=sqrt(log(2*8/0.01)/(2*16384))`, and overall ideal success interval `[max(0,h−epsilon), min(1,h+epsilon+1/63)]` where h is observed head success. The omitted tail is **NOT** misclassified as unsuccessful in upper bounds. These are nominal IID/model bounds (fixed SHA pseudo-random samples, float arithmetic, not directed-rounded formal mathematics), **not measured real quantum processor probabilities**.

Source arithmetic cost for exactly this one **m50 fixed-width modeled attempt** comes from the independently existing `stage_arithmetic_count(N,base,50)['ccx']`. That is the user's already used public reversible arithmetic source-count model, **NOT actual transpiled gates**: ~41 million modeled CCX per attempt for these 25bit cases, vastly beyond the verified N35 toy native resource results. Online classical verifier operation counts are recorded separately and must not be summed directly with source quantum CCX without a conversion cost model. The experiment does not measure a complete adaptive 24-stage stopping policy.

### Original four independent result rows

| New N / a | Validation-only order plain→cube | Ideal head successes plain / 16,384 | Cubed / 16,384 | Source CCX plain→cube (one m50) | Nominal bounded classification |
|---|---|---:|---:|---|---|
| 19,774,537 / 29 | 9,882,818→9,882,818 | 7,325 | 7,325 | 40,939,341→41,169,698 | **Inconclusive** |
| 28,467,259 / 31 | 7,114,126→7,114,126 | 7,631 | 7,631 | 40,900,461→41,053,362 | **Inconclusive** |
| **29,915,783 / 29** | **14,952,360→4,984,120** | **4,139** | **6,335** | 40,925,171→41,236,298 | **Bounded cubic win** |
| **24,556,361 / 23** | **3,068,304→1,022,768** | **5,356** | **8,190** | 41,095,307→41,343,785 | **Bounded cubic win** |

All four were **factor-capable** under a post-freeze exact witness check, and none was selected using that outcome. Two have order unchanged and paired head samples identical; source cost still increases for cube, but the conservative intervals are too wide to certify a LOSS. Two have order reduced by factor 3 and the cubed model has greatly higher factor-producing head outcomes.

### Actual cost-vs-success break-even checks, with confidence bounds

For independent repeated fixed-m50 model attempts with positive ideal factor probabilities, expected logical source CCX per factor success is `C/p`, so cubic wins when `p_cube / p_plain > C_cube / C_plain`. This comparison is **not** valid as an unmodified complete adaptive stopping-rule cost. Conservative interval lower bound for `p_cube/p_plain` is `p_cube_low / p_plain_high`, which includes unassigned tail success; upper is `p_cube_high / p_plain_low` where defined.

| N / a | Observed head success ratio cube/plain | Source CCX break-even cube/plain | Nominal 99% interval for ideal success ratio | Certified under frozen model? |
|---|---:|---:|---:|---|
| 19,774,537 / 29 | 1.000 | 1.005627 | [0.904, 1.106] | Inconclusive |
| 28,467,259 / 31 | 1.000 | 1.003738 | [0.908, 1.102] | Inconclusive |
| **29,915,783 / 29** | **1.531** | **1.007602** | **[1.311, 1.757]** | **Bounded win** |
| **24,556,361 / 23** | **1.529** | **1.006046** | **[1.355, 1.702]** | **Bounded win** |

Two large model success-ratio lower bounds exceed even the *increased* public source CCX per attempted measurement. **Preregistered provisional 2/4 bounded-win directional signal criterion PASSED:** two bounded wins, zero bounded losses, four witness-factor-capable. **This is not replicated evidence of a general advantage.** It indicates that some unseen fixed public N and a can show sufficient ideal order-related online-CF success increases at m50 to compensate modest public structural source-CCX overhead.

## Provenance: original four CPU shard successes, separate independent archive without rescoring

[**Original four separate GitHub Actions source-score jobs 40657959490**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40657959490) **4/4 SUCCESS**. All four jobs used no IBM libraries/secrets, pinned CPU `numpy==2.2.6` and `numba==0.61.2`, verified the SHA-frozen public manifest and ran the original public on-demand verifier at 50-bit ideal precision with 16,384 pseudo-random samples PER ARM. Each CI independently verified original row selftests, factor witness/validation-only order identity, source count fraction and no-runtime status. Original exact generated shard results were uploaded to four different CI artifacts.

[**Independent original-artifact GitHub Actions 40658211255**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658211255) **SUCCESS**. It downloaded all four original JSONs from original CI WITHOUT calling phase sampler or order solver, independently checked original source logs/counts, 131,072 total ideal shots, 4×16,384×2 semantics, source CCX integers and exact Fraction ratios, nominal Hoeffding+tail bounds, classification, immutable manifest, failure to solve each with original fixed public classical budget, and zero QPU. It committed the **unchanged original JSON bytes** to:

- [index00 original](../results/dark_star_ptp/n25_fresh_cf50/n25_fresh_cf50_index00.json)
- [index01 original](../results/dark_star_ptp/n25_fresh_cf50/n25_fresh_cf50_index01.json)
- [index02 original](../results/dark_star_ptp/n25_fresh_cf50/n25_fresh_cf50_index02.json)
- [index03 original](../results/dark_star_ptp/n25_fresh_cf50/n25_fresh_cf50_index03.json)

and the [independently derived combined summary with all original rows](../results/dark_star_ptp/dark_star_n25_fresh_cf50_all_4.json). The source original hashes/receipts and all prior eight-cohort originals remain distinct. Report and research log recorded after the source and audit were complete.

## Important concurrent contrast: separate fresh eight-row post-B47rho cohort found NO bounded wins

A **different SHA-frozen**, independently run [fresh eight-row N25 post-B47rho model aggregate](../results/dark_star_ptp/dark_star_n25_post_b47rho_fresh_all8.json), source [GitHub Actions 40658075317](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40658075317), has its OWN public cohort SHA `e46425355e422ff32d167920d7ddc80ada0ed8733c73048912133db6f79526d2` and **8 different public N/base cases**, scoring the different **24-stage m4..50** model with `4096` per stage and stopped-stage costs. Its separate result found **0 bounded cube wins, 0 losses, 4 inconclusive and 4 factor-incapable/uncertified**, with its own preregistered model signal gate FAIL. These two studies **are NOT interchangeable**: this report tests **four** previously unobserved public survivors at one fixed m50 with 16,384 samples/arm and per-ATTEMPT cost; the other measures eight new survivors under a multi-stage model with different success-bound aggregation and source-cost model. The zero-win separate cohort means **do not portray this fixed-m50 positive as population replication, full Shor speedup, or a scientifically mature advantage**.

## Decisions and next falsifiable step

**Preserve both successes and negatives.** The two fixed-m50 bounded wins support only the directional within-cohort **ideal source-model** claim with public on-demand verifier and conservative nominal bounds. The unmeasured gap remains large: *real quantum circuits* implementing the source modeled N25 multipliers, native ISA costs, noise/fidelity, quantum recycling, and complete real QPE factor recovery. The 25bit semiprimes are classically trivial, and the 41-million-source-CCX-per-attempt modeled circuits are nowhere near Fez's earlier frozen **≤800 native CZ AND ≤2000 depth** feasibility heuristic (source CCX and native CZ are DIFFERENT metrics; do not falsely equate them). **NO REAL IBM QPU**.

Next: pre-register a bigger fresh cohort and a correctly priced, fixed independent **m50 vs multistage adaptive early-stop** comparison with public verifier CPU weights, or analytical variance reduction/precision improvements followed by true source gate generation, while continuing to distinguish negative eight-row staged evidence. Don't expand this result to a novelty theorem, a general cubic Dark Star success probability law, or actual hardware speedup. Keep the original verified real N15 phase-register recycling success and its genuine device receipts separately.
