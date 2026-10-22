# VERIFIED MIXED — all 98 native IBM Fez conditional RZ feedforward operators match source P up to CLASSICAL branch global phase; physical phase-wire routing and QPU feasibility NOT certified

**Research lead / original program: Chase Lunsford / CaMaLabs.** Experiment October 21, 2026 Pacific / October 22 UTC GitHub Actions. **Absolutely ZERO quantum hardware shots, jobs, Open free or paid Runtime, SamplerV2 or EstimatorV2.** This is a read-only IBM Fez TARGET native **CPU compiler** and actual compiled Qiskit 2×2 `Operator` test, not experimental qubit physics or observed feedback latency. N=35 with public bases2 and8 is a toy, easily factored classically.

## Preserve earlier achievement, first conservative ISA result and source

The [actual true one-recycled-phase Qiskit SOURCE](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md) built 32-source-qubit dynamic quantum circuits for b4,b6,b8 with the same phase bit mid-circuit measured+reset+classically fed back between public modulo35 controlled arithmetic powers (work6 coherent, helpers25 clean). It independently preserved **768/768** phase-exact actual arithmetic instruction basis tests PER PUBLIC BASE and **672/672** ideal measurement probability matches across both bases and all b to mathematically independent WIDE QFT. It was not a hardware dynamic experiment.

The distinct [original read-only IBM Fez target CPU compilation](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEZ_ISA_RESULT.md) genuinely **ACCEPTED ALL SIX** original dynamic source circuits and retained b measurements, b−1 resets and b(b−1)/2 `if_else` blocks, but conservatively recorded `COMPILED_UNCERTIFIED_DYNAMIC_SEMANTICS` because source classically conditional `P(theta)` was lowered to native `RZ(theta)` with no matrix proof. The original immutable native metrics were base2 CZ/depth b4 **29813/69008**, b6 **43613/99325**, b8 **59446/138604**; cube8 b4,b6,b8 **14499/34259**. All remain substantially above immutable hardware-native preflight **CZ≤800 AND depth≤2000** and zero QPU.

## Separate preregistered native matrix falsification

[Preregistration committed BEFORE new native matrix checks](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_PREREG.md), initial freeze commit **`10084259eda715d41c38a787de1371ae31b04967`**, held source public modular arithmetic, 32 source quantum qubits, b classical bits, six original public-base/precision cases, seed8776, optimization1, Qiskit~=2.5.2/runtime~=0.47.0, authenticated read-only IBM Fez target and strict QPU gate unchanged. No different seeds, layouts, new oracle, factorizations or phase approximations were chosen. Each arm's native CZ/depth/ISA op vector had to exactly reproduce the ORIGINAL archive. The [new source `hardware/qrr_n35_native_dynamic_feedback_phase_audit.py`](../hardware/qrr_n35_native_dynamic_feedback_phase_audit.py) rebuilds original circuits, checks original 768-per-base stage proof and 336-per-base independent ideal outcome archives before backend read, then recompiles each original 32q dynamic circuit for direct comparison of native conditional matrices.

### Why native RZ can equal source P for CLASSICAL feedforward

Qiskit native `RZ(theta)` is NOT exactly the same 2×2 unitary matrix as source `P(theta)` but is **equal up to a scalar 1-qubit global phase**:

`P(theta) = diag(1, exp(i theta)) = exp(i theta/2) * RZ(theta)`.

A global phase per **already measured classical-history branch** is invisible in that branch's probability distribution; this statement would **NOT** be valid for a controlled operation on an unmeasured, coherently superposed control bit. The genuine Qiskit source uses only `with qc.if_test((priorly_measured_classical_bit,1))` conditions, not a coherent controlled-on-qubit phase, so branch-global equivalence is the relevant narrowly scoped mathematical test. Nevertheless, global equivalence alone does NOT verify circuit execution on an actual processor, real-time measurement latency, correction timing, or compiler SWAP/routing lineage.

For every actual compiled `if_else`:
1. Resolve its classical `Clbit` in the compiled circuit, check literal condition value **1** and its exact **earlier-measurement classical bit index** against fixed public semiclassical IQFT stage ordering; check all output measurement classical destinations and exact b measurements/b−1 resets.
2. Pull the **actual compiled true-block** Qiskit circuit (one qubit; one `rz` operation in these runs), evaluate `Operator(true_body)` as the actual 2×2 complex matrix INCLUDING Qiskit block global phase. Compare to `Operator(PhaseGate(expected_phase_angle))` computed from original `−2π / 2^(t−j+1)`, computing `trace(U_source† U_compiled)/2` to isolate scalar global phase. Require scalar magnitude1 and max matrix residual under **1e−9**, without post-hoc changing angle/sign/endian.
3. Check native compiled source counts/target capabilities, record every reset, measure and conditional gate **physical-qubit location**, and refuse to certify a SINGLE FIXED physical phase wire if phase locations migrate. Source one PHASE logical qubit and compiler's 156-wide physical target display do NOT establish one constant physical quantum position or true on-device scheduling.
4. Preserve raw original numeric source results and any failure; NEVER submit a single IBM QPU job or make a real-noise/latency claim.

## Actual six circuit results and full original conditional coverage

**ALL SIX passed every classically conditional branch-body operator check.** Total conditional branch comparisons across both bases and all precision widths:

`2 × [6 (b4) + 15 (b6) + 28 (b8)] = 98 / 98`.

Every native source conditional body was `rz` and each of its independently computed complex 2×2 matrices matched corresponding source `P(theta)` UP TO exactly one scalar branch-global phase with residual error **≤1.6e−16** across all original six-arm trials; all literal value1 and correct earlier classical controls/angles matched. Original native metrics, all operation count vectors and source width were reproduced with NO drift.

| Public base | Precision | Compiled conditional P→RZ operators equivalent | Original native CZ / depth reproduced | Physical phase-related locations observed |
|---|---:|---:|---:|---|
| base2 | b4 | **6/6** | **29,813 / 69,008** | 106,118,127,129,130 |
| base2 | b6 | **15/15** | **43,613 / 99,325** | 105,106,117,125,126 |
| base2 | b8 | **28/28** | **59,446 / 138,604** | 106,107,109,117,126,127,129,130,131 |
| cube8 | b4 | **6/6** | **14,499 / 34,259** | 85,86,91 |
| cube8 | b6 | **15/15** | **14,499 / 34,259** | 85,86,91 |
| cube8 | b8 | **28/28** | **14,499 / 34,259** | 85,86,91 |

**Quantum-operator semantic subtest PASS:** All 98 originally uncertain conditional feedforward phase rotations DO preserve the intended rotation **up to an unobservable branch-global phase** on an already classically measured history, and conditional bit-index/angle order are correct. This reduces the first ISA compilation's P→RZ uncertainty; do not silently claim that the first run itself performed these tests (they are in an independent later run).

**Physical-mapping qualification FAILS strict original standard:** Compiler placed measurement, reset, and/or feedback qubit operations at **multiple physical locations** across stages. This is consistent with circuit routing/state movement, but the audit did NOT track every native SWAP or logically prove end-to-end routed quantum-state identity through each dynamic stage. The preregistered STRICT `all_conditional_phase_semantics_certified` gate included certifying a single fixed physical phase-wire location and consequently was **0/3 per base**, despite the 98 individual operator checks passing. That gate failure must remain visible; it is NOT evidence of wrong conditional phase gates, but the physical routing lineage is unproven. Multiple physically addressed sites do not refute reuse of **one logical source phase qubit**. No real device execution/scheduling/timing test was attempted.

**Hardware feasibility unequivocally FAILS all six**: smallest compiled CZ **14,499**, depth **34,259**, still massively larger than **800/2000** one-program physical preflight. Actual physical 156-qubit target width does not make source width32 or physical source-route qubit reuse a demonstrated resource saving on real hardware.

## Authentic original two-arm CI and independent immutable original preservation

[Original six-arm native feedback quantum `Operator` test CI **39729974663**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39729974663) **2/2 SUCCESS**. All six original cost anchors matched, all 98 actual source-to-native 2×2 comparisons succeeded within ≈1e−16. Each original experiment receipt properly marked native feedback as **NOT FULLY CERTIFIED** due only to the strict multi-physical-wire mapping guard; NO quantum runtime call.

[Independent raw original-result audit+preservation **39730198680**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39730198680) **SUCCESS**. Downloaded the unmodified source-run two complete original output JSONs **without rerunning backend compilation**, independently checked each of 98 original `Operator` overlap magnitudes and matrix errors, all six native operation+cost anchors, exact previous-measured classical control indices, phase angles, target physical qubit locations, failed unmapped-phase-wire guard, original source integrity and **0 real IBM quantum jobs**. Committed these exact original JSONs:

- [Base2 exact compiled-native feedback unitary proof and mapping data](../results/ibm_shor35_true_recycled_dynamic_feedback_audit/qrr_n35_native_dynamic_feedback_phase_base2.json).
- [Cube8 exact compiled-native feedback unitary proof and mapping data](../results/ibm_shor35_true_recycled_dynamic_feedback_audit/qrr_n35_native_dynamic_feedback_phase_base8.json).

## Interpretation and next experiment boundary

**Genuine new verification:** Qiskit native compilation accepts original dynamic control flow and the phase correction *mathematically preserved the intended semiclassical inverse QFT rotation in every originally emitted classical branch*. This is a meaningful step beyond purely ideal conditional-basis probability calculations. But neither that nor the 32-source-qubit width establishes working feedback on Fez hardware, fidelity, physical one-site qubit recycling, nontrivial N35 factoring performance or cryptanalytic relevance.

**Reasoned next target:** If pursuing true real-QPU feasibility, inspect native SWAP/layout logical-qubit trace through mid-circuit measurement/reset blocks and physical classical-feedback controls, without changing source arithmetic. More importantly, independently reduce the **dominant modular arithmetic costs** by another order of magnitude under matched native compiler seeds while maintaining exact phase and ancilla cleanup. Do NOT spend or submit a QPU job while immutable gate cutoff fails, and do NOT conflate native top-level circuit depth with hardware-measured real-time classical latency. The original genuine N15 Open Plan real hardware milestone remains separately preserved.
