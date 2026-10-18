# VERIFIED ROBUST PASS — N35 public one-bit carry bypass saves native CZ and depth at 8/8 base2 and 7/8 cubic8 matched seeds; full quantum-phase correctness, ZERO QPU

**Original research lead: Chase Lunsford / CaMaLabs.** **Experimental date:** October 17 Pacific / October 18 UTC, 2026. **Scientific scope:** ONE fully reversible, full-six-bit public N35 controlled modular multiplication for each public base a2 and cube a³8, never complete Shor quantum phase estimation, actual real-QPU N35 factoring, RSA-scale attack, new theorem or device performance/fidelity measurement. The IBM Fez hardware BACKEND TARGET was authenticated/read only for local CPU transpilation. **No real quantum shots, quantum device jobs, free/Open or paid IBM Runtime were used.**

## Exact scientific history and why this is the correct baseline

The independently verified [relative-phase temporary comparator carry](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) replaced CCX by quantum-phase-aware RCCX and its actual adjoint inside *temporary comparator carry calculation*, preserving all public modular arithmetic, all 25 cleaned helpers, and final ideal complex phase exactly +1. Later [active-only RCCX cache latch eight-seed work](QRR_N35_ACTIVE_ONLY_MULTI_SEED_PLACEMENT_RESULT.md) showed why single favorable compiler seeds are NOT robust: only 5/8 joint CZ/depth wins for base2, 1/8 for cube8. [De Morgan public zero-CNOT OR-carry synthesis](QRR_N35_DEMORGAN_OR_CARRY_EIGHT_SEED_RESULT.md) subsequently became the strongest separately proven **two-base eight-seed-robust comparator**, with 8/8 matched source-native CZ AND depth wins on each base versus its earlier one-CX OR comparator. This is the **frozen old reference** in the present new experiment, not a deliberately weak original or a postselected circuit.

De Morgan prior original seed8776 baseline: **base2 7993 native CZ, native depth18604**, **cube8 8758 native CZ, depth20575**, 32 source logical qubits with **all 25 auxiliaries returned zero**, public multiplier defined on all six-bit work residues y0..63, identity on invalid work y≥35 or control0. Every source gate's Qiskit complex `Operator` was interpreted on the full relevant computational-basis inputs to require exact final phase +1; QPU/noise fidelity not inferred. Original De Morgan JSONs at `results/ibm_shor35_demorgan_zero_cx_or/` remain unmodified.

A later [De Morgan+active-only relative-phase cache experiment](QRR_N35_DEMORGAN_ACTIVE_LATCH_MATCHED_RESULT.md) failed the strict two-base 8-seed robust gate (3/8 joint wins base2 and 5/8 cube8), despite a very favorable isolated cube8 seed8776. **Do not use that postselected seed as the old reference**.

## Frozen protocol, one intervention and predicted source changes

[Original preregistration `QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_PREREG.md`](QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_PREREG.md), git commit **`57d884d65a9c425794ee7fd6459afc54213d0224`**, was committed **before ANY new native score**. The protocol froze the source identity, 32 logical qubits, 25 clean auxiliary qubits, both public bases, all exact emitted operator phase proofs, exact 8 transpiler seeds **[11,37,101,409,8776,12011,20261,45673]**, Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47.0, `ibm_fez` READ-ONLY target, opt1, identical source old/new target and seed **within every pair**, original De Morgan 8776 native baseline controls, the 6/8 two-metric joint win criterion and strict immutable no-QPU native **CZ≤800 AND depth≤2000** heuristic. No seed/layout parameter search or favorite-seed selection after result.

New source [`hardware/qrr_n35_public_one_bit_carry_bypass_multiseed.py`](../hardware/qrr_n35_public_one_bit_carry_bypass_multiseed.py) imports the untouched De Morgan OR-carry predicate, original `best.optimized_modadd`, existing prefix-carry public constant addition, cached active+enable CCX controls, work/acc controlled swaps and clean modular inverse uncomputation. It changes ONLY **one public-constant carry-comparison special case** inside the add-constant operation on a descending output bit j:

- For `+v mod64`, the carry into bit j from the **STILL UNCHANGED lower j input bits** is `[x_low_j >= 2^j - (v mod2^j)]`. If and only if the known public low j bits of v are EXACTLY `2^(j-1)`, the threshold is `2^(j-1)` and the comparator is simply the ORIGINAL source bit `x[j-1]`. Thus the operation can directly toggle bit j using the unchanged **exact semantic** `primitive.multi_x(controls + [x[j-1]], bit_j, chain)`; no temporary comparator carry qubit computation is required. This is valid for arbitrary lower x values, without knowing outputs, order, subgroup or private factors.
- All other cases use the unmodified De Morgan-carry `best.public_threshold_predicate` and all external source-enable/wrap controls are unchanged. The updated arithmetic returns all old clean carry/scratch registers and all 25 application ancillas to zero, preserves the control and implements the same complete reversible transformation on all 64 work residues.
- The public identity was separately exhaustively verified across all 64 possible six-bit public constants v, j1..5 and all lower source values for every matching threshold, totaling **320/320 checked low-input cases**, before target compilation.
- The source original and new are independently built and quantum-phase verified BEFORE any backend read. Exactly **23 actual carry comparator bypasses per complete multiplier, eliminating 46 CX source gates for BOTH public bases**, with **source RCCX, exact CCX and X unchanged**. This is a genuine source circuit simplification, not a new qubit, a classical truth-table oracle or a known-order shortcut.

| ACTUAL emitted source Qiskit gates, ONE multiplier | Old De Morgan base2 | NEW base2 | Old cube8 | NEW cube8 |
|---|---:|---:|---:|---:|
| CX | 349 | **303** | 357 | **311** |
| Phase-relative RCCX | 596 | 596 | 616 | 616 |
| Exact CCX | 160 | 160 | 162 | 162 |
| X | 1738 | 1738 | 1828 | 1828 |
| Application qubits | 32 | 32 | 32 | 32 |
| Clean auxiliaries | 25 | 25 | 25 | 25 |

## Rigorous actual quantum-source verification — all PASS

Every emitted source instruction is interpreted using its actual Qiskit `Operator(inst.operation)` monomial complex matrix; each computational basis initial input must yield the correct semantic public result, unchanged control, every helper zero and **exact output complex phase +1** (not merely matching classical bits). Thus the stated ideal coherent action extends by linearity to superpositions on the **tested initially-clean auxiliary input subspace**, not experimental fidelity on a noisy device.

The TWO independent base jobs EACH passed **BEFORE first Fez backend read**:

1. **320/320** public constant arithmetic bit-comparison identities, across possible public constants and low-register inputs;
2. **4/4** Boolean De Morgan OR identities and actual Qiskit `RCCX.inverse() * RCCX = I` operator matrix check;
3. **42,672/42,672** unsigned comparator emitted-gate phase-sensitive cases across all widths1..6, thresholds, geq/lt, enable0/1, initial flag0/1, x values; all carry/scratch zero and exact complex phase+1;
4. **1,584/1,584** modulo35 constant-addition actual emitted gate cases **for original** AND **1,584/1,584 for new**, all sixteen distinct public weighted constants, 35 enabled valid and64 disabled arbitrary six-bit target values per constant; all wrap/carry/scratch reset and phase+1;
5. **128/128** full public controlled multiplier on all control×y six-bit states **for original** AND **128/128 for new**; all 25 helper bits clean, exact controlled public output on valid y, identity when disabled/invalid, output phase exactly +1;
6. Original-to-candidate FULL source gate count must match precisely the frozen **23 bypasses, −46 CX, +0 RCCX, +0 CCX, +0 X and 32 logical**.

These gates test **two variants separately**, including the old control and the single changed arithmetic method. A seed affects only the later CPU transpilation; it cannot be an excuse to alter circuit source semantics.

## Exact eight matched placement seed results — preserving even regressions

Each metric is native **CZ / compiled depth**; delta is candidate MINUS original **for the SAME seed**, so negative values mean improvement. These 32 compiles are native-resource proxies, NOT physical IBM quantum runs, fidelity, QPU wall time or observed Shor factor yield.

### N35 public base2, exactly ONE controlled multiplier

| Seed | Original De Morgan CZ/depth | NEW bypass CZ/depth | ΔCZ | Δdepth | BOTH better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,214 / 19,400 | **7,932 / 18,529** | −282 | −871 | YES |
| 37 | 8,298 / 19,708 | **7,875 / 18,757** | −423 | −951 | YES |
| 101 | 8,026 / 18,965 | **7,955 / 18,618** | −71 | −347 | YES |
| 409 | 8,367 / 19,244 | **7,676 / 18,220** | −691 | −1,024 | YES |
| **8,776** | **7,993 / 18,604** | **7,887 / 18,221** | −106 | −383 | YES |
| 12,011 | 8,379 / 19,559 | **7,737 / 18,413** | −642 | −1,146 | YES |
| 20,261 | 8,562 / 19,775 | **7,744 / 18,497** | −818 | −1,278 | YES |
| 45,673 | 8,224 / 19,261 | **8,135 / 19,192** | −89 | −69 | YES |

**Base2 8/8 joint lower CZ AND depth wins**, 8/8 each metric. Median *paired* **ΔCZ −352.5**, median **Δdepth −911**; range CZ **−818..−71**, depth **−1278..−69**. Original seed8776 anchor 7993/18604 EXACT reproduced, NEW at seed8776 7887/18221, modest **−1.33% CZ, −2.06% depth** for that seed. Best new absolute native base2 sample CZ7676/depth18220 at seed409 is NOT chosen as a new default layout, merely included with all eight. **Frozen per-base robust engineering PASS.**

### N35 public cubic base8, exactly ONE controlled multiplier

| Seed | Original De Morgan CZ/depth | NEW bypass CZ/depth | ΔCZ | Δdepth | BOTH better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | 8,629 / 20,313 | **8,242 / 18,553** | −387 | −1,760 | YES |
| 37 | 8,601 / 20,292 | **8,321 / 19,496** | −280 | −796 | YES |
| 101 | 8,639 / 20,262 | **7,604 / 18,627** | −1,035 | −1,635 | YES |
| 409 | 8,222 / 19,715 | **8,156 / 19,775** | **−66** | **+60** | **NO (depth regression)** |
| **8,776** | **8,758 / 20,575** | **7,802 / 18,449** | −956 | −2,126 | YES |
| 12,011 | 8,415 / 20,069 | **8,137 / 18,982** | −278 | −1,087 | YES |
| 20,261 | 8,720 / 20,718 | **8,328 / 19,457** | −392 | −1,261 | YES |
| 45,673 | 8,585 / 20,964 | **8,290 / 19,122** | −295 | −1,842 | YES |

**Cubic8 7/8 joint CZ+depth wins**, 8/8 CZ-only and 7/8 depth-only. Median paired **ΔCZ −341**, median **Δdepth −1448**; CZ range **−1035..−66**, depth **−2126..+60**. Frozen baseline seed8776 8758/20575 EXACT reproduced, NEW 7802/18449 (−10.92% native CZ and −10.33% depth at this single seed). **Honest exception:** seed409 CZ still improves 8222→8156 but depth gets WORSE 19715→19775 (+60), hence not 8/8 joint wins; **preregistered 6/8 threshold nevertheless passes with 7/8.** Best observed candidate CZ7604/depth18627 at seed101 is recorded but NOT a selected new optimized seed after the fact.

### Frozen decisions

**Strong two-base architecture engineering PASS:** base2 **8/8 joint wins**, cube8 **7/8 joint wins** against our strongest verified robust De Morgan source baseline, both median paired CZ and depth negative, exact historical 8776 source anchors, all 32 native CPU compiler cases and ALL strict complex-phase/clean-helper source proofs pass. This is especially credible given the prior multiple correctly preserved single-seed and multi-seed compiler regressions/null ablations in this repository. **It does not imply a general asymptotic new quantum arithmetic algorithm or a quantum speedup**, only the source-gate and compiler-level benefit for full-register public N35 under these fixed settings.

**Immutable physical preflight FAIL (every one of 32 native target circuits):** best new CZ count 7604 on cubic8 seed101 and 7676 on base2 seed409, both still **over 9× the 800-CZ proxy cutoff**; lowest new depth18220 on base2 and18449 on cubic8 are still **over 9× the 2000-depth proxy cutoff**, for only ONE controlled multiplier before QPE control rounds. **No IBM QPU submissions, shots, free Open Plan or paid Runtime.** No actual N35 factor recovery, full 4-stage public cubic order reduction demonstration on QPU, RSA/ML-KEM advantage or physical hardware reliability claim.

## Original source artifacts, independent audit, and reproducibility

[Original 2/2 source experiment **39105116012**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39105116012) **SUCCESS**, both jobs passed all actual gate phase checks, all 32 native CPU compiler jobs and internal postcompile audits. [Independent original source-artifact receipt audit and permanence workflow **39105265764**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39105265764) **SUCCESS**, downloaded the two ORIGINAL source-run JSON artifacts without any new arithmetic or compiler calculations, independently rechecked the full 32 *exact original* native CZ/depth counts, every complex quantum phase/clean-ancilla proof receipt, historical anchor, 23/46 source intervention, metrics distributions, real-device gate and zero-QPU indicators, then byte-preserved original source experiment JSONs:

- [Public base2 original eight-seed JSON](../results/ibm_shor35_one_bit_carry_bypass_multiseed/qrr_n35_one_bit_carry_bypass_base2.json)
- [Public cubic base8 original eight-seed JSON](../results/ibm_shor35_one_bit_carry_bypass_multiseed/qrr_n35_one_bit_carry_bypass_base8.json)

All authentic original source/result/protocol files are independently cited above and original strong De Morgan previous-run receipts remain unmodified.

## Next best direction, with controls

The large per-seed variability—even after removing identical 46 CX on each base—supports keeping the exact matched eight-seed gate for future source changes. Further investigate publicly constant-specific target-gate collapsing or branch-to-constant fused modular correction with exact actual quantum amplitudes and clean helpers, but preregister BEFORE scoring; never switch to favorable seeds or weaker initial ripple baselines. The previous actual real IBM N15 Open Plan recycled phase-qubit experiment remains a separate legitimate milestone. Do not consider real QPU N35 use until a future accurate full Shor/QPE assembly and feasible native gate preflight, with separately verified active Open Plan authorization.
