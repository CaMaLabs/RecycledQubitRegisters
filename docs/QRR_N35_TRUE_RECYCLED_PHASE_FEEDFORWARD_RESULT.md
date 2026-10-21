# VERIFIED — True one-recycled-phase-qubit N35 dynamic source and ideal 4/6/8 inverse-QFT: 32 quantum qubits, 672/672 matching outcome probabilities, ZERO QPU

**Lead/original research program:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-20 local / 2026-10-21 UTC. **Scope:** an ACTUAL Qiskit dynamic quantum circuit SOURCE with mid-circuit measurements, phase-qubit resets and conditional classical feedforward, plus separately verified phase-exact arithmetic stages and an independent IDEAL branch-model match to full prior WIDE-IQFT readout probabilities. **NO physical IBM processor work, NO backend read, NO native ISA compilation, NO hardware shots or hardware-derived fidelity measurement, NO Open or paid QPU runtime.** Not an end-to-end Qiskit Aer dynamic shot simulation or proof that real device dynamic control is supported.

## From wide to truly recycled — preserved history and frozen preregistration

The original [four-WIDE-phase-source + inverse QFT N35 circuit](QRR_N35_FULL_FOUR_PHASE_IQFT_READOUT_RESULT.md) had **35 quantum qubits** (4 simultaneous phase, 6 work, 25 clean helpers) and exact complex operator phase +1 across each of 1,024 control×64 work inputs for both original and sign-selected arithmetic. Its IBM Fez CPU ISA costs FAIL strict frozen device feasibility CZ≤800/depth≤2000. The later [four/six/eight phase ideal outcome research](QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_RESULT.md) proved the entire mathematical QFT distribution for N35 public a2/a8 with Qiskit Statevector, NumPy FFT and independent complex interference, including base2 strict ordinary CF factor percentages **0%, 11.4756%, 29.2552%** and cubic8 **50% each**. But its b6/b8 circuits were only MATHEMATICAL wide predictions, with unbuilt WIDE source widths37/39.

The new [frozen original preregistration](QRR_N35_TRUE_RECYCLED_PHASE_FEEDFORWARD_PREREG.md), git **f952942dc56ecf8e2ad6fab70056c8544651947a**, froze both public bases N35 a=2 and cubic8, phase precisions b=4,6,8, exactly **ONE quantum phase register bit**, 6 quantum work bits and 25 clean arithmetic helper bits (total 32 qubits), and precisely b CLASSICAL readout bits. It required six distinct source gate-level modular multipliers with +1 quantum phase and ALL outcomes matching previously independently verified wide QFT probabilities, without postselection or change of public factor policy. No compiled public period oracle, known true order or secret factors allowed.

## The actual Qiskit dynamic source constructed

[New source generator, standalone emitted-stage proof and ideal branch model](../hardware/qrr_n35_true_recycled_phase_feedforward.py) builds separate real Qiskit QuantumCircuit objects per public base/phase precision (SIX source circuits total) using one named phase quantum register, 6 work quantum qubits, shared accumulator6, wrap1, validity1, carry6, scratch9, active1, enable1; **32 quantum qubits regardless of b**. It starts work in basis |1>, keeps the entire 6-qubit work register COHERENT, and never measures or resets it. Classical result register has b bits.

For each phase-power stage j from b−1 down to0, compute **public** m_j=pow(base,2**j,35); H the SAME phase qubit, apply the old proven true reversible modular multiplier on public work bits controlled by it (skip only public m_j=1 identity). For EACH earlier measured stage t>j, use a real Qiskit **if_test** conditional on classical result bit **b−1−t** to apply phase P(−2π/2^(t−j+1)) to that reused phase bit. H, measure the phase into classical result bit **b−1−j** and explicitly **reset that same phase qubit** before the next stage, if any. After all stages uncompute the original public six-bit work<35 validity helper. This stage ordering and reversed classical bit convention are crucial: the least significant output bit is measured first. All emitted conditional control-flow instructions, phase angles and destinations were inspected directly in the circuit.

Actual source counts:

| Actual dynamic Qiskit circuit | b4 | b6 | b8 |
|---|---:|---:|---:|
| **Quantum qubits** | **32** | **32** | **32** |
| Classical result bits | 4 | 6 | 8 |
| Mid-circuit phase measurements | 4 | 6 | 8 |
| Phase reset instructions | 3 | 5 | 7 |
| Classical if_else phase-feedforward operations | 6 | 15 | 28 |
| Hadamards on the recycled phase | 8 | 12 | 16 |
| Previous WIDE physical/source quantum count | 35 | 37 (unbuilt) | 39 (unbuilt) |
| IBM Fez native CZ/depth measured for this new dynamic circuit | **NONE** | **NONE** | **NONE** |

There is **no** precomputed UnitaryGate/matrix permutation from public output residues hidden in the dynamic source. It uses the [previous exact signed/positive per-constant source selector](QRR_N35_STATIC_GATE_COST_SIGN_SELECTOR_RESULT.md), regenerated and checked against the original archived 34-row public-k source choices (signed odd k, positive even k), including its phase-aware clean carry source and reversible accumulator uncomputation.

## Actual emitted quantum arithmetic tests — 768 cases PER PUBLIC BASE

The union of DISTINCT nonidentity public powers needed by b4/b6/b8, a2/cube8 is **{2,4,8,11,16,29}**. For each, we built a genuine standalone **32-QUBIT emitted Qiskit quantum arithmetic source**, with work validation recomputed/uncomputed and controlled six-bit public modular power. Then interpreted EACH actual X/CX/CCX/RCCX instruction with Qiskit's **Operator** complex monomial basis action, accumulating actual quantum phase. **All 128/128** control0/1×work y0..63 states passed per power: exact public a*y mod35 when valid and controlled, identity on invalid and disabled, original phase control unchanged, **ALL 25 auxiliary bits zero**, final complex amplitude exactly +1. **Six×128 = 768 exact phase-aware source-basis cases per base PASS**. This verifies real arithmetic emitted gate segments; no factoring result is injected.

This does NOT separately simulate the complete measurement+reset+conditional-classical source as a full 2^32-dimensional noisy quantum trajectory in Qiskit Aer or an IBM processor. The adaptive semantics are checked through separately implemented quantum measurement branch propagation as below.

## Independent ideal quantum conditional branch agreement — all outcomes pass

A coherent **64-amplitude six-work-qubit vector** is tracked for every prior measurement history (do NOT measure the work register), initially work|1>. The ONE reused phase is prepared |+>, the public controlled multiplier transforms only its control1 work amplitude, the classically conditioned phase factor from previously measured bits is applied, H mixes two phase branches, and measurement projects the two **unnormalized complex work vectors**. The branch vector norm squared gives exact ideal branch probability. Every intermediate set of branch norms sums to1 and every final k (with correct reversed output-bit ordering) is included.

Compare every such adaptive probability to the previously [independently verified wide inverse QFT ideal P(k)](QRR_N35_IDEAL_PHASE_PRECISION_4_6_8_RESULT.md) for b4/b6/b8 on both bases:

| Full distribution test | Base2 recycled vs wide max absolute P difference | Cube8 recycled vs wide max difference |
|---|---:|---:|
| 4 bits, 16/16 outcomes | **1.39×10^−17** | **0** |
| 6 bits, 64/64 outcomes | **6.94×10^−18** | **0** |
| 8 bits, 256/256 outcomes | **2.08×10^−17** | **0** |
| **Total** | **336/336 pass** | **336/336 pass** |

**672/672 exact IDEAL outcome probabilities match across both bases**, much tighter than frozen 1e−9 tolerance. Since unchanged strict/bounded public CF factor score depends solely on each outcome k, the model reproduces the archived factor scores:

| Ideal factor score | Base2 b4 | Base2 b6 | Base2 b8 | Cube8 b4 | Cube8 b6 | Cube8 b8 |
|---|---:|---:|---:|---:|---:|---:|
| Strict CF | 0% | 11.4756% | 29.2552% | 50% | 50% | 50% |
| Public bounded multiples up to4, r≤64 | 37.5% | 61.7593% | 79.7151% | 75% | 75% | 75% |

Cubic base8 still yields a trivial public proper factor7 via **gcd(8−1,35)** before any quantum processing; no quantum/classical advantage claim. The old true real-IBM Open-Plan N15 recycled-phase pilot remains a separate independently preserved toy QPU milestone, not evidence of physical N35 hardware feasibility.

## Original CI evidence, independently checked raw source results, and audit bookkeeping failures

[First workflow **39541874090**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39541874090) failed a PRE-SCIENCE wrong folder path pointing to the earlier sign-selector archive, fixed to the original source's documented directory; no quantum control-flow design, proof or numerical acceptance was altered.

[Original completed two-base experiment **39542022177**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39542022177) passed the actual 768-source-gate operator cases per base, built all six Qiskit dynamic sources with inspected reset/feedback conditions, and computed all672 ideal branch probabilities matching wide; it stored TWO complete original result JSONs with **success=true** and original source-run uploaded artifacts. GitHub overall workflow status **FAILURE** reflects only a **POST-SCIENCE auditor field capitalization mistake**: nested structure key was `actual_qpu_jobs` but auditor asked `actual_QPU_jobs`. The science calculation and original JSONs were valid; no QPU run occurred and original data were NOT retuned/recompiled.

The first independent archiving workflow [39542289598](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39542289598) repeated that exact audit-only field-name mistake and stopped. The corrected [independent untouched original-artifact audit **39542358654**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39542358654) **SUCCESS** after changing ONLY the nested audit key. It downloaded the original two numerical artifacts without re-running the science, verified all full stage-operator phase/ancilla/probability source receipts, dynamic measurement/reset/if_else and proper bit order, and independently reconstructed **ALL 672 adaptive measurement branch probabilities with pure-Python sparse complex-work vectors — no Qiskit, no NumPy, no original branch code**. It required every output to match archived original wide results, branch normalization and public factor rates, and byte-preserved BOTH original unaltered receipts:

- [Original base2 true recycled-phase result](../results/n35_true_recycled_phase_feedforward/qrr_n35_recycled_phase_feedforward_base2.json)
- [Original cube8 true recycled-phase result](../results/n35_true_recycled_phase_feedforward/qrr_n35_recycled_phase_feedforward_base8.json)

## Correct scope and next independent falsification

**VERIFIED scientific win:** an actual one-recycled-phase-qubit Qiskit dynamic **source circuit construction**, exact quantum-phase correctness of its six distinct gate-level controlled public powers, correct timing and bit orientation of mid-circuit measurements/resets/conditional feedforward, and independent *IDEAL conditional branch* matching of every wide-QFT output across 4/6/8 bits. A meaningful source quantum-width reduction from 35/37/39 WIDE to **32**, with only 1 live phase qubit, was actually constructed in Qiskit.

**NOT established:** end-to-end IBM dynamic ISA translation/support, real hardware measurement/reset/classical feedback latency, physical quantum coherence/noise, quantum factoring performance on N35, full dynamic circuit native CZ/depth, or feasibility against immutable physical preflight **CZ≤800 AND depth≤2000**. The previous compiled WIDE b4 circuit failed by >one order of magnitude; reducing 3/5/7 live qubits is not necessarily enough. No Open/Paid QPU jobs were ever authorized here or submitted.

**Next falsifiable task:** preregister an **IBM Fez native TARGET read-only CPU-only dynamic control-flow lowerability test**, including whether target supports real-time `if_else`, resets, measurements and conditional phase feedforward, and request actual native resource counts if supported. If target/compiler cannot lower, preserve this negative without relaxing or silently replacing dynamic control flow with a different semantics. No real hardware job even if compiler accepts the source; verify Open Plan and obtain separate explicit scope if ever requesting physical QPU later.
