# VERIFIED matched-seed engineering PASS vs original N35 ripple, with a distinct negative-control OR-carry polarity; stronger De Morgan comparator remains preferred

**Research lead / attribution:** Chase Lunsford / CaMaLabs. Date October 17 Pacific / October 18 UTC, 2026. **ZERO real IBM quantum device jobs, physical shots, Open/free Quantum Runtime or paid runtime.** All IBM Fez numbers below are authenticated **backend TARGET gate compilation on a CPU** with Qiskit~=2.5.2 and qiskit-ibm-runtime~=0.47.0, optimization level1, same fixed set of eight seed integers, not QPU execution. This is ONE complete reversible six-bit controlled modular multiplication N=35 on two PUBLIC bases, not complete Shor quantum phase estimation or cryptographic advantage.

## History and why this branch still adds scientific information

The best earlier full-residue, quantum-phase-correct comparator logic [`QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md`](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) has native-ISA compilation base2 **9,263 CZ / depth21,772** and cube8 **9,426 CZ / depth21,933** at frozen seed8776, with 32 source logical qubits (25 initially clean/returned-clean auxiliary). A later [active-only cached control 8-seed study](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) showed one good seed8776 was NOT robust, especially for cube8 (1/8 joint native CZ/depth wins). This motivates preregistering all eight layouts and both public bases before source scoring.

Critically, the repository also independently verified a **different one-CNOT OR-carry implementation** that temporarily inverted the PREVIOUS CARRY bit instead of the input x ([full source and eight-seed result](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_RESULT.md)); it improved CZ for 8/8 seeds on both bases but only 5/8 jointly improved cube8 CZ/depth. A still-later **De Morgan zero-CNOT OR-carry** [robust matched three-arm study](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) **passed 8/8 joint CZ/depth wins on BOTH bases** versus that earlier one-CNOT candidate in a frozen 48-compile CPU benchmark. The present study is a distinct *control-polarity* version (invert source x, not previous carry) using the same Boolean identity, that was **preregistered and committed before its own scoring**. This branch is an extra engineering control and does NOT supersede De Morgan's already verified stronger eight-seed design.

[Immutable preregistration](QRR_N35_OR_CARRY_POLARITY_MATCHED_SEEDS_PREREG.md) git commit `c4032f83db9e91d0986a16ab545f6f9465bcad20`, exact **8 seeds** `[11,37,101,409,8776,12011,20261,45673]`, two bases N35 a2/cube8, both full six-bit inputs and same 32-qubit source register, optimization1 and exact Fez compiler target backend. Frozen **ROBUST engineering gate**: ALL complex quantum phase and clean helper proofs must pass, 8/8 matched compiles per base, seed8776 anchor reproduce historic original, and BOTH public bases have **at least 6/8 joint lower CZ AND depth seeds plus negative paired median CZ/depth**. Frozen device preflight remains **native CZ≤800 AND depth≤2000**, no QPU even if passed.

## Exactly one circuit change

[Original experiment source `hardware/qrr_n35_or_carry_polarity_matched_seeds.py`](../hardware/qrr_n35_or_carry_polarity_matched_seeds.py) retains original X/CX/CCX exact target flips, phase-relative RCCX temporary comparator carry gates and their Qiskit actual adjoints, public prefix-carry adders, modular correction, active/enable cache latches, full work/acc SWAP and inverse cleanup. It modifies ONLY temporary comparator carry when the public threshold complement bit equals 1.

Original clean carry step for source bit x and prior clean computed p:
`x OR p = x XOR p XOR (x AND p)`, source `CX(x,cur); CX(p,cur); RCCX(x,p,cur)`.

**Source-X-negated one-CX alternative** uses `x OR p = x XOR ((NOT x) AND p)`: `CX(x,cur); X(x); RCCX(x,p,cur); X(x)`. On uncompute, it applies `X(x); RCCX.inverse(x,p,cur); X(x); CX(x,cur)`. All operations use temporary clean carry scratch; x is restored before next step; semantic final predicate flag controlled flip is exact, never relative phase. The earlier one-CX experiment inverted *p*; the present arm inverts *x*. The two implementations have the same arithmetic truth table and similar source gate counts, but can route differently on a native IBM target.

**Actual source intervention is observed:** complete base2 source changes old **CX1033→691, X28→712** (exact source CCX160 and RCCX596 unchanged); cube8 **CX1077→717, X28→748** (CCX162/RCCX616 unchanged). Exactly 171 public b=1 OR-carry steps base2, 180 cube8; 2 CX removed and 4 X added per full compute/uncompute step. The application width32 and 25 clean auxiliaries remain identical. No N35 factors, order, orbit or value-to-output truth table is injected.

## BEFORE compiler: direct phase-exact actual emitted operator verification

The experiment built the original full quantum source BEFORE patching its comparator, then independently built the new source. For BOTH variants, it extracted each actual emitted Qiskit gate `Operator(instruction.operation)` and interpreted complex amplitude through the complete X/CX/CCX/RCCX source stream. It required final complex amplitude **+1**, correct 6bit arithmetic and all 25 auxiliaries zero, rather than trusting Boolean identity to preserve quantum phase. Per base:

- Original and candidate comparator each passed **42,672/42,672** cases, every public threshold width1..6, both comparator polarities, both control bits and both initial flag bits, clean carry/scratch and final complex phase+1.
- Original and candidate modular addition each passed **1,584/1,584** emitted-gate cases (all 16 public constants×99 active-valid/disabled residue states), correct modulo35 addition, clean wrap/carry/scratch, final phase+1.
- Original and candidate full controlled modular multiplier each passed **128/128** cases covering all six-bit work y0..63 × control0/1, exact public multiplication if enabled/valid, identity otherwise, final phase+1 and **all25 auxiliary bits clean**. Because the mapping and complex phase are exactly verified on all 128 initially-clean source states, the ideal source action extends coherently to their superpositions.
- The source proof is independent of native transpiler seed and was completed BEFORE authenticated read-only Fez target access. It does not establish physical hardware fidelity.

## Every frozen matched eight-seed result, including regressions

Native CZ / depth costs, with paired **candidate-minus-original** changes. Negative differences are improvements; positive means regression. The original is the previously verified basic relative-phase ripple comparator, not the previously optimized one-CX or De Morgan variant. All 32 compiler runs use the same source/backend target and the frozen seed per pair, not postselected different-seed layouts.

| Seed | Base2 original CZ/depth | Base2 source-X-negated CZ/depth | ΔCZ | Δdepth | Both better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,774 / 20,129 | 8,609 / 19,419 | −165 | −710 | YES |
| 37 | 8,856 / 20,523 | 8,294 / 18,955 | −562 | −1,568 | YES |
| 101 | 9,125 / 21,276 | 8,353 / 19,298 | −772 | −1,978 | YES |
| 409 | 8,953 / 20,627 | 8,649 / 19,523 | −304 | −1,104 | YES |
| **8,776** | **9,263 / 21,772** | **8,945 / 20,616** | **−318** | **−1,156** | **YES** |
| 12,011 | 9,034 / 20,977 | 8,599 / 19,979 | −435 | −998 | YES |
| 20,261 | 9,255 / 21,719 | 8,761 / 19,675 | −494 | −2,044 | YES |
| 45,673 | 9,288 / 21,476 | 8,766 / 19,849 | −522 | −1,627 | YES |

Base2 **8/8** CZ wins, **8/8** depth wins, **8/8 JOINT wins**. Median paired native **ΔCZ −464.5, Δdepth −1,362**; CZ range −772 to−165, depth −2,044 to−710. Historical old seed8776 **exactly reproduced** previously saved native CZ9263/depth21772; new CZ8945/depth20616. **Frozen robust engineering PASS for base2**.

| Seed | Public cubic base8 original CZ/depth | Cube8 source-X-negated CZ/depth | ΔCZ | Δdepth | Both better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,908 / 21,194 | 8,966 / 20,943 | **+58** | −251 | NO |
| 37 | 9,290 / 21,648 | 8,923 / 20,504 | −367 | −1,144 | YES |
| 101 | 9,232 / 21,288 | 8,908 / 20,103 | −324 | −1,185 | YES |
| 409 | 9,281 / 21,510 | 8,882 / 20,493 | −399 | −1,017 | YES |
| **8,776** | **9,426 / 21,933** | **9,104 / 20,762** | **−322** | **−1,171** | **YES** |
| 12,011 | 9,279 / 22,085 | 8,978 / 20,995 | −301 | −1,090 | YES |
| 20,261 | 9,176 / 21,398 | 8,891 / 20,435 | −285 | −963 | YES |
| 45,673 | 9,178 / 21,952 | 9,307 / 21,181 | **+129** | −771 | NO |

Cube8 **6/8 CZ wins**, **8/8 depth wins**, **6/8 JOINT wins**. Median paired **ΔCZ −311.5, Δdepth −1,053.5**; CZ range −399 to+129, depth −1,185 to−251. The historical original seed8776 anchor **exactly reproduced** 9426/21933; new CZ9104/depth20762. **Frozen robust engineering PASS for cube8**, exactly meeting the 6/8 predeclared joint seed requirement; retain BOTH unfavorable cube CZ rows rather than hiding them.

**The predeclared two-base matched robustness engineering gate PASSES** with 8/8 and6/8 joint native wins and strict negative medians. The alternative control polarity helps comparator routing/depth, but is NOT the overall best verified design. The separately independently audited [De Morgan zero-CX comparator](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) performed **8/8 both-resource joint wins against the prior one-CX implementation for both bases** and at seed8776 has lower native CZ/depth than this present comparator: De Morgan base2 **7993 CZ / depth18604**, cube8 **8758 CZ / depth20575**, versus this candidate 8945/20616 and9104/20762. These values are from distinct frozen CI source runs; no invented single common three-/four-arm trial. De Morgan should remain the preferred research baseline under the evidence presently available.

## Original provenance and independent untouched-receipt audit

[Original source-run CI **39099579484**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39099579484) **2/2 source jobs SUCCESS**. Both sources phase verified and compiled 16 authentic native CPU target circuits per base; each individual run's independent source-receipt audit passed. [Independent original source-artifact audit and preservation CI **39099703212**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39099703212) **SUCCESS**: downloaded the two immutable source-run artifact JSONs, verified every one of the 32 original numerical CZ/depth receipts, actual source X/CX/RCCX/CCX distributions, both baselines and complete phase-exact source proofs, all eight pairs and signed deltas/medians, original seed8776 anchors, strict 6/8 gates, and zero hardware submissions, then committed **the exact original JSON bytes without recompiling**:

- [Original full base2 eight-seed receipt](../results/ibm_shor35_or_carry_polarity_seeds/qrr_n35_or_carry_polarity_base2.json).
- [Original full public cube8 eight-seed receipt](../results/ibm_shor35_or_carry_polarity_seeds/qrr_n35_or_carry_polarity_base8.json).

**Hardware feasibility FAIL for EVERY compiled circuit**: smallest new base2 CZ8294 and depth18955 remains about an order of magnitude beyond frozen **native CZ≤800 AND depth≤2000** even for ONE multiplication, before four QPE phase rounds. N35 is a trivial classical-factorable public test instance; no QPU runtime, no physical quantum advantage or practical cryptanalysis. All prior experiments, negative results and the genuinely measured Open Plan N15 phase-recycling pilot remain separately preserved.

## Next grounded step

The better De Morgan zero-CX design is the current **preferred phase-exact two-base eight-seed circuit**. Test a NEW preregistered combined De Morgan plus cached `active_only` relative-phase latch against De Morgan alone using a *full matched eight-seed* phase-exact comparator/modadd/multiplier source gate proof, recording any cubic regressions honestly. Or isolate additional public constant controlled-add/subtract arithmetic paths while keeping De Morgan source fixed. Never assume RCCX active-latch gains at one favorable seed generalize: the older control-latch robustness experiment failed for cubic base8. The predeclared N35 hardware gate remains unchanged and blocks real QPU jobs.
