# VERIFIED NEGATIVE — independent N24 public cubic selector holdout: both residue groups 2/8 joint order+factor-witness cases; half-order witness invariance 16/16; ZERO QPU

**Research lead / original program: Chase Lunsford / CaMaLabs.** Date **2026-10-20**. The experiment concerns number-theoretic *necessary conditions* for an ideal order-finding factoring strategy on 16 NEW 24-bit publicly and classically factorable synthetic semiprimes. It does NOT simulate an entire quantum phase-estimation histogram, compile a new circuit, measure quantum hardware, demonstrate factoring speed or reveal any RSA cryptographic weakness. **No QPU shots/jobs, IBM Open/paid quantum runtime, or quantum secrets.**

## What was preserved, and why this study was needed

Historical prior independent CaMaLabs work remains unchanged:

- [Fresh 22-bit all-outcome precision study](DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_RESULT.md): original preregistered public `N%3==2` group yielded **3/4** strict *ideal-model* cube wins, although one case factor-incapable and all Ns trivial classical factors. This was an actual bounded mathematical-model outcome, NOT hardware.
- [Fresh 23-bit 8-case full-outcome followup](DARK_STAR_N23_FULL_OUTCOME_CUBE_RESULT.md): the SAME `N%3==2` trigger **FAILS** (0/4 bounded cube wins, one strict model loss, two factor-incapable), while *the previously selected control `N%3==1`* happened to contain 3/4 conditional model wins and one factor-incapable. That group inversion was not a new preregistered positive trigger; interpreting it as a successful new policy without prospective validation would be hindsight selection.
- [N35 public-source deterministic sign selector FRESH target-compiler holdout](QRR_N35_STATIC_SIGN_FRESH_SEED_HOLDOUT_RESULT.md) independently showed robust gate-level *engineering* wins. The separate [complete four-controlled-power-block source/ISA CPU study](QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_RESULT.md) further verified 35-qubit integrated source arithmetic and all 8/8 matched seed CZ+depth improvements on both public bases; **QPU native feasibility still FAILED for all compiled layouts**. These compiler wins are NOT evidence of cubic order or factor-witness predictability. The real IBM Open Plan N15 recycled phase-qubit pilot remains independent.

This new study **preregistered an inverted, explicitly post-N23 hypothesis**: public N mod3==1 should predict *both* useful threefold order shortening and a proper standard Shor GCD factor witness. It also preregistered a truly public cheap bit-density diagnostic P2 with no parameter fitting, and required fresh disjoint 24-bit Ns.

## Complete prospectively frozen public population

[Preregistration committed BEFORE sample selection](DARK_STAR_N24_PUBLIC_PREDICTOR_PREREG.md): git **`cc143a71905775adcff1afd944a6af9502ee320f`**. Synthetic squarefree distinct-prime `N=pq` **2²³≤N<2²⁴**, with both construction primes restricted to **2000..6000**, p<q, expressly NOT representative of all random semiprimes or hard factoring. Construction p/q never entered source rank, decision feature or the frozen manifest: public N alone is stored. New SHA256 ranking salt `QRR-N24-PUBLIC-PREDICTOR-V1-POP-20261020`, public base rotation salt `QRR-N24-PUBLIC-PREDICTOR-V1-BASE-20261020`, original prime base pool `[2,3,5,7,11,13,17,19,23,29,31]`. Two balanced group strata `G1:N%3==1` and `G2:N%3==2`, 8 per group, **16 unique Ns total**. Each chosen case was the FIRST public-B31 classical survivor in its SHA order; all B31 public candidate screens and factors discovered before selection were recorded.

[Public selection original source](../hardware/dark_star_n24_public_predictor_manifest.py), [successful public-manifest freeze CI **39512436774**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512436774), original GitHub main **`6a3eb458d63c15b57468ceafadae6c94ebe5c260`** saved [immutable public-only manifest](../results/dark_star_ptp/dark_star_n24_public_predictor_manifest.json) **BEFORE any validation order or factor witness was computed**. The selected-row canonical SHA256 is **`d20a59ede42509cb3fd85ce5c6e1a61bd5edb70621964ebbd3ddea5d6ea2b889`**. Public frame had **57,052** candidate Ns. G1 screened 11 public candidates, three B31 factored; G2 screened 12, four B31 factored. The 16 selected all remained B31-unfactored at sample freeze and were selected irrespective of actual later cube effect. Manifest stores N/base/b, P1, P2 and public Jacobi symbol and the B31 scan ledger, with **NO** validation p/q/orders/witness labels, QPE costs or hardware outcomes.

**Frozen P1** binary decision `N%3==1`. Joint positive label **T** equals exact `ord_N(a)%3==0` AND an EVEN true order whose standard `gcd(a^(r/2)±1,N)` yields a proper nontrivial factor; this is a necessary condition for order-shortened Shor witness, **NOT** proof that cube yields a lower per-success ideal-QPE CCX cost. **P1 prereg support gate:** G1 at least **6/8** T-positive AND G2 at most **2/8**, otherwise fail. No post-result reinterpretation or subgroup filtering allowed.

**Frozen P2** public source-bitweight diagnostic `B(N,z)=sum_{j=0}^7 popcount(pow(z,2^j,N))` over eight simple public powers; vote T-positive iff `B(N,a³)<B(N,a)`, with ties negative. It is NOT a target-native CZ cost, compiler budget or model QPE result; only report confusion/accuracy, never promote it to a predictor without an independent success gate. Public Jacobi(a/N) was recorded as a non-selector observational feature.

## Independent exact algebraic witness identity (generic mathematical fact, not a novel theorem)

Let `r=ord_N(a)`, `g=gcd(r,3)`, `b=a³ mod N`. The standard identity `ord_N(b)=r/g` is exact. Because g is odd, `r` and `r/g` have the SAME parity. For even r:

```
b^((r/g)/2) = (a^3)^((r/g)/2)
            = a^(3r/(2g))
            = a^(r/2) (mod N).
```

- If g=3, the exponents are identical.
- If g=1, the exponent is 3r/2 = r/2 + r and `a^r=1 modN`.

Therefore **ordinary Shor even-order half-power GCD witnesses and their proper factors are exactly the same for plain a and cube b**, even when cubing changes r by a factor3. An odd exponent cannot change witness *capability* simply by shortening order. QPE stage probabilities, continued-fraction denominator availability and modular gate costs CAN differ; no claim of identical quantum runtime or all CF accepted bins follows.

The independently executed [validation source](../hardware/dark_star_n24_public_predictor_validate.py) FIRST applied the same PUBLIC post-B31 B47 Pollard p−1, bounded Floyd rho fixed seed2/3 with 64 iterations, prime trial through97, then full trial to sqrt(N). Every selected N was **actually factored classically**: G1 **6 rho+2 B47**, G2 **7 rho+1 complete prime trial**. The resultant ordinary PUBLIC proper factor, not synthetic hidden data, was used only AFTER the frozen selection to compute `lambda(N)`, orders for a and b, minimality with prime divisors, actual even halfpower modN and both proper GCD witness lists. All 16 matched the exact order identity and the **strict halfpower/witness-invariance property 16/16**. All classical factorization CPU/operation ledgers and public manifest source rows are available in original output JSON.

## ALL 16 held-out cases

`witness` means plain AND cube share a proper original half-order GCD factor; `T` requires the witness AND order shrinking by3. Group P1 predicts YES throughout G1, NO throughout G2. Bit-proxy P2 marks YES only on row N=8,549,227; this row turns out T-negative.

| Group | N | Public a | True r(a)→r(a³) | Proper half-order witness? | T |
|---|---:|---:|---|:---:|:---:|
| G1: N%3=1 | 15,319,861 | 23 | 1,531,150→1,531,150 | YES | NO |
| G1 | 12,454,609 | 23 | 2,074,590→691,530 | YES | **YES** |
| G1 | 10,878,391 | 2 | 258,852→86,284 | YES | **YES** |
| G1 | 10,219,201 | 17 | 283,689→94,563 | NO | NO |
| G1 | 8,549,227 | 13 | 1,067,882→1,067,882 | YES | NO |
| G1 | 12,662,677 | 23 | 351,531→117,177 | NO | NO |
| G1 | 9,928,417 | 5 | 2,480,524→2,480,524 | YES | NO |
| G1 | 9,841,129 | 29 | 4,917,410→4,917,410 | YES | NO |
| G2: N%3=2 | 10,807,151 | 11 | 1,800,052→1,800,052 | YES | NO |
| G2 | 13,411,667 | 2 | 1,675,542→558,514 | NO | NO |
| G2 | 12,161,921 | 23 | 6,077,346→2,025,782 | NO | NO |
| G2 | 13,208,333 | 11 | 314,294→314,294 | YES | NO |
| G2 | 10,494,119 | 23 | 5,243,820→1,747,940 | YES | **YES** |
| G2 | 10,237,943 | 13 | 1,705,240→1,705,240 | YES | NO |
| G2 | 10,303,847 | 19 | 1,716,236→1,716,236 | YES | NO |
| G2 | 12,720,251 | 11 | 3,178,278→1,059,426 | YES | **YES** |

The N24 frame is all PUBLIC and classically easy. It was not selected on validation orders or witness suitability; T-negative cases are **retained and counted**, including true threefold order shrinks without a proper half-order witness.

## Frozen classifications: both proposed indicators fail

| Result | N%3==1 G1 (8) | N%3==2 G2 (8) |
|---|---:|---:|
| Threefold order shortening | 4/8 | 4/8 |
| Plain/cube proper half-order witness present | 6/8 | 6/8 |
| **T: BOTH shortened order and usable witness** | **2/8** | **2/8** |
| Primary P1 6/8 vs≤2/8 gate | **FAIL** | control bounded at 2/8 |
| N24 post-B31 classically factored | **8/8** | **8/8** |
| Half-order witness exactly invariant across cubing | **8/8** | **8/8** |

**P1 confusion**: TP=2, FP=6, FN=2, TN=6; T count4, negative12; **accuracy50%, balanced accuracy50%, sensitivity50%, specificity50%**. Under the fixed balanced-group conditional sample the one-sided hypergeometric enrichment tail is **p≈0.7154 descriptive**—no evidence the group1 stratum enriches joint usable shortening. **P1 prereg support FAILS**, not even close to ≥6/8 G1. Merely switching N22's trigger from residue2 to residue1 in hindsight does not fix the missing predictor.

**P2** cheap public bit-popcount source vote: TP=0, FP=1, FN=4, TN=11, **accuracy68.75%, balanced accuracy45.83%**, sensitivity0%; an **always-negative** classifier would reach **75% raw accuracy** because 12/16 cases are negative. Do NOT treat P2's 68.75% accuracy as validation; it did not find a single desired positive. These P2 figures are descriptive only, as frozen.

**Jacobi exploratory count, NOT promoted to a selector:** among ten Jacobi−1 cases, nine have ordinary witness capacity but only three T-positive; among six Jacobi+1 cases, three have a witness and one T-positive. Jacobi sign alone does not identify cube shortening in this tiny group.

## Original CI and reproducibility

[Source original 24-bit public classical manifest freeze Actions **39512436774**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512436774) **SUCCESS** and committed the original public SHA manifest `6a3eb458d63c15b57468ceafadae6c94ebe5c260` BEFORE test labels. [Source true witness order test + independent all-16-case validation Actions **39512868715**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39512868715) **SUCCESS**: exact SHA, every published public feature, every classical factor, prime interval/primality/order minimality, both factor witnesses, full group counts/confusion tables and separate true P1 gate were all audited. This workflow committed the **ORIGINAL unchanged source receipt** [`dark_star_n24_public_predictor_validation.json`](../results/dark_star_ptp/dark_star_n24_public_predictor_validation.json) without a second science rescore.

Original raw stdout and validation JSON are in the GitHub Actions artifact and repo. The result internally reports zero_QPU and actual qpu_jobs_submitted=0; no hardware libraries, backend read or IBM Quantum account auth were used.

**Interpretation:** This prospective necessary-condition holdout **falsifies both simple public selectors as reliable useful-cubic predictors within the stated sample**, while corroborating an elementary universal odd-exponent factor-witness invariance. The N22 prior 3/4 *ideal-QPE model* success is historical and remains, but the N23 0/4 trigger failure and N24 equal-group 2/8 demonstrate no dependable N mod3 public selection rule. N24 did NOT evaluate the full bounded QPE per-success CCX ratio and cannot reverse or subsume older QPE model success/failure labels. **No real Shor factor recovery, no hardware quantum speed/fidelity demonstration, no RSA cryptanalysis breakthrough**. Focus further work on the separately robust *public arithmetic resource reduction* or on factoring-hard classical benchmarks with explicit physical-QPU feasibility, rather than additional posthoc cubic selection.
