# VERIFIED TWO-BASE ROBUST ENGINEERING WIN — N35 public source-cost sign selector: 8/8 paired CZ and depth wins on BOTH bases

**Research lead / attribution: Chase Lunsford / CaMaLabs.** Research October 19 PDT / October 20 UTC, 2026. These are read-only IBM Fez HARDWARE-TARGET compilations on a CPU for ONE six-bit full-residue controlled modular multiplier, NOT real physical quantum-device execution or a full four-bit Shor factoring circuit. No QPU jobs, shots, Open/free or paid IBM Runtime.

## Scientifically fair historical controls and frozen method

The previously best *two-base robust* source was the [De Morgan comparator and public one-bit carry bypass](QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md): original native Fez seed8776 base2 CZ7887/depth18221 and cube8 CZ7802/depth18449, 32 source qubits/25 clean auxiliaries and exact output complex phase+1, independently preserved raw receipts in results/ibm_shor35_one_bit_carry_bypass_multiseed/. That earlier method passed 8/8 and 7/8 matched paired native improvements against its own prior baseline. The later [signed k>17 correction](QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_RESULT.md) gave base2 8/8 but cube8 only 4/8 joint wins, so that less robust signed version was NOT used as our comparator baseline. Original real IBM Fez Open Plan N15 recycled phase-qubit pilot is independent real hardware work; the N35 public bases remain classically trivial CPU compilations.

[The fixed preregistration](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_PREREG.md) was committed **before new candidate native scores**, original freeze commit **9292116e31aefa6e2309c03a32488835ea55bdeb**. It freezes BOTH public bases a2 and cubic8; exactly eight transpiler seeds [11,37,101,409,8776,12011,20261,45673], Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47, Fez READ-ONLY target, optimization1, original-vs-candidate paired compiled circuits within each seed, 6/8 joint CZ/depth improvement plus negative median gates on BOTH bases, original 8776 anchor, QPU CZ<=800 AND depth<=2000 preflight, no runtime jobs.

## ONE public operation-local source-only method, frozen BEFORE backend READ

[New source script](../hardware/qrr_n35_static_gate_cost_sign_selector.py) builds BOTH mathematically equivalent quantum-phase-aware controlled modulo35 adders for ALL public constants k=1...34 on clean enable1/target6/wrap1/carry6/scratch9 registers:

- Original **positive correction**: compute enabled wrap flag x>=35−k, add +k mod64, conditionally correct −35, uncompute wrap from final output<k.
- Alternative **signed correction**: publicly define d=35−k, compute enabled underflow x<d, subtract d mod64, conditionally correct +35, uncompute flag from final output>=k.
- Both reuse the **same previously verified** one-bit prefix-carry bypass, De Morgan zero-CX relative-phase comparator, exact semantic target gates, full 64-state disabled identity, clean ancillas, and no order/factors/orbit lookup.

For each k it measures ACTUAL emitted SOURCE Qiskit operations, **before any backend compiler access**, and calculates the prespecified proxy S = (#CX)+6*(#CCX)+3*(#RCCX), with X unweighted because it is a two-qubit-cost heuristic. Select signed ONLY if its S is strictly less than original S, ties prefer original. The exact same k-only map is used for BOTH public bases; there is no target compiler, real hardware score, route, experiment outcome, basis input or selected seed in the decision rule. Independent raw 34×2 source gate vectors and score outcomes are preserved verbatim in each original JSON.

**Observed selection from the preregistered score:** ALL odd k =1,3,...,33 select signed; ALL even k=2,4,...,34 select original. This is an observed result of the source gate counts and frozen weights, NOT an independently proven universal parity or cryptographic theorem. Exactly SIX of twelve weighted public additions are signed for base2, SEVEN for cubic8. These weighted constants derive from public base/modulus only, not from an order or precomputed subgroup table.

### Original vs new ACTUAL emitted source gate vectors

| One full six-bit N35 controlled multiplier | Original base2 | New base2 | Original cubic8 | New cubic8 |
|---|---:|---:|---:|---:|
| CX | 303 | **275** | 311 | **284** |
| Relative-phase RCCX | 596 | **520** | 616 | **538** |
| Exact semantic CCX | 160 | **148** | 162 | **151** |
| X | 1738 | **1508** | 1828 | **1528** |
| Application qubits | 32 | 32 | 32 | 32 |
| Clean auxiliaries | 25 | 25 | 25 | 25 |

## Exact Qiskit quantum-complex-phase evidence BEFORE native target access

All checks interpreted the actual Qiskit-emitted X/CX/CCX/RCCX operator matrices as monomial basis permutations with their complex phase factors. They multiplied the amplitude gate-by-gate and required final +1 (not merely Boolean correctness), exact public output, controls unchanged and all helper bits clean. For each public base, all PASSED:

- **3,366/3,366** public underflow/correction identities, ALL 34 k, all35 enabled valid x and64 disabled arbitrary 6-bit x, including flag cleanup.
- **42,672/42,672** actual full public De Morgan comparator emitted gate complex-phase cases over widths1..6, all thresholds, comparator signs, enable values and initial flags, with cleaned temporary carry.
- **6,732/6,732** direct actual operator modular-addition source cases across **34 public constants × BOTH positive and signed implementations ×99 inputs**, every flag/carry/scratch returned zero, final quantum amplitude+1.
- **128/128 original** AND **128/128 new** full controlled modular-multiplier phase-aware source cases per base, all six-bit work y=0...63 ×control0/1, identity for invalid states y>=35 and disabled c0, exact public y*a mod35 for valid enabled inputs, **all 25 auxiliaries cleaned**, exact quantum phase+1.
- Source register width unchanged32. These are ideal quantum-circuit semantic proofs for the tested initially-clean ancillary subspace, NOT physical noisy processor fidelity results.

[Original complete two-base source CI **39367204317**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367204317): **2/2 SUCCESS**, all source quantum operator checks BEFORE Fez target read, eight matched seed pairs per base (32 CPU-native compiler runs total), and original internal source result audits PASS.

## EVERY matched native compilation result — no postselected seed exclusions

Numbers are IBM Fez read-only native target **CZ / compiled depth** for ONE full-residue modular multiplier. Paired delta is candidate MINUS original; negative is an improvement.

| Fixed seed | Base2 original CZ/depth | Base2 new CZ/depth | ΔCZ | Δdepth | Joint gain |
|---:|---:|---:|---:|---:|:---:|
| 11 | 7932 / 18529 | **7393 / 16747** | −539 | −1782 | YES |
| 37 | 7875 / 18757 | **7046 / 16266** | −829 | −2491 | YES |
| 101 | 7955 / 18618 | **7228 / 16211** | −727 | −2407 | YES |
| 409 | 7676 / 18220 | **7003 / 16331** | −673 | −1889 | YES |
| 8776 | 7887 / 18221 | **6871 / 16626** | −1016 | −1595 | YES |
| 12011 | 7737 / 18413 | **7057 / 16004** | −680 | −2409 | YES |
| 20261 | 7744 / 18497 | **7325 / 17043** | −419 | −1454 | YES |
| 45673 | 8135 / 19192 | **6881 / 16125** | −1254 | −3067 | YES |

**Base2 all 8/8 matched CZ+depth joint wins**, median paired CZ delta **−703.5**, depth delta **−2148**; both 8776 original anchor 7887/18221 reproduced. Even least favorable paired CZ −419 and depth −1454 are improvements.

| Fixed seed | Cube8 original CZ/depth | Cube8 new CZ/depth | ΔCZ | Δdepth | Joint gain |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8242 / 18553 | **7254 / 16234** | −988 | −2319 | YES |
| 37 | 8321 / 19496 | **7013 / 16181** | −1308 | −3315 | YES |
| 101 | 7604 / 18627 | **7025 / 16380** | −579 | −2247 | YES |
| 409 | 8156 / 19775 | **7385 / 16865** | −771 | −2910 | YES |
| 8776 | 7802 / 18449 | **7315 / 16286** | −487 | −2163 | YES |
| 12011 | 8137 / 18982 | **7375 / 16619** | −762 | −2363 | YES |
| 20261 | 8328 / 19457 | **7384 / 16500** | −944 | −2957 | YES |
| 45673 | 8290 / 19122 | **7671 / 17700** | −619 | −1422 | YES |

**Cubic base8 all 8/8 matched CZ+depth joint wins**, median paired CZ delta **−766.5**, depth delta **−2341**. Original 8776 anchor cube8 7802/18449 reproduced EXACTLY. Both public bases PASS prereg engineering ≥6/8 joint wins, negative both-metric medians, nonzero source changes and original 8776 controls.

### Familiar seed8776 absolute native resource snapshot

| ONE controlled multiplier, seed8776 | Original base2 | **New base2** | Original cubic8 | **New cubic8** |
|---|---:|---:|---:|---:|
| Native CZ | 7887 | **6871** (−12.88%) | 7802 | **7315** (−6.24%) |
| Native depth | 18221 | **16626** (−8.75%) | 18449 | **16286** (−11.72%) |
| Original/optimized source application qubits | 32 | 32 | 32 | 32 |
| Source result phase +1 and clean25 | PASS | PASS | PASS | PASS |
| Real QPU jobs or charged/free Runtime | 0 | 0 | 0 | 0 |

## Independent preservation of ORIGINAL source artifacts

[Independent original artifact audit/preservation GitHub Actions **39367462324**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367462324): **SUCCESS**. Downloaded the two ORIGINAL JSON source-run artifacts from 39367204317, independently rechecked all 32 exact native CZ/depth/count_ops against genuine source run and unchanged previous eight-seed one-bit bypass results, full 34 public source vector/signed scores and frozen choice conditions, **3,366+42,672+6,732+128+128** complex-source quantum gate proofs per base, exact six/seven signed weighted operation calls, original seed8776 anchors, frozen two-base gate and every failed physical device cutoff; committed unmodified original numerical JSON files without a second arithmetic/target compilation:

- [Original base2 eight-seed JSON, all 34 signed-vs-positive source gates and scores](../results/ibm_shor35_static_gate_sign_selector/qrr_n35_static_sign_selector_base2.json)
- [Original cubic base8 eight-seed JSON, all 34 public choices and eight paired compiles](../results/ibm_shor35_static_gate_sign_selector/qrr_n35_static_sign_selector_base8.json)

Previous positive, negative and null controls, the signed k>17 two-base mixed failure, and the genuine real IBM Fez N15 Open pilot remain separately attributed and unmodified.

## Interpretation and next falsification opportunity

**Fixed eight-seed two-base engineering robustness SUCCESS:** 8/8 paired CZ/depth wins for both bases, with exactly the same preregistered source-only public rule and fixed-target seed cohorts. This is a substantial verifiable ISA compiler optimization, not a new quantum factoring theorem, an RSA attack or an observed quantum hardware result. These eight integer transpiler seeds were already reused in previous N35 optimization studies; a **FRESH independent holdout set of seeds** with the same frozen circuits and a separately captured backend target may be valuable to probe wider placement generalization. Do not update the proxy weights from existing compiler scores.

**Separate immutable real-device preflight STILL FAILS for every one of the 32 compiled old/new circuits**: even the new 6871 CZ/depth16626 and cube8 7315 CZ/depth16286 seed8776 native costs remain roughly 8–9 times the **CZ≤800 and depth≤2000** thresholds for ONE multiplier, before combining full four-round QPE. **ZERO actual IBM QPU jobs, free quantum Runtime or paid Runtime.** No real N35 factor recovery or physical noise fidelity claim. The user must separately authorize any future real QPU, verify current active IBM plan=open and satisfy device feasibility beforehand.
