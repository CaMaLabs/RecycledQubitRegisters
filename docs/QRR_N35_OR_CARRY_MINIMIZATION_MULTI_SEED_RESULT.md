# VERIFIED PARTIAL — phase-exact one-CX-lower public OR comparator improves CZ across ALL 16 paired seeds, but frozen two-base CZ+depth robustness gate FAILS

**Research lead/originating program:** Chase Lunsford / CaMaLabs. **Original experiment:** October 17, 2026 Pacific / October 18 UTC. This is a **CPU-only Qiskit IBM Fez hardware-TARGET native compiler experiment**, never real IBM QPU execution. **ZERO IBM quantum hardware jobs, ZERO Open/free or paid QPU Runtime, ZERO physical shots.** The target is ONE controlled six-bit public N35 modular multiplier on either base2 or cube8, **not a complete four-phase-bit Shor factoring circuit, measured quantum hardware advantage, cryptanalysis of ML-KEM/RSA, or a new factoring theorem**.

## Prior verified milestones and frozen scientific question

The independently audited [original phase-correct shortened-ripple comparator and public prefix-carry arithmetic](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) had **base2 native CZ9263/depth21772** and **cube8 CZ9426/depth21933** for each ONE full-residue controlled multiplier at IBM Fez CPU target compilation with `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, opt1 seed8776. Circuit width was **32 logical qubits, with 25 clean auxiliaries**. The old original source was proven with exact emitted-gate complex output phase+1 across the standalone public comparator, public modulo35 adder and complete full-residue controlled multiplier, not merely a Boolean answer oracle.

Later [relative-phase temporary active/enable cache latch family](QRR_N35_RELATIVE_PHASE_LATCH_FAMILY_ABLATION_RESULT.md) included favorable single-seed native reductions, but the [strict matched 8-seed active-only test](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) showed **only 5/8 base2 and 1/8 cube8** seeds improve BOTH native CZ and depth, failing its prereg two-base ≥6/8 rule; cube8 medians worsened. That is the relevant control for this new experiment: never infer general robustness from one seed. Earlier real IBM N15 Open Plan phase-qubit-recycling observation was genuine but NOT a cubic-order-reduction demonstration; all N35 work here is preflight compiler analysis only.

The new original [precommitted OR-carry matched-seed preregistration](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_PREREG.md), initial git **`51f7fa7cbeb72c83ac03f3f90dcbedb763a81eea`**, freezes the **same eight public integer transpiler seeds** `[11,37,101,409,8776,12011,20261,45673]` on BOTH bases2 and8, in **32 original matched old/new native CPU compilations** with fixed Qiskit optimization1, one IBM Fez read-only target per job. Do not select only favorable seeds, tune layouts, infer QPU performance, or weaken the 6/8 both-resources criterion post hoc.

## Single exact quantum-safe source transformation

[New original source `hardware/qrr_n35_or_carry_multi_seed.py`](../hardware/qrr_n35_or_carry_multi_seed.py) imports the original proven comparator and modular arithmetic, leaving ALL source/target semantics, validity handling, controls, public threshold truncation, public prefix-carry fixed constant adder, full 64-state six-bit register, cached control latches, clean work/acc uncomputation and exact `primitive.multi_x` semantic flips unchanged. It introduces **ONLY** a lower-CNOT Boolean synthesis for each noninitial comparator carry bit where the known public threshold complement bit equals **1**:

Original carry recurrence for source x and previous carry p is `c = x OR p = x XOR p XOR (x AND p)`, implemented by **two CX and one temporary RCCX** in the compute pass. Candidate implements exactly `c = p XOR (x AND NOT p)`, which requires **one CX plus two temporary X on the previous carry and one temporary RCCX**. All temporary X inversions are restored. The uncompute pass executes the literal inverse gate sequence with Qiskit's ACTUAL `RCCXGate().inverse()`, not a Boolean-only approximation. This saves **2 source CX per affected OR-carry step** across compute+uncompute while adding **4 X** per step; it leaves RCCX and exact semantic CCX counts unchanged. Because RCCX has relative phases, it would not suffice to check output bits; a true quantum source transformation must preserve every tested basis amplitude exactly +1.

The program independently verifies all four Boolean inputs for the public OR identity and the 8×8 `Operator(RCCXGate().inverse()) @ Operator(RCCXGate()) = I` relation. Then, **BEFORE any IBM backend target read**, it simulates every ACTUAL emitted X/CX/CCX/RCCX Qiskit operator on basis inputs as monomial complex-amplitude gates, multiplying phases along the **entire real instruction stream** and verifying complete output phase **+1**, semantic output bits and clean ancillas.

Per public-base original job (ALL PASS):
- **4/4** Boolean OR identity cases and actual RCCX inverse operator identity;
- **42,672/42,672** actual emitted-gate unsigned comparator cases across every width1..6, threshold, greater/equal and less-than, enabled/disabled controls and both initial flag values, all temporary carry/scratch clean, complex phase+1;
- **1,584/1,584** actual emitted modular-add cases for all **16** distinct public N35 constants across 35 valid enabled and64 arbitrary disabled target values, complex phase+1 and wrap/carry/scratch reset;
- **128/128 old-original AND 128/128 new-candidate full multiplier** actual emitted-gate cases each: both controls and every six-bit y=0..63, correct public `a*y mod35` on valid enabled inputs, identity on invalid/disabled states, unchanged control, **all 25 helper bits returned ZERO**, and final quantum amplitude exactly **+1** for every test;
- Both source circuit logical widths remain **32**. Exact source change on complete base2: **171 public OR carry steps, CX 1033→691 (342 fewer), X28→712 (684 more), RCCX596 unchanged, exact CCX160 unchanged**. Cube8: **180 OR carry steps, CX1077→717 (360 fewer), X28→748 (720 more), RCCX616 and CCX162 unchanged**. Unlike earlier null-clean-V-chain experiment, this intervention was actually exercised in both complete multipliers. This proof establishes coherent ideal behavior on the tested clean-ancilla subspace by linearity, not any physical-noise fidelity.

## All matched eight-seed native CPU results — no postselection

Each row compares original **neither** phase-aware comparator with the OR-minimized comparator **for the SAME transpiler seed**, both compiled on the same target metadata object, same `qiskit~=2.5.2`/IBM Runtime SDK~=0.47, Qiskit optimization1, register size and public base. Native CZ and depth are *compiler resource proxies*, not QPU runtime or observed fidelity. **Negative Δ means saving, positive Δ means regression.**

### Base2, N35 ONE controlled multiplier

| Seed | Original CZ / depth | OR-minimized CZ / depth | Matched ΔCZ | Matched Δdepth | Both better |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,774 / 20,129 | 8,532 / 20,683 | −242 | +554 | NO |
| 37 | 8,856 / 20,523 | 8,606 / 20,913 | −250 | +390 | NO |
| 101 | 9,125 / 21,276 | 8,340 / 20,193 | −785 | −1,083 | YES |
| 409 | 8,953 / 20,627 | 8,685 / 20,547 | −268 | −80 | YES |
| **8,776** | **9,263 / 21,772** | **8,311 / 19,981** | **−952** | **−1,791** | **YES** |
| 12,011 | 9,034 / 20,977 | 8,691 / 20,798 | −343 | −179 | YES |
| 20,261 | 9,255 / 21,719 | 8,880 / 21,060 | −375 | −659 | YES |
| 45,673 | 9,288 / 21,476 | 8,542 / 20,502 | −746 | −974 | YES |

**Base2 result: 8/8 native CZ improvements, 6/8 native depth improvements, 6/8 JOINT improvements; median paired ΔCZ = −359, median paired Δdepth = −419.** Paired ΔCZ range −952 to−242, depth −1791 to +554. Original seed8776 baseline **exactly reproduced** the previously archived 9263/21772; new 8776 is **8311 CZ/depth19981**, representing −10.28% CZ and −8.23% depth compared with this exact matched original. **This base PASSES the preregistered strict engineering gate.** New CZ8311 is below prior separately observed base2 two-latch CZ8542, but new depth19981 is SLIGHTLY HIGHER than that earlier configuration's 19819, and that comparison is not a matched two-base eight-seed trial; do not call it universally superior.

### Public cubic base8, N35 ONE controlled multiplier

| Seed | Original CZ / depth | OR-minimized CZ / depth | Matched ΔCZ | Matched Δdepth | Both better |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,908 / 21,194 | 8,907 / 21,042 | −1 | −152 | YES |
| 37 | 9,290 / 21,648 | 8,624 / 20,964 | −666 | −684 | YES |
| 101 | 9,232 / 21,288 | 8,963 / 21,548 | −269 | +260 | NO |
| 409 | 9,281 / 21,510 | 8,550 / 21,003 | −731 | −507 | YES |
| **8,776** | **9,426 / 21,933** | **9,141 / 21,528** | **−285** | **−405** | **YES** |
| 12,011 | 9,279 / 22,085 | 8,739 / 21,359 | −540 | −726 | YES |
| 20,261 | 9,176 / 21,398 | 9,048 / 22,035 | −128 | +637 | NO |
| 45,673 | 9,178 / 21,952 | 8,915 / 22,286 | −263 | +334 | NO |

**Cube8 result: 8/8 native CZ improvements, 5/8 native depth improvements, only 5/8 JOINT improvements; median paired ΔCZ = −277, median paired Δdepth = −278.5.** Paired CZ range −731 to −1 (smallest CZ gain just one gate), depth −726 to +637 (three REGRESSIONS). Original seed8776 exactly reproduced original 9426/21933; new 8776 is **9141 CZ/depth21528**, both improved there, but seed8776 alone cannot satisfy frozen multi-seed rule. **Cube8 FAILS the frozen preregistered ≥6/8 joint win rule by one seed despite favorable median and universal CZ reductions.**

**Two-base robust engineering gate therefore FAILS**, not a joint “robust pass.” The promising stronger claim supported by the controlled data is narrower: this **one exact OR-carry rewrite reduces native CZ for all sixteen paired public-base/seed comparisons**, but source gates and native depth remain layout-sensitive, and the cubic-base joint benchmark fails the predeclared criterion. With only eight fixed compiler seeds and one target/compiler version this is not universal gate-count robustness across all backends, calibrations or future Qiskit versions.

## Original run, independent audit, and immutable receipts

[Original eight-seed two-arm CI **39095494407**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39095494407) **SUCCESS 2/2**. Each completed exact-phase checks before backend read, compiled **16** authentic CPU native Fez target circuits (old/new×8 fixed seeds), passed its own independent detailed frozen-target/cost/seed audit, uploaded two original source-run JSON artifacts. **No runtime jobs submitted.**

[Independent original-source artifact audit/preservation CI **39095605020**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39095605020) **SUCCESS**; downloaded the ORIGINAL two source-run JSON artifacts **without rerunning scientific experiment or recompiling any Qiskit circuit**. Independently checked 32 exact source-run native CZ/depth results, all source complex-phase proof counts, all 32 native CZ count_ops and ISA widths, exact historical seed8776 anchors, every frozen paired seed, old original JSON baseline, medians/ranges/win counts including unfavorable seed rows, separate immutable hardware gate and QPU=0 indicators, then committed untouched original JSONs to:

- [Original base2 complete eight-seed source receipt](../results/ibm_shor35_or_carry_multi_seed/qrr_n35_or_carry_multiseed_base2.json)
- [Original public cube8 eight-seed source receipt](../results/ibm_shor35_or_carry_multi_seed/qrr_n35_or_carry_multiseed_base8.json)

All original prior successes, source scripts, negative placement results and real N15 Open Plan quantum phase recycling milestone remain separately preserved in main. QPU secrets are not written to logs.

## Immutable real-QPU no-go gate and next direction

Frozen native ISA physical Fez preflight still requires **CZ≤800 AND depth≤2000** for either base before considering actual hardware. **ALL 32 original and new compiled configurations FAIL both resource limits** by at least an order of magnitude. Even the best new base2 8311 CZ/depth19981 is **10.39× CZ and 9.99× depth** beyond the 800/2000 thresholds, on **only one controlled multiplier**, and a full four-phase-bit Shor period finding / factor production is far larger. **ZERO actual N35 QPU jobs, no Open/paid Runtime consumed.**

This is a measured *resource compiler* advance from a publicly derived Boolean carry equality and exhaustive genuine Qiskit emitted-gate phase checks, **not evidence of real hardware factoring, a new quantum algorithmic theorem, or a cryptographic break**. Next credible research should explore a further constant-specific topology-independent carry network or native routing constraints with **matched multiple seed tests included from the start**, explicitly preserving every seed and the two-base strict joint gate. The user's separate order-reduction/cubic preconditioning proposal should be assessed at a full protocol level only after modular arithmetic is far closer to device feasibility.
