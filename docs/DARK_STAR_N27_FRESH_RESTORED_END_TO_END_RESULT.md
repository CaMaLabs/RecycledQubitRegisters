# Dark Star unified original pruning: fresh N27 independent end-to-end holdout

**Research lead:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-28. **Scientific conclusion: restored original PTP pruning validated in a new population; no practical end-to-end speedup or need for quantum work was demonstrated.** All quantum operations reported below are CPU-only *ideal* QPE counterfactuals; IBM QPU jobs and IBM paid/free Runtime: **ZERO**.

## Prospective selection / original verified evidence

- [Preregistered independent-population and separately preregistered public-identity experiment](DARK_STAR_N27_RESTORED_PLUS_IDENTITY_PRUNING_PREREG.md), committed before scoring.
- [Original new public 27-bit N/base manifest](../results/dark_star_unified/unified_n27_restored_public_manifest.json), separately frozen in successful GitHub Actions [run **40811162116**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811162116). Public SHA256 over the 12 selected rows **`12f169a7edabe5d548dba4c8bd07d348a2bd174378ad2faf934dcfe8b5828b10`**. Selected 12 distinct squarefree 27-bit synthetic semiprimes, six N mod3=1 and six N mod3=2, by public-only SHA ranking among **292,399** constructed N. The construction primes were not used to rank cases, select base or choose any public operation, and neither orders nor classical/QPE outcomes were inspected before the manifest was archived.
- [Whole-path scoring code](../integrations/darkstar_hybrid/darkstar_n27_restored_holdout.py) and successful [original scoring/verification GitHub Actions **40811563655**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/40811563655). Full raw `results/dark_star_unified/unified_n27_restored_original_00.json` through `_11.json` preserve all public filter stages, five-run timings, standalone classical baseline receipts and 3-seed plain/cubic model traces.
- [Small 12-case merged summary](../results/dark_star_unified/unified_n27_restored_all_12_summary.json). No original N25/N26 receipts were changed.

## Actual complete factorization outcomes

**All 12 of 12 N27 cases were correctly factored by the newly restored public classical-first pipeline**, before any hypothetical quantum stage needed execution. Exactly **zero** of twelve reached the conditional ideal QPE fallback under this fixed predeclared budget.

| Actual public algorithm stage finding the factors | Cases |
|---|---:|
| PTP-Fermat M15015 (old low-cap method) | 4 |
| PTP-Fermat M105 | 4 |
| Pollard p−1 B31 | 1 |
| Fixed-seed bounded Floyd rho64 | 3 |
| Restored M255255 late fallback alone | **0** |
| **Total classically solved within fixed public budget** | **12** |
| Full conventional wheel210 factor successes | 12 |
| Full PTP LFK kernel search factor successes | 12 |

The zero M255255 *final-stage* count is not proof the new method is wrong or unused: the old public stages were already sufficient in this particular randomly SHA-frozen population, and the integrated order stops on the first verified classical factor. The previous N26 replay showed a genuine new late-M255255 recovery; that older sample is separate and remains classified as post-hoc restoration.

**Fairer wall-time controls:** On the same GitHub runner, each method was executed five times, with its original factor validation and the entire public preflight sequence included. The full classical-first pipeline was faster than complete conventional wheel210 factoring in **4/12**, and faster than complete PTP LFK/kernel factoring in **4/12**. These timings are noisy Python microbenchmarks and the setup/inverse residue work can dominate, but under no fair reading do they constitute a majority runtime win. An abstract quantum CCX is not interchangeable with Python divisions or microseconds; **no practical end-to-end advantage** is established.

## Separately retained ideal-QPE mechanism probes

Every N/base also underwent **three fixed pseudorandom-seed** (20261028, 20262037, 20263046) *counterfactual* plain (`L1`) and unconditional cubed (`L3`) simulated ideal-QPE paths, with public measured-y continued fraction + pow/GCD verifier, four shots per stage, centered 65-bin head plus explicit unsuccessful unmodeled tail, and full generic clean-MCX source CCX ledgers. A public conditional L3-if-N%3==2 selector merely **references** one of these two original traces; it does not get a third independent sample. No private p/q/order enters the public factor decoder, stage-cost construction or public base selector.

| Original fixed arm over all 12 cases | Plain L1 | Cubic L3 |
|---|---:|---:|
| Ideal simulated sessions | 36 | 36 |
| Simulated successful factor recoveries | **24/36** | **24/36** |
| Total ORIGINAL modeled source CCX | 99,925,111,990 | 94,622,162,391 |
| Total after safely eliding publicly-known identity U's | **unchanged** | **unchanged** |
| Descriptive source CCX reduction for unconditional cube | — | **5.31%** |

Four particular original N27 cases generated 0/3 factor-producing strict even-order/GCD recoveries in both arms (cases N=76,376,821; 105,065,509; 123,535,619; 107,941,919). Do **NOT** report a finite per-success CCX for any one of these. The global 24/36 numerator/denominator still includes all three unsuccessful sessions from each. **Three seeds is a descriptive diagnostic, not certified confidence**, and any apparent cube saving is inside an expensive ideal model that no actual quantum stage was needed to execute.

The independently verified public-only **identity-U optimization** gave **zero source-CCX savings on all frozen N27 bases**, both plain and cubic, at their tested phase widths. It should not be credited as a hidden extra saving within the 5.31% difference.

## Conclusion and next gate

Original PTP prime-table, safe Fermat midpoint pruning, and public-classical-first routing are back in an executable pipeline and now tested on a *new* SHA-frozen population. But all these small semiprimes are easy for conventional factoring, the full pipeline fails the runtime majority test against both competent classical comparators, and every nominal 'quantum saving' was **counterfactual**. It is scientifically misleading to describe this as a quantum factoring breakthrough or hardware result.

The next improvement should be a **public-only cost-based classical router** rather than a fixed long sequence of failed preprocessing stages: use cheap features of N (e.g. size and inexpensive midpoint-derived QR density) to estimate when QR pruning beats wheel/LPK and run the cheapest defensible method first. Such a router must be preregistered on a wholly NEW cohort and benchmarked against standalone wheel/LPK including setup. Separately evaluate native compiled circuit resources for identity-U where applicable, while respecting the earlier N35 32→23 idle-scratch native robustness failure. No paid runtime.
