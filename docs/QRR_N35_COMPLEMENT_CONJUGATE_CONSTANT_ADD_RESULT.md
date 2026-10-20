# VERIFIED NEGATIVE — N35 complement-conjugated constant-add source selection is phase-correct but NOT native Fez seed-robust: 1/8 joint wins per base, zero QPU

**Research lead and original program: Chase Lunsford / CaMaLabs.** Date October 19, 2026 Pacific / October 20 UTC. IBM Fez native **hardware TARGET metadata only** were read; all 36 circuit compilations were CPU-side Qiskit runs, not actual QPU shots, jobs, free Open Plan runtime, paid runtime, quantum device fidelity or Shor factoring. This is **one six-bit full-residue public N=35 controlled modular multiplication per public base a2 and cubic a8**, not four-phase-qubit QPE or cryptographic quantum advantage.

## Correct strong historical comparator and preregistration

The independently audited [static sign-source selector](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md) was the latest **robust** N35 engineering improvement before this experiment: a single public-k source-only choice of positive or signed modular correction based on **S=#CX+6×#CCX+3×#RCCX**, ties positive, original public k=1..34 map (odd signed/even positive) unchanged. [Independent eight FRESH seed holdout](QRR_N35_STATIC_SIGN_FRESH_SEED_HOLDOUT_RESULT.md) preserved strict joint CZ AND depth wins **8/8 base2, 7/8 cubic8**, in addition to 8/8 and 8/8 earlier development seeds. At historical seed8776, **base2 native CZ6871/depth16626; cubic base8 CZ7315/depth16286**, all source phases exact +1, 32 logical application qubits/25 cleaned auxiliaries, full 64-state public residue transformation, identity for disabled or invalid inputs. These original source/results/holdout receipts remain unmodified. Our earlier weak Toffoli, unshortened ripple, De Morgan, signed k>17-only, V-chain null, comparator-minterm regression, etc. are **NOT used as a favorable weaker benchmark**.

The [next experiment preregistration](QRR_N35_COMPLEMENT_CONJUGATE_CONSTANT_ADD_PREREG.md) was committed as **`0c28980f7d507feebcece395cfd17bf63095dee4` BEFORE any new scoring**. Frozen public bases 2 and8, original per-k SIGN selector unchanged; one new INNER public mod64 addition alternative, fixed source proxy S, 8 NEW seeds disjoint from both earlier development and holdout sets, seed8776 separately for exact archived source/target anchor, Qiskit~=2.5.2/runtime~=0.47, IBM Fez read-only target, optimization1; no compiler layout search, no user hardware authorization. **Predeclared robust engineering acceptance:** 6/8 strict paired native CZ and depth reductions with negative both medians **for BOTH public bases**, original anchor exactly reproduces, all quantum-phase correctness and nonzero changed inner-add calls; device feasibility immutable native CZ≤800 AND depth≤2000.

## One new public mod64 adder encoding; no orbit/order shortcuts

New [`hardware/qrr_n35_complement_constant_source_selector.py`](../hardware/qrr_n35_complement_constant_source_selector.py) retains every existing source gate operation *outside* the inner controlled modulo64 constant additions and their already-validated physical layout/source registers. For a public six-bit constant `v`, define bitwise complement `C(x)=63−x`. For every integer x0..63,

`C((C(x) − v) mod64) = (x + v) mod64`.

One candidate adder applies `X` to all six target bits, calls the **UNCHANGED** original one-bit-prefix-carry-bypass `+(-v) mod64` adder with the same external controlled enable and clean carry/scratch, then applies the six `X` operations again in reverse order. The original direct `+v mod64` adder remains untouched. The two encodings are genuinely quantum-phase equivalent on the tested clean-ancilla subspace when their actual Qiskit gate operators are checked; the temporary complement is undone even for disabled controlled source.

Before ever reading the IBM backend, for **each public mod64 v=0..63**, it emits DIRECT and COMPLEMENT-CONJUGATED arithmetic and scores their ACTUAL literal Qiskit source gate counts with the *previously frozen same source-only* proxy **S=CX+6×CCX+3×RCCX** (X unweighted). Choose conjugated iff strictly smaller S; all ties and zero prefer direct. This source decision uses only v and gate structure, not compiler/routing results, seed, prime factors, multiplicative order, known 12-state orbit, full-state truth table, or work-register value. The source selection is identical on both public bases.

**Actual selection (not preregistered as an expected result):** 27 of the 64 public values were cheaper via conjugation: **[15,23,27,28,29,30,31,39,43,44,45,46,47,48,51,52,53,54,55,56,57,58,59,60,61,62,63]**. The complete source score table and original Qiskit source vectors for all 64 constants are byte-preserved in both original result JSONs. The current public weighted full multiplier uses the changed inner adder **12 times base2** (12 unchanged-direct calls) and **10 times cube8** (14 direct); thus the intervention was truly exercised rather than a null no-op. Every other mod35 positive/signed outer correction and source-k map remains exactly as before.

| Actual source full controlled multiplier, 32 qubits | Prior robust base2 | Conjugated-selected base2 | Prior robust cube8 | Conjugated-selected cube8 |
|---|---:|---:|---:|---:|
| Primitive source CX | **275** | **255** | **284** | **267** |
| Primitive source RCCX | 520 | 520 | 538 | 538 |
| Primitive source exact CCX | 148 | 148 | 151 | 151 |
| Source X | 1508 | 1392 | 1528 | 1428 |
| All 25 auxiliary qubits cleaned | yes | **yes** | yes | **yes** |
| Exact complex phase +1 over all 128 inputs | yes | **yes** | yes | **yes** |

This is a valid SOURCE two-qubit-gate reduction of **20 CX** base2, **17 CX** cubic8, even though compiler-level metrics worsen in most matched seeds. A reduction in unweighted X count also occurred, but does not guarantee lower target-native depth.

## Literal quantum-complex-phase emitted-instruction proof before Fez target access

The existing independently audited Qiskit `Operator(inst.operation)` monomial basis/complex amplitude interpreter propagated the ACTUAL emitted X/CX/CCX/RCCX complex quantum gates on all tested states and required final amplitude exactly **+1**, NOT just a Boolean input/output relation. Each independently run base job passed:

- **16,384/16,384** actual literal gate-basis trials covering all 64 public constants×BOTH direct and complement-conjugated ADD encodings×all64 six-bit target inputs×disabled/enabled source control, final exact +1 quantum phase, unchanged controls and carry/scratch zero, including public v=0.
- **3,366/3,366** independent public modular arithmetic identity checks covering all 34 positive/signed k values (35 enabled and64 disabled cases per k).
- **42,672/42,672** previously verified De Morgan comparator signed/public threshold input-phase cases and clean carry/scratch.
- **6,732/6,732** original positive and signed outer modulo35 adder cases for all34 k with 99 enabled/disabled inputs per branch, phase+1 and zero auxiliaries; plus **another 6,732/6,732** candidate inner-adder source cases for the SAME positive/signed outer arithmetic and input conditions.
- **128/128 prior frozen selected full controlled multiplier** and **128/128 new conjugated-source selected full multiplier** per base: every possible six-bit work value y0..63 and control c0/1, correct public y×base mod35 if enabled and y<35, identity for invalid work and disabled control, exact final complex phase+1, every 25 auxiliary bits zero.
- Reconstructed previous original public-k sign decision table and all34 source score rows exactly matched the independently committed originals before the adder replacement; prior full source operations matched archived source instruction counts; both application circuits have exactly32 logical qubits.

These ideal quantum-semantic checks cannot establish noisy-device fidelity, real QPU factor recovery or asymptotic cryptanalytic performance.

## Fixed original native CPU compilation: ALL paired outcomes including regressions

Original [two-arm source run **39376281237**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39376281237) **2/2 SUCCESS**. Each base compiled the original verified static-sign-selector source and new complement-selected source as a pair against the SAME authenticated IBM Fez read-only target with Qiskit~=2.5.2/IBM-runtime~=0.47, opt1, nine fixed paired seeds **[8776(anchor),43,127,211,887,1597,3571,8017,25013]**, 18 native CPU compiles each base = **36 total**, every original count_ops, width, compiled size, CZ/depth and elapsed retained. The new eight were distinct from ALL previous 16 development/holdout seeds; 8776 is NOT scored. Historical frozen baseline seed8776 original **exactly reproduced** for both bases, so no target/compiler comparability drift was observed in that control.

[Independent original artifact audit and permanent preservation run **39376484723**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39376484723) **SUCCESS**: downloaded original source-run JSON files, did NOT rerun science; audited every one of 36 original target-native CZ/depth outputs against source logs, 64 constant score rows, unchanged public-k selector, quantum gate phase/count proofs, true applied gate-vector changes and correct frozen eight-seed medians/wins/no-QPU physical gate; committed ORIGINAL unmodified JSON bytes:

- [Base2 original per-value source-cost table and nine matched native results](../results/ibm_shor35_complement_constant_selector/qrr_n35_complement_constant_selector_base2.json).
- [Cubic8 original per-value source-cost table and nine matched native results](../results/ibm_shor35_complement_constant_selector/qrr_n35_complement_constant_selector_base8.json).

### Base 2: fixed fresh seed paired native CZ / depth, new − prior (negative better)

| Seed | Prior robust CZ/depth | Complement-selected CZ/depth | ΔCZ | Δdepth | BOTH improve? |
|---:|---:|---:|---:|---:|:---:|
| **8776 anchor, NOT scored** | 6871 / 16626 | 6809 / 16088 | −62 | −538 | anchor only |
| 43 | 7151 / 16247 | 7442 / 17270 | +291 | +1023 | NO |
| 127 | 7191 / 16241 | 7086 / 16634 | −105 | +393 | NO |
| 211 | 7313 / 16858 | 7001 / 16433 | −312 | −425 | **YES** |
| 887 | 7007 / 16254 | 7183 / 16551 | +176 | +297 | NO |
| 1597 | 7169 / 16321 | 6970 / 16321 | −199 | **0** | NO |
| 3571 | 7035 / 15847 | 7517 / 16495 | +482 | +648 | NO |
| 8017 | 7209 / 16058 | 7575 / 16922 | +366 | +864 | NO |
| 25013 | 7156 / 16515 | 7246 / 16515 | +90 | **0** | NO |

Base2 new 8-seed strict **1/8 BOTH-resource wins**, CZ-only3/8, depth-only1/8, median paired **ΔCZ+133**, **Δdepth+345** (both worse), paired CZ range −312..+482, depth −425..+1023. Seed8776 *would* show a favorable small result but is a deliberately separate non-scored anchor and must not be used to upgrade 1/8 to 2/9 or cherry-pick a win. Original robust prior stays best.

### Cubic public base8: fixed fresh seed paired native CZ / depth

| Seed | Prior robust CZ/depth | Complement-selected CZ/depth | ΔCZ | Δdepth | BOTH improve? |
|---:|---:|---:|---:|---:|:---:|
| **8776 anchor, NOT scored** | 7315 / 16286 | 7550 / 17498 | +235 | +1212 | anchor only |
| 43 | 7343 / 16732 | 7690 / 17291 | +347 | +559 | NO |
| 127 | 7304 / 16791 | 7321 / 16542 | +17 | −249 | NO |
| 211 | 7224 / 16627 | 7240 / 17119 | +16 | +492 | NO |
| 887 | 7344 / 16724 | 7595 / 17312 | +251 | +588 | NO |
| 1597 | 7328 / 17136 | 7424 / 17338 | +96 | +202 | NO |
| 3571 | 7229 / 16406 | 7472 / 16912 | +243 | +506 | NO |
| 8017 | 7447 / 16760 | 7367 / 17132 | −80 | +372 | NO |
| 25013 | 7346 / 16852 | 7293 / 16840 | −53 | −12 | **YES** |

Cubic8 new 8-seed strict **1/8 BOTH-resource wins**, CZ-only2/8, depth-only2/8, median paired **ΔCZ+56.5**, **Δdepth+432** (both worse), CZ range −80..+347, depth range −249..+588. One isolated seed25013 has a tiny -12 native depth and -53 CZ improvement, not robust.

## Final frozen interpretation and next step

**FROZEN ROBUST ENGINEERING GATE FAILED FOR BOTH BASES.** The attempt is logically exact and removes 20/17 source CNOTs, and all gate-phase/unitary/ancilla proofs passed, but matched native target placement/synthesis usually overwhelms source savings. This adds another independently verified counterexample to the assumption that lower source gate count monotonically implies lower native mapped CZ/depth. Do **NOT** promote this candidate over the previous holdout-validated public sign-source selector or revise the weights/seeds after seeing the results.

**FROZEN HARDWARE GATE FAILED FOR ALL 36 CPU native compiles** (no circuit achieves native CZ<=800 AND native depth<=2000). The best source branch still uses thousands of CZ gates, and this is only one of many controlled operations that a complete four-stage Shor QPE would require. **No IBM hardware jobs or runtime used; zero paid fallback**. No claim of real N35 factor production, error-corrected hardware scalability or RSA-scale breakthrough. The old real IBM N15 Open-only phase-qubit recycling result remains valid and separate.

**Suggested next experiment:** rather than adding complementary X-layer variants, attempt a new mathematically reversible underflow/wrap correction cancellation that removes a complete comparator compute/uncompute pair, with phase-sensitive full-residue tests and paired fixed seeds **before** checking native counts. If that cannot be proven algebraically without introducing dirty helper state, retain the strong existing sign selector and consider cross-modulus generalization of its public-k source rule. Preserve all milestones and strict IBM Open Plan-only real-QPU policy.
