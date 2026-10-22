# VERIFIED SOURCE-WIDTH WIN — genuine one-recycled-phase N35 Qiskit source shrinks 32 → 23 qubits by deleting nine proven IDLE scratch bits; native ISA gate-cost robustness FAIL, physical mapping still unproven

**Research lead / originating program:** Chase Lunsford / CaMaLabs. **Date:** October 22, 2026 (UTC / October 21 California). **NO real IBM QPU jobs, shots, free Open Plan quantum runtime, paid runtime or other hardware execution.** This study uses the real IBM Fez BACKEND TARGET for **CPU transpilation only**. It tests genuine midcircuit measurement/reset/classical feedback, not an abstract 23-qubit factoring oracle. N35 remains classically trivial and cube8 gives a trivial public factor via gcd(8−1,35)=7.

## Baseline: the program had already advanced beyond the earlier one-multiplier work

The latest [true recycled-phase original source](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_RESULT.md) emits actual Qiskit controlled modular-power arithmetic on a persistent 6-qubit work register and **ONE recycled phase qubit**, with dynamic midcircuit phase measurement, resets and classical if_else feedback for phase precisions b=4,6,8. Initially, **32 source quantum wires** = phase1 + work6 + arithmetic helpers25, and b output classical bits. The earlier original gate proofs passed **768 exact emitted phase-operator cases per public base**, 336 independent ideal measurement probabilities per base matched the wide QFT over all branches, and all originally computed helpers returned zero.

An [initial native IBM Fez CPU compilation](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEZ_ISA_RESULT.md) independently verified all six original dynamic circuits lower to real target-supported ISA with correct source counts for `measure=b, reset=b−1, if_else=b(b−1)/2`; native CZ/depth for base2 b4 **29813/69008**, b6 **43613/99325**, b8 **59446/138604**, and cube8 all b4/6/8 **14499/34259**, opt1 seed8776. A [subsequent separate native quantum-Operator proof](QRR_N35_TRUE_RECYCLED_DYNAMIC_FEEDBACK_PHASE_RESULT.md) checked **98/98 compiled conditional branch bodies** as exactly equivalent to the intended source PhaseGate rotations up to CLASSICAL-branch global phase, but did **NOT** establish an unchanging physical phase-wire mapping or real on-device control latency. All six fail original physically conservative **CZ≤800 AND depth≤2000**. These original independent results remain unchanged.

## Preregistered, falsifiable intervention: remove ONLY truly idle `scratch` wires

[Original preregistration, committed BEFORE native scoring](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_PREREG.md), git **`b2f19450390cccb5464a51eeec93027ec517cf7b`**, froze precisely:

- Two public bases a=2 and a³=8, three genuinely dynamic phase precisions b4,b6,b8.
- Four fixed transpiler seeds `[509,1223,4093,8776]`, read-only `ibm_fez` metadata, Qiskit~=2.5.2/runtime~=0.47, optimization1. At each seed compare ORIGINAL 32-source-qubit circuit to the same circuit **with the original 9-qubit `scratch` register omitted**. 2×3×4×2=**48 actual ISA CPU compiles**.
- Strictly inspect every actual source operation's operands, including all nested feedback blocks, and **ABORT before backend read** if ANY original scratch bit is used. Recreate the circuit with exactly the same original remaining `QuantumRegister` and `ClassicalRegister` objects and **replay exactly the same `CircuitInstruction.operation`, original surviving qubit operands, classical operands, source order and conditional body**, not one rewired gate. Validate one original source phase, all6 work bits, original arithmetic powers and b output bits, correct b measurements/b−1 resets/b(b−1)/2 feedback conditions and phase angles, and output width **23 =1 phase+6 work+16 remaining helpers**.
- Demand Qiskit native Fez read-only compilation for every pair and **actual native `Operator` proof of the emitted classically conditional 2×2 phase-correction body**, including its exact old measured classical-bit index, up to unobservable branch-global phase. Record all physical addresses touched and phase-related addresses, without making a false claim that this proves one physical phase wire.
- Independently preserve all raw original results; freeze historic original seed8776 six cost anchors and strict robust-native-gate improvement ≥3/4 seeds improving both CZ and Qiskit top-level depth, negative median paired deltas for **EACH of six base/precision combinations**, and separate unchanged real-QPU preflight CZ≤800/depth≤2000. No device submission under any outcome.

### Harness correction, with first failed run retained

[First attempted precompiler CI **39738758532**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39738758532) **FAILED before backend read/native compilation**. The original b4 source inspection already found zero scratch operands; then the experimental register clone builder incorrectly tried to exclude the scratch register using Python wrapper **object identity** (`reg is not scratch`), and failed the explicit expected one-register reduction assertion. This was NOT a quantum gate mismatch, used scratch register, compiler resource result or rejected target circuit. [Documented prereg correction](QRR_N35_TRUE_RECYCLED_IDLE_SCRATCH_PREREG.md) and source patch changed **only** the register-filtering guard to stable `reg.name!='scratch'`; no arithmetic, quantum operation, classical feedforward, seed, target, original baseline or pass criteria changed. The first run remains visible and is not counted as native evidence.

## Newly proved actual source equivalence — 6/6 successful, no arithmetic changes

[Original successful two-base full source/native GitHub Actions trial **39738979913**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39738979913) **2/2 source job SUCCESS**. For each six original dynamic source circuit, the new code [`hardware/qrr_n35_true_recycled_prune_idle_scratch.py`](../hardware/qrr_n35_true_recycled_prune_idle_scratch.py) built the already audited exact original `source.build_dynamic_source(base,bits)`, then checked that:

1. ALL nine scratch qubit objects occur in **ZERO** top-level quantum instruction operands; EVERY classical feedback block acts solely on the existing phase qubit, not scratch, and has only a one-qubit branch body. No source scratch gates are being omitted.
2. With the scratch register absent, the **new 23-source-qubit Qiskit circuit** has exactly identical emitted operation objects/parameters, original unchanged qubit and classical-bit arguments and order, and unchanged full source instruction-count histogram for every b and base. Every `if_else` condition/branch object agrees with the original. Actual measured classical bits, reset count and feedforward prior-bit/angle logic unchanged. The original phase and 6-work qubits and other 16 helper bits remain the SAME Qiskit source registers.
3. These are **the same quantum operations on the 23 remaining live wires**. The removed wires were idle and initially |0>, so the reduced circuit has the **same ideal quantum instrument on the live state**, including its measurement branch distributions, as the ORIGINAL previously proved circuit. The 768 source stage-operator checks per base and 336 ideal dynamic outcomes per base are **previous independent receipts reused**, not falsely claimed to have been rerun numerically.
4. The source needs **one recycled phase quantum bit**, **23 total source quantum bits**, and b classical results, independent of b4/6/8 precision, with no precompiled multiplicative order/orbit, no hidden factors or altered physical circuit operation semantics.

**This is a real engineering SOURCE representation win: 32→23 qubits (−9, −28.125%) while retaining all six dynamic programs and every quantum gate.** It is NOT a claim that 23 physical IBM Fez hardware sites have been reserved or measured: transpiled native circuits still show a backend-sized **156-qubit register**, and native routing can touch extra physical addresses. Current source qubit width and proven peak physical hardware usage are distinct.

## All original 48 read-only Fez CPU ISA compiles and dynamic phase checks — PASS

Every original and reduced circuit at every frozen seed compiled successfully with original measure, reset and if_else counts. Each native conditional true-block was tested with Qiskit's actual `Operator` against original PhaseGate(theta) up to a measured-classical-history-wide global phase, original bit-index order required. Per base and seed, b4/b6/b8 includes `6+15+28=49` conditional blocks; 2 bases×4 seeds×2 source versions×49=**784/784** compiled branch-body operator equivalence checks. All seed8776 ORIGINAL 32q native cost anchors precisely reproduced previous independent runs.

**Native CZ and depth results are variable** despite identical source gates; the 23-source-qubit width changes Qiskit placement/routing, not quantum arithmetic. Below, each cell `original → pruned` reports raw native CZ / reported top-level compiled depth at the frozen anchor seed8776.

| Public base and precision | Original 32q native CZ / depth | Reduced 23q native CZ / depth at seed8776 | Delta CZ / depth |
|---|---:|---:|---:|
| a2 b4 | 29,813 / 69,008 | **29,223 / 68,106** | −590 / −902 |
| a2 b6 | 43,613 / 99,325 | **44,313 / 102,275** | +700 / +2,950 |
| a2 b8 | 59,446 / 138,604 | **59,730 / 138,953** | +284 / +349 |
| cube8 b4 | 14,499 / 34,259 | **15,036 / 34,595** | +537 / +336 |
| cube8 b6 | 14,499 / 34,259 | **15,036 / 34,597** | +537 / +338 |
| cube8 b8 | 14,499 / 34,259 | **15,036 / 34,599** | +537 / +340 |

At seed8776, the b4 base2 reduced circuit helps both resource counts, but 5 of the 6 combinations regress in at least one resource; **do not postselect b4 a2 as the full program's physical win**. Extra 2–4 units of depth for cube8 b6/b8 despite the same CZ reflect additional dynamic instructions; native circuit `depth()` is not measured classical feedforward latency.

**Predeclared full four-seed paired native robustness gate FAIL for ALL SIX base/precision combinations.** The strict comparison was to have ≥3/4 seeds with both native CZ and depth reductions and negative median deltas; the original 8776 baseline anchor was reproduced but none reached ≥3/4:

| Public base + precision | Seeds both CZ and depth lower | Median paired ΔCZ (23−32) | Median paired Δdepth | Robust resource criterion |
|---|---:|---:|---:|---|
| base2 b4 | **2/4** | −287.5 | −1,281 | FAIL |
| base2 b6 | **2/4** | −411 | +568.5 | FAIL |
| base2 b8 | **1/4** | +123 | +2.5 | FAIL |
| cube8 b4 | **2/4** | −286.5 | −1,800 | FAIL |
| cube8 b6 | **2/4** | −286.5 | −1,800 | FAIL |
| cube8 b8 | **2/4** | −286.5 | −1,800 | FAIL |

Negative deltas reduce native costs; positive increase them. All original **24 pairs** (48 Qiskit compilations) were fully retained with per-seed native operations, CZ, top-level depth, physical addresses touched, genuine previous/classical conditions and compiler timings. Thus reduced source width is **verified**, while native routing cost improvement is **not robust** under the preregistered criterion. All physical device feasibility cutoffs **FAIL** across all candidates.

As an additional clear qualification, a reduced cube8 b4 source seed509 touched **23 distinct compiled physical addresses**, while reduced base2 b4 seed509 touched **25**; the compiled *register* still has width156. Even that touched-address count **does not certify** a constant physical phase wire or temporal qubit reusability. Measured/reset/conditional phase operations appear at multiple physical addresses in these examples. The prior mapping/lineage uncertainty is explicitly retained, not silently solved.

## Immutable original CI results, independent audit and zero hardware runtime

[Original two-base native CPU source trial **39738979913**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39738979913) **2/2 SUCCESS**, pinned identical compiler/backend settings and all 48 native outputs and dynamic branch checks. The separately [failed early source harness CI **39738758532**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39738758532) is preserved honestly.

[Independent original-result verification and archival CI **39739268951**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39739268951) **SUCCESS**. It downloaded the two original source-run JSON artifacts **without recompilation**, checked all 48 exact numerical native CZ/depth tuples, exact b4/6/8 stage structure and 9 idle source scratch bits, per-source operation parameter/operand equality, prior 768 stage-unitary / 336 ideal branch proof anchors, 784 native conditional operator successes, 8776 native cost exact reproducibility, 4-seed paired deltas/medians, all unsuccessful native resource gates, preserved physical phase-wire uncertainty and zero QPU. It committed the **original unmodified raw JSON bytes**:

- [Original base2 b4/6/8 4-seed matched width-reduction results](../results/ibm_shor35_true_recycled_idle_scratch_pruning/qrr_n35_prune_idle_scratch_base2.json)
- [Original cubic base8 b4/6/8 4-seed matched width-reduction results](../results/ibm_shor35_true_recycled_idle_scratch_pruning/qrr_n35_prune_idle_scratch_base8.json)

All the original 32q reference source, arithmetic methods, earlier positive and negative results, genuine previous N15 Open Plan real hardware phase recycling pilot, and target-supported feedforward evidence remain unmodified.

## Conclusions and next falsifiable question

**SOURCE-QUBIT WIDTH GATE: PASS**: real adaptive one-phase N35 quantum circuit source now has 23 vs32 qubits with identical previously verified ideal quantum operations and mathematical measurement statistics, across both public bases and b4/b6/b8. This is a genuine removal of unused ancilla allocation, not an arbitrary reset or a contrived state-specific oracle.

**Robust native CZ/depth gate: FAIL** all six under 4 matched seeds. **Physical single-phase-wire routing/latency demonstration: NOT CERTIFIED.** **Immutable real-QPU preflight: FAIL** all 48 native CPU compiled cases; **0** physical QPU jobs, no Open or paid quantum runtime used. No N35 real hardware factoring, new theorem, practical cryptanalysis or cryptographically relevant period-finding evidence.

Next carefully scoped work should audit the **compiled source→physical layout/SWAP phase-wire lineage** across midcircuit measure/reset/if_else operations, or seek true reductions in the remaining active arithmetic comparator/addition qubits rather than retaining unused scratch. Any new physical quantum experiments require a separate verified Open Plan authorization and a circuit passing hardware resource constraints; do not claim a 23-physical-qubit demonstration from a 23-source-qubit compiler artifact alone.
