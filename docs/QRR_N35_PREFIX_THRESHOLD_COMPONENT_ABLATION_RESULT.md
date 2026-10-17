# VERIFIED — N35 isolated prefix-carry vs trailing-zero threshold component ablation on IBM Fez target (ZERO QPU)

**Research lead / originating program:** Chase Lunsford / CaMaLabs. Experiment 2026-10-16 Pacific / 2026-10-17 UTC. **No QPU job, no Open Plan/free runtime, no paid runtime, no simulator masquerading as hardware.** These numbers are **CPU Qiskit compilations against authenticated real IBM Fez native TARGET information, not live QPU shots or a quantum advantage.**

## Historical controls and frozen preregistration

The previously verified N35 single full-residue controlled modular multiplication circuit from the [cached enable controls study](QRR_N35_LATCHED_CONTROLS_SINGLE_MULTIPLIER_RESULT.md) generated original base2 **18,719 CZ / depth42,335**, cube8 **19,912 CZ / depth44,381** with logical32 application qubits. The subsequent [combined prefix carry + threshold-shortening](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md) was stronger (base2 **12,517 CZ / depth32,312**, cube8 **12,680 CZ / depth33,138**), but because it changed both elements simultaneously we could not separately credit them. Original artifacts and logs remain immutable.

[Preregistered component comparison](QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_PREREG.md), initial separate commit **`79c1934c162b39c253597305cf42b3459738f0dd`** before new compiler measurements, freezes exactly FOUR arms: only prefix-carry rewriting / only threshold-length shortening, each at public original base2 and public cubic base8 modulo35, single controlled six-bit work-register modular multiplication, fixed identical inherited cached enable phase/valid controls, 32 qubits, X/CX/CCX source, Qiskit~=2.5.2/runtime~=0.47.0, IBM `ibm_fez` target read-only, transpiler optimization1 seed8776. No private factoring inputs, true group order, precomputed 12-state orbit, full 64-state truth-table synthesizer or alternate seeds/search. Frozen physical run gate CZ<=800 AND depth<=2000 was not modified.

The four-arm experiment uses original [`hardware/qrr_n35_prefix_threshold_component_ablation.py`](../hardware/qrr_n35_prefix_threshold_component_ablation.py). Both options preserve the [earlier cached controlled multiplier builder](../hardware/qrr_n35_latched_controls_single_modmul.py) and the [unmodified verified low-level reversible X/CX/CCX gates](../hardware/qrr_n35_single_modmul_ripple_toffoli.py). It swaps ONLY `primitive.modadd` at build time to dispatch a single component with explicit variant name:

1. **`prefix_only`**: rewrite `+k mod64` into high-to-low output toggles driven by public carry predicates of the still unchanged lower operand bits. Comparison/threshold gating uses the ORIGINAL full-width comparator `primitive.predicate` everywhere, never the public trailing-zero shortening helper.
2. **`threshold_only`**: retain the ORIGINAL descending controlled suffix-increment `primitive.add_constant_mod2n`, but replace unsigned `x>=t` and `x<t` comparisons (mod-add wrap and output-uncompute) with publicly shortened `x>>s >= t>>s`, where `s=v_2(t)`. This applies no direct prefix-bit carry rewrite.
3. The old cached-enable baseline uses NEITHER. The old combined variant uses BOTH. Comparison is within unchanged one-kernel public base and Qiskit compiler settings; logical qubit width 32 in all cases.
4. Each isolated arm checks EXACT actual Qiskit-emitted X/CX/CCX instruction stream, rather than a separate algebraic shadow reference: **16 unique public `+k mod35` constants ×(35 enabled valid x +64 disabled full-range x)=1584/1584 tests**, plus **128/128 full controlled modulo35 multiplication** `c∈{0,1}, y=0..63`, invalid residues unchanged, control unchanged, all **25 helper qubits clean**. Together four arms yield **4×1712=6848** direct ideal-gate basis cases. These prove the ideal emitted reversible gate mapping on the `ancillas=0` input subspace, NOT physical hardware noise/fidelity.

## Original trial and independent permanent preservation

[Original fixed **four-job** GitHub Actions run **39007742612**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39007742612): **4/4 SUCCESS**, all semantic proof and native target CPU compiler steps passed, no QPU submission. Secret `IBM_QUANTUM_API_KEY` was used only to read `ibm_fez` target. Each completed compiled receipt includes source primitive type gate counts, backend width156 representation (NOT 156 logical application qubits), original prereg/frozen-baseline metadata, compiler CZ/depth/size/elapsed, 16-constant proof and whole-kernel proof, and zero-runtime statements.

[Independent immutable original-source result audit and archival GitHub Actions run **39007830864**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39007830864): **SUCCESS**, downloaded all four original archived experiment output JSONs from source Actions without recompiling; independently checked all prereg conditions, exact current frozen old and combined controls, all 1,584+128 test receipts each, 25 clean helpers, exact fixed-native CZ/depth, correct cost gates, and independently printed interaction residual. Preserved the **untouched original numerical receipts**:

- [prefix only base2](../results/ibm_shor35_prefix_threshold_ablation/qrr_n35_component_prefix_only_base2.json)
- [prefix only cube8](../results/ibm_shor35_prefix_threshold_ablation/qrr_n35_component_prefix_only_base8.json)
- [threshold only base2](../results/ibm_shor35_prefix_threshold_ablation/qrr_n35_component_threshold_only_base2.json)
- [threshold only cube8](../results/ibm_shor35_prefix_threshold_ablation/qrr_n35_component_threshold_only_base8.json)

## Full native CZ result table — one controlled multiplier

| Variant, fixed same N35 base | Base2 native CZ | Base2 compiled depth | Cube8 native CZ | Cube8 compiled depth |
|---|---:|---:|---:|---:|
| Neither: old cached control reference | 18,719 | 42,335 | 19,912 | 44,381 |
| Prefix-carry rewriting ONLY | **14,392** | **38,007** | **14,948** | **39,590** |
| Threshold shortening ONLY | **18,010** | **39,868** | **19,344** | **42,472** |
| Both combined (previous verified) | **12,517** | **32,312** | **12,680** | **33,138** |

All four NEW isolated arm logical widths =32 application qubits; every arm complete controlled modular multiplication passed **128/128** ideal emitted-gate checks and every one of **25 auxiliaries returned to |0>**; each new arm also independently passed the 16×99=1584 enabled/disabled primitive addition checks. All compiled to native `ibm_fez` ISA under fixed same native seed. None passes the frozen device cutoff.

**Isolated result attribution (vs neither baseline):**
- Base2 **prefix only**: CZ 18,719→14,392 (**−23.12%**), depth 42,335→38,007 (**−10.22%**). Cube8: CZ 19,912→14,948 (**−24.93%**), depth 44,381→39,590 (**−10.80%**).
- Base2 **threshold only**: CZ 18,719→18,010 (**−3.79%**), depth 42,335→39,868 (**−5.83%**). Cube8: CZ 19,912→19,344 (**−2.85%**), depth 44,381→42,472 (**−4.30%**).
- The old **BOTH** combination still yields base2 CZ12,517 (−33.13% vs neither), cube8 CZ12,680 (−36.32%), and shorter depth than either isolated arm.

**Nonadditive compiler interaction:** Under the frozen target and layout seed, define `residual=both -(prefix_only + threshold_only - neither)`. This equals:
- Base2 **−1,166 CZ** and **−3,228 depth** (combined *better than separate-difference additive prediction*).
- Cube8 **−1,700 CZ** and **−4,543 depth** (likewise favorable).
This is one deterministic compiler layout/optimization experiment; the residual is an *engineering response interaction*, not proof of independent microscopic gate-composition causality, material QPU coherent interference or asymptotic performance benefits. Backend target calibration changes, different physical mappings, native layout heuristic drift or seed changes are not controlled by repeated trials, so avoid claims of statistically generalized savings.

**Source primitive-gate caveat:** `prefix_only` base2 uses 1,973 primitive gates (CX1,085 / CCX860 / X28), cube8 2,015 (CX1,123 / CCX864 / X28). `threshold_only` base2 uses 1,456 (CX421 / CCX1,007 / X28), cube8 1,504 (CX421 / CCX1,055 / X28). Full combined base2 1,817, cube8 1,883. Native CZ is **not monotonic in total primitive X/CX/CCX count**: the prefix variant reduces expensive Toffoli CCX while increasing cheaper CX. More source gates can transpile to fewer CZ.

## Frozen physical QPU feasibility and next move

**Engineering gate PASSED** 4/4: all exact gate-level semantic proofs and compilations succeeded; each isolated version strictly reduced native CZ and native depth relative to original cached baseline. **Hardware gate FAILED** 4/4: best of new isolated-only circuits still **14,392 CZ/38,007 depth**, substantially above CZ<=800/depth<=2000. The previously verified combined remains lowest **12,517 CZ/32,312 depth**, still far above the bound. **NO IBM QPU job or charges; no hardware experiment, Shor phase-estimation circuit or factor production tested in this new comparison.** N=35 factors classically with trivial work.

**Next experiment direction** should focus on why remaining CCX-to-CZ synthesis is expensive and remove repeated nested wrap predicates at the algorithm/circuit level. The measured interaction indicates the two public constant-specific components are complementary; preserve BOTH in future improvements. A separately preregistered *shared carry/wrap flag* redesign or reduced-workspace arithmetic might help, but must retain the genuine full-register public reversible semantics and exact ideal-gate ancilla checks. Do not propose real QPU Dark Star factoring or loosen hardware limits until a separately verified compact complete phase circuit passes both cost and meaningful factor-output gates. Preserve all prior wins, losses and attribution.
