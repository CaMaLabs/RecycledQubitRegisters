# VERIFIED NEGATIVE — N35 public shared forward carry and reverse borrow uncompute: 8192+1584+128 gate proofs PASS, native CZ costs WORSEN ~56%

**Research lead/original program: Chase Lunsford / CaMaLabs.** Experiment time 2026-10-17 UTC. **This is IBM Fez READ-ONLY NATIVE ISA CPU compilation, NOT IBM quantum device execution; 0 QPU jobs, 0 free Open Plan runtime, 0 paid runtime.**

## Prior history and frozen preregistration

Previous actual real Open Plan IBM Fez N15 Shor factoring of 3×5 with phase-register recycling remains a genuine tiny-N hardware result; it does NOT validate Dark Star cubing. N35 public base2 (validation order12) to cubic base8 (validation order4) compiler-only ablations have produced multiple verifiable reversible arithmetic and conditional native-gate reductions, but NONE have passed the immutable **CZ<=800 and depth<=2000** real-device physical feasibility heuristic. No N35 circuit has been submitted to the actual quantum device.

Immediately preceding [best combined low-prefix carry and public threshold shortening result](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md) was base2 **12517 native CZ/depth32312** and cube8 **12680 CZ/depth33138** on one public 6-bit-residue controlled modular multiplication (not complete QPE), logical32 application qubits, 25 clean auxiliary qubits. The [isolated prefix/threshold component controls](QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_RESULT.md) established that the combination is more efficient than either individual change, under the same fixed Qiskit target, seed and optimization. Original numerical receipts are immutable.

The new **SINGLE fixed algorithmic change** was preregistered in [`QRR_N35_SHARED_CARRY_REUSE_PREREG.md`](QRR_N35_SHARED_CARRY_REUSE_PREREG.md) **commit `c3b61efe87ab2ce6725e739a84c295a20777ab57`** BEFORE new native cost measurements. The hypothesis: reuse intermediate public-constant carry bits across all output-bit updates, rather than re-evaluating low-prefix threshold comparators repeatedly. All other code/protocols are the previously verified public full-register N35 multiplier, cached enable controls, modular wrap and trailing-zero shortened predicates.

## New correct reversible X/CNOT/Toffoli implementation

[New source](../hardware/qrr_n35_shared_carry_borrow_single_modmul.py) replaces only the old `constant_add_from_prefix_carry` helper at build time while preserving the original `optimized_modadd`, validity guard, active/enable controls, accumulator, inverse cleanup, 32 logical qubits and N35 full residue mapping. No private factors, known multiplicative order, precomputed orbit or 64-state synthesized truth-table oracle.

For an enabled public constant `k`, new adder computes one ripple carry chain from the original input into the **existing six zeroed carry ancillas** using public constant-bit AND/OR recurrence. It toggles each output bit with `x_j XOR (enable & k_j) XOR carry_j` with X/CX/CCX gates. To erase carries **AFTER x changed**, the inverse borrow recurrence of subtracting k from updated output reproduces the original addition carries; gates are emitted in reverse order to XOR every stored carry back to zero. Uses coherent negative control temporarily flipping output bits with paired X gates, restoring them. This realizes actual clean, coherent ideal conditional modular-64 addition without borrowing private arithmetic or carrying garbage to later operations.

**Three independent levels of actual emitted-gate proof BEFORE Qiskit ISA compilation, per base**:

- **8192/8192 direct binary-gate basis tests**: all k∈[0,63] × all x∈[0,63] × both enable states for `+k mod64`, zero 6 carry and 9 scratch bits, original control preserved. This tests the forward carry AND backward borrow uncompute, not merely shadow mathematical arithmetic.
- **1584/1584 modular-35 controlled-addition direct-gate cases**: all 16 public constants used across both original/cubic public multiplication kernels ×35 valid enabled operands plus64 arbitrary disabled operands; wrap/carry/scratch flags cleaned.
- **128/128 full controlled multiplication direct-gate cases** per base: y∈[0,63], control∈{0,1}, coherent full-residue unitary with y>=35 unchanged and all **25 ancilla qubits returned zero**, control preserved, original cached active/enable and inverse modular uncomputation. Each X/CX/CCX circuit is a reversible permutation, so correct basis action with initially clean auxiliaries extends linearly to superpositions on that subspace, but not to QPU noise/fidelity.

Original [two fixed GitHub Actions jobs **39060426103**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39060426103) **2/2 SUCCESS**; each used authenticated `ibm_fez` **backend target read only** and CPU native transpilation, pinned Qiskit~=2.5.2/runtime~=0.47.0, optimization level1 and transpiler seed8776, no real hardware submission. Both CI jobs pass their gate-level proof and receipt validators, even though engineering and hardware cost gates FAILED.

An independent [original-artifact audit and preservation workflow **39060515347**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39060515347) **SUCCESS** downloaded exactly the two original source-job JSON receipts, verified prior frozen baselines, original/native ops, source primitive gates, all 8192+1584+128 gate proofs, original no-runtime flags and failed native CZ/depth engineering thresholds, and committed original bytes unchanged to:
- [base2 original receipt](../results/ibm_shor35_shared_carry_borrow/qrr_n35_shared_carry_borrow_base2.json)
- [cube8 original receipt](../results/ibm_shor35_shared_carry_borrow/qrr_n35_shared_carry_borrow_base8.json)

## Frozen native results — ONE multiplication, not a complete Shor factoring algorithm

| N35 controlled full-residue modular multiplication | Original base2 | Shared carry base2 | Original cube8 | Shared carry cube8 |
|---|---:|---:|---:|---:|
| Emitted X/CX/CCX primitive gate count | 1817 | **1897** | 1883 | **1917** |
| Qubits in circuit | 32 | 32 | 32 | 32 |
| All actual gate semantic proofs | old PASS | **8192+1584+128 PASS** | old PASS | **8192+1584+128 PASS** |
| 25/25 auxiliaries clean | yes | **yes** | yes | **yes** |
| Native IBM Fez target compiled CZ | **12517** | **19552** | **12680** | **19895** |
| Native compiled depth | **32312** | **42236** | **33138** | **43075** |
| Frozen <=800 CZ and <=2000 depth | FAIL | **FAIL** | FAIL | **FAIL** |
| Actual IBM QPU jobs | 0 | **0** | 0 | **0** |

**New verified negative:** base2 native CZ **increased by 7035 (+56.20%)** and depth **increased by 9924 (+30.71%)**; cubic base8 CZ **increased by 7215 (+56.90%)** and depth **increased by 9937 (+29.99%)**. The single reusable forward-carry ladder makes arithmetic semantically correct, but its controlled AND/OR compute and inverse borrow cleanup synthesize more expensive IBM Fez native two-qubit gates than the earlier individually uncomputed public low-prefix comparator design. This is a hardware-target *compilation* observation, not an actual hardware error, noise or measurement claim. It also adds no benefit in logical width.

**Engineering improvement gate FAILED for BOTH fixed public bases** (native CZ and depth worse). **Physical device gate FAILED** as before (even old best has >12k CZ for one multiplier). No hardware or full 4-bit Shor circuit is justified. This negative result is recorded **without removing earlier successful outcomes or changing the frozen threshold post hoc**. The best version stays the old combined [low-prefix public threshold](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md).

## What to do next

The issue is not correctness or the ability to reuse carry logically, but cost of conditionally computing *and erasing* the carry chain with unoptimized high-fan-in control structures. Stronger alternatives should optimize reusable carry conditionalization itself or use an optimized native-compatible constant-specific Toffoli adder. One separate preregistered single-element ablation could: (a) reduce duplicated `enable` controls in the forward/reverse carry chains by a dedicated clean carry-active latch; (b) specialize 2-adic carry for sparse constants in public base powers; (c) eliminate costly modulo35 wrap comparisons with a proof-preserving carry correction design. As previously, **run 8192+1584+128 direct-gate tests before native compilation, use identical controlled comparison settings, and forbid real QPU until the separately frozen feasibility gate is met.**

The real N15 IBM QPU phase-recycling win is unaffected, and no claim is made about new RSA-scale quantum cryptanalysis or scalable algorithm performance.
