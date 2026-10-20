# VERIFIED — N35 complete FOUR-WIDE phase preparation, 35-qubit controlled powers, inverse QFT, and 4 terminal measurements: 8/8 paired ISA CZ+depth wins both public bases; QPU feasibility FAIL

**Research lead / original program:** Chase Lunsford / CaMaLabs. **Date:** October 20, 2026. This is a **CPU compiler target-cost and ideal-source correctness experiment**, not execution on a physical IBM quantum processor, not 4-bit phase-register recycling, not a measured Shor period/factor-recovery experiment, and not cryptographic quantum advantage. **ZERO real QPU jobs, shots, Open-plan free runtime or paid Runtime.**

## Preserved baseline and frozen exact scope

The independently audited [N35 35-logical-qubit FOUR-controlled-modular-power original/selected source experiment](QRR_N35_STATIC_SIGN_FOUR_POWER_BLOCK_RESULT.md) had proven 1024+1024 exact emitted quantum operator basis/complex phase+1 results PER base, all 25 auxiliary qubits returned zero, all 64 six-bit residues including identity for invalid y>=35, all 16 four-bit control values, with public multipliers `a=2: [2,4,16,11]`, `a³=8: [8,29,1,1]`; the two latter cube stages skipped because PUBLIC power is exactly identity, not a hidden-order oracle. The original Qiskit SOURCE-only public sign selection is frozen to signed odd modulo35 k, positive even k with `S=CX+6CCX+3RCCX`, no fitting against backend outcomes. [Prior exact original 8-seed native compiler receipts](../results/ibm_shor35_four_power_sign_selector/) were saved from authentic CPU Fez target compilation of these 35-qubit power blocks **without** initial phase Hadamards, IQFT or readout. That result passed 8/8 paired old-vs-selected native CZ AND depth wins for base2 and cube8; physical CZ<=800/depth<=2000 failed for every block.

The **new distinct** [frozen protocol](QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_PREREG.md), original git commit **`903edd3c8005c71d021dfb1e89aeab0bb8b1bb2c`** BEFORE any source-IQFT CPU compiler score, adds an exact literal FOUR-wide order-finding readout construction to BOTH original and selected old-public-power circuits and keeps source arithmetic, modulo35, source sign choices, 35 logical qubits, all25 clean helpers, public base2/cube8 and matched seeds unchanged.

Exactly one scope extension from original unitary block, not a new arithmetic algorithm:
1. Prepare **work `|1>`** from 0 by one X on work[0]; initialize **four simultaneous** phase controls with `H^⊗4` (16 equal-positive phase amplitudes).
2. Compose the previously phase-checked LITERAL whole reversible 35-qubit controlled-public-modular-power circuit, with same four phase and six work qubits/25 scratch; all prior-source operations intact.
3. Append actual Qiskit **`QFTGate(4).inverse()`** on the four phase qubits and **FOUR terminal `measure` instructions** into a four-bit ClassicalRegister. No mid-circuit reset, semiclassical feedback, quantum hardware sampler or factoring response measurement. This is a **wide, non-recycled four-phase-register QPE-readout circuit**.

The full 4-bit register offers only 16 distinct phase outcomes, not adequate to infer general order12 vs4 with high accuracy or extract reliable N35 factors without separate sampling and classical convergence analysis. The experiment intentionally **does not sample any outcome or claim actual factor recovery**.

## Strict mathematical-source proof BEFORE any IBM target metadata read

New reproducible [source experiment](../hardware/qrr_n35_four_phase_iqft_readout_cpu.py) re-executes frozen source sign-k maps and exact earlier source proving code before building the new readout. For BOTH public bases:

- Original 34 sign-k gate decisions, **3366 public arithmetic identities**, **42,672** phase-aware comparator cases, **6732** exact-phase positive/signed modadd cases, plus original/selected **128+128** single multiplier phase-correct cases reproduced.
- Original and selected existing FOUR-public-multiplier unitary source **1024/1024** actual emitted X/CX/CCX/RCCX **Operator** complex-phase basis mappings EACH, all16 phase controls×all64 work residues, all25 auxiliaries returned zero, final complex amplitude+1. Source gate histograms and four-control power schedules matched the ORIGINAL archived power-only source EXACTLY; no gate or selector rewriting.
- Analytic **16×16** Qiskit `QFTGate(4)` and actual inverse matrices compared to direct discrete Fourier (e^{\pm 2\pi i jk/16}/4), inverse times forward identity within 1e-9; isolated four Hadamards produced all 16 **+1/4** basis amplitudes.
- New literal 35-qubit +4 classical bit circuit proves work X, exactly4 initial H, `QFTGate(4).inverse()` with correct actual 16×16 unitary and exactly4 terminal phase measures, zero reset or feedback; the four-power arithmetic between them is completely untouched. Because H and inverse QFT are separately correctly implemented unitaries and the arithmetic block is independently exact on the whole clean initial-source basis subspace, the composition is correct as an ideal circuit construction. This is NOT measured device coherence or verified exact physical factor output probability.

## Original native CPU Fez target compilation and independent immutable proof

[Original two-job source CI **39514204062**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39514204062) **2/2 SUCCESS**, every source QFT/power proof and both jobs' original-result audits passed; used `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47`, authenticated **READ-ONLY `ibm_fez` target metadata** and optimization-level1. FROZEN 8 matched seeds **[239,647,1453,3701,6211,9421,16673,27191]**, same target/seed within each OLD vs SELECTED readout pair. Exactly **32 actual native CPU compiled 35-qubit +4-cbit circuits**, each retained with native count_ops, CZ, depth, 4 measurement instructions and exact compiler output-width.

[Independent original-source-artifact audit/unaltered-results preservation CI **39514510289**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39514510289) **SUCCESS**: downloaded the two ORIGINAL source-run artifacts without rerunning any native compiler job, independently validated ALL 32 native exact measurements, full unchanged 1024+1024 source operator proofs, inverse-QFT mathematical unitary, original public source-k histograms, original no-QFT 8-seed receipts, frozen robustness/physical criteria and zero-QPU contract. It committed the two **untouched original source JSON receipts**:

- [Base2 literal four-phase IQFT readout compiler result JSON](../results/ibm_shor35_four_phase_iqft_readout/qrr_n35_four_phase_iqft_base2.json)
- [Cube8 literal four-phase IQFT readout compiler result JSON](../results/ibm_shor35_four_phase_iqft_readout/qrr_n35_four_phase_iqft_base8.json)

## Every matched outcome with IQFT, H4 and measurement included

Values are compiled native **CZ / depth**; paired Δ=selected−old. No mismatch seeds removed. The previous no-QFT block costs are archived with per-seed IDs inside the original JSON ONLY as **historical comparisons across compiler runs**: native IQFT/readout "overhead" cannot be causally isolated by subtracting previously compiled circuits, because adding gates can change layout/routing/transpiler optimization.

### Base 2, all four public powers [2,4,16,11]

| Seed | Original complete CZ/depth | Public sign selected complete CZ/depth | Paired ΔCZ | Paired Δdepth |
|---:|---:|---:|---:|---:|
| 239 | 33,109 / 76,280 | 29,051 / 67,710 | −4,058 | −8,570 |
| 647 | 31,039 / 72,463 | 28,934 / 66,627 | −2,105 | −5,836 |
| 1453 | 32,780 / 76,784 | 29,358 / 66,717 | −3,422 | −10,067 |
| 3701 | 33,144 / 75,964 | 28,572 / 65,926 | −4,572 | −10,038 |
| 6211 | 31,031 / 75,534 | 28,605 / 66,541 | −2,426 | −8,993 |
| 9421 | 32,233 / 76,181 | 29,927 / 68,251 | −2,306 | −7,930 |
| 16673 | 32,875 / 77,587 | 29,186 / 66,773 | −3,689 | −10,814 |
| 27191 | 31,498 / 73,696 | 29,296 / 66,626 | −2,202 | −7,070 |

**Base2 frozen success:** 8/8 strict same-seed native CZ AND depth gains, median **−2,924 CZ** and **−8,781.5 depth**, paired CZ improvement range2,105..4,572 and depth5,836..10,814. Smallest observed selected CZ **28,572** and selected depth **65,926** at seed3701; these numbers are ISA proxy cost, not device resource fidelity.

### Public cubic base8 powers [8,29,1,1], two publicly identity rounds omitted

| Seed | Original complete CZ/depth | Public sign selected complete CZ/depth | Paired ΔCZ | Paired Δdepth |
|---:|---:|---:|---:|---:|
| 239 | 17,279 / 39,357 | 14,909 / 33,890 | −2,370 | −5,467 |
| 647 | 16,587 / 38,874 | 15,262 / 35,415 | −1,325 | −3,459 |
| 1453 | 16,752 / 40,427 | 15,013 / 34,631 | −1,739 | −5,796 |
| 3701 | 16,677 / 39,924 | 14,671 / 34,088 | −2,006 | −5,836 |
| 6211 | 16,878 / 40,701 | 15,465 / 35,616 | −1,413 | −5,085 |
| 9421 | 16,691 / 39,424 | 15,148 / 34,634 | −1,543 | −4,790 |
| 16673 | 16,775 / 40,023 | 15,405 / 35,340 | −1,370 | −4,683 |
| 27191 | 16,257 / 39,847 | 14,517 / 34,094 | −1,740 | −5,753 |

**Cube8 frozen success:** 8/8 strict same-seed native CZ AND depth wins, median **−1,641 CZ**, **−5,276 depth**, paired CZ savings 1,325..2,370 and depth3,459..5,836. Minimum observed selected CZ **14,517** at seed27191, minimum observed selected depth **33,890** at seed239.

## Scientific conclusions: strong compiler proof, QPU feasibility still an unambiguous NO

**Structural/composition gate PASS:** two original exact source power-blocks each tested 1024 cases per variant/base, mathematically verified 16x16 inverse QFT, correct H4/work|1> preparation and four terminal readout bits. The actually compiled source has **35 logical qubits+4 classical bits**. The source is literal arithmetic, no multiplicative order injection, hidden CRT factor use, precomputed small-N answer oracle or selected layout filter.

**Original robust matched-engineering gate PASS 2/2** with 8/8 seed wins base2 AND 8/8 seed wins cube8. The fixed sign rule continues to save native CZ and depth even after adding inverse QFT and measurement. These are **Qiskit native hardware-target CPU compiler observations**, not necessarily reproducible device-level physical CNOT error or actual quantum result.

**Frozen hard device gate FAIL every one of 32:** smallest observed selected cubic8 14,517 native CZ and depth33,890, vs immutable CZ≤800/depth≤2000 **at least 18.15× gate count and 16.95× depth**. Smallest base2 selected CZ28572/depth65926. **ABSOLUTELY ZERO IBM processor executions, free Open Plan or paid Runtime**. The previous *actual real IBM N15 Open Plan recycled phase-register pilot* remains separately preserved; it did not verify cubic order reduction and cannot be extended to physical N35 with these native resource costs.

**Next falsifiable stage:** an **ideal 4-phase-bit outcome-distribution calculation and strict public continued-fraction proper-factor scoring** (base2 vs cube8) for precisely these new wide readout circuits, including the possibility of no usable factors due to 4 bits of phase resolution; do not use a known order to decide public factor policy or any runtime backend path. A result would quantify this toy circuit's information limit, NOT make it hardware-feasible. Also continue considering truly phase-exact arithmetic networks if aiming at a physical Open Plan QPU.
