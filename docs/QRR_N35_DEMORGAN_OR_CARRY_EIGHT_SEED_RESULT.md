# VERIFIED ROBUST ENGINEERING PASS — N35 De Morgan zero-CX public OR carry: 8/8 both CZ+depth wins for BOTH bases vs old and prior one-CX comparator; zero QPU

**Research lead / originating research program: Chase Lunsford / CaMaLabs.** Experiment date 2026-10-17 Pacific / 2026-10-18 UTC original GitHub CI. **All measurements are CPU-only Qiskit compilation to the authenticated IBM Fez native hardware TARGET. ZERO physical IBM quantum processor jobs, shots, Open/free QPU runtime or paid runtime.** The experiment implements one full-six-bit public N35 controlled modular multiplication for each base2 and cubic base8, NOT a complete Shor quantum phase estimation experiment, a real N35 factoring measurement, RSA-scale attack or mathematical novelty theorem. Both full public bases and their actual 64-state invalid input behavior are retained; no true order, private prime factors, special 12-state orbit or output truth-table shortcut is injected.

## Why this candidate, and the immutable earlier data

The original [phase-exact relative-phase comparator-carry implementation](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) had 32 logical source qubits and 25 clean auxiliaries, with exact quantum emitted operator output phase+1 on 42,672 comparator, 1,584 modular-addition and 128 complete six-bit controlled-modular-multiplier cases per public base. At fixed Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, IBM Fez authenticated target CPU compilation, opt1 and transpiler seed8776, it used base2 **CZ9,263/depth21,772** and cube8 **CZ9,426/depth21,933**. Original independently audited JSON receipts remain at `results/ibm_shor35_relative_phase_ripple/`.

A later [single-CX public OR-carry rewrite](QRR_N35_OR_CARRY_MINIMIZATION_MULTI_SEED_RESULT.md) cut source CX in an OR carry by one per compute pass, showing **8/8 CZ wins per base** across matched seeds, BUT cube8 had only **5/8 joint CZ+depth wins** and therefore FAILED the frozen two-base robust gate. At seed8776 its native compiler counts were base2 **CZ8,311/depth19,981** and cube8 **CZ9,141/depth21,528**. That independent original eight-seed experiment is preserved unchanged under `results/ibm_shor35_or_carry_multi_seed/`. Earlier [active cached-latch multi-seed](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) was similarly not two-base robust. We did NOT use a favorable earlier active-only seed, neither an unproven arithmetic rewrite nor a changed device gate as a baseline.

**This experiment's preregistration** [`QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_PREREG.md`](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_PREREG.md), git commit **`7aa1940b277e895e93932a45a119a6bd28a3d630`**, was frozen BEFORE new compilation. It requires exactly two public bases a2/cube8, one fixed new comparator design, the **eight historical integer seeds** `[11,37,101,409,8776,12011,20261,45673]`, all native costs paired against **both original and previous one-CX OR** in the SAME target snapshot, 3 circuit arms×8 seeds×2 public bases=**48 actual CPU-native compilations**, and original source complex-phase proof before target read. **Preregistered primary robust gate:** for BOTH bases ≥6/8 **joint** strictly lower CZ and strictly lower depth **vs the previous one-CX OR comparator**, both paired medians negative, full quantum phase exactness and both old & OR frozen seed8776 numeric anchors reproducible. Secondary vs original is recorded without replacing primary; separate hardware feasibility **CZ≤800 and depth≤2000**, no QPU authorized.

## Exactly one new public Boolean OR carry lowering — De Morgan complement

Old comparator for each noninitial public 1-bit of the complement threshold requires temporary carry `cur = source_bit OR earlier_carry`. The previously validated one-CX version used `cur XOR=prev; cur XOR=(source AND NOT prev)` with one CX, two temporary X and one relative-phase RCCX per compute step.

The NEW fixed circuit uses the **De Morgan** bit identity `(source OR prev) = 1 XOR ((NOT source) AND (NOT prev))`, on an initially zero temporary carry:

```python
# Temporary carry COMPUTE for publicly known comparator constant bit 1:
qc.x(cur)
qc.x(source); qc.x(prev)
qc.append(RCCXGate(), [source, prev, cur])
qc.x(prev); qc.x(source)

# ... keep the original true semantic flag controlled operation ...

# Temporary carry UNCOMPUTE in exact reverse order:
qc.x(source); qc.x(prev)
qc.append(RCCXGate().inverse(), [source, prev, cur])
qc.x(prev); qc.x(source)
qc.x(cur)
```

There are **zero source CX** in the public OR step's compute or uncompute. Compared with the immediately previous one-CX OR form, this saves **two source CX per full compute/uncompute OR step** and adds six literal public X gates; true RCCX and exact CCX source counts are unchanged. All other conditional arithmetic, exact semantic output target flips, temporary RCCX carry-inverse logic on public 0-bits, comparison polarity, public power-of-two threshold shortening, fixed-constant prefix adder, cached enable/active conditions, work/acc SWAP, inverse weighted uncomputation, qubits and 25 helper reset obligations remain unchanged.

The new [original source `hardware/qrr_n35_demorgan_zero_cx_or_multiseed.py`](../hardware/qrr_n35_demorgan_zero_cx_or_multiseed.py) constructs three independently identifiable original/one-CX/new Qiskit circuits before ANY target access. It validates exactly the public OR truth identity on all **4** Boolean cases and checks the **actual Qiskit complex RCCX inverse operator matrix**. Crucially, RCCX is not equivalent to CCX as a quantum unitary. It is used ONLY for coherent temporary carry work and its actual inverse for cleanup; correctness is established from the actual emitted gate-matrix interpretation, not assumed from Boolean algebra alone.

## Direct original emitted quantum operator and ancilla proof, completed BEFORE every compiler job

Each of the **two independent public-base source jobs** passed:

- **4/4** OR Boolean identity cases, plus actual 8×8 RCCX inverse/forward operator product equals identity.
- **42,672/42,672** ACTUAL Qiskit-emitted X/CX/CCX/RCCX complex-phase comparator basis cases for widths1..6, EVERY public threshold, both `geq` and `lt`, controls disabled/enabled, initial flags0/1 and every x. Source x/control unchanged, semantic predicate flag correct, every carry/scratch qubit zero, final complete quantum phase **+1**.
- **1,584/1,584** actual emitted quantum-phase modulo35 conditional constant-add cases for 16 independent public constants ×35 valid enabled plus64 arbitrary disabled residue values, all flags/carry/scratch clean and exact output **+1**.
- **128/128** controlled full 6-bit multiplier cases for EACH of the 3 circuits per base (384 full cases per base), all work y0..63 ×control0/1, public `a*y mod35` if valid and enabled and identity if control0 or invalid y>=35, every one of **25 auxiliary qubits returned zero**, phase bit preserved and final quantum complex phase **+1**. Thus the complete ideal mapping on clean-input basis states extends coherently to their superpositions (not measured noisy-device fidelity).
- **Source change actually exercised:** base2 had **171** public OR steps, old one-CX CX691/X712 to NEW De Morgan **CX349/X1738**, same RCCX596 and exact CCX160; cube8 **180** steps, old one-CX CX717/X748 to new **CX357/X1828**, same RCCX616/exact CCX162. Original and new all had identical **32 logical qubits** and 25 clean helper qubits. No alternative constant-specific input selection.

## Every one of eight matched seeds — do not postselect

The native costs below are `CZ / depth`. Each triplet was locally compiled against the SAME authenticated Fez target object, SAME Qiskit SDK/opt1, SAME seed, in strict original→oneCX→DeMorgan order. Matched negative differences `DeMorgan - comparison` are improvements. Original seed8776 baselines for BOTH controls reproduced precisely. This is a controlled compiler experiment, not simulated qubit fidelity, hardware timing or quantum runtime.

### Public base2 (N35 single controlled multiplier)

| Seed | Original CZ/depth | Previous one-CX OR CZ/depth | NEW De Morgan CZ/depth | ΔCZ vs one-CX | Δdepth vs one-CX |
|---:|---:|---:|---:|---:|---:|
| 11 | 8,774 / 20,129 | 8,532 / 20,683 | **8,214 / 19,400** | −318 | −1,283 |
| 37 | 8,856 / 20,523 | 8,606 / 20,913 | **8,298 / 19,708** | −308 | −1,205 |
| 101 | 9,125 / 21,276 | 8,340 / 20,193 | **8,026 / 18,965** | −314 | −1,228 |
| 409 | 8,953 / 20,627 | 8,685 / 20,547 | **8,367 / 19,244** | −318 | −1,303 |
| **8,776** | **9,263 / 21,772** | **8,311 / 19,981** | **7,993 / 18,604** | **−318** | **−1,377** |
| 12,011 | 9,034 / 20,977 | 8,691 / 20,798 | **8,379 / 19,559** | −312 | −1,239 |
| 20,261 | 9,255 / 21,719 | 8,880 / 21,060 | **8,562 / 19,775** | −318 | −1,285 |
| 45,673 | 9,288 / 21,476 | 8,542 / 20,502 | **8,224 / 19,261** | −318 | −1,241 |

**Base2 both-resource wins: 8/8 vs previous one-CX, 8/8 vs original.** Median paired vs one-CX **ΔCZ −318, Δdepth −1,262**; ALL eight CZ and depth changes strictly negative, min/max ΔCZ −318..−308, depth −1,377..−1,205. Median vs original **ΔCZ −674, Δdepth −1,681**, 8/8 joint wins. At historical seed8776 vs old original 9,263→7,993 CZ (**−13.71%**) / depth21,772→18,604 (**−14.55%**); vs previous one-CX 8,311→7,993 (**−3.83%**) / depth19,981→18,604 (**−6.89%**).

### Public cubic base8 (N35 single controlled multiplier)

| Seed | Original CZ/depth | Previous one-CX OR CZ/depth | NEW De Morgan CZ/depth | ΔCZ vs one-CX | Δdepth vs one-CX |
|---:|---:|---:|---:|---:|---:|
| 11 | 8,908 / 21,194 | 8,907 / 21,042 | **8,629 / 20,313** | −278 | −729 |
| 37 | 9,290 / 21,648 | 8,624 / 20,964 | **8,601 / 20,292** | −23 | −672 |
| 101 | 9,232 / 21,288 | 8,963 / 21,548 | **8,639 / 20,262** | −324 | −1,286 |
| 409 | 9,281 / 21,510 | 8,550 / 21,003 | **8,222 / 19,715** | −328 | −1,288 |
| **8,776** | **9,426 / 21,933** | **9,141 / 21,528** | **8,758 / 20,575** | **−383** | **−953** |
| 12,011 | 9,279 / 22,085 | 8,739 / 21,359 | **8,415 / 20,069** | −324 | −1,290 |
| 20,261 | 9,176 / 21,398 | 9,048 / 22,035 | **8,720 / 20,718** | −328 | −1,317 |
| 45,673 | 9,178 / 21,952 | 8,915 / 22,286 | **8,585 / 20,964** | −330 | −1,322 |

**Cube8 both-resource wins: 8/8 vs previous one-CX, 8/8 vs original.** Median paired vs one-CX **ΔCZ −326, Δdepth −1,287**, ranges CZ −383..−23 (the small −23 case is preserved), depth −1,322..−672. Median vs original **ΔCZ −630.5, Δdepth −1,191**, 8/8 joint wins. At seed8776 vs old original 9,426→8,758 CZ (**−7.09%**) / depth21,933→20,575 (**−6.19%**); vs previous one-CX CZ9,141→8,758 (**−4.19%**) / depth21,528→20,575 (**−4.43%**). Even with broad fixed-seed savings these are still native **compiled counts** only.

## True original experiment, post-compilation audit typo, and independent permanent verification

[Original 48-native-compilation source run **39096222447**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39096222447) ran the exact 2 base ×8 seeds×3 candidates CPU-only science, all original source emitted-phase tests and **all 48 compilations completed SUCCESSFULLY** in the experiment steps; each original JSON explicitly reports `status=COMPILE_SUCCESS`. Both source-run GitHub jobs have overall **FAILURE** because a strictly downstream audit incorrectly looked for dictionary key `demorgan_zero_cx_full_multiplier_phase_proof` even though the original receipt correctly stored `demorgan_full_multiplier_phase_proof`. It is an auditor field-name error AFTER all science and numeric results were written, **not** failed phase semantics, compiler exception, omitted seed, a source mismatch or physical hardware job. Do not hide the original CI failure or silently rerun science to get a green badge; no experimental gate/seed/target was changed.

The separate [independent ORIGINAL-artifact audit and unchanged-result archival workflow **39096402446**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39096402446) completed **SUCCESS**. It downloaded both original source-run JSON receipts directly via GitHub Actions artifacts, WITHOUT rescoring or recompiling; independently checked every 48 gate/depth metric against the earlier source-run OR and original eight-seed receipts, exact original historical seed8776 anchors, all source gate distributions, 4 Boolean/42,672 comparator/1,584 modadd/3×128 full exact quantum +1 gate checks per base, frozen 8/8 joint win counting and paired medians, all 24 per-base native circuits above physical cutoffs and zero QPU job use. It committed ORIGINAL unchanged raw JSONs:

- [Full original base2 eight-seed/three-arm JSON](../results/ibm_shor35_demorgan_zero_cx_or/qrr_n35_demorgan_zero_cx_base2.json)
- [Full original cubic-base8 eight-seed/three-arm JSON](../results/ibm_shor35_demorgan_zero_cx_or/qrr_n35_demorgan_zero_cx_base8.json)

These receipts preserve all costs, native opcode distributions, times, source phase checks, disfavored seeds and failures for reproducibility.

## Interpretation, frozen verdicts and next gate

**Predeclared ROBUST ENGINEERING PASS FOR BOTH BASES**: exactly 8/8 joint native CZ+depth improvements vs the stronger previous one-CX comparator and also 8/8 vs original, all direct complex output phase proofs pass, all 32 logical source qubits/25 clean helpers unchanged, both seed8776 anchors reproduced. This is the **first tested OR-carry implementation here with 8/8 joint two-base wins** across these fixed eight transpiler seeds under one Fez target/Qiskit SDK snapshot. The source does have **many more X gates** than one-CX OR; do not infer that X-count reductions or generic backend/seed-independent device fidelity improved. No multi-backend calibration stability or larger modulus asymptotic cost was measured.

**FROZEN PHYSICAL DEVICE PREFLIGHT STILL FAILS for ALL 48 compiled circuits**: even lowest new base2 **CZ7,993/depth18,604** at seed8776 is roughly **9.99× CZ** and **9.30× depth** the immutable N35 heuristic CZ≤800/depth≤2000 *for ONLY one modular multiplier*. The lowest observed base2 CZ across eight seeds is 7,993, but different seeds may have lower depth; no physical trial is authorized and **ZERO QPU jobs, free or paid Runtime consumed**. This is not a complete four-round Shor circuit, measured period-factor recovery on N35 or RSA/ML-KEM capability.

**Recommended next move:** freeze a new matched multi-seed research step exploiting the De Morgan comparator as a strong common robust baseline, or compare the absolute cost of public `-35` modular correction and controlled work↔acc arithmetic under 32-qubit full-residue exact phase semantics. Preserve all historical positive, mixed and negative controls (including the real N15 Open Plan phase recycling pilot) without overstating quantum computational advantage or relaxing physical preflight thresholds.
