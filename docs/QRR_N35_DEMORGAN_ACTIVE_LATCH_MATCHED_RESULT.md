# VERIFIED NEGATIVE COMBINATION — De Morgan zero-CX plus phase-exact active cache latch is NOT eight-seed robust (3/8 base2; 5/8 cube8)

**Lead / origin:** Chase Lunsford / CaMaLabs. Original experiment October 17 Pacific / October 18 UTC 2026. **ZERO real IBM Fez QPU jobs, zero shots, zero Open/free or paid Quantum Runtime.** All gate cost results are Qiskit CPU compile to authenticated read-only IBM Fez hardware ISA TARGET, `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, `optimization_level=1`. One full six-bit public N35 controlled modular multiply per base (a2 or cubic a8), NOT a full four-phase-bit Shor circuit or quantum advantage.

## Frozen prior, motivation and precise single change

The independently verified [public De Morgan zero-CNOT OR carry](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) improved native CZ AND depth for BOTH N35 bases in **all 8/8 matched seeds** versus the previously established one-CNOT comparator. This is our *strongest publicly documented two-base robust* N35 arithmetic comparator. Its original native seed8776 a2 **CZ7993 / depth18604**, cube8 **CZ8758 / depth20575**. Actual Qiskit-source quantum-phase (not Boolean-only) proof passed, 32 source logical qubits, every25 auxiliary clean. Original immutable prior results `results/ibm_shor35_demorgan_zero_cx_or/qrr_n35_demorgan_zero_cx_base{2,8}.json`.

A separate `active_only` RCCX cached-control latch had previously shown isolated favorable outcomes on an OLDER ripple comparator, but [strict previous 8-seed two-base robustness](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) failed (5/8 and1/8 joint wins). We hypothesized it might behave differently on the much stronger De Morgan comparator. The [preregistration](QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_PREREG.md), original commit **`47a6a1d80b704df7469795127f2c9ba69fffdae9`**, froze ONE change (two actual active cache latch CCX→RCCX+adjoint), exact eight seeds `[11,37,101,409,8776,12011,20261,45673]`, both public bases, all quantum source semantics, and strict robust **≥6/8 seeds with BOTH CZ and depth strictly lower plus negative paired medians on BOTH public bases**, original 8776 anchors exact, before any new target compiler scores.

The candidate [`hardware/qrr_n35_demorgan_active_latch_matched_seeds.py`](../hardware/qrr_n35_demorgan_active_latch_matched_seeds.py) explicitly sets the already verified `primitive.predicate = demorgan.demorgan_ripple_predicate`, constructs baseline from `previous.verified.build(base)`, candidate from previously verified `family.build_variant(base,"active_only")` with the **SAME** De Morgan comparator source. The ONLY changed source gates are original exact 2 `CCX(phase,valid;active)` forward/back replaced by `RCCX` and actual operator adjoint. All 24 temporary `enable` latch CCX remain exact; all public prefix-carry addition, modular correction, validity, work/acc swap, inverse cleanup, full residue behavior, clean helpers and semantic target flips unchanged. No source multiplicative order, prime factors, 12-state orbit or lookup table. Both 32 application logical qubits, 25 clean helpers.

**Actual source gate distribution:** base2 baseline **CX349/RCCX596/X1738/exact CCX160** → active-only **CX349/RCCX598/X1738/CCX158**. Cubic base8 baseline **CX357/RCCX616/X1828/CCX162** → active-only **CX357/RCCX618/X1828/CCX160**. These precisely confirm the new gate placement actually exercises the intended phase-relative operation; no null intervention.

## Quantum-phase and clean-register proofs before any target compilation

For each public base, before reading the IBM Fez backend target, the program passed:

- **4/4** public De Morgan OR Boolean identities and verified the actual Qiskit RCCX/adjoint matrix product is identity;
- **8/8** independent local relative-phase active cached latch/unlatch controlled-probe source gate unitary tests, exact complex phase+1 and clean helper;
- **42,672/42,672** independent Qiskit-emitted De Morgan comparator quantum monomial-amplitude gate checks (every width1..6, threshold, geq/lt, external enable, original flag0/1), workspace clean and exact complex amplitude+1;
- **1,584/1,584** public 16-constant modulo35 modular-add quantum gate checks, exact amplitude+1 and scratch zero;
- **128/128** FULL baseline AND **128/128** candidate actual emitted `Operator(inst.operation)` complex-phase gated controlled multiplier checks, all work residues y0..63 times external c0/1, exact intended public controlled multiplication for valid y, identity for disabled or y>=35, all 25 auxiliaries returned ZERO, final output complex phase exactly **+1**. This directly verifies ideal coherent action on the tested initially-clean input subspace by linearity, not physical fidelity on a noisy chip.

Both jobs compiled all eight paired seeds×two source circuits = **32 authentic CPU-native IBM Fez target circuit compilations**, original then active-only, same hardware metadata/optimization1/seed within each pair. Original 8776 anchor EXACTLY reproduced archived De Morgan baseline numeric counts (no historical target drift).

## Every native matched-seed result, including regressions

Each cell is **CZ / depth** for exactly ONE full-register N35 controlled modular multiplier. Delta is candidate active-only MINUS matching De Morgan baseline; **negative=improvement**, **positive=regression**. Do not compare different seeds.

| Seed | Base2 De Morgan CZ/depth | Base2 +active CZ/depth | ΔCZ | Δdepth | Both improve |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,214 / 19,400 | 7,980 / 19,046 | −234 | −354 | YES |
| 37 | 8,298 / 19,708 | 8,256 / 19,374 | −42 | −334 | YES |
| 101 | 8,026 / 18,965 | 8,306 / 19,594 | +280 | +629 | NO |
| 409 | 8,367 / 19,244 | 8,082 / 19,461 | −285 | +217 | NO |
| **8,776** | **7,993 / 18,604** | **8,225 / 19,554** | **+232** | **+950** | **NO** |
| 12,011 | 8,379 / 19,559 | 8,072 / 19,105 | −307 | −454 | YES |
| 20,261 | 8,562 / 19,775 | 8,259 / 19,783 | −303 | +8 | NO |
| 45,673 | 8,224 / 19,261 | 8,458 / 20,035 | +234 | +774 | NO |

**Base2 3/8 joint CZ+depth wins, 5/8 CZ wins and 3/8 depth wins**. Median paired CZ **−138**, median paired depth **+112.5** (WORSE). CZ paired range −307..+280; depth −454..+950. The old 8776 favorable De Morgan design **got WORSE** with the active-only latch (CZ7993→8225, depth18604→19554). Predeclared base2 robust gate **FAIL**.

| Seed | Public cube8 De Morgan CZ/depth | Cube8 +active CZ/depth | ΔCZ | Δdepth | Both improve |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,629 / 20,313 | 8,487 / 20,497 | −142 | +184 | NO |
| 37 | 8,601 / 20,292 | 8,481 / 20,118 | −120 | −174 | YES |
| 101 | 8,639 / 20,262 | 8,793 / 20,503 | +154 | +241 | NO |
| 409 | 8,222 / 19,715 | 8,692 / 20,795 | +470 | +1,080 | NO |
| **8,776** | **8,758 / 20,575** | **8,036 / 19,202** | **−722** | **−1,373** | **YES** |
| 12,011 | 8,415 / 20,069 | 8,221 / 19,485 | −194 | −584 | YES |
| 20,261 | 8,720 / 20,718 | 8,459 / 19,859 | −261 | −859 | YES |
| 45,673 | 8,585 / 20,964 | 8,499 / 19,835 | −86 | −1,129 | YES |

**Cubic8 5/8 joint wins**, 6/8 CZ wins and 5/8 depth wins; median paired CZ **−131**, depth **−379**, paired CZ range −722..+470, depth −1373..+1080. Strong favorable seed8776 improvement cube8 CZ8758→**8036** and depth20575→**19202** does **NOT** clear frozen 6/8 joint wins, because seeds11,101,409 regress one or both. Predeclared cube8 robust gate **FAIL**, not an unconditional new best two-base design.

**Predeclared TWO-BASE robust engineering gate FAILED BOTH arms**; although median CZ improves both and cubic median depth improves, base2 median depth worsens and each base has too few joint wins. **Keep the original De Morgan-only comparator as the preferred independently robust two-base architecture** (8/8 matched joint improvements against older oneCX on both public bases), and preserve the isolated favorable cube8 seed 8776 as a conditional metric without promoting it as general quantum hardware speedup.

## True original source-run provenance and independent original-result preservation

[Original 2/2 experiment CI **39100095129**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39100095129) **SUCCESS**, all phase-sensitive source tests, all 32 native CPU compiler jobs, self-audit, original artifact uploads. [Independent original artifact audit/byte preservation CI **39100203559**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39100203559) **SUCCESS**, retrieved original experiment artifacts **without rerunning or reoptimizing science**, independently checked every exact 8-seed native CZ/depth output, every phase+1 clean-register proof, correct source operator count replacement, strict historical 8776 baseline, full signed deltas/median and FAILED 6/8 gate, hardware device criterion and zero runtime, then committed untouched source JSON receipts:

- [Original base2 8-seed De Morgan+active JSON](../results/ibm_shor35_demorgan_active_only/qrr_n35_demorgan_active_only_base2.json)
- [Original cube8 8-seed De Morgan+active JSON](../results/ibm_shor35_demorgan_active_only/qrr_n35_demorgan_active_only_base8.json)

**Immutable device feasibility remains FAILED for all 32 compiles:** native CZ thousands, depth tens of thousands vs frozen **CZ≤800 AND depth≤2000** (for just ONE multiplier, not full four-round QPE), no physical quantum processor job or runtime. Original real IBM Fez N15 Open Plan recycled phase-qubit pilot remains a separate genuine tiny factoring milestone; none of this N35 study demonstrates cubic order reduction or factor recovery on real QPU.

## Next grounded direction

The new phase-exact algebraic De Morgan OR carry remains the dependable common baseline, while further relative-phase cached controls should NOT be assumed beneficial on the basis of one placement. A better next test could isolate a new public-constant-specific correction strategy or examine deeper native layout sensitivity of full multi-round order-finding once single-modmul feasibility plausibly improves. Every new result must be preregistered, phase+1 and clean-aux proved, tested on the same **both public bases across multiple matched seeds**, and keep strict real-QPU hardware preflight and zero paid runtime.
