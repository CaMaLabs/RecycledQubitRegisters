# VERIFIED NEGATIVE — N35 disjoint public prefix comparator gate-proved, but 74–79% MORE IBM Fez target CZ; keep shortened ripple comparator

**Research lead / originating program:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-17. **No quantum processor runtime, jobs, shots or fees were used.** `ibm_fez` was authenticated/read as a *native circuit compilation target only*. This report concerns one N35 six-bit full-residue public controlled modular multiplication, **not** a complete Shor QPE circuit, and certainly not a factoring advantage. N35 is classically trivial.

## Motivation and immutable prior results

The repository already preserved [the actual real IBM Fez N15 Open Plan phase recycling demonstration](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md), successful on a tiny N15 problem, which cannot test cubic order reduction because order(base2 mod15) remains 4 under cubing. Later N35 public base2 vs cube8 CPU compiler studies found ~61% total four-QPE-round savings through two publicly known identity rounds but failed frozen native hardware feasibility **CZ≤800/depth≤2000**. The best subsequent `N35` **single controlled multiplier**, [public low-prefix addition and threshold-shortened ripple comparator](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md), already had strong original direct gate-basis proof and `ibm_fez` native CPU compilation results: base2 **12,517 CZ/depth32,312**, cube8 **12,680 CZ/depth33,138**, **32 logical application qubits / 25 cleaned auxiliaries**. Independent [isolated-components evidence](QRR_N35_PREFIX_THRESHOLD_COMPONENT_ABLATION_RESULT.md) found prefix-carry rewriting strongest and synergistic with the shortened ripple comparator.

Importantly, the [previous N35 shared forward-carry/reverse-borrow candidate](QRR_N35_SHARED_CARRY_REUSE_RESULT.md) was already run and found **56–57% CZ WORSE**, notwithstanding passing full gate-level semantic checks. Its original negative JSON remains in repo. This new experiment does NOT repeat that source or use it as a favorable artificial baseline.

## Frozen, publicly derived comparator hypothesis

[Preregistration](QRR_N35_DISJOINT_PREFIX_COMPARATOR_PREREG.md) was initially committed as `c5c79510139d28ec8da4788ec0a13fc19f7fd054` before any experimental result. **ONE fixed change**, keeping prefix-carry constant addition, old controlled register swaps, clean accumulator uncomputation and cached source enable logic unchanged: replace only the current ripple comparator with **disjoint public threshold bit-prefix minterms**.

For unsigned `x<t`, each set public threshold bit i defines a unique way the first (highest) differing bit could be zero when the threshold bit is one, while all bits above i match t. Those conditions are disjoint, so `[x<t]` is their XOR and `[x≥t]` is its complement. The emitted circuit toggles the target predicate flag using only primitive reversible X/CX/CCX, temporarily X-inverting negative public literals before each `multi_x` and restoring them immediately; it retains the original public trailing-zero reduction of the input comparator width, and restores clean scratch. It does not enumerate residue states, use known multiplicative order, factors, a precompiled orbit or hidden eigenphase. This is an honest generic *public-threshold* combinational comparator, and might naturally perform poorly for dense thresholds.

[Source script](../hardware/qrr_n35_disjoint_prefix_comparator_single_modmul.py) imports the previous verified kernel and changes the predicate only. All direct emitted-gate tests precede IBM Fez CPU compilation. Source and original baseline kept distinct and immutable.

## Gate-level correctness proofs — all PASS

The direct interpreter operated on the ACTUAL emitted X/CX/CCX sequence:

- **42,672/42,672** comparator input cases for every width 1 through 6, each threshold 1 through `2^width-1`, both less-than and greater/equal, both external control values and both initial flag values, with original x unchanged, correct XOR into flag and all carry/scratch bits returned zero. **240 separately built signed-comparator circuits** validated.
- **1,584/1,584** actual-gate modular addition tests per base: 16 distinct publicly generated constants, all 35 valid enabled inputs plus all 64 arbitrary disabled inputs, clean wrap and comparator auxiliaries.
- **128/128** full six-bit modular-multiplier actual-gate basis cases PER base: control `c=0,1`, every work y=0...63, exact `a*y mod35` on valid y<35 when c=1; identity on invalid y and on disabled controls; **all 25 auxiliary qubits returned to zero**, control unmodified. Logical source width remained 32.
- The ideal gate-level basis mapping extends linearly to superpositions with initially clean auxiliaries. This is not proof of accurate operation on noisy hardware, cryptographic quantum advantage or a practical factoring implementation.

The FIRST CI [39070941123](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39070941123) halted on a **test-count bookkeeping assertion**, expecting 21,336 rather than the actual 42,672, because the manual formula omitted the factor of two for both initial flag states; no comparator-operation mismatch had occurred. The [prereg correction commit](https://github.com/CaMaLabs/RecycledQubitRegisters/commit/26990f0da5dc069dff26ebbda895c3e7b812228b) and [assertion correction commit](https://github.com/CaMaLabs/RecycledQubitRegisters/commit/22adf82d9b94d0f42071b0b0dac8df23cf329e13) changed **only the expected number of direct gate cases**, not any arithmetic operation, threshold set, sampling settings, or pass/fail criterion; the first CI reached NO native compiler and submitted NO QPU work. This exception is reported rather than concealed.

The unchanged-design [successful source trial CI **39071031851**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39071031851) **2/2 original base-arm jobs SUCCESS**, verified all tests and compiled with the originally pinned `qiskit~=2.5.2`, `qiskit-ibm-runtime~=0.47.0`, `ibm_fez` native read-only target, transpiler optimization1 and seed8776, no other tuning.

[Independent source artifact receipt audit and archival CI **39071126315**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39071126315) **SUCCESS**: downloaded original experiment JSONs **without rerunning the science**, checked all original gating numbers and baseline JSON, semantic sample counts, unchanged application width and no-QPU status, archived the original two JSON bytes:

- [base2 exact source receipt](../results/ibm_shor35_disjoint_prefix_comparator/qrr_n35_disjoint_comparator_base2.json).
- [cube8 exact source receipt](../results/ibm_shor35_disjoint_prefix_comparator/qrr_n35_disjoint_comparator_base8.json).

## Frozen original native target compiler result

| Metric, exactly ONE controlled N35 modular multiplier | Frozen BEST base2 | New disjoint base2 | Frozen BEST cube8 | New disjoint cube8 |
|---|---:|---:|---:|---:|
| Comparator direct ideal gate tests | old ripple validated | **42,672 PASS** | old ripple validated | **42,672 PASS** |
| Modadd direct ideal cases | 1,584 PASS | **1,584 PASS** | 1,584 PASS | **1,584 PASS** |
| Full multiplier direct ideal cases | 128 PASS | **128 PASS** | 128 PASS | **128 PASS** |
| Clean auxiliary qubits | 25 | **25** | 25 | **25** |
| Logical circuit qubits | 32 | 32 | 32 | 32 |
| Primitive X/CX/CCX total | 1,817 | **2,538** | 1,883 | **2,647** |
| Primitive CX | 1,033 | **233** | 1,077 | **239** |
| Primitive CCX | 756 | **1,225** | 778 | **1,268** |
| **Native IBM Fez-target CZ** | **12,517** | **21,839** | **12,680** | **22,727** |
| **Native IBM Fez-target circuit depth** | **32,312** | **49,751** | **33,138** | **51,441** |
| Predeclared native CZ≤800 and depth≤2,000 | FAIL | **FAIL** | FAIL | **FAIL** |
| Actual real IBM QPU jobs | 0 | **0** | 0 | **0** |

The alternative comparator costs **base2 CZ +74.47% / depth +53.97%** and **cube8 CZ +79.24% / depth +55.23%**, vs original best. It substantially increases source CCX gates (base2 756→1,225; cube8 778→1,268) and X gates due to negative control literals; reducing source CX count does NOT mean lower native CZ. The frozen engineering win gate **FAILED for both**. Even the previous best remains far above physically feasible small Open Plan QPU costs, so **hardware gate FAILED**, and NO device job was attempted. These are resource counts from CPU transpilation, NOT measured gate fidelity, device quantum execution, speed, factor-recovery rate or improvement at cryptographically relevant scales.

## Interpretation and next best direction

**Keep the old public shortened ripple comparator** and the existing best combined `public-prefix-carry` modular adder (original exact JSON and source still intact). Minterm comparator synthesis may be simpler to explain but creates many expensive high-fan-in controls and X toggles in this physical gate basis. Negative control also supports retaining the earlier shared-carry/borrow regression in the historical record.

Future exploratory effort should focus on **reducing the native decomposition cost of controlled Toffoli/multi-control and constant correction**, perhaps comparing a reusable clean *classical-public carry prefix cache* within a SINGLE isolated modular addition, but no automatic four-QPE-bit or paid hardware experiment. A new protocol must freeze semantics and budget before scoring; any apparent generic asymptotic gain needs faithful scaling and meaningful public factoring baselines. The original real Open Plan N15 phase recycling measurement remains an independent milestone and is not affected by this negative.
