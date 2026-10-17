# VERIFIED MIXED — N35 phase-correct cached-control RCCX gate pairs: base2 native CZ −7.8%, depth −9.0%; cube8 CZ −1.0% but depth +0.3%. Two-arm engineering gate FAIL; ZERO QPU.

**Research lead and original work:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-17. **Source experiment:** actual emitted phase-sensitive Qiskit circuit proofs plus authenticated READ-ONLY `ibm_fez` target CPU compilation. **No QPU job, no free Open Plan IBM Runtime, no paid Runtime, no physical quantum measurements.** This is a *single N35 six-bit controlled multiplier per public base*, not a complete Shor factoring/QPE circuit or RSA-scale breakthrough. N35 is classically trivial.

## Provenance, unchanged best and frozen protocol

Prior [verified phase-exact relative-phase ripple comparator result](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_RESULT.md) established the original best native compiler costs for ONE full-residue controlled multiplier on N35 with bases a=2 and a³=8: **a2 CZ 9,263, depth21,772; cube8 CZ9,426, depth21,933**, 32 logical application qubits, 25 initially/returned-clean helpers, 596/616 RCCX source comparator temporary carry gates and 160/162 exact source CCX, with 42,672 comparator and 1,584 modular-add and 128 full multiplier exact +1-complex-phase input cases PER BASE. Original JSON in `results/ibm_shor35_relative_phase_ripple/qrr_n35_relative_phase_clean_vchain_base{2,8}.json` retained unchanged; Fez native target, Qiskit~=2.5.2/runtime~=0.47, optimization1, seed8776. Earlier separate 3+-control clean V-chain RCCX experiment was TRUE NULL; previous shared carry and disjoint comparators were strictly worse. The real IBM Fez Open Plan N15 recycled-phase demonstration remains separate and genuine; it did NOT test public cubic order reduction.

The new [`QRR_N35_RELATIVE_PHASE_CACHED_LATCH_PREREG.md`](QRR_N35_RELATIVE_PHASE_CACHED_LATCH_PREREG.md) preregistered exactly two public-base arms **before any new native scoring**, initial git **`5537b57907162795ead8f64c74d21c3e0cda07ac`**, unchanged quantum arithmetic, layout controls and 32 logical qubits, exact phase tests, immutable Fez target optimizer seed/level and device-gate **CZ≤800 and depth≤2000 for BOTH arms**.

## Exactly one intervention — two temporary Boolean control-latch families

[Source `hardware/qrr_n35_relative_phase_cached_latch.py`](../hardware/qrr_n35_relative_phase_cached_latch.py) imports the already phase-proven **shortened ripple-comparator RCCX carry logic** and original prefix-carry public modular arithmetic without modifying either. It rebuilds the original public full-six-bit-register controlled N35 multiplier and changes **ONLY**:

1. Compute clean `active = phase AND valid` once using Qiskit's **RCCX** instead of exact CCX, and reverse it after all modular additions and work/acc SWAP with the **ACTUAL RCCX.inverse()**. Phase and valid controls do not change in the intervening circuit.
2. For each of six forward and six reverse public modular accumulator additions, compute `enable = active AND work[i]` with RCCX instead of exact CCX, supply enable to the existing phase-correct modadd, and uncompute it with the actual inverse RCCX. The external work bit and active stay unchanged across each modular add.
3. Keep **all semantic target flips** (predicate flag, conditional swaps) exactly as before and all validity correction arithmetic unchanged. No multiplicative order is injected, no factorized orbit, private factors, or source generator timing changed. The circuit uses the same 32 logical qubits, 25 clean helper registers and full y0..63 residue behavior.
4. Total **26 actual source CCX latch calls replaced by 26 RCCX** (2 active, 24 enable) per base. The new quantum source gate counts are **base2 {CX1033, RCCX622, X28, CCX134}** vs old {CX1033, RCCX596, X28, CCX160}, and cube8 **{CX1077, RCCX642, X28, CCX136}** vs old {CX1077, RCCX616, X28, CCX162}. This explicitly confirms the intervention was exercised, unlike the earlier 0-RCCX null V-chain.

## Actual operator/complex-phase validation — complete

RCCX alone is NOT a CCX with identical phase action. Every complex-phase verifier obtains the actual `Operator(gate)` unitary of each emitted Qiskit instruction, ensures it is a monomial basis permutation, interprets the entire gate sequence on chosen basis states, accumulates the exact complex amplitude, and requires final phase **+1**, correct work/control and ALL 25 auxiliaries zero. This proves coherent ideal mapping on the initially clean auxiliary subspace by linearity, **not** robustness under physical noise.

Each of the **two public base-arm jobs** passed, in this order **BEFORE** any backend target read/native compiler:

- **8/8 direct actual-operator local cache-latch checks**: every pair of control input bits and both semantic probe initial values, `RCCX ... CX(latch,probe) ... RCCX.inverse()`, exact target operation, unmodified control, latch zero and phase+1; actual `Operator(RCCX.inverse())@Operator(RCCX)=I` confirmed.
- **42,672/42,672 actual emitted-gate comparator phase checks** across public thresholds and bit widths1..6, including both initial flag values and both predicate polarities; exact phase+1 and carry/scratch zero.
- **1,584/1,584** phase-exact public N35 modular-add cases across 16 constants×(35 valid enabled+64 arbitrary disabled x), all scratch clean, unchanged enable.
- **128/128** phase-exact complete six-bit controlled modular multiplication inputs per base: c0/1, y0..63, exact `a*y mod35` for enabled valid work, identity for control0 or y≥35, final phase+1 and all 25 aux clean.

Fixed original [two-arm source GitHub Actions run **39074215604**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074215604) **2/2 jobs SUCCESS**, including built-in original source result and baseline-independent audits; original Qiskit/IBM Fez compiler target opt1 seed8776; NO real QPU operation. The separate [original artifact independent audit and preservation GitHub Actions run **39074317133**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39074317133) **SUCCESS**, downloaded the two ORIGINAL CI-produced receipts and checked exact frozen 8+42672+1584+128 tests, 26 actual RCCX replacements, precise native counts, original baseline JSON, clean helpers, phase+1, unchanged register width and failed real-device gate. It committed the original unmodified JSON bytes:

- [Base2 original JSON](../results/ibm_shor35_phase_cached_latch/qrr_n35_phase_cached_latch_base2.json).
- [Cube8 original JSON](../results/ibm_shor35_phase_cached_latch/qrr_n35_phase_cached_latch_base8.json).

## Frozen numeric result, including unfavorable base8 depth

| Metric — exactly ONE controlled public N35 multiplier | Previous best base2 | New RCCX cache base2 | Previous best cube8 | New RCCX cache cube8 |
|---|---:|---:|---:|---:|
| Exact quantum-phase complete gate proof | 128/128 | **128/128** | 128/128 | **128/128** |
| Full source RCCX instructions | 596 | **622** | 616 | **642** |
| Full source CCX instructions | 160 | **134** | 162 | **136** |
| Application logical qubits | 32 | **32** | 32 | **32** |
| All clean helper qubits | 25 | **25** | 25 | **25** |
| **IBM Fez-target compiled native CZ** | 9,263 | **8,542** | 9,426 | **9,328** |
| **IBM Fez-target compiled depth** | 21,772 | **19,819** | **21,933** | 22,005 |
| Frozen engineering win (lower CZ AND depth vs old) | baseline | **PASS** | baseline | **FAIL** |
| Native hardware CZ≤800 AND depth≤2000 | FAIL | **FAIL** | FAIL | **FAIL** |
| Actual IBM QPU jobs / paid runtime | 0 | **0** | 0 | **0** |

**Base2 favorable:** native CZ −721 (**−7.78%**), depth −1,953 (**−8.97%**) vs frozen verified best. **Cube8 mixed:** CZ −98 (**−1.04%**) but depth **+72 (+0.33%)**. Consequently the preregistered engineering gate requiring **BOTH bases strictly improve in CZ AND depth FAILED**, despite base2 being the smallest-cost compiler circuit seen so far. Preserve both; do not present the cube8 comparison as a depth improvement or quietly postselect base2. Single seed/layout fixed, target backend costs are compiler proxies and can vary with target metadata and placement; these results do not prove quantum device fidelity or algorithmic asymptotic speedup.

**Frozen device gate FAILURE:** lowest new source arm still costs **8,542 CZ and depth19,819**, 10.68× and 9.91× the hardware proxy thresholds *for only ONE modular multiply*. Cubic arm 9,328 CZ/22,005 also fails. No N35 live device run, no Open Plan Runtime use, no paid runtime, no physical factor recovery and no new cryptanalytic claim.

## Follow-up grounded in this result

The discrepancy between base2 and cube8 points to compiler topology/routing/timing sensitivity or different constant-arithmetic structures. **Preregister a separate isolated active-only vs enable-only RCCX cached latch ablation** across both public bases (2×2=4 arms) to identify which cached latch contributes to cost or depth regression, with the same exact source operator phase proof, old baseline and frozen backend/seed. Do not claim causal attribution to either latch family from this combined result. Even if a single kernel costs less, only a separately scoped full Shor sequence and future explicitly authorized active Open Plan hardware check could establish real N35 factoring ability. The original real N15 Open-only phase-recycling milestone remains preserved separately.
