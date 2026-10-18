# VERIFIED NEGATIVE ROBUSTNESS — N35 phase-exact public constant/carry fusion removes 51/55 source CX but fails both 8-seed native CZ+depth gates

**Research lead / original research program: Chase Lunsford / CaMaLabs.** Date 2026-10-17 Pacific / original Actions timestamps 2026-10-18 UTC. All experiments are **CPU Qiskit native IBM Fez hardware-target compilation ONLY**; authentic Fez target metadata was read, no physical IBM quantum processor instruction was submitted. **Zero real QPU jobs, zero free/Open quantum runtime and zero paid quantum runtime**. A single full-six-bit N35 public controlled multiplier is not a four-phase-bit Shor circuit, and classically trivial N35 work demonstrates no RSA-scale cryptanalytic capability.

## Frozen motivation and clean historical controls

The independently verified [best common comparator-only N35 relative-phase-carry result](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) retained 32 logical source qubits, 25 returned-clean auxiliaries, full six-bit 64-state residue behavior and exact quantum phase+1. At the historical Qiskit~=2.5.2 / qiskit-ibm-runtime~=0.47, read-only target `ibm_fez`, optimization1 seed8776 it compiled **base2 9,263 CZ / depth21,772** and **cubic public base8 9,426 CZ / depth21,933**, stored as original unmodified `results/ibm_shor35_relative_phase_ripple/qrr_n35_relative_phase_clean_vchain_base{2,8}.json`. The prior [eight-seed active-only cached latch ablation](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) established this architectural lesson: even a genuine two-base seed8776 win can fail robustness (5/8 joint resource wins base2 and 1/8 cubic base8). We therefore froze the next target *arithmetic* improvement with **eight paired compiler seeds from the outset**, without using the earlier active-only single-seed as the benchmark.

[Original hypothesis preregistration](QRR_N35_FUSED_CONSTANT_CARRY_MULTISEED_PREREG.md) was committed as **`b516cff92d3786504069f513f5bb4f7f999f4657` BEFORE new compiler costs**. It freezes public N35 bases `2,8`, exact seeds `11,37,101,409,8776,12011,20261,45673`, same backend snapshot within each base job, optimization1, unchanged source register logic and separately immutable native hardware gate **CZ≤800 AND depth≤2000**. Strict two-base *robust engineering PASS* requires BOTH bases with at least **6/8 joint CZ AND depth matched-seed improvements**, both paired metric medians negative, full exact quantum phase proof, and exact old baseline seed8776 reproduction. No post-result seed selection or threshold loosening.

## Exactly one isolated arithmetic rewrite

[Source `hardware/qrr_n35_fused_constant_carry_multiseed.py`](../hardware/qrr_n35_fused_constant_carry_multiseed.py) constructs the original comparator-only `verified.build(base)` circuit **before** changing any arithmetic. It then substitutes exactly one public conditional constant-add function in the same verified multiplier implementation and constructs the candidate, leaving original work/acc registers, cached source enable bits, phase-aware RCCX/inverse temporary **ripple comparator carry**, the same mod35 wrap/−35 correction, swap, inverse addition, and source qubits untouched.

For fixed publicly known k in an enabled `+k (mod2^6)`, the j-th bit would toggle by `k_j XOR carry_j` if the external enable is 1, where `carry_j=[x_{<j} >= (2^j−(k mod2^j))]` for nonzero public lower constant. Since output bits are updated HIGH to LOW, the low source bits still represent the original x. When **both k_j=1 and the public lower k bits are nonzero**, the old lowering emitted (a) a controlled `carry_j>=threshold` predicate XOR and (b) an unconditional controlled X on the same output bit. Their XOR equals **one** controlled `carry_j<threshold` predicate flip, with the existing exact relative-phase temporary-carry comparator's `geq=False` mode; that mode temporarily inverts an internal clean carry bit and undoes the inversion. For k_j=0 or zero low prefix, retain original behavior. The actual transformation is general six-bit fixed-constant modular addition, not factor-, order- or period-aware and not a precomputed multiplication truth table.

**Exact full-source changes VERIFIED**, comparing old and new source emitted quantum opcodes, for precisely one full public controlled N35 multiplier:

| Source emitted quantum gate count | Old base2 | Fused base2 | Old public cube8 | Fused cube8 |
|---|---:|---:|---:|---:|
| CX | 1,033 | **982 (−51)** | 1,077 | **1,022 (−55)** |
| X | 28 | **130 (+102)** | 28 | **138 (+110)** |
| relative-phase RCCX | **596** | **596** | **616** | **616** |
| exact semantic CCX | **160** | **160** | **162** | **162** |
| source logical qubits |32|32|32|32|
| 25 clean aux register bits |25|25|25|25|

The **only observed emitted-gate change** is one CX removed and two temporary X inversions added per fused public bit/carry predicate. Fewer source CX do **not** guarantee fewer native Fez CZ or depth after placement/routing/optimization. This is not an asymptotic factoring theorem.

## Phase-sensitive actual emitted-Qiskit-gate proofs — PASS before backend target read

The source uses the exact prior emitted Qiskit `Operator(inst.operation)` complex-monomial gate interpreter. It propagates real/imaginary quantum phase through the **actual emitted** Qiskit instruction stream and rejects any wrong output, dirty carry/scratch/aux register, nonmonomial instruction, or residual complex phase different from **+1** on every tested basis input. This supports coherent ideal behavior on the clean-aux source subspace via linearity, not actual hardware noise/fidelity.

**Each of the two independent public-base jobs passed:**

- **8,192/8,192** newly added standalone six-bit constant adder cases, **ALL** k=0..63 × **ALL** x=0..63 × both external enable values, correct x+k mod64/disabled identity, clean 6-bit comparator carry and 9 scratch, exact quantum amplitude+1; tests include k=0 and the publicly used modulo64 representation of −35.
- **42,672/42,672** original phase-aware comparator cases, across every public threshold and six-bit-or-shorter input size, both comparator polarities, enabled/disabled controls and initial target flag values, exactly +1 complex amplitude and clean carries.
- **1,584/1,584** actual full mod35 controlled constant additions, 16 public constants × 35 valid enabled input residues plus 64 disabled six-bit residues, exact phase+1, wrap/carry/scratch reset.
- **128/128 original reference** and **128/128 new candidate** complete controlled N35 multiplier cases, each all 64 six-bit work states × phase bit0/1, correct public multiplication on enabled valid y, identity on disabled or invalid y≥35, all **25 auxiliaries returned zero**, complex amplitude exactly +1.
- Explicit source opcode count and 32-qubit width checks proved CX savings with no extra CCX/RCCX or dirty helper registers. No Qiskit native compiler work started before these proofs passed.

## Every seed's native IBM Fez CPU-compiler result, no selective reporting

The [successful original two-base GitHub Actions run **39082263845**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39082263845) completed **2/2 native CPU compiler jobs successfully**, each **8 matched seed pairs**, total **32 authentic native ISA CPU compilations**. The original unchanged `neither` baseline was always compiled FIRST, fused candidate SECOND, using the same native target and compiler seed in each pair. Both passed the independent per-job original-gate/seed-audit step. The **seed8776 old control reproduced exactly** (base2 CZ9263/depth21772, cube8 CZ9426/depth21933), demonstrating no apparent historical native target/SDK anchor drift under these settings.

Values below are **CZ / native depth**. Paired signed changes are candidate−original, so negative is better, positive is worse.

| Frozen seed | Base2 original | Base2 fused | ΔCZ | Δdepth | Both improve |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,774 / 20,129 | 8,694 / 20,628 | −80 | +499 | NO |
| 37 | 8,856 / 20,523 | 9,167 / 21,642 | +311 | +1,119 | NO |
| 101 | 9,125 / 21,276 | 9,218 / 21,092 | +93 | −184 | NO |
| 409 | 8,953 / 20,627 | 9,173 / 21,435 | +220 | +808 | NO |
| 8,776 | 9,263 / 21,772 | 8,906 / 21,167 | −357 | −605 | **YES** |
| 12,011 | 9,034 / 20,977 | 9,052 / 20,955 | +18 | −22 | NO |
| 20,261 | 9,255 / 21,719 | 8,914 / 20,924 | −341 | −795 | **YES** |
| 45,673 | 9,288 / 21,476 | 9,062 / 21,468 | −226 | −8 | **YES** |

**Base2:** **3/8 strict joint wins**, **4/8 CZ-only wins**, **5/8 depth-only wins**; median paired **ΔCZ=−31**, median **Δdepth=−15**, but both medians are too small and **3/8** clearly fails prereg **6/8**. Paired CZ range **−357..+311**, depth **−795..+1,119**; unfavorable seed37 must not be hidden. Seed8776 alone looks substantially attractive (CZ9263→8906, depth21772→21167) but does not generalize reliably to the fixed seed set.

| Frozen seed | Public cubic base8 original | Cube8 fused | ΔCZ | Δdepth | Both improve |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,908 / 21,194 | 9,040 / 21,615 | +132 | +421 | NO |
| 37 | 9,290 / 21,648 | 9,266 / 22,048 | −24 | +400 | NO |
| 101 | 9,232 / 21,288 | 9,022 / 21,529 | −210 | +241 | NO |
| 409 | 9,281 / 21,510 | 9,108 / 21,610 | −173 | +100 | NO |
| 8,776 | 9,426 / 21,933 | 9,261 / 21,876 | −165 | −57 | **YES** |
| 12,011 | 9,279 / 22,085 | 8,872 / 20,718 | −407 | −1,367 | **YES** |
| 20,261 | 9,176 / 21,398 | 8,999 / 21,956 | −177 | +558 | NO |
| 45,673 | 9,178 / 21,952 | 9,194 / 21,474 | +16 | −478 | NO |

**Public cubic base8:** **2/8 strict joint wins**, **6/8 CZ-only wins**, **3/8 depth-only wins**; median paired **ΔCZ=−169** (lower CZ), **Δdepth=+170.5** (**worse**). Paired CZ range −407..+132, depth −1,367..+558. Even with 6/8 CZ reductions, most seed pairs have no improvement in depth; robust engineering gate fails. Selecting the unusually favorable 12011 seed alone would be improper.

### Frozen conclusion and hardware boundary

| Preregistered control | Base2 | Cubic base8 |
|---|---:|---:|
| 8,192+42,672+1,584+128+128 actual source exact phase cases | **PASS** | **PASS** |
| Source function genuinely changed (51/55 CX removed) | **PASS** | **PASS** |
| All 8/8 same-target compiler pairs and exact old 8776 anchor | **PASS** | **PASS** |
| Joint native CZ+depth improvement in ≥6/8 seeds | **FAIL: 3/8** | **FAIL: 2/8** |
| Negative median paired CZ and depth | PASS | **FAIL (depth +170.5)** |
| **Combined robust two-base engineering gate** | **FAIL** | **FAIL** |
| Any single circuit native CZ≤800 AND depth≤2000 | **NO** | **NO** |
| Real IBM QPU jobs, free or paid runtime | 0 | 0 |

The new candidate is a **correct generic constant-adder transformation that is NOT reliable as a two-base native Fez resource improvement**. The old relative-phase comparator-only circuit remains our primary COMMON verified reference. The fused candidate is preserved, not promoted; the earlier seed8776 active-only/enable-only improvements and their negative multi-seed qualification remain separate provenance.

## Independent original artifact audit and source preservation

[Original source-run 39082263845](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39082263845) **SUCCESS**. A second [independent artifact audit/preservation CI **39082382115**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39082382115) **SUCCESS**; it downloaded the **original** produced 2 source-run JSONs (no recompile), independently matched all **32 original CZ/depth numbers** against source job logs, checked native CZ count_ops, source gate counts, exact 8192+42672+1584+128+128 proof counts/complex phases, immutable old receipts, frozen seed list, original seed8776 anchor, signed paired medians and predeclared hardware/engineering-gate failures, and **committed original unmodified JSON bytes** under:

- [Original base2 eight matched seed receipt](../results/ibm_shor35_fused_constant_carry_multiseed/qrr_n35_fused_constant_carry_base2.json).
- [Original public cube8 eight matched seed receipt](../results/ibm_shor35_fused_constant_carry_multiseed/qrr_n35_fused_constant_carry_base8.json).

Prior original real IBM Fez N15 Open Plan toy Shor phase-qubit recycling remains an independent hardware milestone and is NOT extrapolated to N35 cubic QPU factor recovery. All existing N35 negative, null and conditional positive studies remain intact.

**Next disciplined direction:** A more substantive constant-correction lowering, dynamic programming on public carry control literals, or a genuinely lower-cost arithmetic algorithm may be worth preregistering. Require independent `Operator` complex-phase full-residue semantics and matched multi-seed comparisons *from first compilation*, report controls and regressions, and do not attempt real N35 hardware or claim practical factoring until a credible complete-QPE resource budget satisfies hard device boundaries and separately confirmed Open Plan authorization.
