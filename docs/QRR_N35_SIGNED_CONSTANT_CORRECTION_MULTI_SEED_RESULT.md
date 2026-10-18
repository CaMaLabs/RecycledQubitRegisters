# VERIFIED MIXED — N35 signed public modular correction: robust 8/8 improvement for base2 but only 4/8 cubic8; strict two-base gate FAIL

**Research lead / original program:** Chase Lunsford / CaMaLabs. **Experimental date:** October 18, 2026 (UTC, October 17 PDT). This is a CPU-only Qiskit native compilation against authenticated/read-only IBM Fez hardware target metadata, **NOT** a quantum processor run. Zero real QPU jobs, free Open Plan or paid IBM Runtime, sampler/estimator shots, full QPE Shor-factor tests or real quantum hardware performance measurements. N35 is a classically trivial public modulus.

## Original real milestone and updated scientifically fair reference

The repository independently preserves genuine [IBM Fez Open Plan N15 phase-qubit recycling / Shor factoring pilot](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md) (real QPU shots; cubic preconditioning order remains 4 on N15 and does NOT reduce that order). N35 studies since then have been CPU compiler/read-only target benchmarks. Our immediately preceding [public one-bit carry bypass](QRR_N35_PUBLIC_ONE_BIT_CARRY_BYPASS_MULTI_SEED_RESULT.md) extended phase-preserving relative-phase comparator carries and De Morgan zero-CNOT OR-carry synthesis. That intervention eliminated **46 source CX per six-bit full-residue multiplier** with all **25 auxiliary application qubits clean**, phase exactly +1 on every tested computational-basis gate stream input, and **8/8 base2, 7/8 cubic8** paired eight-seed lower CZ+depth trials. It is our **best verified two-base robust baseline**, and its original JSONs remain untouched under `results/ibm_shor35_one_bit_carry_bypass_multiseed/`.

At historical seed8776 that original best had:
- **Base2 original native Fez target CZ7,887/depth18,221;** emitted source `cx303/rccx596/x1738/ccx160`;
- **Cube8 original CZ7,802/depth18,449;** source `cx311/rccx616/x1828/ccx162`;
- fixed Python3.11, `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, `ibm_fez` **read-only** target, optimization level1, transpiler seed8776, source width32 logical qubits with 25 clean auxiliary bits. Both full N35 original base/modular arithmetic paths maintain identity when y≥35 or quantum phase control0, no stored orbit/order table, and a complete exact emitted-gate phase-sensitive 128/128 full multiplier proof.

Previous original arithmetic and topology tests—including per-base active-only cached latch 5/8 and1/8 multiseed regression, modular shared-carry failure, disjoint comparator failure, relative-V-chain null result, and previous robust De Morgan/one-bit wins—remain separately documented and unmodified. We do NOT substitute a deliberately weak older baseline or choose only favorable placement seeds.

The current candidate has an [explicit preregistration](QRR_N35_SIGNED_CONSTANT_CORRECTION_MULTI_SEED_PREREG.md), git freeze **`5879cfba912a066c46c299dbd632cbfcb19293e0`** (and pre-compile original-metric correction `d50556e63f7f1128d85c558566014f2070349963`), committed **before any new candidate scores**. It freezes the public `k>17` switch, unchanged original one-bit-bypass source, both public bases, eight same fixed seeds `[11,37,101,409,8776,12011,20261,45673]`, paired circuits, full exact phase checks, 6/8 both-metric threshold, untouched original seed8776 anchors and zero QPU.

## Exact public arithmetic change (one frozen intervention)

Our reversible modular-adder contract, for public `k` and valid six-bit input `x∈0..34` when source enable=1, is `x → (x+k) mod35` and CLEAN wrap/carry/scratch; for enable=0, it is the identity on **every six-bit x=0..63**. The same complete full 64 work-register reversible modular multiplier builds from this contract using clean cached phase/valid/enable latches, controlled work/accumulator swap and inverse accumulated subtraction. **No factors, true multiplicative orders, special 12-state subgroup, private key, precompiled full mapping or result-specific source controls are used.**

The original [`hardware/qrr_n35_public_one_bit_carry_bypass_multiseed.py`](../hardware/qrr_n35_public_one_bit_carry_bypass_multiseed.py) applies public `+k` then if overflow `−35` correction with two clean wrap predicates, for all k. The new [`hardware/qrr_n35_signed_constant_correction_multiseed.py`](../hardware/qrr_n35_signed_constant_correction_multiseed.py) makes **only a public-constant branch**:

- **k=1..17:** retain the exact original modadd `wrap = enabled & (x≥35−k)`, `+k mod64`, flagged `−35 mod64`, uncompute wrap with `enabled & (final x<k)`, using previously proven one-bit bypass carry arithmetic and quantum-phase-exact De Morgan temporary comparator.
- **k=18..34:** define `d=35−k≤17` publicly. Flag `enabled & (x<d)`; conditionally do `−d mod64` using the **same original one-bit-bypass prefix adder**; if flag=1, conditionally do `+35 mod64`; clean flag by `enabled & (final x≥35−d)`. Valid x arithmetic is exactly `x+k mod35`. Disabled enable leaves all x unchanged. This uses no new register and no quantum measurement.
- On each **full** base2 and cube8 circuit, exactly **seven** of the twelve weighted modular additions take the signed branch and five take the original branch. Frozen public constants are base2 forward `[2,4,8,16,32,29]`, inverse `[17,34,33,31,27,19]`; cube8 forward `[8,16,32,29,23,11]`, inverse `[13,26,17,34,33,31]`.
- General public identity separately checked for **ALL 34 k values** across the 35 valid enabled x values plus all64 disabled x values each = **3,366/3,366** cases per base, including exact wrap-flag uncompute predicate for every signed enabled input. A separately built candidate source circuit is necessary: Boolean math alone never suffices for RCCX quantum phases.

This is a single combined *signed high-k branch* candidate frozen before results, not tuning each constant from gate-count scoring. Full old and new source are built at equal **32 logical qubits** and all 25 auxiliaries start/end zero.

## Strong gate-by-gate quantum-phase verification BEFORE IBM target access

The [two original public-base native CPU CI jobs **39108692489**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39108692489) **2/2 SUCCESS**, full source proof/ISA compiler/independent source-run checks.

The emitted real Qiskit source gates are checked with actual `Operator(inst.operation)` matrices, requiring a basis-state monomial permutation with each complex amplitude magnitude1; the interpreter accumulates every gate's complex amplitude and rejects any final phase except **+1** within tolerance. It checks each output bit, phase control, all wrap/acc/carry/scratch/valid/enables, and public modular operation on the full six-bit input domain. This is an exact ideal coherent source-equivalence proof on the initially clean auxiliary subspace, **not** a hardware-noise/fidelity test.

For EACH base, ALL checks passed before any backend read:
1. **3,366** independent public signed-mod-add Boolean/clean-flag identity cases across all k1..34, input work and disabled controls.
2. **4** De Morgan Boolean AND/OR and exact RCCX inverse/forward operator composition checks.
3. **42,672** emitted quantum-phase comparator cases for every bit width1..6, public interior threshold, geq/lt, control0/1, flag0/1, all x; clean carries and phase+1.
4. **1,584 original AND 1,584 signed candidate** emitted-gate modular-addition cases over the 16 used public constants, all 35 valid enabled and all64 arbitrary disabled input x, correct output phase+1 and clean scratch.
5. **128 original AND 128 signed candidate** complete six-bit full-work control×y multiplier cases: exact `(a*y) mod35` for enabled y<35; identity for disabled or invalid y≥35, all **25 helpers clean**, exact amplitude+1.
6. Actual signed branch exercised seven times per full base (five original branch), same source logical width32; no unsupported Qiskit gates, no precomputed order/orbit.

The source **does change actual costly operations**, but not identically for the two public bases:

| Entire one-multiplier emitted source gate op | Old robust base2 | New signed base2 | Old robust cubic8 | New signed cube8 |
|---|---:|---:|---:|---:|
| CX | 303 | **292** | 311 | **315** |
| Relative phase RCCX | 596 | **556** | 616 | **608** |
| Exact semantic CCX | 160 | **155** | 162 | **163** |
| X | 1,738 | **1,608** | 1,828 | **1,788** |
| Application logical qubits | 32 | 32 | 32 | 32 |
| Clean full-application auxiliaries | 25 | 25 | 25 | 25 |

Base2 achieves significant reductions in comparator RCCX and source X, whereas cubic8 has +4 CX and +1 exact CCX. These are genuine N35 public constant-structure effects: it would be wrong to assume the source count outcome for base2 transfers to a³8. A single native target seed/layout may further modulate these differences.

## All original eight matched compiler seeds — no best-seed postselection

All measurements are native `ibm_fez` ISA CZ counts and full-device-width compiled circuit **depth**, obtained from a CPU Qiskit compiler. Fixed `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, optimization level1; within each seed pair, original baseline and signed candidate used the same target metadata and compiler seed. **Candidate minus baseline deltas:** negative = savings, positive = regression. Exactly **32 CPU native compilations** (two bases×eight seeds×two circuits).

### Public base2 one controlled modular multiplier

| Seed | Original robust CZ / depth | Signed candidate CZ / depth | ΔCZ | Δdepth | Both better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | 7,932 / 18,529 | **7,536 / 17,307** | −396 | −1,222 | YES |
| 37 | 7,875 / 18,757 | **7,685 / 17,829** | −190 | −928 | YES |
| 101 | 7,955 / 18,618 | **7,520 / 17,574** | −435 | −1,044 | YES |
| 409 | 7,676 / 18,220 | **7,642 / 17,523** | −34 | −697 | YES |
| **8,776** | **7,887 / 18,221** | **7,345 / 16,858** | −542 | −1,363 | YES |
| 12,011 | 7,737 / 18,413 | **7,574 / 17,646** | −163 | −767 | YES |
| 20,261 | 7,744 / 18,497 | **7,352 / 17,274** | −392 | −1,223 | YES |
| 45,673 | 8,135 / 19,192 | **7,257 / 16,959** | −878 | −2,233 | YES |

**Base2 engineering gate PASS with 8/8 BOTH metric seed-pair wins**, 8/8 individual CZ wins, 8/8 depth wins; paired median **ΔCZ−394** and **Δdepth−1,133**; CZ delta range −878..−34 and depth delta range −2233..−697. Original source seed8776 anchor **7,887/18,221 EXACT reproduced** (zero historical drift); at 8776 signed candidate **7,345 CZ/16,858 depth**, savings **−6.87% CZ** and **−7.48% depth** at that matched seed. The smallest observed base2 candidate CZ is 7,257 (seed45,673), which is NOT promoted by choosing that one seed; all fixed seed outcomes were retained.

### Public cubic base8 one controlled modular multiplier

| Seed | Original robust CZ / depth | Signed candidate CZ / depth | ΔCZ | Δdepth | Both better? |
|---:|---:|---:|---:|---:|:---:|
| 11 | **8,242 / 18,553** | 8,174 / 18,900 | −68 | +347 | NO |
| 37 | **8,321 / 19,496** | 8,347 / 19,525 | +26 | +29 | NO |
| 101 | **7,604 / 18,627** | 8,317 / 19,254 | +713 | +627 | NO |
| 409 | 8,156 / 19,775 | **8,064 / 19,139** | −92 | −636 | YES |
| **8,776** | **7,802 / 18,449** | 8,199 / 19,269 | **+397** | **+820** | NO |
| 12,011 | 8,137 / 18,982 | **7,828 / 18,527** | −309 | −455 | YES |
| 20,261 | 8,328 / 19,457 | **7,984 / 18,843** | −344 | −614 | YES |
| 45,673 | 8,290 / 19,122 | **8,038 / 18,746** | −252 | −376 | YES |

**Cubic8 robust engineering gate FAIL**: only **4/8** seed pairs improve BOTH CZ+depth, only 5/8 CZ improvements and4/8 depth improvements, despite favorable medians **ΔCZ−80 / Δdepth−173.5**. Paired CZ delta range −344..+713; depth −636..+820. The original seed8776 robust baseline **7,802/18,449 EXACT reproduced**; signed candidate **8,199/19,269**, *worse by +5.09% CZ and +4.44% depth* at that seed. Source-level arithmetic behavior passes every exact phase test, but the compiler resource advantage does NOT generalize to both public bases or all placements.

The **frozen two-base robust engineering gate FAILS** because cubic8 has only 4/8 paired joint wins, below preregistered 6/8. We DO NOT change the seed, promote the isolated base2 result into a universal arithmetic improvement, or use cube8's favorable median as a substitute for six joint wins. The true result is base2 robust positive, cube8 nonrobust/mixed. All source revisions, seeds, failed gate and original strongly verified baselines are preserved.

## Provenance: original successful run and separate independent preservation

[Original matched source Qiskit target compiler run **39108692489**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39108692489) **2/2 SUCCESS**: full public/classical+complex-phase source gate verification BEFORE IBM backend target read, 16 paired CPU compiled ISA circuits in each public-base job, eight seed pairs fixed, independent built-in source audit, all original raw JSON artifacts emitted. NO QPU job.

[**Independent original source artifact JSON auditing/preservation workflow 39108827186**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39108827186) **SUCCESS**: downloaded precisely the two original source-run artifacts and verified raw numeric CZ/depth values for all 32 original CPU compiles, original robust baseline anchored to previous unmodified receipts for ALL eight seeds, output phase-exact source proof counts, seven signed interventions in each constructed circuit, 32 logical qubits/25 clean helpers, native `count_ops` consistency, strict both-base 6/8 gate, historical seed8776 reproduction, all failed device gates and zero quantum runtime; committed ORIGINAL UNCHANGED JSON bytes without rerunning a single compiler call:

- [Original signed base2 eight-seed JSON](../results/ibm_shor35_signed_constant_correction/qrr_n35_signed_correction_base2.json)
- [Original signed cubic base8 eight-seed JSON](../results/ibm_shor35_signed_constant_correction/qrr_n35_signed_correction_base8.json)

This source + independent original audit provenance is stronger than a paraphrased successful-run statement and prevents accidental post-hoc improvement claims.

## Hardware feasibility still blocks QPU

**Every one of all 32 matched CPU-compiled circuit results FAILS the unchanged hardware feasibility heuristic: native CZ≤800 AND depth≤2000**, long before combining multiple modular powers and phase estimation. At seed8776 best new base2 **CZ7345/depth16858** is **9.18× CZ** and **8.43× depth** above cutoffs for a **single modular multiplier**. No quantum QPU shots, Open Plan/free hours, paid fallback or factor-production measurements on N35 hardware, and no inference about real physical-device fidelity, RSA-scale factoring, ML-KEM or new asymptotic algorithm. True N15 QPU factoring/recycling milestone remains independently preserved.

## Grounded next research question

Further compiler seed testing alone does not solve width32/native depth≥10k. The sign-of-k heuristic materially alters expensive comparator/control structure differently across the two public bases. A next strict new preregistered experiment could select `+k` versus `-(35−k)` from a **public operation-local structural cost metric** measured BEFORE any native compile (such as separately phase-proved source RCCX/CCX/CX counts per public k), rather than branching at k=17 and hoping the same rule fits both arithmetic weight sets. It would need an independent fixed formula, no circuit score tuning, exact quantum-phase checks, a full two-base matched eight-seed trial vs the current proven one-bit baseline, and an immutable real-hardware feasibility gate. Other opportunities include preventing repeated modular correction ancilla overhead in the *complete* four-round public QPE circuit, but no automatic free/paid QPU trial.

**Preserve the base2 sign representation as a meaningful independent engineering win, retain the original bypass for general two-base robust reference, and explicitly mark the two-base robust gate FAILED.**
