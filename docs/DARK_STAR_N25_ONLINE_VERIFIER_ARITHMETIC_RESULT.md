# Dark Star N25: independently frozen online-CF/structural-arithmetic cost test — no bounded win (VERIFIED)

**Research direction / lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-25. **Conclusion: preregistered model-improvement gate FAILS**; still no demonstrated quantum hardware speedup. **ZERO IBM QPU jobs or IBM free/paid Runtime.**

## Provenance and necessary caveats

- [Protocol frozen before outcome scoring](DARK_STAR_N25_ONLINE_VERIFIER_ARITHMETIC_PREREG.md).
- [Original independently SHA-frozen 25-bit public manifest](../results/dark_star_ptp/dark_star_n25_online_public_manifest.json), `selected_sha256=66b3cdb1ac58c1dffac3838c4113ffddb6fa9e6a1cc863890d55d997dc97fae7`. Eight distinct 25-bit semiprimes, four public `N mod 3 == 1` and four `N mod 3 == 2`, selected after public B31 screening but **before** obtaining validation-only prime factors/orders, phase outcomes or modeled costs. Manifest freeze [Actions run 40247140146](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40247140146), SUCCESS. Of ten ranked candidate screens, two were eliminated by B31 public factors.
- The first [scoring run 40247465462](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40247465462) FAILED because the initial sampler duplicated QPE outcome bins for small phase widths, spuriously summing head probability >1; no scientific receipts were scored as valid. A correction made all considered outcome bins unique modulo Q. The second [run 40247618408](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40247618408) FAILED when serializing calculated rows due to a public-base-versus-model-arm field collision, again **not** a scientific pass.
- [Run 40247709920](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40247709920) produced **eight successful original independent CPU science jobs** but its independent merge failed because the merging code still referenced a scalar public-base field as a model result. The [recovery-only run 40247830765](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40247830765) then SUCCESSFULLY downloaded, independently audited and committed the **unchanged original eight science shard artifacts** plus the merged receipt. The science was **not re-run** to rescue archive failures.
- [Complete original eight-row merged JSON and all individual original receipts](../results/dark_star_ptp/dark_star_n25_online_model_all_8.json). The separately triggered retries are not extra independent populations; no favorable re-selection occurred.

## Method boundaries
The public-only N/a sample is fresh relative to the known 24-bit results. The new model replaces a prior huge O(N) classical list of all factor-producing continued-fraction denominators with a **genuinely on-demand public CF/GCD check performed on sampled QPE measurement outcomes**. Public N and base, measured y, and phase bits m are the only verifier inputs. Simulated ideal QPE phases depend on exact validation-only multiplicative orders derived after population freezing. The verifier was cross-checked against the previous independent public factor extractor on small cases.

Staged model: `m=4,6,...,50`, 4 nominal independent model shots per stage; 4096 seeded pseudorandom phase/outcome draws per stage and arm; 65 centered outcome bins where Q>65, otherwise every distinct bin. A tail bracket and empirical Bernstein interval account for omitted outcomes and sampling uncertainty, with union family 1536 at overall alpha=.01. Numerical probability intervals are **not formal certified machine arithmetic**; using fixed-seed pseudorandom samples does not guarantee physical IID randomness.

The arithmetic cost uses the repository's explicit **source-level clean-MCX modular-multiplication decomposition** (CCX/CX/controlled-SWAP) at each phase stage, NOT transpiled native CZ gates, physical gate fidelity/latency, true fault-tolerant cost, or QPU runtime. On-demand CF-verifier modular exponentiation and GCD calls are separately reported as **classical evaluation work**, not free quantum operations; the simulator may validate using known factors, but the public verifier does not.

## Results for *all* eight frozen N/a

| Frozen public N | a | Exact validation order a -> a^3 | B47/rho64/trial97 classically solved? | Nominal bounded model cube/plain CCX per success ratio | Model classification |
|---:|---:|---:|:---:|---|---|
| 20,508,127 | 3 | 854,124 -> 284,708 | Yes, rho | [0.3977, 1.8257] | Inconclusive |
| 20,088,463 | 29 | 2,007,928 -> 2,007,928 | Yes, B47 | [0.4427, 2.3086] | Inconclusive |
| 28,811,323 | 31 | 7,200,100 -> 7,200,100 | Yes, rho | [0.4061, 2.4969] | Inconclusive |
| 32,295,103 | 17 | 1,008,860 -> 1,008,860 | **No, fixed budget survivor** | [0.4566, 2.2524] | Inconclusive |
| 24,467,873 | 3 | 12,228,930 -> 4,076,310 | Yes, B47 | [0.3061, 2.4282] | Inconclusive |
| 29,256,449 | 5 | 114,240 -> 38,080 | Yes, rho | Undefined (lower success bound zero) | Factor-incapable or uncertified |
| 28,064,303 | 13 | 1,753,308 -> 584,436 | Yes, rho | [0.3969, 2.0110] | Inconclusive |
| 28,787,333 | 11 | 4,796,098 -> 4,796,098 | Yes, B47 | Undefined (lower success bound zero) | Factor-incapable or uncertified |

**Preregistered complete-population summary:** 0 bounded wins (ratio upper<1), 0 bounded losses (ratio lower>1), 6 inconclusive, 2 cases with zero lower success bounds and therefore undefined per-success cost ratios. Both arms have a positive **lower bound** on modeled eventual factor-success probability in 6/8 cases. The *model pass gate fails* (needed >=3/8 bounded wins and maintained coverage); the numerical intervals are too broad to conclude any gain or regression. In the two undefined cases the upper factor-success bound was positive, so **do not** claim mathematical factoring impossibility.

**Classical-first accounting:** 7/8 originally selected B31 survivors were subsequently factored by the explicitly capped public B47/rho64/small-prime process. Exactly one N=32,295,103 survived that fixed public budget, which means only a limited classical *budget* failed, not that it is cryptographically hard; the experimental 25-bit semiprime remains classically trivial with more work. This independent remaining-work gate passed 1/8 under the protocol, but no factoring speed advantage was established. The online verifier itself logged hundreds of thousands of modular exponentiations on this evaluation; that classical workload must be counted in any true end-to-end comparison.

## Interpretation and next experiment
The N24 reused-population follow-up had 4/16 modeled cube wins, 8 inconclusive and 4 uncertified, but 16/16 classically factored with a huge public certificate scan; it remains a valid **conditional ideal-model finding**, not a practical win. This fresh N25 test does **not** replicate bounded wins when using an on-demand public verifier and wider uncertainty intervals. **The correct inference is no proven improvement at this stage, not a proven absence of any possible cube effect.** The universal odd-cube half-order witness identity remains intact.

Next work should first address confidence-interval width and efficient online verifier accounting, with a preregistered independent population and a principled classical work budget, and separately test actual compiler-native modular arithmetic where hardware feasibility allows. Do not route to paid IBM runtime or equate modeled CCX with device performance.
