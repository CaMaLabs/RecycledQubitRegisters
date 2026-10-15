# VERIFIED — new disjoint 22-bit Dark Star cubic full-outcome precision holdout passes primary model gate, not real factoring

**Research lead and originating quantum optimization:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-15 Pacific. The executed study is an **IDEAL-QPE generic clean-ancilla logical CCX MODEL**, not a QPU, classical-vs-quantum wall-clock speedup, fault-tolerant physical-gate estimate, or practical factoring innovation. **ZERO QPU jobs.**

## Milestone context and historical negative controls MUST survive

Earlier carefully archived CaMaLabs work established phase-register recycling's **simultaneous logical width reduction independently** of Dark Star base transformations. Scout cases gave large conditional ideal-QPE benefit, but the broader n17/18 ell5 trigger-enrichment FAIL, ell7 weak/failed, n18 144-row classical-first v2 with only 2/5 ell3 improvements in the trigger group, n18 public multi-exponent ladder failed to beat always-cube consistently, and a fresh n22 six-case ladder-vs-cube control had 3 improves/3 worsens despite favorable aggregate ratio. Those historical failures remain evidence.

At n22 the previous frozen four-case all-outcome-head (16,384 phase samples, conservative Hoeffding plus tail) was three inconclusive ratios and one provably factor-incapable: primary two-case trigger gate DID NOT PASS. The [same-case numerical precision audit](DARK_STAR_N22_NUMERICAL_PRECISION_AUDIT_RESULT.md) later narrowed finite bands ~11–12× and found one conditional modeled cube win on the SAME old sample; **not independent confirmation**, and old failed primary not erased. The present work was designed and frozen BEFORE selecting its **eight different Ns** to actually test generalization of that precision methodology.

## Original frozen provenance and independent audit

- Original preregistration [`DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_PREREG.md`](DARK_STAR_N22_FRESH_PRECISION_HOLDOUT_PREREG.md), commit `ddf910cf187b11d1f800c2d4a65d0473cbfd4035` BEFORE choosing new Ns, validation private factors/orders or ideal-QPE cost results. Four trigger N%3=2 and four control N%3=1; public B31-classical-surviving independent SHA sample, specific strict public CF and model cost rules; precommitted 3/4 trigger model-win criterion.
- [Public-only selection script](../hardware/dark_star_n22_precision_fresh_public_manifest.py) commit `36f510020a57ddbcf58d1849eead18545685b112`. [FROZEN PUBLIC N/a manifest](../results/dark_star_ptp/dark_star_n22_precision_fresh_public_manifest.json), committed by GitHub Actions in **`67ec6bcdd8cd91d033663c7fab27a646b9ac052f`** BEFORE scoring, SHA256 selected canonical rows **`5c18715c4448069e6231645e180e216b7e591e15a149cbc12d486fe9b9664570`**. The manifest contains ONLY selected public N/base, public a³ choices, all publicly screened B31 candidate and operation counts, **NO synthetic p/q, r, QPE outcomes or cost**.
- The eight new N are disjoint from all **16 previously selected n22 Ns** in older manifests by PUBLIC identifiers alone. No samples chosen for favorable order, factor capability, quantum resource or classical post-baseline performance.
- [Scorer](../hardware/dark_star_n22_precision_fresh_holdout.py) commit `070dc174254b26c24b77563a696a1e62672d7477`; reuses identical `dark_star_n22_numerical_precision_audit.py` math (same SHA phase seed scheme, exact FFT m≤18, W32, 131072 samples, empirical Bernstein), with only preregistered **family-size union budget change 672→1344** because there are now 8 rather than 4 N. Same public factor-producing strict CF verifier. ZERO other post-outcome tuning.
- [Actual freeze + two scoring jobs GitHub Actions **38808625980**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38808625980): **3/3 SUCCESS**, 8 samples; frozen manifest commit BEFORE QPE validation, strict external independently checked public N/base, proper factor, stage and logical resource assertions. ZERO QPU.
- [Independent original-artifact verification and receipt preservation **38809052306**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38809052306): SUCCESS. Downloaded original trigger/control raw JSON from scientific run, verified public SHA, all 8 N disjoint from old 16, proper classical factors, ALL exact & bounded stage invariants and strict frozen primary class outcome, zero QPU, committed immutable results [trigger JSON](../results/dark_star_ptp/dark_star_n22_fresh_precision_trigger.json), [control JSON](../results/dark_star_ptp/dark_star_n22_fresh_precision_control.json). Original results have not been rerun or edited to tune findings.

## Public selection and classical factoring: 25 screened, 17 already factored, remaining 8 classically solved

The synthetic n22 semiprime frame `2^21≤N<2^22`, p<q distinct primes ≥11, is ranked by public SHA256(`QRR-N22-FRESH-PRECISION-20261015|group|N`). First coprime base from independently SHA-rotated 11-prime base pool. Frozen public GCD, bounded power2 GCD and Pollard p−1 B31 remove any N found easy. The first FOUR **B31 survivors** per group are retained without regard to hidden factors/orders, even if quantum-factor-incapable. All screened N, classical source and operation counts preserved.

| Group | Public N screened | Factored by B31 | Selected B31 survivors | Subsequent PUBLIC factor resolution |
|---|---:|---:|---:|---|
| Trigger (N mod 3=2) | 9 | 5 | 4 | 1 B47, 3 fixed-seed rho |
| Control (N mod 3=1) | 16 | 12 | 4 | 4 fixed-seed rho |
| **Total** | **25** | **17** | **8** | **8/8 solved classically** |

**All 25 screened semiprimes are factored without quantum computation** by the prescribed public classical cascade. Furthermore the model's public enumeration of EVEN candidate d in [2,N] with `a^d≡1 (mod N)` and actual public GCD half-power witness **can itself produce proper classical factors**, so it is not a free online quantum subroutine. Its large public modular multiplication, GCD and CPU ledger is recorded in original JSON and cannot be conflated with physical quantum runtime.

## Fixed numerical method and correct uncertainty interpretation

For matched public bases `plain=a` and `cube=a³ mod N`, the validation-only synthetic prime factors provide the ideal uniform QPE eigenphase mixture. **Validation secret p,q/r is NEVER used to select N, a, quantum policy, or to accept a CF output**; the factor test uses only public N/base/d and proper nontrivial GCD.

Stages m=4,6,…,44 with four simulated shots/stage. **All Q=2^m phase outcomes exactly evaluated via ideal eigenphase-mixture FFT for m≤18** (float normalization checked); at m>18 score all 65 centered nearest phase bins per eigenphase, with an analytic ideal probability omitted-tail ≤1/(2·32−1)=1/63. For validation order r≤131072, enumerate all eigenphases; for larger r, **131072** SHA-seeded nominal independent uniform eigenphase draws per (N,m), same unit draws for plain/cube. Per-phase acceptance H and omitted tail T each get **empirical Bernstein variance-sensitive** two-sided error intervals with preregistered 99%-simultaneous budget across **1344 tests**. The intervals are statistical **under i.i.d. uniform phases**; a seeded CPython pseudorandom generator is NOT a formally verified independent random source, and NumPy/Numba trig computations are not directed-rounded formal proof. Do not call this deterministic full-outcome factoring correctness or quantum hardware measurement.

Stage success probability bounds propagate monotonically into expected abstract logical CCX per attempt and successful factor-producing staged session with hypothetical independent restarts. Cube/plain ratio gets `cube_CCX_per_factor_low/plain_CCX_per_factor_high` to `cube_high/plain_low`; a positive model classification needs upper end <1. If a public factor-producing CF certificate set is EMPTY, factor success exactly zero under this specific CF rule and per-factor cost undefined. This prevents interpreting an order reduction alone as quantum factor extraction.

## ALL EIGHT independent frozen holdout results (no discarded negatives)

Numbers represent **cube / original base expected ideal-QPE abstract logical CCX per factor-producing success**, bounded under stated 99% statistical model and analytic omitted-tail. A ratio <1 is a model improvement only.

| Group | N | Public base a | Validation only order a→a³ | Full-outcome/tail ratio confidence interval | Outcome |
|---|---:|---:|---:|---|---|
| **PRIMARY trigger** | **2620559** | 31 | 1294452→431484 | **[0.788770,0.914991]** | model cube win |
| **PRIMARY trigger** | **2622779** | 2 | 621180→207060 | **[0.781293,0.915851]** | model cube win |
| **PRIMARY trigger** | **2489897** | 11 | 414286→414286 | UNDEFINED (0/0 valid public CF denominators) | factor-incapable, retained |
| **PRIMARY trigger** | **3511889** | 23 | 116622→38874 | **[0.805697,0.852538]** | model cube win |
| Control | 2322043 | 3 | 94500→31500 | **[0.805949,0.853348]** | model cube win |
| Control | 2207089 | 5 | 1093178→1093178 | UNDEFINED, 0/0 public certificates | factor-incapable |
| Control | 2556181 | 11 | 1350→450 | UNDEFINED, 0/0 public certificates | factor-incapable despite shorter order |
| Control | 3202981 | 2 | 644→644 | UNDEFINED, 0/0 public certificates | factor-incapable |

**Frozen primary trigger gate: PASSED** for this specific independent public-B31-survivor ideal-QPE model. At least 3 of 4 trigger cases are both-factor-capable (exactly 3); cube retains factor-production *coverage* on all four (3/4 vs 3/4); all three eligible cases have bounded cube/plain ratio entirely below one (3 model cube wins/4 frozen primary N). The fourth was not discarded, and cannot be assigned a finite model cost. The independent control shows 1 model win, 3 factor-incapable: significantly weaker factor-producing coverage than trigger in this tiny sample. **This is the first genuinely disjoint frozen N22 trial of the improved high-precision model, rather than a rerun on previously inspected keys.**

## What this proves and doesn't

**Wins to preserve:**
1. All 8 selected completely new from previous 16 public N; public-only manifest freeze precedes model.
2. Exact low-stage full-outcome probability plus high-stage analytic missed-bin and independent sampled-eigenphase confidence boundaries applied without after-the-fact method change.
3. Proper strict public factor-production check and complete zero-success rows, all 25 public classical factorizations audited, two independent original JSON receipts preserved.
4. Within the frozen new PRIMARY trigger sample, **three independently selected cases show favorable bounded ideal-model logical CCX per successful session**, which satisfies the precommitted *model criterion*. This improves evidence for a conditional mechanism beyond prior same-sample numerical precision audits.

**Critical limitations:**
- **All 25** semiprimes trivially classically factored. No practical factoring workload left for any QPU. Certificate computation itself is publicly factor-producing and expensive and cannot be assumed free.
- 8 keys is underpowered for generalized new public policy claims; FOUR of EIGHT are factor-incapable despite sometimes shorter orders. The model's acceptance criterion is restrictive, and success coverage is a separate limiting factor.
- Bounds are conditional ideal statistical intervals, with phase pseudorandomness and non-directed-floating assumptions, and generic clean-ancilla **abstract logical CCX**, not physical fault-tolerant quantum runtime, noise, measurement errors or deployment.
- A known algebraic identity explains order effects; no new theorem, RSA2048 attack, generic public exponent-selector advantage, or real experimental hardware speedup.

**Independent recycled-width checkpoint:** 22-bit clean-ancilla modular arithmetic coherent workspace =69, textbook wide phase cap =44, **113** simultaneous logical qubits wide vs **70** iterative phase-recycled peak (**38.05%** lower). This is an independent model-width result, **not** caused by cubing and not QPU physical qubit count.

## Cross-project reverse-SynthID source review is separately scoped

At user's request inspected Alosh Denny's [reverse-SynthID](https://github.com/aloshdenny/reverse-SynthID). Main transferable idea is *multi-reference spectral phase-consensus as a reproducibility/noise control*, not a new factorization or quantum algorithm. Detailed [attributed transfer review](REVERSE_SYNTHID_TRANSFER_AUDIT.md) records exact code areas, source limitations and restrictive research/non-commercial license. **No third-party watermark bypass code or spectral carrier algorithm was introduced into the frozen Dark Star primary**, preserving its independence. Any QPE-residual coherence pilot requires new preregistration, null controls and independent tests; never count a circular phase peak as a proper factor-producing GCD.

## Next step

For stronger inference, freeze a **larger independent public population** with realistic classical factoring benchmark and implement a public-factor-capable success filter whose overhead is included in the **classical** budget; do not select based on secret order/quantum outcomes. Separately preregister a *synthetic-null and permutation* cross-reference coherence diagnostics pilot inspired by reverse-SynthID, attributing Alosh Denny and not importing restricted third-party code. Neither prospective pilot should be reinterpreted as a quantum speedup without new physics/hardware evidence.
