# VERIFIED — N35 active-only vs enable-only RCCX latch family ablation: active-only passes BOTH bases, enable-only cubic-depth gate FAILS. ZERO QPU.

**Research lead / originating program:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-17. **Nature of all cost measurements:** IBM Fez authenticated hardware **TARGET compilation on a CPU**, not executing quantum circuits on a physical device. **ZERO QPU shots, jobs, free Open Plan QPU minutes or paid Runtime.** This is only ONE full-six-bit-residue controlled modular multiplication with public N35 bases2 and8, not a complete multi-phase-bit Shor factoring circuit, real N35 factor-recovery demonstration, or RSA-scale cryptanalytic advantage.

## History, preregistration and immutable baseline

The independently preserved [phase-aware temporary comparator carry RCCX source](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) is our original common-gate comparator baseline: **base2 CZ9,263/depth21,772; cube8 CZ9,426/depth21,933**, 32 source logical qubits (including all 25 initially-zero/returned-clean helpers). Source gate counts from original receipts: base2 {CX1033,RCCX596,X28,exact CCX160}; cube8 {CX1077,RCCX616,X28,exact CCX162}. All prior exact quantum-emitted gate comparator/modadd/full-multiplier checks passed, and source original receipt JSON under `results/ibm_shor35_relative_phase_ripple/` has not changed. Fixed `ibm_fez` native **CPU** target, Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, transpiler optimization1, seed8776. Frozen physical N35 preflight **CZ≤800 AND depth≤2000 BOTH bases**, far from satisfied.

The next preregistered [combined cached active+enable latch experiment](QRR_N35_RELATIVE_PHASE_CACHED_LATCH_RESULT.md), commit before scoring `5537b57907162795ead8f64c74d21c3e0cda07ac`, correctly replaced 26 cached CCX with relative-phase RCCX/inverse, preserving exact quantum output phase. It improved base2 CZ9263→**8542**, depth21772→**19819** but cube8 CZ9426→**9328**, depth21933→**22005** (cubic depth became WORSE, joint gate FAIL). Both original receipt JSONs [independently preserved](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074317133); do not hide the negative cubic-depth outcome.

To isolate the source, a **NEW four-arm experiment** was [explicitly preregistered](QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_PREREG.md), original commit `ebbafc19911a073149d30c3728f9bdc70d8f5928`, BEFORE scoring. Exactly four distinct new kernels: `active_only` or `enable_only`, each at public base2 and cube8; all use the same original full-residue, order-blind, clean reversible arithmetic and phase-exact temporary comparator carries. No full 64-state truth-table multipliers, true order injection, hidden factors or precomputed multiplicative orbit. Unchanged original target/seed/compiler; no search across seeds/layouts or quantum execution.

## Frozen different interventions, with actual source proof

New source [`hardware/qrr_n35_relative_phase_latch_families.py`](../hardware/qrr_n35_relative_phase_latch_families.py) constructs original work/acc/control/aux register layout from the prior proven source, with two clean temporary cache latch families:

- **`active_only`:** ONLY the long-lived `active=phase AND valid` compute and exact inverse uncompute are switched from exact CCX to Qiskit `RCCXGate()` and `RCCXGate().inverse()`. All twelve `enable=active AND work[i]` temporary pairs remain exact CCX. Exactly **2** additional RCCX source gates (base2 RCCX598/exact CCX158, cube8 RCCX618/exact CCX160).
- **`enable_only`:** Keep long-lived active pair as exact CCX but switch twelve short-lived forward/inverse-weighted modular-add source enable pairs to RCCX and inverse, **24** additional RCCX source gates (base2 RCCX620/CCX136, cube8 RCCX640/CCX138). Same CX/X source counts as original baseline.
- Prior saved **`neither`** source has no cached RCCX and **`both`** has 26; this study does not rerun or modify either. Remaining semantic controlled-swap output flips, arithmetic public prefix carry, phase-aware comparator ripple, unitary flag and accumulation uncomputation remain untouched.

Each of the four *new* CI jobs checks the **actual Qiskit emitted operator** basis permutation/complex amplitude, not merely the classical truth table. `RCCXGate().inverse()` matrix is checked as Qiskit's actual operator inverse even though gate names may coincide. Exact final complex amplitude must be **+1+0j** with unchanged controls and all clean scratch:

1. **8/8** local cache RCCX→semantic controlled probe→RCCX.inverse cases (all control/probe states), exact phase+1, latch clean, controls unchanged.
2. **42,672/42,672** original public width1..6 comparator actual-emitted-phase cases, every public threshold, both comparisons, control0/1, initial predicate flag0/1, scratch clean.
3. **1,584/1,584** full public modulo35 controlled constant-addition source gate cases across 16 constants and 99 enabled/disabled inputs each, phase+1 and clean ancillas.
4. **128/128** full control×all 6bit work y=0..63 exact complex phase +1 gates with full public `a*y mod35` semantics on valid enabled y, identity on disabled and invalid y, unchanged phase control, all **25 auxiliary source qubits returned zero**. Explicitly asserted that only the intended **2 or24** source CCX→RCCX substitutions actually occurred, with identical 32 application qubits.
5. Only after proofs passed was IBM Fez *TARGET metadata* read for **CPU native transpilation**, Qiskit/Runtime versions frozen, seed8776, opt1. **No Sampler, Estimator or QPU job.**

[Original four-arm GitHub Actions experiment **39074602823**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074602823) **4/4 SUCCESS**, each full source-gate proof+native compiler+original frozen CI audit succeeded.

[Original artifact independent audit/preservation GitHub Actions **39074706319**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074706319) **SUCCESS**: downloaded original source-run artifacts, independently checked all input gate proofs/complex +1 amplitudes, source relative gate distribution, immutable old and combined baseline original JSONs, exact resource costs and separate frozen hardware gate, then committed ORIGINAL unchanged four receipts without recompiling:

- [active-only base2 original receipt](../results/ibm_shor35_phase_latch_family_ablation/qrr_n35_active_only_base2.json)
- [active-only cube8 original receipt](../results/ibm_shor35_phase_latch_family_ablation/qrr_n35_active_only_base8.json)
- [enable-only base2 original receipt](../results/ibm_shor35_phase_latch_family_ablation/qrr_n35_enable_only_base2.json)
- [enable-only cube8 original receipt](../results/ibm_shor35_phase_latch_family_ablation/qrr_n35_enable_only_base8.json)

## Full fixed four-variant comparison — exactly ONE controlled modular multiplier

| Phase-exact N35 variant, IBM Fez CPU ISA compilation | Base2 native CZ | Base2 native depth | Cube8 native CZ | Cube8 native depth |
|---|---:|---:|---:|---:|
| Original comparator RCCX; **neither** cache latch changed | 9,263 | 21,772 | 9,426 | 21,933 |
| **active_only**: just 2 RCCX cached active pair | **9,042** | **21,541** | **9,156** | **21,820** |
| **enable_only**: 24 RCCX cached enable calls | **8,756** | **21,007** | 9,424 | 21,995 |
| **both**: 26 RCCX cached active+enable | 8,542 | 19,819 | 9,328 | 22,005 |

**Active-only frozen two-base engineering PASS:**
- Base2 CZ 9263→**9042** (**−2.39%**); depth 21772→**21541** (**−1.06%**).
- Cube8 CZ 9426→**9156** (**−2.86%**); depth 21933→**21820** (**−0.52%**).
- Both meet strictly lower CZ AND depth than their OWN original best baseline, keep all ideal quantum-phase correctness and 32 logical qubits. This is the **one common phase-correct latch family independently shown to improve both arms in both metrics** under the fixed target/seed.

**Enable-only two-base engineering FAIL:**
- Base2 improves to CZ8756 and depth21007.
- Cube8 decreases native CZ marginally from9426→**9424** but worsens depth21933→**21995**. A source gate count reduction or two-CZ benefit must not be interpreted as a reliable cubic depth benefit.
- The earlier combined both-substituted variant also worsened cube8 depth, consistent with temporary enable latch substitution being linked to the cubic-depth regression **in this fixed compiler ablation**. Interaction/topology/routing or different public arithmetic structures mean this is NOT a proof of general causal or physical hardware fidelity superiority.

**Important trade-off:** The `both` circuit remains the **lowest observed base2** CZ/depth in these fixed comparisons, but `active_only` is the safer shared choice if requiring improvements at both public bases. Comparing circuit instances on the same one-target one-seed transpile is a controlled engineering proxy, not proof of target- or layout-robust performance or a four-round factoring advantage.

**Unchanged real-QPU feasibility FAIL:** Every new one-multiplier arm remains vastly over native **CZ≤800 and depth≤2000**. Best cube8 active-only CZ9156/depth21820 is ~11.45× and ~10.91× these heuristic cutoffs. No full four-phase QPE assembly, no public N35 factoring shots, no quantum hardware test, and no paid/free runtime. N15 actual IBM Open-plan recycling pilot still separate, legitimate and preserved.

## Next objective grounded in the isolated ablation

The next high-value experiment should test whether **public-constant-specific phase-exact controlled adders** or **low-control phase-aware temporary modular correction flags** can reduce the remaining *semantic* exact CCX and native placement cost, with an independent frozen full-gate phase oracle and at least two bases. Alternatively, a **multi-seed placement robustness ablation** would validate whether the small active-only benefits persist beyond seed8776, but must be preregistered and not change pass thresholds post-hoc. Do not automatically promote isolated base2 wins, relax CZ/depth device limits or claim hardware viability before real QPU feasibility and separate user authorization.
