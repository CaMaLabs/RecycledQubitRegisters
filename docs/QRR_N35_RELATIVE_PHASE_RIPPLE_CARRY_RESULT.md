# VERIFIED NEW BEST — Phase-exact relative-phase Toffoli on temporary N35 comparator carries saves ~26% CZ and ~33% depth, ZERO QPU

**Research lead / original program:** Chase Lunsford / CaMaLabs. **Date:** 2026-10-17. **Scientific scope:** only ONE reversible public full-six-bit-residue controlled modular multiplication for each of public base2 and cube8 mod N35. IBM Fez **authentic backend target was READ for CPU compilation only**. **No QPU job, no free or paid IBM Runtime, no measured hardware fidelity, no complete QPE/Shor circuit, no cryptographic factoring evidence.**

## Preserved original wins, baselines, and stringent QPU gate

The initial [actual IBM Fez N15 Open Plan phase-recycling experiment](QRR_REAL_IBM_OPEN_QPU_SHOR15_MATCHED_RESULT.md) truly recovered N15 factors on a QPU, but N15 base2 order4 is NOT reduced by public cubing. All N35 public-cubic experiments remain CPU-only native target compile studies, preserving negative full-state permutation, Fourier-adder, shared forward-carry/borrow and disjoint comparator cases. The immutable heuristic to even consider a new real N35 device experiment remains **native CZ≤800 AND native depth≤2000, BOTH public arms**, plus future separate user authorization/active Open Plan check.

Our immediately preceding best public full-register arithmetic multiplier is [`hardware/qrr_n35_public_prefix_carry_single_modmul.py`](../hardware/qrr_n35_public_prefix_carry_single_modmul.py), [verified result](QRR_N35_PUBLIC_CONSTANT_PREFIX_CARRY_RESULT.md), frozen Qiskit~=2.5.2, qiskit-ibm-runtime~=0.47, IBM Fez read-only target, optimization1 seed8776. Its exact original untouched receipt JSONs are stored under `results/ibm_shor35_public_prefix_carry/`: **a2 12517 native CZ / depth32312, cube8 12680 native CZ / depth33138**, width 32 logical application qubits (25 clean auxiliaries), all 16 distinct public modulo35 adder constants/128 whole inputs correct with only X/CX/CCX instructions.

This next protocol [`QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_PREREG.md`](QRR_N35_RELATIVE_PHASE_RIPPLE_CARRY_PREREG.md) was **committed before any new phase comparator source compile/scoring** (git `bf8868224f565a8e9cfa9a98b384c192f0350369`). It freezes exactly one change, both public bases, original helper registers and semantics, same target/seed/optimization, and mandatory complex-phase proof BEFORE compiler/backend read.

## Initial attempted placement of RCCX in 3+-controlled clean V-chains: VERIFIED NULL

The first [frozen RCCX clean-V-chain hypothesis](QRR_N35_RELATIVE_PHASE_CLEAN_VCHAIN_PREREG.md) proposed replacing scratch conjunction computing Toffolis by Qiskit RCCX gates and their exact inverse, keeping the final semantic target CCX exact. The [first CI 39072252622](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072252622) and [diagnostic CI 39072323655](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072323655) failed **gate-name/test-assertion assumptions only**; Qiskit represents the RCCX inverse under the same `rccx` name, and we corrected the harness to check `Operator(RCCX.inverse()) @ Operator(RCCX) = identity` instead of expecting a fabricated `rccx_dg` source label.

[Original null-run CI 39072419676](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072419676) then passed the **1022/1022** actual complex-phase scratch V-chain tests, **1584/1584** actual phase-aware modular-add cases and **128/128** full modular multiplication cases, all 25 auxiliaries clean. But it found **0 rccx instructions in BOTH whole N35 circuits**: the preceding cached enable had already reduced remaining multi-control fan-ins below 3! Its native costs were **identically baseline** 12517/12680 CZ and depth32312/33138. The source CI's postcompile audit FAILED correctly for not exercising the intervention, despite source proofs and compilation success. No QPU. [Independent null-results archive CI 39072844818](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072844818) **SUCCESS**, committed exact unchanged null JSONs under `results/ibm_shor35_relative_phase_vchain/`. The original experiment was not a savings result or falsification of RCCX itself, but a **null intervention** in an already control-latched kernel.

## Distinct preregistered solution: use RCCX where the clean *comparator carries* actually live

New [`hardware/qrr_n35_relative_phase_ripple_carry.py`](../hardware/qrr_n35_relative_phase_ripple_carry.py) retains the verified original `best.constant_add_from_prefix_carry` and `best.optimized_modadd`, `best.public_threshold_predicate` including trailing-zero threshold shortening, the original verified `primitive.multi_x` (semantic controlled flag flips exact X/CX/CCX), the old cached active/source enable conditions, whole work/acc swap and inverse uncomputation, the full 64-state 6-bit residue behavior, and identical 32-qubit input register. **Only** `primitive.predicate` gets a phase-aware **temporary carry compute/uncompute** implementation:

- The same publicly known threshold `t` yields the same carry recurrence under input `x + (2^n-t)`. At each bit i≥1, temporarily compute the AND contribution to the clean `carry[i]` using `RCCXGate(x[i],carry[i-1],carry[i])` instead of standard CCX. Preserve every original XOR/CX term for public threshold coefficient 1. The initial carry c0 is unchanged.
- Toggle the predicate output flag with the **unchanged exact semantic target** `primitive.multi_x(...)` controlled by final comparator carry, including the original `geq=False` complement/uncomplement sequence.
- Reverse the temporary carry computation in **reverse bit order** using the **actual Qiskit `RCCXGate().inverse()`** and reverse the associated CX updates in exact reverse order. Qiskit's inverse name is `rccx` in this environment, so correctness checks use actual Qiskit operator matrices rather than gate naming conventions. The internal phases cancel on the tested clean subspace; an RCCX alone is not interchangeable with CCX for semantic target flips.
- Never hardcode multiplicative orders, N35 prime factors, a 12-state orbit, particular work input patterns or a classical factoring oracle. Cubic a8 remains a public constant chosen as 2³ mod35. No actual real-device test.

## Actual quantum-phase correctness, not just a classical reversible truth table

Qiskit's **`Operator(inst.operation)`** is extracted for EACH gate opcode's actual matrix; every source gate must be a computational-basis monomial with a single magnitude-one complex amplitude per column. A fully explicit complex-number amplitude is multiplied along **each actual emitted instruction** on each basis input. Correct *bit outputs and all clean ancillas* are NOT sufficient: the final amplitude must be exactly **+1+0j** within numerical tolerance (no residual relative phases). This guarantees exact action on arbitrary superpositions with those initially clean auxiliaries in the ideal coherent gate model, not fidelity under physical noise.

All phase-sensitive gates pass **before any backend read**:

- **42,672/42,672** standalone comparator actual-gate basis input cases PER base: every bit width 1..6, each threshold1..2^w−1, both unsigned greater-or-equal/less-than, disabled/enabled controls, initial target flag0/1 and every input x. All temporary carry/scratch returned zero; control and x unchanged; exact complex amplitude+1. Source comparator genuinely uses RCCX.
- **1,584/1,584** separate actual-emitted-gate modulo35 addition cases PER base, across the 16 unique public constants generated by both multipliers (35 enabled valid input x plus 64 disabled arbitrary inputs for each constant), all controls unchanged, all helpers zero, exact final complex amplitude+1.
- **128/128** complete public base2 and cube8 controlled modular multiplier states per arm (all y0..63 and c∈{0,1}), expected public arithmetic `a*y mod35` when c=1 and y<35; otherwise identity; **all 25 auxiliary bits clean**, semantic control unchanged, exactly **+1 output complex phase**. Importantly, unlike the earlier null V-chain, the full base2 circuit actually contains **596 RCCX** instructions and cube8 **616 RCCX**, proving the changed gate path was exercised.

Original [2/2 successful native Fez TARGET CPU compilation and gate-unitary CI **39072693905**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072693905) used pinned Qiskit/Runtime versions/optimization1 seed8776, no QPU. [Independent exact-source-artifact audit and unchanged JSON preservation CI **39072788179**](https://github.com/CaMaLabs/RecycledQubitRegisters/actions/runs/39072788179) **SUCCESS**; it downloaded the two original source-run artifacts rather than recompiling, checked all phase proofs, actual RCCX presence, immutable prior baseline JSON, exact compiler metrics, original physical gate and zero-QPU, and committed the original JSON files without altering numerical values:

- [Original base2 phase-ripple result JSON](../results/ibm_shor35_relative_phase_ripple/qrr_n35_relative_phase_clean_vchain_base2.json)
- [Original cubic base8 phase-ripple result JSON](../results/ibm_shor35_relative_phase_ripple/qrr_n35_relative_phase_clean_vchain_base8.json)

*Filenames under the distinct `relative_phase_ripple` folder retain the original test-run basename `relative_phase_clean_vchain_baseX.json`; the receipt internal `revision` and separate folder disambiguate the successful comparator intervention from the null 3+-control chain.*

## Frozen native target results: major new engineering win, but QPU gate still FAILED

| EXACTLY ONE full N35 public controlled multiplier, IBM Fez CPU ISA compiler | Previous best base2 | **Phase-aware comparator base2** | Previous best cube8 | **Phase-aware comparator cube8** |
|---|---:|---:|---:|---:|
| Comparator exact ideal phase proof (new) | n/a | **42,672 PASS** | n/a | **42,672 PASS** |
| Modular add exact ideal phase proof | prior bits only | **1,584 PASS** | prior bits only | **1,584 PASS** |
| Whole controlled multiply exact ideal phase proof | prior bits only | **128 PASS** | prior bits only | **128 PASS** |
| Logical qubits | 32 | **32** | 32 | **32** |
| All auxiliaries returned clean | 25 | **25** | 25 | **25** |
| Source CX | 1033 | **1033** | 1077 | **1077** |
| Source exact CCX | 756 | **160** | 778 | **162** |
| Source relative-phase RCCX | 0 | **596** | 0 | **616** |
| Source X | 28 | **28** | 28 | **28** |
| **Native target CZ** | **12,517** | **9,263** | **12,680** | **9,426** |
| **Compiled native depth** | **32,312** | **21,772** | **33,138** | **21,933** |
| Frozen CZ≤800 AND depth≤2000 device gate | FAIL | **FAIL** | FAIL | **FAIL** |
| Real IBM QPU jobs / paid runtime | 0 | **0** | 0 | **0** |

**Frozen engineering gate PASS both arms:** base2 CZ **−26.00%** and native depth **−32.62%**; cube8 CZ **−25.66%**, native depth **−33.81%**. The new circuit retains all 32 logical application qubits; 596 or 616 exact comparator CCX temporary-compute instances are instead phase-aware RCCX, and 160/162 exact CCX remain for semantic operations. Qiskit target ISA compiled fewer CZs; these are native gate-count/depth proxy results only, NOT observed quantum device reliability.

**Immutable hardware feasibility gate FAIL:** even the best 9,263 CZ / depth21,772 is **11.58× native CZ and 10.89× native depth** above the frozen 800/2000 heuristic *for a single modular multiplier*, before any full Shor 4-phase-bit sequence. No physical Open Plan or paid IBM Runtime was used. No new real N35 factoring, no quantum cryptanalytic breakthrough, no practical RSA impact, and no guarantee that unmeasured coherent-device noise permits even toy factoring.

## Reproducibility and research implications

All preregistrations, negative/null controls, phase-aware source, complete independent original artifacts and experiment result remain in `main` as attributable CaMaLabs research. The fixed seed single transpilation quantifies a legitimate controlled engineering ablation, **not** robust multi-layout statistics or a mathematically novel asymptotic algorithm. A next best step is to explore **exact quantum-semantic phase-preserving comparator/native decomposition and then whole-four-round QPE** only when gate budget warrants, with a new frozen protocol and Open Plan-only real-QPU authorization gate; no change to proven N15 hardware milestone or original four-round N35 native failures.
