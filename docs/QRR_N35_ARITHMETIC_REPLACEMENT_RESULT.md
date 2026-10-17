# VERIFIED — N35 reversible modular arithmetic identity-pruning compiler test: ~50% cube reduction, but 0.86–1.73 MILLION CZ and physical feasibility FAILS

**Lead / original research program:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-16 Pacific (CI returned UTC 2026-10-17). **NO QPU jobs, NO free or paid runtime consumed, NO actual hardware measurements in this test.**

## Historical win, negative evidence and preregistration

[Previous frozen N35 full-register native transpiler test](QRR_N35_PUBLIC_CUBE_NATIVE_FOUR_BIT_RESULT.md) established a large, *compiler-only* reduction with public base `2→8`, validation order `12→4`, while ALL four full-permutation circuits failed the real-QPU heuristic of native `CZ<=800` and `depth<=2000`. Recycled compiled CZ `8455→3325`, native depth `17108→6595`; wide CZ `7946→3081`, depth `17193→6616`. No QPU was used there. The prior REAL IBM Fez N=15 Open Plan QPU factor-recovery milestone stays valid and separate: N15 has no cubic order reduction.

The next objective was to REPLACE the expensive full-residue truth-table permutation synthesizer with actual n-bit reversible modular arithmetic, not an order-specific 12-state orbital shortcut. This experiment preregistered [`QRR_N35_ARITHMETIC_REPLACEMENT_PREREG.md`](QRR_N35_ARITHMETIC_REPLACEMENT_PREREG.md), commit `fad3b278da40d7dd12c6e06fcae201eb6380e72a`, BEFORE seeing the new target compiler outcomes. N35, public base2 vs cube8, both recycled and wide, phase resolution 4, fixed seed8776 and optimization1, IBM Fez native target from Qiskit 2.5.2+runtime0.47, no sample selection. All four compilation arms retained whether favorable or not. The parent baseline permutation results remain unmodified. `N=35` is trivially solved by classical trial division; not a useful quantum factoring workload.

## Actual code and strict public arithmetic semantics

[Experimental source](../hardware/qrr_n35_public_modarith_identity_pruned_preflight.py) wraps the preexisting, general-form [`hardware/generic_modarith_shor.py`](../hardware/generic_modarith_shor.py). This **does not use an order-encoded compiled orbit or 64-state full-permutation truth table** to implement the native circuit. It constructs controlled multiplication by `m=a^(2^k) mod35` as shift-and-controlled-modular-add to a clean accumulator; controlled swap; inverse multiplier uncomputes original work into `|0>`; invalid states y≥35 unchanged, all classical helper flags cleaned. The existing [explicit Qiskit lowering compatibility layer](../hardware/ibm_shor35_generic_modarith_preflight_explicit.py) implements controlled IntegerComparator and DraperQFTAdder arithmetic eagerly; this is intended to avoid Qiskit high-level controlled-annotated-operation qubit-width mismatch, but is **extremely expensive in the native basis**.

Exactly ONE frozen public arithmetic improvement is added: skip the controlled modular multiplier circuit entirely when `m==1 modulo N`, a legally computable public matrix identity. This avoids identity-path exponential synthesis without using order labels. Power schedule for four QPE bits: base2 `[2,4,16,11]` has **zero** identity rounds; public cube8 `[8,29,1,1]` has **two** identity rounds. True validation orders are 12→4, but orders do NOT decide circuit construction; there is no 12-state orbit injection. Original classical `semantic_self_test` exhaustively checks modular-add and controlled full-residue mod-mul mathematical reference behavior for each base and bit. **Limit:** classical semantics is NOT itself a formal gate-level proof of the resulting 26/29-qubit synthesized unitary; further gate-level validation would be required before genuine hardware claims.

## Provenance and independent preserved source outputs

[GitHub Actions zero-QPU four-job compilation **38996345928**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996345928): **4/4 successful** fixed-paired runs, no Sampler constructor, no QPU calls; every result was compiled against live-read IBM Fez backend target **only**. Each fixed job held to a 360-second compiler timeout and 12-minute GitHub job cap, seed8776, optimization1. [Independent original-receipt artifact auditing and preservation **38996529069**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/38996529069): **SUCCESS**, downloaded all four original source-run JSONs without re-running compilation, confirmed same public powers, strict source semantics and resource fields, verified primary frozen device-gate failures, compared against prior full-permutation original receipts and committed the exact original JSONs:

- [recycled base2 original](../results/ibm_shor35_modarith_identity_pruned/qrr_n35_public_modarith_recycled_plain.json)
- [recycled cube8 original](../results/ibm_shor35_modarith_identity_pruned/qrr_n35_public_modarith_recycled_cube.json)
- [wide base2 original](../results/ibm_shor35_modarith_identity_pruned/qrr_n35_public_modarith_wide_plain.json)
- [wide cube8 original](../results/ibm_shor35_modarith_identity_pruned/qrr_n35_public_modarith_wide_cube.json).

All files retain full transpiled native `sx`, `rz`, `cz`, measurement, conditional, and reset counts, compilation time, the selected public multipliers and the exact logical widths.

## All four original native target results

| N35 four-bit compiler / method | Original base a=2, r=12 | Public cube a³=8, r=4 | Cube change |
|---|---:|---:|---:|
| **Reversible arithmetic / recycled native CZ** | **1,732,072** | **859,632** | **−50.37%** |
| Reversible arithmetic / recycled native depth | 4,766,896 | 2,370,305 | −50.28% |
| Reversible arithmetic / wide native CZ | **1,733,136** | **860,151** | **−50.37%** |
| Reversible arithmetic / wide native depth | 4,763,959 | 2,372,924 | −50.19% |
| Arithmetic logical circuit qubits | recycled **26** / wide **29** | recycled **26** / wide **29** | zero change within architecture |
| Identity controlled-modular-power rounds out of 4 | **0** | **2** | public identity pruning |

The new arithmetic construction did achieve a ~2× *within-compiler* cost reduction for the cubic base, because two expensive controlled multiplication rounds become genuine identity. However, its overall ISAs are radically larger than the previous 64-state truth-table direct-transposition synthesizer:

| Public base 8 / same target, different synthesis and optimization levels | Previous full-permutation method | New general-structured arithmetic |
|---|---:|---:|
| Recycled native CZ | **3,325** | **859,632** |
| Recycled native depth | **6,595** | **2,370,305** |
| Wide native CZ | **3,081** | **860,151** |
| Wide native depth | **6,616** | **2,372,924** |

The cross-method table is **descriptive**, not a controlled same-optimization-level kernel benchmark (previous transpiler level2, new level1). Nonetheless, the ≈258–279× native CZ difference is far too large to ignore. In these experiments, using more abstractly general/polynomial arithmetic does NOT mean more efficient compiled operations at 6-bit work width; expensive nested controlled comparators and multi-controlled QFT adders dominate Qiskit native synthesis. **Do not claim general reversible-arithmetic was improved, or that this enables larger practical factoring.**

## Frozen hardware success criteria and negative conclusion

Primary gate preregistered ALL FOUR arm native CZ ≤800 and compiled depth ≤2000, cubic < plain CZ and ≤ depth, semantic correctness and compile success. We obtained all four compile successes and cube less expensive in both architectures, **but ZERO of four pass the native CZ/depth device gate**. The best cube arm still requires **859,632 CZ**, over **1,074×** the limit, and **2,370,305 depth**, over **1,185×** the depth limit. Baselines are even larger. **PRIMARY HARDWARE FEASIBILITY FAILS.** Real-QPU submission remained **zero**. This is a valid, clearly documented negative ablation, not grounds for relaxing the gate or switching to oracle/order-precomputed toy circuits without transparent labeling.

The earlier REAL IBM N15 result (factors3/5 recovered 49/64 recycled vs38/64 wide) remains independently true but does not test Dark Star cube. The earlier N35 public-cube target-compiler ~61% smaller-cost effect also remains true in its own synthesis family, but both cannot be run with realistic frozen hardware resource limits. No new theorem, real quantum device improvement, general exponent-selection rule, RSA2048 cryptanalysis, or real-world factoring speedup.

## Next engineering direction

**Do not repeat this QFT-adder-with-nested-controls kernel as-is.** Design and preregister a purpose-built n-bit **Toffoli/ripple-carry constant modular adder** with explicit reusable clean carry/compare ancillas, avoid generic recursive `.control` wrappers around multi-qubit QFTAdder and IntegerComparator, exploit public constant sparsity, and prove the resulting arithmetic subroutine against small exhaustive reversible-basis tests. Start with a single controlled modular multiplier (QPE phase bits1) to establish correct fully uncomputed helper ancillas and native resource scaling. Only expand to FOUR matched 4-bit plain/cube variants if one-bit native cost and depth meet a frozen stage feasibility rule. Compare one fixed transpiler seed and both arm resource costs, and still require a real Open-Plan-only hardware gate before any QPU submission.

There is currently **no reason to spend another minute of the user's limited free IBM runtime** on this unfit construction.
