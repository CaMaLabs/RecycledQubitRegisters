# VERIFIED FRESH HOLDOUT PASS — N35 public constant source-cost selector: 8/8 base2 and 7/8 cubic8 new-seed CZ+depth paired wins, ZERO QPU

**Research lead/original program: Chase Lunsford / CaMaLabs.** Experiment October 19 PDT / October 20 UTC, 2026. All data are Qiskit CPU native compilation to authenticated IBM Fez read-only target metadata, NOT actual quantum processor execution. NO real QPU shots/jobs, free Open-Plan or paid IBM Runtime, Shor factoring on N35 hardware, full four-round QPE or cryptographic quantum advantage.

## Original milestone preserved BEFORE this new test

The preceding [two-base robust 34-public-k source-cost selector experiment](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md) froze a deterministic public operation-local SOURCE-gate decision: compare positive and signed correction circuits for each k=1..34 by Qiskit source-only cost S=CX+6CCX+3RCCX (X unweighted), choose signed iff strictly smaller S and otherwise original positive. Without consulting compiler placements, the frozen choice selected **signed for odd k, original positive for even k**, across both base2 and public cube8. Same original one-bit-bypass De Morgan phase-aware arithmetic and full six-bit residue input/invalid-state identity. The original two-base source run [39367204317](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367204317) achieved **8/8 strict paired native CZ AND depth savings for BOTH bases** on the previous eight development seeds, original JSON saved unchanged by [independent audit 39367462324](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39367462324), with true complex quantum operator phase+1 and all 25 auxiliaries cleaned.

Historical seed8776 **original robust** baseline base2 CZ7887/depth18221, cubic base8 CZ7802/depth18449; **source-cost-selected** candidate base2 CZ6871/depth16626 and cube8 CZ7315/depth16286, all 32 source logical qubits. The earlier fixed k>17 signed correction had only 4/8 cube8 joint wins; it was not substituted as an easy baseline. The existing genuine real IBM N15 Open Plan recycled phase-register pilot remains a separate legitimate hardware result, with no assertion of cubing gain at N15.

**Scientific limitation motivating this test:** the original eight compiler seeds were repeatedly used during development of other N35 candidates. Those first 16 paired wins are reproducible but not independent holdout placements.

## FROZEN independent holdout, not a retrofitted seed search

[Original holdout preregistration](QRR_N35_STATIC_GATE_SIGN_FRESH_SEED_HOLDOUT_PREREG.md), git freeze commit **f1ad7917459fe43f0106662d0ec214d7a103b903**, was committed **BEFORE ANY new holdout compilation outcomes**. Exactly eight new integer Qiskit seeds **[1729,3137,5003,7919,10103,13007,20011,31799]**, all disjoint from the development-cohort [11,37,101,409,8776,12011,20261,45673]. A ninth seed **8776 anchor** was compiled separately as a historical target/compiler comparability check, NEVER included in the new 8-seed numerator or median.

[New source runner](../hardware/qrr_n35_static_sign_selector_fresh_holdout.py) imports the unchanged, previously independently audited ORIGINAL source selector/quantum proof functions. Before reading Fez target metadata, it recomputes the original **34×2 Qiskit source gate vectors/costs/selected choices** and REQUIRES their exact equality with the original archived JSONs; it builds the same original and selected full N35 multipliers and checks original/candidate SOURCE instruction gate counts EXACTLY against independent prior receipts. Source width **32 logical application qubits**, every one of all **25 auxiliary qubits** returned to zero, no factors, multiplicative order, subset orbit, private key or precomputed full output table. No post-result modification to public selection weights, source circuit or target compiler.

Every public-base holdout CI source job re-ran the full Qiskit emitted monomial quantum-operator complex-phase source proof BEFORE backend access, all PASS:
- **3,366** algebraic enabled/disabled public modular correction/underflow identities for all 34 k.
- **42,672** exact emitted comparator cases across all public six-bit thresholds, controls and both initial flag states, all carry/scratch clean, quantum output complex phase+1.
- **6,732** actual emitted positive AND signed per-k controlled modular addition gate cases, all source y enabled/disabled and all helpers cleaned, phase exactly +1.
- **128 ORIGINAL plus 128 selected** complete full six-bit controlled multiplier quantum-gate cases per base, control0 and invalid y identity, correct y*a mod35 for valid y, exact final quantum phase +1, all 25 helpers zero. This is an ideal coherent semantic proof on the tested clean-input subspace, not a noisy quantum hardware measurement.

Each of TWO independently running GitHub CI jobs then read the Fez target (Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47, optimizer1) and compiled 9 fixed paired seeds×2 circuits =18 native CPU compilations per base, **36 total CPU target compiles**, all 8 new paired results and separate 8776 anchor preserved in original JSON with native count_ops, size, width, CZ/depth, elapsed and immutable CZ<=800/depth<=2000 device gate.

## ALL eight held-out matched results, including the equal-CZ non-win

Paired delta = new selected method MINUS previous robust original. Negative means fewer native gates or lower depth. **Strict both-resource improvement requires ΔCZ<0 AND Δdepth<0 in the SAME fresh seed.**

| FRESH seed | Base2 original CZ / depth | Base2 selected CZ / depth | Paired ΔCZ | Paired Δdepth | Both strict? |
|---:|---:|---:|---:|---:|:---:|
| 1729 | 7779 / 18549 | **7144 / 16260** | −635 | −2289 | YES |
| 3137 | 8375 / 19117 | **7031 / 16218** | −1344 | −2899 | YES |
| 5003 | 8318 / 19484 | **6663 / 15740** | −1655 | −3744 | YES |
| 7919 | 7977 / 18828 | **6649 / 15393** | −1328 | −3435 | YES |
| 10103 | 8270 / 19352 | **7314 / 16468** | −956 | −2884 | YES |
| 13007 | 8207 / 18911 | **7013 / 16229** | −1194 | −2682 | YES |
| 20011 | 8120 / 19386 | **7172 / 16387** | −948 | −2999 | YES |
| 31799 | 7792 / 18397 | **7061 / 15900** | −731 | −2497 | YES |

**Base2 FRESH holdout 8/8 joint wins, 8/8 native CZ and depth standalone wins**, median paired **CZ −1075**, **depth −2891.5**; CZ pair range −1655..−635, depth range −3744..−2289. Frozen ≥6/8 + negative paired medians **PASS**. Original seed8776 historical control exactly reproduced original7887/18221 and selected6871/16626, but the anchor is not counted above.

| FRESH seed | Cubic8 original CZ / depth | Cubic8 selected CZ / depth | Paired ΔCZ | Paired Δdepth | Both strict? |
|---:|---:|---:|---:|---:|:---:|
| 1729 | 8146 / 19054 | **7487 / 16857** | −659 | −2197 | YES |
| 3137 | 8164 / 19253 | **7501 / 16723** | −663 | −2530 | YES |
| 5003 | 8114 / 19005 | **6863 / 16582** | −1251 | −2423 | YES |
| 7919 | 8174 / 19149 | **7044 / 16429** | −1130 | −2720 | YES |
| 10103 | 8336 / 19126 | **7058 / 16991** | −1278 | −2135 | YES |
| 13007 | 7507 / 18257 | **7507 / 17149** | **0** | −1108 | **NO: CZ equal** |
| 20011 | 8128 / 19763 | **7426 / 17407** | −702 | −2356 | YES |
| 31799 | 8369 / 19564 | **7474 / 16911** | −895 | −2653 | YES |

**Cubic8 FRESH holdout 7/8 joint CZ+depth wins**, 7/8 CZ reductions and 8/8 depth reductions, median paired **CZ −798.5**, **depth −2389.5**; CZ range −1278..0, depth range −2720..−1108. Seed13007 has exactly **equal native CZ**, not lower, so correctly is NOT a two-resource success. Frozen ≥6/8 + negative medians **PASS**. Original seed8776 historical control exactly reproduced original7802/18449 and selected7315/16286, excluded from these statistics.

**Combined evidence from two frozen cohorts on same target and Qiskit version:** development paired strict 8/8 base2 and 8/8 cubic8; fresh holdout paired strict **8/8 base2 and 7/8 cubic8**. Thus 16/16 base2 and 15/16 cube8 joint wins across 16 distinct seeds per base, **NOT 31 independent quantum hardware trials** and not real runtime performance. The new holdout strengthens robustness against placement randomness in this specific fixed Qiskit/IBM Fez backend target, but not against target-version or device-noise changes.

## Original run provenance and independent source-artifact archival

[Original 2/2 FRESH source experiment CI **39368270962**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39368270962) **SUCCESS**: full exact emitted source phase proofs, strict source artifact matching and 36 genuine CPU native ISA compilations all successful, internal postcompile audits passed, original artifacts uploaded. **No runtime QPU submission**.

[Independent source-artifact audit/byte preservation CI **39368456367**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39368456367) **SUCCESS**: fetched the two ORIGINAL source-run JSON artifacts, did NOT rerun Qiskit, independently checked all 36 EXACT original CZ/depth/ISA metrics against source log results; 34 source-k score tables unchanged; source phase proof counts; every per-base 8 new seed and separate historical anchor; correct 8/8 and 7/8 joint wins including the zero-CZ cube8 seed; pristine previous baseline; all immutable hardware/device failures; and QPU job count0. Preserved the ORIGINAL JSON bytes into main:

- [Original base2 fresh eight-seed and historical 8776 anchor JSON](../results/ibm_shor35_static_sign_selector_fresh_holdout/qrr_n35_static_sign_fresh_holdout_base2.json)
- [Original cubic8 fresh eight-seed and separate anchor JSON](../results/ibm_shor35_static_sign_selector_fresh_holdout/qrr_n35_static_sign_fresh_holdout_base8.json)

Original development source, independent scientific wins, previous negative and null results, and the genuine N15 real IBM Fez Open Plan pilot remain separately preserved with attribution.

## Scientific conclusion and unchanged hard QPU no-go

**The predeclared FRESH holdout engineering gate PASSED for BOTH public bases** without retuning a public constant or changing the original score formula. The sign-selection rule is now supported under **16 different compiler seeds per public base**, including a genuinely separate new holdout cohort, at one read-only hardware target and one fixed SDK/compiler level. This is a meaningful reproducible quantum-arithmetic ISA resource improvement, not an algorithmic theorem, proven practical speedup, noisy hardware fidelity result, or a factoring demonstration.

**Every one of the 36 new read-only target-compiled circuits FAILED the original native QPU feasibility heuristic CZ≤800 AND depth≤2000**, and even one multiplier at our low-count seed5003 base2 CZ6663/depth15740 remains **8.33× CZ / 7.87× depth** over cutoffs (before a full four-round QPE or error correction). Thus **no actual IBM quantum hardware job, no free Open Plan runtime, no paid runtime**. No claim of real N35 factoring, RSA/ML-KEM cryptanalysis, or a hardware-ready next experiment.

**Next research question:** given that the *source-only fixed sign selector* now survives fresh placement holdouts, investigate mathematical circuit-level improvements that reduce native CZ by the further order of magnitude needed: collapse repeated wrap/borrow correction ancillas, or consider novel in-place modular adders preserving exact phase and full residue validity, rather than selecting post-hoc favorable layouts. Another option is testing this source-only arithmetic improvement at a different public N/order without hardcoding known factors or orbits, with a separately frozen scope and no hardware jobs.
