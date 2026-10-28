# Fresh N26 unified Dark Star: end-to-end original PTP/classical + odd powers + recycled ideal-QPE comparison

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-28. **Primary scientific conclusion: practical end-to-end advantage NOT DEMONSTRATED.** The combined algorithm is now verified on a **genuinely fresh 12-row, 26-bit** synthetic semiprime population, all selected before any outcome inspection. **CPU GitHub Actions only; zero real IBM QPU jobs, zero paid or free IBM Runtime.**

## Original public-only freeze before model results

- [Predeclared frozen experimental protocol](DARK_STAR_UNIFIED_N26_FRESH_POPULATION_PREREG.md), commit `1afeaa7b6d402650e4c12ceb750c425a3d0eb5af`.
- [Original 12 input manifest](../results/dark_star_unified/unified_n26_public_manifest.json), frozen in its *own earlier* [successful GitHub Actions run **40659871113**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40659871113), before the scoring script/workflow was launched. SHA256 of canonical public selected rows: **`0c25e448b646a5ade7d919ca78597c8c2883fd8fd450181dd4504c18252fb939`**.
- Original frame: **185,661** public-N synthetic-semiprime candidates, 92,755 with N mod3=1 and 92,906 with N mod3=2. Hash-ranked six from each group, twelve total, 26-bit N in [2^25,2^26). Prime factors were not included in the manifest, and true order/simulation outcomes did not determine the selection.
- [Full new 12-case CPU workflow **40660172585**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40660172585) **SUCCESS:** all **12/12 independent scoring jobs passed** and strict merge verified each original N/base, all seven powers, eight precommitted seeds, full classical-operation/gate counters, original receipt SHA, and zero-QPU flags. Each unchanged original JSON archived in `results/dark_star_unified/unified_n26_original_00.json` through `_11.json`.
- [Small merged summary](../results/dark_star_unified/unified_n26_all_12_summary.json). [Scoring and strict merge code](../integrations/darkstar_hybrid/darkstar_unified_n26_holdout.py). [Original complete integrated algorithm](../integrations/darkstar_hybrid/darkstar_unified.py).

## Real public classical-first experiment (the **actual algorithm**)

**11/12 cases were completely factored by the bounded public-first pipeline**; one more (N=49,273,331) survived that **specific fixed prefilter** and entered simulated ideal-QPE fallback. All 12 were readily factored by standalone conventional wheel-210 trial **and** original PTP/LFK factor-pair kernel search. Thus **there is no demonstrated end-to-end practical factoring advantage**; do not treat the limited public-filter survivor as cryptographically hard.

| Completed public-first method | Cases |
|---|---:|
| PTP Fermat midpoint, wheel=15015 | 3 |
| PTP Fermat midpoint, wheel=105 | 3 |
| Floyd rho64 | 2 |
| Pollard p-1 B31 | 2 |
| Ordinary Fermat | 1 |
| **Fixed classical budget exhausted** | **1** |
| **Standalone conventional wheel-210 success** | **12/12** |
| **Standalone PTP LFK kernel success** | **12/12** |

The public classical controls are crucial: PTP midpoint residue filtering can save square tests *within that stage*, but preceding failed searches, precomputation, and alternative full classical methods must also be counted. Kernel mirror equivalence is NEVER used to delete exact factor candidates; factor roots are checked only after genuine recovery. Trial/wheel division counts and abstract quantum CCX are **not comparable physical cost units**.

### The single fixed-classical-budget survivor: N=49,273,331

Frozen base **a=17**, N%3=2 so the *predeclared public policy* chooses **a³ modN=4913**. The original SHA-frozen case was not replaced or selected using its hidden order. Fixed B31/Fermat/midpoint/rho/trial budget exhausted. The simulator-only post-freeze factorization labels reveal 49,273,331=4,703×10,477, validation orders **24,629,076 → 8,209,692**. The independently controlled ideal-QPE plus **PUBLIC CF/GCD verifier** recovered the exact factors in the first-seed L3 path after 87 shots; its public fixed-exponent fallback correctly stopped there. Across all eight predeclared seeds, both L1 and L3 factor recovery succeeded 8/8 *in this ideal, simulated experiment*, with total counterfactual source CCX:

| Single case N=49,273,331 | Original plain | Public cubic |
|---|---:|---:|
| Eight ideal-QPE recoveries | 8/8 | 8/8 |
| Total source-level CCX, including all attempted sessions | 18,605,554,336 | 15,149,136,842 |
| Mean source-level CCX per recovered factor in these eight runs | 2,325,694,292 | 1,893,642,105 |
| Modeled peak logical width (wide phase, max across seeds) | 133 | 127 |
| Modeled peak logical width with one phase qubit recycled | 82 | 82 |

These are **sampled ideal-model source-operation counts**, not measured QPU runs, performance guarantees, an attack on an unknown semiprime, or a meaningful win versus conventional wheel-210 (1,079 divisions) or PTP kernel LFK (968 integer search steps) that both factor this toy N classically.

## Explicit counterfactual quantum mechanism analysis (NOT actual quantum work)

To avoid a single favorable seed, each original public N/a is tested across the same **eight fixed pseudorandom seeds**, seven fixed precommitted exponents L∈{1,3,5,7,105,1155,15015}, four shots at each staged phase precision up to m=52, public on-demand CF+pow+GCD factor validation, source clean-MCX CCX/CX/CSWAP costs, and wide vs one-phase recycled peak logical width. QPE probabilities are evaluated for up to 65 centered outcome bins and any omitted tails are explicitly counted as unsuccessful model events, **not renormalized into winning bins**. No statistical confidence guarantee is inferred from eight seeds. There is no compiled native CZ, physical qubit routing, QPU error model, or fault-tolerant benchmark.

| Fixed precommitted arm | Public factor shortcuts on whole cohort | Ideal-model successful factor sessions | Total attempted-session source CCX |
|---|---:|---:|---:|
| Plain L1 | 0 | 88/96 | 160,257,888,003 |
| Unconditional cubic L3 | 0 | 88/96 | **142,998,156,168** |
| L5 | 0 | 88/96 | 156,040,908,596 |
| L7 | 0 | 88/96 | 151,629,757,981 |
| L105 | 0 | 88/96 | 125,249,934,336 |
| L1155 | 1 | 80/88 **remaining** quantum-model sessions | 113,271,495,839 **for 88 remaining** |
| L15015 | 1 | 80/88 **remaining** quantum-model sessions | 113,363,016,736 **for 88 remaining** |

**Do not compare the L1155/L15015 totals directly to L1** without separately pricing their public classical factor shortcuts and their missing eight model sessions; they have different denominators.

Plain vs unconditional L3 has **equal empirical factor recoveries** and 10.77% less *aggregate ideal source CCX* in these specific sessions; the simple public PTP-conditioned `L3 if N%3=2 else L1` arm has 150,270,511,956 source CCX (6.23% less than plain, but **worse than always L3** in this sample). Of the **11 factor-capable model cases**, the unconditional cube is descriptively less costly in 10, more costly in one; one further fixed-base case was unresolved in all eight sessions and must not be assigned any finite cost-per-success ratio. These are **single-cohort finite-seed observations, not a bounded/replicated model win** and not a predictor theorem: actual order reduction (in later validation-only labels) occurred 10/12 times while the simple residue condition triggered in only six.

### Per-case original observations (no result selection)

| SHA-frozen N | Public base | Classical-first outcome | Validation order under cube | L3 versus L1 total source CCX ratio over 8 seeds |
|---:|---:|---|---|---:|
| 46,105,429 | 5 | PTP midpoint15015 | Unchanged | 1.0159 |
| 51,283,357 | 11 | PTP midpoint105 | ÷3 | 0.9218 |
| 61,588,231 | 3 | Floyd rho64 | ÷3 | 0.8451 |
| 66,042,979 | 7 | Pollard B31 | ÷3 | 0.9343 |
| 60,072,931 | 7 | Pollard B31 | ÷3 | 0.8284 |
| 41,484,283 | 7 | PTP midpoint15015 | ÷3 | 0.8919 |
| 60,030,401 | 17 | PTP midpoint15015 | ÷3 | 0.7359 |
| 49,069,961 | 13 | Ordinary Fermat | ÷3 | 0.8004 |
| 61,435,931 | 7 | Floyd rho64 | ÷3 | 0.8635 |
| **49,273,331** | **17** | **Fixed budget exhausted** | **÷3** | **0.8142** |
| 43,863,401 | 3 | PTP midpoint105 | ÷3 | 0.8592 |
| 43,565,573 | 23 | PTP midpoint105 | Unchanged | **Undefined per-factor** (neither arm produced a factor in eight runs) |

For the final row the *attempted-work* L3/L1 CCX ratio was approximately 1.0108; with **zero** modeled successful factors either arm, a *per successful factor* ratio is **undefined**. The previous N25 exact theorem and half-order witness cautions remain unchanged.

## Scientific conclusion

We successfully restored and *executed all compatible original PTP prime-table/kernel/classical factoring techniques* alongside the full public odd-power/adaptive recycled QPE approach on newly frozen 26-bit cases. The integrated public/ideal boundary works; in the single fixed-filter survivor it recovers factors through only public output verification from a synthetic QPE source. But **all 12 are trivially factorable with conventional classical methods**, and 11/12 never need the quantum step under the specified preflight. The nominal cube-source-cost improvements are meaningful **as diagnostic ideal model observations**, not end-to-end factoring advantage.

### Next logical gate

1. Tighten public classical-work baselines and total cost units, and compare *actual end-to-end time/operation* under fixed fair budgets rather than a hand-picked classical limit.
2. Preserve a truly fresh separate 28-bit or larger public cohort **before examining orders/outcomes**, allow genuinely factor-capable and factor-incapable strata, and use complete-tail QPE or explicit worst-case tail bounds plus more independent seeds (or analytic proof) before any statistical advantage language.
3. For near-term hardware-native work, establish one actual valid controlled-modmul circuit and native routed CZ/depth/measurement-reset overhead (CPU-only preflight first). Do not spend IBM Runtime on 26-bit full factoring circuits.
4. Keep `L1155`/smooth-exponent classical shortcuts counted as **classical Pollard-like effects**, not independent quantum improvements.
